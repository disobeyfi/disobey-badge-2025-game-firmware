# Badge Firmware

A MicroPython firmware project for electronic badges. This repository manages the complex ecosystem of MicroPython firmware development with custom support for WROOM W2 and EC Cryptography.

## Quick Start

### Prerequisites

- **Docker Desktop** installed and running
- **VS Code** with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
  - Check also other tools in listed in https://containers.dev/supporting
- **Mpremote** (optional)

### Setup

1. Clone the repository with submodules:

   ```bash
   git clone --recursive https://github.com/disobeyfi/disobey-badge-2025-game-firmware
   cd disobey-badge-2025-game-firmware
   ```

2. Dev container configuration:

   **Default configurations** are provided:

   - **Linux**: Includes USB device mappings for `/dev/ttyUSB0` and `/dev/ttyUSB1`
   - **macOS**: No USB mappings (see limitations below)

   **Custom configuration** (optional):
   Create `.devcontainer/local/devcontainer.json` for custom USB devices or settings.

3. Open in VS Code and reopen in container:
   - Open the project folder in VS Code
   - Press `F1` and select "Dev Containers: Reopen in Container"
   - Select the devcontainer type you want to use: Linux, MacOs or MacOs - Rootless
   - Wait for the container to build and setup

#### macOS Note

⚠️ USB devices cannot be mounted into Docker containers on macOS. You must run `mpremote` commands and firmware deployment `make deploy` on the **host machine** (outside the container).

**Set your usb serialport as an environment variable:**
```
export PORT=/dev/cu.usbserial-[badge-serialport-number]
```

**Install required packages on your macOS host:**

**Using uv (recommended):**

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies (creates .venv with all required packages)
uv sync
```

**Or using pip with --user flag:**

```bash
pip3 install --user pyserial esptool
```

### Build Firmware

```bash
# Inside the Dev Container
make rebuild_mpy_cross # Compiling mpy cross will most likely fail on fresh container, so rebuild it first
make build_firmware

# Deploy firmware outside of Dev container
make deploy
```
Then use `make repl_with_firmware_dir` on your host to connect to the badge.

If you encounter issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions.

## Firmware Versions

- **Normal**: Contains the full game functionality
- **Minimal**: Contains badge test screen and OTA update capability for initial badge testing. This is only used to test badges until normal firmware has been developed enough

## Documentation

- **[HARDWARE.md](HARDWARE.md)** - Hardware specifications, schematics, and 3D models
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development setup, code formatting, and contribution guidelines
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Detailed development guide, testing, and hardware setup
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common problems and solutions

## Project Structure

- **`/firmware`** - Development firmware directory for live testing
- **`/frozen_firmware`** - Production-ready modules built into MicroPython
- **`/libs/`** - MicroPython related submodules
- **`/micropython/`** - MicroPython firmware build environment

## Development

For detailed development information, testing procedures, and hardware setup, see [DEVELOPMENT.md](DEVELOPMENT.md).

For contribution guidelines and environment setup, see [CONTRIBUTING.md](CONTRIBUTING.md).

For troubleshooting common issues, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Badge Team

The Disobey Badge is brought to you by:

| Member       | 2025 | 2026 |
| ------------ | :--: | :--: |
| Annenaattori |  ✓   |  ✓   |
| Dist         |  ✓   |  ✓   |
| Hasanen      |  ✓   |  ✓   |
| Kriisi       |  ✓   |  ✓   |
| onja         |      |  ✓   |
| Paaris       |  ✓   |  ✓   |
| Sanduuz      |      |  ✓   |
| Shadikka     |      |  ✓   |
| Troyhy       |  ✓   |  ✓   |
| Zokol        |  ✓   |  ✓   |

## Support

Need help or have questions? We're here to assist!

- **GitHub Issues**: [Report bugs or request features](https://github.com/disobeyfi/disobey-badge-2025-game-firmware/issues)
- **Discord**: Join our community on [Discord](https://discord.gg/S7eMF3TQCj) - find us in the **#badge** channel under the "Contests" category

## License

This project uses submodules with various licenses. Check individual component licenses for details.
