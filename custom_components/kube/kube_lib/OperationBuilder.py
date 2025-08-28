from enum import IntEnum
from typing import List
from .BluetoothPayload import BluetoothPayload
from .KubeDevice import KubeDevice
from .PayloadBuilder import PayloadBuilder
from .KubeBtClient import KubeBtClient


class C30BOperation(IntEnum):
    """Enum for C30B operation values"""
    ONLY_OPEN = 1
    UNKNOWN_2 = 2
    ONLY_CLOSE = 4
    OPEN_CLOSE_TOGGLE = 8
    OPEN_SLIGHTLY_OR_CLOSE = 128
    LIGHTS = 256
    UNKNOWN_131072 = 131072


class OperationBuilder:
    current_group_identifier = 0
    def __init__(self, kube_bt_client=None):
        self.kube_bt_client = kube_bt_client or KubeBtClient()
    
    def get_device_connection_state(self, address):
        """Get connection state for device"""
        if address is None:
            return 0
        return self.kube_bt_client.get_device_connection_state(address)

    @classmethod
    def increment_group_identifier(cls):
        i4 = cls.current_group_identifier
        cls.current_group_identifier += 1
        return i4
    
    def get_info_command_maybe(self, mac, pass_key, end_connection):
        # Store passkey - assuming GetKubeDevice returns an object with store_string_value method
        # Convert passkey to string and pad with zeros to 16 characters
        passkey_str = str(pass_key).zfill(16)
        self.get_kube_device(mac).store_string_value("passkey", passkey_str)
        
        bluetooth_payload_arr_connect_and_discover = self.connect_and_discover_operation(mac, 61)
        bluetooth_payload_arr_subscribe_to_notifications = self.subscribe_to_notifications_operation(mac, 61)
        bluetooth_payload_arr_write_kbinf = self.request_kbinf(mac, 61)
        bluetooth_payload_arr_write_cinf = self.request_cinf(mac, 61)
        bluetooth_payload_arr_write_cgrp_and_cdat = self.request_cgrp_and_cdat(mac, 61)
        bluetooth_payload_arr_write_ccfg1_and_ccfg2 = self.request_ccfg1_and_ccfg2(mac, 61)
        
        if not end_connection:  # IF KEEP CONNECTION
            return self.assign_group_id_and_process_array(
                self.merge_payload_arrays(
                    bluetooth_payload_arr_connect_and_discover,
                    bluetooth_payload_arr_subscribe_to_notifications,
                    bluetooth_payload_arr_write_kbinf,
                    bluetooth_payload_arr_write_cinf,
                    bluetooth_payload_arr_write_cgrp_and_cdat,
                    bluetooth_payload_arr_write_ccfg1_and_ccfg2
                )
            )
        
        self.write_empty_characteristic_value(mac, 38) # this wont be processed as it does not have a processPayload call
        return self.assign_group_id_and_process_array(
            self.merge_payload_arrays(
                bluetooth_payload_arr_connect_and_discover,
                bluetooth_payload_arr_subscribe_to_notifications,
                # bluetooth_payload_arr_write_kbinf,
                # bluetooth_payload_arr_write_cinf,
                bluetooth_payload_arr_write_cgrp_and_cdat,
                bluetooth_payload_arr_write_ccfg1_and_ccfg2,
                self.disconnect_operation(mac, 38)
            )
        )
    
    def connect_and_discover_operation(self, mac, group_class):
        if group_class == 38:
            group_class = 17
        
        payload_builder = PayloadBuilder(group_class, mac)
        payload_builder.add_connect_payload(30000, False)  # Use 30s timeout for paired devices
        payload_builder.add_sleep_payload(300)
        payload_builder.add_discovery_payload()
        payload_builder.add_sleep_payload(150)
        return payload_builder.build_array()
    
    def subscribe_to_notifications_operation(self, address, group_class): #subscribes and authenticates with server
        if group_class == 38:
            group_class = 23
        
        payload_builder = PayloadBuilder(group_class, address)
        payload_builder.add_read_characteristic_payload( # reads sn 
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170003-0190-4567-8fab-4d4158a4eeaf"
        )
        payload_builder.add_set_indicator_payload( # subs to notifications, primary source of data
            "f1110020-0190-4567-8fab-4d4158a4eeaf",
            "f1110021-0190-4567-8fab-4d4158a4eeaf",
            True
        )
        payload_builder.add_read_characteristic_payload( # reads nonce, saves enckey1, enckey2, token
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170002-0190-4567-8fab-4d4158a4eeaf"
        )
        payload_builder.add_write_characteristic_payload( #auth - writes token, handled deeper in KubeBtClient
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170005-0190-4567-8fab-4d4158a4eeaf",
            {}  # Empty bundle
        )
        payload_builder.add_read_characteristic_payload( # get secstate result
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170006-0190-4567-8fab-4d4158a4eeaf"
        )
        return payload_builder.build_array()
    
    def request_kbinf(self, mac, group_class):
        if group_class == 38:
            group_class = 32
        
        payload_builder = PayloadBuilder(group_class, mac)
        cmd = "@FFFFcmd#".replace("cmd", "kbinf")
        cmd_length = len(cmd) - 2 - 4
        cmd = cmd.replace("FFFF", f"{cmd_length:04X}", 1)
        
        bundle = {
            "cmd": cmd,
            "cmdType": "kbinf"
        }
        payload_builder.add_write_characteristic_payload(
            "f1110020-0190-4567-8fab-4d4158a4eeaf",
            "f1110022-0190-4567-8fab-4d4158a4eeaf",
            bundle
        )
        return payload_builder.build_array()
    
    def request_cinf(self, mac, group_class):
        if group_class == 38:
            group_class = 20
        
        payload_builder = PayloadBuilder(group_class, mac)
        cmd = "@FFFFcmd#".replace("cmd", "cinf")
        cmd_length = len(cmd) - 2 - 4
        cmd = cmd.replace("FFFF", f"{cmd_length:04X}", 1)
        
        bundle = {
            "cmd": cmd,
            "cmdType": "cinf"
        }
        payload_builder.add_write_characteristic_payload(
            "f1110020-0190-4567-8fab-4d4158a4eeaf",
            "f1110022-0190-4567-8fab-4d4158a4eeaf",
            bundle
        )
        return payload_builder.build_array()
    
    def request_cgrp_and_cdat(self, mac, group_class):
        if group_class == 38:
            group_class = 15
        
        payload_builder = PayloadBuilder(group_class, mac)
        
        # CGRP command
        cmd1 = "@FFFFcmd#".replace("cmd", "cgrp")
        cmd1_length = len(cmd1) - 2 - 4
        cmd1 = cmd1.replace("FFFF", f"{cmd1_length:04X}", 1)
        
        bundle1 = {
            "cmd": cmd1,
            "cmdType": "cgrp"
        }
        payload_builder.add_write_characteristic_payload(
            "f1110020-0190-4567-8fab-4d4158a4eeaf",
            "f1110022-0190-4567-8fab-4d4158a4eeaf",
            bundle1
        )
        
        # CDAT command
        cmd2 = "@FFFFcmd#".replace("cmd", "cdat")
        cmd2_length = len(cmd2) - 2 - 4
        cmd2 = cmd2.replace("FFFF", f"{cmd2_length:04X}", 1)
        
        bundle2 = {
            "cmd": cmd2,
            "cmdType": "cdat"
        }
        payload_builder.add_write_characteristic_payload(
            "f1110020-0190-4567-8fab-4d4158a4eeaf",
            "f1110022-0190-4567-8fab-4d4158a4eeaf",
            bundle2
        )
        
        return payload_builder.build_array()
    
    def write_C30B_with_param(self, mac: str, group_class: int, val: C30BOperation):
        """
        Write C30B command with operation parameter
        
        Args:
            mac: Device MAC address
            group_class: Group class identifier
            val: Operation to perform (C30BOperation enum)
        """
        if group_class == 38:
            group_class = 15
        
        payload_builder = PayloadBuilder(group_class, mac)
        
        cmd1 = "@FFFFcmd#".replace("cmd", "cact={\"cmd\":\"C30B\",\"val\":" + str(val) + "}")
        cmd1_length = len(cmd1) - 2 - 4
        cmd1 = cmd1.replace("FFFF", f"{cmd1_length:04X}", 1)
        
        bundle1 = {
            "cmd": cmd1,
            "cmdType": "cact"
        }
        payload_builder.add_write_characteristic_payload(
            "f1110020-0190-4567-8fab-4d4158a4eeaf",
            "f1110022-0190-4567-8fab-4d4158a4eeaf",
            bundle1
        )
        
        return payload_builder.build_array()
    
    def request_ccfg1_and_ccfg2(self, mac, group_class):
        if group_class == 38:
            group_class = 18
        
        payload_builder = PayloadBuilder(group_class, mac)
        
        # CCFG1 command
        cmd1 = "@FFFFcmd#".replace("cmd", "ccfg1")
        cmd1_length = len(cmd1) - 2 - 4
        cmd1 = cmd1.replace("FFFF", f"{cmd1_length:04X}", 1)
        
        bundle1 = {
            "cmd": cmd1,
            "cmdType": "ccfg1"
        }
        payload_builder.add_write_characteristic_payload(
            "f1110020-0190-4567-8fab-4d4158a4eeaf",
            "f1110022-0190-4567-8fab-4d4158a4eeaf",
            bundle1
        )
        
        # CCFG2 command
        cmd2 = "@FFFFcmd#".replace("cmd", "ccfg2")
        cmd2_length = len(cmd2) - 2 - 4
        cmd2 = cmd2.replace("FFFF", f"{cmd2_length:04X}", 1)
        
        bundle2 = {
            "cmd": cmd2,
            "cmdType": "ccfg2"
        }
        payload_builder.add_write_characteristic_payload(
            "f1110020-0190-4567-8fab-4d4158a4eeaf",
            "f1110022-0190-4567-8fab-4d4158a4eeaf",
            bundle2
        )
        
        return payload_builder.build_array()
    
    @staticmethod
    def merge_payload_arrays(*bluetooth_payload_arrays):        
        # Create merged array
        merged_array = []
        for arr in bluetooth_payload_arrays:
            merged_array.extend(arr)
        
        return merged_array
    
    def assign_group_id_and_process_array(self, bluetooth_payload_arr: List[BluetoothPayload]):
        """Assign group ID and process payload array using KubeBtClient"""
        new_group_identifier = self.increment_group_identifier()
        index = 0
        
        while index < len(bluetooth_payload_arr):
            bluetooth_payload_arr[index].set_group_identifier(new_group_identifier)
            bluetooth_payload = bluetooth_payload_arr[index]
            
            is_last = index == len(bluetooth_payload_arr) - 1
            
            self.kube_bt_client.add_payload_and_try_process(3, bluetooth_payload, is_last)
            index += 1
        
        return new_group_identifier
    
    
    def get_kube_device(self, address) -> KubeDevice:
        """Get KubeDevice using KubeBtClient's device management"""
        return self.kube_bt_client.get_kube_device(address)

    def write_empty_characteristic_value(self, mac, group_class):
        if group_class == 38:
            group_class = 55
        
        payload_builder = PayloadBuilder(group_class, mac)
        bundle = {
            "characteristicValue": bytes([18])
        }
        payload_builder.add_write_characteristic_payload(
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170008-0190-4567-8fab-4d4158a4eeaf",
            bundle
        )
        payload_builder.add_sleep_payload(600)
        return payload_builder.build_array()

    def disconnect_operation(self, mac, group_class):
        if group_class == 38:
            group_class = 14
        
        payload_builder = PayloadBuilder(group_class, mac)
        payload_builder.add_disconnect_payload()
        return payload_builder.build_array()
    
    def button_command(self, mac, passkey, val):
        """Authenticate command that combines multiple operations"""
        passkey_str = str(passkey).zfill(16)
        self.get_kube_device(mac).store_string_value("passkey", passkey_str)
        return self.assign_group_id_and_process_array(
            self.merge_payload_arrays(
                self.connect_and_discover_operation(mac, 54),
                self.subscribe_to_notifications_operation(mac, 54),
                self.write_C30B_with_param(mac, 54, val),
                self.request_kbinf(mac, 54),
                self.request_cinf(mac, 54),
                self.request_cgrp_and_cdat(mac, 54),
                self.request_ccfg1_and_ccfg2(mac, 54)
            )
        )
    
    def set_new_passkey_command(self, mac, masterkey, passkey):
        """Authenticate command that combines multiple operations"""
        passkey_str = str(passkey).zfill(16)
        self.get_kube_device(mac).store_string_value("passkey", passkey_str)
        return self.assign_group_id_and_process_array(
            self.merge_payload_arrays(
                self.connect_and_discover_operation(mac, 56),
                self.write_master_and_pass_keys(mac, masterkey, passkey, 56),
                PayloadBuilder(56, mac).add_read_characteristic_payload(# read passkeyset state
                    "f1170001-0190-4567-8fab-4d4158a4eeaf",
                    "f1170004-0190-4567-8fab-4d4158a4eeaf"
                ).build_array()
            )
        )
    
    def write_master_and_pass_keys(self, mac, master_key, pass_key, group_class):
        """Write master key and pass key operations"""
        if group_class == 38:
            group_class = 27
        
        payload_builder = PayloadBuilder(group_class, mac)
        
        # Read serial number
        payload_builder.add_read_characteristic_payload(
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170003-0190-4567-8fab-4d4158a4eeaf"
        )
        
        # Read master set status
        payload_builder.add_read_characteristic_payload(
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170007-0190-4567-8fab-4d4158a4eeaf"
        )
        
        # Write master key
        bundle = {
            "masterkey": master_key
        }
        payload_builder.add_write_characteristic_payload(
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170007-0190-4567-8fab-4d4158a4eeaf",
            bundle
        )
        
        # Read passkey set status
        payload_builder.add_read_characteristic_payload(
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170004-0190-4567-8fab-4d4158a4eeaf"
        )
        
        # Generate or format passkey
        if pass_key is None or pass_key == "":
            # Generate random 5-digit passkey and pad to 16 characters with zeros
            import random
            random_passkey = str(random.randint(10000, 99999))
            formatted_passkey = random_passkey.rjust(16, '0')
        else:
            # Format provided passkey to 16 characters, padding with zeros
            formatted_passkey = str(pass_key).rjust(16, '0')
        
        # Write passkey
        bundle2 = {
            "passkey": formatted_passkey
        }
        payload_builder.add_write_characteristic_payload(
            "f1170001-0190-4567-8fab-4d4158a4eeaf",
            "f1170004-0190-4567-8fab-4d4158a4eeaf",
            bundle2
        )
        
        return payload_builder.build_array()
