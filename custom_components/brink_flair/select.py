"""Select platform for Brink Flair — ventilation mode and bypass mode."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BYPASS_MODE_OPTIONS,
    DOMAIN,
    VENTILATION_STEP_OPTIONS,
)
from .coordinator import BrinkFlairCoordinator


@dataclass(frozen=True, kw_only=True)
class BrinkFlairSelectEntityDescription(SelectEntityDescription):
    """Extends SelectEntityDescription with coordinator read/write callables."""

    current_fn: Any  # Callable[[dict], str | None]
    set_fn: Any      # Callable[[BrinkFlairCoordinator, str], Coroutine]


def _vent_step_current(data: dict[str, Any]) -> str | None:
    """Map the ventilation step register value (0–3) to an option string."""
    step = data.get("ventilation_step")
    if step is None or step >= len(VENTILATION_STEP_OPTIONS):
        return None
    return VENTILATION_STEP_OPTIONS[step]


async def _vent_step_set(coordinator: BrinkFlairCoordinator, option: str) -> None:
    await coordinator.async_set_ventilation_step(VENTILATION_STEP_OPTIONS.index(option))


def _bypass_mode_current(data: dict[str, Any]) -> str | None:
    """Map the bypass mode register value (0–2) to an option string."""
    mode = data.get("bypass_mode")
    if mode is None or mode >= len(BYPASS_MODE_OPTIONS):
        return None
    return BYPASS_MODE_OPTIONS[mode]


async def _bypass_mode_set(coordinator: BrinkFlairCoordinator, option: str) -> None:
    await coordinator.async_set_bypass_mode(BYPASS_MODE_OPTIONS.index(option))


SELECT_DESCRIPTIONS: tuple[BrinkFlairSelectEntityDescription, ...] = (
    BrinkFlairSelectEntityDescription(
        key="ventilation_step",
        name="Ventilation Mode",
        icon="mdi:fan",
        options=VENTILATION_STEP_OPTIONS,
        current_fn=_vent_step_current,
        set_fn=_vent_step_set,
    ),
    BrinkFlairSelectEntityDescription(
        key="bypass_mode",
        name="Bypass Mode",
        icon="mdi:valve",
        options=BYPASS_MODE_OPTIONS,
        current_fn=_bypass_mode_current,
        set_fn=_bypass_mode_set,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Brink Flair select entities."""
    coordinator: BrinkFlairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BrinkFlairSelectEntity(coordinator, description)
        for description in SELECT_DESCRIPTIONS
    )


class BrinkFlairSelectEntity(
    CoordinatorEntity[BrinkFlairCoordinator], SelectEntity
):
    """Represents a selectable setting on the Brink Flair 400."""

    entity_description: BrinkFlairSelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairSelectEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.serial_port}_{coordinator.slave_id}_{description.key}"
        )
        self._attr_options = description.options
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.serial_port}_{coordinator.slave_id}")},
            name="Brink Flair 400",
            manufacturer="Brink",
            model="Flair 400",
        )

    @property
    def current_option(self) -> str | None:
        return self.entity_description.current_fn(self.coordinator.data or {})

    async def async_select_option(self, option: str) -> None:
        await self.entity_description.set_fn(self.coordinator, option)
