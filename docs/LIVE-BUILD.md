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

**7.1 Container (done 04:05).** The three backend services (store, verifier, chat API) are packed into one container. Only the chat API is reachable from the internet; the store and the verifier listen inside the container only. It runs as a normal user, not root, starts in 4 seconds and uses about 200 MB. Secrets are uploaded to Render as a private file, never put in the code.

**7.2 Live on the internet (done 04:10).**
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


**What changed, in plain words (done 04:20):**
1. **The AI decides what to look up.** Before, every refund read the same four records. Now the AI picks (order, courier, policy, photos, refund history) and says why. A safety rule then adds anything the verifier will need, so the AI can't "forget" a check. The checks panel shows both: solid chips = the AI chose it, dashed = the safety rule added it.
2. **Two requests in one message.** "Where are my earphones, and the phone cover arrived broken, refund please" gets two answers. The refund still goes through the verifier on its own.
3. **Asks when unsure, with fixed options.** "I want a refund" with no reason gets "What happened? 1 Damaged 2 Wrong item 3 Never received 4 Changed my mind". These are fixed choices, so the AI never invents the question. Messages that look like scams (claims of authority, pressure, a stated amount) are **not** turned into a friendly question; they go straight to the verifier and are blocked on the record. A test caught this case.
4. **"Where is my refund?"** is answered from the refund records, with the date it should arrive.
5. **A greeting that's actually useful.** "Hi! … Good news: your Wireless earphones order is on the way", plus a short menu.
6. **Messages that read like a real brand's support line.** A bold outcome first, a short explanation, an italic "checked from records" line, Indian dates, and a reference number. On WhatsApp and Telegram a receipt link is added that anyone can open to see the checks.

**Bugs found and fixed while building this:** "refund 5000" was read as order number 5000; a photo sent with two requests was filed against both orders; dates were in UTC instead of Indian time.

**Checks:** 81 automated tests pass (7 new). Live test with the real AI: all 5 behaviours work. Security scanners are clean.

---

## Phase 4b: Seller alert calls
*Goal: when something risky happens, the seller's phone rings with a 30-second summary, and can approve or reject with a key press.*


**What was built (done 04:30):**
- **When Kavach rings the seller.** Three cases only:
  1. a customer sends instructions aimed at the AI ("ignore your rules…");
  2. one customer gets blocked 3 times within 10 minutes (someone probing);
  3. a big refund (₹2,000 or more), or one whose order record contains a hidden instruction, is still waiting after 90 seconds.
- **The call itself.** A calm 30-second Indian-English voice states the facts. For waiting refunds it says *"press 1 to approve, or 2 to reject"*. The key press goes through the same checked path as Telegram or the console: the verifier re-reads the records before any money moves.
- **Safety and cost.**
  - Only the seller's number from the server settings can ever be dialled.
  - At most 3 calls a day and 10 in total until 16 Nov (≈ ₹40), and at most one call per 30 minutes. Alerts during the cooldown are summed up in the next call.
  - Calls last at most 35 seconds.
  - Our own test runs can't ring anything, enforced twice.
- **Proof.**
  - Every call is written to the tamper-proof log.
  - The receipt shows "📞 Seller phoned".
  - The seller console shows calls today and in total.
  - The key-press webhook is checked twice: Twilio's signature, and our own code per approval.

**Live test on a real phone (04:27–04:30):** a ₹5,000 refund was sent to the seller → 90 s later the seller's phone rang → the seller pressed 1 → the verifier re-checked → refund paid. The audit log shows: `ESCALATE … over_hard_cap` → `approval: called` → `seller approved … via phone` → `ALLOW` → `₹5,000 refund … done`.

**Checks:** 92 automated tests pass (11 new, with a fake phone service); security scanners clean. 1 of 10 real calls used.

---

## Phase 5-lite: Photo check
*Goal: a "damaged item" photo must actually show the item and the damage. Today any image counts, even a payment screenshot.*

