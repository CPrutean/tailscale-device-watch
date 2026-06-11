from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from .config import Config
from .notifier import Notifier, log_notifier_errors
from .recovery import gather_recovery_intel
from .state import load_state, save_state
from .tailscale import Device, TailscaleClient

logger = logging.getLogger(__name__)


def _state_key(device: Device) -> str:
    return device.id


def _format_transition_reason(device: Device, previously_online: bool | None) -> str:
    if previously_online is None:
        return (
            f"Watched device `{device.display_name}` is currently online on Tailscale "
            "(first poll after watcher started)."
        )
    return (
        f"Watched device `{device.display_name}` transitioned from offline to online "
        f"at {datetime.now(UTC).isoformat()}."
    )


def poll_once(config: Config) -> bool:
    """Poll Tailscale once. Returns True if an alert was sent."""
    client = TailscaleClient(config.tailscale_api_key, config.tailnet)
    notifier = Notifier(config)
    state = load_state(config.state_file)

    try:
        device = client.find_watched_device(config.watch_device)
    except ValueError as exc:
        logger.error("%s", exc)
        raise

    if device is None:
        logger.warning(
            "No device matched WATCH_DEVICE=%r yet; will keep polling",
            config.watch_device,
        )
        return False

    key = _state_key(device)
    previously_online = state.get(key, {}).get("connected_to_control")
    currently_online = device.connected_to_control

    state[key] = {
        "connected_to_control": currently_online,
        "checked_at": datetime.now(UTC).isoformat(),
        "display_name": device.display_name,
        "addresses": device.addresses,
        "last_seen": device.last_seen,
    }
    save_state(config.state_file, state)

    went_online = currently_online and previously_online is False
    if not went_online:
        status = "online" if currently_online else "offline"
        logger.info("Device %s is %s (no alert)", device.display_name, status)
        return False

    reason = _format_transition_reason(device, previously_online)
    logger.warning("ALERT: %s", reason)
    recovery = gather_recovery_intel(client, device, config)
    errors = notifier.send_all(device, reason, recovery)
    log_notifier_errors(errors)
    return True


def poll_loop(config: Config) -> None:
    logger.info(
        "Polling every %ss for device matching %r on tailnet %r",
        config.poll_interval_seconds,
        config.watch_device,
        config.tailnet,
    )
    while True:
        try:
            poll_once(config)
        except Exception:
            logger.exception("Poll cycle failed")
        time.sleep(config.poll_interval_seconds)
