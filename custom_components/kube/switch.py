"""Switch platform for KUBE Gate System."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up KUBE switch entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        KubeGateSwitch(coordinator, ENTITY_OPEN_GATE, "Open Gate", "open_door"),
        KubeGateSwitch(coordinator, ENTITY_CLOSE_GATE, "Close Gate", "close_door"),
        KubeGateSwitch(coordinator, ENTITY_TOGGLE_GATE, "Toggle Gate", "toggle_door"),
        KubeGateSwitch(coordinator, ENTITY_OPEN_SLIGHTLY, "Open Slightly", "open_slightly"),
    ]

    async_add_entities(entities)


class KubeGateSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a KUBE gate control switch."""

    def __init__(
        self,
        coordinator: KubeDataUpdateCoordinator,
        entity_id: str,
        name: str,
        command: str,
    ) -> None:
        """Initialize the switch."""
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
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        # For momentary switches, we don't maintain state
        # They are always considered "off" after execution
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.is_connected

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on (execute the command)."""
        _LOGGER.debug("Executing command: %s", self._command)
        
        success = await self.coordinator.async_execute_command(self._command)
        
        if not success:
            _LOGGER.error("Failed to execute command: %s", self._command)
        else:
            _LOGGER.debug("Successfully executed command: %s", self._command)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off (no-op for momentary switches)."""
        # These are momentary switches, so turning off is a no-op
        pass

    @property
    def icon(self) -> str:
        """Return the icon for the switch."""
        if self._entity_id == ENTITY_OPEN_GATE:
            return "mdi:gate-open"
        elif self._entity_id == ENTITY_CLOSE_GATE:
            return "mdi:gate"
        elif self._entity_id == ENTITY_TOGGLE_GATE:
            return "mdi:gate-arrow-right"
        elif self._entity_id == ENTITY_OPEN_SLIGHTLY:
            return "mdi:gate-buffer"
        return "mdi:gate"
