---
doc: scenarios
status: draft
last_updated: 2026-11-11
---

# What-if scenarios

| # | What if… | Expected behaviour | Test |
|---|---|---|---|
| S-01 | The courier API returns 500 | Retry twice, then escalate with a summary | AT-03, chaos |
| S-02 | Twilio sends the same webhook twice | One reply, one action | AT-15 |
| S-03 | The server dies while waiting for approval | Restart resumes from the checkpoint | AT-14 |
| S-04 | Gemini quota runs out | Groq takes over; if all fail, safe mode (tracking only, rest to seller) | AT-16 |
| S-05 | A judge floods the bot | Per-user cap (15/day), polite refusal | AT-17 |
| S-06 | Twilio trial messages run out | Telegram + web keep working; banner on console | manual |
| S-07 | Seller's WhatsApp window is closed | Approval goes to Telegram + console; WA card skipped | manual |
| S-08 | The agent invents a policy | Quote-or-fail blocks it | AT-04, AT-10 |
| S-09 | The agent "forgets" to include a claim | Required-claims rule blocks it | AT-13 |
| S-10 | Someone edits the amount after approval | Args hash mismatch, executor refuses | AT-02, AT-08 |
| S-11 | The guard model is down or slow | Router runs without it (rules + verifier); flag in X-ray | unit |
| S-12 | Guard wrongly flags a legit angry customer | It can only escalate; seller approves; precedent recorded | AT-18 |
| S-13 | Audit row tampered | Chain verify fails, console shows the broken row | AT-12 |
| S-14 | VPS reboots | Compose restart policy; Postgres volume persists; uptime alert | manual |
| S-15 | The alert call triggers repeatedly | Daily cap 3, dry-run default, fixed number only | unit |
