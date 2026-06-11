# Troubleshooting

Common issues and how to fix them.

## Configuration

### `Missing required environment variables`

Set all three required values in `.env`:

```env
TAILSCALE_API_KEY=...
TAILNET=...
WATCH_DEVICE=...
```

Run with an explicit env file if needed:

```bash
python -m tailscale_device_watch once --env-file /path/to/.env
```

### `WATCH_DEVICE matched multiple devices`

Your search string is too broad. Use a unique hostname or the full node ID from [Admin → Machines](https://login.tailscale.com/admin/machines).

```env
# Too broad
WATCH_DEVICE=laptop

# Better
WATCH_DEVICE=janes-work-laptop
```

## Polling

### `No device matched WATCH_DEVICE yet`

The watcher keeps polling — this is normal if the device was removed from the tailnet or the name is wrong. Verify spelling in the admin console.

### Device is online but no alert

Alerts fire only on **offline → online** transitions.

| Situation | Expected behavior |
|-----------|-------------------|
| First run, device already online | No alert (baseline recorded) |
| Device was always online between polls | No alert |
| Watcher restarted, device still online | No alert |
| Device was offline, now online | **Alert sent** |

To test, delete `state.json`, wait for an offline poll, then bring the device online.

### Alerts too slow

Lower the poll interval:

```env
POLL_INTERVAL_SECONDS=15
```

Minimum is 10 seconds. Do not go lower without reason — more API load, little benefit for a stolen laptop scenario.

## Notifications

### `Warning: no notification channels configured`

Set at least one of:

- `DISCORD_WEBHOOK_URL`
- `SMTP_HOST` + `ALERT_EMAIL_TO`
- All four `TWILIO_*` variables + `ALERT_SMS_TO`

### Discord webhook fails

- Verify the URL is complete and the webhook was not deleted in Discord.
- Check channel permissions — the webhook must be allowed to post.
- Run with `-v` for HTTP error details.

### Email fails (Gmail)

- Use an **App Password**, not your regular Gmail password.
- Ensure 2FA is enabled on the Google account.
- `SMTP_PORT=587` with STARTTLS is required.

### SMS fails (Twilio)

All four variables must be set:

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
ALERT_SMS_TO=+1...
```

Trial accounts can only send to verified recipient numbers.

### One channel fails, others work

This is expected — failures are logged per channel. Check logs:

```bash
python -m tailscale_device_watch poll -v
# or
journalctl -u tailscale-device-watch -f
```

## Tailscale API

### HTTP 401 Unauthorized

- API key is invalid or revoked.
- Generate a new key at [Admin → Settings → Keys](https://login.tailscale.com/admin/settings/keys).

### HTTP 404 on devices list

- `TAILNET` value is wrong. Use your tailnet name (e.g. `example.com`), not a device name.

### `connectedToControl` always false

The device is genuinely offline from Tailscale's perspective, or it was removed. Confirm in the admin console Machines page.

## Webhook server

### Tailscale test event fails (401)

`TAILSCALE_WEBHOOK_SECRET` does not match the endpoint secret. Copy the secret again from admin or rotate it.

### Webhook received but no alert

The receiver only acts on:

- Event types: `nodeCreated`, `nodeApproved`, `nodeKeyExpired`, `nodeKeyExpiringInOneDay`
- Events where `nodeID` or `deviceName` matches `WATCH_DEVICE`

A mere reconnect without re-enrollment will **not** trigger the webhook receiver — use polling.

### Cannot reach webhook from Tailscale

- Endpoint must be HTTPS on port 443 or 80.
- Check firewall rules and reverse proxy config.
- Test locally: `curl http://localhost:8080/health`

## Docker

### State resets every restart

Ensure the volume mount exists in `docker-compose.yml`:

```yaml
volumes:
  - ./state.json:/app/state.json
```

Create an empty state file first if needed:

```bash
echo '{}' > state.json
```

### Container exits immediately

Check logs:

```bash
docker compose logs watcher
```

Usually a missing or invalid `.env` file.

## Getting help

When reporting an issue, include:

- Command mode (`poll`, `once`, `serve`, `both`)
- Redacted `.env` structure (never share API keys)
- Log output with `-v`
- Whether the device shows online in the Tailscale admin console
