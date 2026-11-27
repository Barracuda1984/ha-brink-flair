"""Shared fixtures for Brink Flair tests."""
from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.brink_flair.const import (
    CONF_BAUD_RATE,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    DEFAULT_BAUD_RATE,
    DEFAULT_SLAVE_ID,
    DOMAIN,
)

# ---------------------------------------------------------------------------
# Default config-entry data
# ---------------------------------------------------------------------------

ENTRY_DATA: dict[str, Any] = {
    CONF_SERIAL_PORT: "/dev/ttyUSB0",
    CONF_BAUD_RATE: DEFAULT_BAUD_RATE,
    CONF_SLAVE_ID: DEFAULT_SLAVE_ID,
}

# ---------------------------------------------------------------------------
# Representative coordinator data snapshot (all registers decoded)
# ---------------------------------------------------------------------------

COORDINATOR_DATA: dict[str, Any] = {
    # Status
    "active_function": "auto_modbus",
    "ventilation_mode": "normal",
    "supply_pressure": 125,
    "exhaust_pressure": -11,
    # Supply fan
    "supply_setpoint": 200,
    "supply_flow": 198,
    "supply_fan_rpm": 1450,
    "supply_temperature": 22.3,
    "supply_humidity": 45,
    # Exhaust fan
    "exhaust_setpoint": 200,
    "exhaust_flow": 195,
    "exhaust_fan_rpm": 1420,
    "exhaust_temperature": 20.1,
    "exhaust_humidity": 50,
    # System
    "bypass_status": "closed",
    "frost_status": "no_frost",
    "frost_heater_power": 0,
    "frost_fan_reduction": 0,
    "outside_temperature": 8.5,
    "ntc2_temperature": 8.6,
    "rht_humidity": 45,
    "operating_time": 720,
    "filter_dirty": False,
    "filter_hours": 720,
    # Flow presets
    "flow_preset_0": 75,
    "flow_preset_1": 150,
    "flow_preset_2": 200,
    "flow_preset_3": 300,
    # Imbalance offsets
    "imbalance_supply": 0,
    "imbalance_exhaust": 0,
    # Bypass config
    "bypass_mode": 0,
    "bypass_temp_dwelling": 24.0,
    "bypass_temp_outside": 12.0,
    "bypass_hysteresis": 2.0,
    "bypass_boost": False,
    "bypass_boost_position": 2,
    # Frost config
    "frost_control_temp": 1.0,
    "frost_min_inlet_temp": 15.0,
    # Filter config
    "filter_change_days": 180,
    # Control state
    "modbus_control_mode": "modbus_switch",
    "ventilation_step": 2,
    "flow_rate_setpoint": 200,
    "standby": False,
}


