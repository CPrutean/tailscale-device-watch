# Architecture

How Tailscale Device Watch detects reconnects and sends alerts.

## Overview

```
┌─────────────────┐     poll every N sec      ┌──────────────────────┐
│  Watcher process│ ─────────────────────────►│ Tailscale Devices API │
│  (your server)  │◄───────────────────────── │ /tailnet/.../devices  │
└────────┬────────┘     connectedToControl    └──────────────────────┘
         │
         │ offline → online?
         ▼
┌─────────────────┐
│    Notifier     │──► Discord webhook
│                 │──► SMTP email
│                 │──► Twilio SMS
└─────────────────┘

Optional:
┌─────────────────┐     POST /tailscale-webhook     ┌─────────────────┐
│ Tailscale admin │ ───────────────────────────────►│ FastAPI server  │
│ webhooks        │                                 │ (serve/both)    │
└─────────────────┘                                 └────────┬────────┘
                                                             │
                                                    filter by WATCH_DEVICE
                                                             ▼
                                                      Notifier (same)
```

## Detection logic (polling)

Each poll cycle in `poller.py`:

1. **List devices** — `GET /api/v2/tailnet/{tailnet}/devices`
2. **Match** — find the one device where `WATCH_DEVICE` appears in ID, name, hostname, or IPs
3. **Load state** — read previous `connected_to_control` from `state.json`
4. **Compare** — alert only if:
   - current `connectedToControl` is `true`, **and**
   - previous state was explicitly `false`
5. **Persist** — write updated state to `state.json`

### Why not alert on first run?

If the watcher starts while the device is already online, `previously_online` is `null`, not `false`. No alert fires. This avoids noise on restarts.

### Why not use webhooks for online detection?

Tailscale's coordination server does not expose online/offline as webhook events ([feature request](https://github.com/tailscale/tailscale/issues/11166)). The public Devices API exposes `connectedToControl` for polling.

`lastSeen` alone is unreliable — it reflects the last offline→online transition, not continuous activity.

## Webhook receiver (optional)

`webhook_server.py` runs a FastAPI app with two routes:

| Route | Purpose |
|-------|---------|
| `GET /health` | Liveness probe |
| `POST /tailscale-webhook` | Receive Tailscale event batches |

For each event in the JSON array:

1. Verify HMAC signature (if secret configured)
2. Skip unless `type` is in the watched set
3. Skip unless event `data` matches `WATCH_DEVICE`
4. Fetch device via `GET /api/v2/device/{id}`
5. Send notifications

Webhook alerts are **independent** of poll-based alerts — either can fire alone.

## Notification pipeline

`notifier.py` builds a title and body from device metadata, then dispatches to each configured channel in parallel (failures are logged per channel).

Discord uses an embed (red, 0xFF0000). Email uses plain text. SMS uses a truncated summary via Twilio REST API.

## State persistence

`state.json` maps device ID → last known status. Survives restarts when mounted as a volume (Docker) or stored on disk (systemd).

Deleting the file resets baseline — the next offline→online transition will alert.

## Project layout

```
tailscale-device-watch/
├── tailscale_device_watch/
│   ├── __main__.py       # CLI entrypoint
│   ├── config.py         # Environment loading
│   ├── poller.py         # Poll loop and transition detection
│   ├── tailscale.py      # Tailscale API client
│   ├── notifier.py       # Discord, email, SMS
│   ├── webhook_server.py # FastAPI webhook receiver
│   └── state.py          # JSON state read/write
├── docs/                 # This documentation
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## API authentication

Tailscale API requests use HTTP basic auth:

```
Authorization: Basic base64("{api_key}:")
```

The password is empty — only the API key is sent.

## Limits and tradeoffs

| Topic | Detail |
|-------|--------|
| Poll delay | Up to `POLL_INTERVAL_SECONDS` before detection |
| API rate limits | Tailscale may rate-limit aggressive polling; stay ≥10s |
| Endpoint data | Public IPs appear only when Tailscale has them; may be empty |
| Multi-device match | Refuses to run if `WATCH_DEVICE` matches more than one device |
| Twilio | Requires all four Twilio env vars; SMS is supplementary |
