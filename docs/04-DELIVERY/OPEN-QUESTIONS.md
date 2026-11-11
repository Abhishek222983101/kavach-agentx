---
doc: open-questions
status: active
last_updated: 2026-11-11
---

# Open questions

| ID | Question | Why it matters | Owner | Status |
|---|---|---|---|---|
| Q-01 | Is final judging only the repo/video/deck, or are there live demo slots? | Shapes how much to invest in live robustness vs video polish | Email contact@hack4hack.com | open |
| Q-02 | Is reusing our own earlier code allowed? | Rule says all building inside the window | Organisers | **answered 2026-11-11:** yes, mentors confirmed; commits must be inside the window `[CONFIRMED]` |
| Q-03 | Base URL for the `sk-ant-usr-` token that works in opencode? | Only way the Claude token is usable | Owner's friends | open |
| Q-04 | Hosting? | Always-on until 16 Nov | Owner | **answered 2026-11-11:** Vercel + Render free + Neon, no paid hosting (D-08) |
| Q-05 | Twilio price per WhatsApp message after the 100 free trial units? | Firm's $13.69 balance | Owner (Twilio console) | open |
| Q-06 | Does the Twilio sandbox render quick-reply buttons in-session? | Seller approval UX | Phase 4 test | open |
| Q-07 | Which Hindi TTS voice works in Twilio `<Say>` for the alert call? | Stretch feature | Phase 9 test | open |
| Q-08 | Does PyTorch see the RTX 5050? | ML phase depends on it | Phase 5.0 | **answered 2026-11-11:** yes, torch 2.11+cu128 (Voight venv) and 2.14+cu130 (Prahari venv) both report the RTX 5050 `[OBSERVED]` |
| Q-09 | Licence of `craftloop-ai/hinglish-prompt-guard` and its dataset? | Using it as base/baseline | Check model card | open |
| Q-10 | Who builds what? | Parallel work | Owner | **answered 2026-11-11:** the owner builds everything (solo lane + background GPU job) |
| Q-11 | Final headline: "Sounds genuine. / Refund blocked." or "Polite message. / Fake refund."? | Landing hero | Owner | open |
| Q-12 | Make the GitHub repo public now or at submission? | Judges need a public link | Owner | open (created private) |
| Q-13 | Which Twilio account? Voight's credentials are a **different, upgraded ("Full") account** from the `lynky-test` trial ($13.69) in the screenshot. Its sandbox join code in Voight's docs is `join silver-lion` | Who pays; sandbox join code; trial limits | Owner | open |
| Q-14 | Telegram: reuse `@Voight21_bot` (renamed display, but the username stays "Voight21") or create a Kavach bot? Setting our webhook stops Voight's local polling until `deleteWebhook` | Judges see the username in the link/QR | Owner | open (recommend new bot) |

## Contradictions
- 2026-11-11: owner earlier said "PS-06", then confirmed the deck says PS-04. **Current: PS-04.**
- 2026-11-11: agent earlier recommended Telegram as primary; owner wants WhatsApp primary and both. **Current: D-01.**
- 2026-11-11: agent earlier suggested a free Hugging Face Space for the model; research showed free CPU Docker Spaces now need a subscription. **Current: serve in the API process (D-06, ARCH §11.3).**
- 2026-11-11: agent proposed a "receipt book" UI; owner wants the exact Tessera landing and design system. **Current: D-13** (old brief archived in `99-ARCHIVE/`).
- 2026-11-11: agent proposed a paid VPS; owner chose free Vercel + Render. **Current: D-08.**

