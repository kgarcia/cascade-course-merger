#!/bin/bash
# Cascade Course Merger - macOS launcher
# Double-click this file to launch the app.

cd "$(dirname "$0")"

# Find a Python 3 with working tkinter.
# Homebrew python3.11 is tried first because the macOS system Python
# often ships with an outdated tkinter that crashes on newer macOS.
CANDIDATES=(
    /opt/homebrew/bin/python3.11
    /opt/homebrew/bin/python3
    /usr/local/bin/python3.11
    /usr/local/bin/python3
    python3
    python
)

for py in "${CANDIDATES[@]}"; do
    if command -v "$py" &>/dev/null; then
        # Verify tkinter actually works (not just importable, but can init Tk)
        "$py" -c "import tkinter; tkinter.Tk().destroy()" 2>/dev/null
        if [ $? -eq 0 ]; then
            exec "$py" cascade_merge_gui.py
        fi
    fi
done

echo ""
echo "============================================================"
echo "  Could not find Python 3 with working tkinter on this Mac."
echo ""
echo "  Fix with:  brew install python-tk@3.11"
echo "  Or get Python from: https://www.python.org/downloads/"
echo "============================================================"
echo ""
read -rp "Press Enter to close..."
