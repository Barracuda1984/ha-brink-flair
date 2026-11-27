"""Tests for BrinkFlairCoordinator — register parsing and connection logic."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymodbus.exceptions import ModbusException

from custom_components.brink_flair.coordinator import BrinkFlairCoordinator
from tests.conftest import make_fake_client


async def _fetch(hass, input_overrides=None, holding_overrides=None) -> dict:
    """Run one poll cycle against a fake device with the given raw register overrides."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    coord._client = make_fake_client(input_overrides, holding_overrides)
    return await coord._fetch_data()


# ---------------------------------------------------------------------------
# Register parsing tests
# ---------------------------------------------------------------------------


async def test_temperature_signed_positive(hass):
    """Positive temperature: raw 223 → 22.3 °C."""
    data = await _fetch(hass, {4036: 223})
    assert data["supply_temperature"] == pytest.approx(22.3)


async def test_temperature_signed_negative(hass):
    """Negative temperature: raw 65436 (= 65536 - 100) → -10.0 °C."""
    data = await _fetch(hass, {4036: 65536 - 100})
    assert data["supply_temperature"] == pytest.approx(-10.0)


async def test_pressure_negative(hass):
    """Exhaust pressure raw 65525 (= 65536-11) → -11 Pa (signed, no scaling)."""
    data = await _fetch(hass, {4024: 65525})
    assert data["exhaust_pressure"] == pytest.approx(-11.0)


async def test_ventilation_mode_map(hass):
    """Register value 2 maps to 'normal'."""
    data = await _fetch(hass, {4022: 2})
    assert data["ventilation_mode"] == "normal"


async def test_bypass_boost_decoded(hass):
    """Register 6104 = 1 → bypass_boost is True."""
    data = await _fetch(hass, holding_overrides={6104: 1})
    assert data["bypass_boost"] is True


async def test_filter_dirty_decoded(hass):
    """Register 4100 = 1 → filter_dirty is True."""
    data = await _fetch(hass, {4100: 1})
    assert data["filter_dirty"] is True


async def test_operating_time_32bit(hass):
    """Registers 4113 (high) / 4114 (low) combine into one 32-bit value."""
    data = await _fetch(hass, {4113: 1, 4114: 5})
    assert data["operating_time"] == 65536 + 5


async def test_imbalance_signed(hass):
    """Imbalance offsets are signed: raw 65531 → -5 %."""
    data = await _fetch(hass, holding_overrides={6035: 65531, 6036: 3})
    assert data["imbalance_supply"] == -5
    assert data["imbalance_exhaust"] == 3


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(85, 8.5), (65536 - 150, -15.0), (9999, None), (1500, None)],
)
async def test_ntc_not_connected(hass, raw, expected):
    """NTC 9999 (999.9 °C, sensor not fitted) and out-of-range values become None."""
    data = await _fetch(hass, {4081: raw, 4082: raw})
    assert data["outside_temperature"] == expected
    assert data["ntc2_temperature"] == expected


@pytest.mark.parametrize(("raw", "expected"), [(0, None), (45, 45)])
async def test_rht_not_connected(hass, raw, expected):
    """RHT humidity 0 % means no sensor is fitted."""
    data = await _fetch(hass, {4083: raw})
    assert data["rht_humidity"] == expected


@pytest.mark.parametrize(
    ("status", "expected"), [(4, 650), (3, 650), (1, None), (0, None)]
)
async def test_co2_value_depends_on_status(hass, status, expected):
    """CO2 value is None when the sensor is not initialized or in error."""
    data = await _fetch(hass, {4200: status, 4201: 650})
    assert data["co2_sensor_1_value"] == expected


async def test_co2_values_decoded(hass):
    """CO2 sensor values and thresholds are read from 4200.. / 6150.."""
    data = await _fetch(
        hass, {4200: 4, 4201: 650, 4206: 4, 4207: 900}, holding_overrides={6150: 1, 6157: 500, 6158: 1200}
    )
    assert data["co2_sensor_1_value"] == 650
    assert data["co2_sensor_4_value"] == 900
    assert data["co2_mode"] is True
    assert data["co2_sensor_4_low"] == 500
    assert data["co2_sensor_4_high"] == 1200


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
    client = make_fake_client()
    client.write_register = AsyncMock(side_effect=ModbusException("fail"))
    coord._client = client

    # Should not raise — errors are logged and swallowed
    await coord.async_initialize()

    client.close.assert_called_once()
    # The version read afterwards reconnects and still succeeds
    assert client.connect.await_count == 2
    assert coord.sw_version is not None


