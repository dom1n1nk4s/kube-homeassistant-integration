import asyncio
import logging
from enum import IntEnum
from typing import Optional
from .OperationBuilder import OperationBuilder, C30BOperation
from .KubeBtClient import KubeBtClient

_LOGGER = logging.getLogger(__name__)


class KubeCommands:
    """
    High-level async command interface for Kube devices.
    This class provides concrete methods that can be used externally by Home Assistant
    and other applications. Each method uses connect-per-command pattern for reliability.
    """
    
    def __init__(self, mac: str, passkey: str, master_key: Optional[str] = None, kube_bt_client: Optional[KubeBtClient] = None):
        """
        Initialize KubeCommands with device credentials and optional KubeBtClient instance.
        
        Args:
            mac: Device MAC address
            passkey: Device passkey for authentication
            master_key: Optional master key for device setup operations
            kube_bt_client: Optional KubeBtClient instance. If None, creates a new one.
        """
        self.mac = mac
        self.passkey = passkey
        self.master_key = master_key
        self.kube_bt_client = kube_bt_client or KubeBtClient()
        self.operation_builder = OperationBuilder(self.kube_bt_client)
        
        # Store passkey in device for authentication
        passkey_str = str(passkey).zfill(16)
        self.operation_builder.get_kube_device(mac).store_string_value("passkey", passkey_str)
    
    def button_command(self, val: C30BOperation) -> int:
        """
        Execute a button command that combines authentication and action.
        
        This method authenticates with the device and executes the specified operation.
        It's equivalent to pressing a button on the device remotely.
        
        Args:
            val: Operation to perform (C30BOperation enum)
            
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.operation_builder.assign_group_id_and_process_array(
            self.operation_builder.merge_payload_arrays(
                self.operation_builder.connect_and_discover_operation(self.mac, 54),
                self.operation_builder.subscribe_to_notifications_operation(self.mac, 54),
                self.operation_builder.write_C30B_with_param(self.mac, 54, val),
                # self.operation_builder.request_kbinf(self.mac, 54),
                # self.operation_builder.request_cinf(self.mac, 54),
                # self.operation_builder.request_cgrp_and_cdat(self.mac, 54),
                # self.operation_builder.request_ccfg1_and_ccfg2(self.mac, 54)
            )
        )
    
    def open_door(self) -> int:
        """
        Open the door/lock.
        
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.button_command(C30BOperation.ONLY_OPEN)
    
    def close_door(self) -> int:
        """
        Close the door/lock.
        
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.button_command(C30BOperation.ONLY_CLOSE)
    
    def toggle_door(self) -> int:
        """
        Toggle the door/lock state (open if closed, close if open).
        
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.button_command(C30BOperation.OPEN_CLOSE_TOGGLE)
    
    def open_slightly_or_close(self) -> int:
        """
        Open slightly or close the door/lock.
        
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.button_command(C30BOperation.OPEN_SLIGHTLY_OR_CLOSE)
    
    def control_lights(self) -> int:
        """
        Control the device lights.
        
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.button_command(C30BOperation.LIGHTS)
    
    def get_device_info(self, keep_connection: bool = False) -> int:
        """
        Get comprehensive device information.
        
        This method connects to the device, authenticates, and retrieves all available
        device information including configuration, status, and capabilities.
        
        Args:
            keep_connection: Whether to keep the connection open after getting info
            
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.operation_builder.get_info_command_maybe(self.mac, self.passkey, not keep_connection)
    
    def setup_new_device(self, new_passkey: str) -> int:
        """
        Set up a new device with master key and passkey.
        
        This method is used for initial device setup or when changing device credentials.
        Requires master_key to be set in constructor.
        
        Args:
            new_passkey: New passkey to set for the device
            
        Returns:
            int: Group identifier for tracking the operation
            
        Raises:
            ValueError: If master_key was not provided in constructor
        """
        if self.master_key is None:
            raise ValueError("Master key is required for device setup. Provide it in constructor.")
        return self.operation_builder.set_new_passkey_command(self.mac, self.master_key, new_passkey)
    
    def change_passkey(self, new_passkey: str) -> int:
        """
        Change the device passkey.
        
        Requires master_key to be set in constructor.
        
        Args:
            new_passkey: New passkey to set
            
        Returns:
            int: Group identifier for tracking the operation
            
        Raises:
            ValueError: If master_key was not provided in constructor
        """
        if self.master_key is None:
            raise ValueError("Master key is required for changing passkey. Provide it in constructor.")
        return self.operation_builder.set_new_passkey_command(self.mac, self.master_key, new_passkey)
    
    def quick_connect_and_authenticate(self) -> int:
        """
        Quickly connect and authenticate with the device without performing any actions.
        
        This is useful for testing connectivity or preparing for subsequent operations.
        
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.operation_builder.assign_group_id_and_process_array(
            self.operation_builder.merge_payload_arrays(
                self.operation_builder.connect_and_discover_operation(self.mac, 50),
                self.operation_builder.subscribe_to_notifications_operation(self.mac, 50)
            )
        )
    
    def get_device_status(self) -> int:
        """
        Get basic device status information.
        
        This method connects, authenticates, and retrieves basic status information
        without performing a full info dump.
        
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.operation_builder.assign_group_id_and_process_array(
            self.operation_builder.merge_payload_arrays(
                self.operation_builder.connect_and_discover_operation(self.mac, 52),
                self.operation_builder.subscribe_to_notifications_operation(self.mac, 52),
                self.operation_builder.request_kbinf(self.mac, 52),
                self.operation_builder.request_cinf(self.mac, 52)
            )
        )
    
    def disconnect_device(self) -> int:
        """
        Disconnect from the device.
        
        Returns:
            int: Group identifier for tracking the operation
        """
        return self.operation_builder.assign_group_id_and_process_array(
            self.operation_builder.disconnect_operation(self.mac, 38)
        )
    
    def get_connection_state(self) -> int:
        """
        Get the current connection state for a device.
        
        Returns:
            int: Connection state (0 = disconnected, other values indicate connected states)
        """
        return self.operation_builder.get_device_connection_state(self.mac)
    
    def is_device_connected(self) -> bool:
        """
        Check if a device is currently connected.
        
        Returns:
            bool: True if device is connected, False otherwise
        """
        return self.get_connection_state() != 0

    # New async methods using connect-per-command pattern
    
    async def _connect_and_authenticate_async(self, timeout: int = 15000, retry_once: bool = True) -> bool:
        """
        Connect and authenticate with the device using async pattern.
        
        Args:
            timeout: Connection timeout in milliseconds
            retry_once: Whether to retry once on failure
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Connect to device
            client = await self.kube_bt_client.connect_bt_gatt_async(
                self.mac, 
                use_background_connection=False, 
                connection_timeout=timeout
            )
            
            if not client:
                return False
            
            # Discover services
            await self.kube_bt_client.discover_services_async(client)
            
            # Read serial number
            sn_data = await self.kube_bt_client.read_characteristic_async(
                client,
                "f1170001-0190-4567-8fab-4d4158a4eeaf",
                "f1170003-0190-4567-8fab-4d4158a4eeaf"
            )
            
            if sn_data:
                device = self.kube_bt_client.get_kube_device(self.mac)
                device.put_device_param_bytes("sn", sn_data)
            
            # Set up notifications
            def notification_callback(sender, data):
                device = self.kube_bt_client.get_kube_device(self.mac)
                # Process notification data (decrypt, buffer, etc.)
                self._process_notification(device, data)
            
            await self.kube_bt_client.start_notify_async(
                client,
                "f1110021-0190-4567-8fab-4d4158a4eeaf",
                notification_callback
            )
            
            # Read nonce and authenticate
            nonce_data = await self.kube_bt_client.read_characteristic_async(
                client,
                "f1170001-0190-4567-8fab-4d4158a4eeaf", 
                "f1170002-0190-4567-8fab-4d4158a4eeaf"
            )
            
            if nonce_data:
                device = self.kube_bt_client.get_kube_device(self.mac)
                self._process_nonce_and_generate_keys(device, nonce_data)
                
                # Write token for authentication using the special encryption method
                # This mimics the original payload-based approach
                bundle = {}  # Empty bundle - the method will use stored token
                await self.kube_bt_client.write_bt_gatt_characteristic_with_encryption_async(
                    self.mac,
                    "f1170001-0190-4567-8fab-4d4158a4eeaf",
                    "f1170005-0190-4567-8fab-4d4158a4eeaf",
                    client,
                    None,  # characteristic object not needed for this UUID
                    bundle
                )
                
                # Wait a bit for the write to complete
                await asyncio.sleep(0.5)
                
                # Check security state
                sec_state = await self.kube_bt_client.read_characteristic_async(
                    client,
                    "f1170001-0190-4567-8fab-4d4158a4eeaf",
                    "f1170006-0190-4567-8fab-4d4158a4eeaf"
                )
                
                if sec_state and len(sec_state) > 0 and sec_state[0] == 1:
                    _LOGGER.debug("Authentication successful for device %s", self.mac)
                    return True
                else:
                    _LOGGER.warning("Authentication failed for device %s - sec_state: %s", 
                                  self.mac, sec_state.hex() if sec_state else 'None')
                    return False
            
            return False
            
        except Exception as e:
            _LOGGER.error("Connection/authentication failed for device %s: %s", self.mac, e)
            if retry_once:
                _LOGGER.debug("Retrying connection for device %s", self.mac)
                return await self._connect_and_authenticate_async(timeout, False)
            return False
    
    def _process_nonce_and_generate_keys(self, device, nonce_data):
        """Process nonce and generate encryption keys using the exact Java algorithm"""
        try:
            # Get stored passkey and serial number
            passkey = device.get_device_param_or_default("passkey", "")
            sn = device.get_device_param_or_default("sn", "")
            
            if passkey and sn:
                passkey_bytes = passkey.encode('utf-8')
                sn_bytes = sn.encode('utf-8') if isinstance(sn, str) else sn
                
                # Step 1: enckey1 = AES(passkey, sn)
                enckey1 = self.kube_bt_client.encrypt_data(passkey_bytes, sn_bytes)
                device.put_device_param_bytes("enckey1", enckey1)
                
                # Step 2: nonceXORedWithEnckey1 = nonce XOR enckey1
                nonce_xor_enckey1 = bytearray(len(nonce_data))
                self.kube_bt_client.cipher_helper_xor_byte_arrays(nonce_data, nonce_xor_enckey1, enckey1)
                
                # Step 3: enckey2 = AES(passkey, nonceXORedWithEnckey1)
                enckey2 = self.kube_bt_client.encrypt_data(passkey_bytes, bytes(nonce_xor_enckey1))
                device.put_device_param_bytes("enckey2", enckey2)
                
                # Step 4: token = nonceXORedWithEnckey1 XOR enckey2
                token = bytearray(len(nonce_xor_enckey1))
                self.kube_bt_client.cipher_helper_xor_byte_arrays(bytes(nonce_xor_enckey1), token, enckey2)
                device.put_device_param_bytes("token", bytes(token))
                
            
        except Exception as e:
            _LOGGER.error("Error processing nonce for device %s: %s", self.mac, e)
    
    def _process_notification(self, device, data):
        """Process notification data with proper chunking support"""
        try:
            # Decrypt notification data
            enckey2 = device.get_device_param_bytes("enckey2")
            if enckey2:
                decrypted = bytearray(len(data))
                self.kube_bt_client.cipher_helper_xor_byte_arrays(data, decrypted, enckey2)
                
                # Try to decode as text
                try:
                    text_chunk = decrypted.decode('utf-8', errors='ignore')
                    _LOGGER.debug("Notification chunk received for device %s: %s", self.mac, text_chunk)
                    
                    # Get existing notification buffer or create new one
                    existing_buffer = device.get_device_param_or_default("notification_buffer", "")
                    
                    # Append new chunk to buffer
                    updated_buffer = existing_buffer + text_chunk
                    device.store_string_value("notification_buffer", updated_buffer)
                    
                    # Check if we have a complete message (ends with # or other delimiter)
                    if text_chunk.endswith('#') or text_chunk.endswith('\n') or text_chunk.endswith('\r'):
                        # Complete message received, store as latest notification
                        device.store_string_value("latest_notification", updated_buffer.strip())
                        _LOGGER.info("Complete notification received for device %s: %s", self.mac, updated_buffer.strip())
                        
                        # Clear the buffer for next message
                        device.store_string_value("notification_buffer", "")
                    else:
                        # Partial message, keep buffering
                        _LOGGER.debug("Buffering partial notification for device %s (total length: %d)", self.mac, len(updated_buffer))
                    
                except Exception:
                    # Handle binary data
                    _LOGGER.debug("Binary notification chunk received for device %s: %s", self.mac, decrypted.hex())
                    
                    # For binary data, we might also need to buffer
                    existing_binary = device.get_device_param_bytes("binary_notification_buffer") or b""
                    updated_binary = existing_binary + bytes(decrypted)
                    device.put_device_param_bytes("binary_notification_buffer", updated_binary)
                    
                    # Store as latest binary notification (you might want different logic here)
                    device.put_device_param_bytes("latest_binary_notification", updated_binary)
            
        except Exception as e:
            _LOGGER.error("Error processing notification for device %s: %s", self.mac, e)
    
    async def _send_command_async(self, command: str) -> bool:
        """
        Send a command to the device using connect-per-command pattern.
        
        Args:
            command: Command string to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        client = None
        try:
            # Connect and authenticate
            if not await self._connect_and_authenticate_async():
                return False
            
            client = self.kube_bt_client.connections.get(self.mac)
            if not client:
                _LOGGER.error("No client connection found for device %s after authentication", self.mac)
                return False
            
            # Encrypt and send command
            device = self.kube_bt_client.get_kube_device(self.mac)
            enckey2 = device.get_device_param_bytes("enckey2")
            
            if enckey2:
                cmd_bytes = command.encode('utf-8')
                encrypted_cmd = bytearray(len(cmd_bytes))
                self.kube_bt_client.cipher_helper_xor_byte_arrays(cmd_bytes, encrypted_cmd, enckey2)
                
                success = await self.kube_bt_client.write_characteristic_async(
                    client,
                    "f1110020-0190-4567-8fab-4d4158a4eeaf",
                    "f1110022-0190-4567-8fab-4d4158a4eeaf",
                    bytes(encrypted_cmd)
                )
                
                if success:
                    # Wait for response
                    await asyncio.sleep(1)
                    return True
                else:
                    _LOGGER.warning("Failed to write command '%s' to device %s", command, self.mac)
            else:
                _LOGGER.error("No encryption key (enckey2) available for device %s", self.mac)
            
            return False
            
        except Exception as e:
            _LOGGER.error("Command '%s' failed for device %s: %s", command, self.mac, e)
            return False
        finally:
            # Always disconnect
            if client:
                await self.kube_bt_client.disconnect_bt_gatt_async(self.mac, client)
    
    async def open_door_async(self) -> bool:
        """Open the door asynchronously."""
        cmd = '@0028cact={"cmd":"C30B","val":1}#'
        return await self._send_command_async(cmd)
    
    async def close_door_async(self) -> bool:
        """Close the door asynchronously."""
        cmd = '@0028cact={"cmd":"C30B","val":4}#'
        return await self._send_command_async(cmd)
    
    async def toggle_door_async(self) -> bool:
        """Toggle the door asynchronously."""
        cmd = '@0028cact={"cmd":"C30B","val":8}#'
        return await self._send_command_async(cmd)
    
    async def open_slightly_async(self) -> bool:
        """Open slightly asynchronously."""
        cmd = '@0030cact={"cmd":"C30B","val":128}#'
        return await self._send_command_async(cmd)
    
    async def control_lights_async(self) -> bool:
        """Control lights asynchronously."""
        cmd = '@0030cact={"cmd":"C30B","val":256}#'
        return await self._send_command_async(cmd)
    
    async def get_device_status_async(self) -> dict:
        """
        Get device status asynchronously.
        
        Returns:
            dict: Device status information
        """
        client = None
        try:
            # Connect and authenticate
            if not await self._connect_and_authenticate_async():
                return {}
            
            client = self.kube_bt_client.connections.get(self.mac)
            if not client:
                return {}
            
            device = self.kube_bt_client.get_kube_device(self.mac)
            
            # Send status request commands
            commands = [
                '@0005kbinf#',  # Basic info
                '@0004cinf#',   # Configuration info
            ]
            
            for cmd in commands:
                enckey2 = device.get_device_param_bytes("enckey2")
                if enckey2:
                    cmd_bytes = cmd.encode('utf-8')
                    encrypted_cmd = bytearray(len(cmd_bytes))
                    self.kube_bt_client.cipher_helper_xor_byte_arrays(cmd_bytes, encrypted_cmd, enckey2)
                    
                    await self.kube_bt_client.write_characteristic_async(
                        client,
                        "f1110020-0190-4567-8fab-4d4158a4eeaf",
                        "f1110022-0190-4567-8fab-4d4158a4eeaf",
                        bytes(encrypted_cmd)
                    )
                    
                    # Wait between commands
                    await asyncio.sleep(0.5)
            
            # Wait for responses
            await asyncio.sleep(2)
            
            # Extract status from device parameters
            status = {}
            for key, value in device.device_params.items():
                if isinstance(value, (bytes, bytearray)):
                    try:
                        status[key] = value.decode('utf-8', errors='ignore')
                    except:
                        status[key] = value.hex()
                else:
                    status[key] = str(value)
            
            return status
            
        except Exception as e:
            _LOGGER.error("Status request failed for device %s: %s", self.mac, e)
            return {}
        finally:
            # Always disconnect
            if client:
                await self.kube_bt_client.disconnect_bt_gatt_async(self.mac, client)


# Convenience functions for Home Assistant integration
def create_kube_commands(mac: str, passkey: str, master_key: Optional[str] = None, kube_bt_client: Optional[KubeBtClient] = None) -> KubeCommands:
    """
    Factory function to create a KubeCommands instance.
    
    Args:
        mac: Device MAC address
        passkey: Device passkey for authentication
        master_key: Optional master key for device setup operations
        kube_bt_client: Optional KubeBtClient instance
        
    Returns:
        KubeCommands: Configured KubeCommands instance
    """
    return KubeCommands(mac, passkey, master_key, kube_bt_client)


# Export commonly used enums for external use
__all__ = [
    'KubeCommands',
    'C30BOperation',
    'create_kube_commands'
]
