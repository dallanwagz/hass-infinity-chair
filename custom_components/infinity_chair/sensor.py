"""Sensors for the Infinity chair: 3D strength, active program, and raw status (diagnostic)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InfinityChairConfigEntry
from .entity import InfinityChairEntity

PROGRAM_OPTIONS = [
    "recover",
    "stretch",
    "relax",
    "pain_recovery",
    "upper_body",
    "lower_body",
    "manual",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InfinityChairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the chair's sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            InfinityChairStrengthSensor(coordinator),
            InfinityChairAirbagStrengthSensor(coordinator),
            InfinityChairProgramSensor(coordinator),
            InfinityChairRawStatusSensor(coordinator),
        ]
    )


class InfinityChairAirbagStrengthSensor(InfinityChairEntity, SensorEntity):
    """Airbag strength level (0 = off, 1-5)."""

    _attr_translation_key = "airbag_strength"
    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "airbag_strength")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.airbag_strength


class InfinityChairStrengthSensor(InfinityChairEntity, SensorEntity):
    """3D strength / roller-depth level (1-5)."""

    _attr_translation_key = "strength"
    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "strength")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.strength


class InfinityChairProgramSensor(InfinityChairEntity, SensorEntity):
    """Active program (decoded from status byte 13)."""

    _attr_translation_key = "program"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PROGRAM_OPTIONS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "program")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.program


class InfinityChairRawStatusSensor(InfinityChairEntity, SensorEntity):
    """Raw status frame as hex, for diagnostics / further decoding."""

    _attr_translation_key = "raw_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "raw_status")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.raw
