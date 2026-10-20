#!/usr/bin/env python3
"""
==============================================
BEAT THE BOX SUITE LAUNCHER
==============================================
File Location: Beat-the-Box-Card-Game/python/main.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 218 passed)

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
Opens a small window with one tile per tool. Each tool opens in its own
window, so several can run at once (for example the Player and a long
Optimizer run).

DEPENDENCIES:
------------
- btb.gui_game (PlayerGUI, AssistantGUI)
- btb.gui_sim (SimulatorGUI, OptimizerGUI)
- btb.theme, btb.settings, btb.system, btb.widgets
- Standard library: tkinter, multiprocessing

KEY FUNCTIONS:
-------------
- TOOLS -> list of (button name, window class, description)
- MainApplication.launch(cls) -> opens one tool in a new window
- SettingsDialog -> theme, odds default, CPU cores
- main() -> starts the launcher

CLI USAGE:
---------
# From the python/ folder
python main.py
"""

import multiprocessing
import tkinter as tk
from tkinter import ttk

from btb import __version__
from btb import settings as app_settings
from btb import theme as themes
from btb.gui_game import AssistantGUI, PlayerGUI
from btb.gui_sim import OptimizerGUI, SimulatorGUI
from btb.system import cpu_count, scan
from btb.theme import font
from btb.widgets import rounded_rect

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

TOOL_SUITS = {"Game Assistant": "♥", "Game Player": "♠", "Game Simulator": "♦",
              "Strategy Optimizer": "♣"}

HOW_IT_WORKS = """Beat the Box Suite: How it Works

Every tool plays by the same rules engine (btb/engine.py), which follows
RULES.md exactly. Nothing about the rules is duplicated between tools.
docs/GUIDE.md explains each tool in full; STRATEGY.md explains how to play
well.

1. Game Player
   - Shuffled deck; the banner at the top shows each call and its result
   - Odds under each card (Ctrl+O), full odds table (Ctrl+P)
   - Three card counts with a plain "lean" reading, a play history, undo

2. Game Assistant
   - Pick the nine box cards from your real deal
   - For each flip, click the card you actually drew in the card grid
   - Same odds, counts and undo as the Game Player

3. Game Simulator
   - Plays many games with the built-in strategy
   - Win rate with its margin of error, boxes-left chart, full details
   - Runs in the background: watch the progress, stop at any time
   - Export the results as CSV (Excel) or JSON

4. Strategy Optimizer
   - Sweeps joker counts, inclusive-call budgets and thresholds
   - Every configuration plays the same seeded deals, so the comparison is fair
   - Marks results that are statistically tied; can confirm the top 10
   - Also runs in the background, with Stop and exports

Settings (on this window): theme, odds shown by default, CPU cores."""

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

Reading simulator results
  - "25.6% ±0.9" means the true win rate is almost certainly between 24.7%
    and 26.5%. Ten times more games makes the range about three times
    narrower.
  - In the Optimizer, highlighted rows are statistically tied with the
    best. Use more games or Confirm top 10 to separate them.

