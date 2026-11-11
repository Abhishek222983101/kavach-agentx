---
doc: workflows
status: draft
last_updated: 2026-11-11
---

# Business workflows

Screen-level detail: `APP-FLOW.md`. Technical flow: `../03-SYSTEM/SYSTEM-ARCHITECTURE.md` §8.

| ID | Workflow | Actors | Happy path | Decisions | Exceptions | Permission |
|---|---|---|---|---|---|---|
| W-01 | Where is my order | Customer, agent | Identify order → courier status → reply | Which order (ask if unclear) | Courier down → retry ×2 → escalate | Customer, own orders only |
| W-02 | Return | Customer, agent, verifier, executor | Check window/eligibility/policy → create pickup → confirm by chat + email | In window? Returnable? | Perishable → refuse with clause | Own orders |
| W-03 | Refund ≤ limit | + executor | Verify all claims → ALLOW → refund → reply | Photo needed for damage? | Duplicate → block | Own orders |
| W-04 | Refund > limit | + seller | Verify → ESCALATE → seller approves/edits/rejects → execute | Seller decision | Approval expires 24 h → customer told seller will call | Seller only approves |
| W-05 | Address change | Customer | Before dispatch, identity matches → update | Dispatched? | After dispatch → escalate to seller | Own orders |
| W-06 | Cancel | Customer | Not dispatched → cancel | — | Dispatched → offer return instead | Own orders |
| W-07 | Escalate to human | Agent, seller | Summary to seller on WA/TG/console | — | Seller offline → console queue + email | Seller |
| W-08 | Freeze writes | Seller | Kill switch (console, `/freeze`, keypad on alert call) | — | — | Seller only |
| W-09 | Seller onboarding | Seller | Send policy → confirm extracted rules → live | — | Unreadable photo → ask for text | Seller |
| W-10 | Critical alert (stretch) | System, seller | Blocked attack ≥ ₹2,000 → call verified seller number | Daily cap reached? | Dry-run → no call | System |

Volumes for the demo persona: about 1,500 orders a month `[ASSUMED, from the idea deck persona]`.
Cost of a mistake: a wrong refund is lost money plus a precedent customers repeat; a wrongly blocked legitimate refund costs trust. Both are measured in `eval/`.
