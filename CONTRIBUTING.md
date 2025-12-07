# Contributing to Badge Firmware

Thank you for your interest in contributing to the Badge Firmware project! This document provides guidelines and instructions for contributors.

## Development Setup

### Required Tools

- **Docker Desktop** installed and running
- **VS Code** with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

### Initial Setup

1. Clone the repository with submodules:

   ```bash
   git clone --recursive https://github.com/disobeyfi/badgefirmware.git
   cd badgefirmware
   ```

2. Choose your dev container configuration:

   **Default configurations** are provided for Linux and macOS:
   - Linux: `.devcontainer/linux/devcontainer.json` (includes USB device mappings)
   - macOS: `.devcontainer/macos/devcontainer.json` (no USB mappings - see note below)

   **Custom configuration** (optional):
   If you need different USB devices or custom settings, create `.devcontainer/local/devcontainer.json` based on the Linux or macOS template.

3. Open in Dev Container:
   - Open the project folder in VS Code
   - Press `F1` and select "Dev Containers: Reopen in Container"
   - VS Code will automatically use the appropriate configuration for your platform
   - Wait for the container to build (this may take several minutes on first run)

### macOS USB Device Limitations

⚠️ **Important for macOS users**: Docker Desktop on macOS cannot mount USB devices into containers.

This means:
- **mpremote commands** (connecting to badge, REPL) must be run on the **host machine**
- **Firmware deployment** (flashing) must be done from the **host machine**
- All other development (building firmware, editing code) is done inside the container

**Required Python packages on macOS host:**

Install the required dependencies on your host machine. We recommend using **uv** for the best experience:

**Using uv (recommended):**
```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies from pyproject.toml
uv sync
```

This creates a `.venv` directory with all required packages (pyserial, esptool, black). The Makefile will automatically use this virtual environment when available.

**Alternative: Using pip with --user flag:**
```bash
pip3 install --user pyserial esptool
```

After setup, use `make repl_with_firmware_dir` on your host to connect to the badge.

### Code Formatting

This codebase uses [black](https://github.com/psf/black) to format code. The Dev Container includes black pre-installed.

The [Black Formatter extension](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter) is automatically installed in the Dev Container for automatic formatting.

### Working Inside the Dev Container

All development should be done inside the Dev Container, which includes:

- Python 3.13 and all required dependencies
- ESP-IDF build environment
- mpremote for device communication
- All necessary build tools

**Note:** This project does not support local development outside the Dev Container. The Dev Container ensures consistent build environments across all platforms.

### Special Requirements for Debian Trixie (stable)

In current Debian stable, you need to first compile `mpy-cross` separately before compiling the firmware:

```bash
make rebuild_mpy_cross
make build_firmware
```

## Building the Firmware

### Quick Start (Automated Build)

If you feel extremely lucky, try the automated build:

```bash
make build_firmware
```

If you get an error related to `mpy-cross`, you might need to build that first:

```bash
make rebuild_mpy_cross
make build_firmware
```

### Manual Build Process

On any errors with the automated build, you can try following the manual steps:

```bash
# Cannot be run in a python virtual env! Deactivate first
source set_environ.sh
cd micropython
ci_esp32_idf_setup
ci_esp32_build_common

# Now use the command that is needed
make ${MAKEOPTS} -C ports/esp32   # build
make ${MAKEOPTS} -C ports/esp32 deploy
make ${MAKEOPTS} -C ports/esp32 menuconfig

# If you need to trigger rebuild of mpy files:
rm -rf ports/esp32/build-ESP32_GENERIC_S3-DEVKITW2/frozen_mpy
make ${MAKEOPTS} -C ports/esp32   # build

source set_environ.sh
```

You are now in the build environment with all needed variables. Check help from [README.disobey.md](micropython/README.disobey.md).

The result should be `micropython.bin` in the repo root directory.

## Contribution Guidelines

### Code Style

- Use [black](https://github.com/psf/black) for Python code formatting
- Follow existing code patterns and conventions
- Write clear, descriptive commit messages

### Pull Request Process

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes following the code style guidelines
4. Test your changes thoroughly
5. Submit a pull request with a clear description of your changes

### Testing

Before submitting your contribution, please test your changes:

- Run existing tests (see [DEVELOPMENT.md](DEVELOPMENT.md) for testing instructions)
- Test on actual hardware if possible
- Ensure your changes don't break existing functionality

### Getting Help

If you need help with development setup or have questions about contributing:

- Check the [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development information
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
- Open an issue on GitHub for questions or bug reports

## Project Structure Overview

- **`/set_environment.sh`**: Environment file created when running make, modify to meet your needs
- **`/firmware`**: Firmware development directory for use with mpremote mount or rsync
- **`/frozen_firmware`**: Parts of firmware built into MicroPython itself
- **`/libs/`**: MicroPython related submodules
- **`/micropython/`**: MicroPython firmware build environment including IDF
