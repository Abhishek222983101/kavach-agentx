"""Email copies to the seller (escalations, alerts) over SMTP. Never blocks or breaks a conversation."""
from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

log = logging.getLogger("kavach.email")


class Mailer:
    def __init__(self, host: str, user: str, password: str, to: str, port: int = 587):
        self.host, self.user, self.password, self.to, self.port = host, user, password, to, port

    async def send(self, subject: str, body: str) -> bool:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = f"Kavach <{self.user}>", self.to, subject[:150]
        msg.set_content(body[:5000])
        try:
            await aiosmtplib.send(msg, hostname=self.host, port=self.port, start_tls=True,
                                  username=self.user, password=self.password, timeout=15)
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("email failed: %s", type(e).__name__)
            return False
