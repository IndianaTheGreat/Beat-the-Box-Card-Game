/*
==============================================
RULES ENGINE TESTS (TYPESCRIPT)
==============================================
File Location: Beat-the-Box-Card-Game/extension/tests/engine.test.ts
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (node --test: 80 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Checks src/engine.ts against every engine section of
  shared/test_vectors.json: the shuffle, cards, parsing, calls, offered
  calls, odds, counts, settings, and scripted games step by step (each
  step's result and the whole game state after it, and that illegal
  moves throw and change nothing).

DESCRIPTION:
-----------
The same answers the Python engine gives, so both versions play by
docs/RULES.md in exactly the same way.

DEPENDENCIES:
------------
- ../src/engine.ts, ./vectors.ts
- Node built-ins: node:test, node:assert/strict

CLI USAGE:
---------
From the extension folder:

    node --test                      # every test file
    node --test tests/engine.test.ts # just this one
*/

import assert from "node:assert/strict";
import { describe, test } from "node:test";

import {
  BOX_SIZE, CALLS, CALL_LABELS, Card, COUNT_METHOD_NAMES, Game, MAX_JOKERS, OFFER_ORDER, Odds,
  RANKS, Rng, RulesError, STANDARD_DRAW_PILE, callBlockedReason, callWins, countLean,
  countValues, isExactMatch, maxInclusiveCalls, oddsAgainst, oddsByRank, offeredCalls,
  rankHistogram, shuffledDeck, standardDeck, takeCard, validateSettings,
} from "../src/engine.ts";
import type { Call } from "../src/engine.ts";
import { VECTORS, card, cards, keyOf, resultOf, stateOf } from "./vectors.ts";
import type { Json } from "./vectors.ts";

const V = VECTORS;

/** A joker, then a spade of every rank (vectors.py _rank_cards). */
function rankCards(): Card[] {
  return [Card.joker(), ...RANKS.map((rank) => Card.of(rank, "♠"))];
}

describe("vectors file", () => {
  test("is the format this test knows", () => {
    assert.equal(V.format, 1);
  });
});

describe("shuffle", () => {
  test("Mulberry32 gives the same numbers as Python", () => {
    for (const row of V.rng) {
      const rng = new Rng(row.seed);
      assert.deepEqual(Array.from({ length: 8 }, () => rng.nextUint32()), row.uint32, `seed ${row.seed}`);
      const again = new Rng(row.seed);
      assert.deepEqual([1, 2, 3, 13, 52, 54, 1000].map((n) => again.below(n)),
        row.below_1_2_3_13_52_54_1000, `seed ${row.seed}`);
    }
  });

  test("standard decks and seeded deals match card for card", () => {
    for (let j = 0; j <= MAX_JOKERS; j++) {
      assert.deepEqual(standardDeck(j).map((c) => c.key()), V.decks.standard[String(j)]);
    }
    for (const row of V.decks.shuffled) {
      assert.deepEqual(shuffledDeck(row.jokers, row.seed).map((c) => c.key()), row.deck,
        `jokers ${row.jokers} seed ${row.seed}`);
    }
    for (const bad of V.decks.bad_jokers) assert.throws(() => standardDeck(bad), RulesError);
  });
});

describe("cards", () => {
  test("names, labels, keys and count values", () => {
    for (const row of V.cards) {
      const c = Card.parse(row.key);
      assert.deepEqual({
        key: c.key(), label: c.label(), name: c.name, rank: c.rank, suit: c.suit, kind: c.kind,
        rank_label: c.rankLabel, is_joker: c.isJoker, counts: countValues(c),
      }, row);
    }
  });

  test("parsing reads (and refuses) the same text", () => {
    for (const [text, key] of V.parse as [string, string | null][]) {
      if (key === null) assert.throws(() => Card.parse(text), RangeError, JSON.stringify(text));
      else assert.equal(Card.parse(text).key(), key, JSON.stringify(text));
    }
  });

  test("cards are shared objects; equals ignores the joker kind", () => {
    assert.equal(Card.of(14, "♠"), Card.parse("A♠"));
    assert.notEqual(Card.joker("big"), Card.joker("little"));
    assert.ok(Card.joker("big").equals(Card.joker("little")));
    assert.ok(!Card.of(14, "♠").equals(Card.of(14, "♥")));
    assert.ok(Object.isFrozen(Card.of(2, "♣")));
  });

  test("impossible cards are refused", () => {
    assert.throws(() => Card.of(15, "♠"), RangeError);
    assert.throws(() => Card.of(0, "♠"), RangeError);
    assert.throws(() => Card.of(9, "♠", "big"), RangeError);
    assert.throws(() => Card.of(0, "", "toString"), RangeError); // not fooled by built-in names
    assert.throws(() => Card.of(9, "X"), RangeError);
  });

  test("takeCard takes the same joker kind first, then any joker", () => {
    const pile = standardDeck(2);
    assert.equal(takeCard(pile, Card.joker("little")).kind, "little");
    assert.equal(takeCard(pile, Card.joker("little")).kind, "big");
    assert.throws(() => takeCard(pile, Card.joker()), RangeError);
    assert.equal(pile.length, 52);
  });
});

