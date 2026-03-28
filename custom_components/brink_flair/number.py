"""Number platform for Brink Flair — flow presets and temperature thresholds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BrinkFlairCoordinator


@dataclass(frozen=True, kw_only=True)
class BrinkFlairNumberEntityDescription(NumberEntityDescription):
    """Extends NumberEntityDescription with coordinator read/write callables."""

    value_fn: Any   # Callable[[dict], float | None]
    set_fn: Any     # Callable[[BrinkFlairCoordinator, float], Coroutine]


NUMBER_DESCRIPTIONS: tuple[BrinkFlairNumberEntityDescription, ...] = (
    # ── Flow presets (holding registers 6000–6003) ────────────────────
    BrinkFlairNumberEntityDescription(
        key="flow_preset_0",
        name="Flow Holiday",
        icon="mdi:fan-auto",
        native_min_value=0,
        native_max_value=400,
        native_step=5,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.get("flow_preset_0"),
        set_fn=lambda c, v: c.async_set_flow_preset(0, round(v)),
    ),
    BrinkFlairNumberEntityDescription(
        key="flow_preset_1",
        name="Flow Low",
        icon="mdi:fan-speed-1",
        native_min_value=0,
        native_max_value=400,
        native_step=5,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.get("flow_preset_1"),
        set_fn=lambda c, v: c.async_set_flow_preset(1, round(v)),
    ),
    BrinkFlairNumberEntityDescription(
        key="flow_preset_2",
        name="Flow Normal",
        icon="mdi:fan-speed-2",
        native_min_value=0,
        native_max_value=400,
        native_step=5,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.get("flow_preset_2"),
        set_fn=lambda c, v: c.async_set_flow_preset(2, round(v)),
    ),
    BrinkFlairNumberEntityDescription(
        key="flow_preset_3",
        name="Flow High",
        icon="mdi:fan-speed-3",
        native_min_value=0,
        native_max_value=400,
        native_step=5,
        native_unit_of_measurement=UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.get("flow_preset_3"),
        set_fn=lambda c, v: c.async_set_flow_preset(3, round(v)),
    ),
    # ── Bypass temperature thresholds (holding registers 6101–6103) ───
    BrinkFlairNumberEntityDescription(
        key="bypass_temp_dwelling",
        name="Bypass Temp from Home",
        icon="mdi:home-export-outline",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=15.0,
        native_max_value=35.0,
        native_step=0.5,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.get("bypass_temp_dwelling"),
        set_fn=lambda c, v: c.async_set_bypass_temp_dwelling(v),
    ),
    BrinkFlairNumberEntityDescription(
        key="bypass_temp_outside",
        name="Bypass Temp from Outside",
        icon="mdi:home-import-outline",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=7.0,
        native_max_value=15.0,
        native_step=0.5,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.get("bypass_temp_outside"),
        set_fn=lambda c, v: c.async_set_bypass_temp_outside(v),
    ),
    BrinkFlairNumberEntityDescription(
        key="bypass_hysteresis",
        name="Bypass Hysteresis",
        icon="mdi:home-edit-outline",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0.0,
        native_max_value=5.0,
        native_step=0.5,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.get("bypass_hysteresis"),
        set_fn=lambda c, v: c.async_set_bypass_hysteresis(v),
    ),
    # ── Frost protection (holding registers 6110–6111) ────────────────
    BrinkFlairNumberEntityDescription(
        key="frost_control_temp",
        name="Frost Control Temperature",
        icon="mdi:snowflake-thermometer",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0.0,
        native_max_value=3.0,
        native_step=0.5,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.get("frost_control_temp"),
        set_fn=lambda c, v: c.async_set_frost_control_temp(v),
    ),
    BrinkFlairNumberEntityDescription(
        key="frost_min_inlet_temp",
        name="Frost Minimum Inlet Temperature",
        icon="mdi:snowflake-thermometer",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=7.0,
        native_max_value=22.0,
        native_step=0.5,
        mode=NumberMode.SLIDER,
        value_fn=lambda d: d.get("frost_min_inlet_temp"),
        set_fn=lambda c, v: c.async_set_frost_min_inlet_temp(v),
    ),
    # ── Filter warning threshold (holding register 6120) ─────────────
    BrinkFlairNumberEntityDescription(
        key="filter_change_days",
        name="Days Before Filter Warning",
        icon="mdi:timer-sync-outline",
        native_min_value=1,
        native_max_value=365,
        native_step=1,
        native_unit_of_measurement="d",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.get("filter_change_days"),
        set_fn=lambda c, v: c.async_set_filter_change_days(round(v)),
    ),
    # ── CO2 thresholds (holding registers 6151–6158) ──────────────────
    BrinkFlairNumberEntityDescription(
        key="co2_sensor_1_low",
        name="CO2 Sensor 1 Low Level",
        icon="mdi:molecule-co2",
        native_min_value=400,
        native_max_value=2000,
        native_step=1,
        native_unit_of_measurement="ppm",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.get("co2_sensor_1_low"),
        set_fn=lambda c, v: c.async_set_co2_threshold(1, round(v), round(c.data.get("co2_sensor_1_high", 2000))),
    ),
    BrinkFlairNumberEntityDescription(
        key="co2_sensor_1_high",
        name="CO2 Sensor 1 High Level",
        icon="mdi:molecule-co2",
        native_min_value=400,
        native_max_value=2000,
        native_step=1,
        native_unit_of_measurement="ppm",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.get("co2_sensor_1_high"),
        set_fn=lambda c, v: c.async_set_co2_threshold(1, round(c.data.get("co2_sensor_1_low", 400)), round(v)),
    ),
    BrinkFlairNumberEntityDescription(
        key="co2_sensor_2_low",
        name="CO2 Sensor 2 Low Level",
        icon="mdi:molecule-co2",
        native_min_value=400,
        native_max_value=2000,
        native_step=1,
        native_unit_of_measurement="ppm",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.get("co2_sensor_2_low"),
        set_fn=lambda c, v: c.async_set_co2_threshold(2, round(v), round(c.data.get("co2_sensor_2_high", 2000))),
    ),
    BrinkFlairNumberEntityDescription(
        key="co2_sensor_2_high",
        name="CO2 Sensor 2 High Level",
        icon="mdi:molecule-co2",
        native_min_value=400,
        native_max_value=2000,
        native_step=1,
        native_unit_of_measurement="ppm",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.get("co2_sensor_2_high"),
        set_fn=lambda c, v: c.async_set_co2_threshold(2, round(c.data.get("co2_sensor_2_low", 400)), round(v)),
    ),
    BrinkFlairNumberEntityDescription(
        key="co2_sensor_3_low",
        name="CO2 Sensor 3 Low Level",
        icon="mdi:molecule-co2",
        native_min_value=400,
        native_max_value=2000,
        native_step=1,
        native_unit_of_measurement="ppm",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.get("co2_sensor_3_low"),
        set_fn=lambda c, v: c.async_set_co2_threshold(3, round(v), round(c.data.get("co2_sensor_3_high", 2000))),
    ),
    BrinkFlairNumberEntityDescription(
        key="co2_sensor_3_high",
        name="CO2 Sensor 3 High Level",
        icon="mdi:molecule-co2",
        native_min_value=400,
        native_max_value=2000,
        native_step=1,
        native_unit_of_measurement="ppm",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.get("co2_sensor_3_high"),
        set_fn=lambda c, v: c.async_set_co2_threshold(3, round(c.data.get("co2_sensor_3_low", 400)), round(v)),
    ),
    BrinkFlairNumberEntityDescription(
        key="co2_sensor_4_low",
        name="CO2 Sensor 4 Low Level",
        icon="mdi:molecule-co2",
        native_min_value=400,
        native_max_value=2000,
        native_step=1,
        native_unit_of_measurement="ppm",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.get("co2_sensor_4_low"),
        set_fn=lambda c, v: c.async_set_co2_threshold(4, round(v), round(c.data.get("co2_sensor_4_high", 2000))),
    ),
    BrinkFlairNumberEntityDescription(
        key="co2_sensor_4_high",
        name="CO2 Sensor 4 High Level",
        icon="mdi:molecule-co2",
        native_min_value=400,
        native_max_value=2000,
        native_step=1,
        native_unit_of_measurement="ppm",
        mode=NumberMode.BOX,
        value_fn=lambda d: d.get("co2_sensor_4_high"),
        set_fn=lambda c, v: c.async_set_co2_threshold(4, round(c.data.get("co2_sensor_4_low", 400)), round(v)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Brink Flair number entities."""
    coordinator: BrinkFlairCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BrinkFlairNumberEntity(coordinator, description)
        for description in NUMBER_DESCRIPTIONS
    )


class BrinkFlairNumberEntity(
    CoordinatorEntity[BrinkFlairCoordinator], NumberEntity
):
    """Represents a configurable numeric setting on the Brink Flair 400."""

    entity_description: BrinkFlairNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairNumberEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.serial_port}_{coordinator.slave_id}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.serial_port}_{coordinator.slave_id}")},
            name="Brink Flair 400",
            manufacturer="Brink",
            model="Flair 400",
        )

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data or {})

    async def async_set_native_value(self, value: float) -> None:
        await self.entity_description.set_fn(self.coordinator, value)
