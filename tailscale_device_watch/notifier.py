from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Iterable

import httpx

from .config import Config
from .recovery import RecoveryIntel
from .tailscale import Device

logger = logging.getLogger(__name__)


def build_alert_message(
    device: Device,
    reason: str,
    recovery: RecoveryIntel | None = None,
) -> tuple[str, str]:
    title = f"ALERT: {device.display_name} is back on Tailscale"
    lines = [
        reason,
        "",
        f"Device: {device.display_name}",
        f"Tailscale ID: {device.id}",
        f"OS: {device.os or 'unknown'}",
        f"Addresses: {', '.join(device.addresses) or 'none'}",
        f"Client version: {device.client_version or 'unknown'}",
    ]
    if recovery is not None:
        recovery_lines = recovery.format_lines()
        if recovery_lines:
            lines.extend(["", "Recovery intelligence:"])
            lines.extend(recovery_lines)
    elif device.endpoints:
        lines.append(f"Public endpoints: {', '.join(device.endpoints)}")
    if device.derp:
        lines.append(f"DERP relay: {device.derp}")
    lines.extend(
        [
            "",
            "Recommended actions:",
            "- Save this alert and any public IPs / map links for law enforcement.",
            "- Request ISP subscriber records for the public endpoint IPs.",
            "- Revoke or remove the device in the Tailscale admin console.",
            "- Do not ping or connect further if it may alert the thief.",
        ]
    )
    body = "\n".join(lines)
    return title, body


class Notifier:
    def __init__(self, config: Config) -> None:
        self._config = config

    def send_all(
        self,
        device: Device,
        reason: str,
        recovery: RecoveryIntel | None = None,
    ) -> list[str]:
        title, body = build_alert_message(device, reason, recovery)
        errors: list[str] = []

        for webhook_url in self._config.discord_webhook_urls:
            try:
                self._send_discord(title, body, device, recovery, webhook_url)
            except Exception as exc:  # noqa: BLE001 - surface all notifier failures
                errors.append(f"Discord ({webhook_url}): {exc}")

        if self._config.smtp_host and self._config.alert_email_to:
            try:
                self._send_email(title, body, self._config.alert_email_to)
            except Exception as exc:
                errors.append(f"Email: {exc}")

        if (
            self._config.twilio_account_sid
            and self._config.twilio_auth_token
            and self._config.twilio_from_number
            and self._config.alert_sms_to
        ):
            sms_text = f"{title}. {device.display_name}. Check email/Discord for details."
            for phone_number in self._config.alert_sms_to:
                try:
                    self._send_sms(sms_text, phone_number)
                except Exception as exc:
                    errors.append(f"SMS ({phone_number}): {exc}")

        if not self._config.has_notifier:
            raise RuntimeError("No notification channels configured")

        return errors

    def _send_discord(
        self,
        title: str,
        body: str,
        device: Device,
        recovery: RecoveryIntel | None = None,
        webhook_url: str | None = None,
    ) -> None:
        fields = [
            {"name": "Device", "value": device.display_name, "inline": True},
            {
                "name": "Tailscale IPs",
                "value": ", ".join(device.addresses) or "none",
                "inline": True,
            },
        ]
        if recovery is not None and recovery.posture_country:
            fields.append(
                {
                    "name": "Country (Tailscale)",
                    "value": recovery.posture_country,
                    "inline": True,
                }
            )
        if recovery is not None and recovery.geo_locations:
            fields.append(
                {
                    "name": "GeoIP",
                    "value": recovery.geo_locations[0].summary[:1024],
                    "inline": False,
                }
            )
        if recovery is not None and recovery.maps_url:
            fields.append(
                {
                    "name": "Map (approximate)",
                    "value": recovery.maps_url,
                    "inline": False,
                }
            )
        if recovery is not None and recovery.ping is not None:
            fields.append(
                {
                    "name": "Tailscale ping",
                    "value": recovery.ping.summary[:1024],
                    "inline": False,
                }
            )

        payload = {
            "content": "@everyone",
            "embeds": [
                {
                    "title": title,
                    "description": body[:4000],
                    "color": 0xFF0000,
                    "fields": fields,
                }
            ],
        }
        response = httpx.post(
            webhook_url or self._config.discord_webhook_urls[0],
            json={k: v for k, v in payload.items() if v is not None},
            timeout=30.0,
        )
        response.raise_for_status()

    def _send_email(self, subject: str, body: str, recipients: tuple[str, ...]) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._config.smtp_from or self._config.smtp_user
        message["To"] = ", ".join(recipients)
        message.set_content(body)

        with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port, timeout=30) as smtp:
            smtp.starttls()
            if self._config.smtp_user and self._config.smtp_password:
                smtp.login(self._config.smtp_user, self._config.smtp_password)
            smtp.send_message(message, to_addrs=list(recipients))

    def _send_sms(self, text: str, phone_number: str) -> None:
        url = (
            f"https://api.twilio.com/2010-04-01/Accounts/"
            f"{self._config.twilio_account_sid}/Messages.json"
        )
        response = httpx.post(
            url,
            auth=(self._config.twilio_account_sid, self._config.twilio_auth_token),
            data={
                "From": self._config.twilio_from_number,
                "To": phone_number,
                "Body": text[:1500],
            },
            timeout=30.0,
        )
        response.raise_for_status()


def log_notifier_errors(errors: Iterable[str]) -> None:
    for error in errors:
        logger.error("Notification failed: %s", error)
