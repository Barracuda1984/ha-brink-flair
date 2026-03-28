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
# Mock Modbus client fixture
# ---------------------------------------------------------------------------


def _make_register_result(*values: int) -> MagicMock:
    """Return a mock Modbus read result with the given register values."""
    result = MagicMock()
    result.isError.return_value = False
    result.registers = list(values)
    return result


@pytest.fixture
def mock_modbus_client() -> Generator[MagicMock, None, None]:
    """Patch AsyncModbusSerialClient throughout the integration."""
    with patch(
        "custom_components.brink_flair.coordinator.AsyncModbusSerialClient",
        autospec=True,
    ) as mock_cls:
        client = mock_cls.return_value
        client.connected = False

        async def fake_connect() -> None:
            client.connected = True

        client.connect = AsyncMock(side_effect=fake_connect)
        client.close = MagicMock(side_effect=lambda: setattr(client, "connected", False))
        client.write_register = AsyncMock(return_value=MagicMock(isError=lambda: False))

        # FC04 input-register reads — return plausible raw register values
        # batch 1: 4020..4024  (active_function, skip, ventilation_mode, supply_pressure, exhaust_pressure)
        b1 = _make_register_result(12, 0, 2, 125, 65525)   # supply=125 Pa, exhaust=65525→-11 Pa
        # batch 2: 4031..4037  (supply: setpoint, flow, skip, rpm, skip, temp, humidity)
        b2 = _make_register_result(200, 198, 0, 1450, 0, 223, 45)   # humidity=45 %
        # batch 3: 4041..4047  (exhaust: setpoint, flow, skip, rpm, skip, temp, humidity)
        b3 = _make_register_result(200, 195, 0, 1420, 0, 201, 50)   # humidity=50 %
        # single reads
        b_bypass = _make_register_result(4)                    # closed
        b_frost = _make_register_result(2, 0, 0)               # no_frost, heater=0, reduction=0
        b_ntc = _make_register_result(85, 86, 45)              # NTC1=8.5°C, NTC2=8.6°C, RHT=45%
        b_filter = _make_register_result(0)                    # not dirty
        b_fh = _make_register_result(720)                      # 720 hours
        b_optime = _make_register_result(0, 720)               # 720 lifetime hours (32-bit)
        # FC03 holding reads
        b_presets = _make_register_result(75, 150, 200, 300)
        b_imbalance = _make_register_result(0, 0)              # 0% supply, 0% exhaust offset
        b_bypass_cfg = _make_register_result(0, 240, 120, 20, 0, 2)  # auto, 24°C, 12°C, 2°C, boost=off, position=2
        b_frost_cfg = _make_register_result(10, 150)           # 1.0°C, 15.0°C
        b_fcd = _make_register_result(180)
        b_ctrl = _make_register_result(1, 2, 200, 0)           # modbus_switch, normal, 200, not standby

        client.read_input_registers = AsyncMock(
            side_effect=[b1, b2, b3, b_bypass, b_frost, b_ntc, b_filter, b_fh, b_optime]
            * 100  # repeat so multiple poll cycles work
        )
        client.read_holding_registers = AsyncMock(
            side_effect=[b_presets, b_imbalance, b_bypass_cfg, b_frost_cfg, b_fcd, b_ctrl] * 100
        )

        yield client


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
