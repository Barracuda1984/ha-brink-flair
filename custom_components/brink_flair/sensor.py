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
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BrinkFlairCoordinator


@dataclass(frozen=True, kw_only=True)
class BrinkFlairSensorEntityDescription(SensorEntityDescription):
    """Describes a Brink Flair sensor."""

    value_fn: callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[BrinkFlairSensorEntityDescription, ...] = (
    BrinkFlairSensorEntityDescription(
        key="supply_temperature",
        name="Supply Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data.get("supply_temperature"),
    ),
    # TODO: add more sensors based on available device data
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Brink Flair sensors from a config entry."""
    coordinator: BrinkFlairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BrinkFlairSensorEntity(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class BrinkFlairSensorEntity(CoordinatorEntity[BrinkFlairCoordinator], SensorEntity):
    """Represents a Brink Flair sensor."""

    entity_description: BrinkFlairSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.host}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.host)},
            name="Brink Flair",
            manufacturer="Brink",
            model="Flair",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data or {})
