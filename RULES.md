<div align="center">

# 🂠 Beat the Box — Official Rules

**A solitaire card game of odds, nerve, and second chances.**

`♠` `♥` `♦` `♣` `🃏`

</div>

> [!NOTE]
> This file is the **single source of truth** for the rules. Every part of the project — the Python suite, the TypeScript engine, the Chrome extension, and the simulator — must play exactly as described here. If the code and this file disagree, the code has a bug.

---

## 📋 Contents

1. [The Goal](#-the-goal)
2. [Setup](#-setup)
3. [Card Ranks](#-card-ranks)
4. [Taking a Turn](#-taking-a-turn)
5. [Inclusive Calls](#-inclusive-calls)
6. [Jokers](#-jokers)
7. [Recovering a Failed Box](#-recovering-a-failed-box)
8. [Winning & Losing](#-winning--losing)
9. [Game Settings](#%EF%B8%8F-game-settings)
10. [Card Counting](#-card-counting)
11. [Worked Examples](#-worked-examples)
12. [Quick Reference](#-quick-reference)

---

## 🎯 The Goal

Get through the **entire draw pile** with **at least one box still alive**.

---

## 🃏 Setup

1. Shuffle a standard **52-card deck**, plus **0, 1, or 2 jokers** (your choice).
2. Deal **9 cards face up** in a 3×3 grid. This is **the box**.
3. The remaining cards form the **draw pile** (43 cards, or 44–45 with jokers).

```
┌─────┬─────┬─────┐
│  7♠ │  K♥ │  3♦ │
├─────┼─────┼─────┤
│  9♣ │  A♠ │  5♥ │      Draw pile: 43 cards
├─────┼─────┼─────┤
│  J♦ │  2♣ │  8♥ │
└─────┴─────┴─────┘
```

---

## 🔢 Card Ranks

Aces are **high**. Suits **do not matter**.

| Low → | | | | | | | | | | | | → High |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **2** | **3** | **4** | **5** | **6** | **7** | **8** | **9** | **10** | **J** | **Q** | **K** | **A** |

Jokers have no rank. They are wild (see [Jokers](#-jokers)).

---

## 🔄 Taking a Turn

1. **Pick** any live box.
2. **Call** what the next card from the draw pile will be compared to that box's card:

| Call | Wins when the drawn card is… | Cost |
|---|---|---|
| ⬆️ **Higher** | strictly higher | free |
| ⬇️ **Lower** | strictly lower | free |
| ⏫ **Higher or Equal** | higher **or the same rank** | 1 inclusive call |
| ⏬ **Lower or Equal** | lower **or the same rank** | 1 inclusive call |

3. **Flip** the top card of the draw pile.

| Result | What happens |
|---|---|
| ✅ **Correct** | The drawn card is placed on the box, replacing the old card. Play on. |
| ❌ **Wrong** | The box **fails**. It can't be played again unless it is [recovered](#-recovering-a-failed-box). |

> [!IMPORTANT]
> On a plain **Higher** or **Lower** call, a card of the **same rank is a loss**. An `8` drawn on an `8` after calling Higher fails the box.

---

## ⚖️ Inclusive Calls

Inclusive calls — **Higher or Equal** and **Lower or Equal** — are your limited safety net.

- You start the game with a set number of them (see [Game Settings](#%EF%B8%8F-game-settings)).
- Each one is spent **when you make the call**, win or lose.
- They make a tie count as a win.
- **🎁 Bonus:** if the drawn card is an **exact rank match** for the box card, you also earn **one recovery**.

---

## 🃏 Jokers

Jokers are wild. **Any play involving a joker succeeds**, whether the joker is drawn or is sitting in the box.

| Situation | Plain call (Higher / Lower) | Inclusive call |
|---|:-:|:-:|
| 🃏 **Joker is drawn** | ✅ Success | ✅ Success **+ 🎁 recovery** |
| 🃏 **Joker is in the box** | ✅ Success | ✅ Success **+ 🎁 recovery** |

A joker counts as an **exact match for any card**. That's why an inclusive call on a joker always earns a recovery.

> [!TIP]
> A joker sitting in the box is a **guaranteed recovery** if you spend an inclusive call on it. Strong players save inclusive calls for exactly this.

When a drawn joker wins, it is placed on the box like any other card. The next play on that box is then a guaranteed success too.

---

## ♻️ Recovering a Failed Box

When you earn a recovery:

1. The play resolves first. You see the drawn card and it lands on the box.
2. **Then** you choose **one** failed box to bring back.
3. The recovered box returns with **the card it failed on**.
4. You may also skip the recovery.

| Rule | Detail |
|---|---|
| 🔢 **One per match** | Each exact match or joker earns exactly one recovery. |
| 🚫 **No banking** | If you have **no failed boxes** when you earn a recovery, it is **lost**. Recoveries can't be saved for later. |
| 👁️ **Show failed cards** | If this setting is on, each failed box shows the card it failed on, so you can pick the best one to bring back. A box holding a `2` or an `A` is the easiest to play next. |

---

## 🏆 Winning & Losing

| | Condition |
|---|---|
| 🏆 **Win** | The draw pile runs out **and at least one box is still alive**. |
| 💀 **Lose** | **All nine boxes fail.** |

The more boxes still alive at the end, the cleaner the win. The simulator tracks this as **boxes left**.

---

## ⚙️ Game Settings

| Setting | Options | Notes |
|---|---|---|
| **Jokers** | `0`, `1`, `2` | Added to the deck before shuffling. |
| **Inclusive calls** | `0` up to `43 + jokers` | The maximum equals the size of the draw pile, enough for every flip. |
| **Show failed cards** | `Yes` / `No` | Whether failed boxes reveal their card when you choose a recovery. |

---

## 🧮 Card Counting

The game shows three running counts to help you judge what's left in the draw pile. Every card is counted **once**, when it first becomes visible: either in the opening deal or when it is drawn.

| Rank | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | J | Q | K | A | 🃏 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Method 1** — Basic | −1 | −1 | −1 | −1 | −1 | −1 | 0 | +1 | +1 | +1 | +1 | +1 | +1 | 0 |
| **Method 2** — Weighted | −2 | −2 | −2 | −1 | −1 | −1 | 0 | +1 | +1 | +1 | +2 | +2 | +2 | 0 |
| **Method 3** — Advanced | −3 | −3 | −2 | −2 | −1 | −1 | 0 | +1 | +1 | +2 | +2 | +3 | +3 | 0 |

- A **positive** count means many high cards have been seen, so **more low cards remain**. Lean **Lower**.
- A **negative** count means **more high cards remain**. Lean **Higher**.
- A **recovered** card is **not** counted again. It was already counted when it first appeared.

---

## 📖 Worked Examples

<details>
<summary><b>Example 1 — A plain call</b></summary>

Box has a `4♣`. You call **Higher**. The draw is `J♥`.
✅ Correct. The `J♥` now sits on that box.

</details>

<details>
<summary><b>Example 2 — A tie on a plain call</b></summary>

Box has an `8♦`. You call **Lower**. The draw is `8♠`.
❌ Same rank on a plain call is a loss. The box fails, holding the `8♦`.

</details>

<details>
<summary><b>Example 3 — Inclusive exact match → recovery</b></summary>

You have one failed box, holding a `K♠`. Another box has a `7♥`. You spend an inclusive call: **Lower or Equal**. The draw is `7♣`.
✅ Correct, and an exact match. The `7♣` lands on the box. 🎁 You recover the failed box, and it comes back as `K♠`. Your next call on it is an easy **Lower**.

</details>

<details>
<summary><b>Example 4 — Joker in the box</b></summary>

A `🃏` is sitting in the box. You spend an inclusive call on it. The draw is `5♦`.
✅ Guaranteed success. The `5♦` replaces the joker. 🎁 You earn a recovery.

</details>

<details>
<summary><b>Example 5 — Recovery with nothing to recover</b></summary>

No boxes have failed yet. You make an inclusive call and draw an exact match.
✅ Correct. The recovery is **lost**, because there's nothing to bring back and recoveries can't be saved.

</details>

---

## ⚡ Quick Reference

```
CALL            WINS ON          COST       BONUS
Higher          >                free       —
Lower           <                free       —
Higher/Equal    ≥                1 incl.    exact match → recovery
Lower/Equal     ≤                1 incl.    exact match → recovery

JOKER (drawn or in the box)   always wins   inclusive call → recovery
RECOVERY                      pick after the flip · one box · no banking
WIN                           pile empty + ≥1 live box
LOSE                          all 9 boxes failed
```

<div align="center">

*Good luck — and beat the box.* 🂠

</div>
