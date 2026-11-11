---
doc: start-here
status: active
last_updated:
confidence: low
---

# Start here

> **What this is:** The front page of your project notebook. Your AI reads it first. The next team reads it at handoff.
> **How to fill:** The agent updates the status table and the "current focus" after every session.
> **Truth labels:** `[CONFIRMED]` owner said it · `[OBSERVED]` verified in code · `[ASSUMED]` agent inference · `[UNKNOWN]` no answer yet · `[DECISION]` recorded in `DECISIONS.md`

## What this folder is

A project notebook that your AI keeps up to date while you build. It records what you want, how the business works, what has been built, what is fake, and what is still unknown.

It makes your AI more useful today and gives the next person a clean brief when you hand over.

For a personal project, answer as yourself. "Business" means your project's domain and users.

## What to do

1. Open your project folder in Claude Code — the folder where `AGENTS.md`, `CLAUDE.md`, `.claude/`, `docs/` and `tools/` sit next to your code.
2. Type: `start here`
3. Answer the questions in your own words. Short answers are fine. If you do not know, say "I don't know."
4. Build normally. When you add something new, the AI asks a few questions first.
5. When you are done, or want to hand the project over, type: `/handoff`


## Document map (read in this order)
| Doc | What it answers |
|---|---|
| `OVERVIEW.md` | The idea in plain words, the five pieces, what to say out loud |
| `02-PRODUCT/PRD.md` | What the organisers asked for (word for word) and our requirements |
| `02-PRODUCT/APP-FLOW.md` | Every screen, journey and tap |
| `02-PRODUCT/WORKFLOWS.md` | Business workflows and permissions |
| `02-PRODUCT/UI-UX-BRIEF.md` | Visual direction, tokens, motion, copy |
| `03-SYSTEM/SYSTEM-ARCHITECTURE.md` | The master reference: diagrams, modules, ML, integrations, security, deployment, **build plan §20** |
| `03-SYSTEM/TRD.md` | Technical requirements and targets |
| `03-SYSTEM/DATA-MODEL.md` | Tables, roles, seed |
| `03-SYSTEM/INTEGRATIONS.md` | Services, owners, env vars |
| `04-DELIVERY/BUILD-PLAN.md` | Phase status tracker |
| `04-DELIVERY/SCENARIOS.md` | What-if cases and their tests |
| `04-DELIVERY/DECISIONS.md` · `OPEN-QUESTIONS.md` · `CURRENT-STATE.md` | Decisions, unknowns, honest status |
| `diagrams/architecture.html` | All diagrams rendered (open in a browser) |

## Current state

| | |
|---|---|
| Project | Kavach: verified-action support agent for small Indian sellers (AgentX PS-04) |
| One-line idea | WhatsApp support agent that checks every refund/return against the records before it acts |
| Stage | design done, build not started |
| Built so far | nothing yet |
| In progress | nothing yet |
| Top question | Q-04: hosting (hourly VPS?) |
| Notebook completeness | 0% |
| Handoff ready | no |
| Last updated | 2026-11-11 |

## Current focus

Submit a working, measured Kavach by 12 Nov 10:00 IST. Start with `docs/OVERVIEW.md`, then `docs/04-DELIVERY/BUILD-PLAN.md`.

## The next question

> Can we pay for an hourly VPS so the demo stays live until 16 Nov? (Q-04)

## Commands

| Type this | What happens |
|---|---|
| `start here` or `/start-here` | First-time interview: business, users, first workflow |
| `/deep-dive <topic>` | Digs into one workflow, department, role, rule or integration |
| `/doc-sync` | Brings the notebook back in line with the code after changes |
| `/arch-keeper` | Rebuilds the system architecture from the actual code |
| `/handoff` | Produces the handoff package and `HANDOFF.md` |
| `/status` | Shows what is built, what is next, and the top open questions |

## What the next person gets at handoff

- the full notebook (`docs/`)
- the raw prompt log
- a code snapshot, a git bundle, and the uncommitted diff
- package manifests and a file tree
- environment variable names (never the values)
- `HANDOFF.md`: what you wanted, what was built, what is real, what is broken, what is next

## Rules for you

- Do not paste passwords, API keys, or customer personal data into chat. If you do, rotate the key.
- Answer in your own words. The agent turns it into structure.
- If the agent gets something wrong, say so. Corrections are recorded, not overwritten.
- You can skip a question. It goes on the open-questions list.

## What this is not

This is not a production scaffold, a security review, or an engineering blueprint. It captures your intent and the current state.