async def test_initialize_reads_device_version(hass):
    """async_initialize() decodes SW/HW version and serial number."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    coord._client = make_fake_client()

    await coord.async_initialize()

    assert coord.sw_version == "S1.01.03.0001"
    assert coord.hw_version == "H1.1"
    assert coord.serial_number == "123456789012"


# ---------------------------------------------------------------------------
# Write helpers — each must hit the right register with the right raw value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "args", "expected"),
    [
        ("async_set_ventilation_step", (3,), [(8001, 3)]),
        ("async_set_bypass_mode", (2,), [(6100, 2)]),
        ("async_set_bypass_boost", (True,), [(6104, 1)]),
        ("async_set_bypass_boost", (False,), [(6104, 0)]),
        ("async_set_flow_preset", (2, 210), [(6002, 210)]),
        ("async_set_bypass_temp_dwelling", (24.5,), [(6101, 245)]),
        ("async_set_bypass_temp_outside", (12.0,), [(6102, 120)]),
        ("async_set_bypass_hysteresis", (1.5,), [(6103, 15)]),
        ("async_set_frost_control_temp", (1.0,), [(6110, 10)]),
        ("async_set_frost_min_inlet_temp", (15.0,), [(6111, 150)]),
        ("async_set_filter_change_days", (90,), [(6120, 90)]),
        ("async_filter_reset", (), [(8010, 1)]),
        ("async_appliance_reset", (), [(8011, 1)]),
        ("async_set_standby", (True,), [(8003, 1)]),
        ("async_set_standby", (False,), [(8003, 2)]),
        ("async_set_imbalance_supply", (-5,), [(6035, 65531)]),
        ("async_set_imbalance_exhaust", (5,), [(6036, 5)]),
        ("async_set_bypass_boost_position", (3,), [(6105, 3)]),
        ("async_set_co2_mode", (True,), [(6150, 1)]),
        ("async_set_co2_threshold", (3, 450, 1100), [(6155, 450), (6156, 1100)]),
    ],
)
async def test_write_helpers(hass, method, args, expected):
    """Write helpers write the expected raw value to the expected register."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    coord._client = client
    coord.async_request_refresh = AsyncMock()

    await getattr(coord, method)(*args)

    assert [
        (c.kwargs["address"], c.kwargs["value"]) for c in client.write_register.await_args_list
    ] == expected
    assert all(c.kwargs["device_id"] == 20 for c in client.write_register.await_args_list)
    coord.async_request_refresh.assert_awaited()


async def test_write_closes_client_on_error(hass):
    """A failed write closes the connection and re-raises."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    client.write_register = AsyncMock(side_effect=ModbusException("fail"))
    coord._client = client

    with pytest.raises(ModbusException):
        await coord.async_set_ventilation_step(1)

    client.close.assert_called_once()


# ---------------------------------------------------------------------------
# Flow preset validation (Brink "Instelwaarden" 1.1–1.4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("index", "value", "error"),
    [
        (0, 0, None),                              # holiday may be 0
        (0, 50, None),
        (0, 25, "flow_preset_out_of_range"),       # 1–49 rejected
        (1, 0, "flow_preset_out_of_range"),        # only holiday may be 0
        (1, 40, "flow_preset_out_of_range"),
        (3, 405, "flow_preset_out_of_range"),      # above Flair 400 maximum
        (2, 210, None),                            # 150 ≤ 210 ≤ 300
        (2, 140, "flow_preset_order"),             # below low (150)
        (2, 310, "flow_preset_order"),             # above high (300)
        (0, 160, "flow_preset_order"),             # above low (150)
        (3, 400, None),
    ],
)
async def test_flow_preset_validation(hass, index, value, error):
    """Out-of-range or out-of-order presets raise before anything is written."""
    from homeassistant.exceptions import ServiceValidationError

    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    coord._client = client
    coord.async_request_refresh = AsyncMock()
    coord.data = await coord._fetch_data()   # presets 75 / 150 / 200 / 300

    if error is None:
        await coord.async_set_flow_preset(index, value)
        client.write_register.assert_awaited_once()
    else:
        with pytest.raises(ServiceValidationError) as exc:
            await coord.async_set_flow_preset(index, value)
        assert exc.value.translation_key == error
        client.write_register.assert_not_awaited()
