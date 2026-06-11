FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tailscale_device_watch ./tailscale_device_watch
COPY pyproject.toml .

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "tailscale_device_watch", "both"]
