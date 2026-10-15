"""Coordinator for encrypted Jackery P1 BLE polling."""
from __future__ import annotations
import asyncio
from datetime import timedelta
import logging
from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, WRITE_UUID, NOTIFY_UUID, POLL_SECONDS
from .protocol import Reassembler, decrypt_frame, read_info_packet

_LOGGER = logging.getLogger(__name__)

class JackeryP1Coordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, address: str, key: bytes) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=POLL_SECONDS))
        self.address = address
        self._key = key
        self._client: BleakClient | None = None
        self._lock = asyncio.Lock()
        self._reply: asyncio.Future[dict] | None = None
        self._parser = Reassembler()

    def _notification(self, _sender: object, raw: bytearray) -> None:
        try:
            message = self._parser.add(decrypt_frame(self._key, bytes(raw)))
            if message is None or message["actionId"] != 4005 or message["bleMsgType"] != 106:
                return
            reply = self._reply
            if reply is not None and not reply.done() and isinstance(message["body"], dict):
                reply.set_result(message["body"])
        except (ValueError, KeyError, TypeError) as err:
            _LOGGER.debug("Ignoring invalid P1 notification: %s", err)

    async def _connect(self) -> BleakClient:
        if self._client is not None and self._client.is_connected:
            return self._client
        device = bluetooth.async_ble_device_from_address(self.hass, self.address, connectable=True)
        if device is None:
            raise UpdateFailed("P1 is not available via Bluetooth")
        client = await establish_connection(BleakClient, device, self.address, max_attempts=3)
        try:
            if client.services.get_characteristic(WRITE_UUID) is None or client.services.get_characteristic(NOTIFY_UUID) is None:
                raise BleakError("Missing P1 GATT characteristic")
            await client.start_notify(NOTIFY_UUID, self._notification)
        except Exception:
            await client.disconnect()
            raise
        self._client = client
        self._parser = Reassembler()
        return client

    async def _async_update_data(self) -> dict:
        async with self._lock:
            try:
                client = await self._connect()
                packet = read_info_packet(self._key)
                char = client.services.get_characteristic(WRITE_UUID)
                if char is None or len(packet) > char.max_write_without_response_size:
                    raise BleakError("Encrypted request exceeds BLE write limit")
                reply = asyncio.get_running_loop().create_future()
                self._reply = reply
                try:
                    await client.write_gatt_char(char, packet, response=False)
                    return await asyncio.wait_for(reply, timeout=8)
                finally:
                    self._reply = None
            except (BleakError, OSError, asyncio.TimeoutError, ValueError) as err:
                await self.async_disconnect()
                raise UpdateFailed(f"P1 BLE query failed: {type(err).__name__}") from err

    async def async_disconnect(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            try:
                await client.disconnect()
            except BleakError:
                pass
