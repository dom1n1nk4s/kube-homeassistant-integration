"""Data update coordinator for KUBE Gate System."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    CONF_PASSKEY,
    CONF_MASTER_KEY,
    CONF_AUTH_METHOD,
    AUTH_METHOD_PASSKEY,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class KubeDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the KUBE device."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_data: dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        self.mac_address = config_entry_data[CONF_MAC_ADDRESS]
        self.auth_method = config_entry_data[CONF_AUTH_METHOD]
        self.passkey = config_entry_data.get(CONF_PASSKEY, "")
        self.master_key = config_entry_data.get(CONF_MASTER_KEY)
        
        self._kube_commands = None
        self._last_operation_result = None
        self._connection_state = 0

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

    @property
    def kube_commands(self):
        """Get or create KubeCommands instance."""
        if self._kube_commands is None:
            from .kube_lib import KubeCommands
            
            if self.auth_method == AUTH_METHOD_PASSKEY:
                self._kube_commands = KubeCommands(self.mac_address, self.passkey)
            else:
                self._kube_commands = KubeCommands(
                    self.mac_address, self.passkey, self.master_key
                )
        return self._kube_commands

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library using async methods."""
        try:
            # Get device status using new async method
            device_info = await self.kube_commands.get_device_status_async()
            
            # Check if we got any data (indicates successful connection)
            is_connected = bool(device_info)
            connection_state = 2 if is_connected else 0  # 2 = connected, 0 = disconnected
            
            self._connection_state = connection_state
            
            return {
                "connection_state": connection_state,
                "is_connected": is_connected,
                "mac_address": self.mac_address,
                "device_info": device_info,
                "last_operation_result": self._last_operation_result,
            }

        except Exception as err:
            _LOGGER.error("Error communicating with KUBE device: %s", err)
            # Set disconnected state on error
            self._connection_state = 0
            return {
                "connection_state": 0,
                "is_connected": False,
                "mac_address": self.mac_address,
                "device_info": {},
                "last_operation_result": self._last_operation_result,
            }

    async def async_execute_command(self, command_name: str, **kwargs) -> bool:
        """Execute a command on the KUBE device using async methods."""
        try:
            _LOGGER.debug("Executing command: %s", command_name)
            
            success = False
            if command_name == "open_door":
                success = await self.kube_commands.open_door_async()
            elif command_name == "close_door":
                success = await self.kube_commands.close_door_async()
            elif command_name == "toggle_door":
                success = await self.kube_commands.toggle_door_async()
            elif command_name == "open_slightly":
                success = await self.kube_commands.open_slightly_async()
            elif command_name == "control_lights":
                success = await self.kube_commands.control_lights_async()
            else:
                _LOGGER.error("Unknown command: %s", command_name)
                return False

            _LOGGER.debug("Command %s executed: %s", command_name, "success" if success else "failed")
            self._last_operation_result = {
                "command": command_name,
                "success": success,
            }
            
            # Trigger a data update after command execution
            await self.async_request_refresh()
            
            return success

        except Exception as err:
            _LOGGER.error("Error executing command %s: %s", command_name, err)
            self._last_operation_result = {
                "command": command_name,
                "error": str(err),
                "success": False,
            }
            return False

    async def async_connect(self) -> bool:
        """Connect to the KUBE device using async method."""
        try:
            # Use the new async connect and authenticate method
            success = await self.kube_commands._connect_and_authenticate_async()
            _LOGGER.debug("Connect result: %s", "success" if success else "failed")
            
            if success:
                self._connection_state = 2  # Connected
            else:
                self._connection_state = 0  # Disconnected
            
            return success
            
        except Exception as err:
            _LOGGER.error("Error connecting to device: %s", err)
            self._connection_state = 0
            return False

    async def async_disconnect(self) -> bool:
        """Disconnect from the KUBE device using async method."""
        try:
            # Disconnect any active connections
            await self.kube_commands.kube_bt_client.cleanup()
            _LOGGER.debug("Disconnect completed")
            self._connection_state = 0
            return True
            
        except Exception as err:
            _LOGGER.error("Error disconnecting from device: %s", err)
            return False

    @property
    def is_connected(self) -> bool:
        """Return if device is connected."""
        return self._connection_state != 0

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.mac_address)},
            "name": f"KUBE Gate ({self.mac_address})",
            "manufacturer": "KUBE",
            "model": "Gate System",
            "sw_version": "1.0",
            "via_device": None,
        }
