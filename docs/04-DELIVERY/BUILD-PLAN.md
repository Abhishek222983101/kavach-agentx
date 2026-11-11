---
doc: build-plan
status: active
last_updated: 2026-11-12
---

# Build plan

The full plan (phases, sub-phases, acceptance tests, timings, cut rules) lives in one place:
**[`../03-SYSTEM/SYSTEM-ARCHITECTURE.md` §20](../03-SYSTEM/SYSTEM-ARCHITECTURE.md#20-build-plan-phase-by-phase)**.
This file only tracks status.

| Phase | Name | Status | Notes |
|---|---|---|---|
| 0 | Repo, env, DB, contracts | ✅ | 22:52 (11 Nov) |
| 1 | Mock Store API | ✅ | Neon seeded; per-visitor demo shops (D-17) |
| 2 | Verifier, executor, audit | ✅ | trust service (D-15) |
| 3 | Agent graph + LLM + web chat | ✅ | Groq → Gemini fallback |
| 4 | Channels | ✅ | WhatsApp (poll, budget-capped), Telegram buttons, seller email, seller commands |
| 6 | Website | ✅ | 12 Nov ~04:30; landing, live demo, seller console, proof + receipts; revamped after owner review (D-24) |
| 7 | Deploy | ✅ | 12 Nov 04:10; Render Singapore + Vercel; keepalive Action; chat p50 1.6 s |
| Agent | Agent upgrade | ✅ | 04:20; AI-chosen reads + safety floor, two requests, numbered questions, refund status |
| 4b | Seller alert calls | ✅ | 04:30; live test: called, seller pressed 1, re-verified, paid; 3/day, 10 total |
| 5-lite | Photo check (Gemini vision) | ✅ | 04:40; screenshot scored 0.05 → blocked; unclear → seller |
| 8 | Eval: B0 vs Kavach | ✅ | 05:05; Kavach 0/19 harm, 0/11 honest blocked; B0 6/54 tries paid |
| 10 | Freeze and submit | ⏳ | README, video ≤ 3 min, 6 slides, repo public, portal by 10:00 |
| 5 | ML guard (GPU, W&B) | ⏳ last | D-23: after submission is safe; must commit inside the window |
| 9 | Stretch | ✂️ | inbound customer email (see Q-15) |

**Time plan (12 Nov):** 7 → ~05:30 · 4b → ~06:30 · 5-lite → ~07:00 · 8 → ~07:45 · 10 → ~09:15 · 5 (ML) in the remaining time, with the submission already saved.
