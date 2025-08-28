class BluetoothPayload:
    def __init__(self, address, group_class, command_type, payload_param_bundle):
        """
        Private constructor for BluetoothPayload
        
        Args:
            address (str): Bluetooth device address
            group_class (int): Group class identifier
            command_type (int): Command type identifier
            payload_param_bundle (dict): Parameter bundle as dictionary
        """
        self.address = address
        self.group_class = group_class
        self.command_type = command_type
        self.payload_param_bundle = payload_param_bundle
        self.group_identifier = 0
        self._able_to_be_processed = True

    @staticmethod
    def create_connect_payload(address, group_class, timeout, use_background_connection):
        """
        Create a connect payload
        
        Args:
            address (str): Bluetooth device address
            group_class (int): Group class identifier
            timeout (int): Connection timeout in milliseconds
            use_background_connection (bool): Whether to use background connection
            
        Returns:
            BluetoothPayload: Connect payload instance
        """
        bundle = {
            "connectionTimeout": timeout,
            "useBackgroundConnection": use_background_connection
        }
        return BluetoothPayload(address, group_class, 1, bundle)

    @staticmethod
    def create_disconnect_payload(address, group_class):
        """
        Create a disconnect payload
        
        Args:
            address (str): Bluetooth device address
            group_class (int): Group class identifier
            
        Returns:
            BluetoothPayload: Disconnect payload instance
        """
        return BluetoothPayload(address, group_class, 3, {})

    @staticmethod
    def create_discover_payload(address, group_class):
        """
        Create a discover payload
        
        Args:
            address (str): Bluetooth device address
            group_class (int): Group class identifier
            
        Returns:
            BluetoothPayload: Discover payload instance
        """
        return BluetoothPayload(address, group_class, 2, {})

    @staticmethod
    def create_read_characteristic_payload(address, group_class, service_uuid, characteristic_uuid):
        """
        Create a read characteristic payload
        
        Args:
            address (str): Bluetooth device address
            group_class (int): Group class identifier
            service_uuid (str): Service UUID
            characteristic_uuid (str): Characteristic UUID
            
        Returns:
            BluetoothPayload: Read characteristic payload instance
        """
        bundle = {
            "serviceUUID": service_uuid,
            "characteristiUUID": characteristic_uuid
        }
        return BluetoothPayload(address, group_class, 11, bundle)

    @staticmethod
    def create_set_indicator_payload(address, group_class, service_uuid, characteristic_uuid, enable):
        """
        Create a set indicator payload
        
        Args:
            address (str): Bluetooth device address
            group_class (int): Group class identifier
            service_uuid (str): Service UUID
            characteristic_uuid (str): Characteristic UUID
            enable (bool): Whether to enable the indicator
            
        Returns:
            BluetoothPayload: Set indicator payload instance
        """
        bundle = {
            "enable": enable,
            "serviceUUID": service_uuid,
            "characteristiUUID": characteristic_uuid
        }
        return BluetoothPayload(address, group_class, 13, bundle)

    @staticmethod
    def create_sleep_payload(address, group_class, sleep_duration):
        """
        Create a sleep payload
        
        Args:
            address (str): Bluetooth device address
            group_class (int): Group class identifier
            sleep_duration (int): Sleep duration in milliseconds
            
        Returns:
            BluetoothPayload: Sleep payload instance
        """
        bundle = {
            "sleep": sleep_duration
        }
        return BluetoothPayload(address, group_class, 41, bundle)

    @staticmethod
    def create_write_characteristic_payload(address, group_class, service_uuid, characteristic_uuid, bundle):
        """
        Create a write characteristic payload
        
        Args:
            address (str): Bluetooth device address
            group_class (int): Group class identifier
            service_uuid (str): Service UUID
            characteristic_uuid (str): Characteristic UUID
            bundle (dict): Existing parameter bundle
            
        Returns:
            BluetoothPayload: Write characteristic payload instance
        """
        bundle["serviceUUID"] = service_uuid
        bundle["characteristiUUID"] = characteristic_uuid
        return BluetoothPayload(address, group_class, 12, bundle)

    @staticmethod
    def create_write_descriptor_payload(address, group_class, service_uuid, characteristic_uuid, desc_uuid, bundle):
        """
        Create a write descriptor payload
        
        Args:
            address (str): Bluetooth device address
            group_class (int): Group class identifier
            service_uuid (str): Service UUID
            characteristic_uuid (str): Characteristic UUID
            desc_uuid (str): Descriptor UUID
            bundle (dict): Existing parameter bundle
            
        Returns:
            BluetoothPayload: Write descriptor payload instance
        """
        bundle["serviceUUID"] = service_uuid
        bundle["characteristiUUID"] = characteristic_uuid
        bundle["descUUID"] = desc_uuid
        return BluetoothPayload(address, group_class, 32, bundle)

    # Getter and setter methods

    @property
    def get_group_class(self):
        return self.group_class

    @property
    def get_payload_param_bundle(self):
        return self.payload_param_bundle

    @property
    def get_group_identifier(self):
        return self.group_identifier

    def set_group_identifier(self, value):
        self.group_identifier = value
    
    def get_service_uuid(self):
        """Get service UUID from payload parameters"""
        return self.payload_param_bundle.get("serviceUUID")
    
    def get_characteristic_uuid(self):
        """Get characteristic UUID from payload parameters"""
        return self.payload_param_bundle.get("characteristiUUID")
    
    def get_desc_uuid(self):
        """Get descriptor UUID from payload parameters"""
        return self.payload_param_bundle.get("descUUID")
    
    def able_to_be_processed(self):
        """Check if payload is able to be processed"""
        return self._able_to_be_processed
    
    def set_able_to_be_processed(self, value):
        """Set whether payload is able to be processed"""
        self._able_to_be_processed = value  

    def __repr__(self):
        return self.__str__()
