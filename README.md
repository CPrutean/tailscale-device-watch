# Tailscale Device Watch

Get alerted when a specific Tailscale device comes back online — useful if a laptop or PC was stolen but is still enrolled on your tailnet.

## Features

- Detects **offline → online** reconnects via the Tailscale Devices API
- **Recovery intelligence** on alert — public endpoints, GeoIP city/region, Tailscale `ip:country`, and `tailscale ping` (watcher host on tailnet)
- Alerts via **Discord**, **email**, or **SMS** — multiple recipients per channel
- Optional Tailscale **webhook receiver** for supplementary management events
- Runs as a Python process, **Docker** container, or **systemd** service

> **Note:** Tailscale webhooks do not include “device came online” events. Polling is the reliable detection method. See [docs/architecture.md](docs/architecture.md).

## Quick start (Python)

```bash
git clone https://github.com/CPrutean/tailscale-device-watch.git
cd tailscale-device-watch

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your Tailscale API key, tailnet, device, and notification settings

echo '{}' > state.json   # optional; created automatically on first poll

python -m tailscale_device_watch once   # single poll (test API key + config)
python -m tailscale_device_watch poll   # run continuously
```

## Quick start (Docker)

```bash
cp .env.example .env
# Edit .env — required: TAILSCALE_API_KEY, TAILNET, WATCH_DEVICE, plus at least one notifier

echo '{}' > state.json

docker compose up -d --build
docker compose logs -f watcher
```

Verify the service is up:

```bash
curl http://localhost:8080/health
# {"status":"ok"}
```

Docker runs **`both`** mode by default: background poller + webhook server on port `8080`.

> **Docker note:** The default image does not include the Tailscale CLI, so `tailscale ping` recovery intel is skipped inside the container. API polling, GeoIP, and notifications still work. For ping on alert, run natively on a tailnet node or use a custom image.

## Configuration

Copy [`.env.example`](.env.example) to `.env`. All settings are documented there.

**Required:**

```env
TAILSCALE_API_KEY=tskey-api-...   # API access token from admin console (NOT tskey-auth-)
TAILNET=example.com
WATCH_DEVICE=stolen-laptop-hostname
```

**Notifications** (enable any combination; multiple recipients supported):

```env
# Discord — comma-separate for multiple channels
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Email — comma-separate for multiple recipients (one email, all in To:)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_TO=you@gmail.com,partner@gmail.com

# SMS — comma-separate for multiple phone numbers
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
ALERT_SMS_TO=+1...,+1...
```

The CLI loads `.env` from the current working directory. Override with `--env-file`:

```bash
python -m tailscale_device_watch poll --env-file /path/to/.env
```

See [docs/configuration.md](docs/configuration.md) for every option.

## Commands

```bash
python -m tailscale_device_watch poll    # continuous polling (recommended)
python -m tailscale_device_watch once    # single check
python -m tailscale_device_watch serve   # webhook server only
python -m tailscale_device_watch both    # poll + webhook (Docker default)
```

## Verify it works

1. **Health check** (Docker / webhook modes):
   ```bash
   curl http://localhost:8080/health
   ```

2. **Config + API key** — run one poll; you should see a log line about the watched device (not a config error):
   ```bash
   python -m tailscale_device_watch once --env-file .env
   ```
   A `401 Unauthorized` means the API key is missing or invalid. A successful poll logs `Device … is online/offline (no alert)`.

3. **End-to-end alert test** — see [docs/getting-started.md](docs/getting-started.md#verify-notifications).

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

## License

MIT — use at your own risk; no warranty.
