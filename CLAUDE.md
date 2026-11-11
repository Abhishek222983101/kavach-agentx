@AGENTS.md

# Claude Code specifics

- The project notebook lives in `docs/`. Read `docs/00-START-HERE.md` first.
- Use the skills in `.claude/skills/` when the task matches their description. They are:
  `start-here`, `context-interview`, `deep-dive`, `doc-sync`, `arch-keeper`, `handoff`, `status`.
- `docs/05-SESSIONS/PROMPT-LOG.md` is append-only and written by a hook. Do not edit it.
- Keep `docs/state.json` valid JSON. Hooks and tools read it.
- When the owner says "handoff", "ship", "done", "package it", or similar, run the `handoff` skill.
- Do not paste secrets into the notebook. Use `.env` and `.env.example`.
