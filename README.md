# KUBE Gate System - Home Assistant Integration

A Home Assistant custom integration for controlling KUBE Bluetooth gate systems from [Key Automation](https://keyautomation.com/en). Based on reverse engineering of the [KUBE Android app](https://play.google.com/store/apps/details?id=it.keyautomation.kubeus).

## Features

- **Gate Controls**: Open, close, toggle, and partially open gate operations
- **Light Control**: Control gate lighting system
- **Status Monitoring**: Connection status, gate state, and maintenance information
- **Bluetooth Communication**: Direct Bluetooth Low Energy communication with KUBE devices
- **Authentication Support**: Both passkey and master key authentication methods

## Installation

1. Copy the `custom_components/kube` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Configuration → Integrations
4. Click "Add Integration" and search for "KUBE Gate System"

## Configuration

### Step 1: Device Information
- **MAC Address**: The Bluetooth MAC address of your KUBE device
- **Device Name**: A friendly name for your gate system
- **Authentication Method**: Choose between "Passkey" or "Master Key"

### Step 2: Authentication
- **Passkey Method**: Enter your device passkey
- **Master Key Method**: Enter your master key and optionally a passkey

## Entities

The integration creates the following entities:

### Buttons
- **Open Gate**: Opens the gate completely
- **Close Gate**: Closes the gate
- **Toggle Gate**: Toggles gate state (open/close)
- **Open Slightly**: Opens the gate partially

### Light
- **Gate Lights**: Controls the gate lighting system

### Sensors
- **Connection Status**: Shows Bluetooth connection state
- **Gate State**: Shows current gate position (when available)
- **Maintenance Info**: Shows maintenance-related information

## Requirements

- Home Assistant 2023.1 or later
- Python `bleak` library (automatically installed)
- KUBE gate system with Bluetooth support

## Supported KUBE Operations

The integration supports the following KUBE operations:
- `ONLY_OPEN` (1): Open gate completely
- `ONLY_CLOSE` (4): Close gate
- `OPEN_CLOSE_TOGGLE` (8): Toggle gate state
- `OPEN_SLIGHTLY_OR_CLOSE` (128): Open gate slightly or close
- `LIGHTS` (256): Control gate lights

## Troubleshooting

### Connection Issues
- Ensure your KUBE device is powered on and in range
- Verify the MAC address is correct
- Check that Bluetooth is enabled on your Home Assistant host

### Authentication Errors
- Verify your passkey or master key is correct
- Ensure the device is not already connected to another client

### Entity Unavailable
- Check the connection status sensor
- Restart the integration if needed
- Verify Bluetooth connectivity

## Technical Details

### Architecture
- **Coordinator**: Manages device communication and data updates
- **Config Flow**: Handles device setup and authentication
- **Entities**: Button, light, and sensor entities for device control
- **Library Integration**: Uses the existing KUBE Python library

### Communication
- Uses Bluetooth Low Energy (BLE) for device communication
- Implements KUBE-specific protocol for authentication and commands
- Supports both synchronous and asynchronous operations

### Data Updates
- Polls device status every 30 seconds by default
- Updates entities after command execution
- Maintains connection state monitoring

## Development

### File Structure
```
custom_components/kube/
├── __init__.py          # Integration setup
├── manifest.json        # Integration metadata
├── config_flow.py       # Configuration flow
├── const.py            # Constants
├── coordinator.py      # Data coordinator
├── button.py           # Button entities
├── light.py            # Light entity
├── sensor.py           # Sensor entities
├── strings.json        # UI translations
└── kube_lib/           # KUBE library
    ├── __init__.py
    ├── KubeCommands.py
    ├── KubeBtClient.py
    ├── OperationBuilder.py
    ├── BluetoothPayload.py
    ├── PayloadBuilder.py
    └── KubeDevice.py
```

### Adding New Features
1. Add constants to `const.py`
2. Update the coordinator for new data handling
3. Create or modify entity classes
4. Update configuration flow if needed
5. Add translations to `strings.json`

## License

MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
1. Check the Home Assistant logs for error messages
2. Verify your KUBE device compatibility
3. Ensure proper Bluetooth connectivity

## TODO

1. add tests
2. do total refactor of codebase to remove dead code and improve code quality.
