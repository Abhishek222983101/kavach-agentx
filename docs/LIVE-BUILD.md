# Kavach: live build log

**What this is:** a plain-language diary of the build, updated after every step. Read it to know where the work is, what each piece does, and why it was built that way. No code knowledge needed. Newest entries are at the bottom of each phase.

**Started:** 12 Nov 2026, 04:00 IST · **Deadline:** 12 Nov, 10:00 IST

---

## The product in 30 seconds
Kavach is a customer-support agent for small online sellers in India. Customers write on WhatsApp, Telegram or the website in Hindi, Hinglish or English. The AI understands them and can look up orders, track parcels and read the shop's policy. **It can ask for a refund but can never pay one itself.** A separate checker (the "verifier") re-reads the real records and decides: do it, ask the seller, or block. If something risky happens, Kavach phones the seller.

## Where we are

| Phase | What it means | Status |
|---|---|---|
| 0–4, 6 | Foundation, store, verifier, agent, channels, website | ✅ done (11–12 Nov) |
| **7 Deploy** | Put it on the internet so judges can use it from their phones | ⏳ in progress |
| Agent upgrade | Let the AI choose which records to read, handle two requests in one message, and ask when unsure | ⏳ |
| 4b Alert calls | Kavach phones the seller for high-risk events; "press 1 to approve" | ⏳ |
| 5-lite Photo check | AI vision checks that the "damaged item" photo really shows the item | ⏳ |
| 8 Eval | The same attacks against a plain AI vs Kavach, with real numbers | ⏳ |
| 5 ML guard | Trained scam/injection detector (GPU) | after the above |

## Ground rules for the build
- Nothing ships until its tests pass and a security check is done.
- Automated tests never send real WhatsApp messages or real calls (their sessions are named `test_`, `verify_` or `eval_`).
- Budgets: WhatsApp ≈ 280 messages total; phone calls ≤ 10 real calls until 16 Nov (≈ $0.50).
- Secrets live only in `.env` and the hosting dashboards, never in code or docs.

---

## Phase 7: Deploy
*Goal: a judge opens one link on their phone and everything works, fast.*

(entries follow)

**7.1 Container (done 04:20).** The three backend services (store, verifier, chat API) are packed into one container. Only the chat API is reachable from the internet; the store and the verifier listen inside the container only. It runs as a normal user, not root, starts in 4 seconds and uses about 200 MB. Secrets are uploaded to Render as a private file, never put in the code.

**7.2 Live on the internet (done 04:30).**
- Website: https://kavach-agentx.vercel.app (Vercel). Almost every page is pre-built, so it loads instantly.
- Backend: https://kavach-agentx-api.onrender.com (Render, Singapore, the same region as the database). A full chat reply takes **1.4 seconds** from India (2–7 s from the laptop).
- Telegram now sends messages straight to the server (webhook, with a secret so nobody else can post to it). WhatsApp is checked every 3 seconds, so no Twilio console setting is needed. If the server was asleep, it looks back 10 minutes when it wakes.

**7.3 Security checks (passed).**
- Only our website may call the API from a browser.
- Fake Telegram or WhatsApp webhooks are refused.
- Seller actions need the PIN.
- Developer docs are hidden in production.
- No secret appears in the website's code.

**7.4 Staying awake (done).** The free server sleeps after 15 quiet minutes. A GitHub job pings it every 10 minutes until 16 Nov, so judges never wait for a cold start.

**Still to verify by hand:** send a WhatsApp message and a Telegram message from a phone (owner).

---

## Agent upgrade
*Goal: show real agent behaviour (choosing what to look up, handling two requests in one message, asking when unsure), while the money rules stay exactly as strict.*

