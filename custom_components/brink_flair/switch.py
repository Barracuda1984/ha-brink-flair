"""Switch platform for Brink Flair — standby and bypass boost."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BrinkFlairCoordinator


@dataclass(frozen=True, kw_only=True)
class BrinkFlairSwitchEntityDescription(SwitchEntityDescription):
    """Extends SwitchEntityDescription with coordinator read/write callables."""

    is_on_fn: Any   # Callable[[dict[str, Any]], bool | None]
    turn_on_fn: Any  # Callable[[BrinkFlairCoordinator], Coroutine]
    turn_off_fn: Any  # Callable[[BrinkFlairCoordinator], Coroutine]


SWITCH_DESCRIPTIONS: tuple[BrinkFlairSwitchEntityDescription, ...] = (
    BrinkFlairSwitchEntityDescription(
        key="standby",
        name="Standby",
        icon="mdi:power-sleep",
        is_on_fn=lambda d: d.get("standby"),
        turn_on_fn=lambda c: c.async_set_standby(True),
        turn_off_fn=lambda c: c.async_set_standby(False),
    ),
    BrinkFlairSwitchEntityDescription(
        key="bypass_boost",
        name="Bypass Boost",
        icon="mdi:valve-open",
        is_on_fn=lambda d: d.get("bypass_boost"),
        turn_on_fn=lambda c: c.async_set_bypass_boost(True),
        turn_off_fn=lambda c: c.async_set_bypass_boost(False),
    ),
    BrinkFlairSwitchEntityDescription(
        key="co2_mode",
        name="CO2 Control Mode",
        icon="mdi:molecule-co2",
        is_on_fn=lambda d: d.get("co2_mode"),
        turn_on_fn=lambda c: c.async_set_co2_mode(True),
        turn_off_fn=lambda c: c.async_set_co2_mode(False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Brink Flair switch entities."""
    coordinator: BrinkFlairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BrinkFlairSwitchEntity(coordinator, description)
        for description in SWITCH_DESCRIPTIONS
    )


class BrinkFlairSwitchEntity(
    CoordinatorEntity[BrinkFlairCoordinator], SwitchEntity
):
    """Represents a toggleable setting on the Brink Flair 400."""

    entity_description: BrinkFlairSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.serial_port}_{coordinator.slave_id}_{description.key}"
        )
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.coordinator.data or {})

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.entity_description.turn_on_fn(self.coordinator)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.entity_description.turn_off_fn(self.coordinator)
