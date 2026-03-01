#!/bin/bash
# Cascade Course Merger - macOS launcher
# Double-click this file to launch the app.

cd "$(dirname "$0")"

if command -v python3 &>/dev/null; then
    python3 cascade_merge_gui.py
elif command -v python &>/dev/null; then
    python cascade_merge_gui.py
else
    echo ""
    echo "============================================================"
    echo "  Python 3 is required but was not found."
    echo ""
    echo "  Install it with:   brew install python"
    echo "  Or download from:  https://www.python.org/downloads/"
    echo "============================================================"
    echo ""
    read -p "Press Enter to close..."
fi
