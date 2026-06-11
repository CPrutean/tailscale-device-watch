# Stolen device playbook

Steps to take before, during, and after monitoring a stolen machine on your Tailscale network.

## Before an alert (do now)

### 1. Confirm the device is still enrolled

Open [Admin → Machines](https://login.tailscale.com/admin/machines). If the device is listed, this watcher can detect when it reconnects.

If it was removed from the tailnet, you will not get online alerts — only re-enrollment would trigger a `nodeCreated` webhook.

### 2. Start the watcher

Follow [Getting started](getting-started.md). Run `poll` mode on an always-on host with at least Discord or SMS configured.

Enroll the watcher host on your tailnet and install the Tailscale CLI so alerts include ping and path data. Tag the watcher (e.g. `tag:device-watch`) and allow minimal ACL access to the watched device only.

### 3. Lock down tailnet access

Do not rely on alerts alone. Consider:

| Action | Why |
|--------|-----|
| **Restrict ACLs** | Block the stolen device from reaching sensitive subnets and services. |
| **Enable device approval** | New or re-auth logins require admin approval. |
| **Disable key expiry extension** | Prevents long-lived access if keys were cached locally. |
| **Document the node ID** | Needed for `WATCH_DEVICE` and for police reports. |

Example ACL tag to isolate a device (adapt to your policy):

```json
// Deny stolen device access to internal resources
{"action": "deny", "src": ["tag:stolen"], "dst": ["tag:internal:*"]}
```

Tag the device in admin if possible, or use its Tailscale IP in ACLs.

### 4. Preserve evidence

- Screenshot the device in the admin console (hostname, IPs, last seen).
- Note serial number, asset tag, and MAC address from your inventory.
- File a police report and keep the report number.

### 5. Protect secrets

If the stolen machine had local access to:

- Your `.env` file or API keys → **rotate the Tailscale API key**
- Discord webhook URLs → **regenerate the Discord webhook**
- Twilio credentials → **rotate in Twilio console**

Run the watcher from a machine the thief does not possess.

## When you receive an alert

An alert means the device connected to Tailscale's control plane. Act quickly but carefully.

### Immediate actions (first 15 minutes)

1. **Save the alert** — screenshot Discord/email. The alert may include:
   - Public endpoint IPs (most actionable — police can request ISP subscriber records)
   - GeoIP city/region and an approximate map link
   - Tailscale `ip:country` posture attribute
   - DERP relay region and one `tailscale ping` result (if the watcher is on your tailnet)
2. **Do not tip off the thief** — the watcher runs one ping on alert; avoid further SSH, ping, or remote-wipe unless coordinated with law enforcement.
3. **Check the admin console** — [Admin → Machines](https://login.tailscale.com/admin/machines) for live status, endpoints, and client version.
4. **Record endpoints** — public IP:port pairs (e.g. `203.0.113.50:41641`). Provide these to police; they can request ISP logs. GeoIP map links are approximate context only.

### Tailscale admin actions

| Option | When to use |
|--------|-------------|
| **Remove device** | You want it off the network immediately. |
| **Revoke / expire keys** | Force re-authentication. |
| **Update ACLs** | Block access while keeping the device visible for monitoring. |
| **Disable the user** | If the whole account may be compromised. |

Removing the device stops further Tailscale connectivity but also stops your watcher from detecting future reconnects unless they re-enroll (which would fire `nodeCreated` if webhooks are configured).

### Law enforcement

Provide:

- Time of alert (UTC)
- Public endpoint IPs from the alert
- Device hostname and Tailscale node ID
- Police report number
- Statement that Tailscale logs connection metadata, not file contents or GPS

Tailscale may respond to valid legal process; contact them through official channels if instructed by law enforcement.

## After the incident

- Rotate all compromised credentials.
- Remove or re-tag the device in Tailscale.
- Stop the watcher or update `WATCH_DEVICE` if monitoring is no longer needed.
- Review ACLs and device approval settings for the rest of the tailnet.

## What this tool does not do

- **No GPS tracking** — GeoIP and `ip:country` are derived from public IP addresses, not device GPS.
- **No remote wipe** — use Find My Device, Intune, or similar.
- **No guarantee of instant detection** — polling interval adds up to `POLL_INTERVAL_SECONDS` delay.
- **No offline webhook** — Tailscale does not push reconnect events; polling is required.

## Related docs

- [Architecture](architecture.md) — exactly when alerts fire
- [Troubleshooting](troubleshooting.md) — if alerts are missing or false
