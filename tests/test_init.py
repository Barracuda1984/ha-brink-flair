"""Tests for config entry setup and unload."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


async def test_setup_does_not_write_to_unit(
    hass: HomeAssistant, mock_modbus_client, config_entry
):
    """Setting up the entry only reads — register 8000 stays as the unit left it."""
    mock_modbus_client.holding_registers[8000] = 0
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    mock_modbus_client.write_register.assert_not_awaited()
    assert mock_modbus_client.holding_registers[8000] == 0


async def test_unload_hands_control_back(
    hass: HomeAssistant, mock_modbus_client, config_entry
):
    """Unloading writes 8000 = 0 when the unit is under Modbus switch control."""
    mock_modbus_client.holding_registers[8000] = 1
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
    assert mock_modbus_client.holding_registers[8000] == 0
    mock_modbus_client.close.assert_called()
