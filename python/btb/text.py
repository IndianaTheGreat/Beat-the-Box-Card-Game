"""
==============================================
IN-APP TEXT AND SHORTCUTS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/text.py
Status: ACTIVE
Version: 1.2
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 254 passed)

VERSION 1.2 CHANGES (2026-10-20):
- Text for the one-window app: HOW_IT_WORKS and IMPORTANT_POINTS moved
  here from main.py; tool_guide() builds the Tool Guide page.
- TOOL_HELP rewritten for pages instead of menus and pop-up windows.
- Ctrl+O now shows or hides the odds, the card count and the plays;
  Ctrl+P / Ctrl+L show the odds table / cards left beside the board;
  Ctrl+R / Ctrl+Y / Ctrl+H open the How to Play / Strategy / Shortcuts
  pages.
- Shortcuts are listed in the same order as the call buttons (W, D, S, A).
- Strategy guide: the "Using the odds" section matches the new controls
  and points to docs/CARD_COUNTING.md.

VERSION 1.1 CHANGES (2026-10-20):
- New shortcut: Ctrl+O shows or hides the odds under each card.
- New TOOL_HELP: the "About This Tool" text for each of the four tools.
- Strategy guide rewritten as a short version of STRATEGY.md, with the
  same section names (a test keeps the two in step), the measured value
  of inclusive calls and thresholds, and the joker rule of thumb.

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
- shortcut_help() -> text for the Shortcuts page
- RULES_SUMMARY, STRATEGY_GUIDE -> text for the How to Play and Strategy pages
- STRATEGY_SECTIONS -> section names shared with STRATEGY.md
- TOOL_HELP -> what each tool does, keyed player / assistant /
  simulator / optimizer
- HOW_IT_WORKS, IMPORTANT_POINTS, tool_guide() -> the Tool Guide page

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
    ("D", "Higher or Equal", "higher_equal", ["<KeyPress-d>", "<KeyPress-D>"]),
    ("S", "Lower", "lower", ["<KeyPress-s>", "<KeyPress-S>"]),
    ("A", "Lower or Equal", "lower_equal", ["<KeyPress-a>", "<KeyPress-A>"]),
    ("Ctrl+Z", "Undo", "undo", ["<Control-z>", "<Control-Z>"]),
    ("Ctrl+N", "New game", "new_game", ["<Control-n>", "<Control-N>"]),
    ("Ctrl+O", "Show or hide odds, card count and plays", "toggle_odds",
     ["<Control-o>", "<Control-O>"]),
    ("Ctrl+P", "Odds table beside the board", "show_probabilities",
     ["<Control-p>", "<Control-P>"]),
    ("Ctrl+L", "Cards left beside the board", "show_remaining_cards",
     ["<Control-l>", "<Control-L>"]),
    ("Ctrl+R", "How to Play page", "show_rules", ["<Control-r>", "<Control-R>"]),
    ("Ctrl+Y", "Strategy page", "show_strategy", ["<Control-y>", "<Control-Y>"]),
    ("Ctrl+H", "Shortcuts page", "show_keyboard_help", ["<Control-h>", "<Control-H>"]),
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


# Section names shared with STRATEGY.md (tests/test_docs.py checks both).
STRATEGY_SECTIONS = ("Card Counting", "Reading the Count", "Inclusive Calls",
                     "Jokers", "Recoveries", "Using the Odds")

STRATEGY_GUIDE = """Beat the Box: Strategy Guide
(The full guide, with tables from thousands of simulated games, is
STRATEGY.md in the project folder.)

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
  * The count matters most for middle cards (7, 8, 9). A 2 or an A is a
    near-sure call whatever the count says.

INCLUSIVE CALLS
  * An inclusive call adds exactly one thing: the chance that the next card
    TIES the box card. Early in the game that is only about 6% (3 cards of
    each rank are left out of about 50).
  * So don't spend them early on any middle card. Wait until a rank is
    crowded in the pile, when a tie is much more likely.
  * The simulator's threshold is this idea as a number: spend a call only
    when it adds at least that many points. 10 is the best all-rounder for
    5 to 10 calls; with only 1 to 3 calls, 15 does as well or better.
  * With lots of calls (15 or more), spend them more freely (threshold
    about 5, or 0 when you have one for nearly every card). Unused calls are wasted
    when the pile runs out.

JOKERS
  * A joker in the box is a guaranteed recovery: spend an inclusive call on
    it once you have a failed box to bring back.
  * Until then, hold it, but only while you still have inclusive calls.
  * With no inclusive calls left, play the joker right away. It can't earn
    a recovery any more, so holding it just freezes one of your boxes.

RECOVERIES
  * Bring back the failed box with the most extreme card (a 2 or an A). It
    gives the easiest next call.
  * Recoveries can't be saved: one earned with nothing failed is lost.