describe("calls", () => {
  test("every call against every pair of ranks", () => {
    const deck = rankCards();
    assert.deepEqual(deck.map((c) => c.rank), V.calls.ranks);
    for (const call of CALLS) {
      const grid = deck.map((drawn) => deck.map((target) => Number(callWins(call, drawn, target))));
      assert.deepEqual(grid, V.calls.wins[call], call);
    }
    assert.deepEqual(deck.map((drawn) => deck.map((target) => Number(isExactMatch(drawn, target)))),
      V.calls.exact);
    assert.throws(() => callWins(V.calls.bad_call as Call, deck[2]!, deck[3]!), RulesError);
    assert.deepEqual(CALL_LABELS, V.calls.labels);
    assert.deepEqual(OFFER_ORDER, V.calls.offer_order);
  });

  test("offered calls and the reasons the others are greyed out", () => {
    const byRank = new Map(rankCards().map((c) => [c.rank, c]));
    for (const row of V.offers) {
      const c = byRank.get(row.rank)!;
      const reasons = Object.fromEntries(CALLS.map((call) => [call, callBlockedReason(c, call, row.inclusive_left)]));
      assert.deepEqual(reasons, row.reasons, `rank ${row.rank}, ${row.inclusive_left} left`);
      assert.deepEqual(offeredCalls(c, row.inclusive_left), row.offered);
    }
  });
});

describe("odds and counts", () => {
  test("odds tables for every rank against each pile", () => {
    for (const row of V.odds.tables) {
      const pile = cards(row.pile);
      const hist = rankHistogram(pile);
      assert.deepEqual(hist, row.histogram);
      const table = oddsByRank(hist, pile.length);
      assert.deepEqual(table, row.table, `pile of ${pile.length}`);
      const best = table.map((entry) => {
        if (entry === null) return null;
        const odds = Odds.fromTuple(entry);
        return [odds.bestPlain()[0], odds.bestInclusive()[0]];
      });
      assert.deepEqual(best, row.best_plain_and_inclusive);
    }
  });

  test("odds for one box card", () => {
    for (const row of V.odds.against) {
      const odds = oddsAgainst(card(row.target), cards(row.pile))!;
      assert.deepEqual([odds.higher, odds.lower, odds.higherEqual, odds.lowerEqual, odds.exact], row.odds);
    }
    assert.equal(oddsAgainst(Card.of(9, "♠"), []) === null, V.odds.empty_pile_is_null);
  });

  test("a game's odds for all boxes agree with its odds for each box", () => {
    for (const seed of [31, 32, 33]) {
      const game = Game.deal(2, 5, seed);
      game.play(4, "lower");
      assert.deepEqual(game.oddsAll(), game.box.map((_c, p) => game.odds(p)));
    }
  });

  test("counting methods and which way a count leans", () => {
    assert.deepEqual(COUNT_METHOD_NAMES, V.counts.methods);
    for (const [count, lean] of V.counts.lean) assert.equal(countLean(count), lean, `count ${count}`);
  });

  test("settings limits", () => {
    const s = V.settings;
    assert.deepEqual([0, 1, 2].map(maxInclusiveCalls), s.max_inclusive_calls);
    for (const [jokers, calls, ok] of s.validate) {
      if (ok) validateSettings(jokers, calls);
      else assert.throws(() => validateSettings(jokers, calls), RulesError, `${jokers} jokers, ${calls} calls`);
    }
    assert.equal(BOX_SIZE, s.box_size);
    assert.equal(MAX_JOKERS, s.max_jokers);
    assert.equal(STANDARD_DRAW_PILE, s.standard_draw_pile);
  });
});

/** Run each recorded step and compare its answer and the state after it. */
function replay(game: Game, steps: Json[]): void {
  let previous = stateOf(game);
  steps.forEach((step, i) => {
    const { state: _state, value: _value, ...action } = step;
    const where = `step ${i}: ${JSON.stringify(action)}`;
    const run = (): unknown => {
      switch (step.do) {
        case "play": return resultOf(game.play(step.position, step.call,
          step.drawn === undefined ? undefined : card(step.drawn)));
        case "recover": return keyOf(game.recover(step.position));
        case "skip": game.skipRecovery(); return null;
        case "undo": return game.undo();
        default: throw new Error(`unknown step ${step.do}`);
      }
    };
    if (step.error) {
      assert.throws(run, RulesError, where);
      assert.deepEqual(stateOf(game), previous, `${where} changed the game`);
    } else {
      assert.deepEqual(run(), step.value, where);
      assert.deepEqual(stateOf(game), step.state, where);
      previous = step.state;
    }
  });
}

describe("scripted games", () => {
  for (const g of V.games.dealt) {
    test(`dealt game, seed ${g.seed}, ${g.jokers} jokers, ${g.calls} calls`, () => {
      const game = Game.deal(g.jokers, g.calls, g.seed);
      assert.deepEqual(stateOf(game), g.start);
      replay(game, g.steps);
    });
  }

  for (const g of V.games.assistant) {
    test(`Assistant game from a known box: ${g.box.slice(0, 3).join(" ")}...`, () => {
      const game = Game.fromBox(cards(g.box), g.jokers, g.calls);
      assert.deepEqual(stateOf(game), g.start);
      replay(game, g.steps);
    });
  }

  for (const g of V.games.built) {
    test(`hand-built game: ${g.name}`, () => {
      const game = Game.fromCards(cards(g.box), cards(g.pile), g.calls);
      assert.deepEqual(stateOf(game), g.start);
      replay(game, g.steps);
    });
  }

  test("deals and boxes the rules don't allow", () => {
    for (const row of V.games.bad_boxes) {
      const make = () => Game.fromBox(cards(row.box), row.jokers, row.calls);
      if (row.ok) make();
      else assert.throws(make, RulesError, row.box.join(" "));
    }
    for (const row of V.games.bad_deals) {
      assert.throws(() => Game.deal(row.jokers, row.calls, 1), RulesError);
      assert.equal(row.ok, false);
    }
    for (const row of V.games.bad_from_cards) {
      const make = () => Game.fromCards(cards(row.box), [Card.of(2, "♣")], row.calls);
      if (row.ok) make();
      else assert.throws(make, RulesError);
    }
  });
});