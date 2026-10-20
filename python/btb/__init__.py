"""
==============================================
BTB PACKAGE
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/__init__.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 218 passed)

VERSION 1.1 CHANGES (2026-10-20):
- Suite version 1.2.0: new look and themes, faster and more accurate
  Simulator and Optimizer, exports, strategy and tool guides.
- Lists the new modules: theme, settings, widgets, system, export.

VERSION 1.0 CHANGES (2026-10-20):
- New package holding the shared engine and the four tool windows.

DESCRIPTION:
-----------
Package overview. Every tool imports its rules from btb.engine, so the
rules live in exactly one place.

    btb.engine    the rules (RULES.md), with no GUI code
    btb.strategy  the simulator's playing policy
    btb.sim       batch simulations and parameter sweeps
    btb.system    CPU and memory scan for parallel runs
    btb.export    CSV and JSON exports of simulator results
    btb.text      in-app rules, strategy text, tool help, shortcuts
    btb.settings  remembered settings (theme, odds, CPU cores)
    btb.theme     the colour themes, fonts and ttk styling
    btb.widgets   drawn cards, stat tiles, charts, card picker
    btb.gui_game  Game Player and Game Assistant windows
    btb.gui_sim   Simulator and Strategy Optimizer windows

NOTES:
-----
- __version__ is the suite version, separate from each file's Version.
"""

__version__ = "1.2.0"