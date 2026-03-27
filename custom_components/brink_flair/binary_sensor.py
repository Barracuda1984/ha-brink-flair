"""Binary sensor platform for Brink Flair."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BrinkFlairCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Brink Flair binary sensors."""
    coordinator: BrinkFlairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FilterDirtyBinarySensor(coordinator)])


class FilterDirtyBinarySensor(
    CoordinatorEntity[BrinkFlairCoordinator], BinarySensorEntity
):
    """Reports whether the filter needs replacing (register 4100)."""

    _attr_has_entity_name = True
    _attr_name = "Filter Dirty"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: BrinkFlairCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.serial_port}_{coordinator.slave_id}_filter_dirty"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.serial_port}_{coordinator.slave_id}")},
            name="Brink Flair 400",
            manufacturer="Brink",
            model="Flair 400",
        )

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("filter_dirty")
