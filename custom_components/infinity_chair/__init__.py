"""The Infinity / Rongtai massage chair integration (BLE via Bluetooth proxies)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .coordinator import InfinityChairCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]

type InfinityChairConfigEntry = ConfigEntry[InfinityChairCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: InfinityChairConfigEntry
) -> bool:
    """Set up Infinity chair from a config entry."""
    address: str = entry.data[CONF_ADDRESS]
    coordinator = InfinityChairCoordinator(hass, address)
    await coordinator.async_start()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: InfinityChairConfigEntry
) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded
