#!/bin/bash

# Set the PATH variable if it doesn't exist
if [ -z "$PATH" ]; then
    export PATH="/usr/bin:/bin"
fi

# Activate the virtual environment
source /home/rich/working/pinger/.venv/bin/activate

# Check if we're being run in the background or not
#if [ "$#" -ne 1 ]; then
#    echo "Usage: $0 <foreground>"
#    exit 1
#fi

# Run the program with Python 3
python3 /home/rich/working/pinger/pinger.py &
