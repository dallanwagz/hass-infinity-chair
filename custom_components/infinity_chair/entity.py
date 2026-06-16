"""Shared base entity for the Infinity chair."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import InfinityChairCoordinator


class InfinityChairEntity(CoordinatorEntity[InfinityChairCoordinator]):
    """Base entity tying all chair entities to one device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: InfinityChairCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
            manufacturer=MANUFACTURER,
            name="Massage chair",
        )
