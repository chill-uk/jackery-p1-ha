"""Local Jackery P1 sensors; preserve raw sign on power fields."""
from dataclasses import dataclass
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
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

def _sensor(key: str, name: str, unit: str, device_class: SensorDeviceClass, multiplier: float = 1.0) -> P1Description:
    return P1Description(key=key, name=name, native_unit_of_measurement=unit, device_class=device_class, state_class=SensorStateClass.MEASUREMENT, multiplier=multiplier)

SENSORS = (
    _sensor("power", "Total power (raw sign)", "W", SensorDeviceClass.POWER),
    *(_sensor(f"power{i}", f"Phase {i} power (raw sign)", "W", SensorDeviceClass.POWER) for i in (1, 2, 3)),
    *(_sensor(f"volt{i}", f"Phase {i} voltage", "V", SensorDeviceClass.VOLTAGE) for i in (1, 2, 3)),
    _sensor("curr", "Total current", "A", SensorDeviceClass.CURRENT, 0.1),
    *(_sensor(f"curr{i}", f"Phase {i} current", "A", SensorDeviceClass.CURRENT, 0.1) for i in (1, 2, 3)),
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(JackeryP1Sensor(coordinator, entry, desc) for desc in SENSORS)

class JackeryP1Sensor(CoordinatorEntity[JackeryP1Coordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: JackeryP1Coordinator, entry: ConfigEntry, description: P1Description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id or entry.entry_id)}, name="Jackery Smart Meter P1", manufacturer="Jackery", model="Smart Meter P1 Reader")

    @property
    def native_value(self) -> float | None:
        value = self.coordinator.data.get(self.entity_description.key) if self.coordinator.data else None
        return round(value * self.entity_description.multiplier, 3) if isinstance(value, (int, float)) else None
