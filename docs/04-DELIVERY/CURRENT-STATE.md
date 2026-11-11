---
doc: current-state
status: active
last_updated: 2026-11-12
---

# Current state (honest)

| Area | Status | Evidence |
|---|---|---|
| Database (Neon): schema, least-privilege roles, hash-chained append-only audit log | ✅ real, tested; the AI's role gets `permission denied` writing refunds, shown live on `/proof` | `tests/test_db_security.py`, `/api/proof/roles` |
| Mock store + per-visitor demo shops | ✅ real, tested; **mock data** (sample orders), clearly labelled as a demo shop | `tests/test_store.py` |
| Trust service: verifier, router, signed one-time slips, executor, kill switch, approvals | ✅ real, tested | `tests/test_trust.py` |
| Agent (LangGraph, Groq → Gemini, Hindi/Hinglish/English) | ✅ real, tested; guard is **rules only** (ML guard not built yet) | `tests/test_agent.py` |
| Photo evidence | 🟡 any image counts as a photo; vision check planned (Phase 5-lite) | known gap |
| WhatsApp | ✅ live on the Twilio sandbox (poll mode locally); budget footer; web-demo traffic never uses paid WhatsApp (D-20) | live chats 12 Nov |
| Telegram | ✅ live (@kavach_agentx_bot), seller Approve/Reject buttons | live 12 Nov |
| Seller email | ✅ outbound cards; **no inbound customer email** | `tests/test_channels.py` |
| Seller alert calls | ⬜ planned (D-21), not built | — |
| Website | ✅ landing, live demo, seller console, proof, receipts; runs on localhost only | screenshots in session; `scripts/verify_tries.py` |
| Prompt-only baseline (B0) | ✅ endpoint `/api/arena` (simulated, never moves money); refused the obvious owner scam 3/3 | manual run 12 Nov |
| Eval harness (Phase 8) | ⬜ | — |
| Deploy | ⬜ localhost only | — |
| ML guard model | ⬜ | — |
| Tests and scans | ✅ 74 tests; bandit, semgrep, pip-audit clean; 2 minor build-time npm advisories | `just test`, `just security` |
