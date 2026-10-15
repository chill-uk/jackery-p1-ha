"""Jackery P1 discovery and manual key configuration."""
from __future__ import annotations
import base64
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
import voluptuous as vol
from .const import CONF_BLUETOOTH_KEY, DOMAIN, SERVICE_UUID
from .protocol import decode_key

class JackeryP1ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._address: str | None = None

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        if SERVICE_UUID not in (uuid.lower() for uuid in discovery_info.service_uuids):
            return self.async_abort(reason="not_supported")
        self._address = discovery_info.address
        await self.async_set_unique_id(self._address)
        self._abort_if_unique_id_configured()
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            address = self._address or user_input["address"].strip()
            try:
                decode_key(user_input[CONF_BLUETOOTH_KEY])
            except (ValueError, base64.binascii.Error):
                errors[CONF_BLUETOOTH_KEY] = "invalid_key"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Jackery P1", data={"address": address, CONF_BLUETOOTH_KEY: user_input[CONF_BLUETOOTH_KEY].strip()})
        schema = {vol.Required(CONF_BLUETOOTH_KEY): str}
        if self._address is None:
            schema = {vol.Required("address"): str, **schema}
        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema), errors=errors)
