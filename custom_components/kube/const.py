"""Constants for the KUBE Gate System integration."""
from __future__ import annotations

from typing import Final

# Integration domain
DOMAIN: Final = "kube"

# Configuration keys
CONF_MAC_ADDRESS: Final = "mac_address"
CONF_PASSKEY: Final = "passkey"
CONF_MASTER_KEY: Final = "master_key"
CONF_AUTH_METHOD: Final = "auth_method"
CONF_DEVICE_NAME: Final = "device_name"

# Authentication methods
AUTH_METHOD_PASSKEY: Final = "passkey"
AUTH_METHOD_MASTER_KEY: Final = "master_key"

# Default values
DEFAULT_SCAN_TIMEOUT: Final = 10.0
DEFAULT_UPDATE_INTERVAL: Final = 30
DEFAULT_DEVICE_NAME: Final = "KUBE Gate"

# Entity names
ENTITY_OPEN_GATE: Final = "open_gate"
ENTITY_CLOSE_GATE: Final = "close_gate"
ENTITY_TOGGLE_GATE: Final = "toggle_gate"
ENTITY_OPEN_SLIGHTLY: Final = "open_slightly"
ENTITY_DEVICE_INFO: Final = "device_info"
ENTITY_GATE_LIGHTS: Final = "gate_lights"
ENTITY_CONNECTION_STATUS: Final = "connection_status"
ENTITY_GATE_STATE: Final = "gate_state"
ENTITY_TOTAL_CYCLES: Final = "total_cycles"
ENTITY_CYCLES_TO_MAINTENANCE: Final = "cycles_to_maintenance"


# Service names
SERVICE_OPEN_GATE: Final = "open_gate"
SERVICE_CLOSE_GATE: Final = "close_gate"
SERVICE_TOGGLE_GATE: Final = "toggle_gate"
SERVICE_OPEN_SLIGHTLY: Final = "open_slightly"
SERVICE_CONTROL_LIGHTS: Final = "control_lights"

# Error messages
ERROR_CANNOT_CONNECT: Final = "cannot_connect"
ERROR_INVALID_AUTH: Final = "invalid_auth"
ERROR_UNKNOWN: Final = "unknown"
ERROR_DEVICE_NOT_FOUND: Final = "device_not_found"
ERROR_BLUETOOTH_ERROR: Final = "bluetooth_error"

# State attributes
ATTR_MAC_ADDRESS: Final = "mac_address"
ATTR_DEVICE_NAME: Final = "device_name"
ATTR_CONNECTION_STATE: Final = "connection_state"
ATTR_LAST_OPERATION: Final = "last_operation"
ATTR_OPERATION_RESULT: Final = "operation_result"
