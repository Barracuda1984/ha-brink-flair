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


async def test_initialize_writes_nothing(hass):
    """async_initialize() is read-only — setup must not write to the unit."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client(holding_overrides={8000: 0})
    coord._client = client

    await coord.async_initialize()

    client.write_register.assert_not_awaited()
    assert client.holding_registers[8000] == 0


async def test_initialize_closes_on_read_error(hass):
    """A failed version read closes the connection and is not fatal."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    client.read_input_registers = AsyncMock(side_effect=ModbusException("fail"))
    coord._client = client

    await coord.async_initialize()

    client.close.assert_called_once()
    assert coord.sw_version is None


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


# ---------------------------------------------------------------------------
# Modbus control (8000) is taken on demand and handed back on unload
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "args", "command"),
    [
        ("async_set_ventilation_step", (3,), (8001, 3)),
        ("async_set_standby", (True,), (8003, 1)),
    ],
)
@pytest.mark.parametrize(
    ("mode", "takes_control"),
    [("device_lcd", True), ("modbus_switch", False), ("modbus_flow", False)],
)
async def test_modbus_control_taken_only_when_needed(
    hass, method, args, command, mode, takes_control
):
    """8000 = 1 is written right before the command, only in device LCD mode."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    coord._client = client
    coord.async_request_refresh = AsyncMock()
    coord.data = {"modbus_control_mode": mode}

    await getattr(coord, method)(*args)

    writes = [
        (c.kwargs["address"], c.kwargs["value"]) for c in client.write_register.await_args_list
    ]
    assert writes == ([(8000, 1)] if takes_control else []) + [command]


@pytest.mark.parametrize(
    "method", ["async_set_bypass_mode", "async_set_filter_change_days", "async_filter_reset"]
)
async def test_settings_writes_do_not_take_modbus_control(hass, method):
    """Writes that do not need Modbus control leave register 8000 alone."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    coord._client = client
    coord.async_request_refresh = AsyncMock()
    coord.data = {"modbus_control_mode": "device_lcd"}

    await getattr(coord, method)(*(() if method == "async_filter_reset" else (1,)))

    assert 8000 not in [c.kwargs["address"] for c in client.write_register.await_args_list]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [("modbus_switch", [(8000, 0)]), ("device_lcd", []), ("modbus_flow", [])],
)
async def test_release_modbus_control(hass, mode, expected):
    """Unloading hands control back (8000 = 0) only if the unit is in Modbus switch mode."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    coord._client = client
    coord.data = {"modbus_control_mode": mode}

    await coord.async_release_modbus_control()

    assert [
        (c.kwargs["address"], c.kwargs["value"]) for c in client.write_register.await_args_list
    ] == expected


async def test_release_modbus_control_error_is_not_fatal(hass):
    """A failed hand-back is logged, not raised, so unloading still succeeds."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    client.write_register = AsyncMock(side_effect=ModbusException("fail"))
    coord._client = client
    coord.data = {"modbus_control_mode": "modbus_switch"}

    await coord.async_release_modbus_control()

    client.close.assert_called_once()


def _writes(client) -> list[tuple[int, int]]:
    return [
        (c.kwargs["address"], c.kwargs["value"]) for c in client.write_register.await_args_list
    ]


async def _take_control_and_command(hass, method, args, monkeypatch):
    """Send a command that takes control; return (coordinator, client, clock)."""
    clock = [1000.0]
    monkeypatch.setattr(
        "custom_components.brink_flair.coordinator.time.monotonic", lambda: clock[0]
    )
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    coord._client = client
    coord.async_request_refresh = AsyncMock()
    coord.data = {"modbus_control_mode": "device_lcd"}
    await getattr(coord, method)(*args)
    return coord, client, clock


@pytest.mark.parametrize(
    ("method", "args", "command", "ignored", "applied"),
    [
        (
            "async_set_ventilation_step", (2,), (8001, 2),
            {"ventilation_mode": "high"}, {"ventilation_mode": "normal"},
        ),
        (
            "async_set_standby", (True,), (8003, 1),
            {"active_function": "auto_modbus"}, {"active_function": "standby"},
        ),
    ],
)
async def test_ignored_command_is_resent_once(
    hass, monkeypatch, method, args, command, ignored, applied
):
    """A command the unit ignores after taking control is resent on a later poll."""
    coord, client, clock = await _take_control_and_command(hass, method, args, monkeypatch)
    assert _writes(client) == [(8000, 1), command]

    # The refresh right after the write is too early to judge.
    clock[0] += 1
    await coord._async_verify_pending(ignored)
    assert _writes(client) == [(8000, 1), command]

    # A later poll still shows the old state -> resend once.
    clock[0] += 30
    await coord._async_verify_pending(ignored)
    assert _writes(client) == [(8000, 1), command, command]

    # Applied after the resend -> nothing more is written.
    clock[0] += 30
    await coord._async_verify_pending(applied)
    clock[0] += 30
    await coord._async_verify_pending(ignored)
    assert _writes(client) == [(8000, 1), command, command]


async def test_applied_command_is_not_resent(hass, monkeypatch):
    """No resend when the unit applied the command."""
    coord, client, clock = await _take_control_and_command(
        hass, "async_set_ventilation_step", (3,), monkeypatch
    )
    clock[0] += 30
    await coord._async_verify_pending({"ventilation_mode": "high"})
    clock[0] += 30
    await coord._async_verify_pending({"ventilation_mode": "low"})
    assert _writes(client) == [(8000, 1), (8001, 3)]


async def test_command_resent_only_once(hass, monkeypatch, caplog):
    """After one resend the integration gives up and logs a warning."""
    coord, client, clock = await _take_control_and_command(
        hass, "async_set_ventilation_step", (3,), monkeypatch
    )
    for _ in range(4):
        clock[0] += 30
        await coord._async_verify_pending({"ventilation_mode": "low"})
    assert _writes(client) == [(8000, 1), (8001, 3), (8001, 3)]
    assert "did not apply register 8001 = 3" in caplog.text


async def test_command_without_takeover_is_not_tracked(hass, monkeypatch):
    """Commands sent while already under Modbus control are not resent."""
    coord = BrinkFlairCoordinator(hass, "/dev/ttyUSB0", 19200, 20)
    client = make_fake_client()
    coord._client = client
    coord.async_request_refresh = AsyncMock()
    coord.data = {"modbus_control_mode": "modbus_switch"}

    await coord.async_set_ventilation_step(3)
    await coord._async_verify_pending({"ventilation_mode": "low"})

    assert coord._pending is None
    assert _writes(client) == [(8001, 3)]


async def test_failed_resend_does_not_fail_poll(hass, monkeypatch):
    """A resend error is logged and the pending command dropped."""
    coord, client, clock = await _take_control_and_command(
        hass, "async_set_ventilation_step", (3,), monkeypatch
    )
    client.write_register = AsyncMock(side_effect=ModbusException("fail"))
    clock[0] += 30
    await coord._async_verify_pending({"ventilation_mode": "low"})
    assert coord._pending is None


async def test_poll_runs_verification(hass, monkeypatch):
    """A regular poll resends an ignored command (end to end through _async_update_data)."""
    coord, client, clock = await _take_control_and_command(
        hass, "async_set_ventilation_step", (3,), monkeypatch
    )
    clock[0] += 30
    # Fake device reports ventilation mode 4022 = 1 (low), not high.
    client.input_registers[4022] = 1
    await coord._async_update_data()
    assert _writes(client)[-1] == (8001, 3)


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
