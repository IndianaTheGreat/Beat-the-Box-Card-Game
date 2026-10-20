"""
==============================================
CARD AND CHART WIDGETS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/widgets.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 254 passed)

VERSION 1.1 CHANGES (2026-10-20):
- Resizable: CardView fills whatever space the window gives it, keeping a
  playing card's shape, with fonts scaled to the card (CardView.fit).
  BarChart redraws at its new size.
- A narrow card drops its box number rather than overlap the odds, and a
  card re-centres when only the width of its space changes.
- New ScrollFrame: a panel whose contents scroll when the window is too
  short for them (the scrollbar only shows when needed).
- New AutoScrollbar and scrolled_tree(): tables get a sideways scrollbar
  that only shows when the window is too narrow for every column.
- StatTile shrinks its number to fit a narrow tile and wraps its caption.
- CardGrid shrinks its mini cards to fit the space it is given, and has a
  free slot beside the joker buttons (CardGrid.beside_jokers).
- New wrap_to(label): wrap a label to the width it is given; flow_row:
  a row of controls that wraps onto more rows when narrow;
  notify_resized(widget): tell the ScrollFrame around a widget to re-check.

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
  StatTile  a big number with a caption ("43" / "Draw pile"); the number
            shrinks to fit a narrow tile.
  BarChart  simple labelled bars (Simulator: boxes left in wins).
  CardGrid  4 x 13 mini cards plus jokers, for picking cards (Assistant);
            the cards shrink to fit the width they are given.
  ScrollFrame    a panel that scrolls up and down when it doesn't fit.
  AutoScrollbar  a scrollbar that hides when everything fits.

DEPENDENCIES:
------------
- btb.engine (Card, SUITS, RANKS), btb.theme
- Standard library: tkinter, typing

KEY FUNCTIONS:
-------------
- rounded_rect(canvas, x1, y1, x2, y2, r, **options) -> canvas item
- CardView.show(card, state, ghost, footer_left, footer_right)
- CardView.describe() -> "A♥", "Failed" or "Failed\\nK♥" (tests, screen readers)
- CardView.fit(width, height) -> size the card to a canvas (called on resize)
- text_width(widget, font, text) -> pixels a piece of text needs
- StatTile(parent, caption, variable)
- BarChart.draw(items, value_format)
- CardGrid(parent, theme, on_pick, jokers).set_available / set_selected /
  fit(width) / beside_jokers(widget)
- ScrollFrame(parent, width).body / set_width(width) / update_layout()
- scrolled_tree(parent, columns, height) -> Treeview with scrollbars
- wrap_to(label) -> keep a label wrapped to the width it is given
- flow_row(frame, children) -> a row of controls that wraps when narrow
- notify_resized(widget) -> tell its ScrollFrame to re-check its height

NOTES:
-----
- Jokers are drawn as a star and the word JOKER, so they never depend on
  the emoji font.
- Text turned upside down (the bottom corner of a card) needs Tk 8.6; on
  an older Tk the corner is simply drawn upright.
- ScrollFrame: when its contents are shorter than the space, the body is
  stretched to fill it (so a list at the bottom can grow); when they are
  taller, a scrollbar appears and the mouse wheel scrolls it. Call
  update_layout() after showing or hiding parts of the body; it re-checks
  over a few idle rounds, because a size change inside nested frames
  reaches the body one frame at a time.
- Layout handlers only change something when the value really changes,
  and wrapped labels use width=1 + fill, so a resize can't feed itself.
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


def text_width(widget: tk.Misc, font_spec: tuple, text: str) -> int:
    """Width in pixels of `text` in `font_spec` (no font objects to manage)."""
    try:
        return int(widget.tk.call("font", "measure", font_spec, text))
    except tk.TclError:
        return 0


def wrap_length(label: tk.Misc) -> int:
    """A label's current wraplength in pixels (0 = no wrapping)."""
    try:
        return int(float(str(label.cget("wraplength")) or 0))
    except (tk.TclError, ValueError):
        return 0


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
    """One box of the board, drawn on its own canvas.

    The canvas can be any size (it follows the window); the card is drawn as
    large as fits, keeping a playing card's shape, with every font scaled to
    the card's height.
    """

    MARGIN = 7
    FOOTER = 20
    ASPECT = 0.75          # card width / height
    MIN_HEIGHT = 60

    def __init__(self, parent: tk.Misc, theme: Theme, width: int = 96, height: int = 128,
                 command: Optional[Callable[[], None]] = None):
        self.theme = theme
        self.width, self.height = width, height        # size of the card itself
        self.command = command
        self.card: Optional[Card] = None
        self.ghost: Optional[Card] = None
        self.state = "empty"
        self.footer_left = ""
        self.footer_right = ""
        self.hover = False
        self._canvas_width = 0                          # last width fit() was given
        m = self.MARGIN
        self.canvas = tk.Canvas(parent, width=width + 2 * m, height=height + 2 * m + self.FOOTER,
                                highlightthickness=0, borderwidth=0, background=theme.bg)
        self.canvas.bind("<Button-1>", self._clicked)
        self.canvas.bind("<Enter>", lambda e: self._set_hover(True))
        self.canvas.bind("<Leave>", lambda e: self._set_hover(False))
        self.canvas.bind("<Configure>", self._resized)
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

    def fit(self, canvas_width: int, canvas_height: int) -> None:
        """Size the card to fill a canvas of this size, keeping its shape."""
        m = self.MARGIN
        h = max(self.MIN_HEIGHT, min(canvas_height - 2 * m - self.FOOTER,
                                     (canvas_width - 2 * m) / self.ASPECT))
        w = h * self.ASPECT
        if ((round(w), round(h)) != (round(self.width), round(self.height))
                or canvas_width != self._canvas_width):
            # A new card size, or the same card in a wider/narrower space
            # (it has to move to stay centred).
            self.width, self.height = w, h
            self._canvas_width = canvas_width
            self.redraw()

    def _resized(self, event) -> None:
        self.fit(event.width, event.height)

    def _clicked(self, _event) -> None:
        if self.command:
            self.command()

    def _set_hover(self, on: bool) -> None:
        if self.hover != on:
            self.hover = on
            self.redraw()

    def _size(self, share: float, smallest: int = 7) -> int:
        """A font size (points) as a share of the card's height in pixels."""
        return max(smallest, round(self.height * share))

    # ----- drawing -------------------------------------------------------- #

    def redraw(self) -> None:
        c, t = self.canvas, self.theme
        c.delete("all")
        c.configure(background=t.bg)
        m, w, h = self.MARGIN, self.width, self.height
        shown = c.winfo_width()
        canvas_width = (self._canvas_width or (shown if shown > 1 else int(c.cget("width"))))
        x1 = max(m, (canvas_width - w) / 2)
        y1 = m
        x2, y2 = x1 + w, y1 + h
        radius = max(6, h * 0.08)
        clickable = self.state in ("live", "selected", "recoverable")
        c.configure(cursor="hand2" if clickable else "")

        if self.state == "empty":
            rounded_rect(c, x1, y1, x2, y2, radius, fill="", outline=t.edge, width=2,
                         dash=(5, 4))
        else:
            lift = 3 if self.state == "selected" else 0
            rounded_rect(c, x1 + 3, y1 + 4, x2 + 3, y2 + 4, radius, fill=t.shadow, outline="")
            if self.state in ("live", "selected") and self.card is not None:
                self._face(x1, y1 - lift, x2, y2 - lift, self.card, radius)
            else:
                self._back(x1, y1, x2, y2, radius)
            if self.state == "selected":
                rounded_rect(c, x1 - 3, y1 - lift - 3, x2 + 3, y2 - lift + 3, radius + 2,
                             fill="", outline=t.select, width=4)
            elif self.state == "recoverable":
                rounded_rect(c, x1 - 3, y1 - 3, x2 + 3, y2 + 3, radius + 2,
                             fill="", outline=t.recover, width=4)
            elif self.hover and clickable:
                rounded_rect(c, x1 - 2, y1 - 2, x2 + 2, y2 + 2, radius + 1,
                             fill="", outline=t.select, width=2)

        fy = y2 + m + self.FOOTER / 2 - 2
        key_font, odds_font = font("ui", 9, "bold"), font("ui", 8)
        room = (x2 - x1) - text_width(c, odds_font, self.footer_right) - 6
        if self.footer_left and text_width(c, key_font, self.footer_left) <= room:
            c.create_text(x1 + 2, fy, text=self.footer_left, anchor="w",
                          font=key_font, fill=t.muted)
        if self.footer_right:
            color = t.recover if self.state == "recoverable" else t.text
            c.create_text(x2, fy, text=self.footer_right, anchor="e",
                          font=odds_font, fill=color)

    def _face(self, x1: float, y1: float, x2: float, y2: float, card: Card,
              radius: float) -> None:
        c, t = self.canvas, self.theme
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        h = self.height
        corner_x, rank_y, suit_y = h * 0.11, h * 0.12, h * 0.26
        if card.is_joker:
            rounded_rect(c, x1, y1, x2, y2, radius, fill=t.joker, outline=t.card_edge, width=1)
            c.create_text(cx, cy - h * 0.08, text="★", font=font("symbol", self._size(0.28)),
                          fill=t.joker_ink)
            c.create_text(cx, cy + h * 0.2, text="JOKER", font=font("ui", self._size(0.08), "bold"),
                          fill=t.joker_ink)
            c.create_text(x1 + corner_x, y1 + rank_y, text="★",
                          font=font("symbol", self._size(0.085)), fill=t.joker_ink)
            _text(c, x2 - corner_x, y2 - rank_y, True, text="★",
                  font=font("symbol", self._size(0.085)), fill=t.joker_ink)
            return
        rounded_rect(c, x1, y1, x2, y2, radius, fill=t.card, outline=t.card_edge, width=1)
        color = suit_color(card, t)
        rank = card.rank_label
        rank_font = font("card", self._size(0.11 if len(rank) > 1 else 0.117), "bold")
        suit_font = font("symbol", self._size(0.094))
        c.create_text(x1 + corner_x, y1 + rank_y, text=rank, font=rank_font, fill=color)
        c.create_text(x1 + corner_x, y1 + suit_y, text=card.suit, font=suit_font, fill=color)
        _text(c, x2 - corner_x, y2 - rank_y, True, text=rank, font=rank_font, fill=color)
        _text(c, x2 - corner_x, y2 - suit_y, True, text=card.suit, font=suit_font, fill=color)
        c.create_text(cx, cy, text=card.suit, font=font("symbol", self._size(0.3)), fill=color)

    def _back(self, x1: float, y1: float, x2: float, y2: float, radius: float) -> None:
        c, t = self.canvas, self.theme
        rounded_rect(c, x1, y1, x2, y2, radius, fill=t.back, outline=t.card_edge, width=1)
        inset = max(5, self.height * 0.055)
        ix1, iy1, ix2, iy2 = x1 + inset, y1 + inset, x2 - inset, y2 - inset
        rounded_rect(c, ix1, iy1, ix2, iy2, radius * 0.6, fill="", outline=t.back_line, width=1)
        # Diamond lattice, clipped to the inner border by hand.
        step = max(8, round(self.height * 0.095))
        for offset in range(int(-(iy2 - iy1)), int(ix2 - ix1) + step, step):
            # lines going down-right: x - ix1 = (y - iy1) + offset
            sx = max(ix1, ix1 + offset)
            ex = min(ix2, ix1 + offset + (iy2 - iy1))
            if ex > sx:
                c.create_line(sx, iy1 + (sx - ix1 - offset), ex, iy1 + (ex - ix1 - offset),
                              fill=t.back_line)
                # lines going down-left (mirror image)
                c.create_line(ix1 + ix2 - sx, iy1 + (sx - ix1 - offset),
                              ix1 + ix2 - ex, iy1 + (ex - ix1 - offset), fill=t.back_line)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        w = x2 - x1
        if self.ghost is not None:
            half_w, half_h = w * 0.32, self.height * 0.17
            rounded_rect(c, cx - half_w, cy - half_h, cx + half_w, cy + half_h, 6, fill=t.card,
                         outline=t.card_edge)
            c.create_text(cx, cy, text=card_name(self.ghost) if self.ghost.is_joker
                          else self.ghost.label(), font=font("card", self._size(0.117), "bold"),
                          fill=suit_color(self.ghost, t))
        else:
            half_w, half_h = w * 0.34, self.height * 0.095
            rounded_rect(c, cx - half_w, cy - half_h, cx + half_w, cy + half_h, 6, fill=t.back,
                         outline=t.back_line)
            c.create_text(cx, cy, text="FAILED", font=font("ui", self._size(0.07), "bold"),
                          fill=readable_on(t.back))


