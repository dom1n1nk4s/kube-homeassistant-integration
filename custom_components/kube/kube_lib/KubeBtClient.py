import asyncio
import logging
import time
from typing import Dict, Optional, Any, List
import uuid
from .KubeDevice import KubeDevice
from .BluetoothPayload import BluetoothPayload

_LOGGER = logging.getLogger(__name__)

try:
    import bleak
    from bleak import BleakClient, BleakScanner
    from bleak.backends.characteristic import BleakGATTCharacteristic
    from bleak.backends.service import BleakGATTService
    BLEAK_AVAILABLE = True
except ImportError:
    BLEAK_AVAILABLE = False
    print("Warning: bleak library not available. Install with: pip install bleak")

try:
    from bleak_retry_connector import establish_connection
    BLEAK_RETRY_AVAILABLE = True
except ImportError:
    BLEAK_RETRY_AVAILABLE = False
    print("Warning: bleak-retry-connector library not available. Install with: pip install bleak-retry-connector")
    print("Connection reliability may be reduced without bleak-retry-connector")


class DelayedCommandHandler:
    """Handles delayed command execution using asyncio"""
    
    def __init__(self):
        pass
    
    def post(self, runnable):
        """Execute runnable immediately"""
        asyncio.create_task(runnable())
    
    async def post_delayed(self, runnable, delay_ms):
        """Execute runnable after delay"""
        await asyncio.sleep(delay_ms / 1000.0)  # Convert ms to seconds
        await runnable()


