"""DataUpdateCoordinator for Brink Flair."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ACTIVE_FUNCTION_MAP,
    BYPASS_STATUS_MAP,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FROST_STATUS_MAP,
    MODBUS_CONTROL_MAP,
    REG_H_BYPASS_BOOST,
    REG_H_BYPASS_HYSTERESIS,
    REG_H_BYPASS_MODE,
    REG_H_BYPASS_TEMP_DWELLING,
    REG_H_BYPASS_TEMP_OUTSIDE,
    REG_H_FILTER_CHANGE_DAYS,
    REG_H_FLOW_PRESET_0,
    REG_H_FROST_CONTROL_TEMP,
    REG_H_FROST_MIN_INLET_TEMP,
    REG_I_ACTIVE_FUNCTION,
    REG_I_BYPASS_STATUS,
    REG_I_FILTER_HOURS,
    REG_I_FILTER_STATUS,
    REG_I_FROST_STATUS,
    REG_I_OUTSIDE_TEMPERATURE,
    REG_I_SUPPLY_SETPOINT,
    REG_I_EXHAUST_SETPOINT,
    REG_I_SUPPLY_PRESSURE,
    REG_RC_APPLIANCE_RESET,
    REG_RC_FILTER_RESET,
    REG_RC_MODBUS_CONTROL,
    REG_RC_STANDBY,
    REG_RC_VENTILATION_STEP,
    SERIAL_BYTESIZE,
    SERIAL_PARITY,
    SERIAL_STOPBITS,
    VENTILATION_MODE_MAP,
)

_LOGGER = logging.getLogger(__name__)


def _signed(raw: int) -> int:
    """Convert unsigned 16-bit register value to signed."""
    return raw if raw < 0x8000 else raw - 0x10000


def _temp(raw: int) -> float:
    """Signed 16-bit register in tenths of °C → °C."""
    return _signed(raw) / 10.0


def _humidity(raw: int) -> float:
    """Unsigned 16-bit register in tenths of % → %."""
    return raw / 10.0


def _pressure(raw: int) -> float:
    """Signed 16-bit register in tenths of Pa → Pa."""
    return _signed(raw) / 10.0


class BrinkFlairCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the Brink Flair 400 via Modbus RTU and exposes data to entities.

    The Modbus client is kept connected across poll cycles and write operations.
    On any communication error the connection is closed so that the next call
    triggers a fresh reconnect via _ensure_connected().
    """

    def __init__(
        self,
        hass: HomeAssistant,
        serial_port: str,
        baud_rate: int,
        slave_id: int,
    ) -> None:
        """Initialise the coordinator."""
        self.serial_port = serial_port
        self.slave_id = slave_id
        self._client = AsyncModbusSerialClient(
            port=serial_port,
            baudrate=baud_rate,
            bytesize=SERIAL_BYTESIZE,
            parity=SERIAL_PARITY,
            stopbits=SERIAL_STOPBITS,
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def _ensure_connected(self) -> None:
        """Connect if not already connected."""
        if not self._client.connected:
            _LOGGER.debug("Connecting to Brink Flair at %s", self.serial_port)
            await self._client.connect()

    async def async_shutdown(self) -> None:
        """Close the persistent Modbus connection on integration unload."""
        self._client.close()
        _LOGGER.debug("Modbus connection closed")

    # ------------------------------------------------------------------
    # Startup initialisation
    # ------------------------------------------------------------------

    async def async_initialize(self) -> None:
        """Write register 8000 = 1 (Modbus switch-control mode).

        The Brink device resets to 'Device LCD' mode (8000 = 0) after any
        power loss, which prevents HA from controlling ventilation steps.
        Must be called once at HA startup before the first data fetch.
        """
        await self._ensure_connected()
        try:
            await self._client.write_register(
                address=REG_RC_MODBUS_CONTROL, value=1, slave=self.slave_id
            )
            _LOGGER.debug("Modbus control mode set to 'switch' (8000=1)")
        except ModbusException as err:
            _LOGGER.warning("Could not set Modbus control mode: %s", err)
            self._client.close()

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self._fetch_data()
        except ModbusException as err:
            raise UpdateFailed(f"Modbus error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _fetch_data(self) -> dict[str, Any]:
        """Read all monitored registers in batches and return a flat dict."""
        await self._ensure_connected()
        try:
            # FC04 batch 1 — 4020..4024: active function, [4021 skip], ventilation mode, pressures
            b1 = await self._client.read_input_registers(
                address=REG_I_ACTIVE_FUNCTION, count=5, slave=self.slave_id
            )
            # FC04 batch 2 — 4031..4037: supply setpoint, flow, [4033 skip], RPM, [4035 skip], temp, humidity
            b2 = await self._client.read_input_registers(
                address=REG_I_SUPPLY_SETPOINT, count=7, slave=self.slave_id
            )
            # FC04 batch 3 — 4041..4047: exhaust setpoint, flow, [4043 skip], RPM, [4045 skip], temp, humidity
            b3 = await self._client.read_input_registers(
                address=REG_I_EXHAUST_SETPOINT, count=7, slave=self.slave_id
            )
            # FC04 single reads
            b_bypass = await self._client.read_input_registers(
                address=REG_I_BYPASS_STATUS, count=1, slave=self.slave_id
            )
            b_frost = await self._client.read_input_registers(
                address=REG_I_FROST_STATUS, count=3, slave=self.slave_id
            )
            b_ntc = await self._client.read_input_registers(
                address=REG_I_OUTSIDE_TEMPERATURE, count=1, slave=self.slave_id
            )
            b_filter = await self._client.read_input_registers(
                address=REG_I_FILTER_STATUS, count=1, slave=self.slave_id
            )
            b_fh = await self._client.read_input_registers(
                address=REG_I_FILTER_HOURS, count=1, slave=self.slave_id
            )
            # FC03 batch — 6000..6003: flow presets 0–3
            b_presets = await self._client.read_holding_registers(
                address=REG_H_FLOW_PRESET_0, count=4, slave=self.slave_id
            )
            # FC03 batch — 6100..6104: bypass mode, temps, hysteresis, boost
            b_bypass_cfg = await self._client.read_holding_registers(
                address=REG_H_BYPASS_MODE, count=5, slave=self.slave_id
            )
            # FC03 batch — 6110..6111: frost settings
            b_frost_cfg = await self._client.read_holding_registers(
                address=REG_H_FROST_CONTROL_TEMP, count=2, slave=self.slave_id
            )
            # FC03 single — 6120: filter change days
            b_fcd = await self._client.read_holding_registers(
                address=REG_H_FILTER_CHANGE_DAYS, count=1, slave=self.slave_id
            )
            # FC03 batch — 8000..8003: control mode, ventilation step, flow rate, standby
            b_ctrl = await self._client.read_holding_registers(
                address=REG_RC_MODBUS_CONTROL, count=4, slave=self.slave_id
            )
        except Exception:
            # Close on any error so the next cycle triggers a fresh reconnect.
            self._client.close()
            raise

        return {
            # Status (FC04)
            "active_function": ACTIVE_FUNCTION_MAP.get(b1.registers[0], "unknown"),
            "ventilation_mode": VENTILATION_MODE_MAP.get(b1.registers[2], "unknown"),
            "supply_pressure": _pressure(b1.registers[3]),
            "exhaust_pressure": _pressure(b1.registers[4]),
            # Supply fan (FC04)
            "supply_setpoint": b2.registers[0],
            "supply_flow": b2.registers[1],
            "supply_fan_rpm": b2.registers[3],
            "supply_temperature": _temp(b2.registers[5]),
            "supply_humidity": _humidity(b2.registers[6]),
            # Exhaust fan (FC04)
            "exhaust_setpoint": b3.registers[0],
            "exhaust_flow": b3.registers[1],
            "exhaust_fan_rpm": b3.registers[3],
            "exhaust_temperature": _temp(b3.registers[5]),
            "exhaust_humidity": _humidity(b3.registers[6]),
            # System (FC04)
            "bypass_status": BYPASS_STATUS_MAP.get(b_bypass.registers[0], "unknown"),
            "frost_status": FROST_STATUS_MAP.get(b_frost.registers[0], "unknown"),
            "frost_heater_power": b_frost.registers[1],
            "frost_fan_reduction": b_frost.registers[2],
            "outside_temperature": _temp(b_ntc.registers[0]),
            "filter_dirty": bool(b_filter.registers[0]),
            "filter_hours": b_fh.registers[0],
            # Flow presets (FC03 holding)
            "flow_preset_0": b_presets.registers[0],
            "flow_preset_1": b_presets.registers[1],
            "flow_preset_2": b_presets.registers[2],
            "flow_preset_3": b_presets.registers[3],
            # Bypass config (FC03 holding)
            "bypass_mode": b_bypass_cfg.registers[0],
            "bypass_temp_dwelling": _temp(b_bypass_cfg.registers[1]),
            "bypass_temp_outside": _temp(b_bypass_cfg.registers[2]),
            "bypass_hysteresis": _temp(b_bypass_cfg.registers[3]),
            "bypass_boost": bool(b_bypass_cfg.registers[4]),
            # Frost config (FC03 holding)
            "frost_control_temp": _temp(b_frost_cfg.registers[0]),
            "frost_min_inlet_temp": _temp(b_frost_cfg.registers[1]),
            # Filter config (FC03 holding)
            "filter_change_days": b_fcd.registers[0],
            # Control state (FC03 holding)
            "modbus_control_mode": MODBUS_CONTROL_MAP.get(b_ctrl.registers[0], "unknown"),
            "ventilation_step": b_ctrl.registers[1],
            "flow_rate_setpoint": b_ctrl.registers[2],
            "standby": bool(b_ctrl.registers[3]),
        }

    # ------------------------------------------------------------------
    # Write helpers — use the persistent connection; close on error so
    # the next call reconnects. Each helper refreshes the coordinator
    # after writing so entities reflect the new state immediately.
    # ------------------------------------------------------------------

    async def async_set_ventilation_step(self, step: int) -> None:
        """Set ventilation step via register 8001 (0=holiday … 3=high)."""
        await self._write_register(REG_RC_VENTILATION_STEP, step)

    async def async_set_bypass_mode(self, mode: int) -> None:
        """Set bypass mode via register 6100 (0=auto, 1=closed, 2=open)."""
        await self._write_register(REG_H_BYPASS_MODE, mode)

    async def async_set_bypass_boost(self, enabled: bool) -> None:
        """Enable or disable bypass boost via register 6104."""
        await self._write_register(REG_H_BYPASS_BOOST, 1 if enabled else 0)

    async def async_set_flow_preset(self, index: int, value: int) -> None:
        """Set a flow preset (0–3) to the given m³/h value."""
        await self._write_register(REG_H_FLOW_PRESET_0 + index, value)

    async def async_set_bypass_temp_dwelling(self, value: float) -> None:
        """Set bypass open temperature threshold from dwelling (°C)."""
        await self._write_register(REG_H_BYPASS_TEMP_DWELLING, round(value * 10))

    async def async_set_bypass_temp_outside(self, value: float) -> None:
        """Set bypass open temperature threshold from outside (°C)."""
        await self._write_register(REG_H_BYPASS_TEMP_OUTSIDE, round(value * 10))

    async def async_set_bypass_hysteresis(self, value: float) -> None:
        """Set bypass temperature hysteresis (°C)."""
        await self._write_register(REG_H_BYPASS_HYSTERESIS, round(value * 10))

    async def async_set_frost_control_temp(self, value: float) -> None:
        """Set frost protection activation temperature (°C)."""
        await self._write_register(REG_H_FROST_CONTROL_TEMP, round(value * 10))

    async def async_set_frost_min_inlet_temp(self, value: float) -> None:
        """Set frost protection minimum supply temperature (°C)."""
        await self._write_register(REG_H_FROST_MIN_INLET_TEMP, round(value * 10))

    async def async_set_filter_change_days(self, value: int) -> None:
        """Set number of days before a filter warning is raised."""
        await self._write_register(REG_H_FILTER_CHANGE_DAYS, value)

    async def async_filter_reset(self) -> None:
        """Write 1 to register 8010 to reset the filter warning."""
        await self._write_register(REG_RC_FILTER_RESET, 1)

    async def async_appliance_reset(self) -> None:
        """Write 1 to register 8011 to reset the appliance."""
        await self._write_register(REG_RC_APPLIANCE_RESET, 1)

    async def async_set_standby(self, standby: bool) -> None:
        """Set standby (True) or resume normal mode (False) via register 8003."""
        await self._write_register(REG_RC_STANDBY, 1 if standby else 2)

    async def _write_register(self, address: int, value: int) -> None:
        await self._ensure_connected()
        try:
            await self._client.write_register(
                address=address, value=value, slave=self.slave_id
            )
        except Exception:
            self._client.close()
            raise
        await self.async_request_refresh()
