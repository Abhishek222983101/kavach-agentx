# Project Context Kit

**A project notebook your AI keeps up to date while you build.**

It does two things at once:

1. It gives your coding agent the business context it needs to build the right thing.
2. It leaves a clean, complete brief for the next person when you hand the project over.

You do not need to write documentation. You answer a few plain-language questions as you build. The agent writes the rest.

Works for personal projects, hackathons and client work. See `USAGE.md` for the three modes. For a personal project, treat "business" as the project's domain and users.

---

## Start in 60 seconds

1. Unzip the contents into your project root, so `AGENTS.md`, `CLAUDE.md`, `.claude/`, `docs/` and `tools/` sit next to your code. Or start a new project inside this folder.
2. Open that folder in Claude Code.
3. Type:

   ```text
   start here
   ```

4. Answer the questions in your own words. Short answers are fine. If you do not know, say "I don't know."
5. Build normally. When you add a new feature or workflow, the agent asks a few questions first.
6. When you are done, or want to hand the project over, type:

   ```text
   /handoff
   ```

---

## What it captures

| Area | What gets recorded |
|---|---|
| Business | What the company does, how it makes money, who works there, what a normal day looks like, what must never happen |
| Product | The PRD: users, user stories, requirements, acceptance criteria, scope, success measures |
| Workflows | Every end-to-end workflow: trigger, actors, steps, decisions, exceptions, volume, output |
| Deep context | The "why" behind the work: history, ideology, real examples, contradictions, unwritten rules |
| System | Architecture, components, data model, integrations, auth, deployment, security, known gaps |
| Delivery | Build plan, honest current state, what-if scenarios, decisions, open questions, risks |
| Sessions | Every raw prompt, a session summary, and an analysis of how the owner asks for things |
| Handoff | A one-page brief for the next person: what was wanted, what exists, what is real, what is fake, what is next |

---

## What the next person gets at handoff

`/handoff` produces a package with:

- the full notebook (`docs/`),
- the raw prompt log,
- a snapshot of the code (without `node_modules`, `.git`, or `.env`),
- a git bundle with the full history,
- the uncommitted diff,
- package manifests and a file tree,
- the names of required environment variables (never the values),
- `HANDOFF.md`, the one-page brief.

Send the package, or push the repo with the notebook included. That is the brief.

---

## Commands

| Type this | What happens |
|---|---|
| `start here` or `/start-here` | First-time interview: business, users, first workflow |
| `/deep-dive <topic>` | Digs into one workflow, department, role, rule or integration |
| `/doc-sync` | Brings the notebook back in line with the code after changes |
| `/arch-keeper` | Rebuilds the system architecture section from the actual code |
| `/handoff` | Produces the handoff package and `HANDOFF.md` |
| `/status` | Shows what is built, what is next, and the top open questions |

The agent can also trigger these automatically when the task matches.

---

## What this kit is not

This is **not** a production scaffold, a security review, or an engineering blueprint. It captures what you want and what currently exists. A production team does the production build, if you hand it over.

Keeping the notebook honest is the point. A feature is not "done" because a screen appears. The notebook records whether it is real, mocked, hard-coded, or broken.

---

## Rules

- **Do not paste passwords, API keys, or customer personal data into chat.** If you do, rotate the key.
- Answer in your own words. The agent turns it into structure.
- If the agent gets something wrong, say so. Corrections are recorded, not overwritten.
- If you skip a question, it goes on the open-questions list. It does not disappear.
- The agent may ask "why" more than once. That is deliberate. The reason behind a rule is usually the most valuable part.

---

## Already have a project?

Copy `AGENTS.md`, `CLAUDE.md`, `.claude/`, `docs/`, and `tools/` into the project root. If you already have a `README.md`, keep yours; rename this one to `KIT-README.md` or merge the useful sections. If you already have a `.claude/settings.json`, ask your agent:

```text
Merge this kit into my project. Do not overwrite my existing files.
Merge the hooks and env blocks in .claude/settings.json; keep my existing settings.
```

Works best with Claude Code. The docs and `AGENTS.md` also work with other coding agents.

---

## File map

```text
AGENTS.md                  the agent's operating rules
CLAUDE.md                  Claude Code entry point (imports AGENTS.md)
USAGE.md                   personal / hackathon / client modes
START-PROMPT.md            one-shot setup prompt for a new project
.claude/
  settings.json            hooks + safe permissions
  hooks/                   automatic prompt logging and doc-sync nudge
  skills/                  start-here, context-interview, deep-dive, doc-sync, arch-keeper, handoff
docs/
  00-START-HERE.md         the front page
  01-BUSINESS/             business context, deep context, domain checklist
  02-PRODUCT/              PRD + workflows
  03-SYSTEM/               architecture, data model, integrations
  04-DELIVERY/             build plan, current state, scenarios, decisions, open questions
  05-SESSIONS/             raw prompts, session log, prompting patterns
  06-HANDOFF/              handoff brief + changelog
  99-RAW/                  drop zone for screenshots, exports, links
tools/
  handoff.mjs              builds the handoff package
  check-docs.mjs           checks notebook completeness
```

---

*One notebook per project.*
