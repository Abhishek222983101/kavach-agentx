# Kavach build log (plain language)

> For the team and anyone reviewing the work. Newest phase at the bottom. Each entry says what was built, why, how it works, and the proof (tests, security scans). Technical details: `docs/03-SYSTEM/SYSTEM-ARCHITECTURE.md`.

## Where we are
| Phase | What | Status |
|---|---|---|
| 0 | Foundation: code layout, database, permissions, tamper-proof log | ✅ done (11 Nov, 23:15) |
| 1 | Mock online store (orders, couriers, payments) | ⏳ next |
| 2 | The checker (verifier) and the only component allowed to act (executor) | ⬜ |

---

## Phase 0: the foundation

**What we built**
- A clean code layout: everything lives in `backend/kavach/`, split by job (`store/`, `trust/`, `api/`, `db/`, `common/`).
- The full database on Neon (Postgres 18, Singapore region): customers, orders, shipments, payments, refunds, returns, policy rules, conversations, proposals, verdicts, approvals, executions, settings, events, and the audit log. 20 tables.
- Two database users with the least power each job needs:
  - **reader**: used by the chat/agent side. It can read everything and record conversations, but **cannot touch money**: it can't create a refund, change an order, change settings, or record an execution.
  - **writer**: used only by the store and the trust service.
- A **tamper-evident audit log**. Every row stores a fingerprint (SHA-256 hash) of itself plus the previous row's fingerprint, like a chain. Change any old row and every fingerprint after it stops matching.
- Shared "contracts": the exact shapes of a proposal, a claim, a verdict and a token, so every part of the system speaks the same language. Money is always whole paise (no decimals, so no rounding errors).

**Why it matters**
The judges' reliability judge asked "how does it handle failures and why these design choices". Our answer starts here: safety is enforced by the **database itself**, not by asking the AI nicely. Even if the AI part were completely tricked, its database user physically cannot write a refund.

**Proof**
- 7 automated tests pass. They run against a throwaway Postgres in Docker, so they never touch the real database. The tests check that:
  - the reader user is refused when it tries to insert a refund, change an order, change settings, record an execution or create a proposal;
  - nobody can insert into the audit log directly, only through the one append function;
  - the audit log refuses edits and deletes from the app's users (no permission) **and** from the database owner (a trigger blocks it);
  - a tampered copy of the log is caught at exactly the row that was changed.
- Neon checked live: the reader user was refused a refund insert.
- Security scans: **bandit** (Python code) found nothing at medium severity or above; **semgrep** (Python + secrets rules) found nothing; **pip-audit** found no known vulnerable dependencies.
