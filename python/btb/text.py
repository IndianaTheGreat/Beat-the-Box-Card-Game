"""
==============================================
IN-APP TEXT AND SHORTCUTS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/text.py
Status: ACTIVE
Version: 1.4
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 308 passed)

VERSION 1.4 CHANGES (2026-10-20):
- Recovery text follows the new rule: a recovered box comes back with the
  card that beat it (the drawn card on top of its stack).
- The big and little jokers, and the Cards left view's Simple and Cards
  tabs, are described.
- Plainer wording throughout: fewer colons and less bold, no filler, and
  no em dashes.

VERSION 1.3 CHANGES (2026-10-20):
- Every help text is written in a light Markdown-style markup
  (btb/markup.py), so the pages show real headings, lists, tables, keys
  and card colours (widgets.DocView). shortcut_help() returns a table.
- Two switches instead of one: Ctrl+O shows or hides the odds (under the
  cards and the odds table); new Ctrl+K shows or hides the counts (the
  three card counts, the plays and the cards left). Ctrl+P / Ctrl+L turn
  on the switch they need.
- Calls listed in the new button order: Higher or Equal (D), Higher (W),
  Lower (S), Lower or Equal (A).
- RULES.md and STRATEGY.md moved into docs/; the text points there.
- The Simulator and Optimizer help describe the new Advanced charts.

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
check it on any machine. The rules text is a short summary; docs/RULES.md
stays the source of truth. The markup is described in btb/markup.py.

DEPENDENCIES:
------------
None

KEY FUNCTIONS:
-------------
- SHORTCUTS -> (keys shown, description, action, Tk event sequences)
- POSITION_KEYS -> number keys to box positions, numpad layout
- shortcut_help() -> the Shortcuts page (a table)
- RULES_SUMMARY, STRATEGY_GUIDE -> text for the How to Play and Strategy pages
- STRATEGY_SECTIONS -> section names shared with docs/STRATEGY.md
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
    ("D", "Higher or Equal", "higher_equal", ["<KeyPress-d>", "<KeyPress-D>"]),
    ("W", "Higher", "higher", ["<KeyPress-w>", "<KeyPress-W>"]),
    ("S", "Lower", "lower", ["<KeyPress-s>", "<KeyPress-S>"]),
    ("A", "Lower or Equal", "lower_equal", ["<KeyPress-a>", "<KeyPress-A>"]),
    ("Ctrl+Z", "Undo", "undo", ["<Control-z>", "<Control-Z>"]),
    ("Ctrl+N", "New game", "new_game", ["<Control-n>", "<Control-N>"]),
    ("Ctrl+O", "Show or hide the odds (under the cards, odds table)", "toggle_odds",
     ["<Control-o>", "<Control-O>"]),
    ("Ctrl+K", "Show or hide the counts (card counts, plays, cards left)", "toggle_counts",
     ["<Control-k>", "<Control-K>"]),
    ("Ctrl+P", "Odds table beside the board (shows the odds)", "show_probabilities",
     ["<Control-p>", "<Control-P>"]),
    ("Ctrl+L", "Cards left beside the board (shows the counts)", "show_remaining_cards",
     ["<Control-l>", "<Control-L>"]),
    ("Ctrl+R", "How to Play page", "show_rules", ["<Control-r>", "<Control-R>"]),
    ("Ctrl+Y", "Strategy page", "show_strategy", ["<Control-y>", "<Control-Y>"]),
    ("Ctrl+H", "Shortcuts page", "show_keyboard_help", ["<Control-h>", "<Control-H>"]),
]

# Number keys laid out like a numpad: 7 8 9 is the top row of the box.
POSITION_KEYS = {"7": 0, "8": 1, "9": 2, "4": 3, "5": 4, "6": 5, "1": 6, "2": 7, "3": 8}


def shortcut_help() -> str:
    """The Shortcuts page: one table row per shortcut, keys on chips."""
    rows = [f"| `{keys}` | {desc} |" for keys, desc, *_ in SHORTCUTS]
    return "\n".join([
        "# Keyboard Shortcuts",
        "",
        "These work on the Game Player and Game Assistant pages when you are "
        "not typing in a field.",
        "",
        "| Keys | What it does |",
        "|---|---|",
        *rows,
        "",
        "> Ctrl shortcuts work with Caps Lock on. Ctrl+C is left free for copying, "
        "on these help pages too.",
    ])


RULES_SUMMARY = """# How to Play

