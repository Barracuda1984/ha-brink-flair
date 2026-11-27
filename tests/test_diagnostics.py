"""Tests for Brink Flair diagnostics."""
from __future__ import annotations

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant

from custom_components.brink_flair.diagnostics import (
    async_get_config_entry_diagnostics,
)
from tests.conftest import ENTRY_DATA


async def test_diagnostics(hass: HomeAssistant, mock_modbus_client, config_entry):
    """Diagnostics contain settings, versions and data, with the serial redacted."""
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diag["entry"]["data"] == ENTRY_DATA
    assert diag["device"]["serial_number"] == REDACTED
    assert diag["device"]["sw_version"] is not None
    assert diag["last_update_success"] is True
    assert diag["data"]["ventilation_mode"] == "normal"
    assert diag["data"]["flow_preset_2"] == 200
