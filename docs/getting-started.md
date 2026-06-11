# Getting started

This guide walks you through installing Tailscale Device Watch and receiving your first test alert.

## Prerequisites

- Python 3.11 or later (or Docker)
- A Tailscale account with **Owner**, **Admin**, **Network admin**, or **IT admin** access
- A [Tailscale API key](https://login.tailscale.com/admin/settings/keys)
- At least one notification channel (Discord is the fastest to set up)
- An always-on machine to run the watcher (home server, VPS, NAS, or another tailnet device)
- The watcher host enrolled on your tailnet with the `tailscale` CLI (for recovery intelligence on alert)

## Step 1: Identify the device to watch

1. Open [Admin → Machines](https://login.tailscale.com/admin/machines).
2. Find the stolen or target machine.
3. Note its **hostname** (e.g. `janes-laptop`) or **node ID** (e.g. `nAbCdEf123`).

You will use this value for `WATCH_DEVICE`. The matcher is a case-insensitive substring — it must match **exactly one** device in your tailnet.

## Step 2: Create a Tailscale API key

1. Go to [Admin → Settings → Keys](https://login.tailscale.com/admin/settings/keys).
2. Generate an API access token.
3. Copy the key (starts with `tskey-api-`).

Store this key securely. Anyone with it can read your tailnet device list via the API.

## Step 3: Install

```bash
cd tailscale-device-watch
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Step 4: Configure `.env`

Minimum required variables:

```env
TAILSCALE_API_KEY=tskey-api-your-key-here
TAILNET=example.com
WATCH_DEVICE=janes-laptop
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

| Variable | How to find it |
|----------|----------------|
| `TAILNET` | Your tailnet name — usually your email domain (e.g. `example.com`). Visible in the admin console URL or Settings. |
| `WATCH_DEVICE` | Hostname, full device name, or node ID from the Machines page. |
| `DISCORD_WEBHOOK_URL` | See [Notifications → Discord](notifications.md#discord-recommended). |

See [Configuration reference](configuration.md) for every option.

### Recovery intelligence (recommended)

When an alert fires, the watcher gathers extra data to help locate the device:

```bash
tailscale status    # confirm watcher is on the tailnet
tailscale ping janes-laptop   # test reachability to the watched device
```

Defaults in `.env.example` enable Tailscale ping and GeoIP lookup. Set `TAILSCALE_PING_ENABLED=false` or `GEOIP_ENABLED=false` to disable either.

## Step 5: Test a single poll

```bash
python -m tailscale_device_watch once
```

Expected output when things are working:

- If the device is **offline**: a log line like `Device janes-laptop is offline (no alert)`.
- If the device is **online** and was already online on the previous poll: `is online (no alert)`.
- If the device just came **back online** since the last poll: alerts are sent to your configured channels.

On the very first run, no alert fires even if the device is online — the watcher records baseline state first. Alerts only fire on an explicit **offline → online** transition.

## Step 6: Run continuously

```bash
python -m tailscale_device_watch poll
```

Leave this running on an always-on host. Default poll interval is 30 seconds.

For production, use [Deployment → systemd](deployment.md#systemd-linux) or [Docker](deployment.md#docker).

## Verify notifications

To confirm Discord/email/SMS work without waiting for the stolen device:

1. Temporarily set `WATCH_DEVICE` to a device you control.
2. Stop the watcher, delete `state.json`.
3. Take that device offline (disconnect Wi‑Fi or quit Tailscale).
4. Start the watcher — it records the device as offline.
5. Bring the device back online — you should receive an alert within one poll interval.

Restore `WATCH_DEVICE` to the stolen machine when done testing.

## Next steps

- [Set up email or SMS](notifications.md)
- [Deploy with Docker or systemd](deployment.md)
- [Read the stolen device playbook](stolen-device-playbook.md)
