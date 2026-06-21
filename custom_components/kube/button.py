"""Button platform for KUBE Gate System."""
from __future__ import annotations

import json
import logging
import re
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
from .sensor import C77_STATUS_DESC

_LOGGER = logging.getLogger(__name__)

C76_LIGHT_INTENSITY_DESC = ["Off", "Low", "Medium", "High", "Very high", "Max"]
C76_INPUT_LOCK_DESC = {0: "Unlocked", 1: "Locked"}


def _parse_cinf(notification: str) -> dict[str, Any] | None:
    """Parse a cinf notification into readable fields."""
    match = re.search(r'@[0-9A-F]+cinf=(.*)#$', notification)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        return None


def _parse_door_status(notifications: list) -> str:
    """Parse door status from cpar c77 notification."""
    for n in notifications:
        m = re.search(r'cpar=\{"c77":(\d+)\}#', n)
        if m:
            full = int(m.group(1))
            return C77_STATUS_DESC.get(full & 0xFF, f"Unknown ({full & 0xFF})")
    return "Unknown"


def _parse_light_state(notifications: list) -> tuple[str | None, str | None]:
    """Parse light state from cpar c76 notification. Returns (on_off, intensity)."""
    for n in notifications:
        m = re.search(r'cpar=\{"c76":(\d+)\}#', n)
        if m:
            c76 = int(m.group(1))
            on = bool((c76 >> 25) & 0x1)
            intensity_idx = (c76 >> 26) & 0x7
            on_str = "On" if on else "Off"
            intensity_str = C76_LIGHT_INTENSITY_DESC[intensity_idx] if intensity_idx < len(C76_LIGHT_INTENSITY_DESC) else f"Unknown ({intensity_idx})"
            return on_str, intensity_str
    return None, None


def _parse_cycle_values(notifications: list) -> dict[str, int]:
    """Parse cycle counts from cpar notifications."""
    result = {}
    for n in notifications:
        m = re.search(r'cpar=\{"c6A":(\d+)\}#', n)
        if m:
            result["total_cycles"] = int(m.group(1))
    for n in notifications:
        m = re.search(r'cpar=\{"c6B":(\d+)\}#', n)
        if m:
            result["cycles_to_maintenance"] = int(m.group(1))
    return result


def _parse_kbinf(notification: str) -> dict[str, Any] | None:
    """Parse a kbinf notification into readable fields."""
    match = re.search(r'@[0-9A-F]+kbinf=(.*)#$', notification)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        return None


