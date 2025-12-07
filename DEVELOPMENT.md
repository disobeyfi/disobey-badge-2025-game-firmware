# Development Guide

This document provides detailed information for developers working on the Badge Firmware project.

## Dev Container Setup

### Default Containers

This project provides default dev container configurations for both Linux and macOS:

- **Linux**: `.devcontainer/linux/devcontainer.json` - Includes USB device mappings for `/dev/ttyUSB0` and `/dev/ttyUSB1`
- **macOS**: `.devcontainer/macos/devcontainer.json` - No USB device mappings (see limitations below)

### Custom Configuration

If you need to customize your dev container configuration (different USB devices, additional settings, etc.), you can create a local configuration:

1. Copy the appropriate default configuration to `.devcontainer/local/devcontainer.json`
2. Modify it to meet your needs
3. VS Code will automatically use the `local` configuration if it exists

**Note**: The `.devcontainer/local/` directory is gitignored, so your custom configuration won't be committed.

### macOS USB Device Limitations

⚠️ **Important for macOS users**: USB devices cannot be mounted into Docker containers on macOS due to Docker Desktop limitations.

This means:

- **mpremote commands** must be run on the **host machine** (not inside the container)
- **Firmware deployment** (flashing) must be done from the **host machine**
- All other development work (building firmware, editing code) is done inside the container

**Required Python packages on macOS host:**

Before using mpremote on your host machine, install the required dependencies. We recommend using **uv** for the best experience:

**Using uv (recommended):**

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies from pyproject.toml (creates .venv and installs packages)
uv sync
```

This creates a `.venv` directory with all required packages (pyserial, esptool, black). The Makefile will automatically detect and use this virtual environment.

**Alternative: Using pip with --user flag:**

```bash
# On your macOS host (NOT inside the container)
pip3 install --user pyserial esptool
```

After setup, use the `make repl_with_firmware_dir` command on your host machine to connect to the badge.

## Firmware Versions

There are currently two versions of firmware:

- **Normal**: Contains the game
- **Minimal**: Contains badge test screen and ability to do OTA updates. This is meant to be flashed for new badges for testing and getting flashed with actual firmware via OTA.

## Repository Structure

### Key Directories

- **`/.devcontainer/docker-compose.override.yml`**: Host-specific Docker Compose overrides (gitignored). Copy from `.macos-example` or `.linux-example` in same directory if needed
- **`/set_environment.sh`**: Environment file that is created when running make, modify to meet your needs
- **`/firmware`**: Firmware development directory. Supposed to be used with mpremote mount or just rsync files into target board
- **`/frozen_firmware`**: These parts of the firmware are built into MicroPython itself. This is where modules that are ready will end up
- **`/libs/`**: MicroPython related submodules. These modules are partly used by linking relevant files or modules into `firmware` or `frozen_firmware` folders
- **`/micropython/`**: MicroPython firmware build environment. This will include all the needed parts like IDF, actual Express IDF build environment.

## Python Firmware Development

### Connecting with the Board and Starting the UI

After connecting to the badge with REPL and mounting the firmware directory, you need to start the badge UI by importing the main module.

#### Linux (Inside Container)

On Linux, USB devices are available inside the container. To start a REPL session with the firmware directory:

```bash
# Inside the dev container
make repl_with_firmware_dir
```

Or manually:

```bash
cd firmware
python ../micropython/tools/mpremote/mpremote.py baud 460800 u0 mount -l .
```

#### macOS (On Host Machine)

⚠️ **Important**: On macOS, USB devices cannot be mounted into Docker containers. You must run mpremote commands on your **host machine** (outside the container).

```bash
# On your macOS host (NOT inside the container)
make repl_with_firmware_dir
```

Or manually:

```bash
cd firmware
python ../micropython/tools/mpremote/mpremote.py baud 460800 connect /dev/tty.usbserial-XXX mount -l .
```

**Note**: Replace `/dev/tty.usbserial-XXX` with your actual device. Find it with: `ls /dev/tty.usbserial-*`

### Starting the Badge UI

Once connected to REPL with the firmware directory mounted, **you must import the main module to start the badge UI**:

```python
import badge.main
```

This initializes the display, buttons, and starts the main badge interface. The badge will then be fully interactive and ready for testing your changes.

**Important**: Every time you connect to REPL with mounted firmware, you need to run `import badge.main` to see the UI.

### Multiple Devices Connected

When you have more than one device connected, you might want to specify the device where you connect or deploy firmware. Here are a few examples:

```bash
# Mount folder to specific port (Linux inside container)
python micropython/tools/mpremote/mpremote.py baud 460800 connect /dev/ttyUSB1 mount -l firmware

# Mount folder to specific port (macOS on host)
python micropython/tools/mpremote/mpremote.py baud 460800 connect /dev/tty.usbserial-XXX mount -l firmware

# Deploy firmware to specific port
make PORT=/dev/ttyUSB1 deploy  # Linux
make PORT=/dev/tty.usbserial-XXX deploy  # macOS (on host)
```

## ⚠️ Critical: Import Dependencies

**IMPORT ORDER MATTERS!** Due to circular dependencies in the GUI system, you must follow a specific import pattern:

### The Problem

- `gui.core.colors` imports `hardware_setup`
- `hardware_setup` calls `init_display()` which imports from `gui.core.ugui`
- `gui.core.ugui` imports from `gui.core.colors`

### The Solution

**Always import `hardware_setup` FIRST** in any new module that uses GUI components:

```python
# CORRECT ORDER:
import hardware_setup as hardware_setup
from hardware_setup import BtnConfig, LED_PIN, LED_AMOUNT, LED_ACTIVATE_PIN
# Then other imports...
from gui.core.colors import *
from gui.core.ugui import Screen, ssd, quiet
```

### Error Symptom

If you get `NameError: name 'color_map' isn't defined` in `gui/core/ugui.py`, you've hit this circular dependency issue.

