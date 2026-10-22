<div align="center">

# 🧠 Beat the Box: Strategy Guide

**How to give yourself the best odds, with numbers from thousands of simulated games.**

`♠` `♥` `♦` `♣` `🃏`

</div>

> [!NOTE]
> The rules are in [RULES.md](RULES.md), and this guide assumes you know them. The in-app **Strategy Guide** (Ctrl+Y) is a short version of this page, with the same section names. Every number below can be reproduced in the Simulator (see [How These Numbers Were Made](#-how-these-numbers-were-made)).

---

## 📋 Contents

1. [Rules of Thumb](#-rules-of-thumb)
2. [Card Counting](#-card-counting)
3. [Reading the Count](#-reading-the-count)
4. [Inclusive Calls](#%EF%B8%8F-inclusive-calls)
5. [Jokers](#-jokers)
6. [Recoveries](#%EF%B8%8F-recoveries)
7. [Using the Odds](#-using-the-odds)
8. [What the Simulator Found](#-what-the-simulator-found)
9. [How These Numbers Were Made](#-how-these-numbers-were-made)

---

## ⚡ Rules of Thumb

1. **Play the box with the best odds.** A `2` or an `A` is close to a sure thing. An `8` wins only about 47% either way, because a tie loses. A `7` or a `9` starts at about 55% for its better call, and the count tells you how that changes.
2. **Save inclusive calls.** Early in the game they add only about 6 percentage points. Spend them when a tie is likely.
3. **Hold a joker in the box while you still have inclusive calls**, and spend one on it as soon as a box has failed. That gets you a guaranteed recovery.
4. **No inclusive calls left? Play the joker right away.** It can't earn a recovery any more.
5. **Recover the most extreme card** (a `2` or an `A`). It gives the easiest next call.

---

## 🧮 Card Counting

The game keeps three running counts. Every card is counted once, when it first becomes visible in the opening deal or when it is flipped. A recovered card is not counted again.

| Rank | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | J | Q | K | A | 🃏 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Method 1:** Basic | −1 | −1 | −1 | −1 | −1 | −1 | 0 | +1 | +1 | +1 | +1 | +1 | +1 | 0 |
| **Method 2:** Weighted | −2 | −2 | −2 | −1 | −1 | −1 | 0 | +1 | +1 | +1 | +2 | +2 | +2 | 0 |
| **Method 3:** Advanced | −3 | −3 | −2 | −2 | −1 | −1 | 0 | +1 | +1 | +2 | +2 | +3 | +3 | 0 |

The Basic count is easy to keep in your head with a real deck. The Weighted and Advanced counts give the extreme cards more weight, so they track the pile more closely.

---

## 📈 Reading the Count

| Count | What it means | Lean |
|---|---|---|
| **Positive** | Many high cards have already been seen, so more low cards remain in the pile. | ⬇️ **Lower** |
| **Negative** | Many low cards have already been seen, so more high cards remain. | ⬆️ **Higher** |
| **Zero** | The pile is balanced. | Go by the card itself. |

- The bigger the number, the stronger the lean.
- The count matters most for middle cards (`7`, `8`, `9`). A `2` or an `A` is a near-sure call whatever the count says.
- The Game Player shows all three counts (switch on **Show counts**, Ctrl+K), each with ▼ or ▲ for the call it favours, and spells out the lean ("More LOW cards left: lean Lower").
- **The counts can disagree.** After seeing an A, a 7 and a 6, the Basic count is −1 (lean Higher) but the Advanced count is +1 (lean Lower), because the Advanced count weighs the ace more. The Player then says "The counts disagree". Go with the Basic count, which is exact ([why](CARD_COUNTING.md#-the-basic-count-is-exact)), or the odds under the cards.
- **Learn Basic.** A review of the three counts (and three others) found none that wins more, and Basic is the simplest. See [CARD_COUNTING.md](CARD_COUNTING.md).

---

## ⚖️ Inclusive Calls

An inclusive call (Higher or Equal, Lower or Equal) adds one thing to a plain call, which is the chance that the next card ties the box card.

At the start of a game that chance is small. For any box card, 3 of the other 51 cards share its rank:

| Box card | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | J | Q | K | A |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Best plain call** | ⬆️ | ⬆️ | ⬆️ | ⬆️ | ⬆️ | ⬆️ | either | ⬇️ | ⬇️ | ⬇️ | ⬇️ | ⬇️ | ⬇️ |
| **Wins** | 94.1% | 86.3% | 78.4% | 70.6% | 62.7% | 54.9% | 47.1% | 54.9% | 62.7% | 70.6% | 78.4% | 86.3% | 94.1% |
| **Inclusive adds** | +5.9 | +5.9 | +5.9 | +5.9 | +5.9 | +5.9 | +5.9 | +5.9 | +5.9 | +5.9 | +5.9 | +5.9 | +5.9 |

*(A full 52-card deck with no jokers, before any card is drawn.)*

So an inclusive call spent early buys you about 6 points. Later in the game, when one rank is crowded in a small pile, a tie can be 15 to 25% likely, and the same call is worth three or four times as much. Save them for those moments.

The Simulator's threshold puts a number on this. The strategy spends an inclusive call only when it adds more than that many points over the best plain call. Measured on 5,000 games per setting:

| Inclusive calls | Best threshold | Why |
|---|---|---|
| 1 to 3 | **10 to 15** (up to 20 with 2 jokers) | With very few calls, keep them for big ties and joker recoveries. |
| 5 to 10 | **10** | The best all-rounder. |
| 15 to 30 | **about 5** | With plenty of calls, spend them more freely. (0 or 10 occasionally edges it, within the margin of error.) |
| One per card (43+) | **0** | Spend one on every flip where a tie is possible. Unused calls are wasted. |

A bad threshold costs a lot. With no jokers and 5 inclusive calls:

| Threshold | 0 | 5 | **10** | 15 | 20 | 25 | 30 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Win rate** | 16.0% | 17.0% | **27.2%** | 21.5% | 17.5% | 15.4% | 15.1% |

At a low threshold the calls are gone within the first few flips. At a high one they are never used at all.

---

## 🃏 Jokers

A joker in the box wins any call. An inclusive call on it also earns a recovery, because a joker is an exact match for any card.

- **While you still have inclusive calls:** hold the joker. As soon as a box has failed, spend an inclusive call on it for a guaranteed success and a guaranteed recovery.
- **With no inclusive calls left:** play the joker right away. It can no longer earn a recovery, so holding it only freezes one of your boxes. In development testing (2,000 games, no inclusive calls), the old strategy held it and did *worse* with a joker than without one (12.8% vs 13.9%). Playing it right away fixes that. In the tables below, one joker wins 14.5% and two win 17.6%, against 13.1% with none.
- **A drawn joker** wins whatever you called. If you used an inclusive call, it also earns a recovery.

Jokers are worth more the more inclusive calls you have, because each one is a guaranteed recovery waiting for a call:

| Inclusive calls | 0 jokers | 1 joker | 2 jokers |
|---|:-:|:-:|:-:|
| 0 | 13.1% | 14.5% | 17.6% |
| 5 | 27.2% | 39.7% | 53.3% |
| 10 | 31.2% | 46.3% | 62.1% |

---

## ♻️ Recoveries

- **Pick the most extreme card.** A recovered box comes back with the card that beat it (the drawn card on top of its stack). A `2` or an `A` gives a 94% next call; a `7` gives about 55% and an `8` about 47%.
- **Recoveries can't be saved.** One earned while nothing has failed is lost, which is one more reason to hold inclusive calls until something has failed.
- **Turn on "Show failed cards"** (in the New Game settings) so you can see which card each failed box would come back with.

---

## 🔍 Using the Odds

- **Ctrl+O** (**Show odds**) shows the odds for Higher (▲) and Lower (▼) under every card. **Ctrl+P** shows the full table beside the board, including inclusive calls and the tie (recovery) chance, with the best chance at the top.
- **Ctrl+K** (**Show counts**) shows the three card counts and your plays; **Ctrl+L** shows how many of each rank are left. The two switches are separate, so you can practise counting with the odds hidden.
- **Pick the box whose best plain call has the highest odds.** Ties between boxes go to the more extreme card.
- **The count gives you a quick estimate of the same thing** when the odds are hidden, or when you play with a real deck and keep the count in your head. Without inclusive calls it gets you almost all the way.
- **With inclusive calls, also track how many of each box rank are left.** The count can't see ties coming, but this habit can. [CARD_COUNTING.md](CARD_COUNTING.md#%EF%B8%8F-what-the-count-cant-do-ties) shows what each habit is worth.
- The **Game Assistant** gives exact odds for a real-deck game, because it knows every card you have entered.

---

## 📊 What the Simulator Found

Best win rate for each setting, and the threshold that achieved it. Each cell is 5,000 games (accurate to about ±1.3 points).

| Inclusive calls | 0 jokers | 1 joker | 2 jokers |
|---|:-:|:-:|:-:|
| 0 | 13.1% | 14.5% | 17.6% |
| 1 | 16.1% *(15)* | 25.6% *(15)* | 29.8% *(20)* |
| 3 | 21.8% *(10)* | 33.1% *(15)* | 46.8% *(15)* |
| 5 | 27.2% *(10)* | 39.7% *(10)* | 53.3% *(10)* |
| 10 | 31.2% *(10)* | 46.3% *(10)* | 62.1% *(10)* |
| 15 | 36.6% *(5)* | 49.6% *(5)* | 62.4% *(10)* |
| 20 | 50.9% *(5)* | 66.1% *(5)* | 77.7% *(5)* |
| 30 | 63.8% *(5)* | 79.2% *(0)* | 87.7% *(5)* |
| One per card | 69.0% *(0)* | 84.1% *(0)* | 91.5% *(0)* |

*(Threshold in brackets. "One per card" is 43 calls with no jokers, 44 with one, 45 with two.)*

The main results:

- **Even with no help at all, you beat the box about 1 game in 8.**
- **Each joker adds roughly 10 to 15 points** once you have a few inclusive calls to spend on it.
- **The first 5 calls are worth the most** when spent carefully: 13% → 27% with no jokers.
- **Winning games usually end with 2 to 4 boxes left**; with lots of calls and jokers, closer to 5 or 6.

---

## 🔬 How These Numbers Were Made

Every win rate in this guide comes from the built-in strategy (`python/btb/strategy.py`, suite version 1.4.0) playing 5,000 games per setting with seed 2026. To reproduce any cell, open the **Simulator** and enter:

| Setting | Value |
|---|---|
| Number of games | 5000 |
| Jokers / Inclusive calls / Threshold | from the table |
| Seed | 2026 |

The Simulator plays the same 5,000 deals and gives the same result, card for card. The **Strategy Optimizer** with games per test 5000 and seed 2026 reproduces a whole table at once, because every configuration in a sweep plays the same deals.

The ± figures are 95% ranges. The true win rate for that setting is almost certainly within that many points of the number shown. Two settings whose ranges overlap may be equally good. The Optimizer marks these as tied and can confirm the top ten on fresh deals.

The tool guide, [GUIDE.md](GUIDE.md), explains how the Simulator and Optimizer work inside.

<div align="center">

*Good luck, and beat the box.* 🂠

</div>