<div align="center">

# 🂠 Beat the Box

**A solitaire card game of odds, nerve, and second chances, with a full toolkit for playing, simulating, and optimizing.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-2E7D32)
![Status](https://img.shields.io/badge/status-in%20development-orange)

[Rules](RULES.md) · [Getting Started](#-getting-started) · [The Suite](#-the-suite) · [Roadmap](#%EF%B8%8F-roadmap)

</div>

---

## 🎲 What is Beat the Box?

Nine cards sit face up in a 3×3 grid: **the box**. Pick a card, call whether the next card off the deck will be **higher** or **lower**, and flip.

- Call it right, and the new card takes its place.
- Call it wrong, and that box is gone.

Survive the whole deck with at least one box standing, and you **beat the box**.

You also get a few **inclusive calls** (higher-*or-equal*, lower-*or-equal*). Hit an exact match with one, and you can **bring a dead box back to life**. Add up to two **wild jokers**, and every game becomes a real puzzle of probability and timing.

```
┌─────┬─────┬─────┐
│  7♠ │  K♥ │  3♦ │      Call: 3♦ → HIGHER
├─────┼─────┼─────┤
│  9♣ │  A♠ │ ✖️  │      Flip: J♣  ✅
├─────┼─────┼─────┤
│  J♦ │  2♣ │  8♥ │      Draw pile: 31
└─────┴─────┴─────┘
```

📖 **Full rules, with examples:** [RULES.md](RULES.md)

---

## 🧰 The Suite

This repo is more than the game. It's a set of tools for understanding it.

| Tool | What it does |
|---|---|
| 🎮 **Game Player** | Play the full game with shuffled decks, live odds for every box, three card-counting methods, undo, and keyboard shortcuts. |
| 🧭 **Game Assistant** | Mirror a game you're playing with a real deck. Enter the cards as they come and get the odds and counts as you go. |
| 📊 **Simulator** | Let a strategy play thousands of games automatically and report win rate, boxes left, inclusive calls used, and more. |
| 🔬 **Strategy Optimizer** | Sweep joker counts, inclusive-call budgets, and decision thresholds to find the settings and strategy that win most often. |

All four open from one launcher (`main.py`).

---

## 🚀 Getting Started

**Requirements:** Python 3.10 or newer. Tkinter comes with the standard Python installer on Windows and macOS.

```bash
git clone https://github.com/IndianaTheGreat/Beat-the-Box-Card-Game.git
cd Beat-the-Box-Card-Game/python
python main.py
```

The suite needs nothing beyond the Python standard library.

### 🧪 Running the tests

```bash
cd python
pip install -r requirements-dev.txt
pytest
```

The tests in `python/tests/` are the executable spec: one per rule in [RULES.md](RULES.md), plus one per bug fixed from v1. GUI tests skip when no display is available; on headless Linux, run `xvfb-run pytest`.

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
| `W` / `S` | Higher / Lower |
| `D` / `A` | Higher or Equal / Lower or Equal |
| `Ctrl+Z` | Undo |
| `Ctrl+N` | New game |
| `Ctrl+P` | Show probabilities |
| `Ctrl+L` | Show remaining cards (list) |
| `Ctrl+R` / `Ctrl+Y` / `Ctrl+H` | Rules / Strategy / Shortcut help |

---

## 📁 Project Structure

```
beat-the-box/
├── README.md            ← you are here
├── RULES.md             ← the official rules (single source of truth)
└── python/              ← v1: the Python / Tkinter suite
    ├── main.py              launcher
    ├── btb/
    │   ├── engine.py        the rules engine: no GUI, used by every tool
    │   ├── strategy.py      the simulator's playing policy
    │   ├── sim.py           batch simulations and parameter sweeps
    │   ├── text.py          in-app rules, strategy guide, shortcuts
    │   ├── gui_game.py      🎮 Game Player + 🧭 Game Assistant
    │   └── gui_sim.py       📊 Simulator + 🔬 Strategy Optimizer
    ├── tests/               pytest suite (the spec for the TypeScript port)
    ├── requirements.txt
    └── requirements-dev.txt
```

Every tool plays through `btb/engine.py`, so the rules live in exactly one place. Seeded deals use a Mulberry32 shuffle that the TypeScript port can reproduce card for card.

---

## 🗺️ Roadmap

- [x] **Unified rules engine.** One shared Python module that every tool uses, so the rules live in one place.
- [x] **Bug fixes.** Joker handling, the recovery logic, undo, and the probability math, so all four tools agree with [RULES.md](RULES.md).
- [x] **A responsive optimizer.** Run it in the background, add a Stop button, and show live progress.
- [x] **Tests** covering every rule in [RULES.md](RULES.md).
- [ ] **TypeScript engine.** A port of the rules engine, checked against the same tests as the Python version.
- [ ] **Chrome extension.** Play in the browser side panel, with no install beyond the extension itself.
- [ ] **Web version** on GitHub Pages: play from a link.

---

## 🧠 Strategy Tips

- **Middle cards are the danger zone.** A `2` or an `A` is close to a sure thing, while a `7` or `8` is a coin flip. Spend inclusive calls on the middle.
- **A joker in the box is a free recovery.** Play an inclusive call on it once you have a failed box to bring back. Until then, keep it.
- **Watch the count.** A strongly positive count means low cards are due, and a negative count means high cards are.
- **Choose recoveries carefully.** Bring back the failed box with the most extreme card, since it gives the easiest next call.

---

<div align="center">

Built by **Indiana the Great** · Rules in [RULES.md](RULES.md)

</div>