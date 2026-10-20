#!/usr/bin/env python3
"""
==============================================
BEAT THE BOX SUITE LAUNCHER
==============================================
File Location: Beat-the-Box-Card-Game/python/main.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

VERSION 1.0 CHANGES (2026-10-20):
- Rewritten for Phase 1. Launches the four tools from the btb package
  instead of the old BTB*.py modules.
- Help windows (How it Works, Important Points) updated to the confirmed
  rules and the corrected reading of the card count.

DESCRIPTION:
-----------
Opens a small window with one button per tool. Each tool opens in its own
window, so several can run at once (for example the Player and a long
Optimizer run).

DEPENDENCIES:
------------
- btb.gui_game (PlayerGUI, AssistantGUI)
- btb.gui_sim (SimulatorGUI, OptimizerGUI)
- Standard library: tkinter

KEY FUNCTIONS:
-------------
- TOOLS -> list of (button name, window class, description)
- MainApplication.launch(cls) -> opens one tool in a new window
- main() -> starts the launcher

CLI USAGE:
---------
# From the python/ folder
python main.py
"""

import tkinter as tk
from tkinter import scrolledtext, ttk

from btb.gui_game import AssistantGUI, PlayerGUI
from btb.gui_sim import OptimizerGUI, SimulatorGUI

TOOLS = [
    ("Game Assistant", AssistantGUI,
     "Mirror a game you're playing with a real deck: enter the cards as they "
     "come and get live odds and counts."),
    ("Game Player", PlayerGUI,
     "Play Beat the Box with a shuffled deck, live odds, card counts and undo."),
    ("Game Simulator", SimulatorGUI,
     "Let the strategy play thousands of games and report the results."),
    ("Strategy Optimizer", OptimizerGUI,
     "Sweep jokers, inclusive calls and thresholds to find what wins most."),
]

HOW_IT_WORKS = """Beat the Box Suite: How it Works

Every tool plays by the same rules engine (btb/engine.py), which follows
RULES.md exactly. Nothing about the rules is duplicated between tools.

1. Game Player
   - Shuffled deck, live odds for every box (Ctrl+P), three card counts
   - Undo any move, keyboard shortcuts for everything (Ctrl+H)

2. Game Assistant
   - Pick the nine box cards from your real deal
   - For each flip, pick the card you actually drew
   - Same odds, counts and undo as the Game Player

3. Game Simulator
   - Plays many games with the built-in strategy
   - Reports win rate, boxes left, inclusive calls used and more
   - Runs in the background: watch the progress, stop at any time

4. Strategy Optimizer
   - Sweeps joker counts, inclusive-call budgets and thresholds
   - Every configuration plays the same seeded deals, so the comparison is fair
   - Also runs in the background with a Stop button"""

IMPORTANT_POINTS = """Beat the Box Suite: Important Points

Rules worth remembering
  - A same-rank card on a plain Higher or Lower is a loss.
  - Inclusive calls are spent when made, win or lose.
  - Exact match on an inclusive call = one recovery. A joker (drawn or in
    the box) is an exact match for anything.
  - Recoveries can't be banked: with no failed box, the recovery is lost.
  - A recovered box comes back with the card it failed on.

Settings limits
  - Jokers: 0-2
  - Inclusive calls: 0 to 43 + jokers
  - Threshold: 0-100 percentage points (the gain an inclusive call must
    offer over the best plain call before the strategy spends one)

Reading the counts
  - Positive count: high cards already seen, so more LOW cards remain.
  - Negative count: more HIGH cards remain.

Big runs
  - The simulator and optimizer run in the background. Use Stop if a run
    is taking too long; partial optimizer results are still shown.
  - Use a seed to make a run repeatable."""


class MainApplication:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Beat the Box Suite")
        main = ttk.Frame(root, padding=20)
        main.grid(row=0, column=0, sticky="nsew")
        ttk.Label(main, text="🂠 Beat the Box Suite", font=("Helvetica", 16, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 20))
        for row, (name, cls, blurb) in enumerate(TOOLS, start=1):
            ttk.Button(main, text=name, width=30,
                       command=lambda c=cls: self.launch(c)).grid(
                row=row, column=0, pady=8, padx=10)
            ttk.Label(main, text=blurb, wraplength=260).grid(
                row=row, column=1, pady=8, padx=10, sticky="w")
        info = ttk.Frame(main)
        info.grid(row=len(TOOLS) + 1, column=0, columnspan=2, pady=20)
        ttk.Button(info, text="How it Works", width=20,
                   command=lambda: self.text_window("How it Works", HOW_IT_WORKS)).pack(
            side="left", padx=5)
        ttk.Button(info, text="Important Points", width=20,
                   command=lambda: self.text_window("Important Points", IMPORTANT_POINTS)).pack(
            side="left", padx=5)
        ttk.Button(main, text="Exit", width=20, command=root.destroy).grid(
            row=len(TOOLS) + 2, column=0, columnspan=2)

    def launch(self, cls):
        return cls(tk.Toplevel(self.root))

    def text_window(self, title: str, body: str):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("620x420")
        widget = scrolledtext.ScrolledText(win, wrap="word", font=("Consolas", 10))
        widget.pack(padx=10, pady=10, fill="both", expand=True)
        widget.insert("end", body)
        widget.config(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 10))


def main():
    root = tk.Tk()
    MainApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()