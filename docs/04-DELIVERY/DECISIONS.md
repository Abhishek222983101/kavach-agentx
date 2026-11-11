---
doc: decisions
status: active
last_updated: 2026-11-11
---

# Decisions

The full table with reasons is in `../03-SYSTEM/SYSTEM-ARCHITECTURE.md` §4. Summary:

| ID | Date | Decision | Decided by |
|---|---|---|---|
| D-01 | 2026-11-11 | WhatsApp primary (Twilio sandbox); Telegram and web chat co-equal fallbacks | Owner (WhatsApp + Telegram both) + agent |
| D-02 | 2026-11-11 | Python backend, Next.js 16 frontend (Tessera stack); no Rust/Go | Agent recommendation, owner asked for "fastest"; open to challenge |
| D-03 | 2026-11-11 | LangGraph spine only; no multi-agent swarm; no n8n | Agent |
| D-04 | 2026-11-11 | Agent, executor and store run as separate processes with separate DB roles | Agent |
| D-05 | 2026-11-11 | Postgres on Neon (local: Compose) | Agent, after owner chose free hosting |
| D-06 | 2026-11-11 | ML: trained guard + online seller preference; reused photo/ASR models; ML never overrides BLOCK | Owner wants real ML; agent scoped it |
| D-07 | 2026-11-11 | Gemini → Groq; Claude only if a working key/gateway appears | Owner (free tier only) |
| D-08 | 2026-11-11 | Vercel (web) + Render free (backend, 3 processes in 1 container) + Neon + GitHub Actions keepalive | Owner: "we use vercel, no pay" |
| D-09 | 2026-11-11 | No native app; WhatsApp + mobile web console | Agent; owner had asked |
| D-10 | 2026-11-11 | Fresh repo, all commits inside the window; reusing our own earlier code allowed | Owner (mentors confirmed) |
| D-11 | 2026-11-11 | Four core docs, not twelve | Agent (time) |
| D-12 | 2026-11-11 | Serve a distilled student guard (fits 512 MB); report teacher + student | Agent |
| D-13 | 2026-11-11 | UI = Tessera landing and design system + ETHGlobal light/dark toggle | Owner |
| D-14 | 2026-11-11 | Twilio = Voight's account only; cost caps: sandbox WhatsApp only (no paid sender), outbound replies only inside the 24 h window, per-user 15 msgs/day, global 300 outbound/day, alert calls dry-run by default and ≤ 3/day to the one verified number, 35 s limit; daily spend check in the console | Owner: "cost properly optimised", don't touch lynky |
| D-15 | 2026-11-11 | Verifier, router, token signing and executor live together in one **trust service** process; the api/agent process only proposes and holds no secret | Agent (Phase 2): keeps VERDICT_SECRET out of the agent process |
| D-16 | 2026-11-11 | Render service must be in **Singapore** (same region as Neon); verify measured ~1 s warm from India vs DB, dominated by round trips | Agent (Phase 2 measurement) |
| D-17 | 2026-11-11 | Every new chat identity gets its own demo customer with fresh scenario orders dated from first contact (per-day cap) | Agent: demo data otherwise ages and testers collide |
| D-18 | 2026-11-11 | Facts in replies come from templates (EN/Hinglish/Hindi); the LLM only understands and plans; typed order ids and named items override the LLM's order choice | Agent: a live run showed the LLM can pick the wrong order |
