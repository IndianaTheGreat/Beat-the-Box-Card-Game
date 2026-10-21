<div align="center">

# 🧰 Beat the Box: Tool Guide

**What each of the four tools does, how to use it, and how it works.**

</div>

> [!NOTE]
> The rules are in [RULES.md](RULES.md), playing advice is in [STRATEGY.md](STRATEGY.md), and the card counts are explained in [CARD_COUNTING.md](CARD_COUNTING.md). This guide covers the Python suite (version 1.4.0) in `python/`.

---

## 📋 Contents

1. [How the Suite Fits Together](#-how-the-suite-fits-together)
2. [The Window, Pages and Settings](#-the-window-pages-and-settings)
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
               docs/RULES.md  (the rules, in words)
                        │
                 btb/engine.py  (the rules, in code: cards, odds, counts, play, undo)
                ┌───────┴──────────────────────┐
        btb/strategy.py                  btb/gui_game.py
     (how the computer plays)        Game Player + Game Assistant pages
                │                              │
          btb/sim.py  (many games, sweeps,     │
           margins of error, parallel runs)    │
         ┌──────┴───────┐                      │
  btb/gui_sim.py    btb/export.py              │
  Simulator +       CSV / JSON                 │
  Optimizer pages                              │
         └──────────────┬──────────────────────┘
                   btb/app.py  (one window: sidebar + pages)
                        │
                     main.py  (starts it)
```

- **The engine is the only place the rules live.** The pages, the strategy and the simulator all call it, and none of them has a rule of its own. The TypeScript version (Phase 2) will be checked against the same tests.
- **Other modules:** `theme.py` (colours and fonts), `settings.py` (what is remembered), `widgets.py` (the drawn cards, tiles, charts and help pages), `system.py` (how many CPU cores a run may use), `text.py` (help text and shortcuts), `markup.py` (reads the light Markdown the help text is written in).
- **Everything is standard-library Python.** You only need Python itself.

---

## 🪟 The Window, Pages and Settings

From the `python/` folder:

```powershell
python main.py
```

(The Microsoft Store Python on Windows has no `py` launcher, so the command is `python`. On macOS and Linux it may be `python3`.)

Everything happens in one window. The **sidebar** on the left switches pages:

| Section | Pages |
|---|---|
| (top) | **Home**: one tile per tool |
| PLAY | **Game Player**, **Game Assistant** |
| ANALYZE | **Simulator**, **Optimizer** |
| HELP | **How to Play**, **Strategy**, **Tool Guide** (what each tool does) and **Shortcuts**. These are formatted pages with headings, tables and keys. Select text with the mouse and copy it with Ctrl+C (or right-click › Copy); Ctrl+A selects the whole page. |
| (bottom) | **Settings** |

- **Pages keep their place.** A page is built the first time you open it and stays as it was when you switch away. A game in progress is still there when you come back, and a long Optimizer run keeps going while you play.
- **Nothing pops up.** New Game settings, the Assistant's card picker, the odds table, the Advanced charts, error messages and the end-of-game message all appear on the page itself. The one exception is the system Save dialog when you export results.
- **Resize freely.** The window opens sized to your screen. Make it bigger or smaller and the cards, tables and charts follow (smallest size 960 × 620). In a small window, a side panel that is too tall gets a scrollbar, a table that is too wide gets one along the bottom, and the toolbar drops its shortcut hints. Nothing gets cut off.
- **Keyboard shortcuts** act only on the page that is showing, and never while you are typing in a box.

**Settings** (bottom of the sidebar):

| Setting | What it does |
|---|---|
| **Theme** | Eight colour themes, numbered 1–8, each with a small preview. The theme applies to the whole window when you press Save. |
| **Show odds by default** | Whether the Player and Assistant pages start with the odds showing (under the cards, and the odds table), for pages not opened yet in this session. Ctrl+O still switches them on a page without changing this default. |
| **Show counts by default** | The same for the counts (the three card counts, your plays and the cards left). Ctrl+K switches them on a page. A settings file from before this split uses its old "odds & counts" choice for both. |
| **CPU cores** | How many processes the Simulator and Optimizer may use. **Auto** (recommended) checks what is free each time. **Scan Now** shows what Auto would pick right now. |

**Save** applies and remembers only what you changed on the page. **Cancel** (or Escape) drops your unsaved choices and goes back to the page you came from. When you open the page it always shows what is saved.

Settings are remembered in a small file in your user folder:

| System | File |
|---|---|
| Windows | `%APPDATA%\BeatTheBox\settings.json` |
| macOS | `~/Library/Application Support/BeatTheBox/settings.json` |
| Linux | `~/.config/beat-the-box/settings.json` |

Delete that file to go back to the defaults.

---

## 🎮 Game Player

Use it to play Beat the Box with a shuffled deck, with as much or as little help as you want.

### The page

| Area | What it shows |
|---|---|
| **Toolbar** | New Game, Undo, and two switches: **Show odds** (Ctrl+O) and **Show counts** (Ctrl+K). In a narrow window the labels drop their shortcut hints ("Odds", "Counts"). |
| **Banner** (top, large) | Your last call and its result, for example `Higher on 7♠ → drew J♥ ✓ Correct!`. Green means correct, red means the box failed, and gold means you earned a recovery (with a **Skip Recovery** button). The line under it gives hints and tells you what to do next. The end of the game is announced here too. If your last box fails, the banner says "The box wins." and still shows that call and the card you drew. |
| **The box** (3 × 3 cards) | Live cards are face up and failed boxes show a card back. The selected box has a blue outline. The small number under each card is its key (7 8 9 / 4 5 6 / 1 2 3, like a numpad). With **Show odds** on, ▲ and ▼ show the chance of Higher and Lower. |
| **Tiles** | Cards left in the draw pile, inclusive calls left and boxes still alive. Always shown. |
| **Side panel views** | **Count & plays** and **Cards left** need **Show counts** (Ctrl+K); **Odds table** needs **Show odds** (Ctrl+O). Picking a view whose switch is off turns it on, and a line under the view says which switch is off. With both off, the panel says how to turn them on. The side panel takes whatever width the cards don't need, and scrolls if the window is too short for it. |
| **Count & plays** | The three running counts, each with ▼ or ▲ for the call it favours, a one-line reading, and every play so far. |
| **Odds table** (Ctrl+P) | One row per box: the card first, then its box key, every call's chance in button order, the tie chance, and the best plain call. It starts sorted by Best, highest first. Click a heading to sort by that column. The first click puts the highest at the top, the second the lowest, and the third goes back to box order (7 8 9 / 4 5 6 / 1 2 3). The sorted column is marked ↓ or ↑. Failed boxes always sit at the bottom. |
| **Cards left** (Ctrl+L) | What is still in the pile, shown two ways. **Simple** gives one line per rank (Ace down to 2, then jokers) with the number left and a dot for each card of that rank still to come. **Cards** lays the deck out in four suit rows, Ace to 2, plus the jokers, with cards already played drawn faded. |
| **Call buttons** (across the page) | From the left: ▲= Higher or Equal (D), ▲ Higher (W), ▼ Lower (S), ▼= Lower or Equal (A). The plain calls sit in the middle. The two ▲ buttons share one colour and the two ▼ buttons another. Their text shrinks to fit a narrow window. |

### Calls that are greyed out

The game only offers calls that make sense on the selected card:

| Card | Not offered | Why |
|---|---|---|
| `2` | ▼ Lower | Nothing is lower than a 2. It could only win on a joker, and Higher wins on that joker too. |
| `A` | ▲ Higher | Nothing is higher than an A (same reasoning). |
| Joker (big or little), with inclusive calls left | ▲ Higher, ▼ Lower | An inclusive call on a joker is just as certain and also earns a recovery. Once you're out of inclusive calls, Higher and Lower come back so the joker can still be played. |
| Any card, no inclusive calls left | ▲=, ▼= | None left to spend. |

This is only a guard rail on screen. [RULES.md](RULES.md) still allows every call, and the Simulator's results are unaffected. Pressing the key for a greyed-out call explains why in the hint line (and only suggests an inclusive call if you have one left).

### A turn, step by step

1. Press **New Game** (Ctrl+N) and the settings appear beside the board. Choose 0–2 jokers, the number of inclusive calls, and whether failed cards are shown when recovering, then **Start Game**.
2. Select a box by clicking it or pressing its number key.
3. Make your call. Click a call button or press D / W / S / A.
4. The banner shows what was drawn and whether you were right. A correct card replaces the box card. On a wrong call the drawn card goes on top of the box card and the box fails. If the box is recovered later, it comes back with that top card.
5. If an inclusive call hits an exact match (or involves a joker) and a box has failed, the banner turns gold and failed boxes glow gold. Click one to bring it back with the card that beat it (the card on top of its stack), or press **Skip Recovery** in the banner.
6. The game ends when the pile runs out (you win) or all nine boxes fail. The banner says which.

**Undo** (Ctrl+Z) takes back the last play, including any recovery made with it and any inclusive call it spent. You can undo all the way to the start.

### Help from the page

- **Ctrl+O** shows or hides the odds, and **Ctrl+K** shows or hides the counts. Each switch is for this page only (Settings holds the defaults).
- **Ctrl+P** shows the odds table (switching the odds on if needed) and **Ctrl+L** the cards left (switching the counts on if needed), in the side panel.
- **Ctrl+R**, **Ctrl+Y** and **Ctrl+H** open the How to Play, Strategy and Shortcuts pages.

### How it works inside

- **New Game** shuffles with a seeded Mulberry32 generator (the same one the TypeScript version will use) and deals through `Game.new`.
- **Each call** is one `Game.play(position, call)`. The engine flips the top card, decides success with `call_wins`, checks for an exact match, updates the counts, and reports whether a recovery was earned, is waiting, or was lost (nothing to recover).
- **Greyed-out calls** come from the engine's `offered_calls`, and the reason shown for one from `call_blocked_reason`, so the TypeScript version will offer exactly the same buttons and reasons.
- **Jokers:** a two-joker deck has a Big Joker (green) and a Little Joker (purple), so you can tell them apart on the board, in the banner and in the odds table. They only look different. In the engine they are equal cards, so odds, counts and statistics treat them the same.
- **Odds** come from `Game.odds_all`, which counts the ranks left in the pile. The denominator is the number of cards in the pile; a joker in the pile counts as a win for every call.
- **Undo** restores a full snapshot of the game taken before each play, so nothing can drift out of step.

---

## 🧭 Game Assistant

Use it when you play with a real deck of cards and want the computer to keep track. You tell it which cards you dealt and which card you flipped each turn, and it gives you exact odds and counts for your game.

### Setting up

1. Press **New Game** (Ctrl+N), choose jokers and inclusive calls beside the board as in the Player, then press Start Game.
2. A grid of all 52 cards (plus a **Big Joker** and a **Little Joker** button, for as many jokers as you chose) appears beside the board. Click the nine cards in your box, from the top-left to the bottom-right. They appear on the board as you go. **Undo Pick** takes back the last one; **Cancel** puts the previous game back. The mini cards shrink to fit a narrow window.

### Each turn

1. Flip a card from your real deck.
2. Click that card in the **Card you flipped** grid. Cards that are no longer in the pile are greyed out, so you can't pick one twice. "Flipped:", beside the joker buttons, confirms your choice.
3. Select the box and make your call, the same as in the Player.

Everything else (the banner, the odds and counts switches, greyed-out calls, recoveries, undo and shortcuts) works the same as in the Game Player.

### How it works inside

- The game is created with `Game.from_box`. The box is what you entered, and the pile is every other card in the deck, in unknown order.
- Each play passes the card you picked as `play(position, call, drawn=card)`, so the engine uses your real card instead of a shuffled one.
- Because the pile is exactly the cards you haven't seen, the odds are exact for your game.

---

## 📊 Simulator

The Simulator lets the built-in strategy play thousands of games with one setting, so you can see how good that setting is.

### Settings

| Setting | Meaning |
|---|---|
| **Number of games** | More games give a more accurate win rate (see *margin of error* below). 10,000 is a good default. |
| **Jokers** | 0, 1 or 2. |
| **Inclusive calls** | 0 up to 43 + jokers. |
| **Threshold (% points)** | The strategy spends an inclusive call only when it adds at least this many points of win chance over the best plain call. Default 10. See [STRATEGY.md](STRATEGY.md#%EF%B8%8F-inclusive-calls). |
| **Seed** | Leave blank for a random one (it is shown in the results). The same seed always deals the same games, so a run can be repeated exactly. |
| **CPU cores** | Auto (recommended) or a fixed number. Remembered between runs and shared with the Optimizer and Settings, so a change in one shows up in the others. |

Invalid settings show a red message under the progress bar and nothing starts. A run of more than 2,000,000 games needs a second press of Run before it starts.

### Results

The **Overview** tab:

| Part | What it shows |
|---|---|
| **Win rate (± 95% range)** | For example, `25.6% ±0.9` means the true win rate for this setting is almost certainly between 24.7% and 26.5%. |
| **Games played, average boxes left in wins, average plays per game** | Quick totals. |
| **Chart** | In winning games, how often 1, 2, … 9 boxes were left at the end. |
| **Details table** | Wins and losses, the range, inclusive calls used, recoveries, jokers drawn, cards left in losses, fewest and most plays, the settings and the seed. |

The **Advanced** tab has four tiles (win rate, games, wins / losses, seed) and a bar chart for every distribution: boxes left in wins, cards left in the pile in losses, plays per game, inclusive calls used, recoveries and jokers drawn per game. Each bar is a share of the games (of the wins, or of the losses), and a dashed line marks the average. The charts go two to a row in a wide window and scroll when there are more than fit. **Show as text** switches to the full report as text, and **Copy text** puts that report on the clipboard.

**Export CSV… / Export JSON…** (under the settings) save the results (see below). The progress line shows games per second while running, and the time taken and number of processes when done. **Stop** keeps the games finished so far and labels them as partial. **Clear** empties the results.

In a narrow window the four tiles go two by two and the details table gets a sideways scrollbar.

### Exports

- **CSV** opens in Excel. It is one table with three columns, `section, item, value`:
  - `settings`: jokers, inclusive calls, threshold, games, seed
  - `summary`: games, wins, losses, win rate, margin low/high, averages, min/max plays
  - one section per distribution (`boxes_left_in_wins`, `cards_left_in_losses`, `plays`, `inclusive_used`, `recoveries`, `jokers_drawn`): value → number of games
- **JSON** holds the same data in one file, plus the suite version and the export time.

### How it works inside

**The strategy** (`btb/strategy.py`), each turn:

1. If a joker is in the box, play it when no inclusive calls are left. With a failed box and a call left, spend an inclusive call on it (a guaranteed recovery). Otherwise hold it.
2. Find the box whose best plain call has the highest odds.
3. Find the box whose best inclusive call has the highest odds.
4. Spend the inclusive call only if it beats the plain call by more than the threshold.
5. Ties go to the higher recovery chance, then the more extreme card, then the higher rank, so the choice never depends on where a card sits on the board.
6. After a recovery is earned, bring back the failed box with the best next-call odds (in practice the most extreme card).

**Seeds:** game *i* of a run uses seed + *i*. That makes every run repeatable and lets the Optimizer give every configuration the same deals.

**Speed:**

- The strategy reads one odds table per turn from the engine (`odds_by_rank`) instead of recounting the pile for every box.
- Statistics are kept as tallies (how many games had 30 plays, 31 plays, …), so memory stays the same whether you run a thousand games or ten million.
- **Parallel runs:** big runs (4,000 games or more) are split into chunks of seeded games and spread over helper processes. Because every game has its own seed, the result is identical to a one-process run, and the tests check this.
- **Auto CPU cores** measures how idle the CPU is (over a fifth of a second) and how much memory is free, then uses at most 75% of your cores, always leaves one free, only counts cores that are idle right now, and allows about 150 MB per helper. Helpers run at low priority, so anything you are doing comes first.
- If helper processes can't start (or stop working), the run finishes in the main process instead of failing.

**The window never freezes.** The run happens on a background thread that reports progress through a queue, and the page checks the queue 20 times a second.

**Margin of error:** the range is a *Wilson score interval* at 95%. It stays accurate near 0% and 100%. Ten times more games makes it about three times narrower:

| Games | Typical range at a 25% win rate |
|---|---|
| 1,000 | ±2.7 points |
| 10,000 | ±0.85 points |
| 100,000 | ±0.27 points |

---

## 🔬 Strategy Optimizer

The Optimizer finds the best settings by trying every combination in a range on the same deals and ranking them.

### Settings

| Setting | Meaning |
|---|---|
| **Games per test** | Games played by each configuration. Default 1,000. |
| **Jokers, Inclusive calls, Threshold** | The ranges to try. Combinations that break the rules (more inclusive calls than cards) are skipped. |
| **Threshold step** | The gap between thresholds tried (default 5: 0, 5, 10, … 30). |
| **Seed** | As in the Simulator. Every configuration plays the same deals. |
| **Confirm top 10** | After the sweep, re-run the ten best with 5× more games on fresh deals (on by default). |
| **CPU cores** | As in the Simulator. |

A sweep is limited to 5,000 configurations, and runs of more than 2,000,000 games need a second press of Run.

### Results

The **Results** tab:

| Part | What it shows |
|---|---|
| **Tiles** | The best win rate (± range), its settings, how many configurations were tested and how many are tied, and the total games played. |
| **Table** | One row per configuration: rank, win %, ±, jokers, calls, threshold, average boxes left in wins, games. Click a heading to sort (click again to reverse). |
| **Highlighted rows** | Statistically tied for best. Their 95% ranges overlap the winner's, so the data can't tell them apart. |
| **All configurations / Confirmed top 10** | Switch between the sweep and the confirmation run. When there is a confirmation, the winner shown in the tiles is the confirmed winner. |

The **Advanced** tab has the result tiles and three charts. **Win rate by threshold** and **Win rate by inclusive calls** have one line per joker count; each point is the best configuration for that value (best over the setting not on the chart), with a whisker for its 95% range. Lines also differ by marker shape as well as colour. **Best win rate by joker count** is a bar per joker count with its 95% range. Below them, **Best configuration for each value** lists the winner for every joker count, inclusive-call count and threshold. **Show as text** gives the full report (with the top five for each value), and **Copy text** copies it.

**Use Best in Simulator** (under the settings) switches to the Simulator page with the winning jokers, calls, threshold and seed filled in, ready for a bigger run. If the Simulator is in the middle of a run, it asks you to stop that run first. **Export CSV… / JSON…** save one row per configuration.

### Exports

The CSV has one row per configuration with these columns:

`phase, rank, jokers, inclusive_calls, threshold, games, wins, win_rate, margin_low, margin_high, tied_for_best, avg_boxes_left_in_wins, avg_plays, avg_inclusive_used, avg_recoveries, seed`

`phase` is `sweep` for the main run and `confirm` for the confirmation rows. `seed` is the first seed that row played. That is the sweep seed for sweep rows, and the sweep seed plus the games per test for confirmation rows, so either can be repeated in the Simulator (with 5× the games for a confirmation row). The JSON adds the sweep settings, the best configuration, the suite version and the export time.

### How it works inside

- **Same deals for everyone.** With one seed, every configuration plays the same shuffles (seed, seed + 1, …), so any difference comes from the settings and not from the luck of the deal.
- **Confirmation** uses the next block of seeds, which are deals no configuration has seen. A configuration that only looked best by luck usually drops back.
- **Stop** keeps only configurations that finished, because a half-finished one would skew the ranking. Stopping during the confirmation drops the unfinished confirmation, so the sweep's own ranking stands.
- Sweeps use the same parallel chunks, tallies and CPU limits as the Simulator, with one pool of helpers for the whole sweep.

---

## ⌨️ Keyboard Shortcuts

On the Game Player and Game Assistant pages:

| Keys | Action |
|---|---|
| `7 8 9` / `4 5 6` / `1 2 3` | Select a box (numpad layout; the numpad works too) |
| `D` / `W` | Higher or Equal / Higher |
| `S` / `A` | Lower / Lower or Equal |
| `Ctrl+Z` | Undo |
| `Ctrl+N` | New game |
| `Ctrl+O` | Show or hide the odds (under the cards, the odds table) |
| `Ctrl+K` | Show or hide the counts (card counts, plays, cards left) |
| `Ctrl+P` | Odds table beside the board (turns the odds on) |
| `Ctrl+L` | Cards left beside the board (turns the counts on) |
| `Ctrl+R` / `Ctrl+Y` / `Ctrl+H` | How to Play / Strategy / Shortcuts pages |

Letter shortcuts work with Caps Lock on. `Ctrl+C` is left free for copying (on the help pages too).

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

To change the default, open `python/btb/theme.py` and set `DEFAULT_THEME` to a name or a number (for example `DEFAULT_THEME = 5`). A theme chosen in Settings overrides the default until the settings file is deleted.

To add a theme, copy one `Theme(...)` block in `THEMES`, give it a new name and change the colours (including `up` and `down`, the colours of the Higher and Lower call buttons). It appears in Settings automatically. The tests check every theme for readable contrast, so `python -m pytest` will tell you if a colour pair is too faint.

---

## 🧪 Tests

The tests in `python/tests/` are the executable spec, and they will be the spec for the TypeScript port too.

| File | Covers |
|---|---|
| `test_rules.py` | Every rule in docs/RULES.md |
| `test_bugs.py` | One test per bug fixed from the original v1 files |
| `test_strategy_and_sim.py` | Strategy choices, seeded batches, progress, Stop, sweeps |
| `test_speed_and_accuracy.py` | The fast strategy matches the original move for move; parallel equals single-process; margins, ties, confirmation, fallback |
| `test_export_and_system.py` | CSV and JSON exports, the CPU/memory limits, the settings file |
| `test_theme_and_look.py` | Every theme's contrast; live theme switching; banner, odds switch, cards, exports and tables |
| `test_help_and_charts.py` | The help-page markup and how it is drawn (headings, lists, tables, chips, copying, every theme); the chart data and the charts; the test set-up itself (one Tk root, cleaned after every test) |
| `test_pages_and_controls.py` | Greyed-out calls and their reasons, button order and colours, the two switches, the sidebar pages (kept state, keys only on the page showing, nothing pops up), the New Game panel, in-page messages, the Settings page, resizing, and that every page fits and settles at 960 × 620 and 1306 × 678 |
| `test_gui.py` | Keyboard, recovery on the board, the odds table and its sorting, the card picker, Simulator and Optimizer runs, background-thread safety |
| `test_docs.py` | RULES.md, STRATEGY.md, CARD_COUNTING.md and the in-app guide agree with the engine and with each other; every link (to a file or a heading) works |

From the `python` folder:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest                          # the whole suite
python -m pytest tests/test_rules.py      # one file
```

On headless Linux, run `xvfb-run python3 -m pytest` to include the window tests.

- **Use `python -m pytest`, not `pytest`.** With the Microsoft Store Python, pip puts the `pytest` command in a folder that isn't on PATH, so plain `pytest` isn't found. `python -m` always works.
- **It takes about a minute** (around 45 seconds on a recent PC). The summary lists any skipped test with its reason.
- **Small windows flash on screen** while the window tests run. That's normal. Leave them alone until the run ends.
- **A stuck test tells you where it is.** If a test runs for more than 60 seconds, pytest prints where every thread is (a traceback) so the problem can be found. Ctrl+C stops the run.
- Run it from the `python` folder, because that is where its settings file (`pytest.ini`) is. Tests never touch your real settings file.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `No module named tkinter` (Linux) | `sudo apt install python3-tk` (Debian/Ubuntu) or `sudo dnf install python3-tkinter` (Fedora). |
| `No module named 'btb'` when running tests | Run `python -m pytest` from the `python` folder, not the repo root. |
| `pytest` is not recognised (Windows) | Use `python -m pytest`. The Store Python doesn't put `pytest` on PATH. |
| The tests seem stuck | Wait for the 60-second traceback, or press Ctrl+C once, then share the traceback. Small test windows flashing up is normal. |
| The window is cut off on a small screen | The window's smallest size is 960 × 620. Below the size a page needs, side panels and tables get scrollbars. On a screen smaller than that, lower the display scaling in your system settings. |
| A run is slow | Check CPU cores is **Auto** (or set a number), and use fewer games per test in the Optimizer. The progress line shows games per second. |
| The computer feels busy during a run | Set CPU cores to a lower number. Helpers already run at low priority. |
| Settings look wrong | Delete the settings file (see [The Window, Pages and Settings](#-the-window-pages-and-settings)). |