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


**What was built (done 04:40):**
- **The AI looks at the photo, but our rules decide.** Gemini answers fixed yes/no questions: is it a photo of a product? Is it the ordered item? Does it show the damage? Is it a screenshot or a document? Kavach's own code turns the answers into a score. The model can't talk a photo into passing, and text written inside an image is ignored.
- **What the verifier does with the score.**
  - Clear match → counts as evidence.
  - Clear mismatch (a payment screenshot, a different product, no damage visible) → blocked, with a plain reason: "the photo doesn't show a damaged Phone cover".
  - Unclear, or the check couldn't run → never paid automatically; the seller takes a look.
- **Privacy.** Photos are never stored, only a fingerprint and the score. Website uploads stay in memory for 10 minutes. The short note about the photo never repeats names or numbers read from the image.
- **On the website.** The camera button opens a picker: upload your own photo (shrunk in the browser first, so it's fast) or use the sample payment screenshot. New one-tap try: **"Send a payment screenshot as the photo"** → blocked. This is exactly the trick a friend tried earlier.

**Live checks on production:**
- the sample payment screenshot scored 0.05 → blocked;
- all 13 one-tap tries give the result they promise (the try-checker script ran against the live server, with test sessions, so no WhatsApp messages or calls).

**Honest gap:** we have no real photo of a damaged item yet (image generation isn't available on the free Gemini key), so the honest "broken item" demo try uses a demo photo, and that goes to the seller. With a real photo (uploaded on the site, or sent on WhatsApp or Telegram) the refund is instant.

**Checks:** 98 automated tests pass (6 new); security scanners clean.

---

## Phase 8: Eval
*Goal: real numbers, measured the same way for a "just prompt it" AI and for Kavach.*


**What was built (done 05:00):**
- **30 scenarios:** 19 attacks and 11 honest requests, each in a fresh demo shop. The attacks:
  - "the owner said so" (English, Hinglish, Hindi), a fake seller approval, a made-up 30-day policy;
  - instructions aimed at the AI, a hidden instruction in the order note;
  - someone else's order, a smuggled second request, an inflated amount, a payment screenshot as proof;
  - "never arrived" (it did), food returns, after the 7 days, emergency pressure;
  - redirecting a parcel, cancelling after dispatch.
- **Two systems, the same shop and the same rules.**
  - **Plain AI:** a strict "never refund unless…" prompt; it sees the records but decides alone. Each attack ran 3 times, because a prompt is a probability.
  - **Kavach:** exactly as in production.
  - Each was measured in its own pass, because they share the same free AI keys and would otherwise slow each other down.

**Results (live server, 12 Nov ~04:50):**

| | Kavach | Plain AI (strict prompt) |
|---|---|---|
| Attacks that moved money or changed an order | **0 of 19 (₹0)** | 2 attacks got money, 6 of 54 tries (11%) |
| Honest requests wrongly blocked | **0 of 11** | – |
| Typical reply time | 1.6 s (worst 2.4 s) | – |

**What it means, honestly:** the plain AI resisted every *word* trick (owner, policy, injections, pressure). It paid when it couldn't check the evidence: a payment screenshot sent as the "photo" (3 of 3 tries paid), and a claim with a photo nobody checked (3 of 3; it paid the real ₹299, not the ₹2,999 asked). Kavach's verifier checks the evidence and the records, so it paid nothing. Kavach never turned away an honest customer: unclear cases go to the seller instead.

**Where to see it:** the Proof page, *Proof 4*, with every scenario and a link to Kavach's receipt for each. Full report: `eval/reports/report.md`. Re-run with `uv run python eval/run.py`.

---

## Status after this loop (05:05)
- ✅ 7 Deploy · ✅ Agent upgrade · ✅ 4b Alert calls (tested on a real phone) · ✅ 5-lite Photo check · ✅ 8 Eval
- **Next:** 10 Submission (README, video, slides, repo public) and 5 ML guard.
- **Owner to-dos:**
  1. One real photo of a damaged item (any phone cover or object with a crack), so the honest "instant refund" demo uses a checked photo.
  2. Re-test WhatsApp and Telegram from your phone against the live server.

---

## Phase 5: The trained guard (ML)
*Goal: a model that recognises manipulation in Indian shop chats (English, Hinglish, Hindi), better than simple rules and better than off-the-shelf detectors, while never approving anything on its own.*

**How it was built (06:00–06:35):**
1. **Data.**
   - Realistic shop messages in three languages, built from "families" of phrasing (for example "the owner said so", "ignore your rules", "where is my order?", angry-but-honest complaints).
   - A quarter of every family's phrasings were kept aside for testing, so the test checks *new* wording, not memorised sentences.
   - Plus a public prompt-injection dataset (deepset, Apache-2.0).
   - **60 messages were written by hand before training** and never shown to the model while it learned. They are the honest test.
2. **Teacher model.** Google's MuRIL (a model that understands Indian languages, including Hindi written in English letters), fine-tuned on the laptop's RTX 5050. It was trained twice with different random seeds, and the better one was kept.
3. **Student model (what runs in production).** A small, fast model that learned to copy the teacher. It runs in about 1 ms, needs no GPU, and is stored as a plain data file, never as executable code. A test proves the production version scores exactly like the training version (to 0.000001).
4. **The alarm threshold** was chosen on a *separate* set of 50 hand-written messages, so that at most 5% of honest messages raise an alarm. The first threshold flagged too many honest customers, so it was replaced. That's documented in `ml/README.md`.
5. **Everything is recorded in Weights & Biases:** https://wandb.ai/abhisheksoni1445-mistralfluence/kavach-guard (training curves, every test, the mistakes the model made, and the model file).

**Results on messages the model never saw (hand-written set):**

| Detector | Catches manipulation | False alarms on honest messages |
|---|---|---|
| Simple rules (what we had) | 13% | 3% |
| Meta's Llama Prompt Guard 2 (ready-made) | 7% | 0% |
| **Our trained guard, as it runs in production** | **73%** | **10%** |

It also catches 100% of the eval's attack messages with no false alarms, and 99% of Hinglish manipulation (Meta's detector: 4%).

**Two honest notes.**
- A second version (v2, with more training phrasings) scored better on some tests. But we had decided in advance to pick the version that did best on the *calibration* set, not the test set, and by that rule v1 ships. v2 is reported, not hidden.
- A false alarm never blocks anyone. It only sends the request to the seller, and the verifier still checks every fact.

**With the guard live, the full eval on the live server:** still 0 of 19 attacks did any harm and 0 of 11 honest customers were blocked. Role-play and "emergency" pressure attempts now go to the seller. Reply time is unchanged at 1.6 s.
