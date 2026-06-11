from __future__ import annotations

import ipaddress
import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import Config
from .tailscale import Device, TailscaleClient

logger = logging.getLogger(__name__)

_PONG_LINE = re.compile(r"^pong from .+$", re.MULTILINE)


@dataclass(frozen=True)
class GeoLocation:
    ip: str
    country: str | None
    region: str | None
    city: str | None
    latitude: float | None
    longitude: float | None
    isp: str | None
    org: str | None

    @property
    def summary(self) -> str:
        place = ", ".join(part for part in (self.city, self.region, self.country) if part)
        network = self.org or self.isp or "unknown network"
        coords = ""
        if self.latitude is not None and self.longitude is not None:
            coords = f" ({self.latitude:.4f}, {self.longitude:.4f})"
        return f"{self.ip}: {place or 'unknown location'}{coords} — {network}"


@dataclass(frozen=True)
class PingResult:
    target: str
    reachable: bool
    lines: tuple[str, ...]
    last_pong: str | None

    @property
    def summary(self) -> str:
        if self.last_pong:
            return self.last_pong
        if self.lines:
            return self.lines[-1]
        return "no response"


@dataclass(frozen=True)
class RecoveryIntel:
    posture_attributes: dict[str, Any] = field(default_factory=dict)
    derp: str | None = None
    endpoints: tuple[str, ...] = ()
    geo_locations: tuple[GeoLocation, ...] = ()
    ping: PingResult | None = None

    @property
    def posture_country(self) -> str | None:
        value = self.posture_attributes.get("ip:country")
        return str(value) if value else None

    @property
    def maps_url(self) -> str | None:
        for location in self.geo_locations:
            if location.latitude is not None and location.longitude is not None:
                return (
                    f"https://www.google.com/maps?q={location.latitude},{location.longitude}"
                )
        return None

    def format_lines(self) -> list[str]:
        lines: list[str] = []

        if self.posture_country:
            lines.append(f"Tailscale geolocation (country): {self.posture_country}")

        if self.derp:
            lines.append(f"DERP relay: {self.derp}")

        if self.endpoints:
            lines.append(f"Public endpoints: {', '.join(self.endpoints)}")

        for location in self.geo_locations:
            lines.append(f"GeoIP: {location.summary}")

        if self.ping is not None:
            status = "reachable" if self.ping.reachable else "unreachable"
            lines.append(
                f"Tailscale ping ({self.ping.target}, {status}): {self.ping.summary}"
            )

        if self.maps_url:
            lines.append(f"Approximate map: {self.maps_url}")

        return lines


def parse_endpoint_host(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if endpoint.startswith("["):
        closing = endpoint.index("]")
        return endpoint[1:closing]
    if endpoint.count(":") == 1:
        return endpoint.rsplit(":", 1)[0]
    return endpoint


def public_endpoint_ips(endpoints: list[str]) -> list[str]:
    seen: set[str] = set()
    public: list[str] = []
    for endpoint in endpoints:
        try:
            host = parse_endpoint_host(endpoint)
            address = ipaddress.ip_address(host)
        except ValueError:
            continue
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        ):
            continue
        if host not in seen:
            seen.add(host)
            public.append(host)
    return public


def lookup_geoip(ip: str, timeout: float = 10.0) -> GeoLocation | None:
    url = (
        "http://ip-api.com/json/"
        f"{ip}?fields=status,message,country,regionName,city,lat,lon,isp,org,query"
    )
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.warning("GeoIP lookup failed for %s: %s", ip, exc)
        return None

    if payload.get("status") != "success":
        logger.warning(
            "GeoIP lookup rejected for %s: %s",
            ip,
            payload.get("message", "unknown error"),
        )
        return None

    return GeoLocation(
        ip=str(payload.get("query", ip)),
        country=payload.get("country"),
        region=payload.get("regionName"),
        city=payload.get("city"),
        latitude=payload.get("lat"),
        longitude=payload.get("lon"),
        isp=payload.get("isp"),
        org=payload.get("org"),
    )


def ping_target_for_device(device: Device) -> str | None:
    if device.hostname:
        return device.hostname
    if device.name:
        return device.name
    for address in device.addresses:
        if address.startswith("100."):
            return address
    return device.addresses[0] if device.addresses else None


def run_tailscale_ping(
    target: str,
    *,
    cli: str,
    count: int,
    timeout_seconds: float,
) -> PingResult:
    command = [
        cli,
        "ping",
        "-c",
        str(count),
        f"--timeout={timeout_seconds}s",
        target,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=max(timeout_seconds * count + 10, 20),
            check=False,
        )
    except FileNotFoundError:
        logger.warning("%s not found; skipping tailnet ping", cli)
        return PingResult(target=target, reachable=False, lines=(), last_pong=None)
    except subprocess.TimeoutExpired:
        logger.warning("tailscale ping timed out for %s", target)
        return PingResult(
            target=target,
            reachable=False,
            lines=("tailscale ping timed out",),
            last_pong=None,
        )

    output = "\n".join(
        line for line in (completed.stdout + completed.stderr).splitlines() if line.strip()
    )
    lines = tuple(output.splitlines())
    pong_lines = _PONG_LINE.findall(output)
    last_pong = pong_lines[-1] if pong_lines else None
    reachable = completed.returncode == 0 and last_pong is not None
    return PingResult(
        target=target,
        reachable=reachable,
        lines=lines,
        last_pong=last_pong,
    )


def gather_recovery_intel(
    client: TailscaleClient,
    device: Device,
    config: Config,
) -> RecoveryIntel:
    full_device = client.get_device(device.id, fields="all")
    posture_attributes: dict[str, Any] = {}
    try:
        posture_attributes = client.get_device_attributes(device.id)
    except Exception as exc:
        logger.warning("Could not fetch posture attributes for %s: %s", device.id, exc)

    endpoints = list(full_device.endpoints)
    geo_locations: list[GeoLocation] = []
    if config.geoip_enabled:
        for ip in public_endpoint_ips(endpoints):
            location = lookup_geoip(ip)
            if location is not None:
                geo_locations.append(location)

    ping: PingResult | None = None
    if config.tailscale_ping_enabled:
        target = ping_target_for_device(full_device)
        if target:
            ping = run_tailscale_ping(
                target,
                cli=config.tailscale_cli,
                count=config.tailscale_ping_count,
                timeout_seconds=config.tailscale_ping_timeout_seconds,
            )
        else:
            logger.warning("No ping target available for device %s", full_device.id)

    return RecoveryIntel(
        posture_attributes=posture_attributes,
        derp=full_device.derp,
        endpoints=tuple(endpoints),
        geo_locations=tuple(geo_locations),
        ping=ping,
    )