# --------------------------------------------------------------- StatTile -- #

class StatTile(ttk.Frame):
    """A big value over a small caption. In a narrow tile the value shrinks
    (down to 9 points, then wraps) and the caption wraps, instead of being
    cut off."""

    SIZES = (17, 15, 14, 13, 12, 11, 10, 9)
    PAD_X = 12

    def __init__(self, parent: tk.Misc, caption: str, variable: tk.Variable, **kwargs):
        super().__init__(parent, style="Panel.TFrame", padding=(self.PAD_X, 6), **kwargs)
        self.variable = variable
        # width=1 + fill: the labels take the tile's width instead of asking
        # for their text's width, so fitting the text can't resize the tile
        # (which would refit the text, and so on).
        self.value = ttk.Label(self, textvariable=variable, style="TileValue.TLabel", width=1)
        self.value.pack(anchor="w", fill="x")
        self.caption = ttk.Label(self, text=caption, style="PanelMuted.TLabel", width=1)
        self.caption.pack(anchor="w", fill="x")
        self.size = self.SIZES[0]
        self.bind("<Configure>", self.fit)
        self._trace = variable.trace_add("write", self.fit)
        self.bind("<Destroy>", self._forget_trace)

    def _forget_trace(self, event) -> None:
        if event.widget is self:
            try:
                self.variable.trace_remove("write", self._trace)
            except (tk.TclError, ValueError):
                pass

    def fit(self, *_args) -> None:
        try:
            room = self.winfo_width() - 2 * self.PAD_X - 6     # 6: the label's own edges
        except tk.TclError:
            return
        if room <= 1:
            return
        value = str(self.variable.get())
        size, fits = self.SIZES[-1], False
        for candidate in self.SIZES:
            if text_width(self, font("ui", candidate, "bold"), value) <= room:
                size, fits = candidate, True
                break
        wrap = max(40, room)
        value_wrap = 0 if fits else wrap                 # wrap only if even 9pt is too wide
        changed = False
        if size != self.size:
            self.size = size
            self.value.configure(font=font("ui", size, "bold"))
            changed = True
        if wrap_length(self.value) != value_wrap:
            self.value.configure(wraplength=value_wrap)
            changed = True
        if wrap_length(self.caption) != wrap:
            self.caption.configure(wraplength=wrap)
            changed = True
        if changed:
            notify_resized(self)


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
        self.canvas.bind("<Configure>", self._resized)
        self.redraw()

    def _resized(self, event) -> None:
        if (event.width, event.height) != (self.width, self.height):
            self.width, self.height = event.width, event.height
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
    (card, button) pair, one button per physical joker. The mini cards
    shrink (10 down to 7 points) to fit the width of the panel they sit in.
    """

    SIZES = (10, 9, 8, 7)

    def __init__(self, parent: tk.Misc, theme: Theme,
                 on_pick: Callable[[Card, tk.Button], None], jokers: int = 0,
                 style: str = "TFrame"):
        super().__init__(parent, style=style)
        self.theme = theme
        self.on_pick = on_pick
        self.selected: Optional[str] = None
        self.buttons: List[Tuple[Card, tk.Button]] = []
        self.jokers = jokers
        self.size = self.SIZES[0]
        for row, suit in enumerate(SUITS):
            for col, rank in enumerate(reversed(RANKS)):  # A K Q ... 2
                self._add(Card(rank, suit), row, col)
        for i in range(jokers):
            self._add(Card.joker(), len(SUITS), i * 2, columnspan=2)
        self.set_theme(theme)
        parent.bind("<Configure>", lambda e: self.fit(self._room()), add="+")

    def _room(self) -> int:
        """Width inside the parent panel (its width less its padding)."""
        master = self.master
        try:
            pad = [int(float(p)) for p in str(master.cget("padding")).split()]
        except (tk.TclError, ValueError):
            pad = []
        left = pad[0] if pad else 0
        right = pad[2] if len(pad) > 2 else left
        return master.winfo_width() - left - right

    def fit(self, width: int) -> None:
        """Use the largest mini-card text at which 13 cards fit in `width`."""
        if width <= 1:
            return
        size = self.SIZES[-1]
        for candidate in self.SIZES:
            spec = font("card", candidate, "bold")
            cell = max(text_width(self, spec, "10♠"), 3 * text_width(self, spec, "0")) + 8
            if cell * len(RANKS) <= width:
                size = candidate
                break
        if size != self.size:
            self.size = size
            for _card, button in self.buttons:
                button.configure(font=font("card", size, "bold"))
            notify_resized(self)

    def beside_jokers(self, widget: tk.Misc) -> None:
        """Put `widget` (a child of this grid) in the joker row, after the jokers."""
        start = self.jokers * 2
        widget.grid(row=len(SUITS), column=start, columnspan=len(RANKS) - start,
                    sticky="w", padx=(8 if start else 0, 0))

    def _add(self, card: Card, row: int, col: int, columnspan: int = 1) -> None:
        text = "Joker" if card.is_joker else card.label()
        button = tk.Button(self, text=text, width=6 if card.is_joker else 3, relief="flat",
                           borderwidth=0, padx=2, pady=1, cursor="hand2",
                           font=font("card", self.size, "bold"))
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


# ------------------------------------------------------------ ScrollFrame -- #

_SCROLL_FRAMES: List["ScrollFrame"] = []
_SELF_SCROLLING = ("Listbox", "Text", "Treeview", "TCombobox")


def _wheel(event) -> Optional[str]:
    """Mouse wheel over a ScrollFrame scrolls it (lists and tables scroll
    themselves, so they are left alone)."""
    widget = event.widget
    if isinstance(widget, str) or event.state & 0x0001:     # Shift+wheel: not ours
        return None
    try:
        if widget.winfo_class() in _SELF_SCROLLING:
            return None
        path = str(widget)
    except tk.TclError:
        return None
    for frame in list(_SCROLL_FRAMES):
        if not themes.alive(frame):
            _SCROLL_FRAMES.remove(frame)
            continue
        if frame.scrolling and (path == str(frame.canvas)
                                or path.startswith(str(frame.canvas) + ".")):
            if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
                frame.canvas.yview_scroll(-3, "units")
            else:
                frame.canvas.yview_scroll(3, "units")
            return "break"
    return None


class ScrollFrame(ttk.Frame):
    """A panel whose contents scroll up and down when they don't fit.

    Put widgets in `.body`. The body is always as wide as the panel. When
    it is shorter than the panel it is stretched to fill it (so a list at
    the bottom can grow); when it is taller, a scrollbar appears.
    """

    def __init__(self, parent: tk.Misc, width: int = 0, style: str = "TFrame",
                 background: str = "bg"):
        super().__init__(parent, style=style)
        self._background = background
        self._pending: Optional[str] = None          # id of the scheduled re-check
        self._passes = 0
        self._rounds = 0
        self._need = -1
        self._size = (0, 0)
        self.scrolling = False
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0,
                                width=width or 10, height=10, yscrollincrement=12)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        self.scrollbar.grid_remove()
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.body = ttk.Frame(self.canvas, style=style)
        self._window = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self.update_layout())
        self.canvas.bind("<Configure>", lambda e: self.update_layout())
        self.bind("<Destroy>", self._destroyed, add="+")
        self._paint(themes.current())
        themes.subscribe(self, self._paint)
        _SCROLL_FRAMES.append(self)
        # One wheel handler per Tk interpreter (bind_all is app-wide).
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            if "_wheel" not in str(self.tk.call("bind", "all", sequence)):
                self.bind_all(sequence, _wheel, add="+")

    def _destroyed(self, event) -> None:
        if event.widget is not self:
            return
        if self._pending:
            try:
                self.after_cancel(self._pending)
            except tk.TclError:
                pass
            self._pending = None
        if self in _SCROLL_FRAMES:
            _SCROLL_FRAMES.remove(self)

    def _paint(self, t: Theme) -> None:
        self.canvas.configure(background=getattr(t, self._background))

    def set_width(self, width: int) -> None:
        """The panel's width (the scrollbar, when shown, is extra)."""
        if abs(int(self.canvas.cget("width")) - width) > 1:
            self.canvas.configure(width=width)

    SETTLE_ROUNDS = 6      # re-check this many idle rounds after a change
    MAX_ROUNDS = 40        # ...but never more than this in a row

    def update_layout(self) -> None:
        """Re-check the size over the next few idle rounds. A size change
        inside nested frames climbs one frame per idle round, so a single
        check could read the body's height before the change reaches it."""
        self._passes = self.SETTLE_ROUNDS
        if self._pending is None:
            self._rounds = 0
            self._schedule()

    def _schedule(self) -> None:
        try:
            self._pending = self.after_idle(self._layout)
        except tk.TclError:
            self._pending = None

    def _layout(self) -> None:
        self._pending = None
        try:
            view_w, view_h = self.canvas.winfo_width(), self.canvas.winfo_height()
            need = self.body.winfo_reqheight()
        except tk.TclError:
            return
        if need != self._need:               # still changing: keep watching a bit longer
            self._need = need
            self._passes = max(self._passes, 2)
        self._passes -= 1
        self._rounds += 1
        if self._passes > 0 and self._rounds < self.MAX_ROUNDS:
            self._schedule()
        if view_w <= 1 or view_h <= 1:
            return
        height = max(need, view_h)
        if (view_w, height) != self._size:      # only on a real change, or it never settles
            self._size = (view_w, height)
            self.canvas.itemconfigure(self._window, width=view_w, height=height)
            self.canvas.configure(scrollregion=(0, 0, view_w, height))
        overflow = need > view_h + 1
        if overflow != self.scrolling:
            self.scrolling = overflow
            if overflow:
                self.scrollbar.grid()
            else:
                self.scrollbar.grid_remove()
                self.canvas.yview_moveto(0)

    def visible(self, widget: tk.Misc) -> bool:
        """True if `widget` (inside the body) can be scrolled fully into view."""
        try:
            top = widget.winfo_rooty() - self.body.winfo_rooty()
            return top + widget.winfo_height() <= max(self.body.winfo_height(),
                                                       self.canvas.winfo_height()) + 1
        except tk.TclError:
            return False


