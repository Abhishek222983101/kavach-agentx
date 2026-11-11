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
| Photo evidence | ✅ Gemini vision answers fixed questions, our rules score it; screenshot → blocked, unclear → seller. No real damaged-item sample photo yet | `tests/test_vision.py`, live check 12 Nov |
| WhatsApp | ✅ live on the Twilio sandbox (poll mode locally); budget footer; web-demo traffic never uses paid WhatsApp (D-20) | live chats 12 Nov |
| Telegram | ✅ live (@kavach_agentx_bot), seller Approve/Reject buttons | live 12 Nov |
| Seller email | ✅ outbound cards; **no inbound customer email** | `tests/test_channels.py` |
| Seller alert calls | ✅ live; one real call placed and answered (press 1 → re-verified → paid); 1 of 10 calls used | `tests/test_calls.py`, audit rows 136–140 |
| Website | ✅ landing, live demo, seller console, proof, receipts; runs on localhost only | screenshots in session; `scripts/verify_tries.py` |
| Prompt-only baseline (B0) | ✅ endpoint `/api/arena` (simulated, never moves money); refused the obvious owner scam 3/3 | manual run 12 Nov |
| Eval harness (Phase 8) | ✅ 30 scenarios; Kavach 0/19 harm, 0/11 honest blocked; B0 6/54 | `eval/reports/report.md` |
| Deploy | ✅ https://kavach-agentx.vercel.app + Render Singapore; keepalive until 16 Nov | `Dockerfile`, `.github/workflows/keepalive.yml` |
| ML guard model | ⬜ | — |
| Tests and scans | ✅ 98 tests; bandit, semgrep, pip-audit clean; 2 minor build-time npm advisories | `just test`, `just security` |
