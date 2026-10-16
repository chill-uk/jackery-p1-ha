"""Jackery P1 measurement sensors with optional firmware-specific attributes."""
from __future__ import annotations

from dataclasses import dataclass
from homeassistant.components import bluetooth
from homeassistant.util import dt as dt_util

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JackeryP1Coordinator


@dataclass(frozen=True, kw_only=True)
class P1Description(SensorEntityDescription):
    multiplier: float = 1.0
    optional: bool = False
    inactive_phase: bool = False


def _sensor(
    key: str,
    name: str,
    unit: str | None = None,
    device_class: SensorDeviceClass | None = None,
    multiplier: float = 1.0,
    optional: bool = False,
    inactive_phase: bool = False,
) -> P1Description:
    return P1Description(
        key=key,
        name=name,
        native_unit_of_measurement=unit,
        device_class=device_class,
        state_class=SensorStateClass.MEASUREMENT,
        multiplier=multiplier,
        optional=optional,
        inactive_phase=inactive_phase,
    )


# Existing field names and units validated on the physical P1.
BASE_SENSORS = (
    _sensor("power", "Total power", "W", SensorDeviceClass.POWER),
    *(
        _sensor(f"power{i}", f"Phase {i} power", "W", SensorDeviceClass.POWER)
        for i in (1, 2, 3)
    ),
    *(
        _sensor(f"volt{i}", f"Phase {i} voltage", "V", SensorDeviceClass.VOLTAGE)
        for i in (1, 2, 3)
    ),
    _sensor("curr", "Total current", "A", SensorDeviceClass.CURRENT, 0.1),
    *(
        _sensor(f"curr{i}", f"Phase {i} current", "A", SensorDeviceClass.CURRENT, 0.1)
        for i in (1, 2, 3)
    ),
)

# The shared accessory model defines these fields, but the P1 has not yet
# returned them in testing. Treat unverified units/scaling as raw values.
OPTIONAL_SENSORS = (
    _sensor("volt", "General voltage (raw)"),
    _sensor("freq", "Frequency (raw)"),
    _sensor("enMask", "Energy mask (raw)"),
    *(_sensor(f"fact{i}", f"Phase {i} power factor (raw)") for i in (1, 2, 3)),
    _sensor("fact", "Power factor (raw)"),
    *(_sensor(f"ap{i}", f"Phase {i} apparent power (raw)") for i in (1, 2, 3)),
    _sensor("ap", "Apparent power (raw)"),
    *(_sensor(f"rep{i}", f"Phase {i} reactive power (raw)") for i in (1, 2, 3)),
    _sensor("rep", "Reactive power (raw)"),
    *(
        _sensor(f"l2{field}{phase}", f"Secondary {label} phase {phase} (raw)")
        for field, label in (
            ("curr", "current"),
            ("power", "power"),
            ("rep", "reactive power"),
            ("fact", "power factor"),
            ("ap", "apparent power"),
        )
        for phase in (1, 2, 3)
    ),
    *(
        _sensor(f"l2{field}", f"Secondary {label} (raw)")
        for field, label in (
            ("curr", "current"),
            ("power", "power"),
            ("rep", "reactive power"),
            ("freq", "frequency"),
            ("fact", "power factor"),
            ("ap", "apparent power"),
        )
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JackeryP1Coordinator = hass.data[DOMAIN][entry.entry_id]
    # Register all known fields so a later firmware response can populate them.
    # Unreported fields remain unavailable and are disabled in the registry.
    descriptions = (*BASE_SENSORS, *OPTIONAL_SENSORS)
    async_add_entities([*(JackeryP1Sensor(coordinator, entry, desc) for desc in descriptions), P1RSSI(coordinator, entry), P1LastUpdate(coordinator, entry)])


class JackeryP1Sensor(CoordinatorEntity[JackeryP1Coordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: JackeryP1Coordinator, entry: ConfigEntry, description: P1Description
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        field = description.key
        missing = field not in (coordinator.data or {})
        inactive = field.endswith(("2", "3")) and field.startswith(("power", "volt", "curr")) and (coordinator.data or {}).get("volt" + field[-1], 0) == 0
        if missing or inactive:
            self._attr_entity_registry_enabled_default = False
        if missing:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id or entry.entry_id)},
            name="Jackery Smart Meter P1",
            manufacturer="Jackery",
            model="Smart Meter P1 Reader",
        )

    @property
    def available(self) -> bool:
        return super().available and self.entity_description.key in (self.coordinator.data or {})

    @property
    def native_value(self) -> float | None:
        value = (self.coordinator.data or {}).get(self.entity_description.key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return round(value * self.entity_description.multiplier, 3)

class P1RSSI(CoordinatorEntity[JackeryP1Coordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Bluetooth signal strength"
    _attr_native_unit_of_measurement = "dBm"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: JackeryP1Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_bluetooth_rssi"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id or entry.entry_id)})

    @property
    def native_value(self) -> int | None:
        return self.coordinator.rssi()


class P1LastUpdate(CoordinatorEntity[JackeryP1Coordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Last successful update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: JackeryP1Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_last_successful_update"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id or entry.entry_id)})

    @property
    def native_value(self):
        return self.coordinator.last_success
