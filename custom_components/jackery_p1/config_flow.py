"""BLE discovery and manual/account Jackery P1 setup."""
import base64
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
import voluptuous as vol
from .auth import DeviceListError, LoginError, fetch_bound_p1_keys
from .const import CONF_BLUETOOTH_KEY, DOMAIN, SERVICE_UUID
from .protocol import decode_key
from .lan import normalize_host, read_json
from aiohttp import ClientError

class JackeryP1ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._address = None
        self._devices = []

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        if SERVICE_UUID not in (uuid.lower() for uuid in discovery_info.service_uuids):
            return self.async_abort(reason="not_supported")
        self._address = discovery_info.address
        await self.async_set_unique_id(self._address)
        self._abort_if_unique_id_configured()
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        if user_input:
            if user_input["method"] == "lan":
                return await self.async_step_lan()
            if user_input["method"] == "account":
                return await self.async_step_account()
            return await self.async_step_manual()
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("method", default="lan"): vol.In({
                "account": "Jackery account (Bluetooth)",
                "manual": "Existing key (Bluetooth)",
                "lan": "LAN (local HTTP)",
            })
        }))


    async def async_step_lan(self, user_input=None):
        """Configure local HTTP using the P1's Wi-Fi hostname or IP."""
        errors = {}
        if user_input:
            try:
                host = normalize_host(user_input["host"])
                info = await read_json(self.hass, host, "/device_info")
                if info.get("type") != 4001 or not info.get("sn"):
                    errors["base"] = "not_p1"
                else:
                    serial = str(info["sn"])
                    await self.async_set_unique_id(f"lan_{serial}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"Jackery P1 ({serial[-4:]})",
                        data={"mode": "lan", "host": host},
                    )
            except ValueError:
                errors["base"] = "invalid_host"
            except (ClientError, TimeoutError, OSError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="lan",
            data_schema=vol.Schema({vol.Required("host"): str}),
            errors=errors,
        )

    def _address_field(self):
        return {} if self._address else {vol.Required("address"): str}

    async def _save(self, address, key):
        address = address.strip()
        if not address:
            return self.async_abort(reason="invalid_address")
        await self.async_set_unique_id(address)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Jackery P1",
            data={"mode": "ble", "address": address, CONF_BLUETOOTH_KEY: key},
        )

    async def async_step_manual(self, user_input=None):
        errors = {}
        if user_input:
            try:
                decode_key(user_input[CONF_BLUETOOTH_KEY])
            except (ValueError, base64.binascii.Error):
                errors[CONF_BLUETOOTH_KEY] = "invalid_key"
            else:
                return await self._save(self._address or user_input["address"], user_input[CONF_BLUETOOTH_KEY].strip())
        return self.async_show_form(step_id="manual", data_schema=vol.Schema({
            **self._address_field(), vol.Required(CONF_BLUETOOTH_KEY): str
        }), errors=errors)

    async def async_step_account(self, user_input=None):
        errors = {}
        if user_input:
            address = self._address or user_input["address"].strip()
            try:
                self._devices = await fetch_bound_p1_keys(
                    user_input["email"].strip(),
                    user_input["password"],
                    user_input["region"].strip().upper(),
                )
            except LoginError:
                errors["base"] = "cannot_authenticate"
            except DeviceListError:
                errors["base"] = "cannot_get_devices"
            else:
                self._address = address
                if not self._devices:
                    errors["base"] = "no_p1_devices"
                elif len(self._devices) == 1:
                    return await self._save(address, self._devices[0]["bluetooth_key"])
                else:
                    return await self.async_step_select_device()
        return self.async_show_form(step_id="account", data_schema=vol.Schema({
            **self._address_field(),
            vol.Required("email"): str,
            vol.Required("password"): str,
            vol.Required("region", default="NL"): str,
        }), errors=errors)

    async def async_step_select_device(self, user_input=None):
        if not self._devices:
            return self.async_abort(reason="no_p1_devices")
        if user_input:
            selected = self._devices[int(user_input["device"])]
            return await self._save(self._address, selected["bluetooth_key"])
        choices = {
            str(i): f"{d['name']} (serial ending {d['serial'][-4:]})"
            for i, d in enumerate(self._devices)
        }
        return self.async_show_form(step_id="select_device", data_schema=vol.Schema({
            vol.Required("device"): vol.In(choices)
        }))
