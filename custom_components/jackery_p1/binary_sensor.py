"""Jackery P1 connection diagnostics."""
from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import JackeryP1Coordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    if entry.data.get("mode", "ble") == "ble":
        add([P1Connection(coordinator, entry)])

class P1Connection(CoordinatorEntity[JackeryP1Coordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Bluetooth connected"
    _attr_entity_registry_enabled_default = False
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: JackeryP1Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_bluetooth_connected"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id or entry.entry_id)})
    @property
    def available(self) -> bool:
        return True
    @property
    def is_on(self) -> bool:
        return self.coordinator.is_connected
