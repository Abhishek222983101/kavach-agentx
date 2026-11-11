---
doc: trd
status: draft
last_updated: 2026-11-11
---

# Technical requirements (TRD)

Decisions and reasons live in `SYSTEM-ARCHITECTURE.md` §4–§6; this file states the technical requirements the code must meet.

## Platforms
- Customer: WhatsApp (Twilio sandbox), Telegram, mobile web chat. Seller: the same chat apps plus a mobile-first web console. Judge: phone + desktop browser.
- No native app (D-09).

## Frontend and hosting
- Next.js 16 + React 19 + TypeScript, Tailwind 4, shadcn/ui on Base UI, Motion, Number Flow, Sonner, react-isokit, next-themes (the Tessera stack, `UI-UX-BRIEF.md`). Deployed on Vercel.
- Routes: `/` landing (Tessera layout), `/console` judge page, `/arena`, `/seller`, `/results`, `/guide`, `/trace/[id]`. Live data over SSE (`/events/stream`).
- Must render at 360 px width without horizontal scroll.

## Backend and database
- Python 3.12, FastAPI, Pydantic v2, LangGraph + Postgres checkpointer, httpx, onnxruntime.
- Three processes in one container (Render free = one service), started by `honcho`: `api` (public), `executor` and `store` (localhost only).
- Postgres on Neon with roles `kavach_reader` and `kavach_writer`; append-only trigger on `audit_log`.

## Authentication and roles
| Actor | How identified | Can |
|---|---|---|
| Customer | WhatsApp/Telegram id → `customers.phone`/`tg_id`; unknown ids get a fresh demo customer with 3 orders | Ask, request returns/refunds for own orders |
| Seller | Configured `SELLER_WHATSAPP`, `SELLER_TELEGRAM_CHAT_ID`; console protected by `SELLER_CONSOLE_PIN` | Approve/reject/edit, kill switch, settings |
| Judge (public web) | Anonymous session cookie | Use web chat as a demo customer, arena, view console read-only; approve only in "demo seller" mode on their own session |
| Agent process | DB role `kavach_reader`, Store reader key | Read only |
| Executor | DB role `kavach_writer`, Store writer key, `VERDICT_SECRET` | Write with a valid token |

## External services
Twilio (WhatsApp, Voice), Telegram Bot API, SMTP, Gemini, Groq, W&B. Details and limits: ARCH §12.

## Security and privacy
Fake data only; signature checks on every webhook; no secrets in the repo; masked phone numbers in logs and UI; no real voice notes committed; Trail of Bits checks before deploy. Threat table: ARCH §13.

## Performance and reliability targets
| Target | Value |
|---|---|
| Text reply, typical | ≤ 4 s |
| Voice reply, typical | ≤ 6 s |
| Event to screen | ≤ 1 s |
| Guard inference (served student) | p95 ≤ 20 ms on CPU `[ASSUMED]` |
| Uptime 12–16 Nov | health check every 5 min, alert on failure |
| LLM calls per message | ≤ 4 |
| Duplicate webhook | processed once |
| Crash mid-approval | resumes from checkpoint |

## Environments and delivery
- `local`: `just up` (Compose), Next.js dev server (`pnpm dev`), Telegram polling, ngrok-free alternative `cloudflared` for webhooks.
- `prod`: Vercel (web) + Render free (backend) + Neon (DB) + GitHub Actions keepalive, deployed from tag `v1.0-agentx`. Backend memory budget < 450 MB.
- CI-lite: `just test` before each commit; Playwright smoke before deploy.

## Key technical tradeoffs
Python-only backend (speed of building over raw speed); LangGraph only for the spine; Postgres over SQLite (roles, persistence); SSE over WebSockets; ONNX in-process over a model server; templates for facts over free LLM text.
