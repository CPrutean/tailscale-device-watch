# Deployment

The watcher must run **continuously** on an always-on machine. If it stops, you will miss reconnect events between polls.

## Where to run it

Good options:

| Host | Pros | Cons |
|------|------|------|
| Home server / NAS on tailnet | Simple, no extra cost | Stops if home internet goes down |
| Cloud VPS | Always on, independent of stolen device | Small monthly cost |
| Another laptop / desktop on tailnet | Easy if already always on | Must not be the watched device |
| Docker on existing infra | Easy updates, restart policies | Needs Docker |

**Do not** run the watcher on the stolen device itself.

## Docker

### Quick start

```bash
cp .env.example .env
# Edit .env with your values

docker compose up -d --build
```

### What Docker runs

The default `CMD` runs **`both`** mode:

- Background poller (every `POLL_INTERVAL_SECONDS`)
- Webhook server on port `8080`

### Compose file

```yaml
services:
  watcher:
    build: .
    restart: unless-stopped
    env_file: .env
    ports:
      - "${WEBHOOK_PORT:-8080}:8080"
    volumes:
      - ./state.json:/app/state.json
```

The `state.json` volume preserves online/offline state across container restarts.

### Poll-only Docker

If you do not need the webhook server, override the command:

```yaml
services:
  watcher:
    build: .
    restart: unless-stopped
    env_file: .env
    command: ["python", "-m", "tailscale_device_watch", "poll"]
    volumes:
      - ./state.json:/app/state.json
```

### Logs

```bash
docker compose logs -f watcher
```

## systemd (Linux)

Install to `/opt/tailscale-device-watch`:

```bash
sudo mkdir -p /opt/tailscale-device-watch
sudo cp -r . /opt/tailscale-device-watch/
cd /opt/tailscale-device-watch
sudo python3 -m venv .venv
sudo .venv/bin/pip install -r requirements.txt
sudo cp .env.example .env
# Edit /opt/tailscale-device-watch/.env
```

Create `/etc/systemd/system/tailscale-device-watch.service`:

```ini
[Unit]
Description=Tailscale device online watcher
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=tailscale-watch
Group=tailscale-watch
WorkingDirectory=/opt/tailscale-device-watch
EnvironmentFile=/opt/tailscale-device-watch/.env
ExecStart=/opt/tailscale-device-watch/.venv/bin/python -m tailscale_device_watch poll
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Create a dedicated user and lock down permissions:

```bash
sudo useradd --system --no-create-home tailscale-watch
sudo chown -R tailscale-watch:tailscale-watch /opt/tailscale-device-watch
sudo chmod 600 /opt/tailscale-device-watch/.env
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tailscale-device-watch
sudo systemctl status tailscale-device-watch
sudo journalctl -u tailscale-device-watch -f
```

## Running behind Tailscale (webhook mode)

If you use `serve` or `both`, expose the webhook only to trusted networks:

1. Run the watcher on a tailnet node.
2. Use [Tailscale Serve](https://tailscale.com/kb/1312/serve) or Funnel to expose `/tailscale-webhook` — or reverse-proxy from an existing HTTPS host.
3. Point the Tailscale admin webhook at `https://your-node.example.ts.net/tailscale-webhook`.

Prefer Serve over exposing port 8080 to the public internet.

## Updating

### Manual / systemd

```bash
cd /opt/tailscale-device-watch
git pull   # if using git
.venv/bin/pip install -r requirements.txt
sudo systemctl restart tailscale-device-watch
```

### Docker

```bash
docker compose down
docker compose up -d --build
```

State in `state.json` is preserved via the volume mount.

## Resource usage

Minimal — one HTTP request to Tailscale every poll interval, plus occasional notification HTTP calls. Typical memory footprint is well under 100 MB.
