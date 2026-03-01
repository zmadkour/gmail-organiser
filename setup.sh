#!/bin/bash

# Gmail Inbox Organizer Setup Script
# Uses pyenv with Python 3.13

set -e

echo "Setting up Gmail Inbox Organizer with pyenv and Python 3.13..."

# Check if pyenv is installed
if ! command -v pyenv &> /dev/null; then
    echo "pyenv not found. Please install pyenv first:"
    echo "  - macOS: brew install pyenv"
    echo "  - Linux: curl https://pyenv.run | bash"
    echo ""
    echo "Then add to your shell config (.bashrc/.zshrc):"
    echo '  export PYENV_ROOT="$HOME/.pyenv"'
    echo '  [[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"'
    echo '  eval "$(pyenv init -)"'
    exit 1
fi

echo "✓ pyenv found"

# Check if Python 3.13 is installed via pyenv
if ! pyenv versions | grep -q "3.13"; then
    echo "Python 3.13 not found in pyenv. Installing..."
    pyenv install 3.13.0
fi

echo "✓ Python 3.13 available"

# Create virtual environment with pyenv
VENV_NAME="inbox-organizer"

# Remove existing virtual environment if it exists
if pyenv versions | grep -q "$VENV_NAME"; then
    echo "Removing existing virtual environment..."
    pyenv uninstall -f "$VENV_NAME"
fi

echo "Creating pyenv virtual environment: $VENV_NAME"
pyenv virtualenv 3.13.0 "$VENV_NAME"

# Activate the virtual environment
echo "Activating virtual environment..."
eval "$(pyenv init -)"
pyenv activate "$VENV_NAME"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Set local pyenv version
echo "Setting local pyenv version..."
pyenv local "$VENV_NAME"

echo ""
echo "✓ Setup complete!"
echo ""
echo "To activate the environment in the future, run:"
echo "  pyenv activate inbox-organizer"
echo ""
echo "To run the application:"
echo "  python main.py"
echo ""
echo "To deactivate:"
echo "  pyenv deactivate"
