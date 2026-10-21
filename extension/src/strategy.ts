/*
==============================================
SIMULATOR STRATEGY POLICY (TYPESCRIPT)
==============================================
File Location: Beat-the-Box-Card-Game/extension/src/strategy.ts
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (node --test: 80 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. A port of python/btb/strategy.py 1.1: the same choices and the
  same tie-breaking, checked move for move against the Python traces in
  shared/test_vectors.json.

DESCRIPTION:
-----------
The playing policy the Simulator and Optimizer use. Built only on the
engine's odds; it has no rules of its own.

DEPENDENCIES:
------------
- ./engine.ts

KEY FUNCTIONS:
-------------
- new ThresholdPolicy(threshold).chooseMove(game) -> Move or null
- policy.chooseRecovery(game) -> the failed box to bring back, or null
- playOut(game, policy) -> plays a game to the end
- DEFAULT_THRESHOLD -> 10 percentage points

NOTES:
-----
- threshold: percentage points an inclusive call must add over the best
  plain call before one is spent. 0 spends one on any gain. In practice
  the gain is the chance the next card ties the box card.
- Ties are broken by chance, recovery chance, the more extreme card, then
  the higher rank. Only identical ranks fall through to position.
- Jokers in the box: played with an inclusive call when a box has failed
  and calls remain; held in reserve while nothing has failed; played at
  once when no inclusive calls are left (holding it then only freezes a
  box).
*/

import {
  Game, HIGHER, HIGHER_EQUAL, LOWER, LOWER_EQUAL, oddsByRank, oddsFromHistogram,
  rankHistogram,
} from "./engine.ts";
import type { Call } from "./engine.ts";

export const DEFAULT_THRESHOLD = 10;

export interface Move {
  readonly position: number;
  readonly call: Call;
  readonly probability: number;
}

// Positions in the tuples from oddsByRank.
const H = 0, L = 1, HE = 2, LE = 3, EXACT = 4;

/** A possible move and its sort key, best = largest: [chance, recovery
 * chance, how extreme the card is, rank, -position]. Python's key also ends
 * with the call and position, but -position already differs between any
 * two boxes, so those never decide anything. */
interface Candidate {
  readonly key: readonly number[];
  readonly position: number;
  readonly call: Call;
}

/** Python's tuple comparison: the first place they differ decides. */
function greater(a: readonly number[], b: readonly number[]): boolean {
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== b[i]) return a[i]! > b[i]!;
  }
  return false;
}

function candidate(chance: number, recovery: number, extreme: number, rank: number,
  position: number, call: Call): Candidate {
  return { key: [chance, recovery, extreme, rank, -position], position, call };
}

/** Play the safest plain call; spend an inclusive call only when it adds
 * more than `threshold` percentage points. */
export class ThresholdPolicy {
  readonly threshold: number;

  constructor(threshold: number = DEFAULT_THRESHOLD) {
    this.threshold = threshold;
  }

  chooseMove(game: Game): Move | null {
    const box = game.box;
    const live = game.livePositions;
    if (live.length === 0 || game.drawPile.length === 0 || game.recoveryPending) return null;

    const jokers = live.filter((p) => box[p]!.isJoker);
    if (jokers.length > 0) {
      if (game.inclusiveLeft <= 0) return { position: jokers[0]!, call: HIGHER, probability: 1 };
      if (game.failed.size > 0) return { position: jokers[0]!, call: HIGHER_EQUAL, probability: 1 };
      if (jokers.length === live.length) return { position: jokers[0]!, call: HIGHER, probability: 1 };
    }

    const table = oddsByRank(rankHistogram(game.drawPile), game.drawPile.length);
    const useInclusive = game.inclusiveLeft > 0;
    const failed = game.failed.size > 0;

    let bestPlain: Candidate | null = null;
    let bestIncl: Candidate | null = null;
    for (const p of live) {
      const rank = box[p]!.rank;
      if (rank === 0) continue; // jokers held in reserve
      const o = table[rank]!;
      const extreme = Math.abs(rank - 8);
      const plain = o[L] > o[H]
        ? candidate(o[L], 0, extreme, rank, p, LOWER)
        : candidate(o[H], 0, extreme, rank, p, HIGHER);
      if (bestPlain === null || greater(plain.key, bestPlain.key)) bestPlain = plain;
      if (useInclusive) {
        const recovery = failed ? o[EXACT] : 0;
        const incl = o[LE] > o[HE]
          ? candidate(o[LE], recovery, extreme, rank, p, LOWER_EQUAL)
          : candidate(o[HE], recovery, extreme, rank, p, HIGHER_EQUAL);
        if (bestIncl === null || greater(incl.key, bestIncl.key)) bestIncl = incl;
      }
    }

    let best = bestPlain!;
    if (bestIncl !== null && (bestIncl.key[0]! - best.key[0]!) * 100 > this.threshold) best = bestIncl;
    return { position: best.position, call: best.call, probability: best.key[0]! };
  }

  /** Bring back the failed box that is easiest to play next: the best
   * plain-call odds against the pile (in practice the most extreme card).
   * Ties go to the more extreme rank, then the lower position. */
  chooseRecovery(game: Game): number | null {
    if (game.failed.size === 0) return null;
    const hist = rankHistogram(game.drawPile);
    const total = game.drawPile.length;
    let best: number[] | null = null;
    let choice: number | null = null;
    for (const [position, card] of game.failed) {
      const odds = oddsFromHistogram(card, hist, total);
      const score = [odds ? odds.bestPlain()[1] : 0, Math.abs(card.rank - 8), -position];
      if (best === null || greater(score, best)) {
        best = score;
        choice = position;
      }
    }
    return choice;
  }
}

/** Play a game to the end with `policy`. Returns the same game. */
export function playOut(game: Game, policy: ThresholdPolicy): Game {
  while (!game.isOver) {
    if (game.recoveryPending) {
      game.recover(policy.chooseRecovery(game)!);
      continue;
    }
    const move = policy.chooseMove(game);
    if (move === null) break;
    game.play(move.position, move.call);
  }
  return game;
}