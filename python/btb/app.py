"""
==============================================
ONE-WINDOW APP: SIDEBAR AND PAGES
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/app.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.1 CHANGES (2026-10-20):
- Help pages (How to Play, Strategy, Tool Guide, Shortcuts) look like a
  formatted document (widgets.DocView) in the app's UI font: headings,
  lists, tables, keys and card colours, instead of plain monospaced text.
- Settings has two defaults, "Show odds by default" and "Show counts by
  default", for the two switches on the game pages (Ctrl+O and Ctrl+K).

VERSION 1.0 CHANGES (2026-10-20):
- New. The whole suite in one window: a sidebar on the left switches
  between pages (Home, the four tools, How to Play, Strategy, Tool Guide,
  Shortcuts, Settings). Replaces the launcher and its pop-up windows.
- The sidebar is only as wide as its labels need. A page can have an
  on_show() method; it runs each time the page is shown.
- Settings: what you see is reloaded from the saved settings each time
  the page opens; Cancel (or Escape) drops unsaved choices and goes back
  to the page you came from; Save writes only what you changed.

DESCRIPTION:
-----------
App builds the window, the sidebar and an empty content area. Each page is
built the first time you open it and then kept, so it keeps its place: a
game in progress or a long Optimizer run carries on while you look at
another page. Only the page that is showing reacts to the keyboard.

The window opens sized to fit the screen and can be resized down to
MIN_SIZE; the pages follow it, and panels that don't fit get a scrollbar.

DEPENDENCIES:
------------
- btb.gui_game (PlayerGUI, AssistantGUI), btb.gui_sim (SimulatorGUI,
  OptimizerGUI), btb.text, btb.theme, btb.settings, btb.system,
  btb.widgets, btb (suite version)
- Standard library: tkinter, typing

KEY FUNCTIONS:
-------------
- TOOLS -> (name, page class, description) for the four tools
- App(root).show_page(key) -> shows a page (building it if needed, then
  calling its on_show() if it has one), returns it
- App.page(key) -> the page object if it has been built, else None
- App.launch(cls), App.open_settings() -> shortcuts to show_page
- HomePage, TextPage (a DocView help page), SettingsPage -> the non-tool
  pages

NOTES:
-----
- Page keys: home, player, assistant, simulator, optimizer, rules,
  strategy, guide, shortcuts, settings.
- Closing the window stops any running Simulator or Optimizer first.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Tuple

from . import __version__
from . import settings as app_settings
from . import text
from . import theme as themes
from .gui_game import AssistantGUI, PlayerGUI
from .gui_sim import OptimizerGUI, SimulatorGUI
from .system import cpu_count, scan
from .theme import Theme, font
from .widgets import DocView, rounded_rect, text_width, wrap_to

TOOLS = [
    ("Game Player", PlayerGUI,
     "Play Beat the Box with a shuffled deck, live odds, card counts and undo."),
    ("Game Assistant", AssistantGUI,
     "Mirror a game you're playing with a real deck: enter the cards as they "
     "come and get live odds and counts."),
    ("Game Simulator", SimulatorGUI,
     "Let the strategy play thousands of games and report the results."),
    ("Strategy Optimizer", OptimizerGUI,
     "Sweep jokers, inclusive calls and thresholds to find what wins most."),
]

TOOL_KEYS = {PlayerGUI: "player", AssistantGUI: "assistant", SimulatorGUI: "simulator",
             OptimizerGUI: "optimizer"}
TOOL_SUITS = {"player": "♠", "assistant": "♥", "simulator": "♦", "optimizer": "♣"}

# Sidebar: (section heading, [(page key, label)])
NAVIGATION: List[Tuple[str, List[Tuple[str, str]]]] = [
    ("", [("home", "⌂  Home")]),
    ("PLAY", [("player", "♠  Game Player"), ("assistant", "♥  Game Assistant")]),
    ("ANALYZE", [("simulator", "♦  Simulator"), ("optimizer", "♣  Optimizer")]),
    ("HELP", [("rules", "How to Play"), ("strategy", "Strategy"), ("guide", "Tool Guide"),
              ("shortcuts", "Shortcuts")]),
    ("", [("settings", "⚙  Settings")]),
]

PAGE_TITLES = {key: label.split("  ")[-1] for _section, items in NAVIGATION
               for key, label in items}


# --------------------------------------------------------------------------- #
# Simple pages
# --------------------------------------------------------------------------- #

class TextPage:
    """A help page drawn as a formatted document (widgets.DocView): rules,
    strategy, tool guide, shortcuts. The title is the page's own heading."""

    def __init__(self, parent: tk.Misc, app: "App", title: str, body: str):
        self.app = app
        self.title = title
        self.frame = ttk.Frame(parent, padding=14)
        self.frame.grid(row=0, column=0, sticky="nsew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        self.doc = DocView(self.frame, body)
        self.doc.pack(fill="both", expand=True)
        self.text = self.doc.text


class HomePage:
    """The welcome page: one tile per tool."""

    def __init__(self, parent: tk.Misc, app: "App"):
        self.app = app
        self.frame = ttk.Frame(parent, padding=24)
        self.frame.grid(row=0, column=0, sticky="nsew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        self.suit_labels: List[tk.Label] = []

        header = ttk.Frame(self.frame)
        header.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))
        self.logo = tk.Canvas(header, width=74, height=62, highlightthickness=0, borderwidth=0)
        self.logo.pack(side="left")
        words = ttk.Frame(header)
        words.pack(side="left", padx=(12, 0))
        ttk.Label(words, text="Beat the Box", style="Title.TLabel").pack(anchor="w")
        ttk.Label(words, text="A solitaire card game of odds, nerve, and second chances.",
                  style="Muted.TLabel").pack(anchor="w")

        for i, (name, cls, blurb) in enumerate(TOOLS):
            key = TOOL_KEYS[cls]
            row, col = divmod(i, 2)
            tile = ttk.Frame(self.frame, style="Panel.TFrame", padding=16)
            tile.grid(row=1 + row, column=col, sticky="nsew",
                      padx=(0 if col == 0 else 12, 0), pady=(0, 12))
            suit = tk.Label(tile, text=TOOL_SUITS[key], font=font("symbol", 26, "bold"))
            suit.grid(row=0, column=0, rowspan=2, sticky="n", padx=(0, 12))
            self.suit_labels.append(suit)
            ttk.Label(tile, text=name, style="PanelHeading.TLabel").grid(
                row=0, column=1, sticky="w")
            words_label = ttk.Label(tile, text=blurb, style="PanelMuted.TLabel", wraplength=320)
            words_label.grid(row=1, column=1, sticky="new", pady=(2, 10))
            wrap_to(words_label)
            ttk.Button(tile, text=f"Open {name.split()[-1]}", style="Accent.TButton",
                       command=lambda k=key: app.show_page(k)).grid(row=2, column=1, sticky="w")
            tile.columnconfigure(1, weight=1)
        for col in (0, 1):
            self.frame.columnconfigure(col, weight=1, uniform="tiles")
        for row in (1, 2):
            self.frame.rowconfigure(row, weight=1)

        footer = ttk.Frame(self.frame)
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Label(footer, text="New here? Start with How to Play.", style="Muted.TLabel").pack(
            side="left")
        ttk.Button(footer, text="How to Play", command=lambda: app.show_page("rules")).pack(
            side="left", padx=8)
        ttk.Label(footer, text=f"Suite version {__version__}", style="Muted.TLabel").pack(
            side="right")
        self.paint(themes.current())
        themes.subscribe(self.frame, self.paint)

    def paint(self, t: Theme):
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


