"""
==============================================
SHARED TEST VECTORS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/vectors.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-21
Last Tested: 2026-10-21 (pytest: 314 passed)

VERSION 1.1 CHANGES (2026-10-21):
- Closes three gaps found by breaking the TypeScript port on purpose
  (each break passed every test before this change):
  * The sweep vectors now mix thresholds 0, 2.5 and 10, which sort in a
    different order as text ("0", "10", "2.5") than as numbers. Before,
    a port that sorted best_by, top_by or best_curves as text passed.
  * The confirmed sweep with Stop now stops after two of its four
    confirmation re-runs have finished (Stop on check 331 instead of
    131). Before, it stopped before any re-run finished, so a port that
    kept a half-finished confirmation passed.
  * A tally with zero entries ({2: 0, 5: 1, 9: 0}): min, max and the
    chart range ignore values no game reached.
- No change to the engine, the strategy or the simulator.

VERSION 1.0 CHANGES (2026-10-20):
- New. Writes shared/test_vectors.json: answers worked out by this engine
  that the Chrome extension's TypeScript engine must reproduce exactly.
  Covers the shuffle, card names and parsing, every call, the offered
  calls, odds, counts, settings limits, scripted games (dealt and
  Assistant style, with undo, recoveries and illegal moves), strategy
  decisions, whole simulated games, statistics helpers, batches and
  sweeps (including stopped runs).

DESCRIPTION:
-----------
One file of known answers, shared by both versions of the game. The
Python test (tests/test_vectors.py) checks the file still matches this
engine; the TypeScript tests (extension/tests/) check the port gives the
same answers. If a rule changes, the Python test fails until the file is
rewritten, and then the TypeScript tests fail until the port catches up.
That is how "Phase 2 must pass the same tests" is kept true.

DEPENDENCIES:
------------
- btb.engine, btb.strategy, btb.sim
- Standard library: collections, json, pathlib, typing

KEY FUNCTIONS:
-------------
- build() -> dict of every vector section
- render(data) -> the JSON text written to the file
- write(path) -> rewrites the file, returns its size in bytes
- VECTORS_PATH -> shared/test_vectors.json in the repo folder

CLI USAGE:
---------
From the python folder:

    python -m btb.vectors          # rewrite ../shared/test_vectors.json

Run it after a rule change, then run both test suites.

NOTES:
-----
- Every choice in a scripted game is made with the engine's own Rng
  (Mulberry32), never Python's random module, so the file is the same on
  every computer.
- Keys are snake_case, as in the Python engine. The TypeScript tests map
  them to the port's camelCase names.
- The file is UTF-8 with real suit symbols, so it reads well in an editor.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import engine as e
from . import sim
from .strategy import ThresholdPolicy, play_out

VECTORS_PATH = Path(__file__).resolve().parents[2] / "shared" / "test_vectors.json"
VECTOR_FORMAT = 1


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #

def _key(card: Optional[e.Card]) -> Optional[str]:
    return None if card is None else card.key()


def _keys(cards) -> List[str]:
    return [card.key() for card in cards]


def _tally(counter) -> Dict[str, int]:
    return {str(k): counter[k] for k in sorted(counter)}


def _every_card() -> List[e.Card]:
    """All 52 cards, both joker kinds, and a joker with no kind."""
    return e.standard_deck(2) + [e.Card.joker()]


def _rank_cards() -> List[e.Card]:
    """One card per rank: a joker, then 2 to A."""
    return [e.Card.joker()] + [e.Card(rank, "♠") for rank in e.RANKS]


def _state(game: e.Game) -> Dict[str, Any]:
    return {
        "box": [_key(card) for card in game.box],
        "failed": {str(p): game.failed[p].key() for p in sorted(game.failed)},
        "pile": " ".join(_keys(game.draw_pile)),
        "inclusive_left": game.inclusive_left,
        "recovery_pending": game.recovery_pending,
        "counts": list(game.counts),
        "stats": dict(game.stats),
        "boxes_left": game.boxes_left,
        "cards_left": game.cards_left,
        "live": game.live_positions,
        "failed_positions": game.failed_positions,
        "won": game.won,
        "lost": game.lost,
        "over": game.is_over,
        "can_undo": game.can_undo,
    }


def _result(r: e.PlayResult) -> Dict[str, Any]:
    return {
        "position": r.position, "call": r.call, "target": r.target.key(),
        "drawn": r.drawn.key(), "success": r.success, "exact_match": r.exact_match,
        "recovery_earned": r.recovery_earned, "recovery_pending": r.recovery_pending,
        "recovery_lost": r.recovery_lost, "game_over": r.game_over, "won": r.won,
    }


def _batch(r: sim.BatchResult) -> Dict[str, Any]:
    return {
        "jokers": r.jokers, "calls": r.inclusive_calls, "threshold": r.threshold,
        "games": r.games, "wins": r.wins, "losses": r.losses, "win_rate": r.win_rate,
        "margin": list(r.margin), "margin_points": r.margin_points,
        "seed": r.seed, "stopped": r.stopped,
        "boxes_left_in_wins": _tally(r.boxes_left_in_wins),
        "cards_left_in_losses": _tally(r.cards_left_in_losses),
        "plays": _tally(r.plays), "inclusive_used": _tally(r.inclusive_used),
        "jokers_drawn": _tally(r.jokers_drawn), "recoveries": _tally(r.recoveries),
        "mean_plays": sim.counter_mean(r.plays),
        "min_plays": sim.counter_min(r.plays), "max_plays": sim.counter_max(r.plays),
    }


def _config(r: sim.BatchResult) -> list:
    return [r.jokers, r.inclusive_calls, r.threshold]


class _StopAfter:
    """should_stop that says "stop" on call number calls + 1."""

    def __init__(self, calls: int) -> None:
        self.left = calls

    def __call__(self) -> bool:
        if self.left <= 0:
            return True
        self.left -= 1
        return False


class _Progress:
    def __init__(self) -> None:
        self.calls = 0
        self.last: Optional[list] = None

    def __call__(self, done: int, total: int) -> None:
        self.calls += 1
        self.last = [done, total]

    def record(self) -> Dict[str, Any]:
        return {"calls": self.calls, "last": self.last}


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #

RNG_SEEDS = (0, 1, 7, 42, 2026, 123456789, 4294967295, 4294967296 + 5, -1)


def _rng() -> list:
    out = []
    for seed in RNG_SEEDS:
        rng = e.Rng(seed)
        values = [rng.next_uint32() for _ in range(8)]
        rng = e.Rng(seed)
        below = [rng.below(n) for n in (1, 2, 3, 13, 52, 54, 1000)]
        out.append({"seed": seed, "uint32": values, "below_1_2_3_13_52_54_1000": below})
    return out


def _decks() -> Dict[str, Any]:
    return {
        "standard": {str(j): _keys(e.standard_deck(j)) for j in range(e.MAX_JOKERS + 1)},
        "shuffled": [{"jokers": j, "seed": seed, "deck": _keys(e.shuffled_deck(j, seed))}
                     for seed in (0, 1, 99, 2026, 4294967295) for j in range(3)],
        "bad_jokers": [-1, 3],
    }


def _cards() -> list:
    return [{"key": c.key(), "label": c.label(), "name": c.name, "rank": c.rank,
             "suit": c.suit, "kind": c.kind, "rank_label": c.rank_label,
             "is_joker": c.is_joker, "counts": e.count_values(c)}
            for c in _every_card()]


PARSE_INPUTS = (
    "A♠", "a♠", "10♣", "q♥", "J♣", "k♦", " K♦ ", "7S", "7s", "2h", "9D", "3c",
    "1h", "11♠", "14♦", "07♠", "+7♠", "7 ♠", "1_0♠",
    "🃏", "joker", "JOKER", "jk", "Jk", "🃏:big", "🃏:little", "big joker",
    "Big Joker", "LITTLE JOKER", "little joker",
    "", "A", "Z♠", "15♠", "0♠", "-7♠", "AX", "10", "♠A", "🃏:medium",
    "A♠️", "1__0♠", "_10♠", "10_♠", "J J♠",
)


def _parse() -> list:
    out = []
    for text in PARSE_INPUTS:
        try:
            out.append([text, e.Card.parse(text).key()])
        except ValueError:
            out.append([text, None])
    return out


def _calls() -> Dict[str, Any]:
    cards = _rank_cards()
    ranks = [c.rank for c in cards]
    wins = {call: [[int(e.call_wins(call, drawn, target)) for target in cards]
                   for drawn in cards] for call in e.CALLS}
    exact = [[int(e.is_exact_match(drawn, target)) for target in cards] for drawn in cards]
    return {"ranks": ranks, "rows_are": "drawn", "columns_are": "box card",
            "wins": wins, "exact": exact, "bad_call": "sideways",
            "labels": dict(e.CALL_LABELS), "offer_order": list(e.OFFER_ORDER)}


def _offers() -> list:
    out = []
    for card in _rank_cards():
        for left in (0, 1, 3):
            out.append({
                "rank": card.rank, "inclusive_left": left,
                "reasons": {call: e.call_blocked_reason(card, call, left) for call in e.CALLS},
                "offered": list(e.offered_calls(card, left)),
            })
    return out


def _odds() -> Dict[str, Any]:
    piles: List[List[e.Card]] = [
        [],
        [e.Card.joker("big")],
        [e.Card.parse(t) for t in ("2♠", "2♥", "A♦")],
        [e.Card(rank, "♣") for rank in e.RANKS],
        e.Game.new(0, 5, 2026).draw_pile,
        e.Game.new(2, 5, 7).draw_pile,
    ]
    for size, seed in ((1, 3), (5, 4), (17, 5), (30, 6)):
        piles.append(e.shuffled_deck(2, seed)[:size])
    tables = []
    for pile in piles:
        hist = e.rank_histogram(pile)
        table = e.odds_by_rank(hist, len(pile))
        best = []
        for rank, entry in enumerate(table):
            if entry is None:
                best.append(None)
            else:
                odds = e.Odds(*entry)
                best.append([odds.best_plain()[0], odds.best_inclusive()[0]])
        tables.append({"pile": _keys(pile), "histogram": hist,
                       "table": [None if t is None else list(t) for t in table],
                       "best_plain_and_inclusive": best})
    against = []
    pile = e.shuffled_deck(1, 11)[:20]
    for target in _rank_cards():
        odds = e.odds_against(target, pile)
        against.append({"target": target.key(), "pile": _keys(pile),
                        "odds": [odds.higher, odds.lower, odds.higher_equal,
                                 odds.lower_equal, odds.exact]})
    return {"tables": tables, "against": against,
            "empty_pile_is_null": e.odds_against(e.Card(9, "♠"), []) is None}


def _counts() -> Dict[str, Any]:
    return {"methods": list(e.COUNT_METHOD_NAMES),
            "lean": [[n, e.count_lean(n)] for n in (-5, -1, 0, 1, 3)]}


def _settings() -> Dict[str, Any]:
    cases = []
    for jokers, calls in ((0, 0), (0, 43), (0, 44), (1, 44), (1, 45), (2, 45), (2, 46),
                          (3, 0), (-1, 0), (0, -1)):
        try:
            e.validate_settings(jokers, calls)
            ok = True
        except e.RulesError:
            ok = False
        cases.append([jokers, calls, ok])
    return {"max_inclusive_calls": [e.max_inclusive_calls(j) for j in range(3)],
            "validate": cases, "box_size": e.BOX_SIZE, "max_jokers": e.MAX_JOKERS,
            "standard_draw_pile": e.STANDARD_DRAW_PILE}


# ----- scripted games ---------------------------------------------------- #

def _missing_card(game: e.Game) -> e.Card:
    """A card that is not in the draw pile (for an illegal drawn= move)."""
    for card in e.standard_deck(0):
        if card not in game.draw_pile:
            return card
    return e.Card.joker()


def _try(game: e.Game, action: Dict[str, Any], run) -> Dict[str, Any]:
    """Run one action. Errors are recorded and must leave the state alone."""
    before = _state(game)
    try:
        value = run()
    except e.RulesError:
        assert _state(game) == before, "an illegal move changed the game"
        return {**action, "error": True}
    return {**action, "value": value, "state": _state(game)}


def _illegal(game: e.Game, rng: e.Rng, assistant: bool) -> Dict[str, Any]:
    if game.recovery_pending:
        choice = rng.below(3)
        if choice == 0:
            p = game.live_positions[0]
            return _try(game, {"do": "play", "position": p, "call": e.HIGHER},
                        lambda: game.play(p, e.HIGHER))
        if choice == 1 and game.live_positions:
            p = game.live_positions[-1]
            return _try(game, {"do": "recover", "position": p}, lambda: game.recover(p))
        return _try(game, {"do": "play", "position": 0, "call": e.LOWER},
                    lambda: game.play(0, e.LOWER))
    options = ["position", "call", "recover", "skip"]
    if game.failed:
        options.append("failed")
    if game.inclusive_left == 0:
        options.append("inclusive")
    if assistant:
        options.append("drawn")
    pick = options[rng.below(len(options))]
    live = game.live_positions
    if pick == "position":
        p = (9, -1)[rng.below(2)]
        return _try(game, {"do": "play", "position": p, "call": e.HIGHER},
                    lambda: game.play(p, e.HIGHER))
    if pick == "call":
        return _try(game, {"do": "play", "position": live[0], "call": "sideways"},
                    lambda: game.play(live[0], "sideways"))
    if pick == "recover":
        p = game.failed_positions[0] if game.failed else 0
        return _try(game, {"do": "recover", "position": p}, lambda: game.recover(p))
    if pick == "skip":
        return _try(game, {"do": "skip"}, game.skip_recovery)
    if pick == "failed":
        p = game.failed_positions[0]
        return _try(game, {"do": "play", "position": p, "call": e.LOWER},
                    lambda: game.play(p, e.LOWER))
    if pick == "inclusive":
        return _try(game, {"do": "play", "position": live[0], "call": e.HIGHER_EQUAL},
                    lambda: game.play(live[0], e.HIGHER_EQUAL))
    card = _missing_card(game)
    return _try(game, {"do": "play", "position": live[0], "call": e.HIGHER,
                       "drawn": card.key()},
                lambda: game.play(live[0], e.HIGHER, drawn=card))


SCRIPT_POLICY = ThresholdPolicy(0.0)   # spends inclusive calls freely: more recoveries


def _run(game: e.Game, action: Dict[str, Any]) -> Dict[str, Any]:
    """Run one written-out action (the hand-built games)."""
    do = action["do"]
    if do == "play":
        drawn = action.get("drawn")
        return _try(game, action, lambda: _result(game.play(
            action["position"], action["call"],
            drawn=None if drawn is None else e.Card.parse(drawn))))
    if do == "recover":
        return _try(game, action, lambda: _key(game.recover(action["position"])))
    if do == "skip":
        return _try(game, action, game.skip_recovery)
    return _try(game, action, game.undo)


def _play(p: int, call: str, drawn: Optional[str] = None) -> Dict[str, Any]:
    action: Dict[str, Any] = {"do": "play", "position": p, "call": call}
    if drawn is not None:
        action["drawn"] = drawn
    return action


_UNDO = {"do": "undo"}
_SKIP = {"do": "skip"}


def _recover(p: int) -> Dict[str, Any]:
    return {"do": "recover", "position": p}


H, L, HE, LE = e.HIGHER, e.LOWER, e.HIGHER_EQUAL, e.LOWER_EQUAL

# Hand-built games that reach the rare cases on purpose.
BUILT_GAMES = (
    {"name": "recovery earned on the last card",
     "box": ("5♦", "7♣", "2♠", "3♠", "4♠", "6♠", "9♠", "10♠", "J♠"),
     "pile": ("K♠", "7♥"), "calls": 1,
     "actions": (_play(0, L), _play(1, HE), _play(2, H), _UNDO, _play(1, HE),
                 _recover(1), _recover(0), _play(2, H), _SKIP, _UNDO, _UNDO, _UNDO,
                 _UNDO)},
    {"name": "recovery lost, then a skipped recovery, then a win",
     "box": ("8♠", "8♥", "2♣", "A♣", "3♦", "Q♦", "4♥", "J♥", "6♣"),
     "pile": ("8♦", "9♣", "2♦", "8♣", "5♥"), "calls": 3,
     "actions": (_play(0, HE), _play(1, L), _play(2, HE), _recover(2), _SKIP,
                 _play(3, LE), _play(4, H), _play(5, LE), _play(5, H), _play(0, H))},
    {"name": "jokers in the pile and in the box",
     "box": ("🃏:big", "9♥", "8♦", "K♣", "2♥", "5♣", "7♦", "Q♥", "4♣"),
     "pile": ("🃏:little", "3♠", "9♠", "10♦"), "calls": 2,
     "actions": (_play(1, L), _play(2, H), _play(0, HE), _recover(2), _play(1, L),
                 _play(1, LE))},
    {"name": "all nine boxes fail",
     "box": ("A♠", "A♥", "A♦", "A♣", "K♠", "K♥", "K♦", "K♣", "Q♠"),
     "pile": ("2♠", "2♥", "2♦", "2♣", "3♠", "3♥", "3♦", "3♣", "4♠", "5♠"), "calls": 0,
     "actions": tuple(_play(p, H) for p in range(9)) + (_play(0, L), _UNDO, _play(8, L),
                                                       _UNDO, _play(8, HE), _play(8, H))},
    {"name": "named draws (Assistant) from a known pile",
     "box": ("6♠", "6♥", "J♦", "3♣", "Q♠", "9♦", "2♥", "K♣", "7♠"),
     "pile": ("🃏:big", "🃏:little", "6♦", "A♠", "5♣"), "calls": 2,
     "actions": (_play(0, HE, "6♦"), _play(1, H, "A♠"), _play(2, L, "🃏"),
                 _play(3, H, "🃏:big"), _play(4, LE, "K♠"), _play(4, L, "5♣"),
                 _UNDO, _play(4, HE, "5♣"), _play(4, H, "🃏:little"))},
)


def _built_games() -> list:
    out = []
    for spec in BUILT_GAMES:
        game = e.Game.from_cards([e.Card.parse(t) for t in spec["box"]],
                                 [e.Card.parse(t) for t in spec["pile"]], spec["calls"])
        out.append({"name": spec["name"], "box": list(spec["box"]),
                    "pile": list(spec["pile"]), "calls": spec["calls"],
                    "start": _state(game),
                    "steps": [_run(game, dict(action)) for action in spec["actions"]]})
    return out


def _script(game: e.Game, rng: e.Rng, assistant: bool) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    undos_after_end = 2
    while len(steps) < 200:
        roll = rng.below(100)
        if game.is_over:
            if roll < 40 and undos_after_end > 0:
                undos_after_end -= 1
                steps.append(_try(game, {"do": "undo"}, game.undo))
                continue
            # Nothing is allowed once the game is over.
            p = rng.below(e.BOX_SIZE)
            steps.append(_try(game, {"do": "play", "position": p, "call": e.HIGHER},
                              lambda: game.play(p, e.HIGHER)))
            steps.append(_try(game, {"do": "skip"}, game.skip_recovery))
            break
        if game.recovery_pending:
            if roll < 15:
                steps.append(_try(game, {"do": "skip"}, game.skip_recovery))
            elif roll < 22:
                steps.append(_illegal(game, rng, assistant))
            elif roll < 27:
                steps.append(_try(game, {"do": "undo"}, game.undo))
            else:
                failed = game.failed_positions
                p = failed[rng.below(len(failed))]
                steps.append(_try(game, {"do": "recover", "position": p},
                                  lambda: _key(game.recover(p))))
            continue
        if roll < 6:
            steps.append(_try(game, {"do": "undo"}, game.undo))
        elif roll < 11:
            steps.append(_illegal(game, rng, assistant))
        else:
            # Mostly sensible play (so games last and some are won), with
            # some random calls mixed in.
            move = SCRIPT_POLICY.choose_move(game) if roll < 75 else None
            if move is not None:
                p, call = move.position, move.call
            else:
                live = game.live_positions
                p = live[rng.below(len(live))]
                calls = e.CALLS if game.inclusive_left > 0 else e.PLAIN_CALLS
                call = calls[rng.below(len(calls))]
            action: Dict[str, Any] = {"do": "play", "position": p, "call": call}
            if assistant:
                drawn = game.draw_pile[rng.below(len(game.draw_pile))]
                action["drawn"] = drawn.key()
                steps.append(_try(game, action,
                                  lambda: _result(game.play(p, call, drawn=drawn))))
            else:
                steps.append(_try(game, action, lambda: _result(game.play(p, call))))
    return steps


DEALT_GAMES = ((2026, 0, 5), (7, 1, 3), (99, 2, 8), (12345, 2, 0), (4242, 1, 44),
               (31337, 0, 0))

ASSISTANT_GAMES = (
    (("7♠", "K♥", "3♦", "9♣", "A♠", "2♦", "J♣", "8♥", "5♠"), 1, 5),
    (("🃏:little", "Q♠", "4♥", "10♦", "6♣", "🃏:big", "2♠", "A♦", "8♣"), 2, 2),
    (("🃏", "Q♦", "4♣", "10♥", "6♠", "3♥", "2♣", "A♥", "8♠"), 2, 4),
    (("🃏:big", "🃏:big", "4♦", "10♣", "6♥", "3♠", "2♥", "A♣", "8♦"), 2, 1),
)

BAD_BOXES = (
    (("A♠", "A♠", "3♦", "9♣", "4♠", "2♦", "J♣", "8♥", "5♠"), 0, 5),   # same card twice
    (("🃏", "K♥", "3♦", "9♣", "A♠", "2♦", "J♣", "8♥", "5♠"), 0, 5),    # no jokers in play
    (("7♠", "K♥", "3♦", "9♣", "A♠", "2♦", "J♣", "8♥"), 0, 5),          # eight cards
    (("7♠", "K♥", "3♦", "9♣", "A♠", "2♦", "J♣", "8♥", "5♠"), 0, 44),   # too many calls
    (("7♠", "K♥", "3♦", "9♣", "A♠", "2♦", "J♣", "8♥", "5♠"), 3, 5),    # too many jokers
    (("🃏", "🃏", "🃏", "9♣", "A♠", "2♦", "J♣", "8♥", "5♠"), 2, 5),     # three jokers
)


def _games() -> Dict[str, Any]:
    dealt = []
    for i, (seed, jokers, calls) in enumerate(DEALT_GAMES):
        game = e.Game.new(jokers, calls, seed)
        start = _state(game)
        dealt.append({"seed": seed, "jokers": jokers, "calls": calls, "start": start,
                      "steps": _script(game, e.Rng(1000 + i), assistant=False)})
    assistant = []
    for i, (box, jokers, calls) in enumerate(ASSISTANT_GAMES):
        game = e.Game.from_box([e.Card.parse(t) for t in box], jokers, calls)
        start = _state(game)
        assistant.append({"box": list(box), "jokers": jokers, "calls": calls,
                          "start": start,
                          "steps": _script(game, e.Rng(2000 + i), assistant=True)})
    bad = []
    for box, jokers, calls in BAD_BOXES:
        try:
            e.Game.from_box([e.Card.parse(t) for t in box], jokers, calls)
            ok = True
        except e.RulesError:
            ok = False
        bad.append({"box": list(box), "jokers": jokers, "calls": calls, "ok": ok})
    bad_deals = []
    for jokers, calls in ((3, 0), (0, 44), (0, -1)):
        try:
            e.Game.new(jokers, calls, 1)
            ok = True
        except e.RulesError:
            ok = False
        bad_deals.append({"jokers": jokers, "calls": calls, "ok": ok})
    bad_from_cards = []
    nine = [e.Card.parse(t) for t in ASSISTANT_GAMES[0][0]]
    for box, calls in ((nine[:8], 0), (nine, -1), (nine, 0)):
        try:
            e.Game.from_cards(box, [e.Card(2, "♣")], calls)
            ok = True
        except e.RulesError:
            ok = False
        bad_from_cards.append({"box": _keys(box), "calls": calls, "ok": ok})
    return {"dealt": dealt, "assistant": assistant, "built": _built_games(),
            "bad_boxes": bad, "bad_deals": bad_deals, "bad_from_cards": bad_from_cards}


# ----- strategy ---------------------------------------------------------- #

TRACE_CONFIGS = ((0, 5, 10.0), (1, 0, 10.0), (1, 3, 0.0), (2, 8, 5.0), (2, 45, 30.0),
                 (0, 43, 2.5), (2, 2, 100.0))


def _seeds_with_joker_in_box(jokers: int, start: int, count: int) -> List[int]:
    found = []
    seed = start
    while len(found) < count:
        if any(c.is_joker for c in e.shuffled_deck(jokers, seed)[:e.BOX_SIZE]):
            found.append(seed)
        seed += 1
    return found


def _trace(jokers: int, calls: int, threshold: float, seed: int) -> Dict[str, Any]:
    policy = ThresholdPolicy(threshold)
    game = e.Game.new(jokers, calls, seed)
    moves: list = []
    while not game.is_over:      # the same loop as strategy.play_out
        if game.recovery_pending:
            p = policy.choose_recovery(game)
            moves.append(["recover", p])
            game.recover(p)
            continue
        move = policy.choose_move(game)
        if move is None:
            break
        moves.append([move.position, move.call, move.probability])
        game.play(move.position, move.call)
    check = play_out(e.Game.new(jokers, calls, seed), policy)
    assert _state(check) == _state(game)
    return {"jokers": jokers, "calls": calls, "threshold": threshold, "seed": seed,
            "moves": moves, "won": game.won, "boxes_left": game.boxes_left,
            "cards_left": game.cards_left, "stats": dict(game.stats)}


DECISIONS = (
    # box, pile, inclusive left, threshold, failed {position: card}
    (("7♠", "7♥", "K♦", "4♣", "9♠", "J♥", "5♦", "Q♣", "6♠"),
     ("2♠", "3♥", "8♦", "10♣", "K♠", "A♥"), 0, 10.0, {}),
    (("2♠", "A♥", "8♦", "8♣", "9♠", "J♥", "5♦", "Q♣", "6♠"),
     ("3♠", "4♥", "8♠", "10♣", "K♠", "7♥"), 2, 10.0, {}),
    (("🃏:big", "9♥", "8♦", "8♣", "9♠", "J♥", "5♦", "Q♣", "6♠"),
     ("3♠", "4♥", "8♠", "10♣", "K♠", "7♥"), 2, 10.0, {}),
    (("🃏:big", "9♥", "8♦", "8♣", "9♠", "J♥", "5♦", "Q♣", "6♠"),
     ("3♠", "4♥", "8♠", "10♣", "K♠", "7♥"), 2, 10.0, {1: "2♦"}),
    (("🃏:big", "9♥", "8♦", "8♣", "9♠", "J♥", "5♦", "Q♣", "6♠"),
     ("3♠", "4♥", "8♠", "10♣", "K♠", "7♥"), 0, 10.0, {}),
    (("🃏:big", "🃏:little", None, None, None, None, None, None, None),
     ("3♠", "4♥"), 3, 10.0, {}),
    (("8♠", "8♥", "8♦", None, None, None, None, None, None),
     ("8♣", "9♥", "7♦", "2♣", "A♥"), 1, 0.0, {3: "K♠", 4: "2♥", 5: "7♣"}),
    (("8♠", "8♥", "8♦", None, None, None, None, None, None),
     ("8♣", "9♥", "7♦", "2♣", "A♥"), 1, 50.0, {3: "K♠", 4: "2♥", 5: "7♣"}),
    (("5♠", None, None, None, None, None, None, None, None),
     ("5♣", "5♥", "5♦"), 1, 0.0, {1: "A♠", 2: "2♦", 6: "Q♥"}),
    (("5♠", None, None, None, None, None, None, None, None),
     (), 1, 0.0, {1: "A♠", 2: "2♦", 6: "Q♥"}),
)


def _decisions() -> list:
    out = []
    for box, pile, left, threshold, failed in DECISIONS:
        cards = [e.Card.parse(t) if t else e.Card(2, "♠") for t in box]
        game = e.Game.from_cards(cards, [e.Card.parse(t) for t in pile], left)
        for p, t in enumerate(box):
            if t is None:
                game.box[p] = None
        for p, t in failed.items():
            game.box[p] = None
            game.failed[p] = e.Card.parse(t)
        policy = ThresholdPolicy(threshold)
        move = policy.choose_move(game)
        out.append({
            "box": list(box), "pile": list(pile), "inclusive_left": left,
            "threshold": threshold, "failed": {str(p): t for p, t in failed.items()},
            "move": None if move is None else [move.position, move.call, move.probability],
            "recovery": policy.choose_recovery(game),
        })
    return out


def _strategy() -> Dict[str, Any]:
    traces = []
    for i, (jokers, calls, threshold) in enumerate(TRACE_CONFIGS):
        seeds = [100 * i + 1, 100 * i + 2, 100 * i + 3]
        if jokers:
            seeds += _seeds_with_joker_in_box(jokers, 100 * i + 50, 2)
        traces.extend(_trace(jokers, calls, threshold, seed) for seed in seeds)
    return {"default_threshold": 10.0, "traces": traces, "decisions": _decisions()}


# ----- statistics, batches and sweeps ------------------------------------ #

def _stats() -> Dict[str, Any]:
    wilson = [[w, g, list(sim.wilson_interval(w, g))]
              for w, g in ((0, 0), (0, 10), (10, 10), (5, 10), (1, 3), (1358, 5000),
                           (999, 1000), (123456, 10000000))]
    ranges = []
    for start, stop, step in ((0, 30, 5), (0, 1, 0.1), (2.5, 10, 2.5), (0, 0, 1),
                              (0, 10, 3), (1, 2, 0.3), (0, 100, 0.5), (0.1, 0.7, 0.2),
                              (0, 1, 0), (1, 0, 1), (0, 1, -1)):
        try:
            ranges.append([start, stop, step, sim.float_range(start, stop, step)])
        except ValueError:
            ranges.append([start, stop, step, None])
    tallies = []
    for tally, low, high in (({3: 2, 5: 1}, None, None), ({3: 2, 5: 1}, 0, 7),
                             ({}, None, None), ({4: 3}, 2, 4), ({0: 1, 9: 3}, None, None),
                             ({2: 0, 5: 1, 9: 0}, None, None)):
        counter = Counter(tally)
        tallies.append({"tally": {str(k): v for k, v in tally.items()}, "low": low,
                        "high": high, "mean": sim.counter_mean(counter),
                        "min": sim.counter_min(counter), "max": sim.counter_max(counter),
                        "distribution": [list(x) for x in sim.distribution(counter, low, high)]})
    grids = []
    for jr, mr, th in (((0, 2), (40, 45), [0.0, 10.0]), ((1, 1), (0, 2), [5.0]),
                       ((0, 0), (3, 1), [1.0]), ((2, 2), (44, 50), [0.0])):
        grids.append({"jokers": list(jr), "moves": list(mr), "thresholds": th,
                      "grid": [list(k) for k in sim.sweep_grid(jr, mr, th)]})
    return {
        "z95": sim.Z95, "wilson": wilson, "float_range": ranges, "tallies": tallies,
        "sweep_grid": grids,
        "sweep_games": [[g, c, conf, sim.sweep_games(g, c, conf)]
                        for g, c, conf in ((100, 12, False), (100, 12, True),
                                           (50, 4, True), (7, 30, True))],
        "limits": {"max_configs": sim.MAX_CONFIGS, "confirm_top": sim.CONFIRM_TOP,
                   "confirm_factor": sim.CONFIRM_FACTOR},
    }


BATCHES = ((250, 0, 5, 10.0, 2026), (250, 1, 3, 0.0, 7), (250, 2, 8, 5.0, 4294967290),
           (250, 1, 0, 10.0, 4294967296 + 6))


def _batches() -> Dict[str, Any]:
    runs = []
    for games, jokers, calls, threshold, seed in BATCHES:
        progress = _Progress()
        result = sim.run_batch(games, jokers, calls, threshold, seed=seed, progress=progress)
        runs.append({"games": games, "jokers": jokers, "calls": calls,
                     "threshold": threshold, "seed": seed, "result": _batch(result),
                     "progress": progress.record()})
    progress = _Progress()
    stopped = sim.run_batch(250, 0, 5, 10.0, seed=5, progress=progress,
                            should_stop=_StopAfter(37))
    errors = []
    for games, jokers, calls in ((0, 0, 5), (-3, 0, 5), (10, 3, 5), (10, 0, 44)):
        try:
            sim.run_batch(games, jokers, calls, 10.0, seed=1)
            ok = True
        except ValueError:
            ok = False
        errors.append([games, jokers, calls, ok])
    return {"runs": runs,
            "stopped": {"games": 250, "jokers": 0, "calls": 5, "threshold": 10.0,
                        "seed": 5, "stop_after_checks": 37, "result": _batch(stopped),
                        "progress": progress.record()},
            "errors": errors}


def _sweep(sweep: sim.SweepResult) -> Dict[str, Any]:
    def keys(results) -> list:
        return [_config(r) for r in results]

    def sorted_keys(key_set) -> list:
        return [list(k) for k in sorted(key_set)]

    best = sweep.best
    return {
        "planned": sweep.planned, "stopped": sweep.stopped, "seed": sweep.seed,
        "games_per_test": sweep.games_per_test,
        "results": [_batch(r) for r in sweep.results.values()],
        "ranked": keys(sweep.ranked()),
        "confirmed": [_batch(r) for r in sweep.confirmed.values()],
        "ranked_confirmed": keys(sweep.ranked_confirmed()),
        "best": None if best is None else _config(best),
        "tied": sorted_keys(sweep.tied()),
        "tied_confirmed": sorted_keys(sweep.tied_confirmed()),
        "best_by": {p: [[g, _config(r)] for g, r in sweep.best_by(p).items()]
                    for p in ("jokers", "moves", "threshold")},
        "top_by": {p: [[g, keys(rs)] for g, rs in sweep.top_by(p, 2).items()]
                   for p in ("jokers", "moves", "threshold")},
        "best_curves": {f"{x}_by_{by}": [[g, keys(rs)] for g, rs in
                                         sim.best_curves(sweep.ranked(), x, by).items()]
                        for x, by in (("threshold", "jokers"), ("moves", "jokers"),
                                      ("jokers", "threshold"))},
    }


def _sweeps() -> Dict[str, Any]:
    # 0, 2.5 and 10 sort differently as text ("0", "10", "2.5"), so a port
    # that sorts its results as text instead of as numbers fails.
    grid_a = sim.sweep_grid((0, 1), (0, 2), [0.0, 2.5, 10.0])
    grid_b = sim.sweep_grid((1, 2), (2, 3), [5.0])
    # grid_b with 20 games: 80 one-game chunks, then the confirmation's
    # 4 x 100. Stop on check 331 lands after two re-runs have finished, so
    # the half-finished confirmation must be thrown away.
    runs = []
    for games, grid, seed, confirm, stop in ((30, grid_a, 11, False, None),
                                             (20, grid_b, 4294967290, True, None),
                                             (20, grid_a, 3, False, 50),
                                             (20, grid_b, 9, True, 330)):
        progress = _Progress()
        sweep = sim.run_sweep(games, grid, seed=seed, progress=progress, confirm=confirm,
                              should_stop=None if stop is None else _StopAfter(stop))
        runs.append({"games_per_test": games, "grid": [list(k) for k in grid],
                     "seed": seed, "confirm": confirm, "stop_after_checks": stop,
                     "sweep": _sweep(sweep), "progress": progress.record()})
    errors = []
    for games, grid in ((0, grid_a), (5, [(0, 0, 0.0)] * (sim.MAX_CONFIGS + 1)),
                        (5, [(0, 44, 0.0)]), (5, [(3, 0, 0.0)])):
        try:
            sim.run_sweep(games, grid, seed=1)
            ok = True
        except ValueError:
            ok = False
        errors.append({"games_per_test": games, "configs": len(grid),
                       "first": list(grid[0]), "ok": ok})
    return {"runs": runs, "errors": errors}


# --------------------------------------------------------------------------- #
# Putting it together
# --------------------------------------------------------------------------- #

def build() -> Dict[str, Any]:
    return {
        "about": ("Known answers from the Python engine (python/btb/vectors.py). "
                  "The TypeScript engine must give the same ones. Do not edit by "
                  "hand: run python -m btb.vectors from the python folder."),
        "format": VECTOR_FORMAT,
        "rng": _rng(),
        "decks": _decks(),
        "cards": _cards(),
        "parse": _parse(),
        "calls": _calls(),
        "offers": _offers(),
        "odds": _odds(),
        "counts": _counts(),
        "settings": _settings(),
        "games": _games(),
        "strategy": _strategy(),
        "stats": _stats(),
        "batches": _batches(),
        "sweeps": _sweeps(),
    }


def _format(value: Any, indent: int) -> str:
    """JSON that diffs well: short values on one line, longer lists and
    objects one item per line, lists of plain values always on one line."""
    flat = json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
    if not isinstance(value, (list, dict)) or not value or len(flat) + indent <= 100:
        return flat
    if isinstance(value, list) and all(not isinstance(v, (list, dict)) for v in value):
        return flat
    pad = " " * (indent + 1)
    if isinstance(value, list):
        items = [pad + _format(v, indent + 1) for v in value]
        return "[\n" + ",\n".join(items) + "\n" + " " * indent + "]"
    items = [f"{pad}{json.dumps(k, ensure_ascii=False)}: {_format(v, indent + 1)}"
             for k, v in value.items()]
    return "{\n" + ",\n".join(items) + "\n" + " " * indent + "}"


def render(data: Optional[Dict[str, Any]] = None) -> str:
    return _format(build() if data is None else data, 0) + "\n"


def write(path: Path = VECTORS_PATH) -> int:
    text = render()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return len(text.encode("utf-8"))


if __name__ == "__main__":
    size = write()
    print(f"Wrote {VECTORS_PATH} ({size / 1024:.0f} KB)")