"""Tests for the Brink Flair sensor platform — translated ENUM status sensors."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.brink_flair.const import (
    ACTIVE_FUNCTION_MAP,
    BYPASS_MODE_OPTIONS,
    BYPASS_STATUS_MAP,
    CO2_STATUS_MAP,
    DOMAIN,
    FROST_STATUS_MAP,
    VENTILATION_MODE_MAP,
    VENTILATION_STEP_OPTIONS,
)
from tests.conftest import ENTRY_DATA

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / DOMAIN
TRANSLATION_FILES = [
    COMPONENT_DIR / "strings.json",
    *sorted((COMPONENT_DIR / "translations").glob("*.json")),
]

ENUM_SENSORS = {
    "active_function": ACTIVE_FUNCTION_MAP,
    "ventilation_mode": VENTILATION_MODE_MAP,
    "bypass_status": BYPASS_STATUS_MAP,
    "frost_status": FROST_STATUS_MAP,
    "co2_status": CO2_STATUS_MAP,
}
SELECTS = {
    "ventilation_step": VENTILATION_STEP_OPTIONS,
    "bypass_mode": BYPASS_MODE_OPTIONS,
}


async def _setup(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_DATA,
        unique_id=f"{ENTRY_DATA['serial_port']}_{ENTRY_DATA['slave_id']}",
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("entity_id", "expected", "value_map"),
    [
        ("sensor.brink_flair_400_status", "auto_modbus", ACTIVE_FUNCTION_MAP),
        ("sensor.brink_flair_400_ventilation_mode", "normal", VENTILATION_MODE_MAP),
        ("sensor.brink_flair_400_bypass_status", "closed", BYPASS_STATUS_MAP),
        ("sensor.brink_flair_400_frost_status", "no_frost", FROST_STATUS_MAP),
        ("sensor.brink_flair_400_co2_sensor_1_status", "error", CO2_STATUS_MAP),
    ],
)
async def test_enum_sensor_state_and_options(
    hass, mock_modbus_client, entity_id, expected, value_map
):
    """Status sensors keep raw state keys (automations unaffected) and expose options."""
    await _setup(hass)

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == expected
    assert state.attributes["device_class"] == "enum"
    assert state.attributes["options"] == list(value_map.values())


async def test_enum_sensor_unknown_raw_value(hass, mock_modbus_client):
    """A raw value outside the map shows as unknown instead of failing."""
    mock_modbus_client.input_registers[4020] = 99
    await _setup(hass)

    assert hass.states.get("sensor.brink_flair_400_status").state == STATE_UNKNOWN


@pytest.mark.parametrize("path", TRANSLATION_FILES, ids=lambda p: p.name)
def test_translations_cover_all_states(path: Path):
    """Every translation file translates every state of every ENUM sensor and select."""
    entity = json.loads(path.read_text(encoding="utf-8"))["entity"]
    for key, value_map in ENUM_SENSORS.items():
        assert set(entity["sensor"][key]["state"]) == set(value_map.values()), key
    for key, options in SELECTS.items():
        assert set(entity["select"][key]["state"]) == set(options), key


def test_translation_files_have_same_structure():
    """translations/en.json mirrors strings.json; cs.json has the same keys."""
    strings = json.loads((COMPONENT_DIR / "strings.json").read_text(encoding="utf-8"))
    en = json.loads((COMPONENT_DIR / "translations" / "en.json").read_text(encoding="utf-8"))
    cs = json.loads((COMPONENT_DIR / "translations" / "cs.json").read_text(encoding="utf-8"))
    assert en == strings

    def keys(d, prefix=""):
        out = set()
        for k, v in d.items():
            out |= keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {prefix + k}
        return out

    assert keys(cs) == keys(strings)
