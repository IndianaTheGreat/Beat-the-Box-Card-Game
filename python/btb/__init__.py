"""
==============================================
BTB PACKAGE
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/__init__.py
Status: ACTIVE
Version: 1.3
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 308 passed)

VERSION 1.3 CHANGES (2026-10-20):
- Suite version 1.4.0: a recovered box comes back with the card that beat
  it (docs/RULES.md); a big and a little joker; Cards left as a Simple
  table or as Cards; the Assistant's card picker no longer freezes.

VERSION 1.2 CHANGES (2026-10-20):
- Suite version 1.3.0: separate Show odds / Show counts switches, a
  sortable odds table, the new call-button order, help pages drawn as
  formatted documents, and charts in the Advanced tabs.
- Lists btb.app and the new btb.markup; the rules file is docs/RULES.md.

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

    btb.engine    the rules (docs/RULES.md), with no GUI code
    btb.strategy  the simulator's playing policy
    btb.sim       batch simulations, parameter sweeps, chart data
    btb.system    CPU and memory scan for parallel runs
    btb.export    CSV and JSON exports of simulator results
    btb.text      in-app rules, strategy text, tool help, shortcuts
    btb.markup    reads the help-page markup the text is written in
    btb.settings  remembered settings (theme, odds, counts, CPU cores)
    btb.theme     the colour themes, fonts and ttk styling
    btb.widgets   drawn cards, stat tiles, charts, help pages, card picker
    btb.gui_game  Game Player and Game Assistant pages
    btb.gui_sim   Simulator and Strategy Optimizer pages
    btb.app       the one window: sidebar, Home, help pages, Settings

NOTES:
-----
- __version__ is the suite version, separate from each file's Version.
"""

__version__ = "1.4.0"