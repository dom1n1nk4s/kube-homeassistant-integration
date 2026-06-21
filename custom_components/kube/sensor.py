"""Sensor platform for KUBE Gate System."""
from __future__ import annotations

import logging
import re
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
    ENTITY_TOTAL_CYCLES,
    ENTITY_CYCLES_TO_MAINTENANCE,
    ATTR_MAC_ADDRESS,
    ATTR_CONNECTION_STATE,
)
from .coordinator import KubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# c77.1 door status descriptions (from Kube app resources.xml)
C77_STATUS_DESC: dict[int, str] = {
    0: "Door stopped",
    1: "Opening",
    2: "Open",
    3: "Waiting reclosing timeout",
    4: "Partial opening",
    5: "Partial open reached",
    6: "Waiting for partial reclosing",
    7: "Closing",
    8: "Closed",
    9: "Partial closing",
    10: "Photocell 1 activated while closing, reopening",
    11: "Photocell 2 activated, movement stopped",
    12: "Executed stop while opening",
    13: "Executed stop while closing",
    14: "Safety edge activated during movement",
    15: "Leaf 1 impact with obstacle",
    16: "Leaf 2 impact with obstacle",
    17: "Leaf 1 impact with obstacle",
    18: "Leaf 2 impact with obstacle",
    19: "Photocells malfunction detected",
    20: "Limit switch malfunction detected",
    21: "Safety edge malfunction detected",
    22: "Realignment, searching for limit switches",
    23: "Power supply sag",
    24: "Leaf 1 opening",
    25: "Leaf 1 stop in opening",
    26: "Leaf 2 opening",
    27: "Leaf 1 and 2 stop in opening",
    28: "Leaf 2 stop in opening",
    29: "Leaf 1 closing",
    30: "Leaf 2 closing",
    31: "Leaf 2 stop in closing",
    32: "Limit switch error: is leaf half open?",
    33: "Error learning generic",
    34: "Error learning, procedure stopped",
    35: "Error learning abort",
    36: "Error learning safety settings",
    40: "Aeration opening",
    41: "Stop in aeration",
    42: "Waiting for aeration reclosing",
}


def _get_cpar_value(notifications: list, param: str) -> int | None:
    """Extract a numeric value from a cpar notification response."""
    for notification in notifications:
        match = re.search(r'cpar=\{"' + re.escape(param) + r'":(\d+)\}#', notification)
        if match:
            return int(match.group(1))
    return None


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
        KubeTotalCyclesSensor(coordinator),
        KubeCyclesToMaintenanceSensor(coordinator),
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
            return "Unknown"

        device_info = self.coordinator.data.get("device_info", {})
        notifications = device_info.get("notifications", [])
        if not isinstance(notifications, list):
            return "Unknown"

        for notification in notifications:
            match = re.search(r'cpar=\{"c77":(\d+)\}#', notification)
            if match:
                full_value = int(match.group(1))
                door_status = full_value & 0xFF
                return C77_STATUS_DESC.get(door_status, f"Unknown ({door_status})")

        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            ATTR_MAC_ADDRESS: self.coordinator.mac_address,
        }

        if self.coordinator.data:
            device_info = self.coordinator.data.get("device_info", {})
            notifications = device_info.get("notifications", [])
            if isinstance(notifications, list) and notifications:
                attrs["notification_list"] = notifications

        return attrs

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        state = self.native_value
        if "Open" in state and "ing" not in state and "Partial" not in state:
            return "mdi:gate-open"
        if "Closed" in state or "closed" in state or "Door stopped" in state:
            return "mdi:gate"
        if "Opening" in state or "Closing" in state or "closing" in state:
            return "mdi:gate-arrow-right"
        if "Partial" in state or "Aeration" in state or "stop" in state.lower() or "Stop" in state:
            return "mdi:gate-buffer"
        if "Error" in state or "error" in state or "malfunction" in state:
            return "mdi:alert-circle"
        return "mdi:help-circle"


class KubeTotalCyclesSensor(CoordinatorEntity, SensorEntity):
    """Representation of a KUBE total cycle count sensor."""

    def __init__(self, coordinator: KubeDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address}_{ENTITY_TOTAL_CYCLES}"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Total Cycles"

    @property
    def native_value(self) -> int | None:
        """Return the total cycle count."""
        if not self.coordinator.data or not self.coordinator.data.get("is_connected"):
            return None

        device_info = self.coordinator.data.get("device_info", {})
        notifications = device_info.get("notifications", [])
        if not isinstance(notifications, list):
            return None

        return _get_cpar_value(notifications, "c6A")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {ATTR_MAC_ADDRESS: self.coordinator.mac_address}

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        return "mdi:counter"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "cycles"


class KubeCyclesToMaintenanceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a KUBE cycles to maintenance sensor."""

    def __init__(self, coordinator: KubeDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address}_{ENTITY_CYCLES_TO_MAINTENANCE}"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "Cycles to Maintenance"

    @property
    def native_value(self) -> int | None:
        """Return the cycles remaining until maintenance."""
        if not self.coordinator.data or not self.coordinator.data.get("is_connected"):
            return None

        device_info = self.coordinator.data.get("device_info", {})
        notifications = device_info.get("notifications", [])
        if not isinstance(notifications, list):
            return None

        return _get_cpar_value(notifications, "c6B")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {ATTR_MAC_ADDRESS: self.coordinator.mac_address}

    @property
    def icon(self) -> str:
        """Return the icon for the sensor."""
        return "mdi:calendar-clock"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "cycles"


