"""Light platform for KUBE Gate System."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ENTITY_GATE_LIGHTS,
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
    """Set up KUBE light entities from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities = [
        KubeGateLight(coordinator),
    ]

    async_add_entities(entities)


class KubeGateLight(CoordinatorEntity, LightEntity):
    """Representation of a KUBE gate light."""

    def __init__(self, coordinator: KubeDataUpdateCoordinator) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac_address}_{ENTITY_GATE_LIGHTS}"
        self._attr_has_entity_name = True
        self._is_on = False

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def name(self) -> str:
        """Return the name of the light."""
        return "Gate Lights"

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        # Since we can't read the actual light state from the device,
        # we maintain our own state based on the last command
        return self._is_on

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
            if last_op and last_op.get("command") == "control_lights":
                attrs[ATTR_LAST_OPERATION] = last_op.get("command")
                attrs[ATTR_OPERATION_RESULT] = "success" if last_op.get("success") else "failed"
        
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        _LOGGER.debug("Turning on gate lights")
        
        success = await self.coordinator.async_execute_command("control_lights")
        
        if success:
            self._is_on = True
            self.async_write_ha_state()
            _LOGGER.debug("Successfully turned on gate lights")
        else:
            _LOGGER.error("Failed to turn on gate lights")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        _LOGGER.debug("Turning off gate lights")
        
        # The KUBE system uses the same command to toggle lights
        success = await self.coordinator.async_execute_command("control_lights")
        
        if success:
            self._is_on = False
            self.async_write_ha_state()
            _LOGGER.debug("Successfully turned off gate lights")
        else:
            _LOGGER.error("Failed to turn off gate lights")

    @property
    def icon(self) -> str:
        """Return the icon for the light."""
        return "mdi:lightbulb" if self._is_on else "mdi:lightbulb-outline"
