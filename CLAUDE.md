# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Home Assistant custom integration for the **Brink Flair 400** (other Flair models untested). Communicates directly with HA via **Modbus RTU over RS-485** using `pymodbus`. Domain: `brink_flair`. HACS-compatible. Minimum HA version **2025.9.0** (first release shipping pymodbus ≥ 3.10).

Serial framing is fixed at **8E1**. Factory defaults: slave address **20**, baud rate **19200**. Poll interval 30 s (`DEFAULT_SCAN_INTERVAL`).

## Modbus register map

Three address spaces, each using a different function code:

| Range | FC (read) | FC (write) | Purpose |
|-------|-----------|------------|---------|
| 4000–4544 | 0x04 (read_input_registers) | — | Monitoring data (temperatures, flows, status) |
| 6000–7992 | 0x03 (read_holding_registers) | 0x06 (write_register) | Settings (flow presets, bypass/frost/CO2 config) |
| 8000–8011 | 0x03 | 0x06 | Remote control commands |

Key addresses (see `const.py` for the full map):
- **4000–4012** SW/HW version, serial number (read once at startup)
- **4020** active function / **4022** ventilation mode / **4023/4024** pressure
- **4031/4032** supply setpoint/flow / **4034** RPM / **4036** temp / **4037** humidity (exhaust: 4041–4047)
- **4050** bypass status / **4070–4072** frost status, heater, fan reduction
- **4081** outside temp (NTC1) / **4082** NTC2 / **4083** RHT humidity
- **4100** filter dirty / **4113–4114** operating time (32-bit, high word first) / **4115** filter hours
- **4200–4207** CO2 sensors 1–4 (status, value pairs)
- **6000–6003** flow presets / **6035/6036** imbalance offsets (signed %) / **6100–6105** bypass config incl. boost + boost position / **6110–6111** frost config / **6120** filter days / **6150** CO2 mode / **6151–6158** CO2 low/high thresholds
- **8000** Modbus control mode / **8001** ventilation step / **8003** standby (1 = standby, 2 = normal) / **8010** filter reset / **8011** appliance reset

**Critical startup requirement**: register 8000 must be written to `1` ("Modbus switch" mode) on every HA start. The device resets it to `0` ("Device LCD") after power loss. This is done in `coordinator.async_initialize()`, called from `async_setup_entry` before the first data fetch; it also reads the device version/serial for `DeviceInfo`.

## Architecture

Follows the standard HA `DataUpdateCoordinator` pattern:

- **`coordinator.py`** — `BrinkFlairCoordinator` keeps a persistent `AsyncModbusSerialClient` (closed on any error, reconnected via `_ensure_connected()`), reads all monitored data in 18 Modbus transactions per poll cycle, exposes it as a flat `dict`, and provides async write helpers (`async_set_ventilation_step`, `async_set_bypass_mode`, `async_set_standby`, `async_set_co2_threshold`, …). Each write helper calls `_write_register()` then `async_request_refresh()`.
- **`__init__.py`** — calls `coordinator.async_initialize()` then `coordinator.async_config_entry_first_refresh()`, stores coordinator in `hass.data[DOMAIN][entry_id]`, forwards to all platforms.
- **`config_flow.py`** — collects serial port, baud rate, slave ID; tests by reading FC04 register 4020 before saving.
- **`sensor.py`** — declarative `BrinkFlairSensorEntityDescription` (adds `value_fn`) covers 31 sensors (incl. 4× CO2 value + 4× CO2 status). Text status sensors are built with `_enum_sensor()`: `SensorDeviceClass.ENUM`, `options` from the `*_MAP` in `const.py`, states translated via `entity.sensor.<translation_key>.state` in `strings.json` / `translations/*.json` (en, cs). When adding a value to a map, add its translation to all three files — `tests/test_sensor.py` enforces this.
- **`binary_sensor.py`** — `FilterDirtyBinarySensor` reads `data["filter_dirty"]` (register 4100).
- **`select.py`** — ventilation mode (writes 8001) and bypass mode (writes 6100) using a `current_fn`/`set_fn` pattern.
- **`number.py`** — 21 numeric settings (flow presets, bypass/frost temperatures, filter days, imbalance offsets, bypass boost position, CO2 thresholds) using the same `value_fn`/`set_fn` pattern.
- **`switch.py`** — Standby (8003), Bypass Boost (6104), CO2 Control Mode (6150) using `is_on_fn`/`turn_on_fn`/`turn_off_fn`.
- **`button.py`** — Filter Reset (8010) and Appliance Reset (8011, disabled by default).

