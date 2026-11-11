---
doc: raw-sources
status: reference
last_updated:
confidence: low
---

# Raw sources

Drop anything here that helps explain the project. The agent will read it, index it, and move the useful facts into the notebook.

## What to drop

- screenshots of the old spreadsheet, WhatsApp group, register or app
- exported spreadsheets (`.xlsx`, `.csv`)
- PDFs, invoices, forms, reports
- links to the old app, a Loom, a Figma, a reference product
- voice notes or transcripts
- email threads or WhatsApp exports
- photos of paper forms

## Rules

- **Never drop passwords, API keys, or real customer personal data.** If you must share a sample, redact it.
- Large files are fine locally, but tell the agent before adding them to git.
- Add a short note in `SOURCES.md` so the team knows what each file is and why it matters.

## Index

| File / link | What it is | Why it matters | Date added |
|---|---|---|---|
| [UNKNOWN] | | | |

## How the agent should handle this folder

1. List the files.
2. Read or view each one.
3. Extract the facts that affect the business, product, workflow, data or architecture.
4. Add them to the right notebook file with `[CONFIRMED]` or `[OBSERVED]`.
5. Add the source to the index above.
6. If a file contradicts the notebook, record the contradiction in `OPEN-QUESTIONS.md`.
7. Do not copy secrets or personal data into the notebook.
