---
name: status
description: Use when the owner asks "where are we", "what is built", "what is next", "status", or wants a short progress update. Reads the notebook and reports the honest state in plain language.
---

# Status

Read:

- `docs/state.json`
- `docs/00-START-HERE.md`
- `docs/04-DELIVERY/BUILD-PLAN.md`
- `docs/04-DELIVERY/CURRENT-STATE.md`
- `docs/04-DELIVERY/OPEN-QUESTIONS.md`

Then give a short update in this shape:

```text
Project: <name> — <one-line idea>
Stage: <stage>
Built: <3 bullets, honest>
In progress: <1–3 bullets>
Next: <3 bullets>
Top questions:
1. <question> — why it matters
2. ...
Risks: <1–3, only if real>
Notebook: <completeness>% — <what is missing>
```

Rules:

- Keep it under 25 lines.
- Do not pad with praise.
- If something is mocked or broken, say so.
- If the notebook is stale, say which file and offer to run `doc-sync`.
- If there is no notebook yet, say so and offer to run `start-here`.
