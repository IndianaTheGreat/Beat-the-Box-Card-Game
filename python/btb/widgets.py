"""
==============================================
CARD AND CHART WIDGETS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/widgets.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 218 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Cards drawn on a canvas, stat tiles, a bar chart and a grid of
  mini cards, all coloured by btb.theme.

DESCRIPTION:
-----------
Drawing only: these widgets show what they are told and report clicks.
They contain no rules.

  CardView  one box of the board. States: empty, live, selected, failed,
            recoverable. A failed box shows a card back; during a
            recovery (with "show failed cards" on) the failed card sits
            on the back. A strip under the card shows the box's number
            key and, when switched on, its odds.
  StatTile  a big number with a caption ("43" / "Draw pile").
  BarChart  simple labelled bars (Simulator: boxes left in wins).
  CardGrid  4 x 13 mini cards plus jokers, for picking cards (Assistant).

DEPENDENCIES:
------------
- btb.engine (Card, SUITS, RANKS), btb.theme
- Standard library: tkinter, typing

KEY FUNCTIONS:
-------------
- rounded_rect(canvas, x1, y1, x2, y2, r, **options) -> canvas item
- CardView.show(card, state, ghost, footer_left, footer_right)
- CardView.describe() -> "A♥", "Failed" or "Failed\\nK♥" (tests, screen readers)
- StatTile(parent, caption, variable)
- BarChart.draw(items, value_format)
- CardGrid(parent, theme, on_pick, jokers).set_available / set_selected

NOTES:
-----
- Jokers are drawn as a star and the word JOKER, so they never depend on
  the emoji font.
- Text turned upside down (the bottom corner of a card) needs Tk 8.6; on
  an older Tk the corner is simply drawn upright.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import theme as themes
from .engine import RANKS, SUITS, Card
from .theme import Theme, font

RED_SUITS = ("♥", "♦")
CARD_STATES = ("empty", "live", "selected", "failed", "recoverable")


def card_name(card: Card) -> str:
    """Readable label: "A♥", or "Joker" instead of the emoji."""
    return "Joker" if card.is_joker else card.label()


def suit_color(card: Card, t: Theme) -> str:
    if card.is_joker:
        return t.joker_ink
    return t.red if card.suit in RED_SUITS else t.black


def readable_on(color: str) -> str:
    """Black or white, whichever reads better on `color`."""
    dark, light = "#111111", "#ffffff"
    return dark if themes.contrast(dark, color) >= themes.contrast(light, color) else light


def rounded_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float,
                 r: float = 10, **options) -> int:
    points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
              x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(points, smooth=True, splinesteps=12, **options)


def _text(canvas: tk.Canvas, x: float, y: float, upside_down: bool = False, **options) -> int:
    if upside_down:
        try:
            return canvas.create_text(x, y, angle=180, **options)
        except tk.TclError:
            pass
    return canvas.create_text(x, y, **options)


# --------------------------------------------------------------- CardView -- #

class CardView:
    """One box of the board, drawn on its own canvas."""

    MARGIN = 7
    FOOTER = 20

    def __init__(self, parent: tk.Misc, theme: Theme, width: int = 96, height: int = 128,
                 command: Optional[Callable[[], None]] = None):
        self.theme = theme
        self.width, self.height = width, height
        self.command = command
        self.card: Optional[Card] = None
        self.ghost: Optional[Card] = None
        self.state = "empty"
        self.footer_left = ""
        self.footer_right = ""
        self.hover = False
        m = self.MARGIN
        self.canvas = tk.Canvas(parent, width=width + 2 * m, height=height + 2 * m + self.FOOTER,
                                highlightthickness=0, borderwidth=0, background=theme.bg)
        self.canvas.bind("<Button-1>", self._clicked)
        self.canvas.bind("<Enter>", lambda e: self._set_hover(True))
        self.canvas.bind("<Leave>", lambda e: self._set_hover(False))
        self.redraw()

    # geometry managers pass straight through to the canvas
    def grid(self, **options) -> None:
        self.canvas.grid(**options)

    def pack(self, **options) -> None:
        self.canvas.pack(**options)

    def show(self, card: Optional[Card], state: str, ghost: Optional[Card] = None,
             footer_left: str = "", footer_right: str = "") -> None:
        if state not in CARD_STATES:
            raise ValueError(f"unknown card state {state!r}")
        new = (card, state, ghost, footer_left, footer_right)
        if new == (self.card, self.state, self.ghost, self.footer_left, self.footer_right):
            return
        self.card, self.state, self.ghost, self.footer_left, self.footer_right = new
        self.redraw()

    def describe(self) -> str:
        if self.state in ("live", "selected") and self.card is not None:
            return self.card.label()
        if self.state in ("failed", "recoverable"):
            return f"Failed\n{self.ghost}" if self.ghost else "Failed"
        return ""

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.redraw()

    def _clicked(self, _event) -> None:
        if self.command:
            self.command()

    def _set_hover(self, on: bool) -> None:
        if self.hover != on:
            self.hover = on
            self.redraw()

    # ----- drawing -------------------------------------------------------- #

    def redraw(self) -> None:
        c, t = self.canvas, self.theme
        c.delete("all")
        c.configure(background=t.bg)
        m, w, h = self.MARGIN, self.width, self.height
        x1, y1, x2, y2 = m, m, m + w, m + h
        clickable = self.state in ("live", "selected", "recoverable")
        c.configure(cursor="hand2" if clickable else "")

        if self.state == "empty":
            rounded_rect(c, x1, y1, x2, y2, 10, fill="", outline=t.edge, width=2, dash=(5, 4))
        else:
            lift = 3 if self.state == "selected" else 0
            rounded_rect(c, x1 + 3, y1 + 4, x2 + 3, y2 + 4, 10, fill=t.shadow, outline="")
            if self.state in ("live", "selected") and self.card is not None:
                self._face(x1, y1 - lift, x2, y2 - lift, self.card)
            else:
                self._back(x1, y1, x2, y2)
            if self.state == "selected":
                rounded_rect(c, x1 - 3, y1 - lift - 3, x2 + 3, y2 - lift + 3, 12,
                             fill="", outline=t.select, width=4)
            elif self.state == "recoverable":
                rounded_rect(c, x1 - 3, y1 - 3, x2 + 3, y2 + 3, 12,
                             fill="", outline=t.recover, width=4)
            elif self.hover and clickable:
                rounded_rect(c, x1 - 2, y1 - 2, x2 + 2, y2 + 2, 11,
                             fill="", outline=t.select, width=2)

        fy = y2 + m + self.FOOTER / 2 - 2
        if self.footer_left:
            c.create_text(x1 + 2, fy, text=self.footer_left, anchor="w",
                          font=font("ui", 9, "bold"), fill=t.muted)
        if self.footer_right:
            color = t.recover if self.state == "recoverable" else t.text
            c.create_text(x2, fy, text=self.footer_right, anchor="e",
                          font=font("ui", 8), fill=color)

    def _face(self, x1: float, y1: float, x2: float, y2: float, card: Card) -> None:
        c, t = self.canvas, self.theme
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if card.is_joker:
            rounded_rect(c, x1, y1, x2, y2, 10, fill=t.joker, outline=t.card_edge, width=1)
            c.create_text(cx, cy - 10, text="★", font=font("symbol", 36), fill=t.joker_ink)
            c.create_text(cx, cy + 26, text="JOKER", font=font("ui", 10, "bold"), fill=t.joker_ink)
            c.create_text(x1 + 13, y1 + 15, text="★", font=font("symbol", 11), fill=t.joker_ink)
            _text(c, x2 - 13, y2 - 15, True, text="★", font=font("symbol", 11), fill=t.joker_ink)
            return
        rounded_rect(c, x1, y1, x2, y2, 10, fill=t.card, outline=t.card_edge, width=1)
        color = suit_color(card, t)
        rank = card.rank_label
        rank_font = font("card", 14 if len(rank) > 1 else 15, "bold")
        c.create_text(x1 + 14, y1 + 15, text=rank, font=rank_font, fill=color)
        c.create_text(x1 + 14, y1 + 33, text=card.suit, font=font("symbol", 12), fill=color)
        _text(c, x2 - 14, y2 - 15, True, text=rank, font=rank_font, fill=color)
        _text(c, x2 - 14, y2 - 33, True, text=card.suit, font=font("symbol", 12), fill=color)
        c.create_text(cx, cy, text=card.suit, font=font("symbol", 38), fill=color)

    def _back(self, x1: float, y1: float, x2: float, y2: float) -> None:
        c, t = self.canvas, self.theme
        rounded_rect(c, x1, y1, x2, y2, 10, fill=t.back, outline=t.card_edge, width=1)
        ix1, iy1, ix2, iy2 = x1 + 7, y1 + 7, x2 - 7, y2 - 7
        rounded_rect(c, ix1, iy1, ix2, iy2, 6, fill="", outline=t.back_line, width=1)
        # Diamond lattice, clipped to the inner border by hand.
        step = 12
        for offset in range(int(-(iy2 - iy1)), int(ix2 - ix1) + step, step):
            # lines going down-right: x - ix1 = (y - iy1) + offset
            sx = max(ix1, ix1 + offset)
            ex = min(ix2, ix1 + offset + (iy2 - iy1))
            if ex > sx:
                c.create_line(sx, iy1 + (sx - ix1 - offset), ex, iy1 + (ex - ix1 - offset),
                              fill=t.back_line)
            # lines going down-left (mirror image)
            sx2, ex2 = ix2 - (ex - ix1), ix2 - (sx - ix1)
            if ex > sx:
                c.create_line(ex2, iy1 + (sx - ix1 - offset), sx2, iy1 + (ex - ix1 - offset),
                              fill=t.back_line)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        if self.ghost is not None:
            rounded_rect(c, cx - 30, cy - 22, cx + 30, cy + 22, 6, fill=t.card,
                         outline=t.card_edge)
            c.create_text(cx, cy, text=card_name(self.ghost) if self.ghost.is_joker
                          else self.ghost.label(), font=font("card", 15, "bold"),
                          fill=suit_color(self.ghost, t))
        else:
            rounded_rect(c, cx - 32, cy - 12, cx + 32, cy + 12, 6, fill=t.back,
                         outline=t.back_line)
            c.create_text(cx, cy, text="FAILED", font=font("ui", 9, "bold"),
                          fill=readable_on(t.back))


# --------------------------------------------------------------- StatTile -- #

class StatTile(ttk.Frame):
    """A big value over a small caption."""

    def __init__(self, parent: tk.Misc, caption: str, variable: tk.Variable, **kwargs):
        super().__init__(parent, style="Panel.TFrame", padding=(12, 8), **kwargs)
        ttk.Label(self, textvariable=variable, style="TileValue.TLabel").pack(anchor="w")
        self.caption = ttk.Label(self, text=caption, style="PanelMuted.TLabel")
        self.caption.pack(anchor="w")


# --------------------------------------------------------------- BarChart -- #

class BarChart:
    """Labelled vertical bars. Redraws itself when the theme changes."""

    def __init__(self, parent: tk.Misc, theme: Theme, width: int = 380, height: int = 170,
                 title: str = ""):
        self.theme = theme
        self.width, self.height, self.title = width, height, title
        self.items: List[Tuple[str, float]] = []
        self.value_format: Callable[[float], str] = lambda v: f"{v:.0f}%"
        self.canvas = tk.Canvas(parent, width=width, height=height, highlightthickness=0,
                                borderwidth=0, background=theme.panel)
        self.redraw()

    def grid(self, **options) -> None:
        self.canvas.grid(**options)

    def pack(self, **options) -> None:
        self.canvas.pack(**options)

    def draw(self, items: Sequence[Tuple[str, float]],
             value_format: Optional[Callable[[float], str]] = None) -> None:
        self.items = list(items)
        if value_format:
            self.value_format = value_format
        self.redraw()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.redraw()

    def redraw(self) -> None:
        c, t = self.canvas, self.theme
        c.delete("all")
        c.configure(background=t.panel)
        c.create_text(12, 12, text=self.title, anchor="nw", font=font("ui", 10, "bold"),
                      fill=t.muted)
        if not self.items:
            c.create_text(self.width / 2, self.height / 2, text="Run a simulation to see this",
                          font=font("ui", 9), fill=t.muted)
            return
        left, right, top, bottom = 14, self.width - 14, 40, self.height - 24
        top_value = max(v for _, v in self.items) or 1
        slot = (right - left) / len(self.items)
        bar = max(4, slot * 0.62)
        c.create_line(left, bottom, right, bottom, fill=t.edge)
        for i, (label, value) in enumerate(self.items):
            cx = left + slot * (i + 0.5)
            height = (bottom - top) * value / top_value
            if value > 0:
                c.create_rectangle(cx - bar / 2, bottom - height, cx + bar / 2, bottom,
                                   fill=t.chart, outline="")
                c.create_text(cx, bottom - height - 8, text=self.value_format(value),
                              font=font("ui", 8), fill=t.text)
            c.create_text(cx, bottom + 11, text=label, font=font("ui", 9), fill=t.muted)


# --------------------------------------------------------------- CardGrid -- #

class CardGrid(ttk.Frame):
    """Mini cards in four suit rows, plus a row of joker buttons.

    on_pick(card, button) is called on a click. `buttons` lists every
    (card, button) pair, one button per physical joker.
    """

    def __init__(self, parent: tk.Misc, theme: Theme,
                 on_pick: Callable[[Card, tk.Button], None], jokers: int = 0,
                 style: str = "TFrame"):
        super().__init__(parent, style=style)
        self.theme = theme
        self.on_pick = on_pick
        self.selected: Optional[str] = None
        self.buttons: List[Tuple[Card, tk.Button]] = []
        for row, suit in enumerate(SUITS):
            for col, rank in enumerate(reversed(RANKS)):  # A K Q ... 2
                self._add(Card(rank, suit), row, col)
        for i in range(jokers):
            self._add(Card.joker(), len(SUITS), i * 2, columnspan=2)
        self.set_theme(theme)

    def _add(self, card: Card, row: int, col: int, columnspan: int = 1) -> None:
        text = "Joker" if card.is_joker else card.label()
        button = tk.Button(self, text=text, width=6 if card.is_joker else 3, relief="flat",
                           borderwidth=0, padx=2, pady=2, cursor="hand2",
                           font=font("card", 10, "bold"))
        button.configure(command=lambda c=card, b=button: self.on_pick(c, b))
        button.grid(row=row, column=col, columnspan=columnspan, padx=1, pady=1, sticky="ew")
        self.buttons.append((card, button))

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        for card, button in self.buttons:
            self._paint(card, button)

    def _paint(self, card: Card, button: tk.Button) -> None:
        t = self.theme
        chosen = self.selected is not None and card.label() == self.selected
        bg = t.select if chosen else (t.joker if card.is_joker else t.card)
        fg = readable_on(t.select) if chosen else suit_color(card, t)
        button.configure(background=bg, foreground=fg,
                         activebackground=t.select if chosen else t.card_edge,
                         activeforeground=fg, disabledforeground=t.muted,
                         highlightthickness=0)
        if str(button.cget("state")) == "disabled":
            button.configure(background=t.panel)

    def set_available(self, labels: Iterable[str]) -> None:
        """Enable only cards whose label is in `labels` (others are gone)."""
        labels = set(labels)
        for card, button in self.buttons:
            button.configure(state="normal" if card.label() in labels else "disabled")
            self._paint(card, button)

    def set_selected(self, label: Optional[str]) -> None:
        self.selected = label or None
        for card, button in self.buttons:
            self._paint(card, button)

    def disable(self, button: tk.Button) -> None:
        button.configure(state="disabled")
        for card, b in self.buttons:
            if b is button:
                self._paint(card, b)

    def enable(self, button: tk.Button) -> None:
        button.configure(state="normal")
        for card, b in self.buttons:
            if b is button:
                self._paint(card, b)