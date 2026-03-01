#!/bin/bash
# Cascade Course Merger - macOS launcher
# Double-click this file to launch the app.

cd "$(dirname "$0")"

# Find a Python 3 with working tkinter.
# Homebrew paths are tried first because the macOS system Python
# often ships with an outdated tkinter that crashes on newer macOS.
CANDIDATES=(
    /opt/homebrew/bin/python3
    /usr/local/bin/python3
    python3
    python
)

launch() {
    "$1" -c "import tkinter" 2>/dev/null && exec "$1" cascade_merge_gui.py
}

for py in "${CANDIDATES[@]}"; do
    if command -v "$py" &>/dev/null; then
        launch "$py" && exit 0
    fi
done

echo ""
echo "============================================================"
echo "  Could not find Python 3 with tkinter on this Mac."
echo ""
echo "  Fix with:  brew install python-tk"
echo "  Or get Python from: https://www.python.org/downloads/"
echo "============================================================"
echo ""
read -p "Press Enter to close..."
