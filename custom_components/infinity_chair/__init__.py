"""The Infinity / Rongtai massage chair integration (BLE via Bluetooth proxies)."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .coordinator import InfinityChairCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]

type InfinityChairConfigEntry = ConfigEntry[InfinityChairCoordinator]

SERVICE_SEND_COMMAND = "send_command"
ATTR_MESSAGE_ID = "message_id"
SEND_COMMAND_SCHEMA = vol.Schema(
    {vol.Required(ATTR_MESSAGE_ID): vol.All(cv.positive_int, vol.Range(min=0, max=255))}
)


def _register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return

    async def _handle_send_command(call: ServiceCall) -> None:
        message_id = call.data[ATTR_MESSAGE_ID]
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            raise HomeAssistantError("No Infinity chair is configured")
        for entry in entries:
            await entry.runtime_data.send_command(message_id)

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_COMMAND, _handle_send_command, schema=SEND_COMMAND_SCHEMA
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: InfinityChairConfigEntry
) -> bool:
    """Set up Infinity chair from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    coordinator = InfinityChairCoordinator(hass, address)
    await coordinator.async_start()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: InfinityChairConfigEntry
) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded
