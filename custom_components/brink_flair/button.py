"""Button platform for Brink Flair — filter reset and appliance reset."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BrinkFlairCoordinator


@dataclass(frozen=True, kw_only=True)
class BrinkFlairButtonEntityDescription(ButtonEntityDescription):
    """Extends ButtonEntityDescription with a press action callable."""

    press_fn: Any  # Callable[[BrinkFlairCoordinator], Coroutine]


BUTTON_DESCRIPTIONS: tuple[BrinkFlairButtonEntityDescription, ...] = (
    BrinkFlairButtonEntityDescription(
        key="filter_reset",
        name="Filter Reset",
        icon="mdi:air-filter",
        press_fn=lambda c: c.async_filter_reset(),
    ),
    BrinkFlairButtonEntityDescription(
        key="appliance_reset",
        name="Appliance Reset",
        icon="mdi:restart",
        entity_registry_enabled_default=False,
        press_fn=lambda c: c.async_appliance_reset(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Brink Flair button entities."""
    coordinator: BrinkFlairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BrinkFlairButtonEntity(coordinator, description)
        for description in BUTTON_DESCRIPTIONS
    )


class BrinkFlairButtonEntity(
    CoordinatorEntity[BrinkFlairCoordinator], ButtonEntity
):
    """A pushbutton that triggers a one-shot command on the Brink Flair 400."""

    entity_description: BrinkFlairButtonEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairButtonEntityDescription,
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

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self.coordinator)
