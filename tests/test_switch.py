"""Tests for the Brink Flair switch platform (Standby, Bypass Boost)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.brink_flair.const import DOMAIN
from tests.conftest import COORDINATOR_DATA, ENTRY_DATA


@pytest.fixture(autouse=True)
def _patch_modbus(mock_modbus_client):
    """Activate the shared mock Modbus client for all tests in this module."""
    with patch(
        "custom_components.brink_flair.coordinator.AsyncModbusSerialClient",
        return_value=mock_modbus_client,
    ):
        yield


async def _setup_integration(hass: HomeAssistant) -> MockConfigEntry:
    """Load the integration into hass and return the config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        unique_id=f"{ENTRY_DATA['serial_port']}_{ENTRY_DATA['slave_id']}",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


# ---------------------------------------------------------------------------
# is_on reflects coordinator data
# ---------------------------------------------------------------------------


async def test_standby_is_off_when_data_is_false(hass):
    """Standby switch is OFF when coordinator data['standby'] is False."""
    await _setup_integration(hass)

    state = hass.states.get("switch.brink_flair_400_standby")
    assert state is not None
    assert state.state == STATE_OFF


async def test_bypass_boost_is_off_when_data_is_false(hass):
    """Bypass boost switch is OFF when coordinator data['bypass_boost'] is False."""
    await _setup_integration(hass)

    state = hass.states.get("switch.brink_flair_400_bypass_boost")
    assert state is not None
    assert state.state == STATE_OFF


# ---------------------------------------------------------------------------
# turn_on / turn_off delegate to coordinator
# ---------------------------------------------------------------------------


async def test_standby_turn_on_calls_coordinator(hass):
    """Turning standby on calls coordinator.async_set_standby(True)."""
    entry = await _setup_integration(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_standby = AsyncMock()

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.brink_flair_400_standby"},
        blocking=True,
    )

    coordinator.async_set_standby.assert_awaited_once_with(True)


async def test_standby_turn_off_calls_coordinator(hass):
    """Turning standby off calls coordinator.async_set_standby(False)."""
    entry = await _setup_integration(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_standby = AsyncMock()

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.brink_flair_400_standby"},
        blocking=True,
    )

    coordinator.async_set_standby.assert_awaited_once_with(False)


async def test_bypass_boost_turn_on_calls_coordinator(hass):
    """Turning bypass boost on calls coordinator.async_set_bypass_boost(True)."""
    entry = await _setup_integration(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_bypass_boost = AsyncMock()

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.brink_flair_400_bypass_boost"},
        blocking=True,
    )

    coordinator.async_set_bypass_boost.assert_awaited_once_with(True)


async def test_bypass_boost_turn_off_calls_coordinator(hass):
    """Turning bypass boost off calls coordinator.async_set_bypass_boost(False)."""
    entry = await _setup_integration(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_set_bypass_boost = AsyncMock()

    await hass.services.async_call(
        "switch",
        "turn_off",
        {"entity_id": "switch.brink_flair_400_bypass_boost"},
        blocking=True,
    )

    coordinator.async_set_bypass_boost.assert_awaited_once_with(False)
