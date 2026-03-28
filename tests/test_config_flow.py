"""Tests for the Brink Flair config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymodbus.exceptions import ModbusException

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.brink_flair.const import DOMAIN

ENTRY_DATA = {
    "serial_port": "/dev/ttyUSB0",
    "baud_rate": 19200,
    "slave_id": 20,
}


def _mock_client(*, connect_raises=None, read_raises=None, read_is_error=False):
    """Build a mock AsyncModbusSerialClient for config flow tests."""
    client = MagicMock()

    if connect_raises:
        client.connect = AsyncMock(side_effect=connect_raises)
    else:
        async def fake_connect():
            client.connected = True
        client.connect = AsyncMock(side_effect=fake_connect)

    if read_raises:
        client.read_input_registers = AsyncMock(side_effect=read_raises)
    else:
        result = MagicMock()
        result.isError.return_value = read_is_error
        result.registers = [12]
        client.read_input_registers = AsyncMock(return_value=result)

    client.close = MagicMock()
    return client


@pytest.fixture(autouse=True)
def _no_setup(hass):
    """Prevent the integration from actually being set up during flow tests."""
    with patch(
        "custom_components.brink_flair.async_setup_entry", return_value=True
    ):
        yield


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_form_shows_on_first_step(hass):
    """Opening the flow without data should display the user form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_setup_creates_entry(hass):
    """Valid credentials → config entry created."""
    client = _mock_client()

    with patch(
        "custom_components.brink_flair.config_flow.AsyncModbusSerialClient",
        return_value=client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=ENTRY_DATA
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Brink Flair 400 (/dev/ttyUSB0)"
    assert result["data"] == ENTRY_DATA
    client.close.assert_called_once()


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


async def test_cannot_connect_on_modbus_exception(hass):
    """ModbusException during connection test → 'cannot_connect' error."""
    client = _mock_client(connect_raises=ModbusException("no serial port"))

    with patch(
        "custom_components.brink_flair.config_flow.AsyncModbusSerialClient",
        return_value=client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=ENTRY_DATA
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_unknown_error_on_generic_exception(hass):
    """An unexpected exception → 'unknown' error, flow stays on form."""
    client = _mock_client(connect_raises=RuntimeError("boom"))

    with patch(
        "custom_components.brink_flair.config_flow.AsyncModbusSerialClient",
        return_value=client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=ENTRY_DATA
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_device_error_response_is_cannot_connect(hass):
    """Device returning an error response → 'cannot_connect'."""
    client = _mock_client(read_is_error=True)

    with patch(
        "custom_components.brink_flair.config_flow.AsyncModbusSerialClient",
        return_value=client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=ENTRY_DATA
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_entry_aborts(hass):
    """Attempting to configure the same port+slave again is aborted."""
    client = _mock_client()

    with patch(
        "custom_components.brink_flair.config_flow.AsyncModbusSerialClient",
        return_value=client,
    ):
        # First setup — succeeds
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=ENTRY_DATA
        )

        # Second attempt with identical data
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input=ENTRY_DATA
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
