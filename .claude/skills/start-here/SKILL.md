---
name: start-here
description: First-run onboarding for this project. Use when the notebook is empty, when the owner says "start", "let's begin", "new project", "what is this", or when docs/state.json says onboarded is false. Interviews the owner in plain language and fills the business, product and first-workflow sections before any code is built.
---

# Start here

Your job: in 10–15 minutes, learn enough to build the first useful slice, and fill the notebook so nothing is lost.

Do **not** build code until the owner confirms the first workflow. Do **not** ask technical questions unless the owner brings them up. They are not a developer.

## 0. Read first

Read:

- `AGENTS.md`
- `docs/00-START-HERE.md`
- `docs/state.json`
- `docs/01-BUSINESS/BUSINESS-CONTEXT.md`
- `docs/02-PRODUCT/PRD.md`
- `docs/02-PRODUCT/WORKFLOWS.md`

If `docs/state.json` already says `"onboarded": true`, do not re-run onboarding. Say what is already known and ask what they want to work on.

## 1. The first five questions

Ask **one at a time**, in this order. Use the AskUserQuestion tool if available; otherwise ask in chat. Never send a wall of questions.

1. **"What is the business, in one sentence — like you would explain it to a friend?"**
2. **"Who will use this app every day, and what are they trying to get done?"**
3. **"What are they using today for that — a spreadsheet, WhatsApp, paper, another app?"**
4. **"What is the first thing you want the app to do, start to finish?"**
5. **"How will you know it worked? What number or outcome changes?"**

After each answer:

- Mirror it back in one sentence: "So the business is X, and the first user is Y — did I get that right?"
- Write it into the right doc with `[CONFIRMED]`.
- Ask the next question.

## 2. The second five questions

Only after the first five:

6. **"What should never happen? What would make you switch the app off?"**
7. **"What is the busiest time — day, week, month or festival — and what breaks then?"**
8. **"Who approves exceptions, refunds, overrides or extra spend?"**
9. **"What language do the daily users actually read and type in?"**
10. **"What phone or computer will the busiest user have? What is the internet like there?"**

## 3. Fill the notebook

Update these files as you go, not at the end:

| File | What to write |
|---|---|
| `docs/01-BUSINESS/BUSINESS-CONTEXT.md` | company, money, roles, day in the life, current tools, vocabulary, constraints, red lines |
| `docs/01-BUSINESS/DEEP-CONTEXT.md` | the first topic: the first workflow, in the owner's words + your interpretation |
| `docs/02-PRODUCT/PRD.md` | one-line idea, problem, users, goal, first user stories, first requirements |
| `docs/02-PRODUCT/WORKFLOWS.md` | the first workflow, happy path + exceptions |
| `docs/03-SYSTEM/SYSTEM-ARCHITECTURE.md` | only what you can verify: current tools, hosting, database, integrations. Leave the rest `[UNKNOWN]` |
| `docs/04-DELIVERY/OPEN-QUESTIONS.md` | everything they could not answer |
| `docs/04-DELIVERY/DECISIONS.md` | any choice made during onboarding |
| `docs/05-SESSIONS/SESSION-LOG.md` | the onboarding session |
| `docs/state.json` | project name, onboarded true, stage, current focus, next question |
| `docs/00-START-HERE.md` | the status table |

## 4. Propose the first slice

Before coding, say:

> "Smallest useful version: **[one workflow]**. It will do **[3 steps]**. It will not do **[out of scope]**. When it works, you will see **[observable result]**. Is that right?"

Wait for a yes. If they say "just build it", build the smallest version and mark every guess `[ASSUMED]`.

## 5. Start

Once confirmed:

- Check whether the project already has a scaffold (`package.json`, `app/`, `src/`, etc.).
- If not, propose the simplest stack that fits their tool and ask before installing anything.
- Write the first phase into `docs/04-DELIVERY/BUILD-PLAN.md`.
- Build one end-to-end slice, not a pile of half-features.
- After building, run the `doc-sync` skill.

## Rules

- One topic at a time. Short messages.
- No jargon. If you must use a technical word, explain it in one line.
- If they say "I don't know", write `[UNKNOWN]`, add a question to `OPEN-QUESTIONS.md`, and move on.
- If they contradict themselves, record both and ask which is current.
- Do not ask for passwords, API keys or customer personal data.
- Do not invent numbers, names or rules.
- The notebook can be partial. An honest partial notebook is better than a polished fiction.
