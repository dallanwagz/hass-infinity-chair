"""Command buttons for the Infinity chair."""

from __future__ import annotations

import asyncio

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import InfinityChairConfigEntry
from .coordinator import InfinityChairCoordinator
from .entity import InfinityChairEntity
from .protocol import COMMANDS

_POWER = COMMANDS["power"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InfinityChairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one button per chair command, plus the Return to origin helper."""
    coordinator = entry.runtime_data
    entities: list[ButtonEntity] = [
        InfinityChairButton(coordinator, key, message_id)
        for key, message_id in COMMANDS.items()
    ]
    entities.append(InfinityChairReturnToOriginButton(coordinator))
    async_add_entities(entities)


class InfinityChairReturnToOriginButton(InfinityChairEntity, ButtonEntity):
    """Bring the chair back to the upright/home position regardless of current state.

    Powering off triggers the chair's reset-to-home. If the chair is already stopped (e.g. left
    reclined after a session) a plain power-off does nothing, so we power on, wait, then power off.
    """

    _attr_translation_key = "return_to_origin"
    _attr_icon = "mdi:seat-recline-normal"

    def __init__(self, coordinator: InfinityChairCoordinator) -> None:
        super().__init__(coordinator, "return_to_origin")

    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        data = self.coordinator.data
        state = data.run_state if data else None
        if state == "resetting":
            return  # already heading home
        if state in ("running", "ready"):
            await self.coordinator.send_command(_POWER)  # power off -> resets to home
            return
        # idle / off (possibly reclined) or unknown: power on, settle, power off -> reset to home
        await self.coordinator.send_command(_POWER)
        await asyncio.sleep(4)
        await self.coordinator.send_command(_POWER)


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
