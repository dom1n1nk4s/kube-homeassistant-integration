"""Sensor platform for KUBE Gate System."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ENTITY_CONNECTION_STATUS,
    ENTITY_GATE_STATE,
    ENTITY_MAINTENANCE_INFO,
    ATTR_MAC_ADDRESS,
    ATTR_CONNECTION_STATE,
)
from .coordinator import KubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KUBE sensor entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        KubeConnectionSensor(coordinator),
        KubeGateStateSensor(coordinator),
        KubeMaintenanceSensor(coordinator),
    ]

    async_add_entities(entities)


class KubeConnectionSensor(CoordinatorEntity, SensorEntity):
    """Representation of a KUBE connection status sensor."""

    def __init__(self, coordinator: KubeDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address}_{ENTITY_CONNECTION_STATUS}"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["connected", "disconnected", "connecting", "error"]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Connection Status"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return "disconnected"
        
        connection_state = self.coordinator.data.get("connection_state", 0)
        is_connected = self.coordinator.data.get("is_connected", False)
        
        if is_connected:
            return "connected"
        elif connection_state == 0:
            return "disconnected"
        else:
            return "connecting"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            ATTR_MAC_ADDRESS: self.coordinator.mac_address,
        }
        
        if self.coordinator.data:
            attrs[ATTR_CONNECTION_STATE] = self.coordinator.data.get("connection_state", 0)
        
        return attrs

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        if self.native_value == "connected":
            return "mdi:bluetooth-connect"
        elif self.native_value == "connecting":
            return "mdi:bluetooth-settings"
        else:
            return "mdi:bluetooth-off"


class KubeGateStateSensor(CoordinatorEntity, SensorEntity):
    """Representation of a KUBE gate state sensor."""

    def __init__(self, coordinator: KubeDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address}_{ENTITY_GATE_STATE}"
        self._attr_has_entity_name = True
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_options = ["unknown", "open", "closed", "opening", "closing", "partially_open"]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Gate State"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.data or not self.coordinator.data.get("is_connected"):
            return "unknown"
        
        # Try to extract gate state from device info
        device_info = self.coordinator.data.get("device_info", {})
        
        # Look for gate state indicators in the device parameters
        for key, value in device_info.items():
            if "state" in key.lower() or "status" in key.lower():
                # This is a placeholder - actual implementation would depend on
                # what the KUBE device actually returns
                if isinstance(value, str) and value:
                    return "unknown"  # Would parse actual state here
        
        return "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            ATTR_MAC_ADDRESS: self.coordinator.mac_address,
        }
        
        if self.coordinator.data:
            device_info = self.coordinator.data.get("device_info", {})
            if device_info:
                attrs["device_parameters"] = len(device_info)
        
        return attrs

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        state = self.native_value
        if state == "open":
            return "mdi:gate-open"
        elif state == "closed":
            return "mdi:gate"
        elif state in ["opening", "closing"]:
            return "mdi:gate-arrow-right"
        elif state == "partially_open":
            return "mdi:gate-buffer"
        else:
            return "mdi:help-circle"


class KubeMaintenanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a KUBE maintenance info sensor."""

    def __init__(self, coordinator: KubeDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address}_{ENTITY_MAINTENANCE_INFO}"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Maintenance Info"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor."""
        if not self.coordinator.data or not self.coordinator.data.get("is_connected"):
            return "unavailable"
        
        # Try to extract maintenance info from device info
        device_info = self.coordinator.data.get("device_info", {})
        
        # Look for maintenance-related information
        for key, value in device_info.items():
            if "maintenance" in key.lower() or "cycle" in key.lower():
                return str(value) if value else "no_data"
        
        return "no_data"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            ATTR_MAC_ADDRESS: self.coordinator.mac_address,
        }
        
        if self.coordinator.data:
            device_info = self.coordinator.data.get("device_info", {})
            
            # Add all device info as attributes for debugging
            for key, value in device_info.items():
                # Clean up the key name for attributes
                attr_key = key.lower().replace(" ", "_")
                attrs[f"device_{attr_key}"] = str(value) if value else ""
        
        return attrs

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        return "mdi:wrench"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.is_connected
