---
doc: submission
status: draft
last_updated: 2026-11-11
---

# Submission form (Hack4Hack portal), draft answers

The portal asks for: project name, theme, one-line pitch (≤ 140 chars), description, tech stack (comma separated), repository, live demo, demo video, pitch deck `[OBSERVED: portal screenshot 11 Nov 22:07]`. **There is exactly one video field**, so the launch film cannot be a separate submission item (see "Videos" below). Any teammate can edit until the deadline (12 Nov 10:00 IST).

| Field | Draft |
|---|---|
| Project name | Kavach |
| Theme | AI Agents · E-commerce support (PS-04) |
| One-line pitch | A WhatsApp support agent for small Indian sellers that checks every refund and return against the real records before it acts. *(124 chars)* |
| Description | Small sellers drown in "where is my order", return and refund messages, and an AI agent that can issue refunds can also be talked into the wrong one. Kavach answers customers on WhatsApp and Telegram in Hindi, Hinglish or English, looks up orders and courier status through real API calls on a mock store, and starts returns and refunds. Before any write, a separate verifier re-reads the records and checks every claim the action depends on (ownership, delivery, return window, amount, duplicates, and the exact policy clause, quoted). Small clean actions run; larger ones go to the seller's phone for one tap; anything that doesn't match is blocked. Only a separate executor holding a signed, single-use verdict can write, and every step lands in a hash-chained log. A Hinglish manipulation detector we trained (and distilled to run on a free server) adds caution but can never approve anything. Measured against a plain LLM agent on the same attacks: *[numbers from eval/reports, filled at the end]*. |
| Tech stack | Python, FastAPI, LangGraph, PostgreSQL, Neon, Next.js, React, Tailwind CSS, react-isokit, Twilio WhatsApp, Telegram Bot API, Gemini, Groq, PyTorch, Hugging Face Transformers, ONNX Runtime, scikit-learn, Weights & Biases, Render, Vercel |
| Repository | https://github.com/Abhishek222983101/kavach-agentx *(make public before submitting, Q-12)* |
| Live demo | https://*(vercel project)*.vercel.app |
| Demo video | YouTube (unlisted) or Google Drive link, ≤ 3:00, viewable by anyone |
| Pitch deck | Google Slides / PDF link, 6 slides, viewable by anyone |

## Videos
- **Demo video (the one that counts, ≤ 3:00):** screen recording + voice-over, following the storyboard in ARCH §20 Phase 10.3. It may open with a **10–15 s launch sting** made with Higgsfield, which counts toward the 3 minutes.
- **Launch film (optional, 30–45 s, Higgsfield):** linked from the README's first line, the landing page hero ("Watch the launch film") and deck slide 1. It never replaces the product demo.
- Upload both as unlisted YouTube videos; check they play in a private window.

## Final checklist (09:30–09:55)
- [ ] Repo public, README top shows live link, video, WhatsApp join QR, Telegram link, results table.
- [ ] Live demo loads on a phone on mobile data; WhatsApp and Telegram reply.
- [ ] Video and deck links open in a private window.
- [ ] Tag `v1.0-agentx` pushed.
- [ ] Submitted; screenshot saved to `docs/06-HANDOFF/`.