# ---------------------------------------------------------- AutoScrollbar -- #

class AutoScrollbar(ttk.Scrollbar):
    """A scrollbar that hides itself when everything fits (grid only)."""

    def set(self, first, last) -> None:
        needed = not (float(first) <= 0.0 and float(last) >= 1.0)
        if needed != bool(self.winfo_manager()):
            if needed:
                self.grid()
            else:
                self.grid_remove()
            notify_resized(self)          # showing it adds height to the panel
        super().set(first, last)


def scrolled_tree(parent: tk.Misc, columns: Dict[str, Tuple[str, int, str]],
                  height: int, style: str = "TFrame") -> Tuple[ttk.Frame, ttk.Treeview]:
    """A Treeview with a scrollbar down the side and, when the window is too
    narrow for every column, one along the bottom. Columns never shrink
    below their width, so nothing is cut off; they share any extra room.
    columns: id -> (heading, width, anchor). Returns (holder, tree)."""
    holder = ttk.Frame(parent, style=style)
    tree = ttk.Treeview(holder, columns=list(columns), show="headings", height=height)
    for col, (heading, width, anchor) in columns.items():
        tree.heading(col, text=heading)
        tree.column(col, width=width, minwidth=width, anchor=anchor, stretch=True)
    down = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
    across = AutoScrollbar(holder, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=down.set, xscrollcommand=across.set)
    tree.grid(row=0, column=0, sticky="nsew")
    down.grid(row=0, column=1, sticky="ns")
    across.grid(row=1, column=0, sticky="ew")
    holder.rowconfigure(0, weight=1)
    holder.columnconfigure(0, weight=1)
    return holder, tree


