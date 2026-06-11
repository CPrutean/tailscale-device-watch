from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    hostname: str
    os: str
    addresses: list[str]
    connected_to_control: bool
    last_seen: str | None
    client_version: str | None
    endpoints: list[str]
    derp: str | None
    raw: dict[str, Any]

    @property
    def display_name(self) -> str:
        return self.hostname or self.name or self.id


class TailscaleClient:
    BASE_URL = "https://api.tailscale.com/api/v2"

    def __init__(self, api_key: str, tailnet: str) -> None:
        self._auth = (api_key, "")
        self._tailnet = tailnet

    def list_devices(self) -> list[Device]:
        url = f"{self.BASE_URL}/tailnet/{self._tailnet}/devices"
        response = httpx.get(url, auth=self._auth, timeout=30.0)
        response.raise_for_status()
        payload = response.json()
        return [self._parse_device(item) for item in payload.get("devices", [])]

    def get_device(self, device_id: str, *, fields: str | None = None) -> Device:
        url = f"{self.BASE_URL}/device/{device_id}"
        params = {"fields": fields} if fields else None
        response = httpx.get(url, auth=self._auth, params=params, timeout=30.0)
        response.raise_for_status()
        return self._parse_device(response.json())

    def get_device_attributes(self, device_id: str) -> dict[str, Any]:
        url = f"{self.BASE_URL}/device/{device_id}/attributes"
        response = httpx.get(url, auth=self._auth, timeout=30.0)
        response.raise_for_status()
        payload = response.json()
        attributes = payload.get("attributes")
        if isinstance(attributes, dict):
            return attributes
        return {}

    @staticmethod
    def _parse_device(data: dict[str, Any]) -> Device:
        connectivity = data.get("clientConnectivity") or {}
        endpoints = list(data.get("endpoints") or connectivity.get("endpoints") or [])
        derp = connectivity.get("derp")
        return Device(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            hostname=str(data.get("hostname", "")),
            os=str(data.get("os", "")),
            addresses=list(data.get("addresses") or []),
            connected_to_control=bool(data.get("connectedToControl", False)),
            last_seen=data.get("lastSeen"),
            client_version=data.get("clientVersion"),
            endpoints=endpoints,
            derp=str(derp) if derp else None,
            raw=data,
        )

    def find_watched_device(self, watch_query: str) -> Device | None:
        query = watch_query.lower()
        matches: list[Device] = []
        for device in self.list_devices():
            haystack = " ".join(
                [
                    device.id,
                    device.name,
                    device.hostname,
                    " ".join(device.addresses),
                ]
            ).lower()
            if query in haystack:
                matches.append(device)

        if not matches:
            return None
        if len(matches) > 1:
            names = ", ".join(d.display_name for d in matches)
            raise ValueError(
                f"WATCH_DEVICE={watch_query!r} matched multiple devices: {names}. "
                "Use a more specific hostname or device ID."
            )
        return matches[0]
