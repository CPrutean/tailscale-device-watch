# Configuration reference

All settings are loaded from environment variables, typically via a `.env` file in the project root.

## Required

| Variable | Description | Example |
|----------|-------------|---------|
| `TAILSCALE_API_KEY` | Tailscale API access token | `tskey-api-abc123...` |
| `TAILNET` | Tailnet identifier | `example.com` |
| `WATCH_DEVICE` | Substring match for one device (hostname, name, node ID, or IP) | `janes-laptop` |

### `WATCH_DEVICE` matching rules

- Case-insensitive substring search across: node ID, device name, hostname, Tailscale IP addresses.
- Must match **exactly one** device. If multiple devices match, the watcher exits with an error — use a more specific value.
- Examples that work: `janes-laptop`, `nAbCdEf123`, `100.64.0.5`.

## Polling

| Variable | Default | Description |
|----------|---------|-------------|
| `POLL_INTERVAL_SECONDS` | `30` | Seconds between API polls. Minimum enforced: `10`. |
| `STATE_FILE` | `state.json` | Path to JSON file storing last-known online state per device. |

Shorter intervals detect reconnects faster but increase API usage. 30–60 seconds is a good balance for a stolen-device scenario.

## Notification channels

At least one channel should be configured for alerts to be useful. Multiple channels can be enabled at once — all configured channels fire on each alert.

| Variable | Required for | Description |
|----------|--------------|-------------|
| `DISCORD_WEBHOOK_URL` | Discord | Full Discord incoming webhook URL |
| `SMTP_HOST` | Email | SMTP server hostname |
| `SMTP_PORT` | Email | SMTP port (default `587`) |
| `SMTP_USER` | Email | SMTP username (if auth required) |
| `SMTP_PASSWORD` | Email | SMTP password or app password |
| `SMTP_FROM` | Email | From address (defaults to `SMTP_USER`) |
| `ALERT_EMAIL_TO` | Email | Recipient email address |
| `TWILIO_ACCOUNT_SID` | SMS | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | SMS | Twilio auth token |
| `TWILIO_FROM_NUMBER` | SMS | Twilio sender number (E.164) |
| `ALERT_SMS_TO` | SMS | Your phone number (E.164) |

See [Notifications](notifications.md) for provider-specific setup.

## Recovery intelligence

When an alert fires, the watcher gathers extra data to help locate the device. The watcher host should be enrolled on the same tailnet and have the `tailscale` CLI available.

| Variable | Default | Description |
|----------|---------|-------------|
| `TAILSCALE_PING_ENABLED` | `true` | Run `tailscale ping` against the watched device on alert |
| `TAILSCALE_PING_COUNT` | `3` | Number of ping packets to send |
| `TAILSCALE_PING_TIMEOUT_SECONDS` | `5` | Per-ping timeout passed to the Tailscale CLI |
| `TAILSCALE_CLI` | `tailscale` | Path to the Tailscale CLI binary |
| `GEOIP_ENABLED` | `true` | Look up city/region for public endpoint IPs via ip-api.com |

On alert, the watcher also fetches full device details (`fields=all`) and Tailscale posture attributes (including `ip:country` on Standard+ plans).

## Webhook server (optional)

Used only in `serve` or `both` modes.

| Variable | Default | Description |
|----------|---------|-------------|
| `TAILSCALE_WEBHOOK_SECRET` | _(empty)_ | Secret from Tailscale webhook endpoint. If set, incoming requests are signature-verified. |
| `WEBHOOK_PORT` | `8080` | HTTP port for the webhook server |

## CLI

```bash
python -m tailscale_device_watch [command] [options]
```

### Commands

| Command | Description |
|---------|-------------|
| `poll` | Poll continuously until stopped. **Recommended for stolen-device monitoring.** |
| `once` | Run a single poll cycle (testing). |
| `serve` | Start HTTP server for Tailscale webhooks only. No polling. |
| `both` | Poll in a background thread and run the webhook server. Docker default. |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--env-file PATH` | `.env` | Path to environment file |
| `-v`, `--verbose` | off | Enable debug logging |

### Examples

```bash
python -m tailscale_device_watch poll
python -m tailscale_device_watch once --env-file /etc/tailscale-watch.env
python -m tailscale_device_watch both -v
```

## State file format

`state.json` tracks the last known status per device ID:

```json
{
  "nAbCdEf123": {
    "connected_to_control": false,
    "checked_at": "2026-06-10T12:00:00+00:00",
    "display_name": "janes-laptop",
    "addresses": ["100.64.0.5"],
    "last_seen": "2026-06-09T08:00:00Z"
  }
}
```

Delete this file to reset baseline state (useful when testing).

## HTTP endpoints (webhook modes)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |
| `POST` | `/tailscale-webhook` | Tailscale webhook receiver |
