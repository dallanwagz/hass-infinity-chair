"""Sensors for the Infinity chair: 3D strength, active program, and raw status (diagnostic)."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime
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
    "3d",
]

STATUS_OPTIONS = ["idle", "resetting", "ready", "running"]
WIDTH_OPTIONS = ["narrow", "medium", "wide"]
PART_OPTIONS = ["whole", "partial", "point"]
TECHNIQUE_OPTIONS = ["kneading", "knocking", "sync", "tapping", "shiatsu"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InfinityChairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the chair's sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            InfinityChairStatusSensor(coordinator),
            InfinityChairTimeRemainingSensor(coordinator),
            InfinityChairStrengthSensor(coordinator),
            InfinityChairAirbagStrengthSensor(coordinator),
            InfinityChairProgramSensor(coordinator),
            InfinityChairTechniqueSensor(coordinator),
            InfinityChairRollerPositionSensor(coordinator),
            InfinityChairSpeedSensor(coordinator),
            InfinityChairWidthSensor(coordinator),
            InfinityChairFootRollerSensor(coordinator),
            InfinityChairPartSensor(coordinator),
            InfinityChairRawStatusSensor(coordinator),
        ]
    )


class InfinityChairTechniqueSensor(InfinityChairEntity, SensorEntity):
    """Active manual technique / MODE (kneading/knocking/sync/tapping/shiatsu)."""

    _attr_translation_key = "technique"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = TECHNIQUE_OPTIONS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "technique")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.technique


class InfinityChairRollerPositionSensor(InfinityChairEntity, SensorEntity):
    """Vertical roller position along the back (0% = waist, 100% = neck). Live while running."""

    _attr_translation_key = "roller_position"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:human-handsdown"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "roller_position")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.roller_position


class InfinityChairSpeedSensor(InfinityChairEntity, SensorEntity):
    """Manual massage speed level (1-6), live while running."""

    _attr_translation_key = "speed"
    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "speed")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.speed


class InfinityChairWidthSensor(InfinityChairEntity, SensorEntity):
    """Roller width (narrow/medium/wide), live while running."""

    _attr_translation_key = "width"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = WIDTH_OPTIONS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "width")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.width


class InfinityChairFootRollerSensor(InfinityChairEntity, SensorEntity):
    """Foot-roller level (0 off, 1-3)."""

    _attr_translation_key = "foot_roller"
    _attr_icon = "mdi:foot-print"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "foot_roller")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.foot_roller


class InfinityChairPartSensor(InfinityChairEntity, SensorEntity):
    """Massage scope (whole/partial/point)."""

    _attr_translation_key = "part"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PART_OPTIONS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "part")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.part


class InfinityChairStatusSensor(InfinityChairEntity, SensorEntity):
    """Run state: idle / resetting / ready / running."""

    _attr_translation_key = "status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "status")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.run_state


class InfinityChairTimeRemainingSensor(InfinityChairEntity, SensorEntity):
    """Session time remaining (only valid while a program is running)."""

    _attr_translation_key = "time_remaining"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "time_remaining")

    @property
    def available(self) -> bool:
        return self.coordinator.connected and self.coordinator.data is not None

    @property
    def native_value(self) -> int | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.time_remaining


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
