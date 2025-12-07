# Hardware Documentation

This document provides hardware specifications and documentation for the Disobey 2025 Badge.

## Hardware Overview

The Disobey 2025 Badge is built around an ESP32-S3 microcontroller with a custom PCB design featuring:

- ESP32-S3 WROOM W2 module with built-in WiFi and Bluetooth
- Custom display interface
- Button input matrix
- Power management
- Expansion capabilities

## Documentation Files

All hardware documentation files are located in [`docs/hardware/`](docs/hardware/):

### Badge Design Files

- **`disobey_badge2025.step`** - 3D model in STEP format for mechanical design and visualization
- **`disobey2025_badge_schematic_v11.pdf`** - Circuit schematic (v11) for electrical analysis and debugging

### Component Datasheets

- **`esp32-s3-wroom-2_datasheet_en.pdf`** - ESP32-S3 WROOM-2 microcontroller module datasheet
- **`ER-TFT019-1_Datasheet.pdf`** - Display module specifications and interface details
- **`2412101523_OPSCO-Optoelectronics-SK6812MINI-EA_C5378731.pdf`** - SK6812MINI LED datasheet

## Hardware Specifications

### Microcontroller

- **Model**: ESP32-S3 WROOM-2
- **Architecture**: Xtensa dual-core 32-bit LX7
- **Clock Speed**: Up to 240 MHz
- **Flash Memory**: Built-in flash storage
- **RAM**: 512 KB SRAM
- **Connectivity**: WiFi 802.11 b/g/n, Bluetooth 5.0
- **Datasheet**: [`esp32-s3-wroom-2_datasheet_en.pdf`](docs/hardware/esp32-s3-wroom-2_datasheet_en.pdf)

### Display

- **Model**: ER-TFT019-1 (1.9" TFT Display)
- **Interface**: Custom display interface (refer to schematic for connections)
- **Datasheet**: [`ER-TFT019-1_Datasheet.pdf`](docs/hardware/ER-TFT019-1_Datasheet.pdf)
- **Connection details**: Available in development devkit documentation

### LEDs

- **Model**: SK6812MINI-EA (RGB LEDs)
- **Type**: Addressable RGB LEDs
- **Datasheet**: [`2412101523_OPSCO-Optoelectronics-SK6812MINI-EA_C5378731.pdf`](docs/hardware/2412101523_OPSCO-Optoelectronics-SK6812MINI-EA_C5378731.pdf)

### Input/Output

- Button matrix for user input
- GPIO pins for expansion
- Power input and management

## GPIO Pin Mapping

### Display Interface (ST7789 SPI)

| Function    | GPIO Pin | Description                |
| ----------- | -------- | -------------------------- |
| SPI SCK     | GPIO 4   | SPI Clock                  |
| SPI MOSI    | GPIO 5   | SPI Data Out               |
| SPI MISO    | GPIO 16  | SPI Data In (unused)       |
| Display CS  | GPIO 6   | Chip Select (green wire)   |
| Display DC  | GPIO 15  | Data/Command (violet wire) |
| Display RST | GPIO 7   | Reset (blue wire)          |
| Backlight   | GPIO 19  | Display Backlight Control  |

### Button Matrix

| Button | GPIO Pin | Pull Mode | Description     |
| ------ | -------- | --------- | --------------- |
| Up     | GPIO 11  | PULL_UP   | D-pad Up        |
| Down   | GPIO 1   | PULL_UP   | D-pad Down      |
| Left   | GPIO 21  | PULL_UP   | D-pad Left      |
| Right  | GPIO 2   | PULL_UP   | D-pad Right     |
| Stick  | GPIO 14  | PULL_UP   | Joystick button |
| A      | GPIO 13  | PULL_UP   | Action button A |
| B      | GPIO 38  | PULL_UP   | Action button B |
| Start  | GPIO 12  | PULL_UP   | Start button    |
| Select | GPIO 45  | PULL_DOWN | Select button   |

### LED Control

| Function   | GPIO Pin | Description               |
| ---------- | -------- | ------------------------- |
| LED Data   | GPIO 18  | SK6812MINI LED chain data |
| LED Enable | GPIO 17  | LED power control         |

### System Configuration

| Parameter     | Value   | Description                |
| ------------- | ------- | -------------------------- |
| CPU Frequency | 240 MHz | Maximum ESP32-S3 frequency |
| SPI Baudrate  | 80 MHz  | Display SPI speed          |
| LED Count     | 8 LEDs  | Number of SK6812MINI LEDs  |

### Power Requirements

- Operating voltage range (refer to schematic)
- Power consumption specifications
- Battery/USB power options

## Development Hardware (Devkit)

For development and testing, you can build a devkit with:

- ESP32-S3 development board
- Breadboards
- Individual buttons (9 total)
- Compatible display module
- Jumper wires

### Connection Guide

Detailed connection diagrams are available in [DEVELOPMENT.md](DEVELOPMENT.md) and visual guides in [`docs/assets/`](docs/assets/).

## Manufacturing Information

### PCB Specifications

- Refer to schematic for layer stack-up
- Component placement guidelines
- Assembly notes and requirements

### Bill of Materials (BOM)

- Component specifications in schematic
- Recommended suppliers and part numbers
- Alternative component options

## Safety Considerations

- Follow ESD safety protocols when handling the badge
- Use appropriate power supply specifications
- Ensure proper grounding during development
- Follow local regulations for RF emissions (WiFi/Bluetooth)

## Modifications and Customization

### Hardware Modifications

- GPIO pin availability for custom features
- Expansion connector specifications
- Power budget considerations

### Firmware Compatibility

- Ensure hardware modifications are compatible with firmware
- Update device tree/configuration as needed
- Test thoroughly before deployment

## Support and Resources

- **Hardware Issues**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Development Setup**: See [DEVELOPMENT.md](DEVELOPMENT.md)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Hardware Files**: [`docs/hardware/`](docs/hardware/)

## Version History

- **v11**: Current schematic version (`disobey2025_badge_schematic_v11.pdf`)
- Check schematic file for revision history and changes