> The full rules, with worked examples, are in `docs/RULES.md`.

## Goal

Get through the whole draw pile with at least one box still alive.

## Setup

Shuffle 52 cards plus 0, 1 or 2 jokers. Deal 9 face up in a 3 × 3 grid.
That grid is **the box**, and the rest is the draw pile. Aces are high; suits don't matter.

## Your Turn

Pick a live box, make a call, then flip the top card of the pile.

| Call | Wins on | Costs |
|---|---|---|
| ▲= Higher or Equal | a higher card or the same rank | 1 inclusive call |
| ▲ Higher | a strictly higher card | free |
| ▼ Lower | a strictly lower card | free |
| ▼= Lower or Equal | a lower card or the same rank | 1 inclusive call |

- **Correct:** the drawn card goes on the box.
- **Wrong:** the box fails.
- A same-rank card on a plain Higher or Lower is a loss.

> Example: a box shows 7♠ and you call Higher. If you flip J♣, you are
> right and the J♣ now sits on that box. If you flip 7♥, the box fails,
> because a tie loses on a plain call (Higher or Equal would have won).

## Inclusive Calls

An inclusive call is spent when you make it, win or lose. If the flip is
an exact rank match, you also earn one recovery.

## Jokers

Any play involving a joker succeeds, whether the joker is drawn or is in
the box. With two jokers, one is the **Big Joker** (green) and one the
**Little Joker** (purple). They only look different and play exactly
alike. A joker is an exact match for any card, so an inclusive call
involving a joker always earns a recovery.

## Recovery

1. The play resolves first.
2. Then pick one failed box to bring back, or skip.
3. It returns with the card that beat it. When a box fails, the drawn
   card goes on top and the stack is turned over; a recovery turns it
   back, so that card is on top. Lower on a Q♥ that draws an A♠ fails
   the box, and recovering it later brings back the A♠.

If no box has failed, the recovery is lost. Recoveries can't be saved for
later.

## Win or Lose

- **Win:** the pile runs out with at least one box alive.
- **Lose:** all nine boxes fail."""


# Section names shared with docs/STRATEGY.md (tests/test_docs.py checks both).
STRATEGY_SECTIONS = ("Card Counting", "Reading the Count", "Inclusive Calls",
                     "Jokers", "Recoveries", "Using the Odds")

STRATEGY_GUIDE = """# Strategy Guide

> The full guide, with tables from thousands of simulated games, is
> `docs/STRATEGY.md` in the project folder.

## Card Counting

Each card is counted once, when it first becomes visible (the opening deal
or a flip). A recovered card is not counted again. Jokers and 8s count 0.

| Rank | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | J | Q | K | A |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Basic | -1 | -1 | -1 | -1 | -1 | -1 | 0 | +1 | +1 | +1 | +1 | +1 | +1 |
| Weighted | -2 | -2 | -2 | -1 | -1 | -1 | 0 | +1 | +1 | +1 | +2 | +2 | +2 |
| Advanced | -3 | -3 | -2 | -2 | -1 | -1 | 0 | +1 | +1 | +2 | +2 | +3 | +3 |

## Reading the Count

- **POSITIVE count:** many high cards have already been seen, so MORE LOW
  cards remain in the pile. Lean LOWER.
- **NEGATIVE count:** many low cards have already been seen, so MORE HIGH
  cards remain. Lean HIGHER.
- The bigger the number, the stronger the lean. The Weighted and Advanced
  counts give extra weight to the extreme cards.
- The count matters most for middle cards (7, 8, 9). A 2 or an A is a
  near-sure call whatever the count says.

## Inclusive Calls

- An inclusive call adds one thing, the chance that the next card TIES
  the box card. Early in the game that is only about 6% (3 cards of each
  rank are left out of about 50).
- So don't spend them early on any middle card. Wait until a rank is
  crowded in the pile, when a tie is much more likely.
- The simulator's **threshold** puts a number on this. It spends a call
  only when it adds at least that many points. 10 is the best all-rounder for
  5 to 10 calls; with only 1 to 3 calls, 15 does as well or better.
