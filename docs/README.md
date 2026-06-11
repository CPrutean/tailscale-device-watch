# Documentation

Complete guide for **Tailscale Device Watch** — alert when a specific device reconnects to your tailnet.

## Contents

| Document | Description |
|----------|-------------|
| [Getting started](getting-started.md) | Install, configure, and run your first poll |
| [Configuration reference](configuration.md) | All environment variables and CLI options |
| [Notifications](notifications.md) | Discord, email, and SMS setup |
| [Deployment](deployment.md) | Docker, systemd, and where to run the watcher |
| [Tailscale webhooks](tailscale-webhooks.md) | Optional supplementary webhook receiver |
| [Stolen device playbook](stolen-device-playbook.md) | Security steps before and after an alert |
| [Architecture](architecture.md) | How detection and alerting work |
| [Troubleshooting](troubleshooting.md) | Common problems and fixes |

## Quick reference

```bash
# Install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Test once
python -m tailscale_device_watch once

# Run continuously (recommended)
python -m tailscale_device_watch poll
```

## Key concept

Tailscale **does not** send webhooks when a device simply reconnects. This tool polls the [Devices API](https://tailscale.com/docs/reference/tailscale-api) and alerts when `connectedToControl` changes from `false` to `true`.
