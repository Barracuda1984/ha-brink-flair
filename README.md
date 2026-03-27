# Brink Flair — Home Assistant Custom Integration

Custom integration for the **Brink Flair 400** (and other Flair models) communicating directly with Home Assistant via **Modbus RTU over RS-485** — no ESP board required.

## Requirements

- RS-485 to USB adapter (or RS-485 hat) wired to the Brink Flair Modbus connector
  - Standard model: connector **X15** on PCB UWA2-B
  - Plus model: connector **X06** on Plus PCB UWA2-E
- Serial framing is fixed at **8E1** (8 data bits, even parity, 1 stop bit)
- Home Assistant 2024.1.0 or newer

## Device configuration

On the Brink Flair touchscreen set:

| Menu | Setting | Factory default |
|------|---------|-----------------|
| 14.1 Type of Bus | Modbus | — |
| 14.2 Slave address | _(unique per device)_ | **20** |
| 14.3 Baudrate | _(must match HA config)_ | **19200** |
| 14.4 Parity | Even | Even |

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
3. Enter the connection parameters:

| Field | Description | Default |
|-------|-------------|---------|
| Serial port | Path to RS-485 adapter (e.g. `/dev/ttyUSB0`) | — |
| Baud rate | Must match device menu 14.3 | `19200` |
| Modbus slave address | Must match device menu 14.2 | `20` |

> On every HA startup the integration writes register 8000 = 1 to enable Modbus switch-control mode. The device resets this to 0 on power loss.

## Entities

### Sensors
| Entity | Unit | Description |
|--------|------|-------------|
| Temperature to Inside | °C | Supply fan temperature (register 4036) |
| Temperature to Outside | °C | Exhaust fan temperature (register 4046) |
| Temperature from Outside | °C | NTC1 outdoor temperature (register 4081) |
| Humidity to Inside | % | Supply fan relative humidity (register 4037) |
| Humidity to Outside | % | Exhaust fan relative humidity (register 4047) |
| Current Intake Air Volume | m³/h | Actual supply flow (register 4032) |
| Setpoint Intake Air Volume | m³/h | Desired supply flow (register 4031) |
| Current Exhaust Air Volume | m³/h | Actual exhaust flow (register 4042) |
| Setpoint Exhaust Air Volume | m³/h | Desired exhaust flow (register 4041) |
| Speed Supply Fan | RPM | Supply fan speed (register 4034) |
| Speed Exhaust Fan | RPM | Exhaust fan speed (register 4044) |
| Supply Pressure | Pa | Duct pressure supply side (register 4023) |
| Exhaust Pressure | Pa | Duct pressure exhaust side (register 4024) |
| Frost Heater Power | % | Pre-heater output (register 4071) |
| Frost Fan Reduction | % | Fan speed reduction during frost (register 4072) |
| Current Filter Hours | h | Hours since last filter reset (register 4115) |
| Status | — | Active function text (register 4020) |
| Ventilation Mode | — | Current operational mode (register 4022) |
| Bypass Status | — | Bypass valve state (register 4050) |
| Frost Status | — | Frost protection state (register 4070) |

### Binary sensor
| Entity | Description |
|--------|-------------|
| Filter Dirty | On when filter needs replacement (register 4100) |

### Select
| Entity | Options | Description |
|--------|---------|-------------|
| Ventilation Mode | holiday / low / normal / high | Sets register 8001 |
| Bypass Mode | auto / closed / open | Sets register 6100 |

### Number (sliders)
| Entity | Range | Description |
|--------|-------|-------------|
| Flow Holiday | 0–400 m³/h | Flow preset 0 (register 6000) |
| Flow Low | 0–400 m³/h | Flow preset 1 (register 6001) |
| Flow Normal | 0–400 m³/h | Flow preset 2 (register 6002) |
| Flow High | 0–400 m³/h | Flow preset 3 (register 6003) |
| Bypass Temp from Home | 15–35 °C | Register 6101 |
| Bypass Temp from Outside | 7–15 °C | Register 6102 |
| Bypass Hysteresis | 0–5 °C | Register 6103 |
| Frost Control Temperature | 0–3 °C | Register 6110 |
| Frost Minimum Inlet Temperature | 7–22 °C | Register 6111 |
| Days Before Filter Warning | 1–365 d | Register 6120 |

### Buttons
| Entity | Description |
|--------|-------------|
| Filter Reset | Writes 1 to register 8010 |
| Appliance Reset | Writes 1 to register 8011 _(disabled by default)_ |

## Development

```bash
# Install dev dependencies
pip install homeassistant pymodbus==3.9.2

# Run HA with this integration loaded
hass -c .
```

Bump the version in `custom_components/brink_flair/manifest.json` before releasing.
