# Notifications

Tailscale Device Watch supports three alert channels. Enable any combination — all configured channels receive each alert.

Alerts are sent when a watched device transitions from **offline to online** (`connectedToControl`: `false` → `true`).

## Alert contents

Every alert includes:

- Device hostname / display name
- Tailscale node ID
- Operating system
- Tailscale IP addresses (`100.x.x.x`)
- Tailscale client version
- Public endpoints (if reported by the API — often useful for geolocation)
- Recommended next steps

## Discord (recommended)

Fastest to set up and good for urgent pings.

### Setup

1. In Discord, open your server → **Server Settings** → **Integrations** → **Webhooks**.
2. Click **New Webhook**, choose an alerts channel, and copy the webhook URL.
3. Add to `.env`:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef...
```

For multiple Discord channels, separate webhook URLs with commas:

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/111/aaa,https://discord.com/api/webhooks/222/bbb
```

Or use the optional `DISCORD_WEBHOOK_URLS` alias for additional URLs.

### What you receive

- A red embed with full device details
- `@everyone` mention when the alert title contains the word "stolen" (default behavior in `notifier.py`)

### Tips

- Create a dedicated `#security-alerts` channel with notifications enabled.
- Restrict who can mention `@everyone` if needed — or edit `notifier.py` to use a role ping instead.

## Email

Works with any SMTP provider: Gmail, Outlook, SendGrid, Amazon SES, etc.

### Gmail example

1. Enable [2-Step Verification](https://myaccount.google.com/security).
2. Create an [App Password](https://myaccount.google.com/apppasswords).
3. Configure `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM=you@gmail.com
ALERT_EMAIL_TO=you@gmail.com,partner@gmail.com
```

### SendGrid example

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your-sendgrid-api-key
SMTP_FROM=alerts@yourdomain.com
ALERT_EMAIL_TO=you@gmail.com,security@yourdomain.com
```

### Multiple recipients

Separate email addresses with commas, semicolons, or newlines:

```env
ALERT_EMAIL_TO=alice@example.com,bob@example.com
```

You can also use `ALERT_EMAIL_TO_LIST` for additional addresses (merged with `ALERT_EMAIL_TO`).

All recipients receive the same alert in a single email (one message, multiple `To` addresses).

### Notes

- Uses STARTTLS on the configured port.
- Subject line: `ALERT: {device name} is back on Tailscale`
- Body is plain text with full details.

## SMS (Twilio)

Best for waking you up when email/Discord might be missed. Messages are intentionally short; use Discord or email for full endpoint details.

### Setup

1. Create a [Twilio](https://www.twilio.com) account.
2. Buy or verify a phone number for sending.
3. Verify your personal number as a recipient (trial accounts require this).
4. Configure `.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM_NUMBER=+15551234567
ALERT_SMS_TO=+15559876543,+15551112222
```

Each number receives its own SMS. Separate numbers with commas, semicolons, or newlines.
Use `ALERT_SMS_TO_LIST` for additional numbers if needed.

### Message format

```
ALERT: janes-laptop is back on Tailscale. janes-laptop. Check email/Discord for details.
```

All four Twilio variables must be set for SMS to work.

## Using multiple channels

```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=app-password
ALERT_EMAIL_TO=you@gmail.com,partner@gmail.com
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+1...
ALERT_SMS_TO=+1...,+1...
```

If one channel fails, the others still send. Failures are logged but do not stop the watcher.

## Testing without the stolen device

See [Getting started → Verify notifications](getting-started.md#verify-notifications).
