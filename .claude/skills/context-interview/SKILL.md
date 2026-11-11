---
name: context-interview
description: Use before building any new feature, workflow, screen, integration, role, rule, report, automation, or change to existing behaviour. Asks the owner a small number of plain-language questions, records the answers in the notebook, and reads the requirement back before code is written.
---

# Context interview

Goal: understand the request well enough to build it correctly, and leave a trace of what was decided.

Ask **at most 3 questions per message**. Never ask the owner to write a spec. Never ask for code details.

## 1. The seven core questions

Ask these one or two at a time:

1. **Who does this, and who is not allowed to?**
2. **What triggers it? What happens right before and right after?**
3. **Walk me through the happiest path, step by step.**
4. **What information is needed at each step? Where does it come from?**
5. **What goes wrong most often, and what should happen then?**
6. **What is the output, and who sees it?**
7. **How often, how many, and how fast does it need to be?**

## 2. Depth ladder

After the happy path, ask at least four of these:

- **Last Tuesday:** "Show me a real example from last week — who, what, how long, what went wrong."
- **Who is not allowed:** "Who must never be able to do this?"
- **Offline / busy:** "What happens if the internet drops, the person is on leave, or it is the busiest day of the month?"
- **Bad data:** "What if the data is missing, wrong, or duplicated?"
- **Mistakes:** "Can they undo it? Who approves a correction? What is the audit trail?"
- **Exceptions:** "What is the once-a-month exception that breaks the normal flow?"
- **History:** "Why is it done this way? Is that a rule, a habit, or a workaround?"
- **Cost:** "What does a mistake cost — money, time, customer trust, legal risk?"
- **Old system:** "What did the old tool do? What did you hate about it? What must not change?"

Stop when the answer stops changing. Do not ask all of them mechanically.

## 3. Read it back before coding

Write the **intake card** below, then show the owner a 5-bullet summary and ask: **"Did I get this right?"**

```text
Feature:
Actor:
Trigger:
Happy path:
Data in:
Data out:
Rules:
Exceptions:
Who can see / do:
Frequency and volume:
Success:
Out of scope:
Open questions:
```

If they say yes, continue. If they correct you, update the card and read it back again.

## 4. Record it

Before writing code, update:

- `docs/02-PRODUCT/PRD.md` — user story, requirement ID, EARS acceptance criteria
- `docs/02-PRODUCT/WORKFLOWS.md` — workflow or change to an existing workflow
- `docs/01-BUSINESS/DEEP-CONTEXT.md` — the reasoning, real example, exceptions
- `docs/04-DELIVERY/DECISIONS.md` — any non-obvious choice
- `docs/04-DELIVERY/SCENARIOS.md` — the what-if cases discussed
- `docs/04-DELIVERY/OPEN-QUESTIONS.md` — anything they could not answer
- `docs/04-DELIVERY/BUILD-PLAN.md` — the task and its finish line

Use the truth labels. Record the owner's words, then your interpretation.

## 5. When the owner is vague

| They say | Ask |
|---|---|
| "Make it simple" | "Who is the simplest user, and what should they see on the first screen?" |
| "Make it fast" | "What action is too slow today? How long does it take now, and what is acceptable?" |
| "Like the old one" | "Which part of the old one — the layout, the steps, the data, the feel?" |
| "Just make it work" | "What is the first real example we can test it with?" |
| "You decide" | "I will pick a default and mark it as an assumption. Here are two options; which is closer?" |
| "Everyone should see it" | "Who should *not* see it? That is usually the harder rule." |

## 6. When the owner says "just build it"

Build the smallest reasonable version. Then:

- list every `[ASSUMED]` choice in the reply
- add each one to `OPEN-QUESTIONS.md` under **Assumptions to confirm**
- ask the owner to confirm or correct them before the next feature

## 7. After the build

Run the `doc-sync` skill. Do not leave the notebook describing the old behaviour.

## Rules

- One topic at a time. Short messages.
- Ask for examples, not opinions.
- Never invent a rule, number, name or integration.
- Never ask for passwords, API keys or customer personal data.
- If the request is small and obvious, ask fewer questions. The goal is correctness, not ceremony.
- If the request is large, split it. Interview one workflow at a time.
