from typing import Any, Optional
from .BluetoothPayload import BluetoothPayload


class KubeDevice:
    """Represents a Kube Bluetooth device"""
    
    def __init__(self, address: str):
        self.address = address
        self.device_params = {}
        self.payload_queue = []
        self.bluetooth_gatt = None
        self.pending_reads = {}  # Track pending read operations
        self.read_callbacks = {}  # Store callbacks for read operations
        self.being_processed = False
        
    def store_string_value(self, key: str, value: str):
        self.device_params[key] = value
        
    def store_int_value(self, key: str, value: int):
        self.device_params[key] = value
        
    def put_device_param_bytes(self, key: str, value: bytes):
        self.device_params[key] = value

    def append_device_param_bytes(self, key: str, value: bytes):
        if key in self.device_params:
            # If key exists, append the new bytes to existing bytes
            self.device_params[key] += value
        else:
            # If key doesn't exist, create it with the new value
            self.device_params[key] = value
        
    def get_device_param_value(self, key: str) -> Any:
        return self.device_params.get(key)
        
    def get_device_param_or_default(self, key: str, default: Any) -> Any:
        return self.device_params.get(key, default)
        
    def get_device_param_bytes(self, key: str) -> bytes:
        return self.device_params.get(key, b'')

    def peek_first_payload(self) -> Optional[BluetoothPayload]:
        return self.payload_queue[0] if self.payload_queue else None
        
    def remove_and_retrieve_first_payload(self) -> Optional[BluetoothPayload]:
        if not self.payload_queue:
            print("FATAL ERROR: Attempted to remove payload from empty queue!")
            raise RuntimeError("Payload queue is empty - cannot remove payload")
        return self.payload_queue.pop(0)
        
    def set_bluetooth_gatt(self, gatt):
        self.bluetooth_gatt = gatt
    
    def get_address(self) -> str:
        """Get the device address"""
        return self.address  
    
    def pop_payload_from_queue(self) -> Optional[BluetoothPayload]:
        """Remove and return the first payload from queue (alias for remove_and_retrieve_first_payload)"""
        return self.remove_and_retrieve_first_payload()
    
    def add_payload_and_try_process(self, position_type, bluetooth_payload, is_last):
        """
        Add payload to device queue and try to process it
        Moved from OperationBuilder to KubeDevice
        """
        if position_type == 1:
            self.payload_queue.insert(0, bluetooth_payload)
        elif position_type == 2:
            self.payload_queue.insert(1 if len(self.payload_queue) > 0 else 0, bluetooth_payload)
        elif position_type == 3:
            self.payload_queue.append(bluetooth_payload)
        if not self.being_processed and is_last and self.able_to_be_processed_count() <= 1:
            self.process_a_payload()
    
    def able_to_be_processed_count(self):
        """
        Count how many payloads in the queue are able to be processed
        Moved from OperationBuilder to KubeDevice
        """
        count = 0
        for payload in self.payload_queue:
            if payload.able_to_be_processed():
                count += 1
        return count
    
    def process_a_payload(self):
        """
        Process the first payload in the queue
        Moved from OperationBuilder to KubeDevice
        """
        # KubeBtClient reference should be injected, no import needed

        self.being_processed = True
        payload: BluetoothPayload | None = self.payload_queue[0] if self.payload_queue else None
        
        if payload is None:
            self.being_processed = False
            return
        
        # We need access to KubeBtClient for operations
        # This will be injected when needed
        if not hasattr(self, 'kube_bt_client') or self.kube_bt_client is None:
            print("FATAL ERROR: KubeBtClient not available for payload processing")
            raise RuntimeError("KubeBtClient not available for payload processing")
        
        # Set the current address from the payload
        current_address = payload.address
        connection_state = self.kube_bt_client.get_device_connection_state(current_address)
        service = self.get_service_from_payload(payload)
        characteristic = self.get_characteristic_from_payload(payload, service)
        command_type = payload.command_type
        
        if command_type == 1:  # CONNECT
            self.handle_connect(connection_state, payload)
        elif command_type == 2:  # DISCOVER
            self.handle_discover(connection_state)
        elif command_type == 3:  # DISCONNECT
            self.handle_disconnect()
        elif command_type == 11:  # READ CHARACTERISTIC
            self.handle_read_characteristic(connection_state, payload, characteristic)
        elif command_type == 12:  # WRITE CHARACTERISTIC
            self.handle_write_characteristic(connection_state, payload, characteristic)
        elif command_type == 13:  # SET INDICATOR
            self.handle_set_indicator(connection_state, payload, characteristic)
        elif command_type == 31:  # READ DESCRIPTOR
            self.handle_read_descriptor(connection_state, payload, characteristic)
        elif command_type == 32:  # WRITE DESCRIPTOR
            self.handle_write_descriptor(connection_state, payload, characteristic)
        elif command_type == 41:  # SLEEP
            self.handle_sleep(payload)
        
        self.being_processed = False
    
    def set_kube_bt_client(self, kube_bt_client):
        """Set the KubeBtClient reference for this device"""
        self.kube_bt_client = kube_bt_client
    
    def get_service_from_payload(self, payload):
        """Get service from payload"""
        if payload.get_service_uuid() is not None and self.bluetooth_gatt is not None:
            try:
                # In bleak, services are accessed through the services property
                service_uuid = payload.get_service_uuid()
                return self.bluetooth_gatt.services.get_service(service_uuid)
            except Exception as e:
                print(f"Error getting service {payload.get_service_uuid()}: {e}")
                return None
        return None

    def get_characteristic_from_payload(self, payload, service):
        """Get characteristic from payload"""
        if payload.get_characteristic_uuid() is not None and service is not None:
            try:
                characteristic_uuid = payload.get_characteristic_uuid()
                return service.get_characteristic(characteristic_uuid)
            except Exception as e:
                print(f"Error getting characteristic {payload.get_characteristic_uuid()}: {e}")
                return None
        return None

    def handle_connect(self, connection_state, payload):
        """Handle connect command"""
        if self.address is None:
            self.report_error("error_no_address")
            return
            
        if connection_state == 0:
            params = payload.get_payload_param_bundle
            use_background_connection = params.get("useBackgroundConnection", False)
            connection_timeout = params.get("connectionTimeout", 30000)  # Default to 30s
            self.bluetooth_gatt = self.kube_bt_client.connect_bt_gatt(
                self.address, use_background_connection, connection_timeout
            )
            if self.bluetooth_gatt is not None:
                self.store_int_value("client_link_state", 4)
                print(f"Successfully connected to {self.address}")
                # Continue with next command
                self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())
            else:
                print(f"Failed to connect to {self.address}")
                self.report_error("error_connection_failed")
        elif connection_state == 2:
            # Already connected, process next command
            print(f"Already connected to {self.address}")
            self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())
        else:
            self.report_error("error_connection_state")

    def handle_discover(self, connection_state):
        """Handle discover command"""
        if connection_state != 2:
            self.report_error("error_connection_state")
        elif self.bluetooth_gatt is None:
            self.report_error("error_connection")
        else:
            success = self.kube_bt_client.discover_services(self.bluetooth_gatt)
            if not success:
                self.report_error("error_discover_services")
            else:
                print("Service discovery completed successfully")
                # Continue with next command
                self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())

    def handle_disconnect(self):
        """Handle disconnect command"""
        if self.address is None:
            self.report_error("error_no_address")
            return
            
        if self.bluetooth_gatt is not None:
            self.kube_bt_client.disconnect_bt_gatt(self.address, self.bluetooth_gatt)
        else:
            self.report_error("error_connection")

    def handle_read_characteristic(self, connection_state, payload, characteristic):
        """Handle read characteristic command"""
        if self.address is None:
            self.report_error("error_no_address")
            return
            
        if connection_state != 2:
            self.report_error("error_connection_state")
        elif self.bluetooth_gatt is None:
            self.report_error("error_connection")
        else:
            print(f"Reading characteristic {payload.get_characteristic_uuid()}")
            
            # Define callback to continue processing after read completes
            def read_callback(success, data):
                if success:
                    print(f"Read operation completed successfully for {payload.get_characteristic_uuid()}")
                else:
                    print(f"Read operation failed for {payload.get_characteristic_uuid()}")
                # do not continue, response will handle it
                # self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())
            
            # Execute read with callback
            self.kube_bt_client.handle_read_char(
                self.address,
                payload.get_service_uuid(),
                payload.get_characteristic_uuid(),
                self.bluetooth_gatt,
                characteristic,
                read_callback
            )

    def handle_write_characteristic(self, connection_state, payload, characteristic):
        """Handle write characteristic command"""
        if self.address is None:
            self.report_error("error_no_address")
            return
            
        if connection_state != 2:
            self.report_error("error_connection_state")
        elif self.bluetooth_gatt is None:
            self.report_error("error_connection")
        else:
            print(f"Writing to characteristic {payload.get_characteristic_uuid()}")
            self.kube_bt_client.write_bt_gatt_characteristic_with_encryption(
                self.address,
                payload.get_service_uuid(),
                payload.get_characteristic_uuid(),
                self.bluetooth_gatt,
                characteristic,
                payload.get_payload_param_bundle
            )
            # Continue with next command
            self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())

    def handle_set_indicator(self, connection_state, payload, characteristic):
        """Handle set indicator command"""
        if self.address is None:
            self.report_error("error_no_address")
            return
            
        if connection_state != 2:
            self.report_error("error_connection_state")
        elif self.bluetooth_gatt is None:
            self.report_error("error_connection")
        else:
            print(f"Setting indicator for characteristic {payload.get_characteristic_uuid()}")
            self.kube_bt_client.set_indic_bt_gatt(
                self.address,
                payload.get_service_uuid(),
                payload.get_characteristic_uuid(),
                self.bluetooth_gatt,
                characteristic,
                payload.get_payload_param_bundle
            )
            # Continue with next command
            # self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())

    def handle_read_descriptor(self, connection_state, payload, characteristic):
        """Handle read descriptor command"""
        if self.address is None:
            self.report_error("error_no_address")
            return
            
        if connection_state != 2:
            self.report_error("error_connection_state")
        elif self.bluetooth_gatt is None:
            self.report_error("error_connection")
        else:
            print(f"Reading descriptor {payload.get_desc_uuid()}")
            try:
                descriptor = None
                if characteristic is not None:
                    descriptor = characteristic.get_descriptor(payload.get_desc_uuid())
                
                self.kube_bt_client.read_desc_bt_gatt(
                    self.address,
                    payload.get_service_uuid(),
                    payload.get_characteristic_uuid(),
                    payload.get_desc_uuid(),
                    self.bluetooth_gatt,
                    descriptor
                )
                # reads have responses which need to continue the chain
                # self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())
            except Exception as e:
                print(f"Error in handle_read_descriptor: {e}")
                # self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())

    def handle_write_descriptor(self, connection_state, payload, characteristic):
        """Handle write descriptor command"""
        if self.address is None:
            self.report_error("error_no_address")
            return
            
        if connection_state != 2:
            self.report_error("error_connection_state")
        elif self.bluetooth_gatt is None:
            self.report_error("error_connection")
        else:
            print(f"Writing descriptor {payload.get_desc_uuid()}")
            try:
                descriptor = None
                if characteristic is not None:
                    descriptor = characteristic.get_descriptor(payload.get_desc_uuid())
                
                self.kube_bt_client.write_bluetooth_gatt_descriptor(
                    self.address,
                    payload.get_service_uuid(),
                    payload.get_characteristic_uuid(),
                    payload.get_desc_uuid(),
                    self.bluetooth_gatt,
                    descriptor,
                    payload.get_payload_param_bundle
                )
                # Continue with next command
                self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())
            except Exception as e:
                print(f"Error in handle_write_descriptor: {e}")
                # Continue with next command even on error
                self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())

    def handle_sleep(self, payload):
        """Handle sleep command"""
        sleep_time = payload.get_payload_param_bundle.get("sleep", 0)
        if sleep_time <= 0:
            self.kube_bt_client.delayed_command_handler.post(self._create_command_done_runnable())
        else:
            self.kube_bt_client.delayed_command_handler.post_delayed(
                self._create_command_done_runnable(), sleep_time
            )

    def report_error(self, error_code):
        """Report error"""
        error_bundle = {"errorCode": error_code}
        
        # CRASH THE APPLICATION ON ANY ERROR
        print(f"FATAL ERROR: {error_code}")
        print(f"Address: {self.address}")
        
        if self.address is not None:
            group_identifier = self.kube_bt_client.get_devices_first_payload_group_identifier(self.address)
            group_class = self.kube_bt_client.get_first_payload_group_class(self.address)
            print(f"Group Identifier: {group_identifier}")
            print(f"Group Class: {group_class}")
            print(f"Device: {self}")
        else:
            print("No address available")
        
        # CRASH THE APPLICATION
        raise RuntimeError(f"FATAL ERROR: {error_code} - Application terminating")
    
    def _create_command_done_runnable(self):
        """Create a runnable for command completion"""
        def command_done():
            self.process_next_command()
        return command_done
    
    def process_next_command(self):
        """Process the next command in the queue"""
        if self.payload_queue:
            self.payload_queue.pop(0)  # Remove processed payload
        if self.payload_queue:
            self.process_a_payload()  # Process next payload
