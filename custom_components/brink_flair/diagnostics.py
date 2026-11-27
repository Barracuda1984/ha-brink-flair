"""Diagnostics support for Brink Flair.

Downloadable from the device page in Home Assistant. Read-only: it reports the
connection settings, firmware/hardware versions and the last polled values, so
users can attach it to bug and model-compatibility reports.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import BrinkFlairCoordinator

TO_REDACT = {"serial_number"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: BrinkFlairCoordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
        },
        "device": async_redact_data(
            {
                "sw_version": coordinator.sw_version,
                "hw_version": coordinator.hw_version,
                "serial_number": coordinator.serial_number,
            },
            TO_REDACT,
        ),
        "last_update_success": coordinator.last_update_success,
        "data": coordinator.data,
    }
