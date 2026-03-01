#!/bin/bash

# Run script for Gmail Inbox Organizer
# Automatically activates the pyenv environment

set -e

VENV_NAME="inbox-organizer"

# Check if pyenv is available
if ! command -v pyenv &> /dev/null; then
    echo "Error: pyenv not found. Please install pyenv first."
    exit 1
fi

# Initialize pyenv
eval "$(pyenv init -)"

# Check if virtual environment exists
if ! pyenv versions | grep -q "$VENV_NAME"; then
    echo "Error: Virtual environment '$VENV_NAME' not found."
    echo "Please run ./setup.sh first to set up the environment."
    exit 1
fi

# Activate the virtual environment
pyenv activate "$VENV_NAME"

# Run the application
python main.py "$@"
