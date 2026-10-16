"""Jackery P1 Home Assistant integration and read-only actions."""
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from .const import CONF_BLUETOOTH_KEY, DOMAIN
from .coordinator import JackeryP1Coordinator
from .protocol import READ_COMMANDS, decode_key

PLATFORMS = ["sensor", "binary_sensor"]
SERVICE_SCHEMA = vol.Schema({vol.Required("entry_id"): cv.string})
SENSITIVE = ("password", "passwd", "token", "secret", "credential", "ssid", "wifi", "key", "mac", "ip")

def _redact(value):
    if isinstance(value, dict):
        return {k: ("[redacted]" if any(s in k.lower() for s in SENSITIVE) else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = JackeryP1Coordinator(hass, entry.data["address"], decode_key(entry.data[CONF_BLUETOOTH_KEY]))
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    for command in READ_COMMANDS:
        if not hass.services.has_service(DOMAIN, command):
            async def handler(call: ServiceCall, cmd: str = command):
                instance = hass.data[DOMAIN].get(call.data["entry_id"])
                if instance is None:
                    raise HomeAssistantError("Unknown Jackery P1 entry_id")
                try:
                    result = await instance.async_read_command(cmd)
                except Exception as exc:
                    raise HomeAssistantError(f"BLE read failed: {type(exc).__name__}") from exc
                return {"command": cmd, "response": _redact(result)}
            hass.services.async_register(DOMAIN, command, handler, schema=SERVICE_SCHEMA, supports_response=SupportsResponse.ONLY)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_disconnect()
    if not hass.data[DOMAIN]:
        for command in READ_COMMANDS:
            hass.services.async_remove(DOMAIN, command)
    return True
