# OmniMC 0.4 — Tkinter build

This build replaces PySide6 with Python's built-in Tkinter UI.

Features retained:
- Mojang live release/snapshot catalog
- Bundled 1,121-entry historical archive catalog
- Betacraft legacy metadata fallback for archive builds
- Microsoft OAuth / Xbox Live / XSTS / Minecraft Services login
- Built-in OmniMC Microsoft client ID
- Version install and launch flow
- Background network work so the window renders immediately

## Run on Windows
Double-click `run.bat`, or run:

    py -m pip install -r requirements.txt
    py main.py

Tkinter is included with the standard python.org Windows Python installer.
