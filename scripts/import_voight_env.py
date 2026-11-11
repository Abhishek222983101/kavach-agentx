"""Build kavach-agentx/.env from the credentials Voight already has in ~/.config/voight/*.env.

Copies values file-to-file and never prints them. Prints only which variable names were filled.
Re-running keeps any value already set in .env (so manual edits win).
"""
import os
import re
from pathlib import Path

SRC = Path.home() / ".config" / "voight"
DST = Path(__file__).resolve().parents[1] / ".env"

MAP = {  # kavach name: (voight file, voight name)
    "GROQ_API_KEYS": ("groq.env", "GROQ_API_KEY"),
    "TWILIO_ACCOUNT_SID": ("twilio.env", "TWILIO_ACCOUNT_SID"),
    "TWILIO_AUTH_TOKEN": ("twilio.env", "TWILIO_AUTH_TOKEN"),
    "TWILIO_WHATSAPP_FROM": ("twilio.env", "TWILIO_WHATSAPP_FROM"),
    "TWILIO_CALLER_ID": ("twilio.env", "TWILIO_CALLER_ID"),
    "ALERT_CALL_TO": ("twilio.env", "CALL_TO"),
    "TELEGRAM_BOT_TOKEN": ("telegram.env", "TELEGRAM_BOT_TOKEN"),
    "SELLER_TELEGRAM_CHAT_ID": ("telegram.env", "TELEGRAM_ALLOWED_CHATS"),
    "SMTP_USER": ("mail.env", "IMAP_USER"),
    "SMTP_PASSWORD": ("mail.env", "IMAP_APP_PASSWORD"),
    "WANDB_API_KEY": ("wandb.env", "WANDB_API_KEY"),
    "WANDB_ENTITY": ("wandb.env", "WANDB_ENTITY"),
}
DEFAULTS = {
    "GEMINI_API_KEYS": "", "GEMINI_MODEL": "gemini-3-flash-preview", "GROQ_MODEL": "openai/gpt-oss-120b",
    "ANTHROPIC_API_KEY": "", "ANTHROPIC_BASE_URL": "https://api.anthropic.com", "ANTHROPIC_MODEL": "claude-haiku-5-5",
    "SMTP_HOST": "smtp.gmail.com", "WANDB_PROJECT": "kavach-guard",
    "ALERT_CALLS_ENABLED": "0", "ALERT_CALL_DRY_RUN": "1", "ALERT_CALL_DAILY_CAP": "3",
    "TWILIO_SANDBOX_JOIN_CODE": "", "SELLER_WHATSAPP": "", "TELEGRAM_WEBHOOK_SECRET": "",
    "VERDICT_SECRET": "", "STORE_READER_KEY": "", "STORE_WRITER_KEY": "", "SELLER_CONSOLE_PIN": "",
    "PUBLIC_BASE_URL": "http://localhost:8000", "RATE_LIMIT_PER_USER_DAY": "15", "GLOBAL_DAILY_LLM_BUDGET": "800",
}


def parse(p: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.removeprefix("export ").split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> None:
    cur = parse(DST)
    filled, missing = [], []
    for k, (f, src) in MAP.items():
        if cur.get(k):
            continue
        v = parse(SRC / f).get(src, "")
        if v:
            cur[k] = v
            filled.append(k)
        else:
            missing.append(k)
    for k, v in DEFAULTS.items():
        cur.setdefault(k, v)
    for k in ("VERDICT_SECRET", "STORE_READER_KEY", "STORE_WRITER_KEY", "TELEGRAM_WEBHOOK_SECRET"):
        if not cur.get(k):
            cur[k] = os.urandom(24).hex()
    body = "\n".join(f"{k}={v}" for k, v in cur.items()) + "\n"
    DST.write_text(body)
    DST.chmod(0o600)
    print("filled from Voight:", ", ".join(filled) or "none")
    print("not found in Voight:", ", ".join(missing) or "none")
    print("still empty:", ", ".join(k for k, v in cur.items() if not v) or "none")
    if not re.search(r"^GEMINI_API_KEYS=.+", body, re.M):
        print("-> add GEMINI_API_KEYS (comma-separate keys from different Google projects)")


if __name__ == "__main__":
    main()
