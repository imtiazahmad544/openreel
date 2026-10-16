#!/bin/bash
# OpenReel one-click launcher (Linux / macOS)
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
    python3 launcher.py
else
    python launcher.py
fi
