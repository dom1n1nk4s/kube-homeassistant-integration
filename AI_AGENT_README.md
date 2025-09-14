# KUBE Home Assistant Integration - AI Agent Development Guide

## Overview

This is a Home Assistant custom integration for KUBE Gate System devices that communicate via Bluetooth Low Energy (BLE). This README is specifically written for AI agents who may need to work on this codebase in the future.

## Critical Background: The Async Conversion

### The Original Problem

This integration was originally built with a "frankenstein sync control" architecture that mixed synchronous and asynchronous patterns incorrectly. The main issue was:

```
Error communicating with KUBE device: Caught blocking call to sleep with args (0.01,) inside the event loop by custom integration 'kube' at custom_components/kube/kube_lib/KubeBtClient.py, line 83: time.sleep(0.01)
```

### The Solution: Connect-Per-Command Pattern

The integration was completely refactored to use a **connect-per-command pattern** instead of persistent connections:

1. **Each operation** connects, authenticates, performs the action, and disconnects
2. **No persistent connections** - matches the original Android app behavior
3. **Fully async** - no blocking calls in the event loop
4. **15-second timeout** with retry-once logic for reliability

## Architecture Overview

### Core Components

```
custom_components/kube/
├── __init__.py              # Integration setup (uses BUTTON platform)
├── coordinator.py           # Data update coordinator (async polling)
├── button.py               # Button entities for commands (NEW - replaces switches)
├── sensor.py               # Status sensors
├── light.py                # Light control entities
├── config_flow.py          # Configuration flow
├── const.py                # Constants
└── kube_lib/               # Core Bluetooth library
    ├── KubeBtClient.py     # Async BLE client (HEAVILY MODIFIED)
    ├── KubeCommands.py     # High-level async commands (HEAVILY MODIFIED)
    ├── KubeDevice.py       # Device state management
    ├── OperationBuilder.py # Legacy operation builder (still used)
    └── ...
```

### Key Architectural Decisions

1. **Connect-Per-Command**: Each command connects fresh rather than maintaining persistent connections
2. **Async-First**: All Bluetooth operations use `bleak` library with proper async/await
3. **Button Entities**: Commands are buttons (momentary) not switches (stateful)
4. **Polling Updates**: Status updates via periodic connection attempts

## Critical Files and Their Roles

### 1. `KubeBtClient.py` - The Core BLE Client

**Status**: ✅ FULLY CONVERTED TO ASYNC

**Key Changes Made**:
- Removed all threading infrastructure (`ThreadPoolExecutor`, `_operation_lock`, etc.)
- Converted `DelayedCommandHandler` to use `asyncio.create_task()`
- All methods are now properly async (`connect_bt_gatt_async`, `write_characteristic_async`, etc.)
- Fixed `cleanup()` method to be async and remove threading references

**Important Methods**:
- `connect_bt_gatt_async()` - Connects with timeout and error handling
- `disconnect_bt_gatt_async()` - Clean disconnection
- `write_characteristic_async()` - Send encrypted commands
- `start_notify_async()` - Handle notifications

### 2. `KubeCommands.py` - High-Level Command Interface

**Status**: ✅ FULLY CONVERTED TO ASYNC

**Key Changes Made**:
- Added new async methods: `open_door_async()`, `close_door_async()`, etc.
- Implemented `_connect_and_authenticate_async()` for the connect-per-command pattern
- Added proper encryption key generation and management
- Each command method connects, sends command, and disconnects

**Important Methods**:
- `_connect_and_authenticate_async()` - Full connection and auth flow
- `_send_command_async()` - Send encrypted commands with connect-per-command
- `open_door_async()`, `close_door_async()`, etc. - Individual command methods
- `get_device_status_async()` - Status polling for coordinator

### 3. `coordinator.py` - Data Update Coordinator

**Status**: ✅ CONVERTED TO ASYNC

**Key Changes Made**:
- Removed all `loop.run_in_executor()` calls
- Uses new async methods from `KubeCommands`
- Proper error handling for connect-per-command pattern
- Better logging and state management

### 4. `button.py` - Button Platform (NEW FILE)

**Status**: ✅ CREATED

**Purpose**: Replaces switch entities with proper button entities for momentary commands.

**Key Features**:
- Uses `ButtonEntity` from Home Assistant
- Proper `async_press()` method
- Availability logic adapted for connect-per-command pattern

## Bluetooth Protocol Details

### Device Communication Flow

1. **Connect** to device via BLE
2. **Discover services** automatically
3. **Read serial number** from characteristic `f1170003`
4. **Enable notifications** on characteristic `f1110021`
5. **Read nonce** from characteristic `f1170002`
6. **Generate encryption keys**:
   - `enckey1` = AES(passkey, serial_number)
   - `enckey2` = nonce XOR enckey1
   - `token` = enckey1 XOR enckey2
