#!/usr/bin/env bash
# Hobbes installer script
# Usage: curl -fsSL https://raw.githubusercontent.com/mmasters/hobbes/main/scripts/install.sh | bash

set -e

HOBBES_HOME="${HOBBES_HOME:-$HOME/.hobbes}"

echo "Installing hobbes..."

# Check for Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "Error: Python 3.10+ is required (found $PYTHON_VERSION)"
    exit 1
fi

# Prefer pipx if available
if command -v pipx &> /dev/null; then
    echo "Installing with pipx..."
    pipx install hobbes
else
    echo "Installing with pip..."
    pip3 install --user hobbes
fi

# Create hobbes directories
mkdir -p "$HOBBES_HOME/bin"

# Check if bin directory is in PATH
if [[ ":$PATH:" != *":$HOBBES_HOME/bin:"* ]]; then
    echo ""
    echo "Add the following to your shell profile (.bashrc, .zshrc, etc.):"
    echo ""
    echo "  export PATH=\"\$HOME/.hobbes/bin:\$PATH\""
    echo ""
fi

echo ""
echo "Hobbes installed successfully!"
echo ""
echo "Get started:"
echo "  hobbes install junegunn/fzf"
echo "  hobbes list"
echo "  hobbes --help"
