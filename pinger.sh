#!/bin/bash

# Resolve script location (works even if symlinked)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1


# Set the PATH variable if it doesn't exist
if [ -z "$PATH" ]; then
    export PATH="/usr/bin:/bin"
fi

# Activate the virtual environment
source "$SCRIPT_DIR/.venv/bin/activate"

# Check if we're being run in the background or not
#if [ "$#" -ne 1 ]; then
#    echo "Usage: $0 <foreground>"
#    exit 1
#fi

# Run the program with Python 3
python3 "$SCRIPT_DIR/pinger.py" &
