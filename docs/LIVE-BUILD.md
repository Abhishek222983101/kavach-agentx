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
