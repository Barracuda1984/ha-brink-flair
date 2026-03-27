"""Sensor platform for Brink Flair."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BrinkFlairCoordinator

try:
    from homeassistant.const import UnitOfRotationalSpeed
    _RPM = UnitOfRotationalSpeed.REVOLUTIONS_PER_MINUTE
except ImportError:
    _RPM = "RPM"


@dataclass(frozen=True, kw_only=True)
class BrinkFlairSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with a value extractor."""

    value_fn: Any  # Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[BrinkFlairSensorEntityDescription, ...] = (
    # ── Temperatures ──────────────────────────────────────────────────
    BrinkFlairSensorEntityDescription(
        key="supply_temperature",
        name="Temperature to Inside",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("supply_temperature"),
    ),
    BrinkFlairSensorEntityDescription(
        key="exhaust_temperature",
        name="Temperature to Outside",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("exhaust_temperature"),
    ),
    BrinkFlairSensorEntityDescription(
        key="outside_temperature",
        name="Temperature from Outside",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("outside_temperature"),
    ),
    # ── Humidity ──────────────────────────────────────────────────────
    BrinkFlairSensorEntityDescription(
        key="supply_humidity",
        name="Humidity to Inside",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("supply_humidity"),
    ),
    BrinkFlairSensorEntityDescription(
        key="exhaust_humidity",
        name="Humidity to Outside",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("exhaust_humidity"),
    ),
    # ── Air flow ──────────────────────────────────────────────────────
    BrinkFlairSensorEntityDescription(
        key="supply_flow",
        name="Current Intake Air Volume",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        value_fn=lambda d: d.get("supply_flow"),
    ),
    BrinkFlairSensorEntityDescription(
        key="supply_setpoint",
        name="Setpoint Intake Air Volume",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        value_fn=lambda d: d.get("supply_setpoint"),
    ),
    BrinkFlairSensorEntityDescription(
        key="exhaust_flow",
        name="Current Exhaust Air Volume",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        value_fn=lambda d: d.get("exhaust_flow"),
    ),
    BrinkFlairSensorEntityDescription(
        key="exhaust_setpoint",
        name="Setpoint Exhaust Air Volume",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        value_fn=lambda d: d.get("exhaust_setpoint"),
    ),
    # ── Fan speed ─────────────────────────────────────────────────────
    BrinkFlairSensorEntityDescription(
        key="supply_fan_rpm",
        name="Speed Supply Fan",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=_RPM,
        value_fn=lambda d: d.get("supply_fan_rpm"),
    ),
    BrinkFlairSensorEntityDescription(
        key="exhaust_fan_rpm",
        name="Speed Exhaust Fan",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=_RPM,
        value_fn=lambda d: d.get("exhaust_fan_rpm"),
    ),
    # ── Pressure ──────────────────────────────────────────────────────
    BrinkFlairSensorEntityDescription(
        key="supply_pressure",
        name="Supply Pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.PA,
        value_fn=lambda d: d.get("supply_pressure"),
    ),
    BrinkFlairSensorEntityDescription(
        key="exhaust_pressure",
        name="Exhaust Pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.PA,
        value_fn=lambda d: d.get("exhaust_pressure"),
    ),
    # ── Frost ─────────────────────────────────────────────────────────
    BrinkFlairSensorEntityDescription(
        key="frost_heater_power",
        name="Frost Heater Power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("frost_heater_power"),
    ),
    BrinkFlairSensorEntityDescription(
        key="frost_fan_reduction",
        name="Frost Fan Reduction",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.get("frost_fan_reduction"),
    ),
    # ── Filter ────────────────────────────────────────────────────────
    BrinkFlairSensorEntityDescription(
        key="filter_hours",
        name="Current Filter Hours",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="h",
        value_fn=lambda d: d.get("filter_hours"),
    ),
    # ── Status (text) ─────────────────────────────────────────────────
    BrinkFlairSensorEntityDescription(
        key="active_function",
        name="Status",
        value_fn=lambda d: d.get("active_function"),
    ),
    BrinkFlairSensorEntityDescription(
        key="ventilation_mode",
        name="Ventilation Mode",
        value_fn=lambda d: d.get("ventilation_mode"),
    ),
    BrinkFlairSensorEntityDescription(
        key="bypass_status",
        name="Bypass Status",
        value_fn=lambda d: d.get("bypass_status"),
    ),
    BrinkFlairSensorEntityDescription(
        key="frost_status",
        name="Frost Status",
        value_fn=lambda d: d.get("frost_status"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Brink Flair sensors."""
    coordinator: BrinkFlairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BrinkFlairSensorEntity(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class BrinkFlairSensorEntity(CoordinatorEntity[BrinkFlairCoordinator], SensorEntity):
    """A single Brink Flair sensor."""

    entity_description: BrinkFlairSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.serial_port}_{coordinator.slave_id}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.serial_port}_{coordinator.slave_id}")},
            name="Brink Flair 400",
            manufacturer="Brink",
            model="Flair 400",
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})
