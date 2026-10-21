"""
==============================================
GAME PLAYER AND GAME ASSISTANT PAGES
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/gui_game.py
Status: ACTIVE
Version: 1.3
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.3 CHANGES (2026-10-20):
- Two switches instead of one, each for this page only: Show odds
  (Ctrl+O) for the odds under the cards and the odds table, and Show
  counts (new Ctrl+K) for the card counts, the plays and the cards left.
  Picking a side view whose switch is off (or Ctrl+P / Ctrl+L) turns it
  on, and a line under the view says which switch is off. Defaults come
  from Settings (show_odds, show_counts). In a narrow window the toolbar
  labels shorten to "Odds" and "Counts".
- Odds table: the card is the first column, then the box. It starts
  sorted by Best, highest first; clicking a heading sorts by it, highest
  first, then lowest first, then back to box order (7 8 9 / 4 5 6 /
  1 2 3), and the heading shows ↓ or ↑. Failed boxes stay at the bottom.
- Call buttons in the new engine order: ▲= Higher or Equal, ▲ Higher,
  ▼ Lower, ▼= Lower or Equal.
- Help on its own (no app) opens in a DocView window, like the app pages.

VERSION 1.2 CHANGES (2026-10-20):
- Pages, not pop-ups: each tool builds inside the frame it is given (a
  page of the one-window app). New Game settings and the Assistant's
  nine-card picker open beside the board; the odds table (Ctrl+P) and
  cards left (Ctrl+L) show in the side panel; How to Play / Strategy /
  Shortcuts / About open as app pages; the game-over message is the
  banner. The menu bar is gone (the sidebar and toolbar replace it).
- Resizable: the board and cards grow and shrink with the window. The
  cards get the width their height allows and the side panel the rest
  (within SIDE_WIDTH); the side panel scrolls when the window is too short
  for it, the view switches wrap, and the toolbar drops its shortcut hints
  when narrow. The Assistant's flipped-card grid shrinks to fit, with
  "Flipped:" beside the Joker button to save a row.
- Call buttons in pairs: ▲ Higher, ▲= Higher or Equal (one colour), then
  ▼ Lower, ▼= Lower or Equal (another colour), across the whole page; the
  text shrinks to fit a narrow window.
- Calls that make no sense are greyed out (engine.offered_calls): plain
  Lower on a 2, plain Higher on an A, and plain calls on a joker while
  inclusive calls are left. A shortcut for one says why in the hint line,
  using the engine's reason (call_blocked_reason), and only suggests an
  inclusive call when one is left. The joker hint only promises a
  recovery when a box has failed.
- The odds table follows the button order and has the "Best" (plain
  call) column of the old Probabilities window back. Only the side view
  that is showing is filled in, and the odds are worked out once a turn.
- "Show odds & counts" (Ctrl+O) now shows or hides the odds under the
  cards, the card count and the plays together. The tiles always show.
- Keys only act on the page that is showing, and never while typing in a
  field (Ctrl shortcuts included). A read-only field, like the cards-left
  text, doesn't count, so clicking it never switches the shortcuts off.

VERSION 1.1 CHANGES (2026-10-20):
- New look: cards drawn on a canvas (btb.widgets), colours from the chosen
  theme (btb.theme), switchable live from View > Theme.
- Result banner at the top in large text: your call, the card drawn and
  the outcome, coloured green (correct), red (wrong) or gold (recovery).
  Hints and errors show in the line under it.
- Side panel: draw pile / inclusive calls / boxes alive tiles, the three
  counts (each with the call it favours, from engine.count_lean) and a
  plain reading that says when they disagree, and a play history.
- Menu bar (Game, View, Help) lists every action and shortcut; New Game
  and Undo also sit in the toolbar. The seven-button grid and the bottom
  status bar are gone.
- Odds under each card can be switched on and off (View > Show Odds on
  Cards, Ctrl+O, or the toolbar). Windows start from the default set in
  the launcher's Settings; Ctrl+O only changes the window you are in.
- Each box shows its number key under the card.
- Assistant: a grid of mini cards replaces the "card you flipped"
  dropdown; cards no longer in the pile are greyed out.
- Help > About This Tool explains the window.

VERSION 1.0 CHANGES (2026-10-20):
- New. Replaces BTBGamePlayer.py and BTBGameAid.py.
- AssistantGUI now subclasses PlayerGUI, so the two share one window.
- Game-over message on a win or a loss.
- Keys, undo and buttons before a game no longer crash.
- Recovery picked on the board after the flip, with a Skip button.
- Assistant: jokers handled, undo refunds inclusive calls, two jokers
  tracked separately, labels refresh after every play.

DESCRIPTION:
-----------
Thin Tkinter layers over btb.engine. They turn clicks and keys into engine
calls and draw the resulting state. No rules, odds or counting here.

  Game Player    - shuffled deck, live odds, three counts, undo, shortcuts
  Game Assistant - mirror a real-deck game: pick the nine box cards, then
                   pick each card you actually flip

Each tool is a page: it builds itself inside the frame it is given (a page
of the one-window app in btb/app.py). Given a window of its own instead, it
works on its own too (the tests use that).

DEPENDENCIES:
------------
- btb.engine, btb.text, btb.theme, btb.settings, btb.widgets
- Standard library: tkinter, dataclasses, typing

KEY FUNCTIONS:
-------------
- GameSettings -> jokers, inclusive calls, show failed cards
- GameSetupPanel -> the New Game settings, beside the board
- CardPickerPanel -> pick the nine box cards (Assistant), beside the board
- PlayerGUI(parent, app).new_game / box_clicked / make_call / undo /
  skip_recovery / toggle_odds / toggle_counts / show_probabilities /
  show_remaining_cards / choose_view / sort_odds / update_side_view
- odds_columns(), odds_rows(box, odds), sort_odds_rows(rows, column, mode)
  -> the odds table's columns, rows and sorting
- AssistantGUI -> same page plus the flipped-card grid

ERROR HANDLING:
--------------
RulesError from the engine and invalid settings are shown on the page
(hint line or the settings panel); nothing crashes and nothing pops up.

NOTES:
-----
- Keys are bound on the window and only act on the page that is showing,
  and never while you are typing in a field.
- Plain-letter shortcuts (W, D, S, A, number keys) ignore Ctrl.
- box_views[i] is the CardView for box i; its describe() gives the text a
  player would read ("A♥", "Failed", "Failed\\nK♥").
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, List, Optional

from . import settings as app_settings
from . import text
from . import theme as themes
from .engine import (
    BOX_SIZE, CALL_LABELS, COUNT_METHOD_NAMES, HIGHER, HIGHER_EQUAL, JOKER_USE_INCLUSIVE,
    LOWER, LOWER_EQUAL, MAX_JOKERS, NO_INCLUSIVE_LEFT, NOTHING_HIGHER, NOTHING_LOWER,
    OFFER_ORDER, Card, Game, PlayResult, RulesError, call_blocked_reason, count_lean,
    max_inclusive_calls, offered_calls,
)
from .theme import Theme, font
from .widgets import (
    CardGrid, CardView, DocView, ScrollFrame, StatTile, card_name, flow_row, readable_on,
    scrolled_tree, text_width, wrap_to,
)

CONTROL_MASK = 0x0004

CALL_ORDER = OFFER_ORDER          # ▲= ▲ ▼ ▼=: plain calls in the middle (engine.OFFER_ORDER)
CALL_KEYS = {HIGHER: "W", LOWER: "S", HIGHER_EQUAL: "D", LOWER_EQUAL: "A"}
CALL_ARROWS = {HIGHER: "▲", LOWER: "▼", HIGHER_EQUAL: "▲=", LOWER_EQUAL: "▼="}
CALL_SHORT = {HIGHER: "Higher", LOWER: "Lower", HIGHER_EQUAL: "Higher/Eq",
              LOWER_EQUAL: "Lower/Eq"}
POSITION_LABELS = {pos: key for key, pos in text.POSITION_KEYS.items()}

BANNER_KINDS = ("neutral", "good", "bad", "recover")
SIDE_VIEWS = (("count", "Count & plays"), ("odds", "Odds table"), ("cards", "Cards left"))
VIEW_SWITCH = {"count": "counts", "odds": "odds", "cards": "counts"}   # the switch each needs
TEXT_INPUTS = (tk.Entry, ttk.Entry, tk.Text, tk.Spinbox)  # ttk.Combobox is a ttk.Entry


def _typing_in(widget) -> bool:
    """True if `widget` is a field you can type in right now. A read-only
    one (the cards-left text, a fixed-choice list) leaves the keys to the
    game, so clicking it doesn't switch the shortcuts off."""
    if not isinstance(widget, TEXT_INPUTS):
        return False
    try:
        if isinstance(widget, ttk.Entry):
            return not (widget.instate(["disabled"]) or widget.instate(["readonly"]))
        return str(widget.cget("state")) == "normal"
    except tk.TclError:
        return False


