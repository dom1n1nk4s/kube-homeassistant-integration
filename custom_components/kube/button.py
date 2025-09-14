"""Button platform for KUBE Gate System."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ENTITY_OPEN_GATE,
    ENTITY_CLOSE_GATE,
    ENTITY_TOGGLE_GATE,
    ENTITY_OPEN_SLIGHTLY,
    ENTITY_DEVICE_INFO,
    ATTR_MAC_ADDRESS,
    ATTR_LAST_OPERATION,
    ATTR_OPERATION_RESULT,
)
from .coordinator import KubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KUBE button entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        KubeGateButton(coordinator, ENTITY_OPEN_GATE, "Open Gate", "open_door"),
        KubeGateButton(coordinator, ENTITY_CLOSE_GATE, "Close Gate", "close_door"),
        KubeGateButton(coordinator, ENTITY_TOGGLE_GATE, "Toggle Gate", "toggle_door"),
        KubeGateButton(coordinator, ENTITY_OPEN_SLIGHTLY, "Open Slightly", "open_slightly"),
        KubeDeviceInfoButton(coordinator, ENTITY_DEVICE_INFO, "Device Info"),
    ]

    async_add_entities(entities)


class KubeGateButton(CoordinatorEntity, ButtonEntity):
    """Representation of a KUBE gate control button."""

    def __init__(
        self,
        coordinator: KubeDataUpdateCoordinator,
        entity_id: str,
        name: str,
        command: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._name = name
        self._command = command
        self._attr_unique_id = f"{coordinator.mac_address}_{entity_id}"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return self._name

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # For connect-per-command pattern, buttons are available if:
        # 1. We have coordinator data (integration is loaded)
        # 2. We're not in a persistent error state
        if not self.coordinator.data:
            return False
        
        # Always available for connect-per-command pattern
        # Individual command failures don't make the button unavailable
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            ATTR_MAC_ADDRESS: self.coordinator.mac_address,
        }
        
        # Add last operation info if available
        if self.coordinator.data and "last_operation_result" in self.coordinator.data:
            last_op = self.coordinator.data["last_operation_result"]
            if last_op and last_op.get("command") == self._command:
                attrs[ATTR_LAST_OPERATION] = last_op.get("command")
                attrs[ATTR_OPERATION_RESULT] = "success" if last_op.get("success") else "failed"
        
        return attrs

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.debug("Button pressed: %s", self._command)
        
        success = await self.coordinator.async_execute_command(self._command)
        
        if not success:
            _LOGGER.error("Failed to execute command: %s", self._command)
        else:
            _LOGGER.debug("Successfully executed command: %s", self._command)

    @property
    def icon(self) -> str:
        """Return the icon for the button."""
        if self._entity_id == ENTITY_OPEN_GATE:
            return "mdi:gate-open"
        elif self._entity_id == ENTITY_CLOSE_GATE:
            return "mdi:gate"
        elif self._entity_id == ENTITY_TOGGLE_GATE:
            return "mdi:gate-arrow-right"
        elif self._entity_id == ENTITY_OPEN_SLIGHTLY:
            return "mdi:gate-buffer"
        return "mdi:gate"


class KubeDeviceInfoButton(CoordinatorEntity, ButtonEntity):
    """Representation of a KUBE device info button that shows device information."""

    def __init__(
        self,
        coordinator: KubeDataUpdateCoordinator,
        entity_id: str,
        name: str,
    ) -> None:
        """Initialize the device info button."""
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._name = name
        self._attr_unique_id = f"{coordinator.mac_address}_{entity_id}"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return self._name

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Device info button is always available
        return True

    @property
    def icon(self) -> str:
        """Return the icon for the button."""
        return "mdi:information-outline"

    async def async_press(self) -> None:
        """Handle the button press - fetch device info and show as notification."""
        _LOGGER.debug("Device info button pressed")
        
        try:
            # Fetch fresh device information
            device_info = await self.coordinator.async_fetch_device_info()
            
            # Format the information for display
            info_lines = [
                f"🏠 **{device_info.get('device_name', 'KUBE Gate')}**",
                "",
                f"📍 **MAC Address:** {device_info.get('mac_address', 'Unknown')}",
                f"🏭 **Manufacturer:** {device_info.get('manufacturer', 'KUBE')}",
                f"📦 **Model:** {device_info.get('model', 'Gate System')}",
                f"🔧 **Software Version:** {device_info.get('sw_version', '1.0')}",
                f"🔐 **Auth Method:** {device_info.get('auth_method', 'Unknown')}",
                "",
                f"🔗 **Connection Status:** {'✅ Connected' if device_info.get('is_connected') else '❌ Disconnected'}",
                f"📊 **Connection State:** {device_info.get('connection_state', 0)}",
                "",
            ]
            
            # Add last operation info if available
            last_op = device_info.get('last_operation_result')
            if last_op:
                status = "✅ Success" if last_op.get('success') else "❌ Failed"
                info_lines.extend([
                    f"⚡ **Last Operation:** {last_op.get('command', 'Unknown')} - {status}",
                    "",
                ])
            
            # Add device-specific info if available
            device_data = device_info.get('device_info', {})
            if device_data:
                info_lines.append("📋 **Device Data:**")
                for key, value in device_data.items():
                    info_lines.append(f"   • **{key}:** {value}")
                info_lines.append("")
            
            # Add notification information
            latest_notification = device_info.get('latest_notification', '')
            notification_buffer = device_info.get('notification_buffer', '')
            
            if latest_notification or notification_buffer:
                info_lines.append("📨 **Notifications:**")
                if latest_notification:
                    info_lines.append(f"   • **Latest:** {latest_notification}")
                if notification_buffer and notification_buffer != latest_notification:
                    info_lines.append(f"   • **Buffer:** {notification_buffer}")
                info_lines.append("")
            
            # Add fetch status
            fetch_status = device_info.get('fetch_time', 'unknown')
            if fetch_status == 'success':
                info_lines.append("🕒 **Data fetched successfully**")
            else:
                info_lines.append("⚠️ **Data fetch failed**")
                if 'fetch_error' in device_info:
                    info_lines.append(f"   Error: {device_info['fetch_error']}")
            
            # Join all lines into a single message
            message = "\n".join(info_lines)
            
            # Send persistent notification to Home Assistant
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": f"KUBE Device Information",
                    "message": message,
                    "notification_id": f"kube_device_info_{self.coordinator.mac_address}",
                },
            )
            
            _LOGGER.debug("Device info notification sent successfully")
            
        except Exception as err:
            _LOGGER.error("Error fetching device info: %s", err)
            
            # Send error notification
            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "KUBE Device Info Error",
                    "message": f"Failed to fetch device information:\n{str(err)}",
                    "notification_id": f"kube_device_info_error_{self.coordinator.mac_address}",
                },
            )
