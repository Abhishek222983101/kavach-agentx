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
| 7 | Deploy | ⏳ next | Render (Singapore) + Vercel; owner must run `render login` |
| 4b | Seller alert calls | ⏳ | D-21; ~1 h; IVR approve needs the public URL from Phase 7 |
| 5-lite | Photo check (Gemini vision) | ⏳ | closes "any image passes" |
| 8 | Eval: B0 vs Kavach | ⏳ | `eval_` sessions only (no WhatsApp spend) |
| 10 | Freeze and submit | ⏳ | README, video ≤ 3 min, 6 slides, repo public, portal by 10:00 |
| 5 | ML guard (GPU, W&B) | ⏳ last | D-23: after submission is safe; must commit inside the window |
| 9 | Stretch | ✂️ | inbound customer email (see Q-15) |

**Time plan (12 Nov):** 7 → ~05:30 · 4b → ~06:30 · 5-lite → ~07:00 · 8 → ~07:45 · 10 → ~09:15 · 5 (ML) in the remaining time, with the submission already saved.