USING THE ODDS
  * Ctrl+O shows the odds under each card, the card count and your plays;
    Ctrl+P shows the full odds table beside the board.
  * Pick the box whose best plain call has the highest odds. The count is
    a quick way to guess the same thing when the odds are hidden.
  * The count gets you most of the way without the odds. To use inclusive
    calls well, also keep track of how many cards of each rank in your box
    are left. docs/CARD_COUNTING.md shows what each habit is worth."""


TOOL_HELP = {
    "player": """Game Player

Play Beat the Box with a shuffled deck.

  1. New Game (Ctrl+N): choose jokers, inclusive calls and whether failed
     cards are shown when you recover, beside the board, then Start Game.
  2. Click a box (or press its number key: 7 8 9 / 4 5 6 / 1 2 3).
  3. Make your call: Higher (W), Higher or Equal (D), Lower (S),
     Lower or Equal (A). The banner at the top shows your call, the card
     drawn and the result.
  4. On an exact match with an inclusive call, failed boxes glow gold:
     click one to bring it back, or Skip Recovery in the banner.

Buttons that make no sense are greyed out: Lower on a 2, Higher on an A,
and the plain calls on a joker while you still have inclusive calls (an
inclusive call on a joker is just as certain and can also recover a
failed box).
The rules still allow them; the game just doesn't offer them.

Show odds & counts (Ctrl+O) adds the odds under each card, the three card
counts with what they suggest, and every play so far. Ctrl+P shows the
full odds table and Ctrl+L the cards left, in the same place. The tiles
(draw pile, inclusive calls, boxes alive) always show. Undo (Ctrl+Z)
takes back any play, including its recovery.

More detail: docs/GUIDE.md in the project folder.""",

    "assistant": """Game Assistant

Use this while you play with a real deck of cards.

  1. New Game (Ctrl+N), choose the settings, then click the nine cards you
     dealt, in order from the top-left box to the bottom-right box. They
     appear on the board as you go.
  2. Each turn, flip your real card, then click that card in the
     "Card you flipped" grid. Cards already used are greyed out.
  3. Select the box and make your call, exactly as in the Game Player.

Everything else works like the Game Player: the banner, the odds, the card
counts, recoveries, greyed-out calls and undo. The odds come from the
cards you haven't seen yet, so they are exactly right for your real game.

More detail: docs/GUIDE.md in the project folder.""",

    "simulator": """Simulator

Lets the built-in strategy play thousands of games with one setting and
reports how it did.

The strategy plays the plain call with the best odds, and spends an
inclusive call only when it adds at least the THRESHOLD in points of win
chance. It plays an inclusive call on a joker in the box once a box has
failed, plays the joker right away once no inclusive calls are left, and
recovers the failed box with the most extreme card.

Settings: number of games, jokers, inclusive calls, threshold and a seed.
The same seed always deals the same games, so runs can be repeated.

Results (Overview tab):
  * Win rate, with its 95% range ("25.6% ±0.9" means the true rate is
    almost certainly between 24.7% and 26.5%). More games = narrower.
  * Boxes left in winning games (chart), averages and the details table.
The Advanced tab lists every distribution in full. Export CSV / JSON saves
the results to open in Excel or keep.

Speed: CPU cores "Auto" spreads big runs over several processes, using
only what is free and always leaving a core for you.

More detail: docs/GUIDE.md in the project folder.""",

    "optimizer": """Strategy Optimizer

Tries every combination of jokers, inclusive calls and thresholds in the
ranges you give, plays the same deals with each, and ranks them.

  * Same deals: with one seed, every configuration plays exactly the same
    shuffles, so differences come from the settings, not luck of the deal.
  * Ties: highlighted rows are statistically tied with the best: their 95%
    ranges overlap, so the data can't tell them apart.
  * Confirm top 10: re-runs the best ten with 5x more games on fresh
    deals. This catches a configuration that only looked best by luck.
  * Use Best in Simulator: opens the Simulator page with the winning
    settings filled in.
  * Advanced tab: the best for each joker count, call count and threshold.
  * Export CSV / JSON: one row per configuration.

Big sweeps are spread over several processes (CPU cores: Auto), and Stop
keeps every configuration that finished.

More detail: docs/GUIDE.md in the project folder.""",
}


HOW_IT_WORKS = """Beat the Box: How the Suite Works

Everything happens in this one window. The sidebar on the left switches
pages; each page keeps its place when you switch away, so a long Optimizer
run keeps going while you play.

Every tool plays by the same rules engine (btb/engine.py), which follows
RULES.md exactly. Nothing about the rules is duplicated between tools.
docs/GUIDE.md explains each tool in full; STRATEGY.md explains how to play
well; docs/CARD_COUNTING.md explains the counts.

The window can be resized down to 960 x 620: the cards, tables and charts
follow it, and a panel that doesn't fit gets a scrollbar."""


IMPORTANT_POINTS = """Important Points

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


def tool_guide() -> str:
    """The Tool Guide page: how the suite works, each tool, then key points."""
    parts = [HOW_IT_WORKS]
    for key in ("player", "assistant", "simulator", "optimizer"):
        parts.append(TOOL_HELP[key])
    parts.append(IMPORTANT_POINTS)
    rule = "\n\n" + "-" * 66 + "\n\n"
    return rule.join(parts)