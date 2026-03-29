# Changelog

All notable changes to this project will be documented in this file.

## [0.1.4] — Unreleased

### Added
- Boost script (`homeassistant/scripts.yaml`) — switches ventilation to High for 30 minutes then restores the previous mode
- Boost button added to the ventilation section of both dashboards (EN and CS)
- CO2 sensors (PPM values) added to both dashboards — entities card and 24 h history graph

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
