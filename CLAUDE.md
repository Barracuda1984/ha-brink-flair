# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Home Assistant custom integration for Brink Flair ventilation devices. Domain: `brink_flair`. HACS-compatible.

## Architecture

Follows the standard HA `DataUpdateCoordinator` pattern:

- **`coordinator.py`** — `BrinkFlairCoordinator` polls the device on a configurable interval and stores data as a `dict`. All entities read from this shared state.
- **`__init__.py`** — creates the coordinator, calls `async_config_entry_first_refresh()`, stores it in `hass.data[DOMAIN][entry_id]`, then forwards setup to each platform.
- **`config_flow.py`** — UI config flow; currently calls `_test_connection()` which must be implemented before the flow works end-to-end.
- **`sensor.py`** — uses `BrinkFlairSensorEntityDescription` (extends `SensorEntityDescription` with a `value_fn` callable) to map coordinator data keys to entities declaratively.

## Key TODOs before the integration is functional

1. **`coordinator.py` `_fetch_data()`** — implement actual device communication (HTTP, Modbus, etc.).
2. **`config_flow.py` `_test_connection()`** — validate host/port before creating the entry.
3. **`manifest.json`** — add any PyPI requirements and update `codeowners`/`documentation` URLs.
4. **`sensor.py`** — add `SENSOR_DESCRIPTIONS` entries to match the real data model returned by `_fetch_data()`.
5. Add additional platforms (e.g. `Platform.CLIMATE`, `Platform.FAN`) to `PLATFORMS` in `__init__.py` and create the corresponding platform files.

## File layout

```
custom_components/brink_flair/
  __init__.py        # entry setup/unload
  manifest.json      # integration metadata
  config_flow.py     # UI setup wizard
  const.py           # shared constants
  coordinator.py     # DataUpdateCoordinator
  sensor.py          # sensor platform
  strings.json       # UI strings (source of truth)
  translations/
    en.json          # English translations (mirror of strings.json)
hacs.json            # HACS metadata
```
