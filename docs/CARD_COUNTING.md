<div align="center">

# 🧮 Beat the Box — Card Counting

**How the three counts work, what they are worth in games won, and what to do with them.**

</div>

> [!NOTE]
> The counts themselves are defined in [RULES.md](../RULES.md#-card-counting). This page explains them and reviews them with simulated games. Playing advice in general is in [STRATEGY.md](../STRATEGY.md).

---

## 📋 Contents

1. [Why Counting Works Here](#-why-counting-works-here)
2. [The Three Counts](#-the-three-counts)
3. [The Basic Count Is Exact](#-the-basic-count-is-exact)
4. [Using the Count at the Table](#-using-the-count-at-the-table)
5. [What Counting Is Worth](#-what-counting-is-worth)
6. [Is Any Count Better?](#-is-any-count-better)
7. [What the Count Can't Do: Ties](#%EF%B8%8F-what-the-count-cant-do-ties)
8. [Recommendations](#-recommendations)
9. [How the Review Was Done](#-how-the-review-was-done)

---

## 🎯 Why Counting Works Here

Every card you have seen is a card that is **not** in the draw pile. A count is a single running number that sums up what you have seen, so you can tell at a glance whether the pile is now heavy with **low** cards or **high** cards.

That matters most for **middle cards**. A `2` or an `A` in the box is a near-sure call whatever is left. A `7`, `8` or `9` is much closer to even, so the count can change which call is better: for an `8` it decides outright, and for a `7` or a `9` it has to outweigh the card's own lean (see [Using the Count at the Table](#-using-the-count-at-the-table)).

---

## 🔢 The Three Counts

Every card is counted **once**, when it first becomes visible: in the opening deal or when it is flipped. A recovered card is not counted again. Jokers count 0.

| Rank | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | J | Q | K | A | 🃏 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Method 1** — Basic | −1 | −1 | −1 | −1 | −1 | −1 | 0 | +1 | +1 | +1 | +1 | +1 | +1 | 0 |
| **Method 2** — Weighted | −2 | −2 | −2 | −1 | −1 | −1 | 0 | +1 | +1 | +1 | +2 | +2 | +2 | 0 |
| **Method 3** — Advanced | −3 | −3 | −2 | −2 | −1 | −1 | 0 | +1 | +1 | +2 | +2 | +3 | +3 | 0 |

| Count | Means | Lean |
|---|---|---|
| **Positive** | More high cards have been seen, so more **low** cards are left. | ⬇️ Lower |
| **Negative** | More low cards have been seen, so more **high** cards are left. | ⬆️ Higher |
| **Zero** | Balanced. | Go by the card itself. |

The game shows all three counts (Ctrl+O, **Show odds & counts**), each with ▼ or ▲ for the call it favours, and says when they disagree.

---

## ✅ The Basic Count Is Exact

The deck is symmetric around the `8`: 24 low cards (`2`–`7`) and 24 high cards (`9`–`A`). Because of that, the Basic count isn't an estimate:

> **Basic count = low cards left − high cards left.** Exactly, at every point in every game.

Add the number of cards in the pile (the **Draw pile** tile) and you know the split:

```
low cards left  = (cards left − jokers left − 8s left + Basic count) ÷ 2
high cards left = (cards left − jokers left − 8s left − Basic count) ÷ 2
```

**Example.** The pile has 30 cards, no jokers, two `8`s are still in it, and the Basic count is **+4**.
Low cards left = (30 − 0 − 2 + 4) ÷ 2 = **16**. High cards left = 12.
For an `8` in the box: **Lower** wins on 16 of 30 cards (53%), Higher on 12 (40%).

The Weighted and Advanced counts don't have this property: a +4 there could come from many different mixes of cards.

### How strong is the lean?

The same count means more as the pile gets smaller. +4 with 40 cards left means 4 more low cards than high among 40, a slight lean; +4 with 10 cards left is a strong one. Dividing the count by the cards left (a **"true count"**, as in blackjack) gives the strength. As a rough guide, **±0.1 is mild and ±0.3 or more is strong.**

---

## 🃏 Using the Count at the Table

1. **Extreme cards first.** A `2`–`4` or a `J`–`A` in the box is usually your best play whatever the count says: call toward the middle.
2. **An `8` follows the count exactly.** A positive Basic count means Lower is better, a negative one Higher; at zero they are equal (see the example above).
3. **A `7` or a `9` already favours one side, and the count has to overcome that.** A `7` has more cards above it than below, and a `9` more below than above: the `8`s count for the far side, and a card of the same rank loses a plain call either way.
   - **On a `7`**, Lower is better only when the Basic count is **more than the number of `7`s and `8`s still in the pile**. Otherwise call Higher.
   - **On a `9`**, Higher is better only when the Basic count is **below minus the number of `8`s and `9`s still in the pile**. Otherwise call Lower.
   - *Examples:* early on, with three `7`s and all four `8`s still to come, a `7` needs a count of **+8** before Lower is the better call. In the same way, a `9` with a count of −3 still calls Lower unless at most two `8`s and `9`s (together) are left.
4. **Weigh the lean by the pile.** Late in the game, a modest count can make a middle card the best play on the board.
5. **If the counts disagree**, trust Basic (it is the exact one), or turn on the odds. They can disagree when the extreme cards you've seen don't match the middle ones: after an A, a 7 and a 6, Basic is −1 (lean Higher) but Advanced is +1 (lean Lower), because Advanced weighs the ace three times.

---

## 📊 What Counting Is Worth

Each player below uses the same strategy as the Simulator, but decides from a different amount of information. **"No count"** knows only how many cards are left, as if every rank were equally likely. **"Exact odds"** knows every card in the pile, like the odds display. The counters work out what they can from their count and the number of cards left. *10,000 games each, seed 2026.*

| Player | No help | 1 joker, 5 calls | 2 jokers, 10 calls |
|---|:-:|:-:|:-:|
| No count | 7.2% | 15.7% | 26.8% |
| **Basic count** | **12.2%** | **27.3%** | **43.3%** |
| Weighted count | 12.3% | 26.8% | 42.8% |
| Advanced count | 12.2% | 26.6% | 42.4% |
| Exact odds | 12.9% | 38.7% | 59.5% |

*(No help = no jokers and no inclusive calls. Calls are spent with a threshold of 10. Each figure is accurate to about ±0.6–1.0 points.)*

- **With no inclusive calls, counting is almost as good as knowing every card**: 12.2% against 12.9%, up from 7.2% without a count. The count recovers nearly 90% of the gap.
- **Decision by decision**, a Basic counter makes the best available play **96% of the time**. When it doesn't, the average cost is about a quarter of a point of win chance.
- **With inclusive calls, a gap opens up**: 27% against 39%. The next sections explain why, and how to close it.

---

## 🔬 Is Any Count Better?

Besides the three counts in the game, the review tried three others:

| Count (no help, 10,000 games) | Wins | Best play made |
|---|:-:|:-:|
| **Basic** | 12.2% | 95.7% |
| Weighted | 12.3% | 95.4% |
| Advanced | 12.2% | 95.2% |
| *Hi-Lo with 7 and 9 neutral* (2–6 = −1, 10–A = +1) | 12.1% | 95.1% |
| *Linear* (each card counts its rank minus 8: 2 = −6 … A = +6) | 11.8% | 95.0% |
| *Extremes only* (2–3 = −1, K–A = +1) | 9.7% | 88.4% |

**Verdict:** the three counts in the game are equally good; the differences are smaller than the margin of error. Weighting the extreme cards more (Weighted, Advanced, Linear) doesn't help, because the decisions a count actually changes are the middle cards, and for those what matters is simply how many cards are above or below. Counting only the extremes throws away too much.

**Basic is the one to learn.** It is the easiest to keep in your head, it is exact (see above), and nothing tested beats it. The other two can stay in the game as a cross-check; there is no case for changing the counts in RULES.md.

---

## ⚖️ What the Count Can't Do: Ties

An inclusive call is worth spending when a **tie** is likely: when many cards of the box card's rank are still in the pile. A count only says "more low" or "more high". It can't tell you that three `8`s are still to come, so a counter spends inclusive calls at the wrong moments.

The fix is a second, small habit: **for each rank in your box, keep track of how many of that rank you have seen** (at most 4 per rank). The review gave the Basic counter that extra knowledge:

| Player | 1 joker, 5 calls | 2 jokers, 10 calls |
|---|:-:|:-:|
| Basic count | 27.3% | 43.3% |
| **Basic count + ranks in your box** | **37.0%** | **57.8%** |
| Exact odds | 38.7% | 59.5% |
| *(No count + ranks in your box)* | *26.7%* | *47.5%* |

**Counting plus tracking your box's ranks gets within 2 points of playing with the exact odds** (the Simulator's strategy when it knows every card). Each habit helps on its own, but together they are far stronger than either alone.

With no inclusive calls, tracking ranks adds nothing measurable (11.7% against 12.2%, inside the margin of error). A same-rank card still loses a plain call, but the count alone already picks the right plain call almost every time. Knowing the ties pays off when it tells you **when to spend an inclusive call**.

---

## 📌 Recommendations

1. **Keep the Basic count.** It is exact, easy, and as good as anything tested.
2. **Use it on middle cards**, weighed by how many cards are left.
3. **If you have inclusive calls, also track how many of each box rank are gone.** That is where the remaining wins are.
4. **Treat Weighted and Advanced as optional.** They agree with Basic almost always and don't add wins.

### Ideas for the app (not built yet)

- **A "ties left" figure under each card** (how many of that rank remain) as part of Show odds & counts. It is exactly the information that closes the gap above.
- **A "play by the count" option in the Simulator**, so you can test counting habits yourself with any settings.

---

## 🧪 How the Review Was Done

- **Games:** 10,000 per row, deals seeded from 2026, with the Simulator's strategy (suite version 1.2.0) and a threshold of 10.
- **Counters:** each one turns its count into an estimated pile. It assumes every rank was seen about equally often, then shifts the estimate in proportion to each rank's weight in the count so it matches the count exactly. For Basic this closely matches the exact low/high split above (the count can't see the `8`s, so those are estimated). The strategy then plays from the estimated odds instead of the exact ones.
- **"Ranks in your box":** the same, except that for every rank currently in the box the counter uses the true number left.
- **"Best play made":** at every turn of the no-help games, whether the counter's chosen box and call had the same chance of winning as the best play available.
- **Margins:** with 10,000 games a win rate is accurate to about ±0.6 points near 12% and ±1.0 near 40–60%.

This review uses the engine's own odds formula (`odds_by_rank`) on the estimated piles. The study code isn't part of the app; the "play by the count" idea above would make it repeatable from the Simulator.

<div align="center">

*Count low, count high, and watch your ties.* 🂠

</div>