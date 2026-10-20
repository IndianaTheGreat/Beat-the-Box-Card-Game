"""
==============================================
SIMULATOR STRATEGY POLICY
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/strategy.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

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

NOTES:
-----
- threshold: percentage points an inclusive call must add over the best
  plain call before one is spent. 0 spends one on any gain.
- Ties are broken by probability, recovery chance, the more extreme card,
  then the higher rank. Only identical ranks fall through to position.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .engine import (
    CALLS, HIGHER_EQUAL, Game, Odds, odds_from_histogram,
    rank_histogram,
)


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
        policy always plays an inclusive call on the joker: a guaranteed
        success plus a guaranteed recovery.
      * Otherwise the joker is held in reserve and only played when it is
        the last live box. Playing it early would swap a sure thing for a
        random card, and an inclusive call on it would earn a recovery that
        is lost because nothing has failed yet.
    """

    threshold: float = 5.0

    def choose_move(self, game: Game) -> Optional[Move]:
        live = game.live_positions
        if not live or not game.draw_pile or game.recovery_pending:
            return None

        jokers_in_box = [p for p in live if game.box[p].is_joker]
        if jokers_in_box:
            if game.inclusive_left > 0 and game.failed:
                return Move(jokers_in_box[0], HIGHER_EQUAL, 1.0)
            if len(jokers_in_box) == len(live):
                return Move(jokers_in_box[0], CALLS[0], 1.0)

        hist = rank_histogram(game.draw_pile)
        total = len(game.draw_pile)
        candidates = [(p, odds_from_histogram(game.box[p], hist, total))
                      for p in live if not game.box[p].is_joker]

        plain = max(_ranked(game, p, *o.best_plain(), o) for p, o in candidates)
        best = Move(plain[-1], plain[-2], plain[0])

        if game.inclusive_left > 0:
            incl = max(_ranked(game, p, *o.best_inclusive(), o, inclusive=True)
                       for p, o in candidates)
            gain = (incl[0] - best.probability) * 100
            if gain > self.threshold:
                best = Move(incl[-1], incl[-2], incl[0])
        return best

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


def _ranked(game: Game, position: int, call: str, probability: float, odds: Odds,
            inclusive: bool = False) -> tuple:
    """Sort key for a candidate move, best = largest.

    Ties are broken by what is on the board, never by where it is: first the
    recovery chance (inclusive calls with a failed box), then the more extreme
    card, then the higher rank. Only identical ranks fall through to the
    position, and those moves are equivalent. Ends with (call, position).
    """
    rank = game.box[position].rank
    recovery = odds.exact if (inclusive and game.failed) else 0.0
    return (probability, recovery, abs(rank - 8), rank, -position, call, position)


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