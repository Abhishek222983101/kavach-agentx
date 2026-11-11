# How to use this kit

Three modes. Pick one per project. Do not run the full ceremony on a weekend project.

---

## Mode 1: Personal project (long-running)

Use the kit as project memory. It stops you re-explaining the same thing every session.

### First time

1. Drop the kit into the project root.
2. Open Claude Code.
3. Type `start here`.
4. Answer only these five:
   - What is this project, in one sentence?
   - Who is it for?
   - What is the first workflow?
   - What does "working" look like?
   - What should never happen?
5. Let the agent fill the notebook. Do not fill every `[UNKNOWN]`. Partial is fine.

### Every session

1. Open the project. The hook shows the current focus and next question.
2. Ask `status` if you want a quick recap.
3. For a non-trivial feature, run `/context-interview`. For a tiny fix, skip it.
4. Use graft for code questions:
   ```bash
   graft ask "where is auth handled"
   graft callers createOrder
   graft skeleton src/services/orders.ts
   ```
5. Build.
6. At the end, run `/doc-sync`. The stop hook will nudge you if you forget.
7. After architectural changes, run `/arch-keeper`.

### Every few sessions

- Read `docs/04-DELIVERY/CURRENT-STATE.md`. If it is lying, fix it.
- Read `docs/04-DELIVERY/OPEN-QUESTIONS.md`. Answer the top 1–3.
- Run `node tools/check-docs.mjs` to see what is stale.

### Before a long break or machine switch

Run `/handoff`. You get a zip with the notebook, code snapshot, git history and a brief. Future-you will thank you.

### Personal-project rules

- Keep docs short. Tables and bullets, not essays.
- One fact, one home. Link to code instead of pasting it.
- Skip the business sections that do not apply. Answer as yourself.
- Use `CURRENT-STATE.md` to track stubs, fake data and known bugs.
- Use `DECISIONS.md` for "why I did it this way" — future-you forgets.
- Use `SESSION-LOG.md` as a learning journal.
- Do not document every tiny change. Batch at milestones.

---

## Mode 2: Hackathon (24–48 hours)

Speed matters. Use a lite version.

### Hour 0: 5-minute setup

1. Drop the kit into the repo.
2. Type `start here`.
3. Answer only:
   - What are we building?
   - Who is the demo for?
   - What is the one demo flow?
   - What is in scope for the demo?
   - How do we know it works?
4. Tell the agent:
   ```text
   Hackathon mode. Skip deep-dive and long interviews unless something blocks the build.
   Update only CURRENT-STATE.md, DECISIONS.md, OPEN-QUESTIONS.md and SESSION-LOG.md during the build.
   Run doc-sync at milestones, not after every edit.
   ```

### During the build

- Use graft for code navigation. Do not waste time reading files blindly.
- Use the PRD only for the demo flow. Do not write a full product spec.
- Keep `CURRENT-STATE.md` honest: what works, what is fake, what is broken.
- Add decisions as you make them. This becomes your submission writeup.
- The prompt log runs automatically. Some hackathons require spec/prompt artifacts — this gives you them.

### Last 2 hours

1. Run `/handoff`.
2. Fill only the top of `HANDOFF.md`:
   - what it does
   - what works
   - what is fake or broken
   - how to run it
   - demo flow
   - risks
3. Use that as your README / submission writeup.
4. Do not fill the full two-week production plan. Skip it.

### Hackathon rules

- Do not run `/deep-dive`.
- Do not fill the full business context.
- Do not run doc-sync after every edit. Use it at 3–4 milestones.
- Keep the stop hook on only if it is not slowing you down. If it is, remove the `Stop` hook from `.claude/settings.json`.
- Keep the prompt log. It is cheap and useful for submissions.

---

## Mode 3: Client work / handoff

Use the full kit. This is what it was built for.

1. Client runs `start here` and builds normally.
2. Agent fills the notebook prompt by prompt.
3. Agent runs `/doc-sync` after changes.
4. At handoff, `/handoff` produces the package.
5. You read `HANDOFF.md`, `CURRENT-STATE.md` and `SYSTEM-ARCHITECTURE.md` first.

Client rules:

- Do not let them paste secrets or customer data.
- Do not let the agent mark mocked features as real.
- Do not skip `CURRENT-STATE.md`.
- Run `node tools/check-docs.mjs` before accepting the handoff.

---

## How this fits with graft

They solve different layers:

| Question | Tool |
|---|---|
| Where is this code? | graft |
| Who calls this function? | graft |
| What breaks if I change this? | graft |
| Why does this feature exist? | this kit |
| What is the business rule? | this kit |
| What did I decide last week? | this kit |
| What is real vs fake? | this kit |
| What should the next person know? | this kit |

Use graft to move through the code. Use the kit to remember why the code exists.

At session start:

1. Read `docs/00-START-HERE.md` and `docs/state.json` (the hook does this).
2. Use graft to find the code for the task.
3. Use the relevant kit doc for the rule and the current state.
4. Build.
5. Update the kit doc.
6. Re-index graft if the code structure changed:
   ```bash
   graft build .
   ```

---

## What to skip

- Do not fill every `[UNKNOWN]`. Only the ones that affect the build.
- Do not write long prose in the notebook. Tables and bullets.
- Do not duplicate the same fact in 4 files. One home, link the rest.
- Do not use the full handoff template for a weekend project. Top sections only.
- Do not stack BMAD, Spec Kit, OpenSpec and this kit with duplicate PRDs. Pick one source of truth.
- Do not let the notebook drift. If you skip doc-sync, run `check-docs` before handoff.
- Do not paste passwords, API keys or customer data into chat.

---

## The minimum useful version

If you only do three things:

1. Keep `CURRENT-STATE.md` honest.
2. Keep `DECISIONS.md` current.
3. Run `/handoff` before you stop for a long time.

That alone prevents most of the "what was I doing and why" pain.
