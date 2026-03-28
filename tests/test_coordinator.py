"""Tests for BrinkFlairCoordinator — register parsing and connection logic."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymodbus.exceptions import ModbusException

from custom_components.brink_flair.coordinator import BrinkFlairCoordinator


@pytest.fixture
def coordinator(hass):
    """Return a coordinator wired to the mock Modbus client."""
    return BrinkFlairCoordinator(
        hass,
        serial_port="/dev/ttyUSB0",
        baud_rate=19200,
        slave_id=20,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg(*values: int) -> MagicMock:
    r = MagicMock()
    r.isError.return_value = False
    r.registers = list(values)
    return r


def _patch_client(coordinator: BrinkFlairCoordinator, client: MagicMock) -> None:
    coordinator._client = client


# ---------------------------------------------------------------------------
# Register parsing tests
# ---------------------------------------------------------------------------


async def test_temperature_signed_positive(hass):
    """Positive temperature: raw 223 → 22.3 °C."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    # Patch client directly
    client = MagicMock()
    client.connected = True
    client.read_input_registers = AsyncMock(
        side_effect=[
            _reg(12, 0, 2, 125, 65426),   # b1
            _reg(200, 198, 0, 1450, 0, 223, 450),  # b2 — supply_temperature=22.3
            _reg(200, 195, 0, 1420, 0, 201, 500),  # b3
            _reg(4),   # bypass
            _reg(2, 0, 0),  # frost
            _reg(85),  # outside temp
            _reg(0),   # filter status
            _reg(720), # filter hours
        ]
    )
    client.read_holding_registers = AsyncMock(
        side_effect=[
            _reg(75, 150, 200, 300),     # presets
            _reg(0, 240, 120, 20, 0),    # bypass cfg
            _reg(10, 150),               # frost cfg
            _reg(180),                   # filter days
            _reg(1, 2, 200, 0),          # ctrl
        ]
    )
    coord._client = client

    data = await coord._fetch_data()

    assert data["supply_temperature"] == pytest.approx(22.3)


async def test_temperature_signed_negative(hass):
    """Negative temperature: raw 65436 (= 65536 - 100) → -10.0 °C."""
    raw = 65536 - 100  # -10.0 °C in signed 16-bit tenths
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = True
    client.read_input_registers = AsyncMock(
        side_effect=[
            _reg(12, 0, 2, 125, 65426),
            _reg(200, 198, 0, 1450, 0, raw, 450),  # supply_temperature = -10.0
            _reg(200, 195, 0, 1420, 0, 201, 500),
            _reg(4),
            _reg(2, 0, 0),
            _reg(85),
            _reg(0),
            _reg(720),
        ]
    )
    client.read_holding_registers = AsyncMock(
        side_effect=[
            _reg(75, 150, 200, 300),
            _reg(0, 240, 120, 20, 0),
            _reg(10, 150),
            _reg(180),
            _reg(1, 2, 200, 0),
        ]
    )
    coord._client = client

    data = await coord._fetch_data()

    assert data["supply_temperature"] == pytest.approx(-10.0)


async def test_pressure_negative(hass):
    """Exhaust pressure raw 65525 (= 65536-11) → -11 Pa (signed, no scaling)."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = True
    client.read_input_registers = AsyncMock(
        side_effect=[
            _reg(12, 0, 2, 125, 65525),  # exhaust_pressure raw=65525 → -11 Pa
            _reg(200, 198, 0, 1450, 0, 223, 450),
            _reg(200, 195, 0, 1420, 0, 201, 500),
            _reg(4),
            _reg(2, 0, 0),
            _reg(85),
            _reg(0),
            _reg(720),
        ]
    )
    client.read_holding_registers = AsyncMock(
        side_effect=[
            _reg(75, 150, 200, 300),
            _reg(0, 240, 120, 20, 0),
            _reg(10, 150),
            _reg(180),
            _reg(1, 2, 200, 0),
        ]
    )
    coord._client = client

    data = await coord._fetch_data()

    assert data["exhaust_pressure"] == pytest.approx(-11.0)


async def test_ventilation_mode_map(hass):
    """Register value 2 maps to 'normal'."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = True
    client.read_input_registers = AsyncMock(
        side_effect=[
            _reg(12, 0, 2, 125, 65426),  # ventilation_mode raw=2
            _reg(200, 198, 0, 1450, 0, 223, 450),
            _reg(200, 195, 0, 1420, 0, 201, 500),
            _reg(4),
            _reg(2, 0, 0),
            _reg(85),
            _reg(0),
            _reg(720),
        ]
    )
    client.read_holding_registers = AsyncMock(
        side_effect=[
            _reg(75, 150, 200, 300),
            _reg(0, 240, 120, 20, 0),
            _reg(10, 150),
            _reg(180),
            _reg(1, 2, 200, 0),
        ]
    )
    coord._client = client

    data = await coord._fetch_data()

    assert data["ventilation_mode"] == "normal"


