"""BLE connection + status coordinator for the Infinity chair.

Connects to the chair through Home Assistant's Bluetooth stack (i.e. via any ESPHome/Shelly
Bluetooth proxy in range with active connections), holds the connection open to receive status
notifications, and sends command frames. Reconnects automatically when the chair reappears.
"""

from __future__ import annotations

import asyncio
import logging

from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BLEAK_RETRY_EXCEPTIONS,
    BleakClientWithServiceCache,
    BleakError,
    establish_connection,
)

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .protocol import (
    COMMAND_CHAR_UUID,
    STATUS_CHAR_UUID,
    ChairState,
    build_frame,
    parse_status,
)

_LOGGER = logging.getLogger(__name__)


class InfinityChairCoordinator(DataUpdateCoordinator[ChairState | None]):
    """Owns the BLE connection to one chair and pushes its decoded status to entities."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_{address}", update_interval=None)
        self.address = address
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self._expected_disconnect = False
        self._unsub_bluetooth: CALLBACK_TYPE | None = None

    @property
    def connected(self) -> bool:
        """Whether a live BLE connection to the chair exists."""
        return self._client is not None and self._client.is_connected

    async def async_start(self) -> None:
        """Begin: attempt an initial connection and watch for the chair to (re)appear."""
        self._unsub_bluetooth = bluetooth.async_register_callback(
            self.hass,
            self._async_on_bluetooth_event,
            BluetoothCallbackMatcher(address=self.address, connectable=True),
            BluetoothScanningMode.ACTIVE,
        )
        await self._async_reconnect()

    async def async_stop(self) -> None:
        """Tear down: stop watching and disconnect."""
        self._expected_disconnect = True
        if self._unsub_bluetooth is not None:
            self._unsub_bluetooth()
            self._unsub_bluetooth = None
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def send_command(self, message_id: int) -> None:
        """Send a chair command by messageId, connecting first if needed."""
        try:
            await self._async_ensure_connected()
            assert self._client is not None
            await self._client.write_gatt_char(
                COMMAND_CHAR_UUID, build_frame(message_id), response=False
            )
        except (*BLEAK_RETRY_EXCEPTIONS, BleakError) as err:
            raise HomeAssistantError(f"Failed to send command to chair: {err}") from err

    async def _async_ensure_connected(self) -> None:
        if self.connected:
            return
        async with self._lock:
            if self.connected:
                return
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if ble_device is None:
                raise BleakError(
                    f"{self.address} not reachable via any Bluetooth proxy/adapter"
                )
            self._expected_disconnect = False
            client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                self.address,
                disconnected_callback=self._on_disconnect,
            )
            await client.start_notify(STATUS_CHAR_UUID, self._on_notify)
            self._client = client
            _LOGGER.debug("%s connected", self.address)
            self.async_update_listeners()

    @callback
    def _on_notify(self, _characteristic, data: bytearray) -> None:
        state = parse_status(bytes(data))
        if state is not None:
            self.async_set_updated_data(state)

    @callback
    def _on_disconnect(self, _client: BleakClientWithServiceCache) -> None:
        self._client = None
        if not self._expected_disconnect:
            _LOGGER.debug("%s disconnected; will reconnect when seen again", self.address)
        self.async_update_listeners()

    @callback
    def _async_on_bluetooth_event(
        self, _service_info: BluetoothServiceInfoBleak, _change: BluetoothChange
    ) -> None:
        if not self.connected:
            self.hass.async_create_task(self._async_reconnect())

    async def _async_reconnect(self) -> None:
        try:
            await self._async_ensure_connected()
        except (*BLEAK_RETRY_EXCEPTIONS, BleakError) as err:
            _LOGGER.debug("%s connect attempt failed: %s", self.address, err)
