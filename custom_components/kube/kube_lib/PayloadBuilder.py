from collections import deque
from typing import List, Optional
import copy

from .BluetoothPayload import BluetoothPayload

class PayloadBuilder:
    def __init__(self, group_class: int, mac_address: str):
        """
        Initialize PayloadBuilder
        
        Args:
            group_class (int): Group class identifier
            mac_address (str): MAC address of the device
        """
        self.group_class = group_class
        self.mac_address = mac_address
        self.device_descriptor = "TAG device"
        self._linked_list = deque()

    def add_connect_payload(self, timeout: int, use_background_connection: bool) -> 'PayloadBuilder':
        """
        Add a connect payload to the builder
        
        Args:
            timeout (int): Connection timeout in milliseconds
            use_background_connection (bool): Whether to use background connection
            
        Returns:
            PayloadBuilder: Self for method chaining
        """
        payload = BluetoothPayload.create_connect_payload(
            self.mac_address, 
            self.group_class, 
            timeout, 
            use_background_connection
        )
        self._add_to_list(3, payload)
        return self

    def add_disconnect_payload(self) -> 'PayloadBuilder':
        """
        Add a disconnect payload to the builder
        
        Returns:
            PayloadBuilder: Self for method chaining
        """
        payload = BluetoothPayload.create_disconnect_payload(
            self.mac_address, 
            self.group_class
        )
        self._add_to_list(3, payload)
        return self

    def add_discovery_payload(self) -> 'PayloadBuilder':
        """
        Add a discovery payload to the builder
        
        Returns:
            PayloadBuilder: Self for method chaining
        """
        payload = BluetoothPayload.create_discover_payload(
            self.mac_address, 
            self.group_class
        )
        self._add_to_list(3, payload)
        return self

    def add_read_characteristic_payload(self, service_uuid: str, characteristic_uuid: str) -> 'PayloadBuilder':
        """
        Add a read characteristic payload to the builder
        
        Args:
            service_uuid (str): Service UUID
            characteristic_uuid (str): Characteristic UUID
            
        Returns:
            PayloadBuilder: Self for method chaining
        """
        payload = BluetoothPayload.create_read_characteristic_payload(
            self.mac_address, 
            self.group_class, 
            service_uuid, 
            characteristic_uuid
        )
        self._add_to_list(3, payload)
        return self

    def add_set_indicator_payload(self, service_uuid: str, characteristic_uuid: str, enable: bool) -> 'PayloadBuilder':
        """
        Add a set indicator payload to the builder
        
        Args:
            service_uuid (str): Service UUID
            characteristic_uuid (str): Characteristic UUID
            enable (bool): Whether to enable the indicator
            
        Returns:
            PayloadBuilder: Self for method chaining
        """
        payload = BluetoothPayload.create_set_indicator_payload(
            self.mac_address, 
            self.group_class, 
            service_uuid, 
            characteristic_uuid, 
            enable
        )
        self._add_to_list(3, payload)
        return self

    def add_sleep_payload(self, sleep_duration: int) -> 'PayloadBuilder':
        """
        Add a sleep payload to the builder
        
        Args:
            sleep_duration (int): Sleep duration in milliseconds
            
        Returns:
            PayloadBuilder: Self for method chaining
        """
        payload = BluetoothPayload.create_sleep_payload(
            self.mac_address, 
            self.group_class, 
            sleep_duration
        )
        self._add_to_list(3, payload)
        return self

    def add_write_characteristic_payload(self, service_uuid: str, characteristic_uuid: str, bundle: dict) -> 'PayloadBuilder':
        """
        Add a write characteristic payload to the builder
        Handles command chunking if cmdType is present
        
        Args:
            service_uuid (str): Service UUID
            characteristic_uuid (str): Characteristic UUID
            bundle (dict): Parameter bundle
            
        Returns:
            PayloadBuilder: Self for method chaining
        """
        if bundle.get("cmdType") is not None:
            cmd_string = bundle.get("cmd")
            if cmd_string is not None:
                length = len(cmd_string)
                byte_index = 0
                
                while byte_index < length:
                    end_index = byte_index + 16
                    str_substring = cmd_string[byte_index:end_index] if end_index < len(cmd_string) else cmd_string[byte_index:]
                    
                    # Create a copy of the bundle
                    bundle_copy = copy.deepcopy(bundle)
                    bundle_copy["cmd"] = str_substring
                    
                    payload = BluetoothPayload.create_write_characteristic_payload(
                        self.mac_address, 
                        self.group_class, 
                        service_uuid, 
                        characteristic_uuid, 
                        bundle_copy
                    )
                    
                    self._add_to_list(3, payload)
                    byte_index = end_index
        else:
            payload = BluetoothPayload.create_write_characteristic_payload(
                self.mac_address, 
                self.group_class, 
                service_uuid, 
                characteristic_uuid, 
                bundle
            )
            self._add_to_list(3, payload)
        
        return self

    def build_array(self) -> List['BluetoothPayload']:
        """
        Build and return the array of payloads
        
        Returns:
            List[BluetoothPayload]: List of all added payloads
        """
        return list(self._linked_list)

    def _add_to_list(self, mode: int, bluetooth_payload: 'BluetoothPayload') -> None:
        """
        Add payload to the internal list based on mode
        
        Args:
            mode (int): Addition mode (1=first, 2=second, 3=last)
            bluetooth_payload (BluetoothPayload): Payload to add
        """
        if mode == 1:
            # Add to first position
            self._linked_list.appendleft(bluetooth_payload)
        elif mode == 2:
            # Add to second position (index 1) if list has elements, otherwise add to end
            if len(self._linked_list) <= 0:
                self._linked_list.append(bluetooth_payload)
            else:
                # Convert to list, insert, convert back to deque
                temp_list = list(self._linked_list)
                temp_list.insert(1, bluetooth_payload)
                self._linked_list = deque(temp_list)
        elif mode == 3:
            # Add to last position
            self._linked_list.append(bluetooth_payload)


    def __str__(self) -> str:
        return f"PayloadBuilder(mac_address='{self.mac_address}', group_class={self.group_class}, payload_count={len(self._linked_list)})"

    def __repr__(self) -> str:
        return self.__str__()
