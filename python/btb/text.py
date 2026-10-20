"""
==============================================
IN-APP TEXT AND SHORTCUTS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/text.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Rules summary, strategy guide and the shortcut table, moved out
  of BTBGamePlayer.py.
- Strategy guide now reads the count correctly: positive count = high
  cards seen = more LOW cards remain.
- Show Remaining Cards moved from Ctrl+C (copy) to Ctrl+L.

DESCRIPTION:
-----------
User-facing text shared by the GUIs. Kept free of Tkinter so tests can
check it on any machine. The rules text is a short summary; RULES.md stays
the source of truth.

DEPENDENCIES:
------------
None

KEY FUNCTIONS:
-------------
- SHORTCUTS -> (keys shown, description, action, Tk event sequences)
- POSITION_KEYS -> number keys to box positions, numpad layout
- shortcut_help() -> text for the Keyboard Help window
- RULES_SUMMARY, STRATEGY_GUIDE -> text for the help windows

NOTES:
-----
- Ctrl shortcuts are bound for both letter cases so Caps Lock works.
"""

# (keys shown to the player, what it does, GUI action name, Tk event sequences)
# Each Ctrl shortcut is bound for both letter cases so Caps Lock doesn't break
# it. Ctrl+C is deliberately left free for copy.
SHORTCUTS = [
    ("7 8 9 / 4 5 6 / 1 2 3", "Select a box (numpad layout)", "select", []),
    ("W", "Higher", "higher", ["<KeyPress-w>", "<KeyPress-W>"]),
    ("S", "Lower", "lower", ["<KeyPress-s>", "<KeyPress-S>"]),
    ("D", "Higher or Equal", "higher_equal", ["<KeyPress-d>", "<KeyPress-D>"]),
    ("A", "Lower or Equal", "lower_equal", ["<KeyPress-a>", "<KeyPress-A>"]),
    ("Ctrl+Z", "Undo", "undo", ["<Control-z>", "<Control-Z>"]),
    ("Ctrl+N", "New game", "new_game", ["<Control-n>", "<Control-N>"]),
    ("Ctrl+P", "Show probabilities", "show_probabilities", ["<Control-p>", "<Control-P>"]),
    ("Ctrl+L", "Show remaining cards (list)", "show_remaining_cards",
     ["<Control-l>", "<Control-L>"]),
    ("Ctrl+R", "How to play", "show_rules", ["<Control-r>", "<Control-R>"]),
    ("Ctrl+Y", "Strategy guide", "show_strategy", ["<Control-y>", "<Control-Y>"]),
    ("Ctrl+H", "Keyboard help", "show_keyboard_help", ["<Control-h>", "<Control-H>"]),
]

# Number keys laid out like a numpad: 7 8 9 is the top row of the box.
POSITION_KEYS = {"7": 0, "8": 1, "9": 2, "4": 3, "5": 4, "6": 5, "1": 6, "2": 7, "3": 8}


def shortcut_help() -> str:
    width = max(len(keys) for keys, *_ in SHORTCUTS)
    return "\n".join(f"{keys.ljust(width)}   {desc}" for keys, desc, *_ in SHORTCUTS)


RULES_SUMMARY = """Beat the Box: How to Play
(The full rules, with worked examples, are in RULES.md.)

GOAL
Get through the entire draw pile with at least one box still alive.

SETUP
Shuffle 52 cards plus 0, 1 or 2 jokers. Deal 9 face up in a 3x3 grid: the
box. The rest is the draw pile. Aces are high; suits don't matter.

YOUR TURN
Pick a live box, make a call, then flip the top card of the pile.
  Higher           wins on a strictly higher card      free
  Lower            wins on a strictly lower card       free
  Higher or Equal  wins on higher or the same rank     1 inclusive call
  Lower or Equal   wins on lower or the same rank      1 inclusive call
Correct: the drawn card goes on the box. Wrong: the box fails.
A same-rank card on a plain Higher or Lower is a loss.

INCLUSIVE CALLS
Spent when you make the call, win or lose. If the flip is an exact rank
match, you also earn one recovery.

JOKERS
Any play involving a joker succeeds, whether the joker is drawn or is in the
box. A joker is an exact match for any card, so an inclusive call involving
a joker always earns a recovery.

RECOVERY
The play resolves first. Then pick one failed box to bring back (or skip).
It returns with the card it failed on. If no box has failed, the recovery
is lost: recoveries can't be saved for later.

WIN / LOSE
Win: the pile runs out with at least one box alive.
Lose: all nine boxes fail."""


STRATEGY_GUIDE = """Beat the Box: Strategy Guide

CARD COUNTING
Each card is counted once, when it first becomes visible (the opening deal or
a flip). A recovered card is not counted again. Jokers and 8s count 0.

  Rank       2  3  4  5  6  7  8  9 10  J  Q  K  A
  Basic     -1 -1 -1 -1 -1 -1  0 +1 +1 +1 +1 +1 +1
  Weighted  -2 -2 -2 -1 -1 -1  0 +1 +1 +1 +2 +2 +2
  Advanced  -3 -3 -2 -2 -1 -1  0 +1 +1 +2 +2 +3 +3

READING THE COUNT
  * POSITIVE count: many high cards have already been seen, so MORE LOW
    cards remain in the pile. Lean LOWER.
  * NEGATIVE count: many low cards have already been seen, so MORE HIGH
    cards remain. Lean HIGHER.
  * The bigger the number, the stronger the lean. The weighted and advanced
    counts give extra weight to the extreme cards.

INCLUSIVE CALLS
  * Middle cards (7, 8, 9) are the coin flips. That's where an inclusive
    call adds the most.
  * A 2 or an A in the box is close to a sure thing with a plain call.
    Don't spend an inclusive call there.

JOKERS
  * A joker in the box is a guaranteed recovery: spend an inclusive call on
    it once you have a failed box to bring back.
  * Until then, keep it. Playing it trades a sure thing for a random card,
    and an inclusive call on it would earn a recovery that is lost.

RECOVERIES
  * Bring back the failed box with the most extreme card (a 2 or an A). It
    gives the easiest next call.

ODDS
  * Ctrl+P shows the exact odds for every box against the cards still in
    the pile. Use it to check what the count is telling you."""