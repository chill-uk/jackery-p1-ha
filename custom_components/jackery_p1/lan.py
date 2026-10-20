"""Local HTTP transport for Jackery P1 devices."""
from __future__ import annotations

import logging
import time
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

    def __init__(self, hass: HomeAssistant, host: str, poll_seconds: int = POLL_SECONDS) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=poll_seconds)
        )
        self.base_url = normalize_host(host)
        self.device_info: dict = {}
        self.last_success: datetime | None = None
        self.last_measurement_success: datetime | None = None
        self.last_monitor_success: datetime | None = None
        self.measurement_response_ms: int | None = None
        self.monitor_response_ms: int | None = None
        self.measurement_failures = 0
        self.monitor_failures = 0
        self.measurement_ok = False
        self.monitor_ok = False

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
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"P1 identity query failed: {type(err).__name__}") from err

        result: dict = {}
        for endpoint, path in (
            ("measurement", "/api/measurement"),
            ("monitor", "/api/monitor"),
        ):
            started = time.monotonic()
            try:
                payload = await read_json(self.hass, self.base_url, path)
            except (ClientError, TimeoutError, ValueError, OSError) as err:
                setattr(self, f"{endpoint}_ok", False)
                setattr(self, f"{endpoint}_failures", getattr(self, f"{endpoint}_failures") + 1)
                _LOGGER.debug("P1 %s unavailable: %s", endpoint, type(err).__name__)
            else:
                now = datetime.now(timezone.utc)
                result.update(payload)
                setattr(self, f"{endpoint}_ok", True)
                setattr(self, f"last_{endpoint}_success", now)
                setattr(self, f"{endpoint}_response_ms", round((time.monotonic() - started) * 1000))
                setattr(self, f"{endpoint}_failures", 0)
                self.last_success = now

        if not (self.measurement_ok or self.monitor_ok):
            raise UpdateFailed("P1 measurement and monitor endpoints unavailable")
        return result

    async def async_disconnect(self) -> None:
        """HTTP connections are managed by Home Assistant's shared session."""

    async def async_read_command(self, command: str) -> dict:
        raise UpdateFailed("BLE commands are unavailable in LAN mode")
