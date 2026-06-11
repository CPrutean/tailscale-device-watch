from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .config import Config
from .notifier import Notifier, log_notifier_errors
from .recovery import gather_recovery_intel
from .tailscale import TailscaleClient

logger = logging.getLogger(__name__)

WATCHED_EVENT_TYPES = {
    "nodeCreated",
    "nodeApproved",
    "nodeKeyExpired",
    "nodeKeyExpiringInOneDay",
}


def verify_tailscale_signature(
    secret: str,
    body: bytes,
    signature_header: str | None,
    max_skew_seconds: int = 300,
) -> bool:
    if not signature_header:
        return False

    parts: dict[str, str] = {}
    for element in signature_header.split(","):
        if "=" not in element:
            continue
        key, value = element.split("=", 1)
        parts[key.strip()] = value.strip()

    timestamp = parts.get("t")
    signature = parts.get("v1")
    if not timestamp or not signature:
        return False

    try:
        event_time = int(timestamp)
    except ValueError:
        return False

    if abs(int(time.time()) - event_time) > max_skew_seconds:
        return False

    signed_payload = f"{timestamp}.".encode() + body
    expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def device_matches_event(device_query: str, event: dict[str, Any]) -> bool:
    query = device_query.lower()
    data = event.get("data") or {}
    haystack = " ".join(
        str(data.get(key, "")) for key in ("nodeID", "deviceName", "managedBy")
    ).lower()
    return query in haystack


def create_app(config: Config) -> FastAPI:
    app = FastAPI(title="Tailscale Device Watch")
    client = TailscaleClient(config.tailscale_api_key, config.tailnet)
    notifier = Notifier(config)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/tailscale-webhook")
    async def tailscale_webhook(
        request: Request,
        tailscale_webhook_signature: str | None = Header(default=None),
    ) -> JSONResponse:
        body = await request.body()

        if config.tailscale_webhook_secret:
            if not verify_tailscale_signature(
                config.tailscale_webhook_secret,
                body,
                tailscale_webhook_signature,
            ):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        try:
            events = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

        if not isinstance(events, list):
            raise HTTPException(status_code=400, detail="Expected JSON array of events")

        handled = 0
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            if event_type == "test":
                logger.info("Received Tailscale webhook test event")
                handled += 1
                continue

            if event_type not in WATCHED_EVENT_TYPES:
                continue

            if not device_matches_event(config.watch_device, event):
                continue

            data = event.get("data") or {}
            node_id = str(data.get("nodeID", ""))
            reason = (
                f"Tailscale webhook event `{event_type}` for watched device. "
                f"Message: {event.get('message', 'n/a')}"
            )

            device = None
            if node_id:
                try:
                    device = client.get_device(node_id)
                except Exception as exc:
                    logger.warning("Could not fetch device %s from API: %s", node_id, exc)

            if device is None:
                logger.warning("Webhook matched watched device but device details unavailable")
                continue

            recovery = gather_recovery_intel(client, device, config)
            errors = notifier.send_all(device, reason, recovery)
            log_notifier_errors(errors)
            handled += 1

        return JSONResponse({"ok": True, "handled": handled})

    return app