async def test_bypass_boost_decoded(hass):
    """Register 6104 = 1 → bypass_boost is True."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = True
    client.read_input_registers = AsyncMock(
        side_effect=[
            _reg(12, 0, 2, 125, 65426),
            _reg(200, 198, 0, 1450, 0, 223, 450),
            _reg(200, 195, 0, 1420, 0, 201, 500),
            _reg(4),
            _reg(2, 0, 0),
            _reg(85),
            _reg(0),
            _reg(720),
        ]
    )
    client.read_holding_registers = AsyncMock(
        side_effect=[
            _reg(75, 150, 200, 300),
            _reg(0, 240, 120, 20, 1),   # bypass_boost = 1
            _reg(10, 150),
            _reg(180),
            _reg(1, 2, 200, 0),
        ]
    )
    coord._client = client

    data = await coord._fetch_data()

    assert data["bypass_boost"] is True


async def test_filter_dirty_decoded(hass):
    """Register 4100 = 1 → filter_dirty is True."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = True
    client.read_input_registers = AsyncMock(
        side_effect=[
            _reg(12, 0, 2, 125, 65426),
            _reg(200, 198, 0, 1450, 0, 223, 450),
            _reg(200, 195, 0, 1420, 0, 201, 500),
            _reg(4),
            _reg(2, 0, 0),
            _reg(85),
            _reg(1),   # filter dirty!
            _reg(720),
        ]
    )
    client.read_holding_registers = AsyncMock(
        side_effect=[
            _reg(75, 150, 200, 300),
            _reg(0, 240, 120, 20, 0),
            _reg(10, 150),
            _reg(180),
            _reg(1, 2, 200, 0),
        ]
    )
    coord._client = client

    data = await coord._fetch_data()

    assert data["filter_dirty"] is True


# ---------------------------------------------------------------------------
# Connection management tests
# ---------------------------------------------------------------------------


async def test_ensure_connected_calls_connect_when_disconnected(hass):
    """_ensure_connected() must call client.connect() when not connected."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = False
    client.connect = AsyncMock(side_effect=lambda: setattr(client, "connected", True))
    coord._client = client

    await coord._ensure_connected()

    client.connect.assert_awaited_once()
    assert client.connected is True


async def test_ensure_connected_skips_when_already_connected(hass):
    """_ensure_connected() must NOT call connect() when already connected."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = True
    client.connect = AsyncMock()
    coord._client = client

    await coord._ensure_connected()

    client.connect.assert_not_awaited()


async def test_fetch_data_closes_client_on_modbus_error(hass):
    """On ModbusException during polling the client must be closed."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = True
    client.read_input_registers = AsyncMock(
        side_effect=ModbusException("simulated error")
    )
    client.close = MagicMock()
    coord._client = client

    with pytest.raises(ModbusException):
        await coord._fetch_data()

    client.close.assert_called_once()


async def test_initialize_writes_modbus_control_register(hass):
    """async_initialize() must write 1 to register 8000."""
    from custom_components.brink_flair.const import REG_RC_MODBUS_CONTROL

    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = False
    client.connect = AsyncMock(side_effect=lambda: setattr(client, "connected", True))
    client.write_register = AsyncMock(
        return_value=MagicMock(isError=lambda: False)
    )
    coord._client = client

    await coord.async_initialize()

    client.write_register.assert_awaited_once_with(
        address=REG_RC_MODBUS_CONTROL, value=1, device_id=20
    )


async def test_initialize_closes_on_modbus_error(hass):
    """async_initialize() closes the connection on ModbusException (non-fatal)."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = MagicMock()
    client.connected = False
    client.connect = AsyncMock(side_effect=lambda: setattr(client, "connected", True))
    client.write_register = AsyncMock(side_effect=ModbusException("fail"))
    client.close = MagicMock()
    coord._client = client

    # Should not raise — errors are logged and swallowed
    await coord.async_initialize()

    client.close.assert_called_once()
