"""
==============================================
GAME PLAYER AND GAME ASSISTANT WINDOWS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/gui_game.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

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
- btb.engine, btb.text
- Standard library: tkinter, dataclasses, typing

KEY FUNCTIONS:
-------------
- GameSettings -> jokers, inclusive calls, show failed cards
- GameSetupDialog -> modal settings dialog
- CardPickerDialog -> pick the nine box cards (Assistant)
- PlayerGUI.new_game / box_clicked / make_call / undo / skip_recovery
- AssistantGUI -> same window plus the flipped-card picker

ERROR HANDLING:
--------------
RulesError from the engine is shown in the status bar; nothing crashes.
Message boxes are only used for the game-over announcement and invalid
setup input.

NOTES:
-----
- Plain-letter shortcuts (W, S, D, A, number keys) ignore Ctrl.
- Box buttons are tk.Button (not ttk) so they can be coloured.
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import List, Optional

from . import text
from .engine import (
    CALL_LABELS, CALLS, COUNT_METHOD_NAMES, HIGHER, HIGHER_EQUAL,
    INCLUSIVE_CALLS, LOWER, LOWER_EQUAL, MAX_JOKERS, RANKS, SUITS, BOX_SIZE,
    Card, Game, PlayResult, RulesError, max_inclusive_calls,
)

CONTROL_MASK = 0x0004

COLORS = {
    "live": "#fdfdf8",
    "selected": "#bfe0ff",
    "failed": "#c9c9c9",
    "recoverable": "#ffe7a3",
    "joker": "#e6d7ff",
    "red": "#b3261e",
    "black": "#1d1d1d",
}


@dataclass
class GameSettings:
    jokers: int = 0
    inclusive_calls: int = 5
    show_failed: bool = True


def _percent(p: float) -> str:
    return f"{p * 100:.1f}%"


def _rank_name(rank: int) -> str:
    return {0: "Joker", 11: "Jack", 12: "Queen", 13: "King", 14: "Ace"}.get(rank, str(rank))


# --------------------------------------------------------------------------- #
# Dialogs
# --------------------------------------------------------------------------- #

class GameSetupDialog:
    """Modal dialog for jokers, inclusive calls and the show-failed option."""

    def __init__(self, parent: tk.Misc, initial: Optional[GameSettings] = None):
        initial = initial or GameSettings()
        self.result: Optional[GameSettings] = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Game Setup")
        self.dialog.transient(parent)
        self.dialog.resizable(False, False)

        frame = ttk.LabelFrame(self.dialog, text="Game Configuration", padding=10)
        frame.pack(padx=10, pady=5, fill="x")

        ttk.Label(frame, text="Number of jokers:").pack(anchor="w")
        self.joker_var = tk.StringVar(value=str(initial.jokers))
        ttk.Combobox(frame, textvariable=self.joker_var, state="readonly",
                     values=list(range(MAX_JOKERS + 1))).pack(fill="x", pady=(0, 10))

        ttk.Label(frame, text="Number of inclusive calls:").pack(anchor="w")
        self.calls_var = tk.StringVar(value=str(initial.inclusive_calls))
        self.calls_combo = ttk.Combobox(frame, textvariable=self.calls_var)
        self.calls_combo.pack(fill="x", pady=(0, 10))

        ttk.Label(frame, text="Show failed cards when recovering:").pack(anchor="w")
        self.show_var = tk.StringVar(value="Yes" if initial.show_failed else "No")
        ttk.Combobox(frame, textvariable=self.show_var, state="readonly",
                     values=["Yes", "No"]).pack(fill="x", pady=(0, 10))

        self.help_label = ttk.Label(frame, text="")
        self.help_label.pack()

        buttons = ttk.Frame(self.dialog)
        buttons.pack(pady=10)
        ttk.Button(buttons, text="Start Game", command=self._confirm).pack(side="left", padx=5)
        ttk.Button(buttons, text="Cancel", command=self.dialog.destroy).pack(side="left", padx=5)
        self.dialog.bind("<Return>", lambda e: self._confirm())
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())

        self.joker_var.trace_add("write", self._update_range)
        self._update_range()
        self.dialog.grab_set()

    def _update_range(self, *_):
        jokers = int(self.joker_var.get())
        limit = max_inclusive_calls(jokers)
        self.calls_combo["values"] = list(range(limit + 1))
        self.help_label.config(text=f"Maximum with {jokers} joker(s): {limit}")

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
        self._picked_buttons: List[ttk.Button] = []
        self._on_pick = on_pick
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select the Nine Box Cards")
        self.dialog.transient(parent)

        self.info = ttk.Label(self.dialog, text="")
        self.info.grid(row=0, column=0, columnspan=13, pady=(8, 4))
        for row, suit in enumerate(SUITS, start=1):
            for col, rank in enumerate(RANKS):
                card = Card(rank, suit)
                btn = ttk.Button(self.dialog, text=card.label(), width=5)
                btn.configure(command=lambda c=card, b=btn: self._pick(c, b))
                btn.grid(row=row, column=col, padx=1, pady=1)
        for i in range(jokers):
            btn = ttk.Button(self.dialog, text=Card.joker().label(), width=5)
            btn.configure(command=lambda b=btn: self._pick(Card.joker(), b))
            btn.grid(row=len(SUITS) + 1, column=i, padx=1, pady=1)

        controls = ttk.Frame(self.dialog)
        controls.grid(row=len(SUITS) + 2, column=0, columnspan=13, pady=8)
        ttk.Button(controls, text="Undo Pick", command=self._unpick).pack(side="left", padx=5)
        ttk.Button(controls, text="Cancel", command=self.dialog.destroy).pack(side="left", padx=5)
        self._update_info()
        self.dialog.grab_set()

    def _update_info(self):
        n = len(self.picked)
        self.info.config(text=f"Click the cards in the box, top-left to bottom-right "
                              f"({n}/{BOX_SIZE} picked)")

    def _pick(self, card: Card, button: ttk.Button):
        if len(self.picked) >= BOX_SIZE:
            return
        self.picked.append(card)
        self._picked_buttons.append(button)
        button.state(["disabled"])
        self._update_info()
        if self._on_pick:
            self._on_pick(list(self.picked))
        if len(self.picked) == BOX_SIZE:
            self.result = list(self.picked)
            self.dialog.destroy()

    def _unpick(self):
        if self.picked:
            self.picked.pop()
            self._picked_buttons.pop().state(["!disabled"])
            self._update_info()
            if self._on_pick:
                self._on_pick(list(self.picked))


# --------------------------------------------------------------------------- #
# Game Player
# --------------------------------------------------------------------------- #

class PlayerGUI:
    """🎮 Game Player: a shuffled deck, live odds, counts, undo, shortcuts."""

    TITLE = "Beat the Box: Game Player"
    WELCOME = "Welcome to Beat the Box! Press New Game (Ctrl+N) to start."

    def __init__(self, root: tk.Misc):
        self.root = root
        self.root.title(self.TITLE)
        self.game: Optional[Game] = None
        self.settings = GameSettings()
        self.selected: Optional[int] = None
        self.prob_window: Optional[tk.Toplevel] = None
        self.prob_tree: Optional[ttk.Treeview] = None
        self.cards_window: Optional[tk.Toplevel] = None
        self.cards_text: Optional[tk.Text] = None
        self.status_var = tk.StringVar(value=self.WELCOME)
        self.cards_remaining_var = tk.StringVar(value="Cards remaining: -")
        self.inclusive_var = tk.StringVar(value="Inclusive calls: -")
        self.boxes_var = tk.StringVar(value="Boxes alive: -")
        self.count_vars = [tk.StringVar(value=f"{name}: 0") for name in COUNT_METHOD_NAMES]
        self.build()
        self.bind_shortcuts()
        self.refresh()

    # ----- layout --------------------------------------------------------- #

    def build(self):
        self.main = ttk.Frame(self.root, padding=10)
        self.main.grid(row=0, column=0, sticky="nsew")

        board = ttk.LabelFrame(self.main, text="The Box", padding=6)
        board.grid(row=0, column=0, pady=5)
        self.box_buttons: List[tk.Button] = []
        for i in range(BOX_SIZE):
            btn = tk.Button(board, text="", width=9, height=3,
                            font=("Segoe UI Symbol", 16, "bold"),
                            relief="raised", bd=2,
                            command=lambda pos=i: self.box_clicked(pos))
            btn.grid(row=i // 3, column=i % 3, padx=3, pady=3)
            self.box_buttons.append(btn)

        actions = ttk.LabelFrame(self.main, text="Your Call", padding=5)
        actions.grid(row=1, column=0, pady=5)
        keys = {HIGHER: "W", LOWER: "S", HIGHER_EQUAL: "D", LOWER_EQUAL: "A"}
        self.call_buttons = {}
        for col, call in enumerate(CALLS):
            btn = ttk.Button(actions, text=f"{CALL_LABELS[call]} ({keys[call]})",
                             command=lambda c=call: self.make_call(c))
            btn.grid(row=0, column=col, padx=4, pady=4)
            self.call_buttons[call] = btn
        self.skip_button = ttk.Button(actions, text="Skip Recovery",
                                      command=self.skip_recovery)
        self.skip_button.grid(row=1, column=0, columnspan=4, pady=(2, 0))
        self.skip_button.grid_remove()

        self.build_extra()

        stats = ttk.LabelFrame(self.main, text="Game Statistics", padding=5)
        stats.grid(row=3, column=0, pady=5, sticky="ew")
        for col, var in enumerate((self.cards_remaining_var, self.inclusive_var,
                                   self.boxes_var)):
            ttk.Label(stats, textvariable=var).grid(row=0, column=col, padx=10, pady=3)

        counting = ttk.LabelFrame(self.main, text="Card Counts (positive = more low cards left)",
                                  padding=5)
        counting.grid(row=4, column=0, pady=5, sticky="ew")
        for col, var in enumerate(self.count_vars):
            ttk.Label(counting, textvariable=var).grid(row=0, column=col, padx=10, pady=3)

        controls = ttk.Frame(self.main)
        controls.grid(row=5, column=0, pady=5)
        layout = [
            ("New Game (Ctrl+N)", self.new_game, 0, 0),
            ("Undo (Ctrl+Z)", self.undo, 0, 2),
            ("Show Probabilities (Ctrl+P)", self.show_probabilities, 1, 0),
            ("Show Remaining Cards (Ctrl+L)", self.show_remaining_cards, 1, 2),
            ("How to Play (Ctrl+R)", self.show_rules, 2, 0),
            ("Strategy (Ctrl+Y)", self.show_strategy, 2, 1),
            ("Keyboard Help (Ctrl+H)", self.show_keyboard_help, 2, 2),
        ]
        for label, command, row, col in layout:
            ttk.Button(controls, text=label, command=command).grid(
                row=row, column=col, padx=4, pady=3)

        status = ttk.Frame(self.main, relief="sunken")
        status.grid(row=6, column=0, sticky="ew", pady=5)
        ttk.Label(status, textvariable=self.status_var, wraplength=520).grid(
            row=0, column=0, padx=5, pady=2, sticky="w")

    def build_extra(self):
        """Hook for subclasses: widgets placed at row 2."""

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
        self.settings = settings
        self.game = game
        self.selected = None
        self.set_status("Game started! Select a box, then make your call.")
        self.refresh()
        return True

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
                self.set_status(f"Recovered box {position + 1}: it's back with {card}.")
                self.refresh()
                self.check_game_over()
            else:
                self.set_status("Pick a failed box to recover, or Skip Recovery.")
            return
        if self.game.is_over:
            self.set_status("The game is over. Press New Game (Ctrl+N) to play again.")
            return
        if self.game.box[position] is None:
            self.set_status("That box has failed. Choose another box.")
            return
        self.selected = position
        self.set_status(f"Selected {self.game.box[position]}. "
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
            self.set_status("Pick a failed box to recover, or Skip Recovery.")
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
        verdict = "Correct!" if result.success else "Wrong! The box fails."
        if result.success and (result.drawn.is_joker or result.target.is_joker):
            verdict = "Joker: automatic success!"
        message = (f"{CALL_LABELS[result.call]} on {result.target}: "
                   f"drew {result.drawn}. {verdict}")
        if result.recovery_pending:
            message += " Recovery earned: click a failed box to bring it back, or skip."
        elif result.recovery_lost:
            message += " Exact match, but no box has failed, so the recovery is lost."
        if not self.game.box[result.position]:
            self.selected = None
        self.set_status(message)
        self.refresh()
        self.check_game_over()

    def skip_recovery(self):
        if self.game is None or not self.game.recovery_pending:
            return
        self.game.skip_recovery()
        self.set_status("Recovery skipped.")
        self.refresh()
        self.check_game_over()

    def undo(self):
        if not self._need_game():
            return
        if not self.game.undo():
            self.set_status("No moves to undo!")
            return
        if self.selected is not None and self.game.box[self.selected] is None:
            self.selected = None
        self.set_status("Last move undone.")
        self.refresh()

    def check_game_over(self):
        game = self.game
        if not game.is_over:
            return
        self.selected = None
        self.refresh()
        if game.won:
            title = "You beat the box!"
            body = (f"You got through the whole pile with {game.boxes_left} "
                    f"box{'es' if game.boxes_left != 1 else ''} left.")
        else:
            title = "The box wins"
            body = f"All nine boxes failed with {game.cards_left} cards left in the pile."
        self.set_status(f"{title} {body} Press New Game (Ctrl+N) to play again.")
        self.announce(title, body)

    def announce(self, title: str, body: str):
        messagebox.showinfo(title, body, parent=self.root)

    # ----- drawing -------------------------------------------------------- #

    def set_status(self, message: str):
        game = self.game
        if (game and not game.is_over and not game.recovery_pending
                and game.failed and game.inclusive_left > 0
                and any(c is not None and c.is_joker for c in game.box)):
            message += "  Tip: an inclusive call on the joker earns a recovery."
        self.status_var.set(message)

    def refresh(self):
        game = self.game
        for i, btn in enumerate(self.box_buttons):
            self._draw_box(i, btn)
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
        self.cards_remaining_var.set(f"Cards remaining: {game.cards_left}")
        self.inclusive_var.set(f"Inclusive calls: {game.inclusive_left}")
        self.boxes_var.set(f"Boxes alive: {game.boxes_left}/{BOX_SIZE}")
        for var, name, value in zip(self.count_vars, COUNT_METHOD_NAMES, game.counts):
            var.set(f"{name}: {value:+d}" if value else f"{name}: 0")
        self.update_probabilities()
        self.update_remaining_cards()

    def _draw_box(self, i: int, btn: tk.Button):
        game = self.game
        if game is None:
            btn.config(text="", bg=COLORS["live"], relief="raised", state="normal")
            return
        card = game.box[i]
        if card is None:
            recovering = game.recovery_pending
            label = "Failed"
            if recovering and self.settings.show_failed:
                label = f"Failed\n{game.failed[i]}"
            btn.config(text=label, fg=COLORS["black"], relief="flat",
                       bg=COLORS["recoverable"] if recovering else COLORS["failed"])
            return
        color = COLORS["red"] if card.suit in ("♥", "♦") else COLORS["black"]
        bg = COLORS["joker"] if card.is_joker else COLORS["live"]
        if i == self.selected and not game.recovery_pending:
            bg = COLORS["selected"]
        btn.config(text=card.label(), fg=color, bg=bg,
                   relief="sunken" if i == self.selected else "raised")

    # ----- side windows --------------------------------------------------- #

    def show_probabilities(self):
        if not self._need_game():
            return
        if self.prob_window and self.prob_window.winfo_exists():
            self.prob_window.lift()
            return
        self.prob_window = tk.Toplevel(self.root)
        self.prob_window.title("Probabilities")
        columns = ("box", "card", *CALLS, "exact", "best")
        tree = ttk.Treeview(self.prob_window, columns=columns, show="headings", height=9)
        headings = {"box": "Box", "card": "Card", "exact": "Recovery chance",
                    "best": "Best plain call", **CALL_LABELS}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=105 if col not in ("box", "card") else 50, anchor="center")
        tree.pack(fill="both", expand=True, padx=8, pady=8)
        ttk.Label(self.prob_window, text="Odds use the cards still in the draw pile. "
                  "Recovery chance = exact match or joker on an inclusive call.").pack(
            padx=8, pady=(0, 8))
        self.prob_tree = tree
        self.update_probabilities()

    def update_probabilities(self):
        if not (self.prob_window and self.prob_window.winfo_exists() and self.game):
            return
        tree = self.prob_tree
        tree.delete(*tree.get_children())
        for i, (card, odds) in enumerate(zip(self.game.box, self.game.odds_all())):
            if card is None:
                tree.insert("", "end", values=(i + 1, "Failed", *[""] * 6))
            elif odds is None:
                tree.insert("", "end", values=(i + 1, card, *["-"] * 6))
            else:
                best_call, best_p = odds.best_plain()
                tree.insert("", "end", values=(
                    i + 1, card, *(_percent(odds.for_call(c)) for c in CALLS),
                    _percent(odds.exact), f"{CALL_LABELS[best_call]} {_percent(best_p)}"))

    def show_remaining_cards(self):
        if not self._need_game():
            return
        if self.cards_window and self.cards_window.winfo_exists():
            self.cards_window.lift()
            return
        self.cards_window = tk.Toplevel(self.root)
        self.cards_window.title("Remaining Cards")
        self.cards_text = tk.Text(self.cards_window, width=28, height=20,
                                  font=("Consolas", 11))
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

    def _text_window(self, title: str, body: str, size: str = "640x720"):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry(size)
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        widget = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set,
                         font=("Consolas", 10))
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
        return self._text_window("Keyboard Shortcuts", text.shortcut_help(), "460x340")


# --------------------------------------------------------------------------- #
# Game Assistant
# --------------------------------------------------------------------------- #

class AssistantGUI(PlayerGUI):
    """🧭 Game Assistant: mirror a game played with a real deck.

    You pick the nine box cards, then for each flip you pick the card that
    actually came off your deck. Odds and counts follow along.
    """

    TITLE = "Beat the Box: Game Assistant"

    def build_extra(self):
        frame = ttk.LabelFrame(self.main, text="Card You Flipped", padding=5)
        frame.grid(row=2, column=0, pady=5)
        ttk.Label(frame, text="Pick the card that came off your deck, "
                              "then select the box and make your call:").pack(padx=5, pady=2)
        self.drawn_var = tk.StringVar()
        self.drawn_combo = ttk.Combobox(frame, textvariable=self.drawn_var,
                                        state="readonly", width=30)
        self.drawn_combo.pack(padx=5, pady=5)

    def ask_box_cards(self, jokers: int) -> Optional[List[Card]]:
        def preview(picked: List[Card]):
            for i, btn in enumerate(self.box_buttons):
                btn.config(text=picked[i].label() if i < len(picked) else "")
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
        self.settings = settings
        self.game = self.create_game(settings, box)
        self.selected = None
        self.set_status("Box set! Pick the card you flipped, select a box, and call.")
        self.refresh()
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
        if self.game is None:
            self.drawn_combo["values"] = []
            return
        labels = []
        for card in sorted(self.game.draw_pile, key=lambda c: (-c.rank, c.suit)):
            if card.label() not in labels:  # two jokers share one entry
                labels.append(card.label())
        self.drawn_combo["values"] = labels
        if self.drawn_var.get() not in labels:
            self.drawn_var.set("")