class KubeBtClient:
    """
    Bluetooth client that mimics Android BluetoothGatt functionality using bleak library
    """
    
    def __init__(self):
        if not BLEAK_AVAILABLE:
            raise ImportError("bleak library is required. Install with: pip install bleak")
        
        self.devices: Dict[str, KubeDevice] = {}
        self.connections: Dict[str, BleakClient] = {}
        self.connection_states: Dict[str, int] = {}  # 0=disconnected, 1=connecting, 2=connected
        self.delayed_command_handler = DelayedCommandHandler()
        self.notification_callbacks: Dict[str, Any] = {}
        
        # Connection state constants
        self.STATE_DISCONNECTED = 0
        self.STATE_CONNECTING = 1
        self.STATE_CONNECTED = 2
    
    def get_kube_device(self, address: str) -> KubeDevice:
        """Get or create a KubeDevice for the given address"""
        if address not in self.devices:
            device = KubeDevice(address)
            device.set_kube_bt_client(self)  # Inject KubeBtClient reference
            self.devices[address] = device
        return self.devices[address]
    
    def get_device_connection_state(self, address: str) -> int:
        """Get connection state for device"""
        return self.connection_states.get(address, self.STATE_DISCONNECTED)
    
    def set_device_connection_state(self, address: str, state: int):
        """Set connection state for device"""
        self.connection_states[address] = state
    
    async def connect_bt_gatt_async(self, address: str, use_background_connection: bool = False, 
                                   connection_timeout: int = 30000) -> Optional[BleakClient]:
        """
        Connect to GATT server asynchronously with retry logic for improved reliability.
        
        Args:
            address: Bluetooth device address
            use_background_connection: Whether to use background connection (ignored in bleak)
            connection_timeout: Connection timeout in milliseconds (default 30s for paired devices)
            
        Returns:
            BleakClient instance if successful, crashes on failure
        """
        self.set_device_connection_state(address, self.STATE_CONNECTING)
        print(f"Attempting to connect to {address} with {connection_timeout/1000}s timeout...")
        
        # Use bleak-retry-connector for more reliable connection establishment if available
        if BLEAK_RETRY_AVAILABLE:
            print(f"Using bleak-retry-connector for reliable connection to {address}")
            try:
                # First scan for the device to get BLEDevice object
                print(f"Scanning for device {address}...")
                device = await BleakScanner.find_device_by_address(
                    address, 
                    timeout=connection_timeout / 1000.0
                )
                
                if device is None:
                    raise RuntimeError(f"Bluetooth device {address} not found during scan!")
                
                print(f"Found device: {device.name or 'Unknown'} ({device.address})")
                
                # Now establish connection with the BLEDevice object
                client = await establish_connection(
                    BleakClient,
                    device,
                    device.name or address,  # name parameter
                    timeout=connection_timeout / 1000.0
                )
            except Exception as e:
                self.set_device_connection_state(address, self.STATE_DISCONNECTED)
                print(f"FATAL ERROR: Bluetooth device {address} connection failed with bleak-retry-connector: {e}")
                raise RuntimeError(f"Bluetooth device {address} not found or connection failed!")
        else:
            # Fallback to standard BleakClient connection
            print(f"Warning: Using standard BleakClient.connect() without retry logic")
            client = BleakClient(address, timeout=connection_timeout / 1000.0)
            await client.connect()
        
        if client.is_connected:
            self.connections[address] = client
            self.set_device_connection_state(address, self.STATE_CONNECTED)
            device = self.get_kube_device(address)
            device.set_bluetooth_gatt(client)
            
            print(f"Successfully connected to {address}")
            return client
        else:
            self.set_device_connection_state(address, self.STATE_DISCONNECTED)
            print(f"FATAL ERROR: Bluetooth device {address} not found or connection failed!")
            raise RuntimeError(f"Bluetooth device {address} not found or connection failed!")
    
    
    async def disconnect_bt_gatt_async(self, address: str, client: BleakClient = None):
        """Disconnect from GATT server asynchronously"""
        try:
            if client is None:
                client = self.connections.get(address)
            
            if client and client.is_connected:
                await client.disconnect()
            
            # Clean up
            if address in self.connections:
                del self.connections[address]
            self.set_device_connection_state(address, self.STATE_DISCONNECTED)
            
            device = self.get_kube_device(address)
            device.set_bluetooth_gatt(None)
            
        except Exception as e:
            print(f"Disconnect failed for {address}: {e}")
    
    async def discover_services_async(self, client: BleakClient) -> bool:
        """Discover services asynchronously"""
        try:
            # In bleak, services are automatically discovered on connection
            # We can trigger a refresh if needed
            services = client.services
            service_count = len(list(services))
            print(f"Service discovery found {service_count} services")
            return service_count > 0
        except Exception as e:
            print(f"Service discovery failed: {e}")
            return False
    
    def format_data_output(self, data: bytes, operation: str, uuid: str) -> str:
        """Format data output in hex, ASCII, and raw bytes"""
        if not data:
            return f"{operation} from {uuid}: None"
        
        # Hex representation
        hex_str = data.hex().upper()
        hex_formatted = ' '.join(hex_str[i:i+2] for i in range(0, len(hex_str), 2))
        
        # ASCII representation (replace non-printable chars with '.')
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        
        # Raw bytes representation
        raw_bytes = str(list(data))
        
        output = f"""
{operation} from {uuid}:
  HEX:   {hex_formatted}
  ASCII: {ascii_str}
  RAW:   {raw_bytes}
  LEN:   {len(data)} bytes"""
        
        return output

    async def read_characteristic_async(self, client: BleakClient, service_uuid: str, 
                                      characteristic_uuid: str) -> Optional[bytes]:
        """Read characteristic value asynchronously"""
        try:
            value = await client.read_gatt_char(characteristic_uuid)
            if value:
                print(f"[READ] {self.format_data_output(value, 'READ DATA', characteristic_uuid)}")
            else:
                print(f"[READ] READ DATA from {characteristic_uuid}: None")
            return value
        except Exception as e:
            print(f"Read characteristic failed for {characteristic_uuid}: {e}")
            return None
    
    
    async def write_characteristic_async(self, client: BleakClient, service_uuid: str,
                                       characteristic_uuid: str, data: bytes, 
                                       response: bool = True) -> bool:
        """Write characteristic value asynchronously with enhanced error handling"""
        try:
            # Check connection status before writing
            if not client.is_connected:
                _LOGGER.error("Cannot write to characteristic %s: Client not connected", characteristic_uuid)
                return False
            
            _LOGGER.debug("Writing data to characteristic %s: %s", characteristic_uuid, data.hex())
            
            # Add timeout to prevent hanging on connection issues
            await asyncio.wait_for(
                client.write_gatt_char(characteristic_uuid, data, response=response),
                timeout=10.0  # 10 second timeout
            )
            
            _LOGGER.debug("Successfully wrote to characteristic %s", characteristic_uuid)
            return True
            
        except asyncio.TimeoutError:
            _LOGGER.error("Write characteristic timed out for %s", characteristic_uuid)
            return False
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "disconnected" in error_msg:
                _LOGGER.error("Connection lost during write to characteristic %s: %s", characteristic_uuid, e)
                # Mark device as disconnected
                for address, conn in self.connections.items():
                    if conn == client:
                        self.set_device_connection_state(address, self.STATE_DISCONNECTED)
                        break
            else:
                _LOGGER.error("Write characteristic failed for %s: %s", characteristic_uuid, e)
            return False

    async def write_bt_gatt_characteristic_with_encryption_async(self, mac: str, service_uuid: str, characteristic_uuid: str,
                                                               bluetooth_gatt: BleakClient, bluetooth_gatt_characteristic,
                                                               bundle: dict):
        """
        Write BT GATT Characteristic with encryption handling - Enhanced async version with connection monitoring
        Handles specific characteristic UUIDs with their respective encryption/data processing logic
        """
        try:
            # Check connection status before processing
            if not bluetooth_gatt.is_connected:
                _LOGGER.error("Cannot write to characteristic %s: Device %s not connected", characteristic_uuid, mac)
                return False
            
            data_to_write = None
            
            if characteristic_uuid.lower() == "f1110022-0190-4567-8fab-4d4158a4eeaf":
                # Command characteristic - needs XOR encryption with enckey2
                cmd_type = bundle.get("cmdType")
                if cmd_type is not None and cmd_type != "":
                    cmd = bundle.get("cmd")
                    if cmd is not None:
                        cmd_bytes = cmd.encode('utf-8')
                        device_param_bytes = self.get_kube_device(mac).get_device_param_bytes("enckey2")
                        if device_param_bytes:
                            encrypted_bytes = bytearray(len(cmd_bytes))
                            self.cipher_helper_xor_byte_arrays(cmd_bytes, encrypted_bytes, device_param_bytes)
                            data_to_write = bytes(encrypted_bytes)
                        else:
                            data_to_write = cmd_bytes
                            
            elif characteristic_uuid.lower() == "f1170005-0190-4567-8fab-4d4158a4eeaf":
                # Token characteristic
                token = self.get_kube_device(mac).get_device_param_bytes("token")
                if token:
                    data_to_write = token
                else:
                    print("WARNING TOKEN IS EMPTY------------------------")
                    
            elif characteristic_uuid.lower() == "f1170007-0190-4567-8fab-4d4158a4eeaf":
                # Master key characteristic - complex encryption logic
                master_key = bundle.get("masterkey", "").encode('utf-8')
                if master_key:
                    device = self.get_kube_device(mac)
                    sn_bytes = device.get_device_param_or_default("sn", "").encode('utf-8')
                    
                    # Encrypt master key with serial number
                    encrypted_data = self.encrypt_data(master_key, sn_bytes)
                    
                    # Store keys in device
                    device.put_device_param_bytes("masterkey", master_key)
                    device.put_device_param_bytes("enckey0", encrypted_data)
                    
                    # Check if master key is already set
                    master_set = device.get_device_param_or_default("masterset", "UNSET")
                    if master_set != "UNSET":
                        # XOR with enckey0 if master key is already set
                        enckey0 = device.get_device_param_bytes("enckey0")
                        if enckey0:
                            xor_result = bytearray(len(master_key))
                            self.cipher_helper_xor_byte_arrays(master_key, xor_result, enckey0)
                            data_to_write = bytes(xor_result)
                        else:
                            data_to_write = master_key
                    else:
                        data_to_write = master_key
                        
            elif characteristic_uuid.lower() == "f1170004-0190-4567-8fab-4d4158a4eeaf":
                # Passkey characteristic - AES encryption logic
                passkey = bundle.get("passkey", "").encode('utf-8')
                if passkey:
                    device = self.get_kube_device(mac)
                    sn_bytes = device.get_device_param_or_default("sn", "").encode('utf-8')
                    
                    # Store passkey
                    device.store_string_value("passkey", bundle.get("passkey", ""))
                    
                    # Check for special passkey
                    if bundle.get("passkey", "") == "DEADBEEFDEADBEEF":
                        device.store_int_value("encrypted_channel", 0)
                    
                    passkey_set = device.get_device_param_or_default("passkeyset", "UNSET")
                    if passkey_set == "UNSET":
                        # XOR with enckey0
                        enckey0 = device.get_device_param_bytes("enckey0")
                        if enckey0:
                            xor_result = bytearray(len(passkey))
                            self.cipher_helper_xor_byte_arrays(passkey, xor_result, enckey0)
                            data_to_write = bytes(xor_result)
                        else:
                            data_to_write = passkey
                        
                        # Generate enckey1 using AES encryption
                        try:
                            enckey1 = self.encrypt_data(passkey, sn_bytes)
                            device.put_device_param_bytes("enckey1", enckey1)
                        except Exception as e:
                            print(f"Error generating enckey1: {e}")
                    else:
                        # Passkey already set - return error
                        bundle["errorCode"] = "error_masterkey"
                        self.handle_error(mac, self.get_devices_first_payload_group_identifier(mac),
                                        self.get_first_payload_group_class(mac), 
                                        self.get_kube_device(mac), bundle)
                        return
                        
            else:
                # Default case - use raw characteristic value
                characteristic_value = bundle.get("characteristicValue")
                if characteristic_value is not None:
                    if isinstance(characteristic_value, list):
                        data_to_write = bytes(characteristic_value)
                    elif isinstance(characteristic_value, bytes):
                        data_to_write = characteristic_value
                    else:
                        data_to_write = str(characteristic_value).encode('utf-8')
            
            # Write the characteristic with proper error handling
            if data_to_write is not None:
                success = await self.write_characteristic_async(bluetooth_gatt, service_uuid, 
                                                               characteristic_uuid, data_to_write)
                if not success:
                    _LOGGER.error("Failed to write to characteristic %s for device %s", characteristic_uuid, mac)
                    bundle["errorCode"] = "error_write_characteristic"
                    self.handle_error(mac, self.get_devices_first_payload_group_identifier(mac),
                                    self.get_first_payload_group_class(mac), 
                                    self.get_kube_device(mac), bundle)
                    return False
                
                # Set up timeout for command characteristic if needed
                if characteristic_uuid.lower() == "f1110022-0190-4567-8fab-4d4158a4eeaf":
                    # Add a small delay to allow the write to complete
                    await asyncio.sleep(0.1)
                
                return True
            else:
                _LOGGER.warning("No data to write for characteristic %s", characteristic_uuid)
                return False
                
        except Exception as e:
            _LOGGER.error("Error in write_bt_gatt_characteristic_with_encryption_async: %s", e)
            bundle["errorCode"] = "error_write_characteristic"
            self.handle_error(mac, self.get_devices_first_payload_group_identifier(mac),
                            self.get_first_payload_group_class(mac), 
                            self.get_kube_device(mac), bundle)
            return False
    
    async def start_notify_async(self, client: BleakClient, characteristic_uuid: str, 
                                callback: Any) -> bool:
        """Start notifications asynchronously"""
        try:
            await client.start_notify(characteristic_uuid, callback)
            return True
        except Exception as e:
            print(f"Start notify failed for {characteristic_uuid}: {e}")
            return False
    
    async def stop_notify_async(self, client: BleakClient, characteristic_uuid: str) -> bool:
        """Stop notifications asynchronously"""
        try:
            await client.stop_notify(characteristic_uuid)
            return True
        except Exception as e:
            print(f"Stop notify failed for {characteristic_uuid}: {e}")
            return False
      
    def write_bt_gatt_characteristic(self, address: str, service_uuid: str, 
                                   characteristic_uuid: str, client: BleakClient,
                                   characteristic, bundle: dict):
        """Handle write characteristic operation - crashes on failure"""
        # Extract data from bundle
        data = None
        
        if "cmd" in bundle:
            # Command string - convert to bytes
            cmd_str = bundle["cmd"]
            data = cmd_str.encode('utf-8')
        elif "characteristicValue" in bundle:
            # Raw bytes
            data = bundle["characteristicValue"]
            if isinstance(data, list):
                data = bytes(data)
        
        # Allow empty data - it's valid for some characteristics
        if data is None:
            data = b''  # Empty bytes is valid
        
        # This method needs to be converted to async or removed since write_characteristic no longer exists
        asyncio.create_task(self.write_characteristic_async(client, service_uuid, characteristic_uuid, data))
        print(f"Initiated write to characteristic {characteristic_uuid}: {data.hex() if data else '(empty)'}")
    
    def set_indic_bt_gatt(self, address: str, service_uuid: str, characteristic_uuid: str,
                         client: BleakClient, characteristic, bundle: dict):
        """
        Handle set indicator/notification operation - Python port of Java SetIndicBTGatt
        Synchronized method that enables/disables notifications and writes to CCCD descriptor
        """
        is_enabled = bundle.get("enable", True)
        kube_device = self.get_kube_device(address)
        
        def notification_callback(sender, data):
            device = self.get_kube_device(address)
            XORedResult = bytearray(len(data))
            self.cipher_helper_xor_byte_arrays(data, XORedResult, device.get_device_param_bytes("enckey2"))
            
            # Enhanced notification handling with proper buffering
            print(f"[NOTIFY] {self.format_data_output(XORedResult, 'NOTIFICATION FRAGMENT', characteristic_uuid)}")
            
            # Append to notification buffer
            device.append_device_param_bytes(f"notify_{characteristic_uuid}", XORedResult)
            
            # Check for complete messages ending with '#'
            accumulated_data = device.get_device_param_bytes(f"notify_{characteristic_uuid}")
            try:
                # Try to decode and check for message boundaries
                decoded_text = accumulated_data.decode('utf-8', errors='ignore')
                
                # Process complete messages (those ending with '#')
                complete_messages = []
                remaining_data = decoded_text
                
                while '#' in remaining_data:
                    message_end = remaining_data.find('#')
                    complete_message = remaining_data[:message_end + 1]
                    complete_messages.append(complete_message)
                    remaining_data = remaining_data[message_end + 1:]
                
                # If we found complete messages, process them
                if complete_messages:
                    print(f"[NOTIFY] Found {len(complete_messages)} complete message(s)")
                    
                    # Get existing message queue or create new one
                    message_queue_key = f"message_queue_{characteristic_uuid}"
                    existing_queue_data = device.get_device_param_value(message_queue_key)
                    
                    # Initialize queue as list if it doesn't exist or is not a list
                    if existing_queue_data is None or not isinstance(existing_queue_data, list):
                        existing_queue = []
                    else:
                        existing_queue = existing_queue_data
                    
                    for i, message in enumerate(complete_messages):
                        print(f"[NOTIFY] Complete Message {i+1}: {message}")
                        
                        # Add message to queue with timestamp
                        import time
                        message_entry = {
                            "message": message,
                            "timestamp": time.time(),
                            "sequence": len(existing_queue) + 1
                        }
                        existing_queue.append(message_entry)
                        print(f"[NOTIFY] Added message to queue (sequence #{message_entry['sequence']})")
                    
                    # Store updated message queue as a list in device params
                    device.device_params[message_queue_key] = existing_queue
                    
                    # Also store the latest complete message for easy access
                    if complete_messages:
                        latest_message_key = f"latest_message_{characteristic_uuid}"
                        device.store_string_value(latest_message_key, complete_messages[-1])
                        print(f"[NOTIFY] Updated latest message: {latest_message_key}")
                    
                    # Store only the remaining incomplete data
                    if remaining_data:
                        device.put_device_param_bytes(f"notify_{characteristic_uuid}", remaining_data.encode('utf-8'))
                        print(f"[NOTIFY] Buffering incomplete data: {remaining_data}")
                    else:
                        # Clear the buffer if no remaining data
                        device.put_device_param_bytes(f"notify_{characteristic_uuid}", b'')
                        
            except Exception as e:
                print(f"[NOTIFY] Error processing notification data: {e}")
        
        # First, set characteristic notification (equivalent to bluetoothGatt.setCharacteristicNotification)
        if is_enabled:
            success = asyncio.create_task(self.start_notify_async(client, characteristic_uuid, notification_callback))
        else:
            success = asyncio.create_task(self.stop_notify_async(client, characteristic_uuid))
        
        if not success:
            bundle["errorCode"] = "set_indication_failed"
            self.handle_error(address, self.get_devices_first_payload_group_identifier(address),
                            self.get_first_payload_group_class(address), kube_device, bundle)
        else:
            # Pop payload from queue (equivalent to kubeDeviceGetKubeDevice.PopPayloadFromQueue())
            removedPayload = bluetooth_payload_pop_payload_from_queue = kube_device.pop_payload_from_queue()
            
            # Set payload data based on enable/disable (equivalent to BluetoothGattDescriptor values)
            if is_enabled:
                # ENABLE_NOTIFICATION_VALUE = [0x01, 0x00]
                bundle["payload"] = bytes([0x01, 0x00])
            else:
                # DISABLE_NOTIFICATION_VALUE = [0x00, 0x00]
                bundle["payload"] = bytes([0x00, 0x00])
            
            # Create write descriptor payload for CCCD (Client Characteristic Configuration Descriptor)
            cccd_uuid = "00002902-0000-1000-8000-00805f9b34fb"
            
            # Get group class, default to 0 if no payload available
            group_class = 0
            if bluetooth_payload_pop_payload_from_queue is not None:
                group_class = bluetooth_payload_pop_payload_from_queue.get_group_class
            
            write_descriptor_payload = BluetoothPayload.create_write_descriptor_payload(
                address, 
                group_class,
                service_uuid,
                characteristic_uuid,
                cccd_uuid,
                bundle
            )
            
            # Add payload to first position and try process (equivalent to AddPayloadToFirstPosAndTryProcess)
            self.add_payload_to_first_pos_and_try_process(write_descriptor_payload, True)
            
            # Process a payload wrapper (equivalent to kubeDeviceGetKubeDevice.ProcessAPayloadWrapper())
            kube_device.process_a_payload()
    
    def add_payload_to_first_pos_and_try_process(self, bluetooth_payload: BluetoothPayload, is_last: bool):
        """
        Add payload to first position and try process - equivalent to AddPayloadToFirstPosAndTryProcess
        """
        bluetooth_payload.set_able_to_be_processed(is_last)
        device_address = bluetooth_payload.address
        device = self.get_kube_device(device_address)
        device.add_payload_and_try_process(1,bluetooth_payload, is_last)
    
    async def read_descriptor_async(self, client: BleakClient, service_uuid: str,
                                  characteristic_uuid: str, desc_uuid: str) -> Optional[bytes]:
        """Read descriptor value asynchronously"""
        try:
            # In bleak, we need to access descriptors through the characteristic
            service = client.services.get_service(service_uuid)
            if not service:
                print(f"Service {service_uuid} not found")
                return None
            
            characteristic = service.get_characteristic(characteristic_uuid)
            if not characteristic:
                print(f"Characteristic {characteristic_uuid} not found")
                return None
            
            descriptor = characteristic.get_descriptor(desc_uuid)
            if not descriptor:
                print(f"Descriptor {desc_uuid} not found")
                return None
            
            # Read the descriptor value
            value = await client.read_gatt_descriptor(descriptor.handle)
            return value
        except Exception as e:
            print(f"Read descriptor failed for {desc_uuid}: {e}")
            return None
    
    def read_desc_bt_gatt(self, address: str, service_uuid: str, characteristic_uuid: str,
                         desc_uuid: str, client: BleakClient, descriptor):
        """Handle read descriptor operation"""
        device = self.get_kube_device(address)
        
        async def execute_read():
            try:
                print(f"Executing read for descriptor {desc_uuid}")
                data = await self.read_descriptor_async(client, service_uuid, characteristic_uuid, desc_uuid)
                if data is not None:
                    device.put_device_param_bytes(f"read_desc_{desc_uuid}", data)
                    print(f"[READ] {self.format_data_output(data, 'READ DESCRIPTOR', desc_uuid)}")
                else:
                    print(f"Failed to read descriptor {desc_uuid}")
            except Exception as e:
                print(f"Error reading descriptor {desc_uuid}: {e}")
        
        # Execute read operation asynchronously to avoid blocking
        self.delayed_command_handler.post(execute_read)
    
    async def write_descriptor_async(self, client: BleakClient, service_uuid: str,
                                   characteristic_uuid: str, desc_uuid: str, data: bytes) -> bool:
        """Write descriptor value asynchronously"""
        try:
            # In bleak, we need to access descriptors through the characteristic
            service = client.services.get_service(service_uuid)
            if not service:
                print(f"Service {service_uuid} not found")
                return False
            
            characteristic = service.get_characteristic(characteristic_uuid)
            if not characteristic:
                print(f"Characteristic {characteristic_uuid} not found")
                return False
            
            descriptor = characteristic.get_descriptor(desc_uuid)
            if not descriptor:
                print(f"Descriptor {desc_uuid} not found")
                return False
            
            # Write the descriptor value
            print(f"[WRITE] WRITE DESCRIPTOR to {desc_uuid}: {data.hex()}")
            await client.write_gatt_descriptor(descriptor.handle, data)
            return True
        except Exception as e:
            print(f"Write descriptor failed for {desc_uuid}: {e}")
            return False
    
    def write_bluetooth_gatt_descriptor(self, address: str, service_uuid: str, 
                                      characteristic_uuid: str, desc_uuid: str,
                                      client: BleakClient, descriptor, bundle: dict):
        """Handle write descriptor operation"""
        device = self.get_kube_device(address)
        
        async def execute_write():
            try:
                print(f"Executing write for descriptor {desc_uuid}")
                
                # Extract data from bundle
                data = None

                if "payload" in bundle:
                    data = bytes(bundle["payload"])                
                
                if data is not None:
                    success = await self.write_descriptor_async(client, service_uuid, characteristic_uuid, desc_uuid, data)
                    if success:
                        print(f"Wrote to descriptor {desc_uuid}: {data.hex()}")
                    else:
                        print(f"Failed to write to descriptor {desc_uuid}")
                else:
                    print(f"No data to write for descriptor {desc_uuid}")
                    
            except Exception as e:
                print(f"Error writing descriptor {desc_uuid}: {e}")
        
        # Execute write operation asynchronously to avoid blocking
        self.delayed_command_handler.post(execute_write)
    
    def get_devices_first_payload_group_identifier(self, address: str) -> int:
        """Get first payload group identifier for device"""
        device = self.get_kube_device(address)
        payload = device.peek_first_payload()
        return payload.get_group_identifier if payload else 0
    
    def get_first_payload_group_class(self, address: str) -> int:
        """Get first payload group class for device"""
        device = self.get_kube_device(address)
        payload = device.peek_first_payload()
        return payload.get_group_class if payload else 0
    
    
    async def cleanup(self):
        """Clean up all connections and resources"""
        try:
            # Disconnect all devices asynchronously
            for address, client in list(self.connections.items()):
                await self.disconnect_bt_gatt_async(address, client)
            
            # Clear all device data
            self.devices.clear()
            self.connections.clear()
            self.connection_states.clear()
            self.notification_callbacks.clear()
                
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    # Bluetooth response handling methods (converted from Java)
    
    def get_characteristic_value(self, characteristic) -> Optional[bytes]:
        """Get value from characteristic (handles different characteristic types)"""
        if hasattr(characteristic, 'value'):
            return characteristic.value
        elif isinstance(characteristic, bytes):
            return characteristic
        else:
            return None
    
    def encrypt_data(self, unpadded_key: bytes, data: bytes) -> bytes:
        """Encrypt data using AES/ECB/NoPadding (converted from Java CipherHelper.encryptData)"""
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            # Handle string padding: if input appears to be UTF-8 encoded strings,
            # decode them, pad to 16 characters with leading zeros using zfill, then re-encode
            try:
                # Try to decode as UTF-8 to see if these are string inputs
                key_str = unpadded_key.decode('utf-8')
                data_str = data.decode('utf-8')
                
                # Pad strings to 16 characters with leading zeros using zfill
                if len(key_str) < 16:
                    key_str = key_str.zfill(16)
                elif len(key_str) > 16:
                    key_str = key_str[:16]
                    
                if len(data_str) < 16:
                    data_str = data_str.zfill(16)
                elif len(data_str) > 16:
                    data_str = data_str[:16]
                
                # Re-encode to bytes
                key = key_str.encode('utf-8')
                padded_data = data_str.encode('utf-8')
                
            except UnicodeDecodeError as e:
                # Not UTF-8 strings, use original byte padding logic
                print(f"Warning: Input not UTF-8 decodable, using byte padding: {e}")
                if len(unpadded_key) > 16:
                    key = unpadded_key[:16]
                else:
                    key = unpadded_key.rjust(16, b'0')
                
                if len(data) > 16:
                    padded_data = data[:16]
                else:
                    padded_data = data.rjust(16, b'0')
            
            # Create AES cipher in ECB mode (no padding)
            cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
            encryptor = cipher.encryptor()
            
            # Encrypt the data
            encrypted = encryptor.update(padded_data) + encryptor.finalize()
            return encrypted
            
        except ImportError:
            print("FATAL ERROR: cryptography library not available. Install with: pip install cryptography")
            import sys
            sys.exit(1)
        except Exception as e:
            print(f"FATAL ERROR in AES encryption: {e}")
            import sys
            sys.exit(1)
    
    def handle_error(self, device_address: str, group_identifier: int, group_class: int,
                    kube_device, bundle: dict):
        """Handle error"""
        print(f"Error for device {device_address}: {bundle}")
        # This would be where you'd handle the actual error processing
        # For now, just log the error
    
    def add_payload_and_try_process(self, position_type, bluetooth_payload: BluetoothPayload, is_last):
        """
        Wrapper method that calls add_payload_and_try_process on the appropriate device
        based on the payload's MAC address
        """
        bluetooth_payload.set_able_to_be_processed(is_last)
        device_address = bluetooth_payload.address
        device = self.get_kube_device(device_address)
        device.add_payload_and_try_process(position_type, bluetooth_payload, is_last)

    def cipher_helper_xor_byte_arrays(self, source: bytes, destination: bytearray, key: bytes) -> bool:
        """
        XOR byte arrays similar to CipherHelper.xorByteArrays from Java
        Modifies destination array in-place
        Returns True on success, False if any input is None
        """
        if source is None or destination is None or key is None:
            return False
        
        for i in range(len(source)):
            destination[i] = (source[i] ^ key[i % 16]) & 0xFF
        
        return True