- With lots of calls (15 or more), spend them more freely (threshold
  about 5, or 0 when you have one for nearly every card). Unused calls are
  wasted when the pile runs out.

## Jokers

- A joker in the box is a guaranteed recovery. Spend an inclusive call on
  it once you have a failed box to bring back.
- Until then, hold it, as long as you still have inclusive calls.
- With no inclusive calls left, play the joker right away. It can't earn a
  recovery any more, so holding it just freezes one of your boxes.

## Recoveries

- Bring back the failed box with the most extreme card (a 2♣ or an A♦,
  say). It gives the easiest next call.
- Recoveries can't be saved. One earned with nothing failed is lost.

## Using the Odds

- `Ctrl+O` (**Show odds**) shows the chance of Higher and Lower under each
  card. `Ctrl+P` shows the full odds table beside the board.
- `Ctrl+K` (**Show counts**) shows the three card counts and your plays.
  `Ctrl+L` shows how many of each rank are left.
- Pick the box whose best plain call has the highest odds. The odds table
  starts sorted that way. When the odds are hidden, the count gives you a
  quick guess at the same thing.
- The count gets you most of the way without the odds. To use inclusive
  calls well, also keep track of how many cards of each rank in your box
  are left. `docs/CARD_COUNTING.md` shows what each habit is worth."""


TOOL_HELP = {
    "player": """## Game Player

Play Beat the Box with a shuffled deck.

1. Press **New Game** (`Ctrl+N`). Beside the board, choose jokers,
   inclusive calls and whether failed cards are shown when you recover,
   then press **Start Game**.
2. Click a box, or press its number key (`7 8 9` / `4 5 6` / `1 2 3`).
3. Make your call: Higher or Equal (`D`), Higher (`W`), Lower (`S`) or
   Lower or Equal (`A`). The banner at the top shows your call, the card
   drawn and the result.
4. On an exact match with an inclusive call, failed boxes glow gold. Click
   one to bring it back, or press **Skip Recovery** in the banner.

Buttons that make no sense are greyed out: Lower on a 2, Higher on an A,
and the plain calls on a joker while you still have inclusive calls (an
inclusive call on a joker is just as certain and can also recover a failed
box). The rules still allow these calls, but the game doesn't offer them.

The toolbar has two switches, each for this page only:

- **Show odds** (`Ctrl+O`): the chance of Higher (▲) and Lower (▼) under
  each card, and the **Odds table** (`Ctrl+P`). The table starts with the
  best chance at the top. Click a heading to sort by it (highest first,
  then lowest first, then by box).
- **Show counts** (`Ctrl+K`): the three card counts with what they
  suggest, every play so far, and the **Cards left** (`Ctrl+L`), shown
  as a **Simple** table or as the **Cards** themselves (four suit rows,
  with the ones already played faded).

Picking a view beside the board (or its shortcut) turns on the switch it
needs. The tiles (draw pile, inclusive calls, boxes alive) always show.
**Undo** (`Ctrl+Z`) takes back any play, including its recovery.

> More detail: `docs/GUIDE.md` in the project folder.""",

    "assistant": """## Game Assistant

Use this while you play with a real deck of cards.

1. Press **New Game** (`Ctrl+N`), choose the settings, then click the nine
   cards you dealt, in order from the top-left box to the bottom-right box. They
   appear on the board as you go. Each joker has its own button: **Big
   Joker** and **Little Joker**.
2. Each turn, flip your real card, then click that card in the **Card you
   flipped** grid. Cards already used are greyed out.
3. Select the box and make your call, the same as in the Game Player.

Everything else works like the Game Player: the banner, the odds and
counts switches, recoveries, greyed-out calls and undo. The odds come from
the cards you haven't seen yet, so they are exact for your real game.

> More detail: `docs/GUIDE.md` in the project folder.""",

    "simulator": """## Simulator

The built-in strategy plays thousands of games with one setting, and the
page reports how it did.

The strategy plays the plain call with the best odds, and spends an
inclusive call only when it adds at least the **threshold** in points of
win chance. It plays an inclusive call on a joker in the box once a box
has failed, plays the joker right away once no inclusive calls are left,
and recovers the failed box with the most extreme card.

**Settings:** number of games, jokers, inclusive calls, threshold and a
seed. The same seed always deals the same games, so runs can be repeated.

