#!/bin/bash

# Resolve script location (works even if symlinked)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Set the PATH variable if it doesn't exist
if [ -z "$PATH" ]; then
    export PATH="/usr/bin:/bin"
fi

VENV="$SCRIPT_DIR/.venv"

# If venv does not exist, create it and install dependencies
if [ ! -d "$VENV" ]; then
    echo "⚙️  Creating virtual environment..."
    python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    echo "📦 Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    # Activate the virtual environment
    source "$VENV/bin/activate"
fi

# Check if we're being run in the background or not
#if [ "$#" -ne 1 ]; then
#    echo "Usage: $0 <foreground>"
#    exit 1
#fi

# Run the program with Python 3
python3 "$SCRIPT_DIR/pinger.py" &
