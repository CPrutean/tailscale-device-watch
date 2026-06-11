from __future__ import annotations

import os
import re
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
    discord_webhook_urls: tuple[str, ...]
    smtp_host: str | None
    smtp_port: int
    smtp_user: str | None
    smtp_password: str | None
    smtp_from: str | None
    alert_email_to: tuple[str, ...]
    twilio_account_sid: str | None
    twilio_auth_token: str | None
    twilio_from_number: str | None
    alert_sms_to: tuple[str, ...]
    tailscale_webhook_secret: str | None
    webhook_port: int
    tailscale_ping_enabled: bool
    tailscale_ping_count: int
    tailscale_ping_timeout_seconds: float
    tailscale_cli: str
    geoip_enabled: bool
    env_file: Path | None

    @property
    def has_notifier(self) -> bool:
        return bool(
            self.discord_webhook_urls
            or (self.smtp_host and self.alert_email_to)
            or (self.twilio_account_sid and self.twilio_auth_token and self.alert_sms_to)
        )


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    return normalized in {"1", "true", "yes", "on"}


def _env_list(*names: str) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for name in names:
        raw = os.getenv(name)
        if not raw:
            continue
        for part in re.split(r"[\n,;]+", raw):
            item = part.strip()
            if item and item not in seen:
                seen.add(item)
                values.append(item)
    return tuple(values)


def _resolve_env_path(env_file: str | None) -> Path | None:
    candidate = Path(env_file or ".env")
    if candidate.is_file():
        return candidate.resolve()
    return None


def load_config(env_file: str | None = None) -> Config:
    resolved_env = _resolve_env_path(env_file)
    if resolved_env is not None:
        load_dotenv(resolved_env, override=True)
    elif env_file and env_file != ".env":
        raise ValueError(f"Environment file not found: {env_file}")

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

    state_file = Path(os.getenv("STATE_FILE", "state.json"))
    if not state_file.is_absolute():
        state_file = Path.cwd() / state_file

    return Config(
        tailscale_api_key=api_key,
        tailnet=tailnet,
        watch_device=watch_device,
        poll_interval_seconds=max(10, int(os.getenv("POLL_INTERVAL_SECONDS", "30"))),
        state_file=state_file,
        discord_webhook_urls=_env_list("DISCORD_WEBHOOK_URL", "DISCORD_WEBHOOK_URLS"),
        smtp_host=_optional(os.getenv("SMTP_HOST")),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=_optional(os.getenv("SMTP_USER")),
        smtp_password=_optional(os.getenv("SMTP_PASSWORD")),
        smtp_from=_optional(os.getenv("SMTP_FROM")),
        alert_email_to=_env_list("ALERT_EMAIL_TO", "ALERT_EMAIL_TO_LIST"),
        twilio_account_sid=_optional(os.getenv("TWILIO_ACCOUNT_SID")),
        twilio_auth_token=_optional(os.getenv("TWILIO_AUTH_TOKEN")),
        twilio_from_number=_optional(os.getenv("TWILIO_FROM_NUMBER")),
        alert_sms_to=_env_list("ALERT_SMS_TO", "ALERT_SMS_TO_LIST"),
        tailscale_webhook_secret=_optional(os.getenv("TAILSCALE_WEBHOOK_SECRET")),
        webhook_port=int(os.getenv("WEBHOOK_PORT", "8080")),
        tailscale_ping_enabled=_bool(os.getenv("TAILSCALE_PING_ENABLED"), default=True),
        tailscale_ping_count=max(1, int(os.getenv("TAILSCALE_PING_COUNT", "3"))),
        tailscale_ping_timeout_seconds=float(
            os.getenv("TAILSCALE_PING_TIMEOUT_SECONDS", "5")
        ),
        tailscale_cli=os.getenv("TAILSCALE_CLI", "tailscale").strip() or "tailscale",
        geoip_enabled=_bool(os.getenv("GEOIP_ENABLED"), default=True),
        env_file=resolved_env,
    )
