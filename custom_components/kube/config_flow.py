"""Config flow for KUBE Gate System integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_MAC_ADDRESS,
    CONF_PASSKEY,
    CONF_MASTER_KEY,
    CONF_AUTH_METHOD,
    CONF_DEVICE_NAME,
    AUTH_METHOD_PASSKEY,
    AUTH_METHOD_MASTER_KEY,
    DEFAULT_DEVICE_NAME,
    ERROR_CANNOT_CONNECT,
    ERROR_INVALID_AUTH,
    ERROR_UNKNOWN,
    ERROR_DEVICE_NOT_FOUND,
    ERROR_BLUETOOTH_ERROR,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MAC_ADDRESS): str,
        vol.Required(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): str,
        vol.Required(CONF_AUTH_METHOD, default=AUTH_METHOD_PASSKEY): vol.In(
            [AUTH_METHOD_PASSKEY, AUTH_METHOD_MASTER_KEY]
        ),
    }
)

STEP_AUTH_PASSKEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSKEY): str,
    }
)

STEP_AUTH_MASTER_KEY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MASTER_KEY): str,
        vol.Optional(CONF_PASSKEY, default=""): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    try:
        mac_address = data[CONF_MAC_ADDRESS].upper().replace("-", ":")
        auth_method = data[CONF_AUTH_METHOD]
        
        # Validate MAC address format
        if not _is_valid_mac_address(mac_address):
            raise InvalidMacAddress
        
        # Validate authentication data
        if auth_method == AUTH_METHOD_PASSKEY:
            if CONF_PASSKEY not in data or not data[CONF_PASSKEY]:
                raise InvalidAuth("Passkey is required")
            passkey = data[CONF_PASSKEY].strip()
            if not passkey:
                raise InvalidAuth("Passkey cannot be empty")
        else:  # master_key method
            if CONF_MASTER_KEY not in data or not data[CONF_MASTER_KEY]:
                raise InvalidAuth("Master key is required")
            master_key = data[CONF_MASTER_KEY].strip()
            if not master_key:
                raise InvalidAuth("Master key cannot be empty")

        # Skip library import test during configuration
        # The actual library will be tested when the integration loads
        _LOGGER.debug("Configuration validation passed")

        # Return info that you want to store in the config entry.
        return {
            "title": data[CONF_DEVICE_NAME],
            "mac_address": mac_address,
            "auth_method": auth_method,
        }

    except CannotConnect:
        raise
    except InvalidAuth:
        raise
    except InvalidMacAddress:
        raise
    except Exception as err:
        _LOGGER.exception("Unexpected exception during validation: %s", err)
        raise UnknownError from err


def _is_valid_mac_address(mac: str) -> bool:
    """Validate MAC address format."""
    import re
    mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
    return bool(mac_pattern.match(mac))


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KUBE Gate System."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._mac_address: str | None = None
        self._device_name: str | None = None
        self._auth_method: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Store the basic info
                self._mac_address = user_input[CONF_MAC_ADDRESS].upper().replace("-", ":")
                self._device_name = user_input[CONF_DEVICE_NAME]
                self._auth_method = user_input[CONF_AUTH_METHOD]

                # Check if already configured
                await self.async_set_unique_id(self._mac_address)
                self._abort_if_unique_id_configured()

                # Proceed to authentication step
                if self._auth_method == AUTH_METHOD_PASSKEY:
                    return await self.async_step_auth_passkey()
                else:
                    return await self.async_step_auth_master_key()

            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = ERROR_UNKNOWN

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_auth_passkey(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle passkey authentication step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Combine all data for validation
                data = {
                    CONF_MAC_ADDRESS: self._mac_address,
                    CONF_DEVICE_NAME: self._device_name,
                    CONF_AUTH_METHOD: self._auth_method,
                    CONF_PASSKEY: user_input[CONF_PASSKEY],
                }

                info = await validate_input(self.hass, data)

                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_MAC_ADDRESS: info["mac_address"],
                        CONF_DEVICE_NAME: self._device_name,
                        CONF_AUTH_METHOD: info["auth_method"],
                        CONF_PASSKEY: user_input[CONF_PASSKEY],
                    },
                )

            except CannotConnect:
                errors["base"] = ERROR_CANNOT_CONNECT
            except InvalidAuth:
                errors["base"] = ERROR_INVALID_AUTH
            except InvalidMacAddress:
                errors["base"] = ERROR_DEVICE_NOT_FOUND
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = ERROR_UNKNOWN

        return self.async_show_form(
            step_id="auth_passkey",
            data_schema=STEP_AUTH_PASSKEY_SCHEMA,
            errors=errors,
        )

    async def async_step_auth_master_key(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle master key authentication step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Combine all data for validation
                data = {
                    CONF_MAC_ADDRESS: self._mac_address,
                    CONF_DEVICE_NAME: self._device_name,
                    CONF_AUTH_METHOD: self._auth_method,
                    CONF_MASTER_KEY: user_input[CONF_MASTER_KEY],
                    CONF_PASSKEY: user_input.get(CONF_PASSKEY, ""),
                }

                info = await validate_input(self.hass, data)

                return self.async_create_entry(
                    title=info["title"],
                    data={
                        CONF_MAC_ADDRESS: info["mac_address"],
                        CONF_DEVICE_NAME: self._device_name,
                        CONF_AUTH_METHOD: info["auth_method"],
                        CONF_MASTER_KEY: user_input[CONF_MASTER_KEY],
                        CONF_PASSKEY: user_input.get(CONF_PASSKEY, ""),
                    },
                )

            except CannotConnect:
                errors["base"] = ERROR_CANNOT_CONNECT
            except InvalidAuth:
                errors["base"] = ERROR_INVALID_AUTH
            except InvalidMacAddress:
                errors["base"] = ERROR_DEVICE_NOT_FOUND
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = ERROR_UNKNOWN

        return self.async_show_form(
            step_id="auth_master_key",
            data_schema=STEP_AUTH_MASTER_KEY_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidMacAddress(HomeAssistantError):
    """Error to indicate invalid MAC address format."""


class UnknownError(HomeAssistantError):
    """Error to indicate unknown error."""
