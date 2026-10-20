"""
==============================================
THEMES AND STYLING
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/theme.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 218 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Eight numbered colour themes, the fonts, and the ttk styling every
  window uses. The chosen theme is remembered (btb.settings) and can be
  switched live from Settings or View > Theme.

DESCRIPTION:
-----------
All colours live here, so the windows contain no colour codes of their
own. Each theme is one Theme(...) block in THEMES. To change the default,
edit DEFAULT_THEME (a name or a number from the list). To add a theme,
copy a block, give it a new name and change the colours; it shows up in
Settings and View > Theme automatically. The tests check every theme for
readable contrast.

    1 Felt Green     2 Royal Blue     3 Casino Red     4 Classic Light
    5 Midnight       6 Slate          7 Parchment      8 High Contrast

Pure Tkinter: the ttk "clam" theme plus our colours. Nothing is copied
from other projects.

DEPENDENCIES:
------------
- btb.settings
- Standard library: tkinter, tkinter.font, dataclasses, typing

KEY FUNCTIONS:
-------------
- THEMES, DEFAULT_THEME, theme_names(), get(name_or_number)
- current() -> the active Theme (from settings, else the default)
- use(root) -> styles a window with the active theme, returns it
- set_theme(name, root, save=True) -> switch live and remember
- subscribe(widget, callback) -> callback(theme) on every switch
- font(kind, size, weight) -> font tuple; kind is ui, card, symbol or mono
- style_text_widget(widget, theme) -> colours a tk Text or Listbox
- repaint(text_widgets, windows, theme) -> recolours open help windows and
  forgets closed ones
- alive(widget) -> True while a widget still exists
- contrast(a, b) -> WCAG contrast ratio of two colours (used by tests)

NOTES:
-----
- ttk styles belong to the whole application, so switching restyles every
  open window at once. Plain tk widgets (canvas cards, banners, lists) are
  recoloured through subscribe().
- Fonts are picked from what is installed: Segoe UI on Windows, the system
  font on macOS, DejaVu/Ubuntu on Linux.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, fields
from tkinter import font as tkfont
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Tuple, Union

from . import settings


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str             # window background (the table)
    panel: str          # tiles, side panels, tables
    edge: str           # panel borders
    text: str           # main text on bg and panel
    muted: str          # secondary text
    card: str           # card face
    card_edge: str
    shadow: str         # shadow under a card
    back: str           # card back (failed box)
    back_line: str      # pattern on the card back
    red: str            # hearts, diamonds
    black: str          # spades, clubs
    joker: str          # joker face
    joker_ink: str
    select: str         # selected box outline
    recover: str        # recoverable box glow, recovery banner
    good: str           # correct call banner
    bad: str            # wrong call banner
    banner_text: str    # text on the good / bad / recover banners
    button: str
    button_hover: str
    button_text: str
    accent: str         # main buttons (New Game, Run, inclusive calls)
    accent_hover: str
    accent_text: str
    field: str          # entry and combobox background
    field_text: str
    chart: str          # bars in charts


COLOR_FIELDS = tuple(f.name for f in fields(Theme) if f.name != "name")

THEMES: List[Theme] = [
    Theme("Felt Green",
          bg="#155e35", panel="#0f4528", edge="#2a7a4b", text="#f3f7f0", muted="#b9d6c2",
          card="#fbf8ef", card_edge="#cfc8b4", shadow="#0b3520",
          back="#8c2323", back_line="#b04545", red="#b42318", black="#1c1c1c",
          joker="#efe7ff", joker_ink="#5b21b6", select="#4cc3ff", recover="#f5b82e",
          good="#1f8a4c", bad="#b42318", banner_text="#ffffff",
          button="#2a7a4b", button_hover="#33915a", button_text="#ffffff",
          accent="#e8c15a", accent_hover="#f2d27c", accent_text="#1b1b1b",
          field="#fbf8ef", field_text="#1c1c1c", chart="#e8c15a"),
    Theme("Royal Blue",
          bg="#1d3b7a", panel="#152c5e", edge="#3657a3", text="#eef2ff", muted="#bccaf0",
          card="#fbfbf7", card_edge="#c9ccd6", shadow="#0f2148",
          back="#9a3412", back_line="#c2541f", red="#b91c1c", black="#111827",
          joker="#ede9fe", joker_ink="#5b21b6", select="#67e8f9", recover="#fbbf24",
          good="#15803d", bad="#b91c1c", banner_text="#ffffff",
          button="#3657a3", button_hover="#4468bb", button_text="#ffffff",
          accent="#fbbf24", accent_hover="#fcd34d", accent_text="#1b1b1b",
          field="#fbfbf7", field_text="#111827", chart="#fbbf24"),
    Theme("Casino Red",
          bg="#7a1c1c", panel="#5e1414", edge="#a03636", text="#fff3f0", muted="#efc2bb",
          card="#fdf9f1", card_edge="#d6ccb8", shadow="#4a0f0f",
          back="#1e3a8a", back_line="#3b5cc4", red="#b42318", black="#1c1c1c",
          joker="#f3e8ff", joker_ink="#6b21a8", select="#7dd3fc", recover="#facc15",
          good="#15803d", bad="#9f1239", banner_text="#ffffff",
          button="#a03636", button_hover="#b84848", button_text="#ffffff",
          accent="#facc15", accent_hover="#fde047", accent_text="#1b1b1b",
          field="#fdf9f1", field_text="#1c1c1c", chart="#facc15"),
    Theme("Classic Light",
          bg="#eef0f3", panel="#ffffff", edge="#cfd4dc", text="#111827", muted="#4b5563",
          card="#ffffff", card_edge="#9ca3af", shadow="#c7ccd4",
          back="#1d4ed8", back_line="#4f7ef0", red="#b91c1c", black="#111827",
          joker="#ede9fe", joker_ink="#5b21b6", select="#2563eb", recover="#d97706",
          good="#15803d", bad="#b91c1c", banner_text="#ffffff",
          button="#e2e6ec", button_hover="#d3d9e2", button_text="#111827",
          accent="#2563eb", accent_hover="#1d4ed8", accent_text="#ffffff",
          field="#ffffff", field_text="#111827", chart="#2563eb"),
    Theme("Midnight",
          bg="#0f172a", panel="#1e293b", edge="#334155", text="#e2e8f0", muted="#94a3b8",
          card="#f8fafc", card_edge="#94a3b8", shadow="#020617",
          back="#4338ca", back_line="#6366f1", red="#be123c", black="#0f172a",
          joker="#ede9fe", joker_ink="#6d28d9", select="#38bdf8", recover="#f59e0b",
          good="#15803d", bad="#be123c", banner_text="#ffffff",
          button="#334155", button_hover="#475569", button_text="#f1f5f9",
          accent="#38bdf8", accent_hover="#7dd3fc", accent_text="#0f172a",
          field="#0b1220", field_text="#e2e8f0", chart="#38bdf8"),
    Theme("Slate",
          bg="#3a4150", panel="#2b313c", edge="#525b6b", text="#f3f4f6", muted="#c3c8d2",
          card="#f9fafb", card_edge="#9ca3af", shadow="#1f242c",
          back="#0f766e", back_line="#2a9d8f", red="#b91c1c", black="#111827",
          joker="#ede9fe", joker_ink="#5b21b6", select="#5eead4", recover="#fbbf24",
          good="#15803d", bad="#b91c1c", banner_text="#ffffff",
          button="#525b6b", button_hover="#616b7d", button_text="#ffffff",
          accent="#5eead4", accent_hover="#99f6e4", accent_text="#0f1a1a",
          field="#f9fafb", field_text="#111827", chart="#5eead4"),
    Theme("Parchment",
          bg="#eadfc8", panel="#f7f0e1", edge="#cbb994", text="#3a2e1d", muted="#6b5a3e",
          card="#fffdf7", card_edge="#b8a77f", shadow="#cbbd9c",
          back="#6b3f1d", back_line="#8f5a2e", red="#a61b1b", black="#2a2116",
          joker="#f1e8ff", joker_ink="#5b2a86", select="#1d6fa5", recover="#b7791f",
          good="#2f6b2f", bad="#a61b1b", banner_text="#ffffff",
          button="#ddd0b3", button_hover="#d2c29f", button_text="#3a2e1d",
          accent="#6b3f1d", accent_hover="#7d4d27", accent_text="#fffdf7",
          field="#fffdf7", field_text="#2a2116", chart="#8f5a2e"),
    Theme("High Contrast",
          bg="#000000", panel="#111111", edge="#ffffff", text="#ffffff", muted="#e0e0e0",
          card="#ffffff", card_edge="#000000", shadow="#444444",
          back="#003cff", back_line="#7a9bff", red="#c00000", black="#000000",
          joker="#ffffff", joker_ink="#6a00ff", select="#00e5ff", recover="#ffd600",
          good="#00a83e", bad="#d10000", banner_text="#ffffff",
          button="#ffffff", button_hover="#ffd600", button_text="#000000",
          accent="#ffd600", accent_hover="#ffe866", accent_text="#000000",
          field="#000000", field_text="#ffffff", chart="#ffd600"),
]

DEFAULT_THEME: Union[str, int] = "Felt Green"   # a name, or a number 1-8

_current: Optional[Theme] = None
_listeners: List[Tuple[tk.Misc, Callable[[Theme], None]]] = []
_families: Dict[str, str] = {}

_FONT_CANDIDATES = {
    "ui": ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Ubuntu", "Noto Sans",
           "DejaVu Sans", "Helvetica", "Arial"),
    "card": ("Georgia", "Cambria", "Noto Serif", "DejaVu Serif", "Times New Roman",
             "Times"),
    "symbol": ("Segoe UI Symbol", "Apple Symbols", "DejaVu Sans", "Noto Sans Symbols2",
               "Arial Unicode MS"),
    "mono": ("Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New",
             "Courier"),
}


# --------------------------------------------------------------- lookups -- #

def theme_names() -> List[str]:
    return [t.name for t in THEMES]


def get(name: Union[str, int, None]) -> Theme:
    """A theme by name or by its number (1 = first). Unknown -> the default."""
    if isinstance(name, int) and not isinstance(name, bool):
        if 1 <= name <= len(THEMES):
            return THEMES[name - 1]
    elif isinstance(name, str):
        for t in THEMES:
            if t.name.lower() == name.strip().lower():
                return t
    if name is not DEFAULT_THEME:
        return get(DEFAULT_THEME)
    return THEMES[0]


def current() -> Theme:
    global _current
    if _current is None:
        _current = get(settings.get("theme"))
    return _current


# ----------------------------------------------------------------- fonts -- #

def _pick_families(root: tk.Misc) -> None:
    if _families:
        return
    try:
        installed = {f.lower(): f for f in tkfont.families(root)}
    except tk.TclError:
        installed = {}
    for kind, candidates in _FONT_CANDIDATES.items():
        _families[kind] = next((installed[c.lower()] for c in candidates
                                if c.lower() in installed), "TkDefaultFont")


def font(kind: str = "ui", size: int = 10, weight: str = "normal") -> tuple:
    family = _families.get(kind) or _families.get("ui") or "TkDefaultFont"
    return (family, size, weight)


# --------------------------------------------------------------- styling -- #

def _apply_style(root: tk.Misc, t: Theme) -> None:
    _pick_families(root)
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    ui = font("ui", 10)
    style.configure(".", background=t.bg, foreground=t.text, font=ui,
                    bordercolor=t.edge, lightcolor=t.panel, darkcolor=t.panel,
                    troughcolor=t.panel, fieldbackground=t.field,
                    selectbackground=t.accent, selectforeground=t.accent_text,
                    insertcolor=t.field_text, focuscolor=t.select)
    style.configure("TFrame", background=t.bg)
    style.configure("Panel.TFrame", background=t.panel, relief="flat")
    style.configure("TLabel", background=t.bg, foreground=t.text)
    style.configure("Muted.TLabel", background=t.bg, foreground=t.muted)
    style.configure("Title.TLabel", background=t.bg, foreground=t.text,
                    font=font("ui", 20, "bold"))
    style.configure("Heading.TLabel", background=t.bg, foreground=t.text,
                    font=font("ui", 13, "bold"))
    style.configure("Panel.TLabel", background=t.panel, foreground=t.text)
    style.configure("PanelMuted.TLabel", background=t.panel, foreground=t.muted,
                    font=font("ui", 9))
    style.configure("PanelHeading.TLabel", background=t.panel, foreground=t.text,
                    font=font("ui", 11, "bold"))
    style.configure("TileValue.TLabel", background=t.panel, foreground=t.text,
                    font=font("ui", 17, "bold"))
    style.configure("TLabelframe", background=t.bg, bordercolor=t.edge,
                    lightcolor=t.bg, darkcolor=t.bg)
    style.configure("TLabelframe.Label", background=t.bg, foreground=t.muted,
                    font=font("ui", 10, "bold"))
    style.configure("Panel.TLabelframe", background=t.panel, bordercolor=t.edge,
                    lightcolor=t.panel, darkcolor=t.panel)
    style.configure("Panel.TLabelframe.Label", background=t.panel, foreground=t.muted,
                    font=font("ui", 10, "bold"))

    for name, bg, hover, fg, size, weight, pad in (
            ("TButton", t.button, t.button_hover, t.button_text, 10, "normal", (10, 5)),
            ("Accent.TButton", t.accent, t.accent_hover, t.accent_text, 10, "bold", (12, 5)),
            ("Call.TButton", t.button, t.button_hover, t.button_text, 12, "bold", (12, 9)),
            ("CallAccent.TButton", t.accent, t.accent_hover, t.accent_text, 12, "bold", (12, 9))):
        style.configure(name, background=bg, foreground=fg, bordercolor=t.edge,
                        lightcolor=bg, darkcolor=bg, padding=pad,
                        font=font("ui", size, weight), focuscolor=fg, anchor="center")
        style.map(name,
                  background=[("disabled", t.panel), ("pressed", hover), ("active", hover)],
                  lightcolor=[("disabled", t.panel), ("active", hover)],
                  darkcolor=[("disabled", t.panel), ("active", hover)],
                  foreground=[("disabled", t.muted)])

    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=t.field, foreground=t.field_text,
                        background=t.button, arrowcolor=t.button_text,
                        bordercolor=t.edge, lightcolor=t.field, darkcolor=t.field,
                        insertcolor=t.field_text, padding=3)
        style.map(name, fieldbackground=[("readonly", t.field), ("disabled", t.panel)],
                  foreground=[("readonly", t.field_text), ("disabled", t.muted)],
                  background=[("active", t.button_hover)])
    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(name, background=t.bg, foreground=t.text,
                        indicatorbackground=t.field, indicatorforeground=t.field_text,
                        upperbordercolor=t.edge, lowerbordercolor=t.edge)
        style.map(name, background=[("active", t.bg)],
                  indicatorbackground=[("selected", t.accent), ("pressed", t.accent)],
                  indicatorforeground=[("selected", t.accent_text)])
        style.configure("Panel." + name, background=t.panel, foreground=t.text,
                        indicatorbackground=t.field, indicatorforeground=t.field_text)
        style.map("Panel." + name, background=[("active", t.panel)],
                  indicatorbackground=[("selected", t.accent)],
                  indicatorforeground=[("selected", t.accent_text)])

    style.configure("Treeview", background=t.panel, fieldbackground=t.panel,
                    foreground=t.text, bordercolor=t.edge, rowheight=24, font=ui)
    style.map("Treeview", background=[("selected", t.accent)],
              foreground=[("selected", t.accent_text)])
    style.configure("Treeview.Heading", background=t.button, foreground=t.button_text,
                    bordercolor=t.edge, lightcolor=t.button, darkcolor=t.button,
                    font=font("ui", 10, "bold"))
    style.map("Treeview.Heading", background=[("active", t.button_hover)])
    style.configure("Horizontal.TProgressbar", background=t.accent, troughcolor=t.panel,
                    bordercolor=t.edge, lightcolor=t.accent, darkcolor=t.accent)
    style.configure("TScrollbar", background=t.button, troughcolor=t.panel,
                    bordercolor=t.edge, arrowcolor=t.button_text,
                    lightcolor=t.button, darkcolor=t.button)
    style.map("TScrollbar", background=[("active", t.button_hover)])
    style.configure("TSeparator", background=t.edge)

    # Combobox drop-down lists are plain Tk listboxes.
    root.option_add("*TCombobox*Listbox.background", t.field)
    root.option_add("*TCombobox*Listbox.foreground", t.field_text)
    root.option_add("*TCombobox*Listbox.selectBackground", t.accent)
    root.option_add("*TCombobox*Listbox.selectForeground", t.accent_text)


def paint_window(window: tk.Misc, t: Theme) -> None:
    """Background of a Tk or Toplevel window (not a ttk widget)."""
    try:
        window.configure(background=t.bg)
    except tk.TclError:
        pass


def style_text_widget(widget: tk.Misc, t: Theme) -> None:
    """Colours for a plain tk Text or Listbox."""
    options = dict(background=t.panel, foreground=t.text, highlightthickness=1,
                   highlightbackground=t.edge, highlightcolor=t.select,
                   selectbackground=t.accent, selectforeground=t.accent_text,
                   relief="flat", borderwidth=0)
    if isinstance(widget, tk.Text):
        options["insertbackground"] = t.text
    try:
        widget.configure(**options)
    except tk.TclError:
        pass


def use(root: tk.Misc) -> Theme:
    """Style a new window with the active theme and return it."""
    t = current()
    _apply_style(root, t)
    paint_window(root, t)
    return t


def repaint(text_widgets: List[tk.Misc], windows: List[tk.Misc], t: Theme) -> None:
    """Recolour open text widgets and windows; drop the ones that were closed."""
    for collection, paint in ((text_widgets, style_text_widget), (windows, paint_window)):
        for widget in list(collection):
            if alive(widget):
                paint(widget, t)
            else:
                collection.remove(widget)


def subscribe(widget: tk.Misc, callback: Callable[[Theme], None]) -> None:
    """Call callback(theme) whenever the theme changes, while widget exists."""
    _listeners.append((widget, callback))


def alive(widget: tk.Misc) -> bool:
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


def set_theme(name: Union[str, int], root: tk.Misc, save: bool = True) -> Theme:
    """Switch every open window to another theme (and remember it)."""
    global _current
    _current = get(name)
    _apply_style(root, _current)
    if save:
        settings.update(theme=_current.name)
    for widget, callback in list(_listeners):
        if alive(widget):
            callback(_current)
        else:
            _listeners.remove((widget, callback))
    return _current


def reset() -> None:
    """Forget the active theme so it is read from settings again (tests)."""
    global _current
    _current = None
    _listeners.clear()


# -------------------------------------------------------------- contrast -- #

def _luminance(color: str) -> float:
    color = color.lstrip("#")
    channels = [int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio, 1.0 (none) to 21.0 (black on white)."""
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)