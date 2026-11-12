---
doc: submission
status: draft
last_updated: 2026-11-12
---

# Submission form (Hack4Hack portal), answers

The portal asks for: project name, theme, one-line pitch (≤ 140 chars), description, tech stack (comma separated), repository, live demo, demo video, pitch deck `[OBSERVED: portal screenshot 11 Nov 22:07]`. **There is exactly one video field**, so any launch film cannot be a separate submission item (see "Videos"). Any teammate can edit until the deadline (12 Nov 10:00 IST).

## Fields

| Field | Answer |
|---|---|
| Project name | Kavach |
| Theme / track | AI Agents · E-commerce support (PS-04: autonomous support agent for online sellers) |
| One-line pitch (126 chars) | A support agent for Indian sellers that can ask for refunds but can't pay them. A separate checker re-reads the records first. |
| Tech stack | Python, FastAPI, LangGraph, PostgreSQL, Neon, Groq (gpt-oss-120b), Google Gemini, Twilio WhatsApp, Twilio Voice, Telegram Bot API, Gmail SMTP, Next.js 16, React, Tailwind CSS, Render, Vercel, GitHub Actions PyTorch, Hugging Face Transformers (MuRIL), scikit-learn, Weights & Biases |
| Repository | https://github.com/Abhishek222983101/kavach-agentx *(must be public before submitting, Q-12)* |
| Live demo | https://kavach-agentx.vercel.app |
| Demo video | TBD (YouTube unlisted or Google Drive, ≤ 3:00, viewable by anyone) |
| Pitch deck | https://kavach-agentx.vercel.app/deck.pdf (public PDF, 6 slides) |

Pitch character count: **126** (limit 140).

## Description (about 150 words)

Small online sellers lose hours to "where is my order?", return and refund messages. An AI agent can answer them, but an agent that can issue refunds can also be talked into the wrong one. Kavach answers customers on WhatsApp, Telegram and the web in Hindi, Hinglish or English. It looks up orders and courier status and asks for refunds, but it cannot pay one. A separate verifier re-reads the real records and checks every fact the action depends on, including the exact policy line and the photo. It then allows, asks the seller (by WhatsApp, Telegram, email or a phone call: "press 1 to approve"), or blocks. Only an executor holding a signed one-time slip can write, and every step goes into a hash-chained log. In our test of 19 attacks and 11 honest requests, Kavach paid ₹0 and blocked no honest customer. A plain strict-prompt AI paid on 6 of 54 attack tries. A guard model we trained (MuRIL teacher, distilled student, tracked in W&B) catches 73% of hand-written manipulation attempts, against 13% for rules and 7% for Meta's Prompt Guard 2.

## Key facts for the form notes

- Live product: web demo, Telegram bot, WhatsApp sandbox (send `join ask-contain` to +1 415 523 8886).
- Judges can test in 5 minutes with no setup: `docs/MANUAL-TESTING.md`, Part 1.
- The seller console PIN goes in the portal's notes field, not in any file in the repo.
- Honest limits: mock shop data, WhatsApp is the Twilio sandbox, free hosting.

## Videos

- **Demo video (the one that counts, ≤ 3:00):** screen recording plus voice-over, following `docs/06-HANDOFF/VIDEO-SCRIPT.md`.
- Upload as unlisted on YouTube (or Google Drive). Check it plays in a private window.
- An optional short launch film, if one exists, is linked from the README only. It never replaces the product demo.

## Final checklist (09:30-09:55)

- [ ] Repo public. README top shows live link, Telegram link, WhatsApp join text and the results table. Add the video link when ready.
- [x] ML results filled from `ml/reports/guard_eval.json` in README, DECK and this file.
- [ ] Live demo loads on a phone on mobile data. WhatsApp and Telegram reply.
- [ ] Video and deck links open in a private window.
- [ ] Tag `v1.0-agentx` pushed.
- [ ] Submitted. Screenshot saved to `docs/06-HANDOFF/`.
