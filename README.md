<div align="center">

# 🂠 Beat the Box

**A solitaire card game about odds and second chances, with tools for playing, simulating and optimizing it.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-2E7D32)
![Status](https://img.shields.io/badge/status-in%20development-orange)

[Rules](docs/RULES.md) · [Strategy](docs/STRATEGY.md) · [Tool Guide](docs/GUIDE.md) · [Getting Started](#-getting-started) · [The Suite](#-the-suite) · [Roadmap](#%EF%B8%8F-roadmap)

</div>

---

## 🎲 What is Beat the Box?

Nine cards sit face up in a 3×3 grid, and that grid is the box. Pick a card, call whether the next card off the deck will be higher or lower, and flip.

- Call it right, and the new card takes its place.
- Call it wrong, and that box is gone.

Get through the whole deck with at least one box standing and you beat the box.

You also get a few inclusive calls (higher-*or-equal*, lower-*or-equal*). If one hits an exact match, you can bring a dead box back. You can add up to two wild jokers as well, and then each game comes down to odds and timing.

```
┌─────┬─────┬─────┐
│  7♠ │  K♥ │  3♦ │      Call: 3♦ → HIGHER
├─────┼─────┼─────┤
│  9♣ │  A♠ │ ✖️  │      Flip: J♣  ✅
├─────┼─────┼─────┤
│  J♦ │  2♣ │  8♥ │      Draw pile: 31
└─────┴─────┴─────┘
```

📖 **Full rules, with examples:** [docs/RULES.md](docs/RULES.md)<br>
🧠 **How to play well, with simulated win rates:** [docs/STRATEGY.md](docs/STRATEGY.md)<br>
🧰 **What each tool does and how it works:** [docs/GUIDE.md](docs/GUIDE.md)<br>
🧮 **The card counts explained and reviewed:** [docs/CARD_COUNTING.md](docs/CARD_COUNTING.md)

---

## 🧰 The Suite

Besides the game itself, this repo has tools for studying it.

| Tool | What it does |
|---|---|
| 🎮 **Game Player** | Play the full game with shuffled decks. A big banner shows each call and its result. **Show odds** puts the chances under each card and gives a sortable odds table; **Show counts** shows three card counts with a plain "lean" reading, a play history and the cards left. Calls that can't help (Lower on a `2`, Higher on an `A`) are greyed out. Undo and keyboard shortcuts throughout. |
| 🧭 **Game Assistant** | Mirror a game you're playing with a real deck. Click the cards as they come and get exact odds and counts as you go. |
| 📊 **Simulator** | Let the strategy play thousands of games and report the win rate with its margin of error, with a chart for every distribution (boxes left, cards left, plays, inclusive calls, recoveries, jokers). Export to CSV or JSON. |
| 🔬 **Strategy Optimizer** | Sweep joker counts, inclusive-call budgets, and thresholds on the same deals, chart the win rate against each, see which results are statistically tied, confirm the top ten, and export the table. |

All four live in one window (`main.py`). A sidebar switches between them, the help pages and Settings, and each page keeps its place while you look at another. Nothing pops up. The pages resize with the window (down to 960 × 620, with scrollbars where something doesn't fit), the help pages are laid out like a formatted document, and there are eight colour themes. Big runs use several CPU cores after checking which ones are free. [docs/GUIDE.md](docs/GUIDE.md) explains every page in detail.

---

## 🚀 Getting Started

**Requirements:** Python 3.10 or newer. Tkinter comes with the standard Python installer on Windows and macOS (including the Microsoft Store Python).

```powershell
git clone https://github.com/IndianaTheGreat/Beat-the-Box-Card-Game.git
cd Beat-the-Box-Card-Game/python
python main.py
```

The suite needs nothing beyond the Python standard library. The commands here use `python`, which works with the Microsoft Store Python (it has no `py` launcher). On macOS and Linux it may be `python3`.

### 🧪 Running the tests

From the `python` folder:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest                          # the whole suite, about a minute
python -m pytest tests/test_rules.py      # one file
```

Use `python -m pytest` rather than `pytest`, because with the Store Python `pytest` isn't on PATH. Small windows flash on screen while the window tests run. That's normal. Skipped tests are listed with their reason, and a test stuck for more than 60 seconds prints a traceback of where it is.

The tests in `python/tests/` are the executable spec. There is one per rule in [docs/RULES.md](docs/RULES.md) and one per bug fixed from v1, plus checks that the fast simulator matches the original, that parallel runs match single-process runs, that every theme is readable, and that the docs agree with the engine. GUI tests skip when no display is available. On headless Linux, run `xvfb-run python3 -m pytest`. The tests never touch your real settings.

<details>
<summary><b>Linux: Tkinter not found?</b></summary>

Some Linux distributions ship Python without Tkinter. Install it with your package manager:

```bash
sudo apt install python3-tk      # Debian / Ubuntu
sudo dnf install python3-tkinter # Fedora
```

</details>

### ⌨️ Game Player shortcuts

| Keys | Action |
|---|---|
| `7 8 9` / `4 5 6` / `1 2 3` | Select a box (laid out like a numpad) |
| `D` / `W` | Higher or Equal / Higher |
| `S` / `A` | Lower / Lower or Equal |
| `Ctrl+Z` | Undo |
| `Ctrl+N` | New game |
| `Ctrl+O` | Show or hide the odds (under the cards, the odds table) |
| `Ctrl+K` | Show or hide the counts (card counts, plays, cards left) |
| `Ctrl+P` | Odds table beside the board (turns the odds on) |
| `Ctrl+L` | Cards left beside the board (turns the counts on) |
| `Ctrl+R` / `Ctrl+Y` / `Ctrl+H` | How to Play / Strategy / Shortcuts pages |

---

## 📁 Project Structure

```
Beat-the-Box-Card-Game/
├── README.md            ← you are here
├── docs/
│   ├── RULES.md         ← the official rules (single source of truth)
│   ├── STRATEGY.md      ← how to play well, with simulated win rates
│   ├── GUIDE.md         ← what each tool does and how it works
│   └── CARD_COUNTING.md ← the card counts explained, with a review of how well they work
└── python/              ← the Python / Tkinter suite
    ├── main.py              starts the app
    ├── btb/
    │   ├── app.py           the one window: sidebar, Home, help pages, Settings
    │   ├── engine.py        the rules engine: no GUI, used by every tool
    │   ├── strategy.py      the simulator's playing policy
    │   ├── sim.py           batches, sweeps, margins of error, parallel runs
    │   ├── system.py        CPU / memory scan that sizes parallel runs
    │   ├── export.py        CSV and JSON exports
    │   ├── text.py          in-app rules, strategy guide, tool help, shortcuts
    │   ├── markup.py        reads the light Markdown the help text is written in
    │   ├── settings.py      remembered settings (theme, odds, counts, CPU cores)
    │   ├── theme.py         the eight colour themes, fonts, styling
    │   ├── widgets.py       drawn cards, stat tiles, charts, help pages, card picker
    │   ├── gui_game.py      🎮 Game Player + 🧭 Game Assistant
    │   └── gui_sim.py       📊 Simulator + 🔬 Strategy Optimizer
    ├── tests/               pytest suite (the spec for the TypeScript port)
    ├── archive/             the original v1 files, kept for the record (not maintained)
    ├── requirements.txt
    └── requirements-dev.txt
```

Every tool plays through `btb/engine.py`, so the rules live in one place. Seeded deals use a Mulberry32 shuffle that the TypeScript port can reproduce card for card.

---

## 🗺️ Roadmap

- [x] **Unified rules engine.** One shared Python module that every tool uses, so the rules live in one place.
- [x] **Bug fixes.** Joker handling, the recovery logic, undo, and the probability math, so all four tools agree with [RULES.md](docs/RULES.md).
- [x] **A responsive optimizer.** Run it in the background, add a Stop button, and show live progress.
- [x] **Tests** covering every rule in [RULES.md](docs/RULES.md).
- [x] **Modern look and docs.** Drawn cards, a result banner, eight themes, a faster and more accurate simulator with exports, and the [strategy](docs/STRATEGY.md) and [tool](docs/GUIDE.md) guides.
- [x] **One window.** A sidebar instead of pop-ups, a board that resizes, call buttons paired by direction with dead calls greyed out, and a [card-counting guide](docs/CARD_COUNTING.md).
- [x] **Polish.** Separate odds and counts switches, a sortable odds table, help pages that read like a document, charts in the Advanced tabs, and the docs gathered in `docs/`.
- [x] **Play-testing fixes.** A recovered box comes back with the card that beat it, a big and a little joker, a Cards view of what's left in the pile, and the fix for the window (and the test run) freezing on Windows when the Assistant's card grid kept resizing itself.
- [ ] **TypeScript engine.** A port of the rules engine, checked against the same tests as the Python version.
- [ ] **Chrome extension.** Play in the browser side panel, with no install beyond the extension itself.

---

## 🧠 Strategy Tips

- **Middle cards are the risky ones.** A `2` or an `A` is close to a sure thing. An `8` wins only about 47% either way (a tie loses), and a `7` or a `9` starts at about 55% for its better call.
- **Save inclusive calls.** Early on they add only about 6 points (the chance of a tie). Spend them when a tie is likely.
- **A joker in the box is a free recovery.** Play an inclusive call on it once you have a failed box to bring back. If you have no inclusive calls left, play it right away.
- **Watch the count.** A strongly positive count means low cards are due, and a negative count means high cards are. The Basic count is exact (see [CARD_COUNTING.md](docs/CARD_COUNTING.md)). **Show counts** (Ctrl+K) shows it without the odds, for practice.
- **Choose recoveries carefully.** Bring back the failed box with the most extreme card. It gives the easiest next call.

There's more, with the numbers behind it, in [STRATEGY.md](docs/STRATEGY.md).

---

<div align="center">

Built by **Indiana the Great** · Rules in [RULES.md](docs/RULES.md)

</div>