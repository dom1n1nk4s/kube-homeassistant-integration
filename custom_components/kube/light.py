"""Light platform for KUBE Gate System."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ENTITY_GATE_LIGHTS,
    ATTR_MAC_ADDRESS,
)
from .coordinator import KubeDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_c76_value(notifications: list) -> int | None:
    """Extract the full c76 value from a cpar notification response."""
    for notification in notifications:
        match = re.search(r'cpar=\{"c76":(\d+)\}#', notification)
        if match:
            return int(match.group(1))
    return None


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
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF

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
        """Return true if light is on based on c76.5 from device."""
        if not self.coordinator.data or not self.coordinator.data.get("is_connected"):
            return False

        device_info = self.coordinator.data.get("device_info", {})
        notifications = device_info.get("notifications", [])
        if not isinstance(notifications, list):
            return False

        c76 = _get_c76_value(notifications)
        if c76 is None:
            return False

        # c76.5 = bit 25 of c76 — manual activation of lights
        return bool((c76 >> 25) & 0x1)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return bool(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return {ATTR_MAC_ADDRESS: self.coordinator.mac_address}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        _LOGGER.debug("Turning on gate lights")

        if self.is_on:
            _LOGGER.debug("Gate lights already on")
            return

        success = await self.coordinator.async_execute_command("control_lights")

        if success:
            _LOGGER.debug("Successfully toggled gate lights on")
        else:
            _LOGGER.error("Failed to toggle gate lights on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        _LOGGER.debug("Turning off gate lights")

        if not self.is_on:
            _LOGGER.debug("Gate lights already off")
            return

        success = await self.coordinator.async_execute_command("control_lights")

        if success:
            _LOGGER.debug("Successfully toggled gate lights off")
        else:
            _LOGGER.error("Failed to toggle gate lights off")

    @property
    def icon(self) -> str:
        """Return the icon for the light."""
        return "mdi:lightbulb" if self.is_on else "mdi:lightbulb-outline"
