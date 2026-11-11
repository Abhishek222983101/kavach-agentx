---
name: doc-sync
description: Use after any code change, before ending a session, or when the notebook may be stale. Brings the PRD, workflows, architecture, data model, integrations, delivery docs and session log back in line with the actual code. Never finish a code change without it.
---

# Doc sync

Goal: the notebook must describe the app that exists, not the app that was planned or the app the demo pretends to be.

Work from evidence: the diff, the running app, the schema, the logs, the deployment. Do not copy claims from the chat.

## 0. Gather evidence

Run or inspect:

```bash
git status --porcelain
git diff --stat
git diff
```

Then read the files that changed. If the project is not a git repo, list the files modified today and read them.

Also inspect the relevant source of truth:

- routes / pages / screens
- API handlers / server actions
- database schema / migrations / ORM models
- `.env.example`
- deployment config (`vercel.json`, `Dockerfile`, `docker-compose.yml`, `fly.toml`, etc.)
- package manifests
- logs / error tracking if available

## 1. The sync checklist

For each change, ask: **who needs to know this, and in which file?**

| Question | File |
|---|---|
| Did a user-visible behaviour change? | `docs/02-PRODUCT/PRD.md` |
| Did a workflow, step, actor, decision or exception change? | `docs/02-PRODUCT/WORKFLOWS.md` |
| Did a component, data flow, API, auth rule, job, deployment or security posture change? | `docs/03-SYSTEM/SYSTEM-ARCHITECTURE.md` |
| Did an entity, field, relationship or retention rule change? | `docs/03-SYSTEM/DATA-MODEL.md` |
| Did a third-party service, account, API or webhook change? | `docs/03-SYSTEM/INTEGRATIONS.md` |
| Was a non-obvious choice made? | `docs/04-DELIVERY/DECISIONS.md` |
| Is something now real, mocked, hard-coded, broken or untested? | `docs/04-DELIVERY/CURRENT-STATE.md` |
| Did the plan or next step change? | `docs/04-DELIVERY/BUILD-PLAN.md` |
| Is there a new "what if this goes wrong" scenario? | `docs/04-DELIVERY/SCENARIOS.md` |
| Is there a new unanswered question or assumption? | `docs/04-DELIVERY/OPEN-QUESTIONS.md` |
| Did we learn something about how the business really works? | `docs/01-BUSINESS/DEEP-CONTEXT.md` |
| Would the owner or staff notice the change? | `docs/06-HANDOFF/CHANGELOG.md` |
| What happened this session? | `docs/05-SESSIONS/SESSION-LOG.md` |
| How did the owner ask, decide, or change their mind? | `docs/05-SESSIONS/PROMPTING-PATTERNS.md` |

Not every row applies to every change. Say which ones you checked and which did not apply.

## 2. Drift audit

Look for things the chat forgot:

- new routes, screens or pages with no PRD requirement
- new tables, columns or migrations with no data-model entry
- new env vars with no `.env.example` entry
- new third-party services with no integration entry
- hard-coded values, fake users, seed data, placeholder numbers
- `TODO`, `FIXME`, `HACK`, `mock`, `fake`, `coming soon`, `console.log`
- disabled auth checks, open database rules, public buckets
- deploy steps that only exist in someone's head
- features the owner believes exist but do not
- features that exist but the owner does not know about

Add each finding to the right doc. If it is a problem, add it to `CURRENT-STATE.md` and, if it needs a human answer, `OPEN-QUESTIONS.md`.

## 3. Session entry

Write a new entry at the top of `docs/05-SESSIONS/SESSION-LOG.md` using the template. Include:

- what the owner asked for, in their words
- what you understood
- what changed
- decisions (`D-…`)
- assumptions (`[ASSUMED]`)
- open questions (`Q-…`)
- what is real vs mocked
- what is next
- prompting notes

## 4. Prompting patterns

If the session revealed something about how the owner works, update `docs/05-SESSIONS/PROMPTING-PATTERNS.md`:

- a recurring phrase and what it means
- what they cared about
- what they ignored
- a reversal or contradiction
- a technical misconception
- how to communicate better next time

Quote a real prompt with the date. Do not speculate.

## 5. Status updates

Update:

- `docs/state.json` — project name, stage, current focus, next question, open questions count, assumptions count, handoff ready, last session, last updated
- `docs/00-START-HERE.md` — the human-readable status table and current focus
- `docs/04-DELIVERY/BUILD-PLAN.md` — phase status and next 3
- `docs/06-HANDOFF/CHANGELOG.md` — user-visible changes

Keep `state.json` valid JSON.

## 6. Consistency pass

Before finishing:

- [ ] Every new requirement has an ID and acceptance criteria.
- [ ] Every new workflow is in the index.
- [ ] Every new screen/route is in the PRD or workflow.
- [ ] Every new entity/field is in the data model.
- [ ] Every new env var is in `.env.example` and `INTEGRATIONS.md`.
- [ ] Every `[ASSUMED]` is in `OPEN-QUESTIONS.md`.
- [ ] Every `[UNKNOWN]` is either answered or in `OPEN-QUESTIONS.md`.
- [ ] `SYSTEM-ARCHITECTURE.md` matches the code.
- [ ] `CURRENT-STATE.md` is honest about what is fake.
- [ ] The session log is written.
- [ ] `state.json` and `START-HERE.md` are current.

## Rules

- Update the notebook in the same turn as the code. Do not say "I will document later."
- Never delete history. Move superseded text to `docs/99-ARCHIVE/`.
- Date every change.
- Prefer a short, true entry over a long, vague one.
- If you cannot verify a claim, write `[UNKNOWN]` or `[ASSUMED]`.
- If the change was trivial, say so in the session log and update `state.json` anyway.