class SettingsPage:
    """Theme, odds default and CPU cores. Applied and remembered on Save;
    Cancel (or Escape) drops unsaved choices."""

    def __init__(self, parent: tk.Misc, app: "App"):
        self.app = app
        t = themes.current()
        self.theme_var = tk.StringVar()
        self.odds_var = tk.BooleanVar()
        self.counts_var = tk.BooleanVar()
        self.cores_var = tk.StringVar()
        self.saved_var = tk.StringVar(value="")
        self.loaded: Dict[str, object] = {}
        self.reload()

        self.frame = ttk.Frame(parent, padding=24)
        self.frame.grid(row=0, column=0, sticky="nsew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        f = self.frame
        ttk.Label(f, text="Settings", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(f, text="Theme", style="TLabelframe.Label").grid(row=1, column=0, sticky="w")
        themes_box = ttk.Frame(f)
        themes_box.grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 14))
        self.swatches: List[tk.Canvas] = []
        for i, theme in enumerate(themes.THEMES):
            row, col = divmod(i, 2)
            cell = ttk.Frame(themes_box)
            cell.grid(row=row, column=col, sticky="w", padx=(0, 24), pady=3)
            swatch = tk.Canvas(cell, width=64, height=26, highlightthickness=1,
                               highlightbackground=t.edge, borderwidth=0)
            self._draw_swatch(swatch, theme)
            swatch.pack(side="left")
            swatch.bind("<Button-1>", lambda e, n=theme.name: self.theme_var.set(n))
            ttk.Radiobutton(cell, text=f"{i + 1}. {theme.name}", value=theme.name,
                            variable=self.theme_var).pack(side="left", padx=(8, 0))
            self.swatches.append(swatch)

        ttk.Label(f, text="Game pages", style="TLabelframe.Label").grid(
            row=3, column=0, sticky="w")
        switches = ttk.Frame(f)
        switches.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 14))
        ttk.Checkbutton(switches, text="Show odds by default (Ctrl+O still switches them on "
                        "a page)", variable=self.odds_var).pack(anchor="w")
        ttk.Checkbutton(switches, text="Show counts by default (Ctrl+K still switches them on "
                        "a page)", variable=self.counts_var).pack(anchor="w", pady=(2, 0))

        ttk.Label(f, text="Simulator and Optimizer", style="TLabelframe.Label").grid(
            row=5, column=0, sticky="w")
        cores = ttk.Frame(f)
        cores.grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Label(cores, text="CPU cores:").pack(side="left")
        ttk.Combobox(cores, textvariable=self.cores_var, width=8, state="readonly",
                     values=["Auto"] + [str(n) for n in range(1, cpu_count() + 1)]).pack(
            side="left", padx=(8, 8))
        ttk.Button(cores, text="Scan Now", command=self.rescan).pack(side="left")
        self.scan_label = ttk.Label(f, text="", style="Muted.TLabel", wraplength=520)
        self.scan_label.grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 16))

        buttons = ttk.Frame(f)
        buttons.grid(row=8, column=0, columnspan=2, sticky="w")
        ttk.Button(buttons, text="Save", style="Accent.TButton", command=self.save).pack(
            side="left")
        ttk.Button(buttons, text="Cancel", command=self.cancel).pack(side="left", padx=(6, 0))
        saved = ttk.Label(f, textvariable=self.saved_var, style="Muted.TLabel", wraplength=520)
        saved.grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))
        app.root.bind("<Escape>", self._escape, add="+")
        self.rescan()

    def _values(self) -> Dict[str, object]:
        cores = self.cores_var.get()
        return {"theme": self.theme_var.get(), "show_odds": bool(self.odds_var.get()),
                "show_counts": bool(self.counts_var.get()),
                "cpu_workers": "auto" if cores == "Auto" else int(cores)}

    def reload(self):
        """Show what is saved now (it may have changed on another page)."""
        current = app_settings.load()
        workers = current["cpu_workers"]
        self.theme_var.set(themes.current().name)
        self.odds_var.set(bool(current["show_odds"]))
        self.counts_var.set(bool(current["show_counts"]))
        self.cores_var.set("Auto" if workers == "auto" else str(workers))
        self.loaded = self._values()

    def on_show(self):
        self.reload()
        self.saved_var.set("")

    def cancel(self):
        """Drop unsaved choices and go back to the page you came from."""
        self.reload()
        self.saved_var.set("")
        self.app.show_page(self.app.previous or "home")

    def _escape(self, _event=None):
        if self.app.current == "settings":
            self.cancel()

    @staticmethod
    def _draw_swatch(canvas: tk.Canvas, t: Theme):
        canvas.configure(background=t.bg)
        rounded_rect(canvas, 6, 4, 26, 24, 4, fill=t.card, outline=t.card_edge)
        canvas.create_text(16, 14, text="♥", fill=t.red, font=font("symbol", 9))
        rounded_rect(canvas, 30, 4, 50, 24, 4, fill=t.back, outline=t.card_edge)
        canvas.create_oval(54, 10, 62, 18, fill=t.accent, outline="")

    def rescan(self):
        self.scan_label.config(text=f"Right now: {scan().describe()}.")

    def save(self):
        """Apply and remember only what was changed here."""
        values = self._values()
        changed = {key: value for key, value in values.items() if value != self.loaded.get(key)}
        if "theme" in changed:
            themes.set_theme(changed.pop("theme"), self.app.root)
        if changed:
            app_settings.update(**changed)
        self.loaded = values
        self.saved_var.set("Saved. The theme applies everywhere now; the odds and counts "
                           "defaults apply to game pages opened from now on.")


