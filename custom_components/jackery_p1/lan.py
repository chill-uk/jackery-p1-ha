"""Local HTTP transport for Jackery P1 devices."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, POLL_SECONDS

_LOGGER = logging.getLogger(__name__)


def normalize_host(value: str) -> str:
    """Validate a LAN host or HTTP URL without accepting embedded credentials."""
    value = value.strip()
    if not value:
        raise ValueError("Host is required")
    parsed = urlsplit(value if "://" in value else f"http://{value}")
    if (parsed.scheme != "http" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ValueError("Enter a local hostname or HTTP URL without a path")
    try:
        port = parsed.port
    except ValueError as err:
        raise ValueError("Invalid HTTP port") from err
    hostname = parsed.hostname
    if ":" in hostname:
        hostname = f"[{hostname}]"
    return f"http://{hostname}:{port}" if port is not None else f"http://{hostname}"


async def read_json(hass: HomeAssistant, base_url: str, path: str) -> dict:
    """Read a JSON endpoint without logging response bodies or identifiers."""
    session = async_get_clientsession(hass)
    async with session.get(
        f"{base_url}{path}", timeout=ClientTimeout(total=8), allow_redirects=False
    ) as response:
        response.raise_for_status()
        if response.content_type != "application/json":
            raise ValueError("Expected JSON from Jackery P1")
        payload = await response.json()
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object from Jackery P1")
        return payload


class JackeryP1LanCoordinator(DataUpdateCoordinator[dict]):
    """Poll local measurement and monitoring endpoints."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=POLL_SECONDS)
        )
        self.base_url = normalize_host(host)
        self.device_info: dict = {}
        self.last_success: datetime | None = None

    @property
    def is_connected(self) -> bool:
        return self.last_update_success

    def rssi(self) -> None:
        return None

    async def _async_update_data(self) -> dict:
        try:
            if not self.device_info:
                info = await read_json(self.hass, self.base_url, "/device_info")
                if info.get("type") != 4001:
                    raise ValueError("HTTP server is not a Jackery P1")
                self.device_info = info
            measurement = await read_json(self.hass, self.base_url, "/api/measurement")
            monitor = await read_json(self.hass, self.base_url, "/api/monitor")
            result = {**measurement, **monitor}
            self.last_success = datetime.now(timezone.utc)
            return result
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"P1 LAN query failed: {type(err).__name__}") from err

    async def async_disconnect(self) -> None:
        """HTTP connections are managed by Home Assistant's shared session."""

    async def async_read_command(self, command: str) -> dict:
        raise UpdateFailed("BLE commands are unavailable in LAN mode")
