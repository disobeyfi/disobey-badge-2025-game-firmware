#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <FIRMWARE_PATH> <SERIAL_PORT_PATH>"
    exit 1
fi
# activate virtual environment
source .venv/bin/activate

# Arguments
FIRMWARE_PATH="$1"
SERIAL_PORT_PATH=$2

# Find all ttyUSB devices
SERIAL_PORTS=($SERIAL_PORT_PATH)

# Command to run
CMD_PREFIX="./automatic_deploy.sh $FIRMWARE_PATH"

# Kill tmux session if it exist
tmux has-session -t badge_flash 2>/dev/null
if [ $? != 0 ]; then
    tmux kill-session -d -s badge_flash
fi

i=0
for port in "${SERIAL_PORTS[@]}"; do
    echo "Current port: $port"
    # your commands here
    CMD="$CMD_PREFIX $port"
    echo "Running command: $CMD"

    if [ "$i" -eq 0 ]; then
        tmux new-session -d -s badge_flash "${CMD_PREFIX} ${port}"
    else
        tmux split-window -t badge_flash "${CMD_PREFIX} ${port}"
        tmux select-layout -t badge_flash tiled
    fi

    ((i++))
done

# Attach to the session
tmux attach -t badge_flash