@dataclass
class GameSettings:
    jokers: int = 0
    inclusive_calls: int = 5
    show_failed: bool = True


def _percent(p: float) -> str:
    return f"{p * 100:.1f}%"


def _rank_name(rank: int) -> str:
    return {0: "Joker", 11: "Jack", 12: "Queen", 13: "King", 14: "Ace"}.get(rank, str(rank))


def _why_not(card: Card, call: str, inclusive_left: int) -> str:
    """Why a call isn't offered on this card, in words (the hint line).
    The reason itself comes from the engine (call_blocked_reason)."""
    reason = call_blocked_reason(card, call, inclusive_left)
    tie = inclusive_left > 0
    if reason == NO_INCLUSIVE_LEFT:
        return "No inclusive calls left!"
    if reason == JOKER_USE_INCLUSIVE:
        return ("On a joker, use Higher or Equal / Lower or Equal: it wins just as surely, "
                "and it recovers a failed box if you have one.")
    if reason == NOTHING_LOWER:
        return "Nothing is lower than a 2: call Higher" + (
            " (or Lower or Equal, which wins on a tie)." if tie else ".")
    if reason == NOTHING_HIGHER:
        return "Nothing is higher than an A: call Lower" + (
            " (or Higher or Equal, which wins on a tie)." if tie else ".")
    return ""


# --------------------------------------------------------------------------- #
# The odds table
# --------------------------------------------------------------------------- #

def odds_columns() -> dict:
    """Odds-table columns: the card first, its box, the calls in button
    order, the tie chance and the best plain call."""
    return {"card": ("Card", 58, "center"), "box": ("Box", 42, "center"),
            **{call: (CALL_ARROWS[call], 60, "center") for call in CALL_ORDER},
            "exact": ("Tie", 60, "center"), "best": ("Best", 78, "center")}


def odds_rows(box: List[Optional[Card]], odds_all) -> List[tuple]:
    """(position, values shown, sort keys by column) for each box. Sort
    keys are None for a failed box (it has no odds), so it sorts last."""
    blanks = len(CALL_ORDER) + 2
    rows = []
    for position, (card, odds) in enumerate(zip(box, odds_all)):
        key = POSITION_LABELS[position]
        if card is None:
            rows.append((position, ("Failed", key, *[""] * blanks), None))
        elif odds is None:
            rows.append((position, (card, key, *["-"] * blanks), None))
        else:
            if card.is_joker:
                best_text, best = "Sure win", 1.0
            else:
                call, best = odds.best_plain()
                best_text = f"{CALL_ARROWS[call]} {_percent(best)}"
            keys = {"card": 15 if card.is_joker else card.rank,    # a joker beats an A
                    "box": int(key), "exact": odds.exact, "best": best,
                    **{call: odds.for_call(call) for call in CALL_ORDER}}
            rows.append((position, (card, key, *(_percent(odds.for_call(c))
                                                 for c in CALL_ORDER),
                                    _percent(odds.exact), best_text), keys))
    return rows


def sort_odds_rows(rows: List[tuple], column: str, mode: str) -> List[tuple]:
    """Sort odds_rows() by `column`: "desc" highest first, "asc" lowest
    first, "box" in box order (7 8 9 / 4 5 6 / 1 2 3). Ties keep box
    order; rows with no odds (failed boxes) always come last."""
    in_order = sorted(rows, key=lambda row: row[0])
    live = [row for row in in_order if row[2] is not None]
    dead = [row for row in in_order if row[2] is None]
    if mode != "box":
        live.sort(key=lambda row: row[2][column], reverse=(mode == "desc"))
    return live + dead


# --------------------------------------------------------------------------- #
# In-page panels
# --------------------------------------------------------------------------- #

