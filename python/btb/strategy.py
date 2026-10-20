"""
==============================================
SIMULATOR STRATEGY POLICY
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/strategy.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 218 passed)

VERSION 1.1 CHANGES (2026-10-20):
- Faster: choose_move reads one odds table per turn (engine.odds_by_rank)
  instead of rebuilding sums for every box. Same decisions and the same
  tie-breaking, checked game for game against the 1.0 code in the tests.
- Joker fix: once no inclusive calls are left, a joker in the box is
  played right away. Holding it can no longer earn a recovery, so it only
  froze a box (measured: 1 joker, 0 calls, 12.8% -> 14.8% wins).
- Default threshold raised from 5 to 10 (0 jokers, 5 calls: 18.8% ->
  25.6% wins in seeded tests).

VERSION 1.0 CHANGES (2026-10-20):
- New. Replaces SimulatedGame.find_best_move from BTBSimulator.py.
- Scores every legal move first, then ranks them, so the choice never
  depends on the order boxes are scanned in.
- Recovery decided after the flip; picks the failed box with the best
  next-call odds (the most extreme card), not max(position).
- Box joker: inclusive call when a box has failed and calls remain;
  otherwise held in reserve (beat 'always' in every seeded comparison).

DESCRIPTION:
-----------
The playing policy used by the Simulator and Optimizer. Built only on
engine odds; contains no rules of its own.

DEPENDENCIES:
------------
- btb.engine
- Standard library: dataclasses, typing

KEY FUNCTIONS:
-------------
- ThresholdPolicy(threshold).choose_move(game) -> Move or None
- ThresholdPolicy.choose_recovery(game) -> failed position to bring back
- play_out(game, policy) -> plays a game to the end
- DEFAULT_THRESHOLD -> 10 percentage points

NOTES:
-----
- threshold: percentage points an inclusive call must add over the best
  plain call before one is spent. 0 spends one on any gain. In practice
  the gain is the chance the next card ties the box card, so the
  threshold reads as "only spend a call when a tie is at least this
  likely".
- Ties are broken by probability, recovery chance, the more extreme card,
  then the higher rank. Only identical ranks fall through to position.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .engine import (
    HIGHER, HIGHER_EQUAL, LOWER, LOWER_EQUAL, Game, odds_by_rank,
    odds_from_histogram, rank_histogram,
)

DEFAULT_THRESHOLD = 10.0

# Positions in the tuples returned by engine.odds_by_rank.
_H, _L, _HE, _LE, _EXACT = range(5)


@dataclass(frozen=True)
class Move:
    position: int
    call: str
    probability: float


@dataclass(frozen=True)
class ThresholdPolicy:
    """Play the safest plain call; spend an inclusive call only when it is
    worth it.

    threshold: how many percentage points an inclusive call must add over
        the best plain call before one is spent. 0 spends one on any gain.

    Jokers in the box:
      * With a failed box to bring back and an inclusive call left, the
        policy plays an inclusive call on the joker: a guaranteed success
        plus a guaranteed recovery.
      * With inclusive calls left but nothing failed yet, the joker is held
        in reserve (it becomes a free recovery later) and is only played
        when it is the last live box.
      * With no inclusive calls left, the joker is played right away: it
        can no longer earn a recovery, so holding it just freezes a box.
    """

    threshold: float = DEFAULT_THRESHOLD

    def choose_move(self, game: Game) -> Optional[Move]:
        box = game.box
        live = [p for p, c in enumerate(box) if c is not None]
        if not live or not game.draw_pile or game.recovery_pending:
            return None

        jokers = [p for p in live if box[p].is_joker]
        if jokers:
            if game.inclusive_left <= 0:
                return Move(jokers[0], HIGHER, 1.0)
            if game.failed:
                return Move(jokers[0], HIGHER_EQUAL, 1.0)
            if len(jokers) == len(live):
                return Move(jokers[0], HIGHER, 1.0)

        table = odds_by_rank(rank_histogram(game.draw_pile), len(game.draw_pile))
        use_inclusive = game.inclusive_left > 0
        failed = bool(game.failed)

        # Sort key, best = largest: (probability, recovery chance, how extreme
        # the card is, rank, -position, call, position). Ties are broken by
        # what is on the board, never by where it is.
        best_plain = best_incl = None
        for p in live:
            rank = box[p].rank
            if rank == 0:
                continue  # jokers held in reserve
            o = table[rank]
            extreme = abs(rank - 8)
            if o[_L] > o[_H]:
                key = (o[_L], 0.0, extreme, rank, -p, LOWER, p)
            else:
                key = (o[_H], 0.0, extreme, rank, -p, HIGHER, p)
            if best_plain is None or key > best_plain:
                best_plain = key
            if use_inclusive:
                recovery = o[_EXACT] if failed else 0.0
                if o[_LE] > o[_HE]:
                    key = (o[_LE], recovery, extreme, rank, -p, LOWER_EQUAL, p)
                else:
                    key = (o[_HE], recovery, extreme, rank, -p, HIGHER_EQUAL, p)
                if best_incl is None or key > best_incl:
                    best_incl = key

        best = best_plain
        if best_incl is not None and (best_incl[0] - best_plain[0]) * 100 > self.threshold:
            best = best_incl
        return Move(best[-1], best[-2], best[0])

    def choose_recovery(self, game: Game) -> Optional[int]:
        """Bring back the failed box that is easiest to play next.

        That is the box whose card has the best plain-call odds against the
        current pile (in practice the most extreme card: a 2 or an A). Ties
        go to the more extreme rank, then the lower position.
        """
        if not game.failed:
            return None
        hist = rank_histogram(game.draw_pile)
        total = len(game.draw_pile)

        def score(position: int) -> tuple:
            card = game.failed[position]
            odds = odds_from_histogram(card, hist, total)
            best = odds.best_plain()[1] if odds else 0.0
            return (best, abs(card.rank - 8), -position)

        return max(game.failed, key=score)


def play_out(game: Game, policy: ThresholdPolicy) -> Game:
    """Play a game to the end with `policy`. Returns the same game."""
    while not game.is_over:
        if game.recovery_pending:
            game.recover(policy.choose_recovery(game))
            continue
        move = policy.choose_move(game)
        if move is None:
            break
        game.play(move.position, move.call)
    return game