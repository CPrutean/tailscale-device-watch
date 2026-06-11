from __future__ import annotations

import argparse
import logging
import sys
import threading

import uvicorn

from .config import load_config
from .poller import poll_loop, poll_once
from .webhook_server import create_app


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Watch a Tailscale device and alert when it comes back online.",
    )
    parser.add_argument(
        "command",
        choices=["poll", "once", "serve", "both"],
        help=(
            "poll: continuous API polling (recommended); "
            "once: single poll; "
            "serve: Tailscale webhook receiver only; "
            "both: webhook server + background poller"
        ),
    )
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)

    try:
        config = load_config(args.env_file)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if not config.has_notifier and args.command in {"poll", "once", "both"}:
        print(
            "Warning: no notification channels configured. "
            "Set DISCORD_WEBHOOK_URL, SMTP_*, or TWILIO_* in .env",
            file=sys.stderr,
        )

    if args.command == "once":
        poll_once(config)
        return 0

    if args.command == "poll":
        poll_loop(config)
        return 0

    if args.command == "serve":
        app = create_app(config)
        uvicorn.run(app, host="0.0.0.0", port=config.webhook_port, log_level="info")
        return 0

    if args.command == "both":
        thread = threading.Thread(target=poll_loop, args=(config,), daemon=True)
        thread.start()
        app = create_app(config)
        uvicorn.run(app, host="0.0.0.0", port=config.webhook_port, log_level="info")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