7. **Authenticate** by writing token to characteristic `f1170005`
8. **Send commands** encrypted with `enckey2` to characteristic `f1110022`
9. **Disconnect** when done

### Command Format

Commands are JSON strings encrypted with XOR using `enckey2`:

```
@0028cact={"cmd":"C30B","val":1}#  // Open door
@0028cact={"cmd":"C30B","val":4}#  // Close door
@0028cact={"cmd":"C30B","val":8}#  // Toggle door
```

## Common Issues and Solutions

### 1. "Blocking call to sleep" Error

**Cause**: Using `time.sleep()` or other blocking calls in async context
**Solution**: Use `await asyncio.sleep()` instead

### 2. Entities Show as "Unavailable"

**Cause**: Availability logic checking for persistent connection
**Solution**: For connect-per-command pattern, entities should be available if coordinator has data

### 3. Authentication Failure (sec_state = 0)

**Cause**: Incorrect key generation algorithm or token writing method
**Solutions**: 
1. Use `write_bt_gatt_characteristic_with_encryption()` for token characteristic (`f1170005`) instead of direct `write_characteristic_async()`
2. Verify key generation algorithm matches expected values from test data

**Test Data for Debugging**:
```
SN: 0000CF243BE079F2
Passkey: 0000000000086828
Nonce: D9 D6 88 4D 3C FC 8D E2 6E 89 E3 87 2B 8C 37 56
Expected Enckey1: EB EE CD 75 0E CD C9 DA 5B BB A5 B5 1F CF 76 56
Expected Enckey2: 24 44 21 4D 74 F2 3F B7 63 3D 14 B8 3F 7B 54 0F
Expected Token: 16 7C 64 75 46 C3 7B 8F 56 0F 52 8A 0B 38 15 0F
```

**Debugging**: The `_process_nonce_and_generate_keys()` method now includes comprehensive debugging that tests both XOR and AES approaches for Enckey2 generation and compares against expected values.

### 4. Commands Not Working

**Check**:
1. Bluetooth proxy is working (ESP32 logs)
2. Device MAC address is correct
3. Passkey is correct (16 characters, zero-padded)
4. Encryption keys are being generated properly
5. Authentication is successful (sec_state = 1)

### 5. Connection Timeouts

**Current Settings**:
- 15-second connection timeout
- Retry once on failure
- These can be adjusted in `_connect_and_authenticate_async()`

## Development Guidelines for AI Agents

### 1. Async Best Practices

- **Always use `await`** for async operations
- **Never use blocking calls** like `time.sleep()` in async context
- **Use `asyncio.create_task()`** for fire-and-forget operations
- **Proper exception handling** with try/catch blocks

### 2. Connect-Per-Command Pattern

- **Don't maintain persistent connections** - they're unreliable for BLE
- **Each operation should be self-contained**: connect → authenticate → command → disconnect
- **Handle connection failures gracefully** - they're expected

### 3. Home Assistant Integration

- **Use proper entity types**: Buttons for commands, Sensors for status
- **Implement proper availability logic** for connect-per-command pattern
- **Use coordinator pattern** for data updates
- **Follow HA naming conventions** and best practices

### 4. Debugging Tips

- **Enable debug logging** in Home Assistant configuration:
  ```yaml
  logger:
    logs:
      custom_components.kube: debug
  ```
- **Check ESP32 Bluetooth proxy logs** for connection issues
- **Monitor device parameters** in sensor attributes for debugging
- **Use Home Assistant Developer Tools** to test commands

## Testing Checklist

When making changes, verify:

- [ ] Integration loads without errors
- [ ] Entities appear as buttons (not switches)
- [ ] Buttons are available (not grayed out)
- [ ] Commands execute successfully
- [ ] Status sensors update properly
- [ ] No "blocking call" errors in logs
- [ ] Bluetooth proxy shows successful connections
- [ ] Device responds to commands

## File Modification History

### Major Changes Made:

1. **KubeBtClient.py**: Complete async conversion, removed threading
2. **KubeCommands.py**: Added async methods, connect-per-command pattern
3. **coordinator.py**: Removed executor calls, uses async methods
4. **button.py**: Created new file to replace switches
5. **__init__.py**: Changed from SWITCH to BUTTON platform
6. **sensor.py**: Updated availability logic

## Future Improvements

Potential areas for enhancement:

1. **Better error recovery** - more sophisticated retry logic
2. **Status parsing** - interpret device responses for gate state
3. **Configuration options** - timeout settings, retry counts
4. **Performance optimization** - connection pooling (if reliable)
5. **Additional commands** - more device features

## Dependencies

- **bleak**: Bluetooth Low Energy library for Python
- **cryptography**: For AES encryption
- **Home Assistant**: 2023.x or later (for button platform)



---

**Note for AI Agents**: This integration has been fully converted from a problematic sync/async hybrid to a proper async architecture. The connect-per-command pattern is intentional and should not be changed back to persistent connections. Always test changes thoroughly as Bluetooth integrations can be fragile.
