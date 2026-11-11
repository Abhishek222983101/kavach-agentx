---
doc: integrations
status: draft
last_updated: 2026-11-11
---

# Integrations

Details, limits and gotchas: `SYSTEM-ARCHITECTURE.md` §12. Credentials are imported from Voight's `~/.config/voight/*.env` by `scripts/import_voight_env.py` into `.env` (never committed).

| Service | Purpose | Account owner | Env vars | Status |
|---|---|---|---|---|
| Twilio (WhatsApp sandbox, Voice) | Primary channel; alert call | Owner's firm (trial, about $13.69) | `TWILIO_*`, `ALERT_CALL_*` | 🟡 credentials imported from Voight; sandbox join code and webhook not set yet. Uses the account **Auth Token** (Voight's setup), not a separate API key `[OBSERVED]` |
| Telegram Bot API | Channel + seller approvals | Team | `TELEGRAM_*` | 🟡 Voight's bot token imported; the bot is named for Voight, so create a new `@…kavach…bot` for branding (2 min) or accept the name |
| Gmail SMTP | Emails | Team | `SMTP_*` | 🟡 Voight's Gmail app password imported (same password works for SMTP) |
| Gemini | Main LLM | Owner (free tier, key from ETHGlobal `adx/.env`) | `GEMINI_*` | ✅ works on `gemini-3-flash-preview` (2.4 s); `gemini-2.5-flash` errored on this key `[OBSERVED 2026-11-11]` |
| Groq | LLM fallback, Whisper, Prompt Guard 2 | Owner (2 keys from `~/Documents/groq api key`) | `GROQ_*` | ✅ both keys work; real call 0.6 s on `openai/gpt-oss-120b` `[OBSERVED 2026-11-11]`. `llama-3.3-70b-versatile` is **no longer listed**. Available: gpt-oss-120b/20b, qwen3.8-27b, whisper-large-v3(-turbo), llama-prompt-guard-2-22m/86m |
| Anthropic | Optional | Owner's manager | `ANTHROPIC_*` | ❌ token rejected (Q-03) |
| Weights & Biases | Training evidence | Owner | `WANDB_*` | 🟡 key imported from Voight; project `kavach-guard` to be created on first run |
| Vercel | Web host | Owner (CLI logged in) | `NEXT_PUBLIC_API_URL` | ⬜ |
| Render | Backend host (free) | Owner (CLI logged in) | dashboard env | ⬜ |
| Neon | Postgres | Owner | `DATABASE_URL_READER`, `DATABASE_URL_WRITER` | ⬜ project not created |
| GitHub | Repo + keepalive Action | Abhishek222983101 (gh logged in) | — | 🟡 repo being created |