class GameSetupPanel:
    """New Game settings, shown beside the board instead of a pop-up."""

    def __init__(self, parent: tk.Misc, on_start: Callable[[GameSettings], None],
                 on_cancel: Callable[[], None]):
        self.on_start, self.on_cancel = on_start, on_cancel
        self.frame = ttk.Frame(parent, style="Panel.TFrame", padding=(14, 12))
        ttk.Label(self.frame, text="New Game", style="PanelHeading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.joker_var = tk.StringVar(value="0")
        self.calls_var = tk.StringVar(value="5")
        self.show_var = tk.BooleanVar(value=True)
        ttk.Label(self.frame, text="Jokers in the deck:", style="Panel.TLabel").grid(
            row=1, column=0, sticky="w", pady=3)
        self.joker_combo = ttk.Combobox(self.frame, textvariable=self.joker_var, width=6,
                                        state="readonly", values=list(range(MAX_JOKERS + 1)))
        self.joker_combo.grid(row=1, column=1, sticky="w", padx=(10, 0))
        ttk.Label(self.frame, text="Inclusive calls:", style="Panel.TLabel").grid(
            row=2, column=0, sticky="w", pady=3)
        self.calls_combo = ttk.Combobox(self.frame, textvariable=self.calls_var, width=6)
        self.calls_combo.grid(row=2, column=1, sticky="w", padx=(10, 0))
        ttk.Checkbutton(self.frame, text="Show failed cards when recovering",
                        variable=self.show_var, style="Panel.TCheckbutton").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.help_label = ttk.Label(self.frame, text="", style="PanelMuted.TLabel")
        self.help_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.error_label = ttk.Label(self.frame, text="", style="Error.TLabel", wraplength=300)
        wrap_to(self.error_label, pad=20)
        buttons = ttk.Frame(self.frame, style="Panel.TFrame")
        buttons.grid(row=6, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Button(buttons, text="Start Game", style="Accent.TButton",
                   command=self.start).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=self.on_cancel).pack(side="left", padx=6)
        for widget in (self.joker_combo, self.calls_combo):
            widget.bind("<Return>", lambda e: self.start())
            widget.bind("<Escape>", lambda e: self.on_cancel())
        self.joker_var.trace_add("write", self._update_range)
        self._update_range()

    def load(self, settings: GameSettings) -> None:
        self.joker_var.set(str(settings.jokers))
        self.calls_var.set(str(settings.inclusive_calls))
        self.show_var.set(settings.show_failed)
        self.error_label.grid_remove()

    def _update_range(self, *_):
        jokers = int(self.joker_var.get())
        limit = max_inclusive_calls(jokers)
        self.calls_combo["values"] = list(range(limit + 1))
        self.help_label.config(text=f"Inclusive calls: 0 to {limit} with {jokers} joker(s).")

    def show_error(self, message: str) -> None:
        self.error_label.config(text=message)
        self.error_label.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def start(self) -> None:
        try:
            jokers = int(self.joker_var.get())
            calls = int(self.calls_var.get())
        except ValueError:
            self.show_error("Please enter whole numbers.")
            return
        limit = max_inclusive_calls(jokers)
        if not 0 <= calls <= limit:
            self.show_error(f"Inclusive calls must be 0-{limit} with {jokers} joker(s).")
            return
        self.error_label.grid_remove()
        self.on_start(GameSettings(jokers, calls, bool(self.show_var.get())))


class CardPickerPanel:
    """Pick the nine cards dealt into the box (Game Assistant), beside the board.

    Each physical card, including each joker, has its own button, so picking
    one joker never removes the other.
    """

    def __init__(self, parent: tk.Misc, theme: Theme, jokers: int,
                 on_pick: Callable[[List[Card]], None], on_done: Callable[[List[Card]], None],
                 on_cancel: Callable[[], None]):
        self.result: Optional[List[Card]] = None
        self.picked: List[Card] = []
        self._picked_buttons: List[tk.Button] = []
        self._on_pick, self._on_done = on_pick, on_done
        self.frame = ttk.Frame(parent, style="Panel.TFrame", padding=(14, 12))
        self.info = ttk.Label(self.frame, text="", style="PanelHeading.TLabel")
        self.info.pack(anchor="w")
        hint = ttk.Label(self.frame, text="Click the cards in your box, from the top-left box "
                         "to the bottom-right box.", style="PanelMuted.TLabel", wraplength=420)
        hint.pack(anchor="w", fill="x", pady=(2, 8))
        wrap_to(hint)
        self.grid = CardGrid(self.frame, theme, self._pick, jokers=jokers, style="Panel.TFrame")
        self.grid.pack(anchor="w")
        controls = ttk.Frame(self.frame, style="Panel.TFrame")
        controls.pack(anchor="w", pady=(10, 0))
        ttk.Button(controls, text="Undo Pick", command=self._unpick).pack(side="left")
        ttk.Button(controls, text="Cancel", command=on_cancel).pack(side="left", padx=6)
        self._update_info()

    def _update_info(self):
        self.info.config(text=f"Deal: pick the nine box cards ({len(self.picked)}/{BOX_SIZE})")

    def _pick(self, card: Card, button: tk.Button):
        if len(self.picked) >= BOX_SIZE or str(button.cget("state")) == "disabled":
            return
        self.picked.append(card)
        self._picked_buttons.append(button)
        self.grid.disable(button)
        self._update_info()
        self._on_pick(list(self.picked))
        if len(self.picked) == BOX_SIZE:
            self.result = list(self.picked)
            self._on_done(self.result)

    def _unpick(self):
        if self.picked:
            self.picked.pop()
            self.grid.enable(self._picked_buttons.pop())
            self._update_info()
            self._on_pick(list(self.picked))


# --------------------------------------------------------------------------- #
# Game Player
# --------------------------------------------------------------------------- #

class PlayerGUI:
    """🎮 Game Player: a shuffled deck, live odds, counts, undo, shortcuts."""

    TITLE = "Beat the Box: Game Player"
    HEADING = "Game Player"
    TOOL = "player"
    WELCOME = "Welcome to Beat the Box! Press New Game (Ctrl+N) to start."
    START_MESSAGE = "Game started! Select a box, then make your call."
    CARD_SIZE = (96, 128)
    HISTORY_ROWS = 4                # the list starts this tall and grows into spare room
    SIDE_WIDTH = (300, 520)         # narrowest and widest the side panel gets

    def __init__(self, parent: tk.Misc, app=None):
        self.app = app
        self.root = parent.winfo_toplevel()
        self.standalone = parent is self.root
        if self.standalone:
            self.root.title(self.TITLE)
        self.theme: Theme = themes.use(self.root)
        self.game: Optional[Game] = None
        self.settings = GameSettings()
        self.selected: Optional[int] = None
        self.history: List[str] = []
        self.mode = "play"                       # play | setup | pick
        self._text_widgets: List[tk.Misc] = []
        self._windows: List[tk.Misc] = []        # only used when standalone
        self.banner_var = tk.StringVar(value="Beat the Box")
        self.banner_kind = "neutral"
        self.status_var = tk.StringVar(value=self.WELCOME)
        self.cards_remaining_var = tk.StringVar(value="-")
        self.inclusive_var = tk.StringVar(value="-")
        self.boxes_var = tk.StringVar(value="-")
        self.count_vars = [tk.StringVar(value="0") for _ in COUNT_METHOD_NAMES]
        self.lean_var = tk.StringVar(value="")
        defaults = app_settings.load()
        self.odds_var = tk.BooleanVar(value=bool(defaults["show_odds"]))
        self.counts_var = tk.BooleanVar(value=bool(defaults["show_counts"]))
        self.side_view = tk.StringVar(value="count")

        self.frame = ttk.Frame(parent, padding=14)
        self.frame.grid(row=0, column=0, sticky="nsew")
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        self.build()
        self.bind_shortcuts()
        themes.subscribe(self.frame, self.on_theme)
        self.refresh()

    # ----- layout --------------------------------------------------------- #

    def build(self):
        f = self.frame
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        self.toolbar = toolbar = ttk.Frame(f)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.heading_label = ttk.Label(toolbar, text=self.HEADING, style="Heading.TLabel")
        self.heading_label.pack(side="left")
        counts_check = ttk.Checkbutton(toolbar, text="Show counts (Ctrl+K)",
                                       variable=self.counts_var, command=self.on_counts_changed)
        counts_check.pack(side="right", padx=(10, 0))
        odds_check = ttk.Checkbutton(toolbar, text="Show odds (Ctrl+O)",
                                     variable=self.odds_var, command=self.on_odds_changed)
        odds_check.pack(side="right", padx=(10, 0))
        self.odds_check, self.counts_check = odds_check, counts_check
        undo_button = ttk.Button(toolbar, text="Undo (Ctrl+Z)", command=self.undo)
        undo_button.pack(side="right", padx=4)
        new_button = ttk.Button(toolbar, text="New Game (Ctrl+N)", style="Accent.TButton",
                                command=self.new_game)
        new_button.pack(side="right", padx=4)
        # In a narrow window the toolbar drops the shortcut hints.
        self._toolbar_labels = []
        for widget, short in ((new_button, "New Game"), (undo_button, "Undo"),
                              (odds_check, "Odds"), (counts_check, "Counts")):
            long = str(widget.cget("text"))
            long_width = widget.winfo_reqwidth()
            widget.configure(text=short)
            self._toolbar_labels.append((widget, long, short, long_width))
            widget.configure(text=long)
        self.toolbar_short = False
        toolbar.bind("<Configure>", self._fit_toolbar)

        # The result banner: what you called and what happened, big.
        self.banner = tk.Frame(f, borderwidth=0, highlightthickness=0)
        self.banner.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 10))
        self.banner_label = tk.Label(self.banner, textvariable=self.banner_var, anchor="w",
                                     justify="left", font=font("ui", 17, "bold"), padx=14)
        self.banner_label.grid(row=0, column=0, sticky="ew", pady=(8, 0))
        self.status_label = tk.Label(self.banner, textvariable=self.status_var, anchor="w",
                                     justify="left", font=font("ui", 11), padx=14)
        self.status_label.grid(row=1, column=0, sticky="ew", pady=(2, 8))
        self.skip_button = ttk.Button(self.banner, text="Skip Recovery",
                                      command=self.skip_recovery)
        self.skip_button.grid(row=0, column=1, rowspan=2, padx=14)
        self.skip_button.grid_remove()
        self.banner.columnconfigure(0, weight=1)
        self.banner.bind("<Configure>", self._wrap_banner)

        # The board grows and shrinks with the window; so do the cards.
        self.board = board = ttk.Frame(f)
        board.grid(row=2, column=0, sticky="nsew")
        width, height = self.CARD_SIZE
        self.box_views: List[CardView] = []
        for i in range(BOX_SIZE):
            view = CardView(board, self.theme, width, height,
                            command=lambda pos=i: self.box_clicked(pos))
            view.grid(row=i // 3, column=i % 3, padx=3, pady=2, sticky="nsew")
            self.box_views.append(view)
        for n in range(3):
            board.rowconfigure(n, weight=1, uniform="rows", minsize=90)
            board.columnconfigure(n, weight=1, uniform="cols", minsize=70)

        # The side panel scrolls if the window is too short for it, and takes
        # whatever width the cards don't need (between SIDE_WIDTH's limits).
        self.side_scroll = ScrollFrame(f, width=self.SIDE_WIDTH[0])
        self.side_scroll.grid(row=2, column=1, sticky="ns", padx=(16, 0))
        self.side = self.side_scroll.body
        self.build_side_panel()
        f.bind("<Configure>", self._share_width, add="+")
        board.bind("<Configure>", self._share_width, add="+")

        # The calls span the page; their text shrinks if the window is narrow.
        self.actions = ttk.Frame(f)
        self.actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        prefix = f"Page{id(self)}"
        self._call_styles = (f"{prefix}.CallUp.TButton", f"{prefix}.CallDown.TButton")
        self._call_font_size = 0
        self.call_buttons = {}
        for col, call in enumerate(CALL_ORDER):
            style = self._call_styles[0 if call in (HIGHER, HIGHER_EQUAL) else 1]
            btn = ttk.Button(self.actions, style=style,
                             text=f"{CALL_ARROWS[call]} {CALL_LABELS[call]} ({CALL_KEYS[call]})",
                             command=lambda c=call: self.make_call(c))
            btn.grid(row=0, column=col, padx=3, sticky="ew")
            self.actions.columnconfigure(col, weight=1, uniform="calls")
            self.call_buttons[call] = btn
        self.actions.bind("<Configure>", self._fit_call_buttons)
        self._fit_call_buttons()
        self.paint()

    def _fit_call_buttons(self, _event=None):
        """Largest text size (12pt down to 8pt) at which every call label fits."""
        width = self.actions.winfo_width()
        if width <= 1:
            width = 1000
        room = width / len(self.call_buttons) - 30
        labels = [str(b.cget("text")) for b in self.call_buttons.values()]
        size = 8
        for candidate in (12, 11, 10, 9):
            spec = font("ui", candidate, "bold")
            if all(text_width(self.actions, spec, label) <= room for label in labels):
                size = candidate
                break
        if size != self._call_font_size:
            self._call_font_size = size
            style = ttk.Style(self.root)
            for name in self._call_styles:
                style.configure(name, font=font("ui", size, "bold"))

    def _fit_toolbar(self, _event=None):
        """Long labels ("New Game (Ctrl+N)") when they fit, short ones when not."""
        width = self.toolbar.winfo_width()
        if width <= 1:
            return
        need = self.heading_label.winfo_reqwidth() + sum(
            long_width for *_rest, long_width in self._toolbar_labels) + 40   # + gaps
        short = width < need
        if short != self.toolbar_short:
            self.toolbar_short = short
            for widget, long, brief, _width in self._toolbar_labels:
                widget.configure(text=brief if short else long)

    def _share_width(self, _event=None):
        """Give the cards the width their height allows; the side panel gets
        the rest, within SIDE_WIDTH."""
        try:
            room = self.frame.winfo_width() - 28
            board_height = self.board.winfo_height()
        except tk.TclError:
            return
        if room <= 1 or board_height <= 1:
            return
        m = CardView.MARGIN
        card_height = max(CardView.MIN_HEIGHT, board_height / 3 - 2 * m - CardView.FOOTER - 4)
        board_need = 3 * (card_height * CardView.ASPECT + 2 * m + 6)
        low, high = self.SIDE_WIDTH
        self.side_scroll.set_width(int(max(low, min(high, room - board_need - 16))))

    def build_side_panel(self):
        side = self.side
        tiles = ttk.Frame(side)
        tiles.pack(fill="x")
        for col, (caption, var) in enumerate((("Draw pile", self.cards_remaining_var),
                                              ("Inclusive calls", self.inclusive_var),
                                              ("Boxes alive", self.boxes_var))):
            StatTile(tiles, caption, var).grid(row=0, column=col, sticky="ew",
                                               padx=(0 if col == 0 else 6, 0))
            tiles.columnconfigure(col, weight=1)

        self.setup_panel = GameSetupPanel(side, self.new_game, self.cancel_setup)
        self.picker_panel: Optional[CardPickerPanel] = None
        self.extra_panel = self.build_side_extra(side)

        # Two switches: Show odds (Ctrl+O) for the odds table, Show counts
        # (Ctrl+K) for the count & plays and the cards left. Picking a view
        # (or Ctrl+P / Ctrl+L) turns on the switch it needs.
        self.aids = ttk.Frame(side, style="Panel.TFrame", padding=(12, 6))
        self.views = views = ttk.Frame(self.aids, style="Panel.TFrame")
        views.pack(fill="x")
        self.view_buttons = [
            ttk.Radiobutton(views, text=label, value=value, variable=self.side_view,
                            style="Panel.TRadiobutton",
                            command=lambda v=value: self.choose_view(v))
            for value, label in SIDE_VIEWS]
        flow_row(views, self.view_buttons)

        self.count_frame = ttk.Frame(self.aids, style="Panel.TFrame")
        counts = ttk.Frame(self.count_frame, style="Panel.TFrame")
        counts.pack(fill="x", pady=(6, 0))
        ttk.Label(counts, text="Card count", style="PanelHeading.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w")
        for col, (name, var) in enumerate(zip(COUNT_METHOD_NAMES, self.count_vars)):
            ttk.Label(counts, text=name, style="PanelMuted.TLabel").grid(
                row=1, column=col, sticky="w")
            ttk.Label(counts, textvariable=var, style="Panel.TLabel",
                      font=font("ui", 13, "bold")).grid(row=2, column=col, sticky="w")
            counts.columnconfigure(col, weight=1)
        lean = ttk.Label(counts, textvariable=self.lean_var, style="Panel.TLabel",
                         wraplength=360)
        lean.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 0))
        wrap_to(lean)
        ttk.Label(self.count_frame, text="Plays", style="PanelHeading.TLabel").pack(
            anchor="w", pady=(6, 0))
        inner = ttk.Frame(self.count_frame, style="Panel.TFrame")
        inner.pack(fill="both", expand=True, pady=(4, 0))
        self.history_list = tk.Listbox(inner, height=self.HISTORY_ROWS, width=30,
                                       activestyle="none", font=font("ui", 10))
        scroll = ttk.Scrollbar(inner, command=self.history_list.yview)
        self.history_list.configure(yscrollcommand=scroll.set)
        self.history_list.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.odds_frame = ttk.Frame(self.aids, style="Panel.TFrame")
        holder, self.prob_tree = scrolled_tree(self.odds_frame, odds_columns(), height=9,
                                               style="Panel.TFrame")
        self.odds_sort = ("best", "desc")      # Best first, highest at the top
        for col in self.prob_tree["columns"]:
            self.prob_tree.heading(col, command=lambda c=col: self.sort_odds(c))
        self._label_odds_headings()
        holder.pack(fill="both", expand=True, pady=(8, 0))
        note = ttk.Label(self.odds_frame, text="Chance each call wins against the cards still "
                         "in the pile. Tie = exact match or joker: the recovery chance on an "
                         "inclusive call. Best = the better plain call. Click a heading to "
                         "sort: highest first, then lowest first, then by box.",
                         style="PanelMuted.TLabel", wraplength=360)
        note.pack(anchor="w", fill="x", pady=(6, 0))
        wrap_to(note)

        self.cards_frame = ttk.Frame(self.aids, style="Panel.TFrame")
        cards_scroll = ttk.Scrollbar(self.cards_frame)
        self.cards_text = tk.Text(self.cards_frame, width=24, height=10,
                                  font=font("mono", 11), padx=10, pady=8,
                                  yscrollcommand=cards_scroll.set)
        cards_scroll.configure(command=self.cards_text.yview)
        themes.style_text_widget(self.cards_text, self.theme)
        self._text_widgets.append(self.cards_text)
        cards_scroll.pack(side="right", fill="y", pady=(8, 0))
        self.cards_text.pack(side="left", fill="both", expand=True, pady=(8, 0))

        # Under the view: which switch is off, and how to turn it on.
        self.aids_note_var = tk.StringVar(value="")
        self.aids_note = ttk.Label(self.aids, textvariable=self.aids_note_var,
                                   style="PanelMuted.TLabel", wraplength=300)
        wrap_to(self.aids_note)

        self.aids_hint = ttk.Frame(side, style="Panel.TFrame", padding=(12, 10))
        hint = ttk.Label(self.aids_hint, text="Odds and card counts are hidden. Show odds "
                         "(Ctrl+O) adds the chances under each card and the odds table. "
                         "Show counts (Ctrl+K) adds the card counts, your plays and the "
                         "cards left.", style="PanelMuted.TLabel", wraplength=300)
        hint.pack(anchor="w", fill="x")
        wrap_to(hint)
        self.layout_side()

    def build_side_extra(self, side: ttk.Frame) -> Optional[ttk.Frame]:
        """Hook for subclasses: a panel between the tiles and the odds and counts views."""
        return None

    def layout_side(self):
        """Show the side-panel parts that fit the current mode and switches."""
        parts = [self.setup_panel.frame, self.aids, self.aids_hint, self.count_frame,
                 self.odds_frame, self.cards_frame]
        if self.picker_panel is not None:
            parts.append(self.picker_panel.frame)
        if self.extra_panel is not None:
            parts.append(self.extra_panel)
        for part in parts:
            part.pack_forget()
        if self.mode == "setup":
            self.setup_panel.frame.pack(fill="x", pady=(10, 0))
            self.side_scroll.update_layout()
            return
        if self.mode == "pick" and self.picker_panel is not None:
            self.picker_panel.frame.pack(fill="x", pady=(10, 0))
            self.side_scroll.update_layout()
            return
        if self.extra_panel is not None:
            self.extra_panel.pack(fill="x", pady=(10, 0))
        self.aids_note.pack_forget()
        available = self.available_views()
        if available:
            if self.side_view.get() not in available:
                self.side_view.set(available[0])
            self.aids.pack(fill="both", expand=True, pady=(10, 0))
            view = {"count": self.count_frame, "odds": self.odds_frame,
                    "cards": self.cards_frame}[self.side_view.get()]
            view.pack(fill="both", expand=True)
            note = ("Card counts are hidden: Show counts (Ctrl+K)."
                    if not self.counts_var.get() else
                    "Odds are hidden: Show odds (Ctrl+O)." if not self.odds_var.get() else "")
            self.aids_note_var.set(note)
            if note:
                self.aids_note.pack(anchor="w", fill="x", pady=(6, 2))
            self.update_side_view()
        else:
            self.aids_hint.pack(fill="x", pady=(10, 0))
        self.side_scroll.update_layout()

    def available_views(self) -> List[str]:
        """The side views whose switch is on, in tab order."""
        on = {"odds": bool(self.odds_var.get()), "counts": bool(self.counts_var.get())}
        return [value for value, _label in SIDE_VIEWS if on[VIEW_SWITCH[value]]]

    def choose_view(self, view: str):
        """A view picked in the side panel: turn on its switch if needed."""
        self.side_view.set(view)
        self._switch_for(view).set(True)
        self.layout_side()
        self.refresh()

    def _switch_for(self, view: str) -> tk.BooleanVar:
        return self.odds_var if VIEW_SWITCH[view] == "odds" else self.counts_var

    def _wrap_banner(self, _event=None):
        """Wrap the banner text to the space left beside the Skip button."""
        width = self.banner.winfo_width()
        if width <= 1:
            return
        reserve = (self.skip_button.winfo_reqwidth() + 28
                   if self.skip_button.winfo_manager() else 0)
        wrap = max(200, width - 30 - reserve)
        self.banner_label.configure(wraplength=wrap)
        self.status_label.configure(wraplength=wrap)

    # ----- keys ----------------------------------------------------------- #

    def active(self) -> bool:
        """True while this page is the one showing."""
        try:
            return bool(self.frame.winfo_ismapped())
        except tk.TclError:
            return False

    def bind_shortcuts(self):
        actions = {
            "higher": lambda: self.make_call(HIGHER),
            "lower": lambda: self.make_call(LOWER),
            "higher_equal": lambda: self.make_call(HIGHER_EQUAL),
            "lower_equal": lambda: self.make_call(LOWER_EQUAL),
        }
        for _keys, _desc, action, sequences in text.SHORTCUTS:
            handler = actions.get(action) or getattr(self, action, None)
            if handler is None:
                continue
            plain_letter = action in actions
            for seq in sequences:
                self.root.bind(seq, self._key_handler(handler, plain_letter), add="+")
        keypad = {"7": "KP_Home", "8": "KP_Up", "9": "KP_Prior", "4": "KP_Left",
                  "5": "KP_Begin", "6": "KP_Right", "1": "KP_End", "2": "KP_Down",
                  "3": "KP_Next"}
        for key, pos in text.POSITION_KEYS.items():
            handler = self._key_handler(lambda p=pos: self.box_clicked(p), True)
            for seq in (f"<KeyPress-{key}>", f"<KeyPress-KP_{key}>",
                        f"<KeyPress-{keypad[key]}>"):
                try:
                    self.root.bind(seq, handler, add="+")
                except tk.TclError:
                    pass  # keysym not known on this platform

    def _key_handler(self, action, plain: bool):
        def handler(event):
            if not self.active():
                return None                      # another page is showing
            # Plain keys (W, 7, ...) must not fire on Ctrl+W, Ctrl+7, ...
            if plain and event.state & CONTROL_MASK:
                return None
            if _typing_in(event.widget):
                return None                      # typing in a field: the keys are its own
            action()
            return "break"
        return handler

    # ----- game flow ------------------------------------------------------ #

    def new_game(self, settings: Optional[GameSettings] = None) -> bool:
        """With settings: start a game. Without: show the New Game panel."""
        if settings is None:
            self.show_setup()
            return False
        game = self.create_game(settings)
        if game is None:
            return False
        self.start(settings, game, self.START_MESSAGE)
        return True

    def show_setup(self):
        self.setup_panel.load(self.settings)
        self.mode = "setup"
        self.layout_side()
        self.set_status("Choose the settings beside the board, then Start Game.")
        self.refresh()
        self.setup_panel.calls_combo.focus_set()

    def cancel_setup(self):
        self.mode = "play"
        self.layout_side()
        self.set_status("Select a box and make your call." if self.game else self.WELCOME)
        self.refresh()

    def start(self, settings: GameSettings, game: Game, message: str):
        self.settings = settings
        self.game = game
        self.selected = None
        self.history = []
        self.mode = "play"
        self.layout_side()
        self.set_banner("New game: nine cards are in the box", "neutral")
        self.set_status(message)
        self.refresh()
        self.frame.focus_set()

    def create_game(self, settings: GameSettings) -> Optional[Game]:
        return Game.new(settings.jokers, settings.inclusive_calls)

    def _need_game(self) -> bool:
        if self.game is None:
            self.set_status(self.WELCOME)
            return False
        return True

    def _need_play_mode(self) -> bool:
        if self.mode == "setup":
            self.set_status("Finish the New Game settings beside the board, or Cancel.")
            return False
        if self.mode == "pick":
            self.set_status("Pick the nine box cards beside the board first, or Cancel.")
            return False
        return True

    def box_clicked(self, position: int):
        if not self._need_play_mode() or not self._need_game():
            return
        if self.game.recovery_pending:
            if position in self.game.failed:
                card = self.game.recover(position)
                if self.history:
                    self.history[-1] += f"  ↺ box {POSITION_LABELS[position]}"
                self.set_banner(f"Recovered box {POSITION_LABELS[position]}: "
                                f"it's back with {card_name(card)}", "recover")
                self.set_status("Select a box and make your next call.")
                self.refresh()
                self.check_game_over()
            else:
                self.set_status("Pick a gold (failed) box to recover, or Skip Recovery.")
            return
        if self.game.is_over:
            self.set_status("The game is over. Press New Game (Ctrl+N) to play again.")
            return
        if self.game.box[position] is None:
            self.set_status("That box has failed. Choose another box.")
            return
        self.selected = position
        card = self.game.box[position]
        if card.is_joker and self.game.inclusive_left > 0:
            if self.game.failed:
                hint = "A joker: Higher or Equal / Lower or Equal is a sure win plus a recovery."
            else:
                hint = ("A joker: Higher or Equal / Lower or Equal is a sure win, but no box "
                        "has failed yet, so there is nothing to recover. You can hold it and "
                        "play another box first.")
        else:
            hint = "Make your call."
        self.set_status(f"Selected {card_name(card)}. {hint}")
        self.refresh()

    def drawn_card(self) -> Optional[Card]:
        """The card to flip: None means the top of the shuffled pile."""
        return None

    def make_call(self, call: str):
        if not self._need_play_mode() or not self._need_game():
            return
        game = self.game
        if game.recovery_pending:
            self.set_status("Pick a gold (failed) box to recover, or Skip Recovery.")
            return
        if game.is_over:
            self.set_status("The game is over. Press New Game (Ctrl+N) to play again.")
            return
        if self.selected is None or game.box[self.selected] is None:
            self.set_status("Select a box first (click it, or use the number keys).")
            return
        target = game.box[self.selected]
        if call not in offered_calls(target, game.inclusive_left):
            self.set_status(_why_not(target, call, game.inclusive_left))
            return
        try:
            drawn = self.drawn_card()
            if drawn is False:
                return
            result = game.play(self.selected, call, drawn)
        except RulesError as exc:
            self.set_status(str(exc))
            return
        self.after_play(result)

    def after_play(self, result: PlayResult):
        joker = result.drawn.is_joker or result.target.is_joker
        if result.success:
            verdict = "Joker: automatic success!" if joker else "Correct!"
            kind, mark = "good", "✓"
        else:
            verdict, kind, mark = "Wrong! The box fails.", "bad", "✗"
        if result.recovery_pending:
            kind = "recover"
        self.set_banner(f"{CALL_LABELS[result.call]} on {card_name(result.target)}  →  "
                        f"drew {card_name(result.drawn)}    {mark} {verdict}", kind)
        line = (f"{len(self.history) + 1:>2}. {CALL_SHORT[result.call]} on "
                f"{card_name(result.target)} → {card_name(result.drawn)}  {mark}")
        if result.recovery_pending:
            self.set_status("Exact match: recovery earned! Click a gold box to bring it back, "
                            "or Skip Recovery.")
        elif result.recovery_lost:
            line += "  (recovery lost)"
            self.set_status("Exact match, but no box has failed, so the recovery is lost.")
        else:
            self.set_status("Select a box and make your next call.")
        self.history.append(line)
        if not self.game.box[result.position]:
            self.selected = None
        self.refresh()
        self.check_game_over()

    def skip_recovery(self):
        if self.game is None or not self.game.recovery_pending:
            return
        self.game.skip_recovery()
        if self.history:
            self.history[-1] += "  (recovery skipped)"
        self.set_banner("Recovery skipped", "neutral")
        self.set_status("Select a box and make your next call.")
        self.refresh()
        self.check_game_over()

    def undo(self):
        if not self._need_play_mode() or not self._need_game():
            return
        if not self.game.undo():
            self.set_status("No moves to undo!")
            return
        if self.history:
            self.history.pop()
        if self.selected is not None and self.game.box[self.selected] is None:
            self.selected = None
        self.set_banner("Last play undone", "neutral")
        self.set_status("Select a box and make your call.")
        self.refresh()

    def check_game_over(self):
        """At the end of a game the banner says how it went (no pop-up)."""
        game = self.game
        if not game.is_over:
            return
        self.selected = None
        if game.won:
            boxes = f"{game.boxes_left} box{'es' if game.boxes_left != 1 else ''}"
            self.set_banner(f"★ You beat the box! {boxes} left.", "good")
            self.set_status("You got through the whole pile. Press New Game (Ctrl+N) "
                            "to play again.")
        else:
            self.set_banner("The box wins: all nine boxes failed.", "bad")
            self.set_status(f"{game.cards_left} cards were left in the pile. Press New Game "
                            "(Ctrl+N) to play again.")
        self.refresh()

    # ----- drawing -------------------------------------------------------- #

    def set_banner(self, message: str, kind: str = "neutral"):
        self.banner_var.set(message)
        self.banner_kind = kind if kind in BANNER_KINDS else "neutral"
        self.paint_banner()

    def set_status(self, message: str):
        game = self.game
        if (game and self.mode == "play" and not game.is_over and not game.recovery_pending
                and game.failed and game.inclusive_left > 0
                and any(c is not None and c.is_joker for c in game.box)):
            message += "  Tip: an inclusive call on the joker earns a recovery."
        self.status_var.set(message)

    def paint_banner(self):
        t = self.theme
        bg = {"neutral": t.panel, "good": t.good, "bad": t.bad,
              "recover": t.recover}[self.banner_kind]
        fg = t.text if self.banner_kind == "neutral" else readable_on(bg)
        for widget in (self.banner, self.banner_label, self.status_label):
            widget.configure(background=bg)
        self.banner_label.configure(foreground=fg)
        self.status_label.configure(foreground=fg)

    def paint(self):
        """Colours for the plain tk widgets (ttk ones follow the style)."""
        if self.standalone:
            themes.paint_window(self.root, self.theme)
        self.paint_banner()
        themes.style_text_widget(self.history_list, self.theme)
        themes.repaint(self._text_widgets, self._windows, self.theme)

    def on_theme(self, theme: Theme):
        self.theme = theme
        for view in self.box_views:
            view.set_theme(theme)
        if self.picker_panel is not None:
            self.picker_panel.grid.set_theme(theme)
        self.paint()
        self.refresh()

    def toggle_odds(self):
        """Ctrl+O: the odds under the cards and the odds table."""
        self.odds_var.set(not self.odds_var.get())
        self.on_odds_changed()

    def toggle_counts(self):
        """Ctrl+K: the card counts, the plays and the cards left."""
        self.counts_var.set(not self.counts_var.get())
        self.on_counts_changed()

    def on_odds_changed(self):
        """Odds on or off for this page only; Settings holds the default."""
        self.layout_side()
        self.refresh()

    def on_counts_changed(self):
        """Counts on or off for this page only; Settings holds the default."""
        self.layout_side()
        self.refresh()

    def refresh(self):
        self.side_scroll.update_layout()
        game = self.game
        show_odds = bool(self.odds_var.get())
        odds = game.odds_all() if (game and show_odds and not game.is_over) else None
        if self.mode != "pick":
            for i, view in enumerate(self.box_views):
                self._show_box(i, view, odds)
        self.history_list.delete(0, "end")
        for line in self.history:
            self.history_list.insert("end", line)
        self.history_list.see("end")
        if game is None:
            for btn in self.call_buttons.values():
                btn.state(["disabled"])
            self.skip_button.grid_remove()
            self._wrap_banner()
            return
        can_play = (self.mode == "play" and not game.is_over and not game.recovery_pending
                    and self.selected is not None and game.box[self.selected] is not None)
        offered = offered_calls(game.box[self.selected], game.inclusive_left) if can_play else ()
        for call, btn in self.call_buttons.items():
            btn.state(["!disabled"] if call in offered else ["disabled"])
        if game.recovery_pending:
            self.skip_button.grid()
        else:
            self.skip_button.grid_remove()
        self._wrap_banner()
        self.cards_remaining_var.set(str(game.cards_left))
        self.inclusive_var.set(str(game.inclusive_left))
        self.boxes_var.set(f"{game.boxes_left}/{BOX_SIZE}")
        arrows = {LOWER: " ▼", HIGHER: " ▲", None: ""}
        leans = [count_lean(value) for value in game.counts]
        for var, value, lean in zip(self.count_vars, game.counts, leans):
            var.set((f"{value:+d}" if value else "0") + arrows[lean])
        self.lean_var.set(self.lean_message(leans))
        self.update_side_view(odds)

    @staticmethod
    def lean_message(leans: List[Optional[str]]) -> str:
        """One line summing up what the three counts favour."""
        favoured = {lean for lean in leans if lean}
        if favoured == {LOWER}:
            return "More LOW cards left: lean Lower ▼"
        if favoured == {HIGHER}:
            return "More HIGH cards left: lean Higher ▲"
        if favoured:
            return "The counts disagree: no clear lean"
        return "Even count: no lean"

    def _show_box(self, i: int, view: CardView, odds):
        game = self.game
        key = POSITION_LABELS[i]
        if game is None:
            view.show(None, "empty", footer_left=key)
            return
        card = game.box[i]
        if card is None:
            recovering = game.recovery_pending
            ghost = game.failed.get(i) if recovering and self.settings.show_failed else None
            view.show(None, "recoverable" if recovering else "failed", ghost=ghost,
                      footer_left=key, footer_right="↺ recover" if recovering else "")
            return
        state = "selected" if i == self.selected and not game.recovery_pending else "live"
        right = ""
        if odds and odds[i] is not None:
            right = f"▲{odds[i].higher * 100:.0f}% ▼{odds[i].lower * 100:.0f}%"
        view.show(card, state, footer_left=key, footer_right=right)

    # ----- odds table, cards left, help ----------------------------------- #

    def _show_side_view(self, view: str):
        if not self._need_game():
            return
        self.choose_view(view)

    def show_probabilities(self):
        """Ctrl+P: the full odds table, beside the board (turns odds on)."""
        self._show_side_view("odds")

    def show_remaining_cards(self):
        """Ctrl+L: how many of each rank are left, beside the board (turns
        counts on)."""
        self._show_side_view("cards")

    def update_side_view(self, odds=None):
        """Fill only the side view that is showing (the odds table or the
        cards left); the hidden one is filled when it is switched to."""
        view = self.side_view.get()
        if (self.game is None or self.mode != "play"
                or not self._switch_for(view).get()):
            return
        if view == "odds":
            self.update_probabilities(odds)
        elif view == "cards":
            self.update_remaining_cards()
        self.side_scroll.update_layout()

    def update_probabilities(self, odds_all=None):
        """Fill the odds table, sorted as chosen (Best, highest first, at
        the start). Failed boxes always go last, in box order."""
        if not self.game:
            return
        tree = self.prob_tree
        tree.delete(*tree.get_children())
        rows = odds_rows(self.game.box, odds_all or self.game.odds_all())
        for _position, values, _keys in sort_odds_rows(rows, *self.odds_sort):
            tree.insert("", "end", values=values)

    def sort_odds(self, column: str):
        """A click on an odds-table heading: highest first, then lowest
        first, then back to box order (7 8 9 / 4 5 6 / 1 2 3)."""
        current, mode = self.odds_sort
        if column != current:
            mode = "desc"
        else:
            mode = {"desc": "asc", "asc": "box", "box": "desc"}[mode]
        self.odds_sort = (column, mode)
        self._label_odds_headings()
        self.update_probabilities()

    def _label_odds_headings(self):
        """Mark the sorted column: ↓ highest first, ↑ lowest first."""
        column, mode = self.odds_sort
        for col, (heading, _w, _a) in odds_columns().items():
            mark = {"desc": " ↓", "asc": " ↑"}.get(mode, "") if col == column else ""
            self.prob_tree.heading(col, text=heading + mark)

    def update_remaining_cards(self):
        if not self.game:
            return
        remaining = self.game.remaining_by_rank()
        lines = ["Cards left in the draw pile:", ""]
        for rank in sorted(remaining, key=lambda r: (r != 0, -r)):
            lines.append(f"{_rank_name(rank):<8}{remaining[rank]:>3}")
        lines += ["", f"{'Total':<8}{self.game.cards_left:>3}"]
        self.cards_text.config(state="normal")
        self.cards_text.delete("1.0", "end")
        self.cards_text.insert("1.0", "\n".join(lines))
        self.cards_text.config(state="disabled")

    def _help(self, page: str, title: str, body: str):
        """Help opens as a page of the app; on its own, in a plain window."""
        if self.app is not None:
            return self.app.show_page(page)
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("700x620")
        themes.paint_window(win, self.theme)
        self._windows.append(win)
        DocView(win, body).pack(fill="both", expand=True, padx=10, pady=10)
        return win

    def show_rules(self):
        return self._help("rules", "How to Play", text.RULES_SUMMARY)

    def show_strategy(self):
        return self._help("strategy", "Strategy Guide", text.STRATEGY_GUIDE)

    def show_keyboard_help(self):
        return self._help("shortcuts", "Keyboard Shortcuts", text.shortcut_help())

    def show_about(self):
        return self._help("guide", f"About the {self.HEADING}", text.TOOL_HELP[self.TOOL])


