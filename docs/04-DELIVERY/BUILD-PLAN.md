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
| 0 | Repo, env, DB, contracts | ⬜ | |
| 1 | Mock Store API | ⬜ | |
| 2 | Verifier, executor, audit | ⬜ | hardest |
| 3 | Agent graph + LLM + web chat | ⬜ | |
| 4 | Channels | ⬜ | |
| 5 | ML guard (+ seller preference) | ⬜ | GPU check first |
| 6 | Web console | ⬜ | |
| 7 | Deploy | ⬜ | Q-04 |
| 8 | Eval, arena, chaos | ⬜ | |
| 9 | Stretch | ⬜ | |
| 10 | Freeze and submit | ⬜ | 08:00 freeze |
