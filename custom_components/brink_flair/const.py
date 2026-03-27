"""Constants for the Brink Flair integration."""

DOMAIN = "brink_flair"

# Config entry keys
CONF_SERIAL_PORT = "serial_port"
CONF_BAUD_RATE = "baud_rate"
CONF_SLAVE_ID = "slave_id"

# Defaults — Brink factory: slave=20, 19200 baud, 8E1
DEFAULT_BAUD_RATE = 19200
DEFAULT_SLAVE_ID = 20
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Serial framing fixed at 8E1 for all Brink Flair units
SERIAL_BYTESIZE = 8
SERIAL_PARITY = "E"
SERIAL_STOPBITS = 1

# ---------------------------------------------------------------------------
# Input registers (FC 0x04) — read-only, addresses 4000–4544
# Temperatures: signed 16-bit, value in tenths of °C (÷10 → °C)
# Humidity:     unsigned 16-bit, value in tenths of % (÷10 → %)
# Pressure:     signed 16-bit, value in tenths of Pa (÷10 → Pa)
# Flow:         unsigned 16-bit, value in m³/h (no scaling)
# Fan speed:    unsigned 16-bit, value in RPM (no scaling)
# ---------------------------------------------------------------------------
REG_I_ACTIVE_FUNCTION = 4020
REG_I_VENTILATION_MODE = 4022
REG_I_SUPPLY_PRESSURE = 4023
REG_I_EXHAUST_PRESSURE = 4024
REG_I_SUPPLY_SETPOINT = 4031
REG_I_SUPPLY_FLOW = 4032
REG_I_SUPPLY_FAN_RPM = 4034
REG_I_SUPPLY_TEMPERATURE = 4036
REG_I_SUPPLY_HUMIDITY = 4037
REG_I_EXHAUST_SETPOINT = 4041
REG_I_EXHAUST_FLOW = 4042
REG_I_EXHAUST_FAN_RPM = 4044
REG_I_EXHAUST_TEMPERATURE = 4046
REG_I_EXHAUST_HUMIDITY = 4047
REG_I_BYPASS_STATUS = 4050
REG_I_FROST_STATUS = 4070
REG_I_FROST_HEATER_POWER = 4071
REG_I_FROST_FAN_REDUCTION = 4072
REG_I_OUTSIDE_TEMPERATURE = 4081  # NTC1
REG_I_FILTER_STATUS = 4100
REG_I_FILTER_HOURS = 4115

# ---------------------------------------------------------------------------
# Holding registers (FC 0x03 read / 0x06 write) — settings, addresses 6000–7992
# ---------------------------------------------------------------------------
REG_H_FLOW_PRESET_0 = 6000
REG_H_FLOW_PRESET_1 = 6001
REG_H_FLOW_PRESET_2 = 6002
REG_H_FLOW_PRESET_3 = 6003
REG_H_BYPASS_MODE = 6100          # 0=auto, 1=closed, 2=open
REG_H_BYPASS_TEMP_DWELLING = 6101  # tenths °C, 150–350 (15–35 °C)
REG_H_BYPASS_TEMP_OUTSIDE = 6102   # tenths °C, 70–150 (7–15 °C)
REG_H_BYPASS_HYSTERESIS = 6103     # tenths °C, 0–50 (0–5 °C)
REG_H_BYPASS_BOOST = 6104          # 0=off, 1=on
REG_H_BYPASS_BOOST_POSITION = 6105 # 0–3 (step preset)
REG_H_FROST_CONTROL_TEMP = 6110    # tenths °C, 0–30 (0–3 °C)
REG_H_FROST_MIN_INLET_TEMP = 6111  # tenths °C, 70–220 (7–22 °C)
REG_H_FILTER_CHANGE_DAYS = 6120    # 1–365 days

# ---------------------------------------------------------------------------
# Remote control registers (FC 0x03 read / 0x06 write) — commands, 8000–8011
# NOTE: Register 8000 must be written to 1 on every HA startup (Modbus switch
#       control mode). The device resets to 0 (device LCD) after power loss.
# ---------------------------------------------------------------------------
REG_RC_MODBUS_CONTROL = 8000   # 0=device LCD, 1=modbus switch, 2=modbus flow
REG_RC_VENTILATION_STEP = 8001 # 0=holiday, 1=low, 2=normal, 3=high
REG_RC_FLOW_RATE = 8002        # m³/h (requires REG_RC_MODBUS_CONTROL=2)
REG_RC_STANDBY = 8003          # 0=no action, 1=standby, 2=normal mode
REG_RC_FILTER_RESET = 8010     # write 1 to reset filter warning
REG_RC_APPLIANCE_RESET = 8011  # write 1 to reset appliance

# ---------------------------------------------------------------------------
# Value maps
# ---------------------------------------------------------------------------
ACTIVE_FUNCTION_MAP: dict[int, str] = {
    0: "standby",
    1: "bootloader",
    2: "non_blocking_error",
    3: "blocking_error",
    4: "manual",
    5: "holiday",
    6: "night_ventilation",
    7: "party",
    8: "bypass_boost",
    9: "normal_boost",
    10: "auto_co2",
    11: "auto_ebus",
    12: "auto_modbus",
    13: "auto_lan_portal",
    14: "auto_lan_local",
}

VENTILATION_MODE_MAP: dict[int, str] = {
    0: "holiday",
    1: "low",
    2: "normal",
    3: "high",
    4: "auto",
}

BYPASS_STATUS_MAP: dict[int, str] = {
    0: "initialize",
    1: "opening",
    2: "closing",
    3: "open",
    4: "closed",
}

FROST_STATUS_MAP: dict[int, str] = {
    0: "initialize",
    1: "power_up_delay",
    2: "no_frost",
    3: "no_frost_delay",
    4: "frost_control_start_delay",
    5: "wait_for_icing",
    6: "ice_detected_delay",
    7: "heating",
    8: "wait_for_free_heater",
    9: "fan_control_start_delay",
    10: "fan_control_wait_delay",
    11: "fan_control",
    12: "fan_off_delay",
    13: "fan_off",
    14: "fan_restarting",
    15: "error",
    16: "test_mode",
}

MODBUS_CONTROL_MAP: dict[int, str] = {
    0: "device_lcd",
    1: "modbus_switch",
    2: "modbus_flow",
}

# Options for select entities
VENTILATION_STEP_OPTIONS = ["holiday", "low", "normal", "high"]
BYPASS_MODE_OPTIONS = ["auto", "closed", "open"]
