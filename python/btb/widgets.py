"""
==============================================
CARD AND CHART WIDGETS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/widgets.py
Status: ACTIVE
Version: 1.3
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 308 passed)

VERSION 1.3 CHANGES (2026-10-20):
- Fixes the freeze seen on Windows ("Not responding", and the test run
  hanging): before the window was drawn, CardGrid sized its font from a
  panel that was only as wide as the grid itself, so it flipped between
  two sizes forever. It now sizes itself from the width its ScrollFrame
  was set to. New FlipGuard stops any layout that resizes itself more
  than 6 times in half a second (CardGrid, StatTile, flow_row).
- Big and little jokers: green and purple faces with BIG / LITTLE JOKER,
  their own buttons in CardGrid (keyed by Card.key()); card_name() gives
  their names. CardView redraws when one joker replaces the other.
- New CardsLeftView: the cards left in the pile as a Simple table (rank,
  number left, a dot per card) or as Cards (four suit rows, played cards
  faded).
- The odds line under a card shrinks (8, 7, 6 points, then without %) so
  it is never cut off under a narrow card.
- CardGrid removes its resize handler from the side panel when it is
  destroyed (a rebuilt picker left dead handlers behind), reads its
  panel's padding correctly, and can hide the jokers a game doesn't have
  (show_jokers).

VERSION 1.2 CHANGES (2026-10-20):
- New DocView: a help page drawn as a formatted document from the markup
  in btb/markup.py: headings in real sizes, bullet and numbered lists
  with hanging indents, tables as aligned columns (numbers centred), keys
  on keycaps and cards on card-coloured chips, notes and dividing lines.
  It wraps to the width, scrolls, can be selected and copied (Ctrl+C,
  Ctrl+A, right-click), and redraws on a theme change keeping its place.
- BarChart: a y-axis with gridlines, x labels thinned so they never
  overlap (for 50 bars as easily as 9), values over the bars only when
  they fit, a dashed average line, and optional 95% whiskers.
- New LineChart (built on BarChart): one line per series with a marker
  shape and colour each, 95% whiskers and a legend; the y-axis covers the
  data rather than starting at 0, so small differences show.
- New nice_ticks(low, high): round values for an axis.
- The mouse wheel over a list or table that has nothing to scroll now
  scrolls the panel around it.
- DocView tables fit the page's width (narrower gaps, then a smaller
  font) and re-fit when the window is resized; chips are measured as
  drawn; the wheel scrolls the page over a chip; the copy menu is on the
  right button (Button-2 only on a Mac).

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
  BarChart  labelled bars on an axis, with an average line and whiskers.
  LineChart a line per series, with whiskers and a legend (Optimizer).
  DocView   a help page drawn as a formatted document (btb.markup).
  CardGrid  4 x 13 mini cards plus jokers, for picking cards (Assistant);
            the cards shrink to fit the width they are given.
  ScrollFrame    a panel that scrolls up and down when it doesn't fit.
  AutoScrollbar  a scrollbar that hides when everything fits.

DEPENDENCIES:
------------
- btb.engine (Card, SUITS, RANKS), btb.theme, btb.markup
- Standard library: tkinter, math, typing

KEY FUNCTIONS:
-------------
- rounded_rect(canvas, x1, y1, x2, y2, r, **options) -> canvas item
- CardView.show(card, state, ghost, footer_left, footer_right)
- CardView.describe() -> "A♥", "Failed" or "Failed\\nK♥" (tests, screen readers)
- CardView.fit(width, height) -> size the card to a canvas (called on resize)
- text_width(widget, font, text) -> pixels a piece of text needs
- StatTile(parent, caption, variable)
- BarChart.draw(items, value_format, average, errors, title)
- LineChart.draw_series(labels, series, title)
- nice_ticks(low, high, count) -> round axis values
- DocView(parent, source).set_source / plain / copy / render
- CardsLeftView(parent, theme).show(pile, jokers, mode) -> Simple or Cards
- FlipGuard().allow() -> False once a layout keeps resizing itself
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

import math
import time
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import markup
from . import theme as themes
from .engine import JOKER_KINDS, RANKS, SUITS, Card
from .theme import Theme, font

RED_SUITS = ("♥", "♦")
CARD_STATES = ("empty", "live", "selected", "failed", "recoverable")


def card_name(card: Card) -> str:
    """Readable label: "A♥", or "Big Joker" / "Little Joker" / "Joker"."""
    return card.name


def joker_colors(card: Card, t: Theme) -> Tuple[str, str]:
    """(face, ink) for a joker: green for the big joker, purple otherwise."""
    if card.kind == "big":
        return t.joker_big, t.joker_big_ink
    return t.joker, t.joker_ink


def suit_color(card: Card, t: Theme) -> str:
    if card.is_joker:
        return joker_colors(card, t)[1]
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
        kinds = (getattr(card, "kind", ""), getattr(ghost, "kind", ""))
        old_kinds = (getattr(self.card, "kind", ""), getattr(self.ghost, "kind", ""))
        # Two jokers are equal in play, so compare their kinds too (big/little).
        if (new == (self.card, self.state, self.ghost, self.footer_left, self.footer_right)
                and kinds == old_kinds):
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
        key_font = font("ui", 9, "bold")
        odds_text, odds_font = self.fit_footer(c, self.footer_right, x2 - x1)
        room = (x2 - x1) - text_width(c, odds_font, odds_text) - 6
        if self.footer_left and text_width(c, key_font, self.footer_left) <= room:
            c.create_text(x1 + 2, fy, text=self.footer_left, anchor="w",
                          font=key_font, fill=t.muted)
        if odds_text:
            color = t.recover if self.state == "recoverable" else t.text
            c.create_text(x2, fy, text=odds_text, anchor="e", font=odds_font, fill=color)

    @staticmethod
    def fit_footer(widget: tk.Misc, text: str, width: float) -> Tuple[str, tuple]:
        """The odds line under a card, made to fit the card's width: 8 points,
        then 7, then 6, then without the % signs ("▲100 ▼100"), so it is
        never cut off at the left."""
        candidates = [(text, size) for size in (8, 7, 6)]
        if "%" in text:
            candidates.append((text.replace("%", ""), 6))
        for words, size in candidates:
            if text_width(widget, font("ui", size), words) <= width:
                return words, font("ui", size)
        return candidates[-1][0], font("ui", candidates[-1][1])

    def _face(self, x1: float, y1: float, x2: float, y2: float, card: Card,
              radius: float) -> None:
        c, t = self.canvas, self.theme
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        h = self.height
        corner_x, rank_y, suit_y = h * 0.11, h * 0.12, h * 0.26
        if card.is_joker:
            face, ink = joker_colors(card, t)
            rounded_rect(c, x1, y1, x2, y2, radius, fill=face, outline=t.card_edge, width=1)
            star = self._size(0.34 if card.kind == "big" else 0.24)    # big joker, bigger star
            c.create_text(cx, cy - h * 0.1, text="★", font=font("symbol", star), fill=ink)
            words = {"big": "BIG", "little": "LITTLE"}.get(card.kind)
            if words:
                c.create_text(cx, cy + h * 0.15, text=words,
                              font=font("ui", self._size(0.075), "bold"), fill=ink)
            c.create_text(cx, cy + h * (0.26 if words else 0.2), text="JOKER",
                          font=font("ui", self._size(0.075), "bold"), fill=ink)
            c.create_text(x1 + corner_x, y1 + rank_y, text="★",
                          font=font("symbol", self._size(0.085)), fill=ink)
            _text(c, x2 - corner_x, y2 - rank_y, True, text="★",
                  font=font("symbol", self._size(0.085)), fill=ink)
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
        self._guard = FlipGuard()
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
        if size != self.size and self._guard.allow():
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

def nice_ticks(low: float, high: float, count: int = 4) -> List[float]:
    """About `count` round tick values covering low..high (1, 2, 2.5 or 5
    times a power of ten apart), for a chart's y-axis."""
    if high <= low:
        high = low + 1
    raw = (high - low) / max(1, count)
    power = 10 ** math.floor(math.log10(raw))
    step = next(m * power for m in (1, 2, 2.5, 5, 10) if m * power >= raw)
    first = math.floor(low / step) * step
    ticks, value = [], first
    while value < high + step * 0.999:
        ticks.append(round(value, 10))
        value += step
    return ticks