def _format_notification_summary(notifications: list) -> str:
    """Build a user-friendly summary from notification data."""
    parts: list[str] = []

    door_status = _parse_door_status(notifications)
    parts.append(f"🚪 **Door:** {door_status}")

    cycles = _parse_cycle_values(notifications)
    if "total_cycles" in cycles:
        parts.append(f"🔢 **Total Cycles:** {cycles['total_cycles']}")
    if "cycles_to_maintenance" in cycles:
        parts.append(f"🔧 **Cycles to Maintenance:** {cycles['cycles_to_maintenance']}")

    light_on, light_intensity = _parse_light_state(notifications)
    if light_on is not None:
        parts.append(f"💡 **Lights:** {light_on} ({light_intensity})")

    for notification in notifications:
        if "kbinf" in notification:
            parsed = _parse_kbinf(notification)
            if parsed:
                kmod = parsed.get("kmod", "?")
                kfwv = parsed.get("kfwv", "?")
                khwm = parsed.get("khwm", "?")
                kconint = parsed.get("kconint", "?")
                krst = parsed.get("krst", "?")
                kcomerr = parsed.get("kcomerr", 0)
                kcomtout = parsed.get("kcomtout", 0)
                parts.append(f"🧩 **Module:** {kmod}  |  **FW:** {kfwv}  |  **HW:** {khwm}")
                parts.append(f"🔗 **Conn Interval:** {kconint}  |  **Resets:** {krst}")
                parts.append(f"⚠️ **Comm Errors:** {kcomerr}  |  **Timeouts:** {kcomtout}")
            break

    for notification in notifications:
        if "cinf" in notification:
            parsed = _parse_cinf(notification)
            if parsed:
                cstate = parsed.get("cstate", "?")
                rstate = parsed.get("rstate", "?")
                parts.append(f"🔄 **CEN State:** {cstate}  |  **Requested:** {rstate}")
                serial = parsed.get("cFFFC", "?")
                model = parsed.get("cFFFB", "?")
                fw_ver = parsed.get("cFFF9", "?")
                hw_ver = parsed.get("cFFFA", "?")
                parts.append(f"🆔 **CEN Serial:** {serial}")
                parts.append(f"📟 **CEN Model:** {model}")
                parts.append(f"🔬 **CEN FW:** {fw_ver}  |  **CEN HW:** {hw_ver}")
                r_serial = parsed.get("rFFFC", "?")
                r_model = parsed.get("rFFFB", "?")
                r_fw = parsed.get("rFFF9", "?")
                r_hw = parsed.get("rFFFA", "?")
                parts.append(f"📻 **Radio Model:** {r_model}  |  **Serial:** {r_serial}")
                parts.append(f"🔬 **Radio FW:** {r_fw}  |  **Radio HW:** {r_hw}")
            break

    return "\n".join(parts)


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
        if not self.coordinator.data:
            return False
        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            ATTR_MAC_ADDRESS: self.coordinator.mac_address,
        }
        
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
        """Device info button is always available."""
        return True

    @property
    def icon(self) -> str:
        """Return the icon for the button."""
        return "mdi:information-outline"

    async def async_press(self) -> None:
        """Handle the button press - fetch device info and show as notification."""
        _LOGGER.debug("Device info button pressed")
        
        try:
            device_info = await self.coordinator.async_fetch_device_info()
            notifications = device_info.get("notification_list", [])
            if not isinstance(notifications, list):
                notifications = device_info.get("device_info", {}).get("notifications", [])

            lines: list[str] = [
                f"🏠 **{device_info.get('device_name', 'KUBE Gate')}**",
                "",
                f"📍 **MAC Address:** {device_info.get('mac_address', 'Unknown')}",
                f"🏭 **Manufacturer:** {device_info.get('manufacturer', 'KUBE')}",
                f"📦 **Model:** {device_info.get('model', 'Gate System')}",
                f"🔧 **Software Version:** {device_info.get('sw_version', '1.0')}",
                f"🔐 **Auth Method:** {device_info.get('auth_method', 'Unknown')}",
                "",
                f"🔗 **Connection:** {'✅ Connected' if device_info.get('is_connected') else '❌ Disconnected'}",
                "",
            ]

            last_op = device_info.get("last_operation_result")
            if last_op:
                status = "✅ Success" if last_op.get("success") else "❌ Failed"
                lines.append(f"⚡ **Last Operation:** {last_op.get('command', 'Unknown')} - {status}")
                lines.append("")

            if notifications and len(notifications) > 0:
                lines.append("📋 **Status:**")
                summary = _format_notification_summary(notifications)
                lines.append(summary)
                lines.append("")

            if _LOGGER.isEnabledFor(logging.DEBUG):
                lines.append("---")
                lines.append("🔧 **Debug Info:**")
                lines.append(f"• **Notifications received:** {len(notifications)}")
                for i, n in enumerate(notifications):
                    lines.append(f"  `[{i+1}]: {n}`")
                lines.append("")

                raw_notification = device_info.get("latest_notification", "")
                if raw_notification:
                    lines.append(f"• **Latest raw:** `{raw_notification}`")

                notification_buffer = device_info.get("notification_buffer", "")
                if notification_buffer and notification_buffer != raw_notification:
                    lines.append(f"• **Buffer:** `{notification_buffer}`")

                raw_data = device_info.get("device_info", {})
                if raw_data:
                    lines.append("")
                    lines.append("📋 **Raw Device Data:**")
                    for key in sorted(raw_data.keys()):
                        val = raw_data[key]
                        lines.append(f"  • **{key}:** {val}")

                lines.append("")

            fetch_status = device_info.get("fetch_time", "unknown")
            if fetch_status == "success":
                lines.append("🕒 **Data fetched successfully**")
            else:
                lines.append("⚠️ **Data fetch failed**")
                if "fetch_error" in device_info:
                    lines.append(f"   Error: {device_info['fetch_error']}")

            message = "\n".join(lines)

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

            await self.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "KUBE Device Info Error",
                    "message": f"Failed to fetch device information:\n{str(err)}",
                    "notification_id": f"kube_device_info_error_{self.coordinator.mac_address}",
                },
            )
