# Tailscale Device Watch

Get alerted when a specific Tailscale device comes back online — useful if a laptop or PC was stolen but is still enrolled on your tailnet.

## Features

- Detects **offline → online** reconnects via the Tailscale Devices API
- **Recovery intelligence** on alert — public endpoints, GeoIP city/region, Tailscale `ip:country`, and `tailscale ping` (watcher host on tailnet)
- Alerts via **Discord**, **email**, or **SMS** (any combination)
- Optional Tailscale **webhook receiver** for supplementary management events
- Runs as a Python process, **Docker** container, or **systemd** service

> **Note:** Tailscale webhooks do not include “device came online” events. Polling is the reliable detection method. See [docs/architecture.md](docs/architecture.md).

## Quick start

```bash
cd tailscale-device-watch
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — see docs/getting-started.md

python -m tailscale_device_watch once   # test
python -m tailscale_device_watch poll   # run continuously
```

Or with Docker:

```bash
docker compose up -d --build
```

## Documentation

Full documentation lives in **[docs/](docs/README.md)**:

| Guide                                                    | Description                        |
| -------------------------------------------------------- | ---------------------------------- |
| [Getting started](docs/getting-started.md)               | Install, configure, first poll     |
| [Configuration](docs/configuration.md)                   | Environment variables and CLI      |
| [Notifications](docs/notifications.md)                   | Discord, email, SMS setup          |
| [Deployment](docs/deployment.md)                         | Docker, systemd, hosting           |
| [Tailscale webhooks](docs/tailscale-webhooks.md)         | Optional webhook receiver          |
| [Stolen device playbook](docs/stolen-device-playbook.md) | Security steps before/after alerts |
| [Architecture](docs/architecture.md)                     | How detection works                |
| [Troubleshooting](docs/troubleshooting.md)               | Common problems                    |

## Commands

```bash
python -m tailscale_device_watch poll    # continuous polling (recommended)
python -m tailscale_device_watch once    # single check
python -m tailscale_device_watch serve   # webhook server only
python -m tailscale_device_watch both    # poll + webhook (Docker default)
```

## Minimum configuration

```env
TAILSCALE_API_KEY=tskey-api-...
TAILNET=example.com
WATCH_DEVICE=stolen-laptop-hostname
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

## License

MIT — use at your own risk; no warranty.
