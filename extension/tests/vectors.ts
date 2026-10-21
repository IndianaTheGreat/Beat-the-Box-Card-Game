/*
==============================================
SHARED TEST VECTOR HELPERS
==============================================
File Location: Beat-the-Box-Card-Game/extension/tests/vectors.ts
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-21
Last Tested: 2026-10-21 (node --test: 80 passed)

VERSION 1.1 CHANGES (2026-10-21):
- Header only: added the KEY FUNCTIONS list. No code changes.

VERSION 1.0 CHANGES (2026-10-20):
- New. Loads shared/test_vectors.json and turns the engine's objects into
  the same shapes the Python generator wrote, so tests can compare them
  directly.

DESCRIPTION:
-----------
Not a test file itself. The *.test.ts files import it.

DEPENDENCIES:
------------
- ../src/engine.ts, ../src/sim.ts
- Node built-ins: node:fs

KEY FUNCTIONS:
-------------
- VECTORS -> shared/test_vectors.json, parsed
- card(key), cards(keys), keyOf(card) -> cards from and to their keys
- stateOf(game), resultOf(playResult), batchOf(result, mean, low, high)
  -> the same shapes as _state(), _result() and _batch() in vectors.py
- tallyObject(tally) -> a tally as {"value": games}, smallest value first
- stopAfter(calls), progressRecorder() -> the Stop check and progress
  recorder the Python vectors used

NOTES:
-----
- The vectors use Python's snake_case names; the mapping to the port's
  camelCase names lives here and nowhere else.
- JSON object keys are text, so tallies come back as {"3": 2}; tallyObject
  writes a Map the same way.
*/

import { readFileSync } from "node:fs";

import { Card } from "../src/engine.ts";
import type { Game, PlayResult } from "../src/engine.ts";
import type { BatchResult, Tally } from "../src/sim.ts";

/** The file has no fixed shape for TypeScript; tests reach into it freely. */
export type Json = any;

export const VECTORS: Json = JSON.parse(
  readFileSync(new URL("../../shared/test_vectors.json", import.meta.url), "utf8"),
);

export function card(key: string): Card {
  return Card.parse(key);
}

export function cards(keys: readonly string[]): Card[] {
  return keys.map(card);
}

export function keyOf(c: Card | null | undefined): string | null {
  return c == null ? null : c.key();
}

/** The same fields, names and order as vectors.py _state(). */
export function stateOf(game: Game): Json {
  const failed: Record<string, string> = {};
  for (const p of game.failedPositions) failed[String(p)] = game.failed.get(p)!.key();
  const s = game.stats;
  return {
    box: game.box.map(keyOf),
    failed,
    pile: game.drawPile.map((c) => c.key()).join(" "),
    inclusive_left: game.inclusiveLeft,
    recovery_pending: game.recoveryPending,
    counts: [...game.counts],
    stats: {
      plays: s.plays, inclusive_used: s.inclusiveUsed, jokers_drawn: s.jokersDrawn,
      recoveries: s.recoveries, recoveries_lost: s.recoveriesLost,
    },
    boxes_left: game.boxesLeft,
    cards_left: game.cardsLeft,
    live: game.livePositions,
    failed_positions: game.failedPositions,
    won: game.won,
    lost: game.lost,
    over: game.isOver,
    can_undo: game.canUndo,
  };
}

/** vectors.py _result(). */
export function resultOf(r: PlayResult): Json {
  return {
    position: r.position, call: r.call, target: r.target.key(), drawn: r.drawn.key(),
    success: r.success, exact_match: r.exactMatch, recovery_earned: r.recoveryEarned,
    recovery_pending: r.recoveryPending, recovery_lost: r.recoveryLost,
    game_over: r.gameOver, won: r.won,
  };
}

export function tallyObject(tally: Tally): Record<string, number> {
  const out: Record<string, number> = {};
  for (const value of [...tally.keys()].sort((a, b) => a - b)) out[String(value)] = tally.get(value)!;
  return out;
}

/** vectors.py _batch(). */
export function batchOf(r: BatchResult, mean: number, low: number, high: number): Json {
  return {
    jokers: r.jokers, calls: r.inclusiveCalls, threshold: r.threshold,
    games: r.games, wins: r.wins, losses: r.losses, win_rate: r.winRate,
    margin: r.margin, margin_points: r.marginPoints, seed: r.seed, stopped: r.stopped,
    boxes_left_in_wins: tallyObject(r.boxesLeftInWins),
    cards_left_in_losses: tallyObject(r.cardsLeftInLosses),
    plays: tallyObject(r.plays), inclusive_used: tallyObject(r.inclusiveUsed),
    jokers_drawn: tallyObject(r.jokersDrawn), recoveries: tallyObject(r.recoveries),
    mean_plays: mean, min_plays: low, max_plays: high,
  };
}

/** should_stop that says "stop" on call number calls + 1 (vectors.py _StopAfter). */
export function stopAfter(calls: number): () => boolean {
  let left = calls;
  return () => {
    if (left <= 0) return true;
    left -= 1;
    return false;
  };
}

/** Counts progress calls and keeps the last one (vectors.py _Progress). */
export function progressRecorder(): { fn: (done: number, total: number) => void; record: () => Json } {
  let calls = 0;
  let last: number[] | null = null;
  return {
    fn: (done, total) => { calls += 1; last = [done, total]; },
    record: () => ({ calls, last }),
  };
}