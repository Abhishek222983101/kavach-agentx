---
doc: build-plan
status: active
last_updated: 2026-11-11
---

# Build plan

The full plan (phases, sub-phases, acceptance tests, timings, cut rules) lives in one place:
**[`../03-SYSTEM/SYSTEM-ARCHITECTURE.md` §20](../03-SYSTEM/SYSTEM-ARCHITECTURE.md#20-build-plan-phase-by-phase)**.
This file only tracks status.

| Phase | Name | Status | Notes |
|---|---|---|---|
| 0 | Repo, env, DB, contracts | ✅ | 22:52; 7 tests |
| 1 | Mock Store API | ✅ | 22:56; Neon seeded |
| 2 | Verifier, executor, audit | ✅ | 23:08; AT-01…13 + 13 more; trust service (D-15) |
| 3 | Agent graph + LLM + web chat | ✅ | 23:58; 55 tests; live run with Groq |
| 4 | Channels | ⬜ | |
| 5 | ML guard (+ seller preference) | ⬜ | GPU check first |
| 6 | Web console | ⬜ | |
| 7 | Deploy | ⬜ | Q-04 |
| 8 | Eval, arena, chaos | ⬜ | |
| 9 | Stretch | ⬜ | |
| 10 | Freeze and submit | ⬜ | 08:00 freeze |
