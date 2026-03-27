"""Brink Flair integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_BAUD_RATE, CONF_SERIAL_PORT, CONF_SLAVE_ID, DOMAIN
from .coordinator import BrinkFlairCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Brink Flair from a config entry."""
    coordinator = BrinkFlairCoordinator(
        hass,
        serial_port=entry.data[CONF_SERIAL_PORT],
        baud_rate=entry.data[CONF_BAUD_RATE],
        slave_id=entry.data[CONF_SLAVE_ID],
    )
    # Enable Modbus switch-control mode before the first data fetch.
    # The device resets this on power loss so we must do it every startup.
    await coordinator.async_initialize()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: BrinkFlairCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok
