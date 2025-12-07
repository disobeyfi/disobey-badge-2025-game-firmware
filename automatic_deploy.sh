#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <FIRMWARE_PATH> <SERIAL_PORT>"
    exit 1
fi

# Arguments
FIRMWARE_PATH="$1"
SERIAL_PORT="$2"
NUM_OF_LINES=5

# Function to check if a specific device is connected
is_device_connected() {
    local port="$1"
    if [ -e "$port" ]; then
        return 0  # Device is connected
    else
        return 1  # Device is not connected
    fi
}

print_empty_tail_lines() {
    for ((i=0; i<$NUM_OF_LINES; i++)); do
        echo ""
    done
}

# Loop to continuously check the status of the port
while true; do
    FLAG_FILE="/tmp/flash_done_${SERIAL_PORT//\//_}.flag"

    if is_device_connected "$SERIAL_PORT"; then
        if [ -f "$FLAG_FILE" ]; then
            clear
            echo "Device flashed, please disconnect device in port $SERIAL_PORT"
        else
            echo "Device connected, flashing..."
            echo "___________________"
            touch "$FLAG_FILE"
            esptool --chip esp32s3 -p $SERIAL_PORT -b 460800 --before=default-reset --after=hard-reset write-flash --flash-size detect 0x0 $FIRMWARE_PATH 
            echo "___________________"
            echo "Device flashed, please disconnect device"
        fi
    else
        clear
        echo "Connect device to port $SERIAL_PORT" 
        rm -f "$FLAG_FILE"
    fi
    sleep 0.5  # Wait before checking again
done