# --------------------------------------------------------------------------- #
# The app
# --------------------------------------------------------------------------- #

class App:
    """The whole suite in one window: sidebar on the left, pages on the right."""

    MIN_SIZE = (960, 620)
    SIDEBAR_WIDTH = (180, 236)      # narrowest and widest; set from the labels

    def __init__(self, root: tk.Misc):
        self.root = root
        self.root.title("Beat the Box")
        self.theme = themes.use(root)
        self._fit_to_screen()
        self.pages: Dict[str, object] = {}
        self.holders: Dict[str, ttk.Frame] = {}
        self.nav_buttons: Dict[str, ttk.Button] = {}
        self.current: Optional[str] = None
        self.previous: Optional[str] = None
        self.factories: Dict[str, Callable[[ttk.Frame], object]] = {
            "home": lambda holder: HomePage(holder, self),
            "player": lambda holder: PlayerGUI(holder, app=self),
            "assistant": lambda holder: AssistantGUI(holder, app=self),
            "simulator": lambda holder: SimulatorGUI(holder, app=self),
            "optimizer": lambda holder: OptimizerGUI(holder, app=self),
            "rules": lambda holder: TextPage(holder, self, "How to Play", text.RULES_SUMMARY),
            "strategy": lambda holder: TextPage(holder, self, "Strategy",
                                                text.STRATEGY_GUIDE),
            "guide": lambda holder: TextPage(holder, self, "Tool Guide", text.tool_guide()),
            "shortcuts": lambda holder: TextPage(holder, self, "Keyboard Shortcuts",
                                                 text.shortcut_help()),
            "settings": lambda holder: SettingsPage(holder, self),
        }

        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.sidebar = ttk.Frame(root, style="Sidebar.TFrame", padding=(10, 16),
                                 width=self.sidebar_width())
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.pack_propagate(False)   # same width on every page
        self.content = ttk.Frame(root)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)
        self._build_sidebar()

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        themes.subscribe(self.root, self.paint)
        self.show_page("home")

    def _fit_to_screen(self):
        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
        except tk.TclError:
            return
        width = max(self.MIN_SIZE[0], min(1360, screen_w - 60))
        height = max(self.MIN_SIZE[1], min(880, screen_h - 90))
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(*self.MIN_SIZE)

    def sidebar_width(self) -> int:
        """Wide enough for the longest label (bold, as when selected)."""
        labels = [label for _section, items in NAVIGATION for _key, label in items]
        need = max([text_width(self.root, font("ui", 11, "bold"), label) + 34
                    for label in labels]
                   + [text_width(self.root, font("ui", 15, "bold"), "Beat the Box") + 12])
        low, high = self.SIDEBAR_WIDTH
        return int(max(low, min(high, need + 20 + 8)))   # + sidebar padding + slack

    def _build_sidebar(self):
        ttk.Label(self.sidebar, text="Beat the Box", style="SidebarTitle.TLabel").pack(
            anchor="w", padx=6, pady=(0, 12))
        for heading, items in NAVIGATION:
            if heading:
                ttk.Label(self.sidebar, text=heading, style="NavHeading.TLabel").pack(
                    anchor="w", padx=6, pady=(12, 2))
            elif items[0][0] == "settings":
                ttk.Frame(self.sidebar, style="Sidebar.TFrame").pack(fill="y", expand=True)
            for key, label in items:
                button = ttk.Button(self.sidebar, text=label, style="Nav.TButton",
                                    command=lambda k=key: self.show_page(k))
                button.pack(fill="x", pady=1)
                self.nav_buttons[key] = button

    # ----- pages ---------------------------------------------------------- #

    def show_page(self, key: str):
        """Show a page (building it the first time) and return its object."""
        if key not in self.factories:
            raise KeyError(f"no page called {key!r}")
        if key not in self.pages:
            holder = ttk.Frame(self.content)
            holder.grid(row=0, column=0, sticky="nsew")
            self.holders[key] = holder
            self.pages[key] = self.factories[key](holder)
        for other, holder in self.holders.items():
            if other != key:
                holder.grid_remove()
        self.holders[key].grid()
        if key != self.current:
            self.previous = self.current
        self.current = key
        for name, button in self.nav_buttons.items():
            button.configure(style="NavActive.TButton" if name == key else "Nav.TButton")
        self.root.title(f"Beat the Box: {PAGE_TITLES[key]}" if key != "home"
                        else "Beat the Box")
        page = self.pages[key]
        on_show = getattr(page, "on_show", None)
        if on_show is not None:
            on_show()
        getattr(page, "frame", self.holders[key]).focus_set()
        return page

    def page(self, key: str):
        return self.pages.get(key)

    def launch(self, cls):
        return self.show_page(TOOL_KEYS[cls])

    def open_settings(self) -> SettingsPage:
        return self.show_page("settings")

    def paint(self, t: Theme):
        self.theme = t
        themes.paint_window(self.root, t)

    def close(self):
        for key in ("simulator", "optimizer"):
            page = self.pages.get(key)
            if page is not None:
                page.stop()
        self.root.destroy()