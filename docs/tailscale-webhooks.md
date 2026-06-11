# Tailscale webhooks

This document covers the **optional** webhook receiver built into Tailscale Device Watch. Read this together with the main limitation below.

## What Tailscale webhooks cannot do

Tailscale webhooks **do not** include device online/offline events. Available events are limited to tailnet management and misconfiguration, for example:

| Event | When it fires |
|-------|----------------|
| `nodeCreated` | A new node joins the tailnet |
| `nodeDeleted` | A node is removed |
| `nodeApproved` | A pending node is approved |
| `nodeKeyExpired` | A node key expired |
| `nodeKeyExpiringInOneDay` | Key expires within 24 hours |
| `policyUpdate` | ACL policy file changed |

A stolen laptop that **reconnects without re-enrolling** will **not** trigger any of these. That is why **API polling is the primary detection method** in this project.

Webhooks are still useful as a supplement — e.g. if someone re-enrolls the machine or its key expires.

## When to use the webhook receiver

Enable webhook mode if you want alerts for Tailscale management events **on the watched device**, in addition to online detection via polling.

| Mode | Polling | Webhook server |
|------|---------|----------------|
| `poll` | Yes | No |
| `once` | Single check | No |
| `serve` | No | Yes |
| `both` | Yes | Yes (Docker default) |

## Setup

### 1. Expose the webhook endpoint

The watcher must be reachable by Tailscale's webhook delivery service over HTTPS on port 443 or 80.

Options:

- Deploy on a VPS with a valid TLS certificate.
- Use Tailscale Serve/Funnel on a tailnet node.
- Reverse-proxy through nginx/Caddy with TLS.

Endpoint path: **`POST /tailscale-webhook`**

Health check: **`GET /health`**

### 2. Create the webhook in Tailscale admin

1. Open [Admin → Webhooks](https://login.tailscale.com/admin/webhooks).
2. Click **Add endpoint**.
3. Set **Webhook URL** to `https://your-host/tailscale-webhook`.
4. Subscribe to **Tailnet management** events (or select specific events).
5. Copy the **webhook secret** when shown — you cannot retrieve it later.

### 3. Configure the secret

```env
TAILSCALE_WEBHOOK_SECRET=your-secret-from-tailscale
WEBHOOK_PORT=8080
```

If `TAILSCALE_WEBHOOK_SECRET` is set, requests without a valid `Tailscale-Webhook-Signature` header are rejected with HTTP 401.

### 4. Run the server

```bash
# Webhook only
python -m tailscale_device_watch serve

# Polling + webhook
python -m tailscale_device_watch both
```

### 5. Test the endpoint

In the Tailscale admin console:

1. Find your webhook endpoint.
2. Open the menu → **Test endpoint** → **Send test event**.

You should see a log line: `Received Tailscale webhook test event`.

## Handled events

The receiver filters events to those matching `WATCH_DEVICE` and these types:

- `nodeCreated`
- `nodeApproved`
- `nodeKeyExpired`
- `nodeKeyExpiringInOneDay`

When a matching event arrives, the watcher fetches full device details from the API and sends notifications through your configured channels (Discord, email, SMS).

## Signature verification

Tailscale signs each request with an HMAC-SHA256 header:

```
Tailscale-Webhook-Signature: t=1663781880,v1=0123...abc
```

The watcher:

1. Parses timestamp `t` and signature `v1` from the header.
2. Rejects requests older than 5 minutes (replay protection).
3. Computes HMAC over `{timestamp}.{raw_body}` using your webhook secret.
4. Compares signatures with a constant-time compare.

Reference: [Tailscale webhook docs — Verifying an event signature](https://tailscale.com/docs/features/webhooks#verifying-an-event-signature)

## Payload format

Events arrive as a JSON **array** of objects:

```json
[
  {
    "timestamp": "2026-06-10T12:00:00Z",
    "version": 1,
    "type": "nodeCreated",
    "tailnet": "example.com",
    "message": "Node janes-laptop.example.ts.net created",
    "data": {
      "nodeID": "nAbCdEf123",
      "deviceName": "janes-laptop.example.ts.net",
      "managedBy": "jane@example.com",
      "actor": "jane@example.com",
      "url": "https://login.tailscale.com/admin/machines/100.64.0.5"
    }
  }
]
```

## Direct Discord webhook (alternative)

Tailscale admin lets you set **Destination: Discord** when the webhook URL is a Discord URL. That sends Tailscale events directly to Discord **without** this project.

That approach does **not** add online/offline detection. Use this project's poller for reconnect alerts, and optionally use either:

- This project's webhook receiver (filtered to your watched device), or
- A native Tailscale → Discord webhook for all tailnet events.
