# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Home Assistant custom integration for the **Brink Flair 400** (and compatible Flair models). Communicates directly with HA via **Modbus RTU over RS-485** using `pymodbus`. Domain: `brink_flair`. HACS-compatible.

Serial framing is fixed at **8E1**. Factory defaults: slave address **20**, baud rate **19200**.

## Modbus register map

Three address spaces, each using a different function code:

| Range | FC (read) | FC (write) | Purpose |
|-------|-----------|------------|---------|
| 4000–4544 | 0x04 (read_input_registers) | — | Monitoring data (temperatures, flows, status) |
| 6000–7992 | 0x03 (read_holding_registers) | 0x06 (write_register) | Settings (flow presets, bypass/frost config) |
| 8000–8011 | 0x03 | 0x06 | Remote control commands |

Key addresses (see `const.py` for the full map):
- **4020** active function / **4022** ventilation mode / **4036** supply temp / **4046** exhaust temp / **4081** outside temp (NTC1)
- **4031/4032** supply setpoint/flow / **4041/4042** exhaust setpoint/flow
- **4034/4044** fan RPM / **4037/4047** humidity / **4023/4024** pressure
- **4050** bypass status / **4070** frost status / **4100** filter dirty / **4115** filter hours
- **6000–6003** flow presets / **6100–6103** bypass config / **6110–6111** frost config / **6120** filter days
- **8000** Modbus control mode / **8001** ventilation step / **8003** standby / **8010** filter reset / **8011** appliance reset

**Critical startup requirement**: register 8000 must be written to `1` ("Modbus switch" mode) on every HA start. The device resets it to `0` ("Device LCD") after power loss. This is done in `coordinator.async_initialize()`, called from `async_setup_entry` before the first data fetch.

## Architecture

Follows the standard HA `DataUpdateCoordinator` pattern:

- **`coordinator.py`** — `BrinkFlairCoordinator` reads all monitored data in batches (~10 Modbus transactions per poll cycle), exposes it as a flat `dict`, and provides async write helpers (`async_set_ventilation_step`, `async_set_bypass_mode`, `async_set_flow_preset`, `async_filter_reset`, etc.). Each write helper calls `_write_register()` then `async_request_refresh()`.
- **`__init__.py`** — calls `coordinator.async_initialize()` then `coordinator.async_config_entry_first_refresh()`, stores coordinator in `hass.data[DOMAIN][entry_id]`, forwards to all platforms.
- **`config_flow.py`** — collects serial port, baud rate, slave ID; tests by reading FC04 register 4020 before saving.
- **`sensor.py`** — declarative `BrinkFlairSensorEntityDescription` (adds `value_fn`) covers all 19 monitoring sensors.
- **`binary_sensor.py`** — `FilterDirtyBinarySensor` reads `data["filter_dirty"]` (register 4100).
- **`select.py`** — `VentilationModeSelect` (writes 8001) and `BypassModeSelect` (writes 6100) using a `current_fn`/`set_fn` pattern.
- **`number.py`** — 10 numeric settings (flow presets, bypass/frost temperatures, filter days) using the same `value_fn`/`set_fn` pattern.
- **`button.py`** — Filter Reset (8010) and Appliance Reset (8011, disabled by default).

## Polling batch layout

| Call | FC | Address | Count | Data extracted |
|------|----|---------|-------|----------------|
| b1 | 04 | 4020 | 5 | active_function[0], vent_mode[2], pressures[3,4] |
| b2 | 04 | 4031 | 7 | supply: setpoint[0], flow[1], RPM[3], temp[5], hum[6] |
| b3 | 04 | 4041 | 7 | exhaust: setpoint[0], flow[1], RPM[3], temp[5], hum[6] |
| b_bypass | 04 | 4050 | 1 | bypass status |
| b_frost | 04 | 4070 | 3 | frost status[0], heater[1], fan reduction[2] |
| b_ntc | 04 | 4081 | 1 | outside temperature (NTC1) |
| b_filter | 04 | 4100 | 1 | filter dirty flag |
| b_fh | 04 | 4115 | 1 | filter hours |
| b_presets | 03 | 6000 | 4 | flow presets 0–3 |
| b_bypass_cfg | 03 | 6100 | 4 | bypass mode, temps, hysteresis |
| b_frost_cfg | 03 | 6110 | 2 | frost control temp, min inlet temp |
| b_fcd | 03 | 6120 | 1 | filter change days |
| b_ctrl | 03 | 8000 | 4 | modbus control, vent step, flow rate, standby |

## File layout

```
custom_components/brink_flair/
  __init__.py        # entry setup/unload — calls async_initialize() before first refresh
  manifest.json      # requires pymodbus==3.11.2
  config_flow.py     # UI wizard: serial port, baud rate, slave ID (default 20)
  const.py           # all register addresses, value maps, framing constants
  coordinator.py     # DataUpdateCoordinator — batched polling + write helpers
  sensor.py          # 19 sensors (temperatures, flows, RPM, pressure, humidity, status)
  binary_sensor.py   # filter_dirty (register 4100)
  select.py          # ventilation mode (8001), bypass mode (6100)
  number.py          # 10 number entities (flow presets, bypass/frost temps, filter days)
  button.py          # filter reset (8010), appliance reset (8011)
  strings.json       # UI strings (source of truth)
  translations/
    en.json          # English translations (mirror of strings.json)
hacs.json            # HACS metadata
```