Big runs
  - CPU cores "Auto" checks free CPU and memory at the start of each run,
    uses at most three quarters of your cores, always leaves one free,
    and runs its helpers at low priority.
  - Use Stop if a run is taking too long; finished results are kept.
  - Use a seed to make a run repeatable."""


class SettingsDialog:
    """Theme, odds default and CPU cores. Saved when you press Save."""

    def __init__(self, parent: tk.Misc):
        self.parent = parent
        current = app_settings.load()
        t = themes.current()
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.transient(parent)
        self.dialog.resizable(False, False)
        themes.paint_window(self.dialog, t)
        self.theme_var = tk.StringVar(value=t.name)
        self.odds_var = tk.BooleanVar(value=bool(current["show_odds"]))
        workers = current["cpu_workers"]
        self.cores_var = tk.StringVar(value="Auto" if workers == "auto" else str(workers))

        frame = ttk.Frame(self.dialog, padding=16)
        frame.pack(fill="both")
        ttk.Label(frame, text="Settings", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(frame, text="Theme", style="TLabelframe.Label").grid(
            row=1, column=0, columnspan=2, sticky="w")
        themes_box = ttk.Frame(frame)
        themes_box.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 10))
        self.swatches = []
        for i, theme in enumerate(themes.THEMES):
            row, col = divmod(i, 2)
            cell = ttk.Frame(themes_box)
            cell.grid(row=row, column=col, sticky="w", padx=(0, 16), pady=2)
            swatch = tk.Canvas(cell, width=64, height=26, highlightthickness=1,
                               highlightbackground=t.edge, borderwidth=0)
            self._draw_swatch(swatch, theme)
            swatch.pack(side="left")
            swatch.bind("<Button-1>", lambda e, n=theme.name: self.theme_var.set(n))
            ttk.Radiobutton(cell, text=f"{i + 1}. {theme.name}", value=theme.name,
                            variable=self.theme_var).pack(side="left", padx=(6, 0))
            self.swatches.append(swatch)

        ttk.Label(frame, text="Game windows", style="TLabelframe.Label").grid(
            row=3, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(frame, text="Show odds under the cards by default",
                        variable=self.odds_var).grid(row=4, column=0, columnspan=2,
                                                     sticky="w", pady=(4, 10))

        ttk.Label(frame, text="Simulator and Optimizer", style="TLabelframe.Label").grid(
            row=5, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text="CPU cores:").grid(row=6, column=0, sticky="w", pady=(4, 0))
        ttk.Combobox(frame, textvariable=self.cores_var, width=8, state="readonly",
                     values=["Auto"] + [str(n) for n in range(1, cpu_count() + 1)]).grid(
            row=6, column=1, sticky="w", pady=(4, 0))
        self.scan_label = ttk.Label(frame, text="", style="Muted.TLabel", wraplength=380)
        self.scan_label.grid(row=7, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Button(frame, text="Scan Now", command=self.rescan).grid(
            row=8, column=0, sticky="w", pady=(4, 10))

        buttons = ttk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Cancel", command=self.dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Save", style="Accent.TButton", command=self.save).pack(
            side="right", padx=6)
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())
        self.rescan()

    @staticmethod
    def _draw_swatch(canvas: tk.Canvas, t: themes.Theme):
        canvas.configure(background=t.bg)
        rounded_rect(canvas, 6, 4, 26, 24, 4, fill=t.card, outline=t.card_edge)
        canvas.create_text(16, 14, text="♥", fill=t.red, font=font("symbol", 9))
        rounded_rect(canvas, 30, 4, 50, 24, 4, fill=t.back, outline=t.card_edge)
        canvas.create_oval(54, 10, 62, 18, fill=t.accent, outline="")

    def rescan(self):
        result = scan()
        self.scan_label.config(text=f"Right now: {result.describe()}.")

    def save(self):
        cores = self.cores_var.get()
        app_settings.update(show_odds=bool(self.odds_var.get()),
                            cpu_workers="auto" if cores == "Auto" else int(cores))
        themes.set_theme(self.theme_var.get(), self.parent)
        self.dialog.destroy()


class MainApplication:
    def __init__(self, root: tk.Misc):
        self.root = root
        self.root.title("Beat the Box Suite")
        self.theme = themes.use(root)
        self.suit_labels = []
        main = ttk.Frame(root, padding=20)
        main.grid(row=0, column=0, sticky="nsew")

        header = ttk.Frame(main)
        header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))
        self.logo = tk.Canvas(header, width=74, height=62, highlightthickness=0, borderwidth=0)
        self.logo.pack(side="left")
        words = ttk.Frame(header)
        words.pack(side="left", padx=(12, 0))
        ttk.Label(words, text="Beat the Box", style="Title.TLabel").pack(anchor="w")
        ttk.Label(words, text="A solitaire card game of odds, nerve, and second chances.",
                  style="Muted.TLabel").pack(anchor="w")

        for i, (name, cls, blurb) in enumerate(TOOLS):
            row, col = divmod(i, 2)
            tile = ttk.Frame(main, style="Panel.TFrame", padding=14)
            tile.grid(row=1 + row, column=col, sticky="nsew", padx=(0 if col == 0 else 10, 0),
                      pady=(0, 10))
            suit = tk.Label(tile, text=TOOL_SUITS[name], font=font("symbol", 22, "bold"))
            suit.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 10))
            self.suit_labels.append(suit)
            ttk.Label(tile, text=name, style="PanelHeading.TLabel").grid(
                row=0, column=1, sticky="w")
            ttk.Label(tile, text=blurb, style="PanelMuted.TLabel", wraplength=230).grid(
                row=1, column=1, sticky="w", pady=(2, 8))
            ttk.Button(tile, text=f"Open {name.split()[-1]}", style="Accent.TButton",
                       command=lambda c=cls: self.launch(c)).grid(row=2, column=1, sticky="w")
        main.columnconfigure(0, weight=1, uniform="tile")
        main.columnconfigure(1, weight=1, uniform="tile")

        footer = ttk.Frame(main)
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        for label, command in (("How it Works", lambda: self.text_window("How it Works",
                                                                          HOW_IT_WORKS)),
                               ("Important Points", lambda: self.text_window(
                                   "Important Points", IMPORTANT_POINTS)),
                               ("Settings", self.open_settings)):
            ttk.Button(footer, text=label, command=command).pack(side="left", padx=(0, 6))
        ttk.Button(footer, text="Exit", command=root.destroy).pack(side="right")
        ttk.Label(main, text=f"Suite version {__version__}", style="Muted.TLabel").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self.text_widgets = []
        self.windows = []
        self.paint(self.theme)
        themes.subscribe(self.root, self.paint)

    def paint(self, t: themes.Theme):
        self.theme = t
        themes.paint_window(self.root, t)
        c = self.logo
        c.delete("all")
        c.configure(background=t.bg)
        rounded_rect(c, 6, 10, 42, 58, 6, fill=t.shadow, outline="")
        rounded_rect(c, 4, 6, 40, 54, 6, fill=t.card, outline=t.card_edge)
        c.create_text(22, 30, text="♠", fill=t.black, font=font("symbol", 20))
        rounded_rect(c, 32, 4, 68, 52, 6, fill=t.card, outline=t.card_edge)
        c.create_text(50, 28, text="♥", fill=t.red, font=font("symbol", 20))
        for label in self.suit_labels:
            label.configure(background=t.panel, foreground=t.accent)
        themes.repaint(getattr(self, "text_widgets", []), getattr(self, "windows", []), t)

    def launch(self, cls):
        return cls(tk.Toplevel(self.root))

    def open_settings(self):
        return SettingsDialog(self.root)

    def text_window(self, title: str, body: str):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("640x460")
        themes.paint_window(win, self.theme)
        self.windows.append(win)
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        widget = tk.Text(frame, wrap="word", font=font("mono", 10), padx=12, pady=10,
                         yscrollcommand=scrollbar.set)
        themes.style_text_widget(widget, self.theme)
        self.text_widgets.append(widget)
        widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=widget.yview)
        widget.insert("end", body)
        widget.config(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 10))
        return win


def main():
    multiprocessing.freeze_support()
    root = tk.Tk()
    MainApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()