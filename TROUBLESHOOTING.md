# Troubleshooting

This document contains solutions to common problems you might encounter when working with the Badge Firmware project.

## Build Issues

### `idf.py fullclean` Error

If you get a similar error to the following:

```bash
#...
Synchronizing submodule url for 'lib/tinyusb'
# If available, do blobless partial clones of submodules to save time and space.
# A blobless partial clone lazily fetches data as needed, but has all the metadata available (tags, etc.).
# Fallback to standard submodule update if blobless isn't available (earlier than 2.36.0)
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
idf.py -D MICROPY_BOARD=ESP32_GENERIC_S3 -D MICROPY_BOARD_DIR="PATH/badgefirmware/micropython/ports/esp32/boards/ESP32_GENERIC_S3" -D MICROPY_FROZEN_MANIFEST=PATH/badgefirmware/frozen_firmware/frozen_manifest_minimal.py -D MICROPY_BOARD_VARIANT=DEVKITW2 -B build-ESP32_GENERIC_S3-DEVKITW2 build || (echo -e "See \033[1;31mhttps://github.com/micropython/micropython/wiki/Build-Troubleshooting\033[0m"; false)
Executing action: all (aliases: build)
'$HOME/.espressif/python_env/idf5.2_py3.13_env/bin/python' is currently active in the environment while the project was configured with '$HOME/.espressif/python_env/idf5.2_py3.12_env/bin/python'. Run 'idf.py fullclean' to start again.
-e See https://github.com/micropython/micropython/wiki/Build-Troubleshooting
make[1]: *** [all] Error 1
make: *** [dist/firmware_minimal.bin] Error 2
```

**Solution:**

Run the following command to clean previously built versions of firmware and clear caches:

```bash
make clean
```

This error typically occurs when there's a mismatch between Python environments used for ESP-IDF configuration.

### `mpy-cross` Related Errors

If you get errors related to `mpy-cross` during the build process:

**Solution:**

Build `mpy-cross` manually first:

```bash
cd micropython/mpy-cross
make clean && make
cd ../..

make build_firmware
```

### Python Virtual Environment Issues

**Problem:** Build fails when running inside a Python virtual environment.

**Solution:**

Always use the Dev Container for development. If you're experiencing issues:

1. Make sure you're working inside the Dev Container:

   - Check VS Code's bottom-left corner for "Dev Container: Badge Firmware Dev Container"
   - If not, press `F1` → "Dev Containers: Reopen in Container"

2. If issues persist, rebuild the container:
   ```bash
   # From VS Code: F1 → "Dev Containers: Rebuild Container"
   ```

**Note:** Local development outside the Dev Container is not supported.

## Development Issues

### Testing Errors

**Problem:** Getting errors when trying to load test modules.

**Solution:**

If you get an error when importing test modules, try loading again:

```python
# In REPL, if this fails:
from tests import test_image

# Try running it again - it often works on the second attempt
```

### Connection Issues with Multiple Devices

**Problem:** Unable to connect to the correct device when multiple badges are connected.

**Solution:**

Specify the port explicitly:

```bash
# For mounting firmware
python micropython/tools/mpremote/mpremote.py baud 460800 connect /dev/ttyUSB0 mount -l firmware

# For deploying firmware
make PORT=/dev/ttyUSB0 deploy
```

Replace `/dev/ttyUSB0` with your actual device port.

## Hardware Issues

### Display Not Working

**Problem:** Display remains blank or shows incorrect output.

**Solution:**

1. Check all display connections according to the devkit diagram
2. Ensure power connections are secure
3. Verify the display is compatible with the expected interface

### Button Input Not Responding

**Problem:** Button presses are not detected.

**Solution:**

1. Ensure buttons are properly connected to ground
2. Check that pull-up resistors are configured correctly (usually handled in software)
3. Test individual buttons using the button test script:
   ```python
   import tests.badge_gui
   ```

## General Troubleshooting Tips

### Clean Build

If you encounter persistent build issues, try a complete clean:

```bash
make clean
cd micropython/mpy-cross
make clean
cd ../..
```

Then rebuild from scratch.

### Environment Variables

Ensure you've sourced the environment file:

```bash
source set_environ.sh
```

### Submodule Issues

If you encounter submodule-related problems:

```bash
git submodule update --init --recursive
```

### Permission Issues

On Linux/macOS, you might need to add your user to the dialout group to access serial ports:

```bash
sudo usermod -a -G dialout $USER
```

Log out and log back in for the change to take effect.

#### docker rootless mode

If you are using docker in rootless mode, you might get permission denied errors when trying to
build the firmware within the container due to UID remapping. To overcome this problem use the
supplied rootless version of the docker-compose file to build the container:

1. `docker compose -f docker-compose.rootless.yaml up --force-recreate --build -d`

Then proceed to build the firmware as usual:

1. `docker exec -it badgefirmware-app-1 /bin/bash`
2. `make build_firmware`

Note: You might still get mpy-cross problems when building the firmware. For that refer the
[mpy-cross Related Errors](#mpy-cross-related-errors) section from this file.

## Getting Additional Help

If you continue to experience issues:

1. Check the [MicroPython Build Troubleshooting Wiki](https://github.com/micropython/micropython/wiki/Build-Troubleshooting)
2. Review the [DEVELOPMENT.md](DEVELOPMENT.md) guide for detailed setup instructions
3. Check [CONTRIBUTING.md](CONTRIBUTING.md) for environment setup
4. Open an issue on GitHub with detailed error messages and your system information