Device name is hard-coded as **Brink Flair 400**, so entity IDs follow `<platform>.brink_flair_400_*` (dashboards and tests rely on this).

## Polling batch layout

| Call | FC | Address | Count | Data extracted |
|------|----|---------|-------|----------------|
| b1 | 04 | 4020 | 5 | active_function[0], vent_mode[2], pressures[3,4] |
| b2 | 04 | 4031 | 7 | supply: setpoint[0], flow[1], RPM[3], temp[5], hum[6] |
| b3 | 04 | 4041 | 7 | exhaust: setpoint[0], flow[1], RPM[3], temp[5], hum[6] |
| b_bypass | 04 | 4050 | 1 | bypass status |
| b_frost | 04 | 4070 | 3 | frost status[0], heater[1], fan reduction[2] |
| b_ntc | 04 | 4081 | 3 | NTC1 outside temp, NTC2, RHT humidity |
| b_filter | 04 | 4100 | 1 | filter dirty flag |
| b_fh | 04 | 4115 | 1 | filter hours |
| b_optime | 04 | 4113 | 2 | operating time (32-bit) |
| b_presets | 03 | 6000 | 4 | flow presets 0–3 |
| b_imbalance | 03 | 6035 | 2 | supply/exhaust imbalance offsets (signed) |
| b_bypass_cfg | 03 | 6100 | 6 | bypass mode, temps, hysteresis, boost, boost position |
| b_frost_cfg | 03 | 6110 | 2 | frost control temp, min inlet temp |
| b_fcd | 03 | 6120 | 1 | filter change days |
| b_ctrl | 03 | 8000 | 4 | modbus control, vent step, flow rate, standby |
| b_co2 | 04 | 4200 | 8 | CO2 sensors 1–4: status, value |
| b_co2_mode | 03 | 6150 | 1 | CO2 control mode |
| b_co2_cfg | 03 | 6151 | 8 | CO2 low/high thresholds, sensors 1–4 |

## Tests

```bash
pip install -r requirements_test.txt "pymodbus>=3.10.0,<4"
pytest --cov
```

- `tests/conftest.py` provides a **fake Modbus device** (`make_fake_client()`): reads are answered by register address from `DEFAULT_INPUT_REGISTERS` / `DEFAULT_HOLDING_REGISTERS`, so tests do not depend on batch order. Override only the registers a test cares about. Adding a new register to the poll cycle needs no mock changes (unknown addresses read 0), but add a default value there if the decoded value matters.
- `enable_custom_integrations` is enabled for every test via an autouse fixture.
- When adding a write helper, add a row to `test_write_helpers` in `tests/test_coordinator.py`.

## CI and repo conventions

- `.github/workflows/validate.yml`: HACS action (incl. brands check, satisfied by `custom_components/brink_flair/brand/`), hassfest, and pytest.
- Issue forms in `.github/ISSUE_TEMPLATE/` (bug report, working model report); questions go to GitHub Discussions.
- Commits use Conventional Commits prefixes (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `test:`) and are signed off (`git commit -s`). Add user-facing changes to `[Unreleased]` in `CHANGELOG.md`.
- `manifest.json` keys: `domain`, `name`, then alphabetical (hassfest).

## File layout

```
custom_components/brink_flair/
  __init__.py        # entry setup/unload — calls async_initialize() before first refresh
  manifest.json      # requires pymodbus>=3.10.0,<4 (range, not a pin — HA core constrains pymodbus)
  config_flow.py     # UI wizard: serial port, baud rate, slave ID (default 20)
  const.py           # all register addresses, value maps, framing constants
  coordinator.py     # DataUpdateCoordinator — batched polling + write helpers
  sensor.py          # 31 sensors (temperatures, flows, RPM, pressure, humidity, CO2, status)
  binary_sensor.py   # filter_dirty (register 4100)
  select.py          # ventilation mode (8001), bypass mode (6100)
  number.py          # 21 number entities
  switch.py          # standby (8003), bypass boost (6104), CO2 mode (6150)
  button.py          # filter reset (8010), appliance reset (8011)
  strings.json       # UI strings (source of truth)
  translations/
    en.json          # English translations (mirror of strings.json)
  brand/             # icon/logo PNGs (light + dark, 1x + @2x) shown in HA and HACS
homeassistant/       # example dashboards (EN/CS) and Boost script
tests/               # pytest suite (fake Modbus device in conftest.py)
.github/             # CI workflow and issue forms
hacs.json            # HACS metadata (min HA 2025.9.0)
```
