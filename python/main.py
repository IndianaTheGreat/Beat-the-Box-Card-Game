#!/usr/bin/env python3
"""
==============================================
BEAT THE BOX SUITE LAUNCHER
==============================================
File Location: Beat-the-Box-Card-Game/python/main.py
Status: ACTIVE
Version: 1.2
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 254 passed)

VERSION 1.2 CHANGES (2026-10-20):
- Starts the one-window app (btb/app.py): a sidebar of pages instead of a
  launcher that opens a window per tool. The launcher tiles, Settings
  window and help windows moved into that app as pages; their text moved
  to btb/text.py.
- MainApplication is now the app; TOOLS is re-exported from btb.app.

VERSION 1.1 CHANGES (2026-10-20):
- New look in the chosen theme: a drawn logo and one tile per tool.
- New Settings window: pick a theme (numbered 1-8, with a preview), set
  whether odds show under the cards by default, and set the CPU cores the
  Simulator and Optimizer may use (Auto scans what is free). All three
  are remembered between runs (btb/settings.py). The odds choice is the
  default for new game windows; Ctrl+O changes only the open window.
- Help windows updated: themes, parallel runs, margins of error, exports.
- multiprocessing.freeze_support(), required for parallel runs in a
  packaged .exe later.

VERSION 1.0 CHANGES (2026-10-20):
- Rewritten for Phase 1. Launches the four tools from the btb package
  instead of the old BTB*.py modules.
- Help windows (How it Works, Important Points) updated to the confirmed
  rules and the corrected reading of the card count.

DESCRIPTION:
-----------
Starts Beat the Box: one window with a sidebar on the left (Home, the four
tools, help pages and Settings) and the chosen page on the right.

DEPENDENCIES:
------------
- btb.app (App, TOOLS)
- Standard library: tkinter, multiprocessing

KEY FUNCTIONS:
-------------
- MainApplication(root) -> the one-window app (btb.app.App)
- TOOLS -> (name, page class, description) for the four tools
- main() -> starts the app

CLI USAGE:
---------
# From the python/ folder
python main.py

NOTES:
-----
- multiprocessing.freeze_support() must stay first in main(): parallel
  Simulator runs start helper copies of this program, and a packaged .exe
  needs it to tell them apart.
"""

import multiprocessing
import tkinter as tk

from btb.app import TOOLS, App

MainApplication = App

__all__ = ["MainApplication", "TOOLS", "main"]


def main():
    multiprocessing.freeze_support()
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()