**Overview tab:**

- Win rate, with its 95% range ("25.6% ±0.9" means the true rate is
  almost certainly between 24.7% and 26.5%). More games make it narrower.
- Boxes left in winning games (chart), averages and the details table.

**Advanced tab:** a chart of every distribution (boxes left in wins, cards
left in losses, plays per game, inclusive calls used, recoveries, jokers
drawn), each with its average. **Show as text** gives every figure as
text to read or copy. **Export CSV / JSON** saves the results to open in
Excel or keep.

**Speed:** CPU cores "Auto" spreads big runs over several processes, using
only what is free and always leaving a core for you.

> More detail: `docs/GUIDE.md` in the project folder.""",

    "optimizer": """## Strategy Optimizer

The Optimizer tries every combination of jokers, inclusive calls and
thresholds in the ranges you give, plays the same deals with each, and
ranks them.

- **Same deals:** with one seed, every configuration plays the same
  shuffles, so any difference comes from the settings and not from the
  luck of the deal.
- **Ties:** highlighted rows are statistically tied with the best. Their
  95% ranges overlap, so the data can't tell them apart.
- **Confirm top 10:** re-runs the best ten with 5× more games on fresh
  deals. This catches a configuration that only looked best by luck.
- **Use Best in Simulator:** opens the Simulator page with the winning
  settings filled in.
- **Advanced tab:** charts of win rate against the threshold (one line per
  joker count, with the 95% ranges), against inclusive calls and against
  jokers, and the best configuration for each value. **Show as text**
  gives the full report to read or copy.
- **Export CSV / JSON:** one row per configuration.

Big sweeps are spread over several processes (CPU cores: Auto), and
**Stop** keeps every configuration that finished.

> More detail: `docs/GUIDE.md` in the project folder.""",
}


HOW_IT_WORKS = """## How the Suite Works

Everything happens in this one window. The sidebar on the left switches
pages; each page keeps its place when you switch away, so a long Optimizer
run keeps going while you play.

Every tool plays by the same rules engine (`btb/engine.py`), which follows
`docs/RULES.md` exactly. No tool has its own copy of a rule.

- `docs/GUIDE.md` explains each tool in full.
- `docs/STRATEGY.md` explains how to play well.
- `docs/CARD_COUNTING.md` explains the counts.

The window can be resized down to 960 × 620. The cards, tables and charts
follow it, and a panel that doesn't fit gets a scrollbar."""


IMPORTANT_POINTS = """## Important Points

### Rules worth remembering

- A same-rank card on a plain Higher or Lower is a loss.
- Inclusive calls are spent when made, win or lose.
- Exact match on an inclusive call = one recovery. A joker (drawn or in
  the box) is an exact match for anything.
- Recoveries can't be banked. With no failed box, the recovery is lost.
- A recovered box comes back with the card that beat it (the drawn card
  on top of its stack) instead of the card it held before.

### Settings limits

| Setting | Allowed |
|---|---|
| Jokers | 0 to 2 |
| Inclusive calls | 0 to 43 + jokers |
| Threshold | 0 to 100 percentage points (what an inclusive call must add over the best plain call before the strategy spends one) |

### Reading the counts

- **Positive count:** high cards have already been seen, so more LOW
  cards remain.
- **Negative count:** more HIGH cards remain.

### Reading simulator results

- "25.6% ±0.9" means the true win rate is almost certainly between 24.7%
  and 26.5%. Ten times more games makes the range about three times
  narrower.
- In the Optimizer, highlighted rows are statistically tied with the best.
  Use more games or **Confirm top 10** to separate them.

### Big runs

- CPU cores "Auto" checks free CPU and memory at the start of each run,
  uses at most three quarters of your cores, always leaves one free, and
  runs its helpers at low priority.
- Use **Stop** if a run is taking too long; finished results are kept.
- Use a seed to make a run repeatable."""


def tool_guide() -> str:
    """The Tool Guide page: how the suite works, each tool, then key points,
    with a dividing line between them."""
    parts = [HOW_IT_WORKS]
    for key in ("player", "assistant", "simulator", "optimizer"):
        parts.append(TOOL_HELP[key])
    parts.append(IMPORTANT_POINTS)
    return "# Tool Guide\n\n" + "\n\n---\n\n".join(parts)