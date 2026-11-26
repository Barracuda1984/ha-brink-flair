# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Translated states (English, Czech) for the status sensors — Status, Ventilation Mode, Bypass Status, Frost Status and CO2 sensor status — and for the Ventilation Mode and Bypass Mode selects. The UI now shows e.g. "Auto (Modbus)" / "Bez mrazu" instead of `auto_modbus` / `no_frost`. Entity states stay the same raw keys, so automations and dashboards keep working.

### Fixed
- Optional sensors that are not fitted no longer report bogus values: NTC2 (999.9 °C) and the NTC1 outside sensor when disconnected or out of range, RHT humidity (0 %), and CO2 sensors that are not initialized or in error (0 ppm) now show as *unknown*
- Czech dashboard (`homeassistant/dashboard_cs.yaml`) was invalid YAML — the ventilation mode block was indented one level too deep

### Changed
- Example dashboards no longer show NTC2 and RHT humidity (optional sensors, not fitted on most units)

### Docs
- README: credits to [fonske/Brink-flair-modbus](https://github.com/fonske/Brink-flair-modbus)

---

## [1.0.0] — 2026-11-26

First stable release. No changes to entities or Modbus behaviour compared to 0.1.4 — existing installations update without reconfiguration.

### ⚠️ Breaking
- Minimum Home Assistant version is now **2025.9.0** (first release shipping pymodbus ≥ 3.10, which the integration already required)

### Added
- Brand icons and logos (light and dark) bundled in `custom_components/brink_flair/brand/`

### Changed
- `manifest.json`: codeowner set to `@Barracuda1984`, documentation links to the README, keys sorted per hassfest
- `hacs.json`: removed obsolete `render_readme` option

### Tests
- Fixed the test suite (all tests were failing): custom integrations are now enabled in pytest, and the Modbus mock answers by register address instead of call order
- New tests for 32-bit operating time, signed imbalance offsets, CO2 registers, device version decoding and all write helpers (coverage 97 %)
- `pyserial` added to `requirements_test.txt`
- CI: new GitHub Actions workflow with HACS, hassfest and test jobs

### Docs
- README: badges, My Home Assistant buttons, compatibility table, hardware and wiring guide (tested adapter, A/B/GND wiring), complete entity tables
- New `CONTRIBUTING.md` and GitHub issue forms (bug report, working model report)

---

## [0.1.4] — 2026-11-21

### Added
- Boost script (`homeassistant/scripts.yaml`) — switches ventilation to High for 30 minutes then restores the previous mode
- Boost button added to the ventilation section of both dashboards (EN and CS)
- CO2 sensors (PPM values) added to both dashboards — entities card and 24 h history graph

### Fixed
- Setup failure on HA 2026.11 (`Requirements for brink_flair not found: ['pymodbus==3.11.2']`): requirement relaxed to `pymodbus>=3.10.0,<4` so it no longer conflicts with the pymodbus version pinned by HA core

### Docs
- README: new *Boost script* section covering helper setup and installation steps

---

## [0.1.3] — 2026-03-28

### Added
- New sensors: NTC2 temperature, RHT humidity, operating time, supply/exhaust imbalance offsets, bypass boost position
- Dashboards updated with all new sensors and controls

---

## [0.1.2] — 2026-03-28

### Fixed
- Removed incorrect ÷10 scaling applied to humidity and pressure register values

---

## [0.1.1] — 2026-03-28

### Added
- Device info populated with hardware/software version and serial number
- CO2 sensor support — 4 sensors, PPM values and status (registers 4200–4207, 6150–6158)

---

## [0.1.0] — 2026-03-28

### Added
- Initial integration: Brink Flair 400 Modbus RTU over RS-485 (`pymodbus`)
- Full sensor set: temperatures, humidity, air flow, fan RPM, pressure, frost, filter
- Select entities: ventilation mode, bypass mode
- Number entities: flow presets, bypass/frost temperatures, filter days
- Binary sensor: filter dirty
- Buttons: filter reset, appliance reset
- Bypass boost and standby switches
- Lovelace dashboards in English and Czech
- HACS-compatible structure, config flow, test environment

---
