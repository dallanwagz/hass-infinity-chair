"""Command buttons for the Infinity chair."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InfinityChairConfigEntry
from .coordinator import InfinityChairCoordinator
from .entity import InfinityChairEntity
from .protocol import COMMANDS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InfinityChairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one button per chair command."""
    coordinator = entry.runtime_data
    async_add_entities(
        InfinityChairButton(coordinator, key, message_id)
        for key, message_id in COMMANDS.items()
    )


class InfinityChairButton(InfinityChairEntity, ButtonEntity):
    """A momentary button that sends one chair command."""

    def __init__(
        self, coordinator: InfinityChairCoordinator, key: str, message_id: int
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._message_id = message_id

    @property
    def available(self) -> bool:
        # Always available: pressing a button will connect on demand if needed.
        return True

    async def async_press(self) -> None:
        await self.coordinator.send_command(self._message_id)
