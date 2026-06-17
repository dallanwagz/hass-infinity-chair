"""Binary sensors for the Infinity chair: running, heat, airbag zones, connectivity."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InfinityChairConfigEntry
from .entity import InfinityChairEntity
from .protocol import ChairState


@dataclass(frozen=True, kw_only=True)
class ChairBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a chair binary sensor derived from a decoded ChairState field."""

    value_fn: Callable[[ChairState], bool]


# Data-driven sensors (available only while connected, value comes from the status frame).
STATE_SENSORS: tuple[ChairBinarySensorDescription, ...] = (
    ChairBinarySensorDescription(
        key="running",
        translation_key="running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda s: s.running,
    ),
    ChairBinarySensorDescription(
        key="heat",
        translation_key="heat",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda s: s.heat,
    ),
    ChairBinarySensorDescription(
        key="ionizer",
        translation_key="ionizer",
        value_fn=lambda s: s.ionizer,
    ),
    ChairBinarySensorDescription(
        key="zero_gravity",
        translation_key="zero_gravity",
        value_fn=lambda s: s.zero_gravity,
    ),
    ChairBinarySensorDescription(
        key="airbag_arm_shoulder",
        translation_key="airbag_arm_shoulder",
        value_fn=lambda s: s.airbag_arm_shoulder,
    ),
    ChairBinarySensorDescription(
        key="airbag_back_waist",
        translation_key="airbag_back_waist",
        value_fn=lambda s: s.airbag_back_waist,
    ),
    ChairBinarySensorDescription(
        key="airbag_leg_foot",
        translation_key="airbag_leg_foot",
        value_fn=lambda s: s.airbag_leg_foot,
    ),
    ChairBinarySensorDescription(
        key="airbag_buttock",
        translation_key="airbag_buttock",
        value_fn=lambda s: s.airbag_buttock,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InfinityChairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the chair's binary sensors."""
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = [
        InfinityChairStateBinarySensor(coordinator, desc) for desc in STATE_SENSORS
    ]
    entities.append(InfinityChairConnectedSensor(coordinator))
    async_add_entities(entities)


class InfinityChairStateBinarySensor(InfinityChairEntity, BinarySensorEntity):
    """A binary sensor whose value is decoded from the latest status frame."""

    entity_description: ChairBinarySensorDescription

    def __init__(self, coordinator, description: ChairBinarySensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


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
        # CoordinatorEntity re-renders on every async_update_listeners(), which the coordinator
        # fires on connect and disconnect, so this stays current automatically.
        return self.coordinator.connected
