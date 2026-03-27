# Brink Flair — Home Assistant Custom Integration

Custom integration for [Brink Flair](https://www.brinkclimatesystems.nl/) ventilation units.

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add this repository URL and select category **Integration**
3. Search for **Brink Flair** and install

### Manual

Copy `custom_components/brink_flair/` into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Brink Flair**
3. Enter the host (IP address) and port of your device

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Supply Temperature | Sensor | Supply air temperature (°C) |

## Development

```bash
# Install dev dependencies
pip install homeassistant

# Run HA with this integration loaded (point config dir at repo root)
hass -c .
```

Bump the version in `custom_components/brink_flair/manifest.json` before releasing.
