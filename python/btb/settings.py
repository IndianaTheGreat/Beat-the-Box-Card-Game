"""
==============================================
REMEMBERED SETTINGS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/settings.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.1 CHANGES (2026-10-20):
- New setting show_counts: whether game pages start with the card counts,
  plays and cards left showing (show_odds now covers only the odds). A
  settings file from before this change has only show_odds; its value is
  used for both, so nothing you saw before disappears.

VERSION 1.0 CHANGES (2026-10-20):
- New. Remembers the theme, the "show odds on cards" choice and the CPU
  cores setting between runs.

DESCRIPTION:
-----------
A tiny JSON file in your user folder:

  Windows  %APPDATA%\\BeatTheBox\\settings.json
  macOS    ~/Library/Application Support/BeatTheBox/settings.json
  Linux    ~/.config/beat-the-box/settings.json

Only known keys with the right type are read; anything else in the file
is ignored, and a missing or damaged file just means the defaults. No GUI
code.

DEPENDENCIES:
------------
- Standard library: json, os, sys, pathlib

KEY FUNCTIONS:
-------------
- DEFAULTS -> theme (None = the theme.py default), show_odds,
  show_counts, cpu_workers
- settings_path() -> where the file lives
- load() -> dict of every setting (defaults filled in)
- save(values) -> True if written
- get(key), update(**changes) -> read one / change some and save

ERROR HANDLING:
--------------
Never raises for file problems: load() falls back to the defaults and
save() returns False, so a read-only folder can't break the game.

NOTES:
-----
- The BTB_SETTINGS_DIR environment variable moves the file (the tests use
  it so they never touch your real settings).
- Writes go to a temporary file first, then replace the old one, so a
  crash mid-write can't leave a half-written file.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

ENV_DIR = "BTB_SETTINGS_DIR"
FILE_NAME = "settings.json"

DEFAULTS: Dict[str, Any] = {
    "theme": None,          # None = theme.DEFAULT_THEME
    "show_odds": False,     # odds under the cards and the odds table
    "show_counts": False,   # card counts, plays and cards left
    "cpu_workers": "auto",  # "auto" or a number of processes
}


def settings_dir() -> Path:
    override = os.environ.get(ENV_DIR)
    if override:
        return Path(override)
    home = Path.home()
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        return (Path(base) if base else home / "AppData" / "Roaming") / "BeatTheBox"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "BeatTheBox"
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else home / ".config") / "beat-the-box"


def settings_path() -> Path:
    return settings_dir() / FILE_NAME


def _valid(key: str, value: Any) -> bool:
    if key == "theme":
        return value is None or isinstance(value, str)
    if key in ("show_odds", "show_counts"):
        return isinstance(value, bool)
    if key == "cpu_workers":
        return value == "auto" or (isinstance(value, int) and not isinstance(value, bool)
                                   and value >= 1)
    return False


def load() -> Dict[str, Any]:
    values = dict(DEFAULTS)
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return values
    if isinstance(data, dict):
        for key in DEFAULTS:
            if key in data and _valid(key, data[key]):
                values[key] = data[key]
        if "show_counts" not in data and _valid("show_odds", data.get("show_odds")):
            values["show_counts"] = data["show_odds"]    # file from before the split
    return values


def save(values: Dict[str, Any]) -> bool:
    clean = {k: v for k, v in values.items() if k in DEFAULTS and _valid(k, v)}
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(clean, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def get(key: str) -> Any:
    return load()[key]


def update(**changes: Any) -> bool:
    values = load()
    for key, value in changes.items():
        if key not in DEFAULTS or not _valid(key, value):
            raise ValueError(f"invalid setting {key}={value!r}")
        values[key] = value
    return save(values)