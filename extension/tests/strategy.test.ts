/*
==============================================
STRATEGY POLICY TESTS (TYPESCRIPT)
==============================================
File Location: Beat-the-Box-Card-Game/extension/tests/strategy.test.ts
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (node --test: 80 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Replays the Python policy's whole games move for move (with the
  chance it gave each move) and its tie-breaking on hand-built boards.

DESCRIPTION:
-----------
If these pass, the Simulator and Optimizer in Chrome choose exactly what
the Python ones choose, so their win rates match.

DEPENDENCIES:
------------
- ../src/engine.ts, ../src/strategy.ts, ./vectors.ts
- Node built-ins: node:test, node:assert/strict

CLI USAGE:
---------
From the extension folder:

    node --test tests/strategy.test.ts
*/

import assert from "node:assert/strict";
import { describe, test } from "node:test";

import { Card, Game } from "../src/engine.ts";
import { DEFAULT_THRESHOLD, ThresholdPolicy, playOut } from "../src/strategy.ts";
import { VECTORS, card, cards, stateOf } from "./vectors.ts";

const V = VECTORS.strategy;

describe("strategy", () => {
  test("default threshold", () => {
    assert.equal(DEFAULT_THRESHOLD, V.default_threshold);
  });

  for (const t of V.traces) {
    test(`whole game: ${t.jokers} jokers, ${t.calls} calls, threshold ${t.threshold}, seed ${t.seed}`, () => {
      const policy = new ThresholdPolicy(t.threshold);
      const game = Game.deal(t.jokers, t.calls, t.seed);
      const moves: unknown[] = [];
      while (!game.isOver) { // the same loop as playOut
        if (game.recoveryPending) {
          const p = policy.chooseRecovery(game)!;
          moves.push(["recover", p]);
          game.recover(p);
          continue;
        }
        const move = policy.chooseMove(game);
        if (move === null) break;
        moves.push([move.position, move.call, move.probability]);
        game.play(move.position, move.call);
      }
      assert.deepEqual(moves, t.moves);
      assert.equal(game.won, t.won);
      assert.equal(game.boxesLeft, t.boxes_left);
      assert.equal(game.cardsLeft, t.cards_left);
      assert.deepEqual(stateOf(game).stats, t.stats);
      const check = playOut(Game.deal(t.jokers, t.calls, t.seed), policy);
      assert.deepEqual(stateOf(check), stateOf(game));
    });
  }

  test("tie-breaking and jokers on hand-built boards", () => {
    for (const d of V.decisions) {
      const box = d.box.map((key: string | null) => (key === null ? Card.of(2, "♠") : card(key)));
      const game = Game.fromCards(box, cards(d.pile), d.inclusive_left);
      d.box.forEach((key: string | null, p: number) => { if (key === null) game.box[p] = null; });
      for (const [p, key] of Object.entries(d.failed) as [string, string][]) {
        game.box[Number(p)] = null;
        game.failed.set(Number(p), card(key));
      }
      const policy = new ThresholdPolicy(d.threshold);
      const move = policy.chooseMove(game);
      assert.deepEqual(move === null ? null : [move.position, move.call, move.probability], d.move,
        JSON.stringify(d.box));
      assert.equal(policy.chooseRecovery(game), d.recovery, JSON.stringify(d.box));
    }
  });
});