### Testing Import Success

Always test that your imports work:

```bash
cd firmware
mpremote mount -l .
# In REPL:
import badge.main  # Should work without errors
```

## Testing

We have a few test scripts in the `firmware/tests` folder.

### Screen Test

```bash
cd firmware
mpremote mount -l .
```

In REPL:

```python
from tests import test_image
```

If you get an error, try loading again.

### Button Tests

To test buttons (at least arrows and A button), open REPL:

```bash
cd firmware
mpremote mount -l .
```

And in REPL:

```python
import tests.badge_gui
```

## Memory Management for ESP32

### RAM Constraints

- **Total SRAM**: 512KB on ESP32-S3
- **MicroPython overhead**: ~200KB
- **Available for user code**: ~300KB
- **Monitor usage**: Use `gc.mem_free()` regularly

### Best Practices

#### Memory-Efficient Coding

```python
# Use const() for configuration values
from micropython import const
BUTTON_DEBOUNCE_MS = const(50)

# Prefer generators over lists for large datasets
def get_game_data():
    for i in range(1000):
        yield process_item(i)  # Instead of building a list

# Use __slots__ in classes to reduce memory
class GameState:
    __slots__ = ('score', 'level', 'lives')
    def __init__(self):
        self.score = 0
        self.level = 1
        self.lives = 3
```

#### Memory Monitoring

```python
import gc

# Check available memory
print(f"Free memory: {gc.mem_free()} bytes")

# Force garbage collection before memory-intensive operations
gc.collect()
start_memory = gc.mem_free()
# ... your code ...
end_memory = gc.mem_free()
print(f"Memory used: {start_memory - end_memory} bytes")
```

#### Common Memory Issues

- **Circular references**: Break them explicitly with `del`
- **Large strings**: Use `bytearray` for mutable data
- **Import bloat**: Only import what you need
- **Display buffers**: The framebuffer uses significant RAM

## Understanding the Build Process

### MicroPython Compilation Pipeline

1. **mpy-cross**: Compiles Python files to bytecode (.mpy files)
2. **Frozen Modules**: Compiled into firmware ROM (faster access, less RAM usage)
3. **Runtime Modules**: Loaded from filesystem (slower, uses more RAM, easier to modify)

### Development Workflow

#### Runtime Modules (`/firmware`) - Development Only

- **Use for**: Active development, debugging, testing new features
- **Benefits**: Instant updates via mpremote, easy iteration, no firmware rebuild needed
- **⚠️ Important**: Files in `/firmware` are **NOT included in the built firmware**
- **Before Pull Requests**: All working code **MUST** be moved to `/frozen_firmware`

#### Frozen Modules (`/frozen_firmware`) - Production Code

- **Use for**: Stable, tested code ready for production
- **Benefits**: Faster import, less RAM usage, included in firmware build
- **Drawbacks**: Requires firmware rebuild to change
- **Required for**: All code in pull requests

### Build Targets

- **Normal firmware**: Full game functionality for production badges
- **Minimal firmware**: Test screen + OTA capability for initial badge testing

### Development Best Practice

1. Develop and test new features in `/firmware` using mpremote mount
2. Once stable and tested, move code to `/frozen_firmware`
3. Test that the moved code works in frozen firmware build
4. Submit pull request with code in `/frozen_firmware` only

## Hardware Development (Devkit)

### Devkit Components

Devkit parts for two "badges", each badge has:

- One breadboard
- 9 buttons
- Display
- ESP32

### Connections

Connect display and buttons following this diagram:

![Devkit Display and Buttons Connections](docs/assets/devkit-display-buttons-connections.png)

Connect the other side of the buttons to ground.

An example of connections without buttons (and 1 missing wire for display):

![Example without buttons](docs/assets/example_without_buttons.png)

### Hardware Documentation

For detailed hardware specifications, 3D models, and schematics, see [HARDWARE.md](HARDWARE.md).

## Automatic Flashing Scripts

There are two scripts available for automated flashing:

### `automatic_deploy.sh`

Watches a given serial port (ARG2) and when it detects a new badge, it automatically flashes the given firmware (ARG1).

### `tmux_flashing_session.sh`

Uses tmux to create a session and splits for all connected serial ports. Run as:

```bash
./tmux_flashing_session.sh dist/firmware_minimal.bin "/dev/ttyUSB*" # on Linux and macOS
```

**Note**: Connect first badges to all cables you are going to use in the flashing session before running the script.

## Build Environment

This project is a submodule monster that aims to help develop firmware which is a MicroPython project. It needs custom `micropython.bin` that supports WROOM W2 and EC Cryptography.

After running the setup commands (see [CONTRIBUTING.md](CONTRIBUTING.md)), you will be in the build environment with all needed variables to make individual parts of the build process.

For additional help, check [README.disobey.md](micropython/README.disobey.md).

## Development Workflow

1. Set up your development environment (see [CONTRIBUTING.md](CONTRIBUTING.md))
2. Make changes in the appropriate directory (`firmware/` for development, `frozen_firmware/` for production-ready modules)
3. Test your changes using the testing procedures above
4. Build and flash the firmware to test on hardware
5. Submit a pull request following the guidelines in [CONTRIBUTING.md](CONTRIBUTING.md)

## Tips for Development

- Use `mpremote mount` for rapid development iterations
- Test on actual hardware when possible
- Use the minimal firmware for initial badge testing
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
