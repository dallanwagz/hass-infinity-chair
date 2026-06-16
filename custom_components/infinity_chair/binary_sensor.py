"""Binary sensors for the Infinity chair: running state and connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the chair's binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            InfinityChairRunningSensor(coordinator),
            InfinityChairConnectedSensor(coordinator),
        ]
    )


class InfinityChairRunningSensor(InfinityChairEntity, BinarySensorEntity):
    """True while the chair is running a program."""

    _attr_translation_key = "running"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "running")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.running


class InfinityChairConnectedSensor(InfinityChairEntity, BinarySensorEntity):
    """Whether Home Assistant currently holds a BLE connection to the chair."""

    _attr_translation_key = "connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "connected")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        # CoordinatorEntity already re-renders on every async_update_listeners(), which the
        # coordinator fires on connect and disconnect — so this stays current automatically.
        return self.coordinator.connected