def notify_resized(widget: tk.Misc) -> None:
    """Tell the ScrollFrame holding `widget` (if any) that its contents may
    have changed height, e.g. after text was re-wrapped or re-sized."""
    path = str(widget)
    for frame in list(_SCROLL_FRAMES):
        if not themes.alive(frame):
            _SCROLL_FRAMES.remove(frame)
        elif path.startswith(str(frame.body) + "."):
            frame.update_layout()


def wrap_to(label: tk.Misc, pad: int = 4, minimum: int = 40) -> None:
    """Wrap `label` to its own width. Place it with fill="x" (pack) or
    sticky="ew" (grid): with width=1 it takes the room it is given instead
    of asking for its text's width, so re-wrapping can't feed back into the
    layout."""
    label.configure(width=1)

    def update(event):
        width = max(minimum, event.width - pad)
        if wrap_length(label) != width:
            label.configure(wraplength=width)
            notify_resized(label)
    label.bind("<Configure>", update, add="+")


def flow_row(frame: tk.Misc, children: Sequence[tk.Misc], gap: int = 10) -> None:
    """Lay `children` out in one row inside `frame`, wrapping onto more rows
    when the frame is too narrow for them all (like words in a line)."""
    state = {"columns": 0}

    def arrange(_event=None):
        width = frame.winfo_width()
        widths = [child.winfo_reqwidth() + gap for child in children]
        columns = len(children)
        if width > 1:
            while columns > 1 and sum(sorted(widths, reverse=True)[:columns]) > width:
                columns -= 1
        if columns == state["columns"]:
            return
        state["columns"] = columns
        for i, child in enumerate(children):
            child.grid(row=i // columns, column=i % columns, sticky="w", padx=(0, gap))
        notify_resized(frame)
    frame.bind("<Configure>", arrange, add="+")
    arrange()