class BarChart:
    """Labelled vertical bars on a y-axis with gridlines. Redraws itself
    when resized or when the theme changes.

    draw(items, value_format, average, errors): items are (label, value)
    pairs. With many bars, only every few labels are written, so they
    never overlap, and values are written over the bars only when there
    is room. `average` (a position in bar units, 0 = the first bar) adds
    a dashed line with its label; `errors` adds a 95% whisker
    (low, high) to each bar."""

    PAD = 12

    def __init__(self, parent: tk.Misc, theme: Theme, width: int = 380, height: int = 170,
                 title: str = ""):
        self.theme = theme
        self.width, self.height, self.title = width, height, title
        self.items: List[Tuple[str, float]] = []
        self.value_format: Callable[[float], str] = lambda v: f"{v:.0f}%"
        self.axis_format: Callable[[float], str] = lambda v: f"{v:g}%"
        self.average: Optional[Tuple[float, str]] = None
        self.errors: Optional[List[Tuple[float, float]]] = None
        self.empty_message = "Run a simulation to see this"
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
             value_format: Optional[Callable[[float], str]] = None,
             average: Optional[Tuple[float, str]] = None,
             errors: Optional[Sequence[Tuple[float, float]]] = None,
             title: Optional[str] = None) -> None:
        self.items = list(items)
        if value_format:
            self.value_format = value_format
        self.average = average
        self.errors = list(errors) if errors else None
        if title is not None:
            self.title = title
        self.redraw()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.redraw()

    # ----- shared drawing ------------------------------------------------- #

    def _frame(self) -> bool:
        """Clear, draw the title; False (after a message) when empty."""
        c, t = self.canvas, self.theme
        c.delete("all")
        c.configure(background=t.panel)
        c.create_text(self.PAD, 10, text=self.title, anchor="nw",
                      font=font("ui", 10, "bold"), fill=t.text, width=max(60, self.width - 24))
        if not self._has_data():
            c.create_text(self.width / 2, self.height / 2 + 8, text=self.empty_message,
                          font=font("ui", 9), fill=t.muted, width=max(60, self.width - 24))
            return False
        return True

    def _has_data(self) -> bool:
        return bool(self.items)

    def _plot_area(self, ticks: List[float]) -> Tuple[float, float, float, float]:
        """left, top, right, bottom of the plotting area, leaving room for
        the title, the y tick labels and the x labels."""
        tick_font = font("ui", 8)
        label_room = max(text_width(self.canvas, tick_font, self.axis_format(v)) for v in ticks)
        title_lines = 1 + int(text_width(self.canvas, font("ui", 10, "bold"), self.title)
                              > self.width - 24)
        return (self.PAD + label_room + 8, 18 + 17 * title_lines, self.width - self.PAD,
                self.height - 24)

    def _axis(self, ticks: List[float], left: float, top: float, right: float,
              bottom: float, low: float, high: float) -> Callable[[float], float]:
        """Gridlines and y tick labels; returns value -> y pixel."""
        c, t = self.canvas, self.theme
        grid = themes.mix(t.panel, t.text, 0.16)
        span = (high - low) or 1

        def y_of(value: float) -> float:
            return bottom - (bottom - top) * (value - low) / span

        for value in ticks:
            y = y_of(value)
            c.create_line(left, y, right, y, fill=grid)
            c.create_text(left - 6, y, text=self.axis_format(value), anchor="e",
                          font=font("ui", 8), fill=t.muted)
        c.create_line(left, bottom, right, bottom, fill=t.edge)
        return y_of

    def _x_labels(self, labels: List[str], xs: List[float], slot: float, bottom: float) -> None:
        """Write every k-th label so neighbours never overlap (the last one
        is always written)."""
        label_font = font("ui", 8)
        widest = max((text_width(self.canvas, label_font, label) for label in labels), default=0)
        every = max(1, math.ceil((widest + 6) / max(1.0, slot)))
        for i, (label, x) in enumerate(zip(labels, xs)):
            if i % every == 0 or (i == len(labels) - 1 and (i % every) > every // 2):
                self.canvas.create_text(x, bottom + 11, text=label, font=label_font,
                                        fill=self.theme.muted)

    def _whisker(self, x: float, y_low: float, y_high: float, color: str) -> None:
        c = self.canvas
        c.create_line(x, y_low, x, y_high, fill=color, width=1)
        c.create_line(x - 3, y_low, x + 3, y_low, fill=color)
        c.create_line(x - 3, y_high, x + 3, y_high, fill=color)

    def redraw(self) -> None:
        if not self._frame():
            return
        c, t = self.canvas, self.theme
        values = [v for _, v in self.items]
        tops = values + [high for _low, high in (self.errors or [])]
        ticks = nice_ticks(0, max(tops) or 1)
        left, top, right, bottom = self._plot_area(ticks)
        y_of = self._axis(ticks, left, top, right, bottom, 0, ticks[-1])
        slot = (right - left) / len(self.items)
        bar = max(1.0, slot * 0.7)
        value_font = font("ui", 8)
        room = all(text_width(c, value_font, self.value_format(v)) <= slot + 2 for v in values)
        xs = []
        for i, (_label, value) in enumerate(self.items):
            cx = left + slot * (i + 0.5)
            xs.append(cx)
            if value > 0:
                c.create_rectangle(cx - bar / 2, y_of(value), cx + bar / 2, bottom,
                                   fill=t.chart, outline="")
            if self.errors:
                low, high = self.errors[i]
                self._whisker(cx, y_of(low), y_of(high), t.text)
            if room and value > 0 and not self.errors:
                c.create_text(cx, y_of(value) - 7, text=self.value_format(value),
                              font=value_font, fill=t.text)
        self._x_labels([label for label, _ in self.items], xs, slot, bottom)
        if self.average is not None:
            position, label = self.average
            x = left + slot * (position + 0.5)
            c.create_line(x, top - 4, x, bottom, fill=t.text, dash=(4, 3), width=2)
            anchor = "e" if x > (left + right) / 2 else "w"
            c.create_text(x + (-5 if anchor == "e" else 5), top + 2, text=label, anchor=anchor,
                          font=font("ui", 8, "bold"), fill=t.text)


class LineChart(BarChart):
    """One line per series over shared x labels, each point with its 95%
    whisker, and a legend. The y-axis covers the data (it need not start at
    0, so small differences show).

    draw_series(labels, series): labels are the x labels; series maps a
    name to one (value, low, high) per label, or None where a series has
    no point."""

    SHAPES = ("circle", "square", "diamond", "triangle")   # one per series, as well as colour

    def __init__(self, parent: tk.Misc, theme: Theme, width: int = 380, height: int = 200,
                 title: str = ""):
        self.labels: List[str] = []
        self.series: Dict[str, List[Optional[Tuple[float, float, float]]]] = {}
        super().__init__(parent, theme, width, height, title)

    def draw_series(self, labels: Sequence[str],
                    series: Dict[str, Sequence[Optional[Tuple[float, float, float]]]],
                    title: Optional[str] = None) -> None:
        self.labels = list(labels)
        self.series = {name: list(points) for name, points in series.items()}
        if title is not None:
            self.title = title
        self.redraw()

    def _has_data(self) -> bool:
        return any(p is not None for points in self.series.values() for p in points)

    def _marker(self, shape: str, x: float, y: float, color: str, r: float = 4.0) -> None:
        c, edge = self.canvas, self.theme.panel
        if shape == "square":
            c.create_rectangle(x - r + 0.5, y - r + 0.5, x + r - 0.5, y + r - 0.5, fill=color,
                               outline=edge)
        elif shape == "diamond":
            c.create_polygon(x, y - r - 1, x + r + 1, y, x, y + r + 1, x - r - 1, y,
                             fill=color, outline=edge)
        elif shape == "triangle":
            c.create_polygon(x, y - r - 1, x + r + 1, y + r, x - r - 1, y + r, fill=color,
                             outline=edge)
        else:
            c.create_oval(x - r, y - r, x + r, y + r, fill=color, outline=edge)

    def redraw(self) -> None:
        if not self._frame():
            return
        c, t = self.canvas, self.theme
        points = [p for line in self.series.values() for p in line if p is not None]
        low = min(p[1] for p in points)
        high = max(p[2] for p in points)
        pad = max(0.5, (high - low) * 0.08)
        ticks = nice_ticks(max(0.0, low - pad), min(100.0, high + pad))
        legend_height = 16
        left, top, right, bottom = self._plot_area(ticks)
        top += legend_height
        y_of = self._axis(ticks, left, top, right, bottom, ticks[0], ticks[-1])
        slot = (right - left) / max(1, len(self.labels))
        xs = [left + slot * (i + 0.5) for i in range(len(self.labels))]
        colors = themes.chart_palette(t)
        legend_x = left
        for n, (name, line) in enumerate(self.series.items()):
            color = colors[n % len(colors)]
            shift = (n - (len(self.series) - 1) / 2) * min(4.0, slot / 8)   # keep whiskers apart
            path = []
            for x, point in zip(xs, line):
                if point is None:
                    if len(path) >= 4:
                        c.create_line(*path, fill=color, width=2)
                    path = []
                    continue
                value, p_low, p_high = point
                px, py = x + shift, y_of(value)
                self._whisker(px, y_of(p_low), y_of(p_high), color)
                path += [px, py]
            if len(path) >= 4:
                c.create_line(*path, fill=color, width=2)
            shape = self.SHAPES[n % len(self.SHAPES)]
            for x, point in zip(xs, line):
                if point is not None:
                    self._marker(shape, x + shift, y_of(point[0]), color)
            # legend: the marker and the name, left to right under the title
            mid = top - legend_height + 4
            c.create_line(legend_x, mid, legend_x + 16, mid, fill=color, width=2)
            self._marker(shape, legend_x + 8, mid, color)
            c.create_text(legend_x + 21, mid, text=name, anchor="w",
                          font=font("ui", 8), fill=t.text)
            legend_x += 34 + text_width(c, font("ui", 8), name)
        self._x_labels(self.labels, xs, slot, bottom)


# ---------------------------------------------------------------- DocView -- #

class DocView(ttk.Frame):
    """A help page drawn as a formatted document (btb.markup): headings in
    real sizes, bullet and numbered lists with hanging indents, tables as
    aligned columns, keys on a chip, cards in card colours, notes and
    dividing lines. Text wraps to the width, scrolls, can be selected and
    copied (Ctrl+C or the right-click menu), and repaints on a theme change."""

    MARGIN = 30          # left and right page margin (pixels)
    INDENT = 24          # extra indent per list level
    CELL_GAP = 26        # space between table columns
    BASE = 11            # body text size (points)

    def __init__(self, parent: tk.Misc, source: str = "", style: str = "TFrame"):
        super().__init__(parent, style=style)
        self.source = source
        self.chips: List[tk.Label] = []          # keys and cards drawn inline
        self.text = tk.Text(self, wrap="word", padx=self.MARGIN, pady=20, borderwidth=0,
                            highlightthickness=0, relief="flat", cursor="xterm",
                            takefocus=1, exportselection=True)
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        # A read-only page still takes the focus on a click, so Ctrl+C copies.
        self.text.bind("<Button-1>", lambda e: self.text.focus_set(), add="+")
        self.text.bind("<Control-a>", self._select_all)
        self.text.bind("<Control-A>", self._select_all)
        self.menu = tk.Menu(self, tearoff=False)
        self.menu.add_command(label="Copy", command=self.copy)
        self.menu.add_command(label="Select All", command=self._select_all)
        for sequence in self._menu_buttons():
            self.text.bind(sequence, self._popup)
        self._fitted_width = 0
        self._refit: Optional[str] = None
        self.text.bind("<Configure>", self._resized, add="+")
        self.render()
        themes.subscribe(self, lambda _t: self.render())

    # ----- public --------------------------------------------------------- #

    def set_source(self, source: str) -> None:
        self.source = source
        self.render()

    def plain(self) -> str:
        """Everything on the page, as text (what Select All + Copy gives)."""
        return self.text.get("1.0", "end-1c")

    def copy(self) -> None:
        """Copy the selection, or the whole page when nothing is selected."""
        try:
            chosen = self.text.get("sel.first", "sel.last")
        except tk.TclError:
            chosen = self.plain()
        self.clipboard_clear()
        self.clipboard_append(chosen)

    def _select_all(self, _event=None) -> str:
        self.text.tag_add("sel", "1.0", "end-1c")
        return "break"

    def _menu_buttons(self) -> Tuple[str, ...]:
        """The right mouse button: Button-3, or Button-2 on a Mac (on
        Windows and Linux Button-2 is the middle button)."""
        try:
            aqua = self.tk.call("tk", "windowingsystem") == "aqua"
        except tk.TclError:
            aqua = False
        return ("<Button-2>", "<Control-Button-1>") if aqua else ("<Button-3>",)

    def _wheel(self, event) -> str:
        """Scroll the page (used for the chips, which would swallow the wheel)."""
        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            self.text.yview_scroll(-3, "units")
        else:
            self.text.yview_scroll(3, "units")
        return "break"

    def _popup(self, event) -> None:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    # ----- drawing -------------------------------------------------------- #

    def render(self) -> None:
        """Draw the page from the markup in the current theme, keeping the
        scroll position."""
        t = themes.current()
        p = themes.doc_palette(t)
        text = self.text
        top = text.index("@0,0") if self.source == getattr(self, "_drawn", None) else "1.0"
        text.configure(state="normal", background=p["bg"], foreground=p["text"],
                       selectbackground=p["select_bg"], selectforeground=p["select_text"],
                       inactiveselectbackground=p["select_bg"], insertbackground=p["text"],
                       font=font("ui", self.BASE))
        text.delete("1.0", "end")
        for chip in self.chips:
            chip.destroy()
        self.chips = []
        self._palette = p
        for tag in text.tag_names():
            if tag != "sel":
                text.tag_delete(tag)
        self._styles(p)
        self._tables = 0
        previous = None
        for block in markup.parse(self.source):
            if previous is not None:
                self._space(previous, block)
            getattr(self, f"_{block.kind}")(block)
            previous = block
        text.delete("end-2c", "end-1c")         # no empty line at the very end
        text.tag_raise("sel")
        text.configure(state="disabled")
        text.yview(top)                         # same page: same line at the top
        self._drawn = self.source

    # Space between blocks is an empty line in a small font. (Tk takes a
    # line's spacing from its first character, which may be a chip, so
    # spacing options alone can't be relied on.) Copied text gets a blank
    # line between paragraphs from it, too.
    GAPS = {"small": 3, "medium": 6, "large": 9}

    def _space(self, previous, block) -> None:
        if block.kind == "item" and previous.kind == "item":
            return                                  # a list stays together
        if block.kind == "rule":
            return                                  # the rule has its own space
        if block.kind == "heading":
            size = "large" if block.level <= 2 else "medium"
        elif previous.kind == "heading":
            size = "small"
        else:
            size = "medium"
        self.text.insert("end", "\n", (f"gap_{size}",))

    def _styles(self, p: Dict[str, str]) -> None:
        text, base = self.text, self.BASE
        marker_width = text_width(self, font("ui", base, "bold"), "88.") + 10
        for name, size in self.GAPS.items():
            text.tag_configure(f"gap_{name}", font=font("ui", size), spacing1=0, spacing3=0)
        text.tag_configure("para", spacing2=3)
        text.tag_configure("h1", font=font("ui", 20, "bold"), foreground=p["title"],
                           spacing1=2, spacing3=4)
        text.tag_configure("h2", font=font("ui", 15, "bold"), foreground=p["heading"],
                           spacing1=4, spacing3=2)
        text.tag_configure("h3", font=font("ui", 12, "bold"), foreground=p["text"],
                           spacing1=2, spacing3=0)
        for level in range(3):
            left = level * self.INDENT
            text.tag_configure(f"item{level}", lmargin1=left, lmargin2=left + marker_width,
                               tabs=(left + marker_width,), spacing1=3, spacing2=3)
        text.tag_configure("marker", foreground=p["marker"], font=font("ui", base, "bold"))
        text.tag_configure("bold", font=font("ui", base, "bold"))
        # Keys and cards are drawn as small labels (a chip); their text sits
        # beside them, hidden, so Copy still includes it.
        text.tag_configure("hidden", elide=True)
        text.tag_configure("note", lmargin1=0, lmargin2=marker_width,
                           tabs=(marker_width,), spacing1=2, spacing2=3,
                           foreground=p["note_text"])
        text.tag_configure("notebar", foreground=p["marker"], font=font("ui", base + 2, "bold"))
        text.tag_configure("rule", font=font("ui", 1), background=p["rule"])
        text.tag_configure("gap", font=font("ui", 6))
        text.tag_configure("trow", spacing1=3, spacing3=3)
        text.tag_configure("th", font=font("ui", base, "bold"), background=p["head_bg"])
        text.tag_configure("stripe", background=p["stripe_bg"])

    def _spans(self, spans, tags: Tuple[str, ...]) -> None:
        for piece, style in spans:
            if style in ("card", "code"):
                self._chip(piece, style, tags)
            else:
                self.text.insert("end", piece, tags + (("bold",) if style == "bold" else ()))

    CHIP_EXTRA = 2 * 3 + 2 * 1 + 2 * 1     # a chip's padx, border and window padding

    def _chip_font(self, style: str) -> tuple:
        return font("card", self.BASE - 1, "bold") if style == "card" else font("mono",
                                                                                 self.BASE - 1)

    def _chip(self, piece: str, style: str, tags: Tuple[str, ...]) -> None:
        """A key (on a keycap) or a card (in card colours, on a card face)."""
        p = self._palette
        if style == "card":
            red = any(suit in piece for suit in RED_SUITS)
            options = dict(font=self._chip_font(style), background=p["card_bg"],
                           foreground=p["red" if red else "black"])
        else:
            options = dict(font=self._chip_font(style), background=p["code_bg"],
                           foreground=p["code_text"])
        chip = tk.Label(self.text, text=piece, padx=3, pady=0, borderwidth=0,
                        highlightthickness=1, highlightbackground=p["rule"], cursor="xterm",
                        **options)
        for sequence in self._menu_buttons():
            chip.bind(sequence, self._popup)
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            chip.bind(sequence, self._wheel)                 # the page scrolls over a chip
        chip.bind("<Button-1>", lambda e: self.text.focus_set())
        self.chips.append(chip)
        self.text.window_create("end", window=chip, align="center", padx=1)
        self.text.insert("end", piece, tags + ("hidden",))

    def _heading(self, block) -> None:
        tag = f"h{block.level}"
        self._spans(block.spans, (tag,))
        self.text.insert("end", "\n", (tag,))

    def _para(self, block) -> None:
        self._spans(block.spans, ("para",))
        self.text.insert("end", "\n", ("para",))

    def _item(self, block) -> None:
        tags: Tuple[str, ...] = (f"item{block.level}",)
        self.text.insert("end", f"{block.marker}\t", tags + ("marker",))
        self._spans(block.spans, tags)
        self.text.insert("end", "\n", tags)

    def _note(self, block) -> None:
        """A note: a bar in the accent colour, the text indented beside it."""
        self.text.insert("end", "▍\t", ("note", "notebar"))
        self._spans(block.spans, ("note",))
        self.text.insert("end", "\n", ("note",))

    def _rule(self, _block) -> None:
        self.text.insert("end", "\n", ("gap",))
        self.text.insert("end", "\n", ("rule",))
        self.text.insert("end", "\n", ("gap",))

    def _table(self, block) -> None:
        """Rows as tab-separated lines with tab stops at each column; a
        column of numbers is centred, others start at their stop. A long
        last cell wraps under itself."""
        self._tables += 1
        name = f"table{self._tables}"
        rows = block.header + block.rows
        columns = max(len(row) for row in rows)
        numeric = [all(_is_number("".join(p for p, _s in row[c])) for row in block.rows
                       if c < len(row) and row[c]) for c in range(columns)]
        # Fit the page's width: first narrow the gaps, then a smaller font.
        room = self._text_room()
        for size in (self.BASE, self.BASE - 1, self.BASE - 2):
            widths = self._column_widths(block, columns, size)
            gap = self.CELL_GAP
            if room and sum(widths) + 10 + gap * (columns - 1) > room:
                gap = max(8, (room - sum(widths) - 10) // max(1, columns - 1))
            if not room or sum(widths) + 10 + gap * (columns - 1) <= room:
                break
        stops, x = [], 10
        for c in range(columns):
            if numeric[c]:
                stops += [x + widths[c] / 2, "center"]
            else:
                stops += [x, "left"]
            x += widths[c] + gap
        last_start = stops[-2] if not numeric[-1] else 10
        self.text.tag_configure(name, tabs=tuple(stops), lmargin1=0, lmargin2=last_start)
        header_tags: Tuple[str, ...] = ("th",)
        if size != self.BASE:               # made after "th", so these fonts win
            self.text.tag_configure(name, font=font("ui", size))
            self.text.tag_configure(f"{name}h", font=font("ui", size, "bold"))
            header_tags += (f"{name}h",)
        for r, row in enumerate(rows):
            tags: Tuple[str, ...] = (name, "trow")
            if r < len(block.header):
                tags += header_tags
            elif (r - len(block.header)) % 2 == 1:
                tags += ("stripe",)
            for c in range(columns):
                self.text.insert("end", "\t", tags)
                if c < len(row):
                    self._spans(row[c], tags)
            self.text.insert("end", "\n", tags)


    def _column_widths(self, block, columns: int, size: int) -> List[int]:
        """Pixels each column needs at text size `size`. Keys and cards are
        measured as the chips they are drawn as (their own font, padding
        and border), so a chip never pushes past its column's tab stop."""
        widths = [0] * columns
        for r, row in enumerate(block.header + block.rows):
            weight = "bold" if r < len(block.header) else "normal"
            for c, cell in enumerate(row):
                width = 0
                for piece, style in cell:
                    if style in ("code", "card"):
                        width += text_width(self, self._chip_font(style), piece) + self.CHIP_EXTRA
                    else:
                        width += text_width(self, font("ui", size, "bold" if style == "bold"
                                                       else weight), piece)
                widths[c] = max(widths[c], width + 4)
        return widths

    def _text_room(self) -> int:
        """Width the text can use (0 while the page isn't laid out yet)."""
        width = self.text.winfo_width()
        return max(0, width - 2 * self.MARGIN - 6) if width > 1 else 0

    def _resized(self, event) -> None:
        """Re-fit the tables when the width changes enough to matter."""
        if "|" not in self.source or abs(event.width - self._fitted_width) < 30:
            return
        self._fitted_width = event.width
        if self._refit is not None:
            self.after_cancel(self._refit)
        self._refit = self.after(80, self._do_refit)

    def _do_refit(self) -> None:
        self._refit = None
        if themes.alive(self.text):
            self.render()


def _is_number(words: str) -> bool:
    return bool(words) and all(ch in "0123456789+-−.%, " for ch in words)


# ---------------------------------------------------------- CardsLeftView -- #

class CardsLeftView:
    """The cards still in the draw pile, drawn on a canvas, in two modes:

      simple  one line per rank (A down to 2, then jokers): the rank, how
              many are left, and four pips (filled = still in the pile)
      cards   the deck laid out as four suit rows (A to 2) plus the jokers,
              as small cards; a card no longer in the pile is drawn faded

    The canvas takes the width it is given and sets its own height."""

    ORDER = tuple(reversed(RANKS))          # A K Q ... 2

    def __init__(self, parent: tk.Misc, theme: Theme):
        self.theme = theme
        self.mode = "simple"
        self.pile: List[Card] = []
        self.jokers = 0
        self.width = 300
        self.canvas = tk.Canvas(parent, width=self.width, height=40, highlightthickness=0,
                                borderwidth=0, background=theme.panel)
        self.canvas.bind("<Configure>", self._resized)

    def pack(self, **options) -> None:
        self.canvas.pack(**options)

    def _resized(self, event) -> None:
        if abs(event.width - self.width) > 2:
            self.width = event.width
            self.redraw()

    def show(self, pile: Sequence[Card], jokers: int, mode: Optional[str] = None) -> None:
        """pile: the cards still in the draw pile; jokers: how many the game has."""
        self.pile, self.jokers = list(pile), jokers
        if mode:
            self.mode = mode
        self.redraw()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.redraw()

    def left_by_rank(self) -> Dict[int, int]:
        counts = {rank: 0 for rank in self.ORDER}
        counts[0] = 0
        for card in self.pile:
            counts[card.rank] += 1
        return counts

    def redraw(self) -> None:
        c, t = self.canvas, self.theme
        c.delete("all")
        c.configure(background=t.panel)
        height = self._simple() if self.mode == "simple" else self._cards()
        if int(float(c.cget("height"))) != height:
            c.configure(height=height)
            notify_resized(c)

    def _simple(self) -> int:
        """A small table: rank, number left, and pips (one per card of it)."""
        c, t = self.canvas, self.theme
        counts = self.left_by_rank()
        name_font, count_font = font("ui", 10), font("ui", 10, "bold")
        row, top = 22, 24
        c.create_text(4, 10, text="Rank", anchor="w", font=font("ui", 9, "bold"), fill=t.muted)
        c.create_text(110, 10, text="Left", anchor="e", font=font("ui", 9, "bold"),
                      fill=t.muted)
        ranks = list(self.ORDER) + ([0] if self.jokers else [])
        for i, rank in enumerate(ranks):
            y = top + i * row + row / 2
            if i % 2:
                c.create_rectangle(0, y - row / 2, self.width, y + row / 2, outline="",
                                   fill=themes.mix(t.panel, t.text, 0.05))
            name = {0: "Jokers", 11: "Jack", 12: "Queen", 13: "King", 14: "Ace"}.get(
                rank, str(rank))
            left = counts[rank]
            whole = self.jokers if rank == 0 else 4
            c.create_text(4, y, text=name, anchor="w", font=name_font,
                          fill=t.text if left else t.muted)
            c.create_text(110, y, text=str(left), anchor="e", font=count_font,
                          fill=t.text if left else t.muted)
            for pip in range(whole):
                x = 128 + pip * 18
                filled = pip < left
                c.create_oval(x, y - 6, x + 12, y + 6, outline=t.chart if filled else t.edge,
                              fill=t.chart if filled else "", width=1.5)
        total = len(self.pile)
        y = top + len(ranks) * row + 14
        c.create_line(4, y - 10, self.width - 4, y - 10, fill=t.edge)
        c.create_text(4, y + 2, text="Total", anchor="w", font=count_font, fill=t.text)
        c.create_text(110, y + 2, text=str(total), anchor="e", font=count_font, fill=t.text)
        return int(y + 16)

    def _cards(self) -> int:
        """Four suit rows of small cards (A to 2), then the jokers."""
        c, t = self.canvas, self.theme
        here = {(card.rank, card.suit) for card in self.pile if not card.is_joker}
        kinds_here = [card.kind for card in self.pile if card.is_joker]
        gap = 3
        w = max(16.0, (self.width - 4 - gap * 12) / 13)
        h = w * 1.35
        size = max(6, min(11, round(w * 0.36)))
        faded = themes.mix(t.panel, t.card, 0.18)
        y = 2
        for suit in SUITS:
            for i, rank in enumerate(self.ORDER):
                x = 2 + i * (w + gap)
                card = Card(rank, suit)
                if (rank, suit) in here:
                    rounded_rect(c, x, y, x + w, y + h, 4, fill=t.card, outline=t.card_edge)
                    color = suit_color(card, t)
                else:
                    rounded_rect(c, x, y, x + w, y + h, 4, fill=faded, outline=t.edge)
                    color = themes.mix(faded, suit_color(card, t), 0.35)
                c.create_text(x + w / 2, y + h * 0.34, text=card.rank_label,
                              font=font("card", size, "bold"), fill=color)
                c.create_text(x + w / 2, y + h * 0.7, text=suit, font=font("symbol", size),
                              fill=color)
            y += h + gap + 1
        for i, kind in enumerate(JOKER_KINDS[:self.jokers]):
            joker = Card.joker(kind)
            x, jw = 2 + i * (3 * w + 3 * gap), 3 * w + 2 * gap
            face, ink = joker_colors(joker, t)
            if kind not in kinds_here:
                face, ink = faded, themes.mix(faded, ink, 0.6)
            rounded_rect(c, x, y, x + jw, y + h * 0.7, 4, fill=face,
                         outline=t.card_edge if kind in kinds_here else t.edge)
            c.create_text(x + jw / 2, y + h * 0.35, text=f"★ {joker.name}",
                          font=font("ui", max(6, size - 1), "bold"), fill=ink)
        if self.jokers:
            y += h * 0.7 + gap
        return int(y + 2)


# -------------------------------------------------------------- FlipGuard -- #

class FlipGuard:
    """A backstop for layouts that resize themselves: allow() is False once
    something has changed size MAX_CHANGES times within WINDOW seconds, so a
    feedback loop stops after a few rounds instead of freezing the window.
    A person resizing the window never changes a size that often."""

    MAX_CHANGES = 6
    WINDOW = 0.5

    def __init__(self) -> None:
        self.changes: List[float] = []

    def allow(self) -> bool:
        now = time.monotonic()
        self.changes = [t for t in self.changes if now - t < self.WINDOW]
        if len(self.changes) >= self.MAX_CHANGES:
            return False
        self.changes.append(now)
        return True


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
        for i, kind in enumerate(JOKER_KINDS[:jokers]):    # a big and a little joker
            self._add(Card.joker(kind), len(SUITS), i * 3, columnspan=3)
        self.set_theme(theme)
        self._guard = FlipGuard()
        parent.bind("<Configure>", lambda e: self.fit(self._room()), add="+")
        scroll = self._scroll_frame()
        if scroll is not None:     # the panel's set width changed: fit again
            # The ScrollFrame outlives this grid (the Assistant rebuilds its
            # picker every game), so the binding goes when the grid does.
            binding = scroll.canvas.bind("<Configure>", lambda e: self.fit(self._room()),
                                         add="+")
            self.bind("<Destroy>", lambda e, c=scroll.canvas, b=binding:
                      self._unbind(e, c, b), add="+")

    def _unbind(self, event, canvas: tk.Misc, binding: str) -> None:
        """Remove only this grid's <Configure> script from the canvas."""
        if event.widget is not self:
            return
        try:
            scripts = canvas.bind("<Configure>").split("\n")
            kept = [line for line in scripts if binding not in line]
            canvas.bind("<Configure>", "\n".join(kept))
            canvas.deletecommand(binding)
        except tk.TclError:
            pass

    def _scroll_frame(self) -> Optional["ScrollFrame"]:
        widget = self.master
        while widget is not None:
            if isinstance(widget, ScrollFrame):
                return widget
            widget = widget.master
        return None

    def _room(self) -> int:
        """Width the grid may use: the parent panel's width less its padding.

        Inside a ScrollFrame, the panel's width is taken from the width the
        ScrollFrame was SET to, not from the panel itself. Before the window
        is drawn, the panel is only as wide as what it holds, so measuring it
        would make the grid size itself to its own font: big font, wide
        panel, small font, narrow panel, big font... forever (the window then
        never appears and Windows says "Not responding")."""
        master = self.master
        try:
            pad = [int(float(str(p))) for p in master.tk.splitlist(master.cget("padding"))]
        except (tk.TclError, ValueError):
            pad = []
        left = pad[0] if pad else 0
        right = pad[2] if len(pad) > 2 else left
        scroll = self._scroll_frame()
        if scroll is not None:
            try:
                width = int(float(scroll.canvas.cget("width")))
            except (tk.TclError, ValueError):
                width = 0
            shown = scroll.canvas.winfo_width()
            if shown > 1:
                width = min(width, shown) if width > 1 else shown
            return width - left - right
        return master.winfo_width() - left - right

    def fit(self, width: int) -> None:
        """Use the largest mini-card text at which 13 cards fit in `width`."""
        if width <= 1 or not themes.alive(self):
            return
        size = self.SIZES[-1]
        for candidate in self.SIZES:
            spec = font("card", candidate, "bold")
            cell = max(text_width(self, spec, "10♠"), 3 * text_width(self, spec, "0")) + 8
            if cell * len(RANKS) <= width:
                size = candidate
                break
        if size != self.size and self._guard.allow():
            self.size = size
            for _card, button in self.buttons:
                button.configure(font=font("card", size, "bold"))
            notify_resized(self)

    def show_jokers(self, count: int) -> None:
        """Show only the first `count` joker buttons (the jokers this game
        has); the rest are hidden, not just greyed out."""
        jokers = [button for card, button in self.buttons if card.is_joker]
        for i, button in enumerate(jokers):
            if i < count:
                button.grid()
            else:
                button.grid_remove()
        self.shown_jokers = count
        if getattr(self, "_beside", None) is not None:
            self.beside_jokers(self._beside)        # move it up next to the jokers left

    def beside_jokers(self, widget: tk.Misc) -> None:
        """Put `widget` (a child of this grid) in the joker row, after the jokers."""
        self._beside = widget
        start = getattr(self, "shown_jokers", self.jokers) * 3
        widget.grid(row=len(SUITS), column=start, columnspan=len(RANKS) - start,
                    sticky="w", padx=(8 if start else 0, 0))

    def _add(self, card: Card, row: int, col: int, columnspan: int = 1) -> None:
        text = card.name if card.is_joker else card.label()
        button = tk.Button(self, text=text, width=10 if card.is_joker else 3, relief="flat",
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
        chosen = self.selected is not None and card.key() == self.selected
        bg = t.select if chosen else (joker_colors(card, t)[0] if card.is_joker else t.card)
        fg = readable_on(t.select) if chosen else suit_color(card, t)
        button.configure(background=bg, foreground=fg,
                         activebackground=t.select if chosen else t.card_edge,
                         activeforeground=fg, disabledforeground=t.muted,
                         highlightthickness=0)
        if str(button.cget("state")) == "disabled":
            button.configure(background=t.panel)

    def set_available(self, labels: Iterable[str]) -> None:
        """Enable only cards whose key (Card.key(): "A♥", "🃏:big") is in `labels`."""
        labels = set(labels)
        for card, button in self.buttons:
            button.configure(state="normal" if card.key() in labels else "disabled")
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
        if widget.winfo_class() in _SELF_SCROLLING and _can_scroll(widget):
            return None                      # the list scrolls itself
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


def _can_scroll(widget: tk.Misc) -> bool:
    """True if a list, table or text has more lines than it shows."""
    try:
        first, last = (float(v) for v in widget.yview())
    except (tk.TclError, AttributeError, ValueError, TypeError):
        return True
    return first > 0.0 or last < 1.0


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
    guard = FlipGuard()

    def arrange(_event=None):
        width = frame.winfo_width()
        widths = [child.winfo_reqwidth() + gap for child in children]
        columns = len(children)
        if width > 1:
            while columns > 1 and sum(sorted(widths, reverse=True)[:columns]) > width:
                columns -= 1
        if columns == state["columns"] or (state["columns"] and not guard.allow()):
            return
        state["columns"] = columns
        for i, child in enumerate(children):
            child.grid(row=i // columns, column=i % columns, sticky="w", padx=(0, gap))
        notify_resized(frame)
    frame.bind("<Configure>", arrange, add="+")
    arrange()