"""DataUpdateCoordinator for Brink Flair."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ACTIVE_FUNCTION_MAP,
    BYPASS_STATUS_MAP,
    CO2_STATUS_MAP,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FLOW_PRESET_MAX,
    FLOW_PRESET_MIN,
    FROST_STATUS_MAP,
    MODBUS_CONTROL_DEVICE,
    MODBUS_CONTROL_MAP,
    MODBUS_CONTROL_SWITCH,
    REG_H_BYPASS_BOOST,
    REG_H_BYPASS_BOOST_POSITION,
    REG_H_BYPASS_HYSTERESIS,
    REG_H_BYPASS_MODE,
    REG_H_BYPASS_TEMP_DWELLING,
    REG_H_BYPASS_TEMP_OUTSIDE,
    REG_H_CO2_MODE,
    REG_H_CO2_SENSOR_1_LOW,
    REG_H_FILTER_CHANGE_DAYS,
    REG_H_FLOW_PRESET_0,
    REG_H_FROST_CONTROL_TEMP,
    REG_H_FROST_MIN_INLET_TEMP,
    REG_I_ACTIVE_FUNCTION,
    REG_I_BASE_HW_VERSION,
    REG_I_BASE_SERIAL,
    REG_I_BASE_SW_VERSION,
    REG_I_BYPASS_STATUS,
    REG_I_CO2_SENSOR_1_STATUS,
    REG_I_EXT_SW_VERSION,
    REG_H_IMBALANCE_EXHAUST,
    REG_H_IMBALANCE_SUPPLY,
    REG_I_FILTER_HOURS,
    REG_I_FILTER_STATUS,
    REG_I_FROST_STATUS,
    REG_I_OPERATING_TIME,
    REG_I_OUTSIDE_TEMPERATURE,
    REG_I_SUPPLY_SETPOINT,
    REG_I_EXHAUST_SETPOINT,
    REG_I_SUPPLY_PRESSURE,
    REG_I_UIF_SW_VERSION,
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


# Raw value an NTC input reports when no sensor is fitted (shown as 999.9 °C)
NTC_NOT_CONNECTED = 9999


def _ntc(raw: int) -> float | None:
    """NTC temperature in °C, or None when the sensor is not fitted / out of range."""
    if raw == NTC_NOT_CONNECTED:
        return None
    value = _temp(raw)
    return value if -50.0 <= value <= 100.0 else None


def _rht(raw: int) -> int | None:
    """Standalone RHT humidity; 0 % means no sensor is fitted (impossible indoors)."""
    return raw or None


def _co2_value(status: str, raw: int) -> int | None:
    """CO2 ppm, or None when the sensor is not fitted / not running."""
    return None if status in ("not_initialized", "error") else raw


def _humidity(raw: int) -> int:
    """Unsigned 16-bit register → % (device stores integer %, not tenths)."""
    return raw


def _pressure(raw: int) -> int:
    """Signed 16-bit register → Pa (device stores integer Pa, not tenths)."""
    return _signed(raw)


def _decode_sw_version(r0: int, r1: int, r2: int) -> str:
    """Decode three registers into a version string like 'S1.01.03.0001'.

    r0 high byte: ASCII type char (e.g. 0x53 = 'S')
    r0 low byte:  major number
    r1 high byte: minor number
    r1 low byte:  fix number
    r2:           build number (16-bit word)
    """
    type_char = chr((r0 >> 8) & 0xFF)
    major = r0 & 0xFF
    minor = (r1 >> 8) & 0xFF
    fix = r1 & 0xFF
    build = r2
    return f"{type_char}{major}.{minor:02d}.{fix:02d}.{build:04d}"


def _decode_hw_version(r: int) -> str:
    """Decode one register into a HW version string like 'H1.1'.

    High byte: major (BCD), low byte: minor (BCD).
    """
    major = (r >> 8) & 0xFF
    minor = r & 0xFF
    return f"H{major}.{minor}"


def _decode_serial(r0: int, r1: int, r2: int) -> str:
    """Decode three BCD registers into a 12-digit serial number string."""
    digits = ""
    for reg in (r0, r1, r2):
        for shift in (12, 8, 4, 0):
            digits += str((reg >> shift) & 0xF)
    return digits


class BrinkFlairCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls a Brink Flair unit via Modbus RTU and exposes data to entities.

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
        self.sw_version: str | None = None
        self.hw_version: str | None = None
        self.serial_number: str | None = None
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

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry info, including version data when available."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.serial_port}_{self.slave_id}")},
            name="Brink Flair 400",
            manufacturer="Brink",
            model="Flair 400",
            sw_version=self.sw_version,
            hw_version=self.hw_version,
            serial_number=self.serial_number,
        )

    # ------------------------------------------------------------------
    # Startup initialisation
    # ------------------------------------------------------------------

    async def async_initialize(self) -> None:
        """Read the device version and serial number for DeviceInfo.

        Read-only: nothing is written to the unit during setup. Modbus control
        (register 8000) is taken only when the user sends a command that needs
        it, see _async_ensure_modbus_control().
        """
        await self._async_read_device_version()

    async def _async_read_device_version(self) -> None:
        """Read HW/SW version and serial number registers (once at startup).

        Non-fatal: failures are logged at debug level and the attributes
        remain None, so DeviceInfo simply omits the fields.
        """
        await self._ensure_connected()
        try:
            b_sw = await self._client.read_input_registers(
                address=REG_I_BASE_SW_VERSION, count=3, device_id=self.slave_id
            )
            b_hw = await self._client.read_input_registers(
                address=REG_I_BASE_HW_VERSION, count=1, device_id=self.slave_id
            )
            b_serial = await self._client.read_input_registers(
                address=REG_I_BASE_SERIAL, count=3, device_id=self.slave_id
            )
            self.sw_version = _decode_sw_version(
                b_sw.registers[0], b_sw.registers[1], b_sw.registers[2]
            )
            self.hw_version = _decode_hw_version(b_hw.registers[0])
            self.serial_number = _decode_serial(
                b_serial.registers[0], b_serial.registers[1], b_serial.registers[2]
            )
            _LOGGER.debug(
                "Device version: SW=%s HW=%s serial=%s",
                self.sw_version,
                self.hw_version,
                self.serial_number,
            )
        except Exception as err:
            _LOGGER.debug("Could not read device version info: %s", err)
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
                address=REG_I_ACTIVE_FUNCTION, count=5, device_id=self.slave_id
            )
            # FC04 batch 2 — 4031..4037: supply setpoint, flow, [4033 skip], RPM, [4035 skip], temp, humidity
            b2 = await self._client.read_input_registers(
                address=REG_I_SUPPLY_SETPOINT, count=7, device_id=self.slave_id
            )
            # FC04 batch 3 — 4041..4047: exhaust setpoint, flow, [4043 skip], RPM, [4045 skip], temp, humidity
            b3 = await self._client.read_input_registers(
                address=REG_I_EXHAUST_SETPOINT, count=7, device_id=self.slave_id
            )
            # FC04 single reads
            b_bypass = await self._client.read_input_registers(
                address=REG_I_BYPASS_STATUS, count=1, device_id=self.slave_id
            )
            b_frost = await self._client.read_input_registers(
                address=REG_I_FROST_STATUS, count=3, device_id=self.slave_id
            )
            # FC04 batch — 4081..4083: NTC1 outside temp, NTC2 second sensor, RHT humidity
            b_ntc = await self._client.read_input_registers(
                address=REG_I_OUTSIDE_TEMPERATURE, count=3, device_id=self.slave_id
            )
            b_filter = await self._client.read_input_registers(
                address=REG_I_FILTER_STATUS, count=1, device_id=self.slave_id
            )
            b_fh = await self._client.read_input_registers(
                address=REG_I_FILTER_HOURS, count=1, device_id=self.slave_id
            )
            # FC04 batch — 4113..4114: operating time (32-bit, high word first)
            b_optime = await self._client.read_input_registers(
                address=REG_I_OPERATING_TIME, count=2, device_id=self.slave_id
            )
            # FC03 batch — 6000..6003: flow presets 0–3
            b_presets = await self._client.read_holding_registers(
                address=REG_H_FLOW_PRESET_0, count=4, device_id=self.slave_id
            )
            # FC03 batch — 6035..6036: supply/exhaust imbalance offsets
            b_imbalance = await self._client.read_holding_registers(
                address=REG_H_IMBALANCE_SUPPLY, count=2, device_id=self.slave_id
            )
            # FC03 batch — 6100..6105: bypass mode, temps, hysteresis, boost, boost position
            b_bypass_cfg = await self._client.read_holding_registers(
                address=REG_H_BYPASS_MODE, count=6, device_id=self.slave_id
            )
            # FC03 batch — 6110..6111: frost settings
            b_frost_cfg = await self._client.read_holding_registers(
                address=REG_H_FROST_CONTROL_TEMP, count=2, device_id=self.slave_id
            )
            # FC03 single — 6120: filter change days
            b_fcd = await self._client.read_holding_registers(
                address=REG_H_FILTER_CHANGE_DAYS, count=1, device_id=self.slave_id
            )
            # FC03 batch — 8000..8003: control mode, ventilation step, flow rate, standby
            b_ctrl = await self._client.read_holding_registers(
                address=REG_RC_MODBUS_CONTROL, count=4, device_id=self.slave_id
            )
            # FC04 batch — 4200..4207: CO2 sensor status + values (4 sensors × 2 registers)
            b_co2 = await self._client.read_input_registers(
                address=REG_I_CO2_SENSOR_1_STATUS, count=8, device_id=self.slave_id
            )
            # FC03 — 6150: CO2 mode; 6151..6158: low/high thresholds for sensors 1–4
            b_co2_mode = await self._client.read_holding_registers(
                address=REG_H_CO2_MODE, count=1, device_id=self.slave_id
            )
            b_co2_cfg = await self._client.read_holding_registers(
                address=REG_H_CO2_SENSOR_1_LOW, count=8, device_id=self.slave_id
            )
        except Exception:
            # Close on any error so the next cycle triggers a fresh reconnect.
            self._client.close()
            raise

        co2_status = [
            CO2_STATUS_MAP.get(b_co2.registers[2 * i], "unknown") for i in range(4)
        ]

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
            "outside_temperature": _ntc(b_ntc.registers[0]),
            "ntc2_temperature": _ntc(b_ntc.registers[1]),
            "rht_humidity": _rht(b_ntc.registers[2]),
            "operating_time": (b_optime.registers[0] << 16) | b_optime.registers[1],
            "filter_dirty": bool(b_filter.registers[0]),
            "filter_hours": b_fh.registers[0],
            # Flow presets (FC03 holding)
            "flow_preset_0": b_presets.registers[0],
            "flow_preset_1": b_presets.registers[1],
            "flow_preset_2": b_presets.registers[2],
            "flow_preset_3": b_presets.registers[3],
            # Imbalance offsets (FC03 holding)
            "imbalance_supply": _signed(b_imbalance.registers[0]),
            "imbalance_exhaust": _signed(b_imbalance.registers[1]),
            # Bypass config (FC03 holding)
            "bypass_mode": b_bypass_cfg.registers[0],
            "bypass_temp_dwelling": _temp(b_bypass_cfg.registers[1]),
            "bypass_temp_outside": _temp(b_bypass_cfg.registers[2]),
            "bypass_hysteresis": _temp(b_bypass_cfg.registers[3]),
            "bypass_boost": bool(b_bypass_cfg.registers[4]),
            "bypass_boost_position": b_bypass_cfg.registers[5],
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
            # CO2 sensors (FC04 input) — value is None when the sensor is not fitted
            "co2_sensor_1_status": co2_status[0],
            "co2_sensor_1_value": _co2_value(co2_status[0], b_co2.registers[1]),
            "co2_sensor_2_status": co2_status[1],
            "co2_sensor_2_value": _co2_value(co2_status[1], b_co2.registers[3]),
            "co2_sensor_3_status": co2_status[2],
            "co2_sensor_3_value": _co2_value(co2_status[2], b_co2.registers[5]),
            "co2_sensor_4_status": co2_status[3],
            "co2_sensor_4_value": _co2_value(co2_status[3], b_co2.registers[7]),
            # CO2 config (FC03 holding)
            "co2_mode": bool(b_co2_mode.registers[0]),
            "co2_sensor_1_low": b_co2_cfg.registers[0],
            "co2_sensor_1_high": b_co2_cfg.registers[1],
            "co2_sensor_2_low": b_co2_cfg.registers[2],
            "co2_sensor_2_high": b_co2_cfg.registers[3],
            "co2_sensor_3_low": b_co2_cfg.registers[4],
            "co2_sensor_3_high": b_co2_cfg.registers[5],
            "co2_sensor_4_low": b_co2_cfg.registers[6],
            "co2_sensor_4_high": b_co2_cfg.registers[7],
        }

    # ------------------------------------------------------------------
    # Write helpers — use the persistent connection; close on error so
    # the next call reconnects. Each helper refreshes the coordinator
    # after writing so entities reflect the new state immediately.
    # ------------------------------------------------------------------

    async def async_set_ventilation_step(self, step: int) -> None:
        """Set ventilation step via register 8001 (0=holiday … 3=high)."""
        await self._async_ensure_modbus_control()
        await self._write_register(REG_RC_VENTILATION_STEP, step)

    async def async_set_bypass_mode(self, mode: int) -> None:
        """Set bypass mode via register 6100 (0=auto, 1=closed, 2=open)."""
        await self._write_register(REG_H_BYPASS_MODE, mode)

    async def async_set_bypass_boost(self, enabled: bool) -> None:
        """Enable or disable bypass boost via register 6104."""
        await self._write_register(REG_H_BYPASS_BOOST, 1 if enabled else 0)

    async def async_set_flow_preset(self, index: int, value: int) -> None:
        """Set a flow preset (0–3) to the given m³/h value.

        Preset 0 accepts 0 or FLOW_PRESET_MIN..max, presets 1–3 accept
        FLOW_PRESET_MIN..max, and the presets must stay ascending. Values the
        unit would reject raise ServiceValidationError before anything is written.
        """
        if not (value == 0 and index == 0) and not (
            FLOW_PRESET_MIN <= value <= FLOW_PRESET_MAX
        ):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="flow_preset_out_of_range",
                translation_placeholders={
                    "value": str(value),
                    "minimum": str(FLOW_PRESET_MIN),
                    "maximum": str(FLOW_PRESET_MAX),
                },
            )
        data = self.data or {}
        lower = data.get(f"flow_preset_{index - 1}") if index > 0 else None
        upper = data.get(f"flow_preset_{index + 1}") if index < 3 else None
        if (lower is not None and value < lower) or (upper is not None and value > upper):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="flow_preset_order",
                translation_placeholders={
                    "value": str(value),
                    "lower": str(lower if lower is not None else 0),
                    "upper": str(upper if upper is not None else FLOW_PRESET_MAX),
                },
            )
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
        await self._async_ensure_modbus_control()
        await self._write_register(REG_RC_STANDBY, 1 if standby else 2)

    async def async_set_imbalance_supply(self, value: int) -> None:
        """Set supply imbalance offset (% correction, signed, -15..+15)."""
        await self._write_register(REG_H_IMBALANCE_SUPPLY, value & 0xFFFF)

    async def async_set_imbalance_exhaust(self, value: int) -> None:
        """Set exhaust imbalance offset (% correction, signed, -15..+15)."""
        await self._write_register(REG_H_IMBALANCE_EXHAUST, value & 0xFFFF)

    async def async_set_bypass_boost_position(self, value: int) -> None:
        """Set bypass boost step preset (0–3) via register 6105."""
        await self._write_register(REG_H_BYPASS_BOOST_POSITION, value)

    async def async_set_co2_mode(self, enabled: bool) -> None:
        """Enable or disable CO2 sensor control mode via register 6150."""
        await self._write_register(REG_H_CO2_MODE, 1 if enabled else 0)

    async def async_set_co2_threshold(self, sensor: int, low: int, high: int) -> None:
        """Set CO2 low/high thresholds for a sensor (sensor: 1–4, values in ppm)."""
        base = REG_H_CO2_SENSOR_1_LOW + (sensor - 1) * 2
        await self._write_register(base, low)
        await self._write_register(base + 1, high)

    # ------------------------------------------------------------------
    # Modbus control (register 8000)
    # ------------------------------------------------------------------

    async def _async_ensure_modbus_control(self) -> None:
        """Switch the unit to Modbus control right before a command needs it.

        Ventilation step (8001) and standby (8003) are ignored by the unit
        unless register 8000 = 1. Write it only when the last poll shows the
        unit under its own control (device_lcd) — this also covers the unit
        resetting 8000 to 0 after a power loss.
        """
        if (self.data or {}).get("modbus_control_mode") != "device_lcd":
            return
        await self._write_raw(REG_RC_MODBUS_CONTROL, MODBUS_CONTROL_SWITCH)
        _LOGGER.debug("Modbus control taken (8000=1)")

    async def async_release_modbus_control(self) -> None:
        """Hand control back to the unit (8000 = 0) when the entry is unloaded.

        Only when the last poll shows Modbus switch control; best effort, a
        failure is logged and does not block unloading.
        """
        if (self.data or {}).get("modbus_control_mode") != "modbus_switch":
            return
        try:
            await self._write_raw(REG_RC_MODBUS_CONTROL, MODBUS_CONTROL_DEVICE)
            _LOGGER.debug("Modbus control handed back to the unit (8000=0)")
        except Exception as err:  # noqa: BLE001 - unloading must not fail
            _LOGGER.warning("Could not hand control back to the unit: %s", err)

    async def _write_raw(self, address: int, value: int) -> None:
        """Write one register without refreshing; close the client on error."""
        await self._ensure_connected()
        try:
            await self._client.write_register(
                address=address, value=value, device_id=self.slave_id
            )
        except Exception:
            self._client.close()
            raise

    async def _write_register(self, address: int, value: int) -> None:
        await self._write_raw(address, value)
        await self.async_request_refresh()