# ---------------------------------------------------------------------------
# Custom integrations must be explicitly enabled in pytest-homeassistant
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load custom_components/brink_flair in every test."""


# ---------------------------------------------------------------------------
# Fake Modbus device — answers reads by register address, not call order
# ---------------------------------------------------------------------------

# Raw FC04 input-register values (as the device would return them)
DEFAULT_INPUT_REGISTERS: dict[int, int] = {
    # 4000..4012: version / serial (read once in async_initialize)
    4000: 0x5301, 4001: 0x0103, 4002: 1, 4003: 0x0101,
    4010: 0x1234, 4011: 0x5678, 4012: 0x9012,
    # 4020..4024: active function, fan control type, ventilation mode, pressures
    4020: 12, 4021: 0, 4022: 2, 4023: 125, 4024: 65525,   # exhaust 65525 → -11 Pa
    # 4031..4037: supply setpoint, flow, mass flow, rpm, status, temp, humidity
    4031: 200, 4032: 198, 4033: 0, 4034: 1450, 4035: 0, 4036: 223, 4037: 45,
    # 4041..4047: exhaust setpoint, flow, mass flow, rpm, status, temp, humidity
    4041: 200, 4042: 195, 4043: 0, 4044: 1420, 4045: 0, 4046: 201, 4047: 50,
    4050: 4,                                  # bypass closed
    4070: 2, 4071: 0, 4072: 0,                # no frost, heater 0 %, reduction 0 %
    4081: 85, 4082: 86, 4083: 45,             # NTC1 8.5 °C, NTC2 8.6 °C, RHT 45 %
    4100: 0,                                  # filter not dirty
    4113: 0, 4114: 720,                       # operating time 720 h (32-bit)
    4115: 720,                                # filter hours
    # 4200..4207: CO2 sensors 1–4 (status, value) — 1, 2 running; 3, 4 not fitted
    4200: 4, 4201: 430, 4202: 4, 4203: 650, 4204: 1, 4205: 0, 4206: 1, 4207: 0,
}

# Raw FC03 holding-register values
DEFAULT_HOLDING_REGISTERS: dict[int, int] = {
    6000: 75, 6001: 150, 6002: 200, 6003: 300,          # flow presets
    6035: 0, 6036: 0,                                   # imbalance offsets
    6100: 0, 6101: 240, 6102: 120, 6103: 20,            # bypass auto, 24 °C, 12 °C, 2 °C
    6104: 0, 6105: 2,                                   # bypass boost off, position 2
    6110: 10, 6111: 150,                                # frost 1.0 °C, 15.0 °C
    6120: 180,                                          # filter change days
    6150: 0,                                            # CO2 mode off
    6151: 400, 6152: 1000, 6153: 400, 6154: 1000,       # CO2 thresholds
    6155: 400, 6156: 1000, 6157: 400, 6158: 1000,
    8000: 1, 8001: 2, 8002: 200, 8003: 0,               # modbus switch, normal, 200, not standby
}


def _make_register_result(*values: int) -> MagicMock:
    """Return a mock Modbus read result with the given register values."""
    result = MagicMock()
    result.isError.return_value = False
    result.registers = list(values)
    return result


def make_fake_client(
    input_overrides: dict[int, int] | None = None,
    holding_overrides: dict[int, int] | None = None,
    client: MagicMock | None = None,
) -> MagicMock:
    """Build (or configure) a mock AsyncModbusSerialClient backed by register maps.

    Reads return the registers at the requested address range, so tests are
    independent of how the coordinator batches its reads. Unknown addresses
    read as 0. Writes update the holding-register map.
    """
    inputs = {**DEFAULT_INPUT_REGISTERS, **(input_overrides or {})}
    holding = {**DEFAULT_HOLDING_REGISTERS, **(holding_overrides or {})}
    client = client if client is not None else MagicMock()
    client.connected = False

    async def fake_connect() -> bool:
        client.connected = True
        return True

    def fake_close() -> None:
        client.connected = False

    async def read_input(address: int, count: int = 1, **_: Any) -> MagicMock:
        return _make_register_result(*(inputs.get(a, 0) for a in range(address, address + count)))

    async def read_holding(address: int, count: int = 1, **_: Any) -> MagicMock:
        return _make_register_result(*(holding.get(a, 0) for a in range(address, address + count)))

    async def write(address: int, value: int, **_: Any) -> MagicMock:
        holding[address] = value
        return MagicMock(isError=lambda: False)

    client.connect = AsyncMock(side_effect=fake_connect)
    client.close = MagicMock(side_effect=fake_close)
    client.read_input_registers = AsyncMock(side_effect=read_input)
    client.read_holding_registers = AsyncMock(side_effect=read_holding)
    client.write_register = AsyncMock(side_effect=write)
    client.input_registers = inputs
    client.holding_registers = holding
    return client


@pytest.fixture
def mock_modbus_client() -> Generator[MagicMock, None, None]:
    """Patch AsyncModbusSerialClient throughout the integration with a fake device."""
    with patch(
        "custom_components.brink_flair.coordinator.AsyncModbusSerialClient",
        autospec=True,
    ) as mock_cls:
        yield make_fake_client(client=mock_cls.return_value)


# ---------------------------------------------------------------------------
# Config entry fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a pre-configured MockConfigEntry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        unique_id=f"{ENTRY_DATA[CONF_SERIAL_PORT]}_{ENTRY_DATA[CONF_SLAVE_ID]}",
    )
