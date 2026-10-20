"""
==============================================
GAME PLAYER AND GAME ASSISTANT WINDOWS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/gui_game.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 218 passed)

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

DEPENDENCIES:
------------
- btb.engine, btb.text, btb.theme, btb.settings, btb.widgets
- Standard library: tkinter, dataclasses, typing

KEY FUNCTIONS:
-------------
- GameSettings -> jokers, inclusive calls, show failed cards
- GameSetupDialog -> modal settings dialog
- CardPickerDialog -> pick the nine box cards (Assistant)
- PlayerGUI.new_game / box_clicked / make_call / undo / skip_recovery
- PlayerGUI.toggle_odds / show_probabilities / show_remaining_cards
- AssistantGUI -> same window plus the flipped-card grid (side panel)

ERROR HANDLING:
--------------
RulesError from the engine is shown in the hint line; nothing crashes.
Message boxes are only used for the game-over announcement and invalid
setup input.

NOTES:
-----
- Plain-letter shortcuts (W, S, D, A, number keys) ignore Ctrl.
- box_views[i] is the CardView for box i; its describe() gives the text a
  player would read ("A♥", "Failed", "Failed\\nK♥").
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import List, Optional

from . import settings as app_settings
from . import text
from . import theme as themes
from .engine import (
    BOX_SIZE, CALL_LABELS, CALLS, COUNT_METHOD_NAMES, HIGHER, HIGHER_EQUAL,
    INCLUSIVE_CALLS, LOWER, LOWER_EQUAL, MAX_JOKERS, Card, Game, PlayResult,
    RulesError, count_lean, max_inclusive_calls,
)
from .theme import Theme, font
from .widgets import CardGrid, CardView, StatTile, card_name, readable_on

CONTROL_MASK = 0x0004

CALL_KEYS = {HIGHER: "W", LOWER: "S", HIGHER_EQUAL: "D", LOWER_EQUAL: "A"}
CALL_ARROWS = {HIGHER: "▲", LOWER: "▼", HIGHER_EQUAL: "▲=", LOWER_EQUAL: "▼="}
CALL_SHORT = {HIGHER: "Higher", LOWER: "Lower", HIGHER_EQUAL: "Higher/Eq",
              LOWER_EQUAL: "Lower/Eq"}
POSITION_LABELS = {pos: key for key, pos in text.POSITION_KEYS.items()}

BANNER_KINDS = ("neutral", "good", "bad", "recover")


@dataclass
class GameSettings:
    jokers: int = 0
    inclusive_calls: int = 5
    show_failed: bool = True


def _percent(p: float) -> str:
    return f"{p * 100:.1f}%"


def _rank_name(rank: int) -> str:
    return {0: "Joker", 11: "Jack", 12: "Queen", 13: "King", 14: "Ace"}.get(rank, str(rank))


def _themed_toplevel(parent: tk.Misc, title: str) -> tk.Toplevel:
    win = tk.Toplevel(parent)
    win.title(title)
    themes.paint_window(win, themes.current())
    return win


# --------------------------------------------------------------------------- #
# Dialogs
# --------------------------------------------------------------------------- #

class GameSetupDialog:
    """Modal dialog for jokers, inclusive calls and the show-failed option."""

    def __init__(self, parent: tk.Misc, initial: Optional[GameSettings] = None):
        initial = initial or GameSettings()
        self.result: Optional[GameSettings] = None
        self.dialog = _themed_toplevel(parent, "New Game")
        self.dialog.transient(parent)
        self.dialog.resizable(False, False)

        frame = ttk.Frame(self.dialog, padding=16)
        frame.pack(fill="both")
        ttk.Label(frame, text="New Game", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.joker_var = tk.StringVar(value=str(initial.jokers))
        self.calls_var = tk.StringVar(value=str(initial.inclusive_calls))
        self.show_var = tk.StringVar(value="Yes" if initial.show_failed else "No")
        self.calls_combo = ttk.Combobox(frame, textvariable=self.calls_var, width=8)
        rows = [
            ("Jokers in the deck:", ttk.Combobox(frame, textvariable=self.joker_var, width=8,
                                                 state="readonly",
                                                 values=list(range(MAX_JOKERS + 1)))),
            ("Inclusive calls:", self.calls_combo),
            ("Show failed cards when recovering:",
             ttk.Combobox(frame, textvariable=self.show_var, width=8, state="readonly",
                          values=["Yes", "No"])),
        ]
        for r, (label, widget) in enumerate(rows, start=1):
            ttk.Label(frame, text=label).grid(row=r, column=0, sticky="w", pady=4)
            widget.grid(row=r, column=1, sticky="w", padx=(10, 0), pady=4)
        self.help_label = ttk.Label(frame, text="", style="Muted.TLabel")
        self.help_label.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 10))

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=2, sticky="e")
        ttk.Button(buttons, text="Cancel", command=self.dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Start Game", style="Accent.TButton",
                   command=self._confirm).pack(side="right", padx=6)
        self.dialog.bind("<Return>", lambda e: self._confirm())
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

        self.joker_var.trace_add("write", self._update_range)
        self._update_range()
        self.dialog.grab_set()

    def _update_range(self, *_):
        jokers = int(self.joker_var.get())
        limit = max_inclusive_calls(jokers)
        self.calls_combo["values"] = list(range(limit + 1))
        self.help_label.config(text=f"Inclusive calls: 0 to {limit} with {jokers} joker(s).")

    def _confirm(self):
        try:
            jokers = int(self.joker_var.get())
            calls = int(self.calls_var.get())
        except ValueError:
            messagebox.showwarning("Invalid input", "Please enter whole numbers.",
                                   parent=self.dialog)
            return
        limit = max_inclusive_calls(jokers)
        if not 0 <= calls <= limit:
            messagebox.showwarning("Invalid input",
                                   f"Inclusive calls must be 0-{limit} with {jokers} joker(s).",
                                   parent=self.dialog)
            return
        self.result = GameSettings(jokers, calls, self.show_var.get() == "Yes")
        self.dialog.destroy()


class CardPickerDialog:
    """Pick the nine cards dealt into the box (Game Assistant).

    Each physical card, including each joker, has its own button, so picking
    one joker never removes the other.
    """

    def __init__(self, parent: tk.Misc, jokers: int, on_pick=None):
        self.result: Optional[List[Card]] = None
        self.picked: List[Card] = []
        self._picked_buttons: List[tk.Button] = []
        self._on_pick = on_pick
        self.dialog = _themed_toplevel(parent, "Select the Nine Box Cards")
        self.dialog.transient(parent)

        frame = ttk.Frame(self.dialog, padding=14)
        frame.pack(fill="both")
        self.info = ttk.Label(frame, text="", style="Heading.TLabel")
        self.info.pack(anchor="w", pady=(0, 8))
        self.grid = CardGrid(frame, themes.current(), self._pick, jokers=jokers)
        self.grid.pack()
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(10, 0))
        ttk.Button(controls, text="Cancel", command=self.dialog.destroy).pack(side="right")
        ttk.Button(controls, text="Undo Pick", command=self._unpick).pack(side="right", padx=6)
        self._update_info()
        self.dialog.grab_set()

    def _update_info(self):
        n = len(self.picked)
        self.info.config(text=f"Click the cards in the box, top-left to bottom-right "
                              f"({n}/{BOX_SIZE} picked)")

    def _pick(self, card: Card, button: tk.Button):
        if len(self.picked) >= BOX_SIZE or str(button.cget("state")) == "disabled":
            return
        self.picked.append(card)
        self._picked_buttons.append(button)
        self.grid.disable(button)
        self._update_info()
        if self._on_pick:
            self._on_pick(list(self.picked))
        if len(self.picked) == BOX_SIZE:
            self.result = list(self.picked)
            self.dialog.destroy()

    def _unpick(self):
        if self.picked:
            self.picked.pop()
            self.grid.enable(self._picked_buttons.pop())
            self._update_info()
            if self._on_pick:
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
    HISTORY_ROWS = 8

    def __init__(self, root: tk.Misc):
        self.root = root
        self.root.title(self.TITLE)
        self.theme: Theme = themes.use(root)
        self.game: Optional[Game] = None
        self.settings = GameSettings()
        self.selected: Optional[int] = None
        self.history: List[str] = []
        self.prob_window: Optional[tk.Toplevel] = None
        self.prob_tree: Optional[ttk.Treeview] = None
        self.cards_window: Optional[tk.Toplevel] = None
        self.cards_text: Optional[tk.Text] = None
        self._text_widgets: List[tk.Misc] = []
        self._windows: List[tk.Misc] = []
        self.banner_var = tk.StringVar(value="Beat the Box")
        self.banner_kind = "neutral"
        self.status_var = tk.StringVar(value=self.WELCOME)
        self.cards_remaining_var = tk.StringVar(value="-")
        self.inclusive_var = tk.StringVar(value="-")
        self.boxes_var = tk.StringVar(value="-")
        self.count_vars = [tk.StringVar(value="0") for _ in COUNT_METHOD_NAMES]
        self.lean_var = tk.StringVar(value="")
        self.odds_var = tk.BooleanVar(value=bool(app_settings.get("show_odds")))
        self.theme_var = tk.StringVar(value=self.theme.name)
        self.build_menu()
        self.build()
        self.bind_shortcuts()
        themes.subscribe(self.root, self.on_theme)
        self.refresh()

    # ----- layout --------------------------------------------------------- #

    def build_menu(self):
        bar = tk.Menu(self.root)
        game = tk.Menu(bar, tearoff=0)
        game.add_command(label="New Game", accelerator="Ctrl+N", command=self.new_game)
        game.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        game.add_separator()
        game.add_command(label="Close Window", command=self.root.destroy)
        bar.add_cascade(label="Game", menu=game)

        view = tk.Menu(bar, tearoff=0)
        view.add_checkbutton(label="Show Odds on Cards", accelerator="Ctrl+O",
                             variable=self.odds_var, command=self.on_odds_changed)
        view.add_command(label="Probabilities...", accelerator="Ctrl+P",
                         command=self.show_probabilities)
        view.add_command(label="Remaining Cards...", accelerator="Ctrl+L",
                         command=self.show_remaining_cards)
        view.add_separator()
        view.add_cascade(label="Theme", menu=self._theme_menu(view))
        bar.add_cascade(label="View", menu=view)

        help_menu = tk.Menu(bar, tearoff=0)
        help_menu.add_command(label="How to Play", accelerator="Ctrl+R", command=self.show_rules)
        help_menu.add_command(label="Strategy Guide", accelerator="Ctrl+Y",
                              command=self.show_strategy)
        help_menu.add_command(label="Keyboard Shortcuts", accelerator="Ctrl+H",
                              command=self.show_keyboard_help)
        help_menu.add_separator()
        help_menu.add_command(label="About This Tool", command=self.show_about)
        bar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=bar)
        self.menu = bar

    def _theme_menu(self, parent: tk.Menu) -> tk.Menu:
        menu = tk.Menu(parent, tearoff=0)
        for number, name in enumerate(themes.theme_names(), start=1):
            menu.add_radiobutton(label=f"{number}. {name}", value=name, variable=self.theme_var,
                                 command=lambda n=name: themes.set_theme(n, self.root))
        return menu

    def build(self):
        self.main = ttk.Frame(self.root, padding=14)
        self.main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        toolbar = ttk.Frame(self.main)
        toolbar.grid(row=0, column=0, columnspan=3, sticky="ew")
        ttk.Label(toolbar, text=self.HEADING, style="Heading.TLabel").pack(side="left")
        ttk.Checkbutton(toolbar, text="Show odds (Ctrl+O)", variable=self.odds_var,
                        command=self.on_odds_changed).pack(side="right", padx=(10, 0))
        ttk.Button(toolbar, text="Undo (Ctrl+Z)", command=self.undo).pack(side="right", padx=4)
        ttk.Button(toolbar, text="New Game (Ctrl+N)", style="Accent.TButton",
                   command=self.new_game).pack(side="right", padx=4)

        # The result banner: what you called and what happened, big.
        self.banner = tk.Frame(self.main, borderwidth=0, highlightthickness=0)
        self.banner.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 10))
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

        board = ttk.Frame(self.main)
        board.grid(row=2, column=0, sticky="n")
        width, height = self.CARD_SIZE
        self.box_views: List[CardView] = []
        for i in range(BOX_SIZE):
            view = CardView(board, self.theme, width, height,
                            command=lambda pos=i: self.box_clicked(pos))
            view.grid(row=i // 3, column=i % 3, padx=3, pady=2)
            self.box_views.append(view)

        self.build_side_panel()

        actions = ttk.Frame(self.main)
        actions.grid(row=3, column=0, columnspan=2, pady=(12, 0))
        self.call_buttons = {}
        for col, call in enumerate(CALLS):
            style = "CallAccent.TButton" if call in INCLUSIVE_CALLS else "Call.TButton"
            btn = ttk.Button(actions, style=style,
                             text=f"{CALL_ARROWS[call]} {CALL_LABELS[call]} ({CALL_KEYS[call]})",
                             command=lambda c=call: self.make_call(c))
            btn.grid(row=0, column=col, padx=4)
            self.call_buttons[call] = btn

        self.paint()

    def build_side_panel(self):
        side = ttk.Frame(self.main)
        side.grid(row=2, column=1, sticky="nsew", padx=(16, 0))
        tiles = ttk.Frame(side)
        tiles.pack(fill="x")
        for col, (caption, var) in enumerate((("Draw pile", self.cards_remaining_var),
                                              ("Inclusive calls", self.inclusive_var),
                                              ("Boxes alive", self.boxes_var))):
            StatTile(tiles, caption, var).grid(row=0, column=col, sticky="ew",
                                               padx=(0 if col == 0 else 6, 0))
            tiles.columnconfigure(col, weight=1)

        counts = ttk.Frame(side, style="Panel.TFrame", padding=(12, 8))
        counts.pack(fill="x", pady=(10, 0))
        ttk.Label(counts, text="Card count", style="PanelHeading.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w")
        for col, (name, var) in enumerate(zip(COUNT_METHOD_NAMES, self.count_vars)):
            ttk.Label(counts, text=name, style="PanelMuted.TLabel").grid(
                row=1, column=col, sticky="w")
            ttk.Label(counts, textvariable=var, style="Panel.TLabel",
                      font=font("ui", 13, "bold")).grid(row=2, column=col, sticky="w")
            counts.columnconfigure(col, weight=1)
        ttk.Label(counts, textvariable=self.lean_var, style="Panel.TLabel",
                  wraplength=360).grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))

        self.build_side_extra(side)

        history = ttk.Frame(side, style="Panel.TFrame", padding=(12, 8))
        history.pack(fill="both", expand=True, pady=(10, 0))
        ttk.Label(history, text="Plays", style="PanelHeading.TLabel").pack(anchor="w")
        inner = ttk.Frame(history, style="Panel.TFrame")
        inner.pack(fill="both", expand=True, pady=(4, 0))
        self.history_list = tk.Listbox(inner, height=self.HISTORY_ROWS, width=30, activestyle="none",
                                       font=font("ui", 10))
        scroll = ttk.Scrollbar(inner, command=self.history_list.yview)
        self.history_list.configure(yscrollcommand=scroll.set)
        self.history_list.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def build_side_extra(self, side: ttk.Frame):
        """Hook for subclasses: a panel between the counts and the history."""

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
                self.root.bind(seq, self._key_handler(handler, plain_letter))
        keypad = {"7": "KP_Home", "8": "KP_Up", "9": "KP_Prior", "4": "KP_Left",
                  "5": "KP_Begin", "6": "KP_Right", "1": "KP_End", "2": "KP_Down",
                  "3": "KP_Next"}
        for key, pos in text.POSITION_KEYS.items():
            handler = self._key_handler(lambda p=pos: self.box_clicked(p), True)
            for seq in (f"<KeyPress-{key}>", f"<KeyPress-KP_{key}>",
                        f"<KeyPress-{keypad[key]}>"):
                try:
                    self.root.bind(seq, handler)
                except tk.TclError:
                    pass  # keysym not known on this platform

    def _key_handler(self, action, plain: bool):
        def handler(event):
            # Plain keys (W, 7, ...) must not fire on Ctrl+W, Ctrl+7, ...
            if plain and event.state & CONTROL_MASK:
                return None
            action()
            return "break"
        return handler

    # ----- game flow ------------------------------------------------------ #

    def ask_settings(self) -> Optional[GameSettings]:
        dialog = GameSetupDialog(self.root, self.settings)
        self.root.wait_window(dialog.dialog)
        return dialog.result

    def new_game(self, settings: Optional[GameSettings] = None) -> bool:
        settings = settings or self.ask_settings()
        if settings is None:
            return False
        game = self.create_game(settings)
        if game is None:
            return False
        self.start(settings, game, self.START_MESSAGE)
        return True

    def start(self, settings: GameSettings, game: Game, message: str):
        self.settings = settings
        self.game = game
        self.selected = None
        self.history = []
        self.set_banner("New game: nine cards are in the box", "neutral")
        self.set_status(message)
        self.refresh()

    def create_game(self, settings: GameSettings) -> Optional[Game]:
        return Game.new(settings.jokers, settings.inclusive_calls)

    def _need_game(self) -> bool:
        if self.game is None:
            self.set_status(self.WELCOME)
            return False
        return True

    def box_clicked(self, position: int):
        if not self._need_game():
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
        self.set_status(f"Selected {card_name(self.game.box[position])}. "
                        "Call Higher or Lower, or use an inclusive call.")
        self.refresh()

    def drawn_card(self) -> Optional[Card]:
        """The card to flip: None means the top of the shuffled pile."""
        return None

    def make_call(self, call: str):
        if not self._need_game():
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
        if call in INCLUSIVE_CALLS and game.inclusive_left <= 0:
            self.set_status("No inclusive calls left!")
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
        if not self._need_game():
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
        game = self.game
        if not game.is_over:
            return
        self.selected = None
        if game.won:
            title = "You beat the box!"
            body = (f"You got through the whole pile with {game.boxes_left} "
                    f"box{'es' if game.boxes_left != 1 else ''} left.")
            self.set_banner(f"★ {title}", "good")
        else:
            title = "The box wins"
            body = f"All nine boxes failed with {game.cards_left} cards left in the pile."
            self.set_banner(title, "bad")
        self.set_status(f"{body} Press New Game (Ctrl+N) to play again.")
        self.refresh()
        self.announce(title, body)

    def announce(self, title: str, body: str):
        messagebox.showinfo(title, body, parent=self.root)

    # ----- drawing -------------------------------------------------------- #

    def set_banner(self, message: str, kind: str = "neutral"):
        self.banner_var.set(message)
        self.banner_kind = kind if kind in BANNER_KINDS else "neutral"
        self.paint_banner()

    def set_status(self, message: str):
        game = self.game
        if (game and not game.is_over and not game.recovery_pending
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
        themes.paint_window(self.root, self.theme)
        self.paint_banner()
        themes.style_text_widget(self.history_list, self.theme)
        themes.repaint(self._text_widgets, self._windows, self.theme)

    def on_theme(self, theme: Theme):
        self.theme = theme
        self.theme_var.set(theme.name)
        for view in self.box_views:
            view.set_theme(theme)
        self.paint()
        self.refresh()

    def toggle_odds(self):
        self.odds_var.set(not self.odds_var.get())
        self.on_odds_changed()

    def on_odds_changed(self):
        """Odds on or off for this window only; Settings holds the default."""
        self.refresh()

    def refresh(self):
        game = self.game
        odds = game.odds_all() if (game and self.odds_var.get() and not game.is_over) else None
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
            return
        can_play = (not game.is_over and not game.recovery_pending
                    and self.selected is not None)
        for call, btn in self.call_buttons.items():
            enabled = can_play and (call not in INCLUSIVE_CALLS or game.inclusive_left > 0)
            btn.state(["!disabled"] if enabled else ["disabled"])
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
        self.update_probabilities()
        self.update_remaining_cards()

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

    # ----- side windows --------------------------------------------------- #

    def show_probabilities(self):
        if not self._need_game():
            return
        if self.prob_window and self.prob_window.winfo_exists():
            self.prob_window.lift()
            return
        self.prob_window = _themed_toplevel(self.root, "Probabilities")
        self._windows.append(self.prob_window)
        frame = ttk.Frame(self.prob_window, padding=10)
        frame.pack(fill="both", expand=True)
        columns = ("box", "card", *CALLS, "exact", "best")
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=9)
        headings = {"box": "Box", "card": "Card", "exact": "Recovery chance",
                    "best": "Best plain call", **CALL_LABELS}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=110 if col not in ("box", "card") else 56, anchor="center")
        tree.pack(fill="both", expand=True)
        ttk.Label(frame, text="Odds use the cards still in the draw pile. Recovery chance = "
                  "exact match or joker on an inclusive call.", style="Muted.TLabel").pack(
            anchor="w", pady=(8, 0))
        self.prob_tree = tree
        self.update_probabilities()

    def update_probabilities(self):
        if not (self.prob_window and self.prob_window.winfo_exists() and self.game):
            return
        tree = self.prob_tree
        tree.delete(*tree.get_children())
        for i, (card, odds) in enumerate(zip(self.game.box, self.game.odds_all())):
            box = POSITION_LABELS[i]
            if card is None:
                tree.insert("", "end", values=(box, "Failed", *[""] * 6))
            elif odds is None:
                tree.insert("", "end", values=(box, card, *["-"] * 6))
            else:
                best_call, best_p = odds.best_plain()
                tree.insert("", "end", values=(
                    box, card, *(_percent(odds.for_call(c)) for c in CALLS),
                    _percent(odds.exact), f"{CALL_LABELS[best_call]} {_percent(best_p)}"))

    def show_remaining_cards(self):
        if not self._need_game():
            return
        if self.cards_window and self.cards_window.winfo_exists():
            self.cards_window.lift()
            return
        self.cards_window = _themed_toplevel(self.root, "Remaining Cards")
        self._windows.append(self.cards_window)
        self.cards_text = tk.Text(self.cards_window, width=28, height=20,
                                  font=font("mono", 11), padx=10, pady=8)
        themes.style_text_widget(self.cards_text, self.theme)
        self._text_widgets.append(self.cards_text)
        self.cards_text.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(self.cards_window, text="Close",
                   command=self.cards_window.destroy).pack(pady=(0, 10))
        self.update_remaining_cards()

    def update_remaining_cards(self):
        if not (self.cards_window and self.cards_window.winfo_exists() and self.game):
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

    def _text_window(self, title: str, body: str, size: str = "660x720"):
        win = _themed_toplevel(self.root, title)
        self._windows.append(win)
        win.geometry(size)
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        widget = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set,
                         font=font("mono", 10), padx=12, pady=10)
        themes.style_text_widget(widget, self.theme)
        self._text_widgets.append(widget)
        widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=widget.yview)
        widget.insert("1.0", body)
        widget.config(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 10))
        return win

    def show_rules(self):
        return self._text_window("How to Play", text.RULES_SUMMARY)

    def show_strategy(self):
        return self._text_window("Strategy Guide", text.STRATEGY_GUIDE)

    def show_keyboard_help(self):
        return self._text_window("Keyboard Shortcuts", text.shortcut_help(), "480x380")

    def show_about(self):
        return self._text_window(f"About the {self.HEADING}", text.TOOL_HELP[self.TOOL],
                                 "640x520")


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

    HISTORY_ROWS = 3

    def build_side_extra(self, side: ttk.Frame):
        frame = ttk.Frame(side, style="Panel.TFrame", padding=(12, 8))
        frame.pack(fill="x", pady=(10, 0))
        ttk.Label(frame, text="Card you flipped: click it, then pick a box and call",
                  style="PanelHeading.TLabel").pack(anchor="w", pady=(0, 6))
        self.drawn_var = tk.StringVar()
        self.flip_label_var = tk.StringVar(value="Flipped: none picked")
        self.flip_grid = CardGrid(frame, self.theme, self._flip_picked, jokers=1,
                                  style="Panel.TFrame")
        self.flip_grid.pack(anchor="w")
        ttk.Label(frame, textvariable=self.flip_label_var, style="Panel.TLabel",
                  font=font("ui", 12, "bold")).pack(anchor="w", pady=(6, 0))
        self.drawn_var.trace_add("write", lambda *_: self._show_flip())

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

    def ask_box_cards(self, jokers: int) -> Optional[List[Card]]:
        def preview(picked: List[Card]):
            for i, view in enumerate(self.box_views):
                if i < len(picked):
                    view.show(picked[i], "live", footer_left=POSITION_LABELS[i])
                else:
                    view.show(None, "empty", footer_left=POSITION_LABELS[i])
        picker = CardPickerDialog(self.root, jokers, on_pick=preview)
        self.root.wait_window(picker.dialog)
        if picker.result is None:
            self.refresh()  # cancelled: put the old board back
        return picker.result

    def create_game(self, settings: GameSettings, box: Optional[List[Card]] = None):
        box = box or self.ask_box_cards(settings.jokers)
        if box is None:
            return None
        return Game.from_box(box, settings.jokers, settings.inclusive_calls)

    def new_game(self, settings: Optional[GameSettings] = None,
                 box: Optional[List[Card]] = None) -> bool:
        if box is None:
            return super().new_game(settings)
        settings = settings or GameSettings()
        self.start(settings, self.create_game(settings, box), self.START_MESSAGE)
        return True

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