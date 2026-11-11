# Kavach in plain words (read this first)

**Last updated:** 11 Nov 2026, night. **For:** the team, before and during the build.

## The idea in one paragraph
A small online seller gets flooded with "where is my order", "return this", "refund me". Kavach is an AI agent that answers these on WhatsApp (and Telegram and a web chat) in Hindi, Hinglish or English. The twist: the agent is allowed to **look things up** but not to **change** anything by itself. Before any refund, return, cancellation or address change, a separate **checker** (the verifier) re-reads the real records and checks every fact the agent relied on. Small, clean actions go through automatically. Bigger ones go to the seller's phone for one tap. Anything that doesn't match the records is blocked, and the attempt is logged.

## Why this wins points (mapped to the judging)
- **Impact (25%):** a real Indian small-business pain, plus refund fraud.
- **Agent design (25%):** the agent plans and calls real tools; memory of the chat, the customer and the seller's past decisions; a clean separation between "think", "check" and "act".
- **Working demo (20%):** judges message it from their own phones; a chaos switch shows it surviving failures; measured results.
- **Innovation (15%):** required evidence for every action; a trained Hinglish manipulation guard; a limit that learns the seller's comfort; an attack arena.
- **Presentation (15%):** a live screen where every step lights up.

## The five pieces you must understand
1. **The agent** (LangGraph). Reads the message, looks up the order, decides what to do, and writes a *proposal* ("refund ₹1,299 on order 1042, because: it's the customer's order, it was delivered 3 days ago, the policy says 7 days, here's the exact clause").
2. **The verifier.** Throws away what the agent *said* and checks the records itself. It also insists on a fixed list of facts for each kind of action, so the agent can't skip one. Output: ALLOW, ESCALATE or BLOCK.
3. **The executor.** A separate program, the only one with permission to write. It runs an action only with a signed approval for those exact details. Change ₹500 to ₹5,000 and the signature no longer matches.
4. **The log.** Every step is chained together like a receipt book; editing an old row breaks the chain and the check catches it.
5. **The ML.** (a) A model *we train tonight* that spots manipulation in Hinglish ("owner ne bola", "ignore your rules", "review dunga"), which can only make Kavach more careful; (b) a small model that learns from the seller's approve/reject taps and *suggests* a better auto-limit. Optional extras: voice-note transcription and a fake/reused photo check.

## How a message flows
Customer message → (voice note transcribed) → manipulation score → agent looks up order/courier/policy → proposal → verifier checks → ALLOW (runs) / ESCALATE (seller taps approve) / BLOCK (customer told why) → reply in the customer's language, facts filled from the records → everything logged and shown live.

## What the judge sees
One page: chat on the left, the pipeline lighting up in the middle, counters on the right (₹ refunded correctly, attacks blocked, ₹ protected). Buttons: "Where's my order?", "Get a refund", "Try to scam it". A QR code to message the bot from their own WhatsApp. An arena where a plain agent and Kavach face the same scams side by side. A results page with the numbers and the training runs.

## The code that matters most
`backend/kavach/verifier/` (the rules that protect money), `backend/kavach/executor/` (signed, single-use, idempotent writes), `backend/kavach/agent/graph.py` (the flow), `ml/` (the guard training and its report). If time runs out, these four are what must work.

## Honest limits to say out loud
The store is a mock (allowed and required by the rules). WhatsApp runs on Twilio's sandbox, so judges send a join message first. The guard is trained mostly on generated data; we test it on data from a different generator, on hand-written messages and on real attempts from the arena, and report what we get.

## Where things are
Architecture: `docs/03-SYSTEM/SYSTEM-ARCHITECTURE.md` · Build plan: `docs/04-DELIVERY/BUILD-PLAN.md` · Requirements: `docs/02-PRODUCT/PRD.md` · Decisions: `docs/04-DELIVERY/DECISIONS.md` · Open questions: `docs/04-DELIVERY/OPEN-QUESTIONS.md` · Diagram page: `docs/diagrams/architecture.html`.
