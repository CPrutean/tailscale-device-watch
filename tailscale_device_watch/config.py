from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    tailscale_api_key: str
    tailnet: str
    watch_device: str
    poll_interval_seconds: int
    state_file: Path
    discord_webhook_url: str | None
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    smtp_from: str | None
    alert_email_to: str | None
    twilio_account_sid: str | None
    twilio_auth_token: str | None
    twilio_from_number: str | None
    alert_sms_to: str | None
    tailscale_webhook_secret: str | None
    webhook_port: int

    @property
    def has_notifier(self) -> bool:
        return bool(
            self.discord_webhook_url
            or (self.smtp_host and self.alert_email_to)
            or (self.twilio_account_sid and self.alert_sms_to)
        )


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def load_config(env_file: str | None = None) -> Config:
    load_dotenv(env_file)

    api_key = os.getenv("TAILSCALE_API_KEY", "").strip()
    tailnet = os.getenv("TAILNET", "").strip()
    watch_device = os.getenv("WATCH_DEVICE", "").strip()

    missing = [
        name
        for name, value in [
            ("TAILSCALE_API_KEY", api_key),
            ("TAILNET", tailnet),
            ("WATCH_DEVICE", watch_device),
        ]
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        tailscale_api_key=api_key,
        tailnet=tailnet,
        watch_device=watch_device,
        poll_interval_seconds=max(10, int(os.getenv("POLL_INTERVAL_SECONDS", "30"))),
        state_file=Path(os.getenv("STATE_FILE", "state.json")),
        discord_webhook_url=_optional(os.getenv("DISCORD_WEBHOOK_URL")),
        smtp_host=_optional(os.getenv("SMTP_HOST")),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=_optional(os.getenv("SMTP_USER")),
        smtp_password=_optional(os.getenv("SMTP_PASSWORD")),
        smtp_from=_optional(os.getenv("SMTP_FROM")),
        alert_email_to=_optional(os.getenv("ALERT_EMAIL_TO")),
        twilio_account_sid=_optional(os.getenv("TWILIO_ACCOUNT_SID")),
        twilio_auth_token=_optional(os.getenv("TWILIO_AUTH_TOKEN")),
        twilio_from_number=_optional(os.getenv("TWILIO_FROM_NUMBER")),
        alert_sms_to=_optional(os.getenv("ALERT_SMS_TO")),
        tailscale_webhook_secret=_optional(os.getenv("TAILSCALE_WEBHOOK_SECRET")),
        webhook_port=int(os.getenv("WEBHOOK_PORT", "8080")),
    )