# --------------------------------------------------------------------------- #
# Game Assistant
# --------------------------------------------------------------------------- #

class AssistantGUI(PlayerGUI):
    """🧭 Game Assistant: mirror a game played with a real deck.

    You pick the nine box cards, then for each flip you pick the card that
    actually came off your deck. Odds and counts follow along.
    """

    TITLE = "Beat the Box: Game Assistant"
    HEADING = "Game Assistant"
    TOOL = "assistant"
    START_MESSAGE = "Box set! Pick the card you flipped, select a box, and call."
    HISTORY_ROWS = 2
    SIDE_WIDTH = (340, 580)

    def build_side_extra(self, side: ttk.Frame) -> ttk.Frame:
        frame = ttk.Frame(side, style="Panel.TFrame", padding=(12, 6))
        ttk.Label(frame, text="Card you flipped", style="PanelHeading.TLabel").pack(
            anchor="w", pady=(0, 3))
        self.drawn_var = tk.StringVar()
        self.flip_label_var = tk.StringVar(value="Flipped: none picked")
        self.flip_grid = CardGrid(frame, self.theme, self._flip_picked, jokers=1,
                                  style="Panel.TFrame")
        self.flip_grid.pack(anchor="w")
        # "Flipped: 7♠" sits in the joker row, beside the joker button.
        self.flip_label = ttk.Label(self.flip_grid, textvariable=self.flip_label_var,
                                    style="Panel.TLabel", font=font("ui", 12, "bold"))
        self.flip_grid.beside_jokers(self.flip_label)
        self.drawn_var.trace_add("write", lambda *_: self._show_flip())
        return frame

    def _flip_picked(self, card: Card, _button):
        self.drawn_var.set(card.label())

    def _show_flip(self):
        label = self.drawn_var.get()
        self.flip_grid.set_selected(label)
        if label:
            self.flip_label_var.set(f"Flipped: {card_name(Card.parse(label))}")
        else:
            self.flip_label_var.set("Flipped: none picked")

    def flip_choices(self) -> List[str]:
        """Labels of the cards that can still be flipped (one per joker kind)."""
        if self.game is None:
            return []
        labels: List[str] = []
        for card in sorted(self.game.draw_pile, key=lambda c: (-c.rank, c.suit)):
            if card.label() not in labels:  # two jokers share one entry
                labels.append(card.label())
        return labels

    def on_theme(self, theme: Theme):
        self.flip_grid.set_theme(theme)
        super().on_theme(theme)

    # ----- dealing the box ------------------------------------------------ #

    def new_game(self, settings: Optional[GameSettings] = None,
                 box: Optional[List[Card]] = None) -> bool:
        """No settings: show New Game. Settings but no box: pick the nine
        box cards beside the board. Both: start the game."""
        if settings is None:
            self.show_setup()
            return False
        if box is None:
            self.show_picker(settings)
            return False
        self.start(settings, Game.from_box(box, settings.jokers, settings.inclusive_calls),
                   self.START_MESSAGE)
        return True

    def show_picker(self, settings: GameSettings):
        if self.picker_panel is not None:
            self.picker_panel.frame.destroy()
        self.picker_panel = CardPickerPanel(
            self.side, self.theme, settings.jokers, self._preview,
            lambda box: self.new_game(settings, box=box), self.cancel_pick)
        self.mode = "pick"
        self.layout_side()
        self._preview([])
        self.set_status("Click the nine cards in your box, top-left to bottom-right.")
        self.refresh()

    def _preview(self, picked: List[Card]):
        for i, view in enumerate(self.box_views):
            if i < len(picked):
                view.show(picked[i], "live", footer_left=POSITION_LABELS[i])
            else:
                view.show(None, "empty", footer_left=POSITION_LABELS[i])

    def cancel_pick(self):
        self.mode = "play"
        self.layout_side()
        self.set_status("Select a box and make your call." if self.game else self.WELCOME)
        self.refresh()   # put the old board back

    def create_game(self, settings: GameSettings, box: Optional[List[Card]] = None):
        if box is None:
            return None
        return Game.from_box(box, settings.jokers, settings.inclusive_calls)

    def drawn_card(self):
        label = self.drawn_var.get()
        if not label:
            self.set_status("Pick the card you flipped first!")
            return False
        return Card.parse(label)

    def after_play(self, result: PlayResult):
        self.drawn_var.set("")
        super().after_play(result)

    def refresh(self):
        super().refresh()
        labels = self.flip_choices()
        self.flip_grid.set_available(labels)
        if self.drawn_var.get() not in labels:
            self.drawn_var.set("")