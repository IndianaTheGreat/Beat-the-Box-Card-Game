<div align="center">

# 🧰 Beat the Box — Tool Guide

**What each of the four tools does, how to use it, and how it works inside.**

</div>

> [!NOTE]
> The rules are in [RULES.md](../RULES.md) and playing advice is in [STRATEGY.md](../STRATEGY.md). This guide covers the Python suite (version 1.2.0) in `python/`.

---

## 📋 Contents

1. [How the Suite Fits Together](#-how-the-suite-fits-together)
2. [Starting Up and Settings](#-starting-up-and-settings)
3. [Game Player](#-game-player)
4. [Game Assistant](#-game-assistant)
5. [Simulator](#-simulator)
6. [Strategy Optimizer](#-strategy-optimizer)
7. [Keyboard Shortcuts](#%EF%B8%8F-keyboard-shortcuts)
8. [Themes](#-themes)
9. [Tests](#-tests)
10. [Troubleshooting](#%EF%B8%8F-troubleshooting)

---

## 🧩 How the Suite Fits Together

```
                    RULES.md  (the rules, in words)
                        │
                 btb/engine.py  (the rules, in code: cards, odds, counts, play, undo)
                ┌───────┴──────────────────────┐
        btb/strategy.py                  btb/gui_game.py
     (how the computer plays)        Game Player + Game Assistant
                │
          btb/sim.py  (many games, sweeps, margins of error, parallel runs)
         ┌──────┴───────┐
  btb/gui_sim.py    btb/export.py
  Simulator +       CSV / JSON
  Optimizer
```

- **The engine is the only place the rules live.** The windows, the strategy and the simulator all call it; none of them has a rule of its own. The TypeScript version (Phase 2) will be checked against the same tests.
- **Supporting modules:** `theme.py` (colours and fonts), `settings.py` (what is remembered), `widgets.py` (the drawn cards, tiles and charts), `system.py` (how many CPU cores a run may use), `text.py` (help text and shortcuts).
- **Everything is standard-library Python.** Nothing to install except Python itself.

---

## 🚀 Starting Up and Settings

From the `python/` folder:

```bash
python main.py
```

The launcher shows one tile per tool. Each tool opens in its own window, so you can, for example, play in the Game Player while a long Optimizer run works in the background.

**Settings** (button on the launcher):

| Setting | What it does |
|---|---|
| **Theme** | Eight colour themes, numbered 1–8, each with a small preview. The choice applies to every open window at once. You can also switch from **View → Theme** in any tool. |
| **Show odds under the cards by default** | Whether new Player and Assistant windows start with the odds showing. Ctrl+O still switches them on or off in the window you are in, without changing this default. |
| **CPU cores** | How many processes the Simulator and Optimizer may use. **Auto** (recommended) checks what is free each time; **Scan Now** shows what Auto would pick right now. |

Settings are **remembered** in a small file in your user folder:

| System | File |
|---|---|
| Windows | `%APPDATA%\BeatTheBox\settings.json` |
| macOS | `~/Library/Application Support/BeatTheBox/settings.json` |
| Linux | `~/.config/beat-the-box/settings.json` |

Delete that file to go back to the defaults.

---

## 🎮 Game Player

**What it's for:** playing Beat the Box with a shuffled deck, with as much (or as little) help as you want.

### The window

| Area | What it shows |
|---|---|
| **Toolbar** | New Game, Undo, and the Show odds switch. |
| **Banner** (top, large) | Your last call and its result, for example `Higher on 7♠ → drew J♥ ✓ Correct!`. Green = correct, red = the box failed, gold = you earned a recovery. The line under it gives hints and tells you what to do next. |
| **The box** (3 × 3 cards) | Live cards face up; failed boxes as a card back. The selected box has a blue outline. The small number under each card is its key (7 8 9 / 4 5 6 / 1 2 3, like a numpad). With odds on, ▲ and ▼ show the chance of Higher and Lower. |
| **Tiles** | Cards left in the draw pile, inclusive calls left, boxes still alive. |
| **Card count** | The three running counts, each with ▼ (favours Lower) or ▲ (favours Higher), and a one-line reading: "More LOW cards left: lean Lower", or "The counts disagree" when they point different ways. See [STRATEGY.md](../STRATEGY.md#-reading-the-count). |
| **Plays** | Every play so far: the call, the card, ✓ or ✗, and any recovery. |
| **Call buttons** | Higher (W), Lower (S), Higher or Equal (D), Lower or Equal (A). The inclusive calls are the highlighted pair; they are greyed out when none are left. |

### A turn, step by step

1. **New Game** (Ctrl+N): choose 0–2 jokers, the number of inclusive calls, and whether failed cards are shown when recovering.
2. **Select a box**: click it, or press its number key.
3. **Make your call**: click a call button or press W / S / D / A.
4. The banner shows what was drawn and whether you were right. A correct card replaces the box card; a wrong one fails the box.
5. **Recovery:** if an inclusive call hits an exact match (or involves a joker) and a box has failed, the banner turns gold and failed boxes glow gold. Click one to bring it back with the card it failed on, or press **Skip Recovery** in the banner.
6. The game ends when the pile runs out (you win) or all nine boxes fail.

**Undo** (Ctrl+Z) takes back the last play, including any recovery made with it and any inclusive call it spent. You can undo all the way to the start.

### Menus and side windows

- **Game:** New Game, Undo, Close Window.
- **View:** Show Odds on Cards (Ctrl+O), **Probabilities** (Ctrl+P: every call's odds for every box, plus the recovery chance), **Remaining Cards** (Ctrl+L: how many of each rank are left), Theme.
- **Help:** How to Play (Ctrl+R), Strategy Guide (Ctrl+Y), Keyboard Shortcuts (Ctrl+H), About This Tool.

The side windows update after every play.

### How it works inside

- **New Game** shuffles with a seeded Mulberry32 generator (the same one the TypeScript version will use) and deals through `Game.new`.
- **Each call** is one `Game.play(position, call)`. The engine flips the top card, decides success with `call_wins`, checks for an exact match, updates the counts, and reports whether a recovery was earned, is waiting, or was lost (nothing to recover).
- **Odds** come from `Game.odds_all`, which counts the ranks left in the pile. The denominator is the number of cards in the pile; a joker in the pile counts as a win for every call.
- **Undo** restores a full snapshot of the game taken before each play, so nothing can drift out of step.

---

## 🧭 Game Assistant

**What it's for:** playing with a **real deck of cards** while the computer keeps track. You tell it which cards you dealt and which card you flipped each turn; it gives you exact odds and counts for your real game.

### Setting up

1. **New Game** (Ctrl+N): choose jokers and inclusive calls, as in the Player.
2. A grid of all 52 cards (plus one button per joker) opens. **Click the nine cards in your box, from the top-left to the bottom-right.** They appear on the board as you go. Undo Pick takes back the last one.

### Each turn

1. Flip a card from your real deck.
2. **Click that card in the "Card you flipped" grid.** Cards that are no longer in the pile are greyed out, so you can't pick one twice. "Flipped:" confirms your choice.
3. Select the box and make your call, exactly as in the Player.

Everything else (the banner, odds, counts, play history, recoveries, undo, menus and shortcuts) works the same as in the Game Player.

### How it works inside

- The game is created with `Game.from_box`: the box is what you entered, and the pile is **every other card in the deck, in unknown order**.
- Each play passes the card you picked as `play(position, call, drawn=card)`, so the engine uses your real card instead of a shuffled one.
- Because the pile is exactly the cards you haven't seen, the odds are exact for your game.

---

## 📊 Simulator

**What it's for:** letting the built-in strategy play thousands of games with one setting, to see how good that setting is.

### Settings

| Setting | Meaning |
|---|---|
| **Number of games** | More games = a more accurate win rate (see *margin of error* below). 10,000 is a good default. |
| **Jokers** | 0, 1 or 2. |
| **Inclusive calls** | 0 up to 43 + jokers. |
| **Threshold (% points)** | The strategy spends an inclusive call only when it adds at least this many points of win chance over the best plain call. Default 10. See [STRATEGY.md](../STRATEGY.md#%EF%B8%8F-inclusive-calls). |
| **Seed** | Leave blank for a random one (it is shown in the results). The same seed always deals the same games, so a run can be repeated exactly. |
| **CPU cores** | Auto (recommended) or a fixed number. Remembered between runs. |

### Results

| Part | What it shows |
|---|---|
| **Win rate (± 95% range)** | For example `25.6% ±0.9`: the true win rate for this setting is almost certainly between 24.7% and 26.5%. |
| **Games played, average boxes left in wins, average plays per game** | Quick totals. |
| **Chart** | In winning games, how often 1, 2, … 9 boxes were left at the end. |
| **Details table** | Wins and losses, the range, inclusive calls used, recoveries, jokers drawn, cards left in losses, fewest and most plays, the settings and the seed. |
| **Advanced Statistics** | Everything above as text, plus every distribution in full. |
| **Export CSV… / Export JSON…** | Save the results (see below). |

The progress line shows games per second while running, and the time taken and number of processes when done. **Stop** keeps the games finished so far and labels them as partial.

### Exports

- **CSV** opens in Excel. One table with three columns, `section, item, value`:
  - `settings`: jokers, inclusive calls, threshold, games, seed
  - `summary`: games, wins, losses, win rate, margin low/high, averages, min/max plays
  - one section per distribution (`boxes_left_in_wins`, `cards_left_in_losses`, `plays`, `inclusive_used`, `recoveries`, `jokers_drawn`): value → number of games
- **JSON** holds the same data in one file, plus the suite version and the export time.

### How it works inside

**The strategy** (`btb/strategy.py`), each turn:

1. If a joker is in the box: with no inclusive calls left, play it; with a failed box and a call left, spend an inclusive call on it (guaranteed recovery); otherwise hold it.
2. Find the box whose **best plain call** has the highest odds.
3. Find the box whose **best inclusive call** has the highest odds.
4. Spend the inclusive call only if it beats the plain call by more than the threshold.
5. Ties go to the higher recovery chance, then the more extreme card, then the higher rank, so the choice never depends on where a card sits on the board.
6. After a recovery is earned, bring back the failed box with the best next-call odds (in practice the most extreme card).

**Seeds:** game *i* of a run uses seed + *i*. That makes every run repeatable, and lets the Optimizer give every configuration the same deals.

**Speed:**

- The strategy reads one odds table per turn from the engine (`odds_by_rank`) instead of recounting the pile for every box.
- Statistics are kept as **tallies** (how many games had 30 plays, 31 plays, …), so memory stays the same whether you run a thousand games or ten million.
- **Parallel runs:** big runs (4,000 games or more) are split into chunks of seeded games and spread over helper processes. Because every game has its own seed, the result is **identical** to a one-process run; the tests check this.
- **Auto CPU cores** measures how idle the CPU is (over a fifth of a second) and how much memory is free, then uses at most 75% of your cores, always leaves one free, only counts cores that are idle right now, and allows about 150 MB per helper. Helpers run at **low priority**, so anything you are doing comes first.
- If helper processes can't start (or stop working), the run finishes in the main process instead of failing.

**The window never freezes:** the run happens on a background thread that reports progress through a queue; the window checks the queue 20 times a second.

**Margin of error:** the range is a *Wilson score interval* at 95%. It is accurate even near 0% and 100%. Ten times more games makes it about three times narrower:

| Games | Typical range at a 25% win rate |
|---|---|
| 1,000 | ±2.7 points |
| 10,000 | ±0.85 points |
| 100,000 | ±0.27 points |

---

## 🔬 Strategy Optimizer

**What it's for:** finding the best settings by trying every combination in a range, on the same deals, and ranking them.

### Settings

| Setting | Meaning |
|---|---|
| **Games per test** | Games played by each configuration. Default 1,000. |
| **Jokers, Inclusive calls, Threshold** | The ranges to try. Combinations that break the rules (more inclusive calls than cards) are skipped. |
| **Threshold step** | The gap between thresholds tried (default 5: 0, 5, 10, … 30). |
| **Seed** | As in the Simulator. Every configuration plays the same deals. |
| **Confirm top 10** | After the sweep, re-run the ten best with 5× more games on **fresh** deals (on by default). |
| **CPU cores** | As in the Simulator. |

A sweep is limited to 5,000 configurations, and very large runs ask before starting.

### Results

| Part | What it shows |
|---|---|
| **Tiles** | The best win rate (± range), its settings, how many configurations were tested and how many are tied, and the total games played. |
| **Table** | One row per configuration: rank, win %, ±, jokers, calls, threshold, average boxes left in wins, games. **Click a heading to sort** (click again to reverse). |
| **Highlighted rows** | Statistically **tied for best**: their 95% ranges overlap the winner's, so the data can't tell them apart. |
| **All configurations / Confirmed top 10** | Switch between the sweep and the confirmation run. When there is a confirmation, the winner shown in the tiles is the confirmed winner. |
| **Use Best in Simulator** | Opens a Simulator with the winning jokers, calls, threshold and seed filled in, ready for a bigger run. |
| **Advanced Statistics** | The best overall, the best for each joker count, inclusive-call count and threshold, and the top five for each. |
| **Export CSV… / JSON…** | One row per configuration. |

### Exports

The CSV has one row per configuration with these columns:

`phase, rank, jokers, inclusive_calls, threshold, games, wins, win_rate, margin_low, margin_high, tied_for_best, avg_boxes_left_in_wins, avg_plays, avg_inclusive_used, avg_recoveries, seed`

`phase` is `sweep` for the main run and `confirm` for the confirmation rows. `seed` is the first seed that row played: the sweep seed for sweep rows, and the sweep seed plus the games per test for confirmation rows, so either can be repeated in the Simulator (with 5× the games for a confirmation row). The JSON adds the sweep settings, the best configuration, the suite version and the export time.

### How it works inside

- **Same deals for everyone.** With one seed, every configuration plays exactly the same shuffles (seed, seed + 1, …), so differences come from the settings, not from the luck of the deal.
- **Confirmation** uses the next block of seeds, deals no configuration has seen. A configuration that only looked best by luck usually drops back.
- **Stop** keeps only configurations that finished, because a half-finished one would skew the ranking. Stopping during the confirmation drops the unfinished confirmation, so the sweep's own ranking stands.
- Sweeps use the same parallel chunks, tallies and CPU limits as the Simulator, with one pool of helpers for the whole sweep.

---

## ⌨️ Keyboard Shortcuts

In the Game Player and Game Assistant:

| Keys | Action |
|---|---|
| `7 8 9` / `4 5 6` / `1 2 3` | Select a box (numpad layout; the numpad works too) |
| `W` / `S` | Higher / Lower |
| `D` / `A` | Higher or Equal / Lower or Equal |
| `Ctrl+Z` | Undo |
| `Ctrl+N` | New game |
| `Ctrl+O` | Show or hide odds on the cards |
| `Ctrl+P` | Probabilities window |
| `Ctrl+L` | Remaining cards window |
| `Ctrl+R` / `Ctrl+Y` / `Ctrl+H` | How to play / Strategy guide / Keyboard help |

Letter shortcuts work with Caps Lock on. `Ctrl+C` is left free for copying.

---

## 🎨 Themes

| # | Theme | Look |
|:-:|---|---|
| 1 | **Felt Green** (default) | Green card table, red card backs, gold buttons |
| 2 | Royal Blue | Deep blue table, orange card backs |
| 3 | Casino Red | Red table, blue card backs, yellow buttons |
| 4 | Classic Light | Light grey and white, blue accents |
| 5 | Midnight | Dark navy, sky-blue accents |
| 6 | Slate | Dark grey, teal accents |
| 7 | Parchment | Warm paper tones, brown accents |
| 8 | High Contrast | Black and white with bright yellow, for maximum readability |

**Change the default** in `python/btb/theme.py`: set `DEFAULT_THEME` to a name or a number (for example `DEFAULT_THEME = 5`). A theme chosen in Settings overrides the default until the settings file is deleted.

**Add a theme:** copy one `Theme(...)` block in `THEMES`, give it a new name and change the colours. It appears in Settings and View → Theme automatically. The tests check every theme for readable contrast, so `pytest` will tell you if a colour pair is too faint.

---

## 🧪 Tests

The tests in `python/tests/` are the executable spec, and they will be the spec for the TypeScript port too.

| File | Covers |
|---|---|
| `test_rules.py` | Every rule in RULES.md |
| `test_bugs.py` | One test per bug fixed from the original v1 files |
| `test_strategy_and_sim.py` | Strategy choices, seeded batches, progress, Stop, sweeps |
| `test_speed_and_accuracy.py` | The fast strategy matches the original move for move; parallel equals single-process; margins, ties, confirmation, fallback |
| `test_export_and_system.py` | CSV and JSON exports, the CPU/memory limits, the settings file |
| `test_theme_and_look.py` | Every theme's contrast; live theme switching; banner, odds toggle, cards, exports and tables in the windows |
| `test_gui.py` | Keyboard, recovery on the board, side windows, Simulator and Optimizer runs, background-thread safety |
| `test_docs.py` | RULES.md, STRATEGY.md and the in-app guide agree with the engine and with each other; every link to a heading works |

```bash
cd python
pip install -r requirements-dev.txt
pytest                 # Windows / macOS
xvfb-run pytest        # headless Linux, to include the window tests
```

Tests never touch your real settings file.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `No module named tkinter` (Linux) | `sudo apt install python3-tk` (Debian/Ubuntu) or `sudo dnf install python3-tkinter` (Fedora). |
| The window is cut off on a small screen | The Game Assistant is the tallest window (about 720 px) and the Optimizer the widest (about 1,300 px). Maximise the window; on a very small screen, lower the display scaling in your system settings. |
| A run is slow | Check CPU cores is **Auto** (or set a number), and use fewer games per test in the Optimizer. The progress line shows games per second. |
| The computer feels busy during a run | Set CPU cores to a lower number; helpers already run at low priority. |
| Settings look wrong | Delete the settings file (see [Starting Up and Settings](#-starting-up-and-settings)). |