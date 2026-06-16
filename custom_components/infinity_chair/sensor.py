"""Diagnostic sensors for the Infinity chair (raw/partial status)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InfinityChairConfigEntry
from .entity import InfinityChairEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InfinityChairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up diagnostic status sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            InfinityChairIntensitySensor(coordinator),
            InfinityChairProgramSensor(coordinator),
            InfinityChairRawStatusSensor(coordinator),
        ]
    )


class InfinityChairIntensitySensor(InfinityChairEntity, SensorEntity):
    """Massage intensity / strength level (1-5)."""

    _attr_translation_key = "intensity"
    _attr_icon = "mdi:gauge"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "intensity")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.intensity


class InfinityChairProgramSensor(InfinityChairEntity, SensorEntity):
    """Active program/technique code (byte 2 of the status frame)."""

    _attr_translation_key = "program"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "program")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
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
