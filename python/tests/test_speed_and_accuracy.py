"""
==============================================
SIMULATOR SPEED AND ACCURACY TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_speed_and_accuracy.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 218 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Proves the faster simulator gives the same answers: the lean
  strategy matches the original one move for move, parallel runs match
  single-process runs, and tallies match plain averages. Also covers the
  margin of error, ties, the confirm phase (including its seeds and Stop
  during it), Stop in parallel runs, the fallback when helper processes
  fail, and the sweep size limit.

DESCRIPTION:
-----------
ReferencePolicy below is the strategy.py 1.0 algorithm, kept here word for
word (plus the 1.1 joker rule) as the yardstick for the faster code.

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)

KEY FUNCTIONS:
-------------
- ReferencePolicy -> the original strategy, used as the yardstick
- same(a, b) -> True when two BatchResults hold identical statistics
- SETTINGS -> (jokers, calls, threshold) cases for the move-by-move check

CLI USAGE:
---------
# From the python/ folder
pytest tests/test_speed_and_accuracy.py
"""

import random
from collections import Counter

import pytest

from btb import sim
from btb.engine import (
    CALLS, HIGHER, HIGHER_EQUAL, RANKS, Card, Game, odds_by_rank,
    odds_from_histogram, rank_histogram, standard_deck,
)
from btb.sim import (
    BatchResult, counter_max, counter_mean, counter_min, run_batch, run_sweep,
    sweep_grid, tied_with_best, wilson_interval,
)
from btb.strategy import Move, ThresholdPolicy, play_out


# ------------------------------------------------- reference (v1.0) policy -- #

class ReferencePolicy(ThresholdPolicy):
    """strategy.py 1.0 choose_move, plus the 1.1 joker rule."""

    def choose_move(self, game):
        live = game.live_positions
        if not live or not game.draw_pile or game.recovery_pending:
            return None
        jokers_in_box = [p for p in live if game.box[p].is_joker]
        if jokers_in_box:
            if game.inclusive_left <= 0:                       # 1.1 joker rule
                return Move(jokers_in_box[0], HIGHER, 1.0)
            if game.inclusive_left > 0 and game.failed:
                return Move(jokers_in_box[0], HIGHER_EQUAL, 1.0)
            if len(jokers_in_box) == len(live):
                return Move(jokers_in_box[0], CALLS[0], 1.0)
        hist = rank_histogram(game.draw_pile)
        total = len(game.draw_pile)
        candidates = [(p, odds_from_histogram(game.box[p], hist, total))
                      for p in live if not game.box[p].is_joker]

        def ranked(position, call, probability, odds, inclusive=False):
            rank = game.box[position].rank
            recovery = odds.exact if (inclusive and game.failed) else 0.0
            return (probability, recovery, abs(rank - 8), rank, -position, call, position)

        plain = max(ranked(p, *o.best_plain(), o) for p, o in candidates)
        best = Move(plain[-1], plain[-2], plain[0])
        if game.inclusive_left > 0:
            incl = max(ranked(p, *o.best_inclusive(), o, inclusive=True)
                       for p, o in candidates)
            if (incl[0] - best.probability) * 100 > self.threshold:
                best = Move(incl[-1], incl[-2], incl[0])
        return best


SETTINGS = [(0, 0, 5.0), (1, 5, 10.0), (2, 20, 0.0), (2, 45, 5.0), (0, 10, 2.5),
            (1, 3, 30.0), (2, 1, 10.0)]


@pytest.mark.parametrize("jokers, calls, threshold", SETTINGS)
def test_lean_strategy_matches_the_reference_move_for_move(jokers, calls, threshold):
    fast, ref = ThresholdPolicy(threshold), ReferencePolicy(threshold)
    for seed in range(120):
        a, b = Game.new(jokers, calls, seed), Game.new(jokers, calls, seed)
        while not a.is_over:
            if a.recovery_pending:
                pos = fast.choose_recovery(a)
                assert pos == ref.choose_recovery(b)
                a.recover(pos)
                b.recover(pos)
                continue
            ma, mb = fast.choose_move(a), ref.choose_move(b)
            assert (ma.position, ma.call) == (mb.position, mb.call)
            assert ma.probability == pytest.approx(mb.probability)
            a.play(ma.position, ma.call)
            b.play(mb.position, mb.call)
        assert (a.won, a.boxes_left, a.stats) == (b.won, b.boxes_left, b.stats)


def test_odds_table_matches_single_card_odds():
    rng = random.Random(4)
    for _ in range(400):
        pile = standard_deck(2)
        rng.shuffle(pile)
        pile = pile[:rng.randint(0, 45)]
        hist, total = rank_histogram(pile), len(pile)
        table = odds_by_rank(hist, total)
        for rank in list(RANKS) + [0]:
            target = Card.joker() if rank == 0 else Card(rank, "♠")
            odds = odds_from_histogram(target, hist, total)
            if total == 0:
                assert odds is None and table[rank] is None
            else:
                assert (odds.higher, odds.lower, odds.higher_equal, odds.lower_equal,
                        odds.exact) == table[rank]


# ---------------------------------------------------------------- tallies -- #

def test_tallies_give_the_same_statistics_as_lists():
    values = [random.Random(1).randint(5, 43) for _ in range(500)]
    tally = Counter(values)
    assert counter_mean(tally) == pytest.approx(sum(values) / len(values))
    assert (counter_min(tally), counter_max(tally)) == (min(values), max(values))
    assert counter_mean(Counter()) == 0 and counter_max(Counter()) == 0


def test_batch_memory_does_not_grow_with_games():
    result = run_batch(2000, 1, 5, 10.0, seed=3)
    for name in ("plays", "inclusive_used", "jokers_drawn", "recoveries",
                 "boxes_left_in_wins", "cards_left_in_losses"):
        tally = getattr(result, name)
        assert isinstance(tally, Counter) and len(tally) <= 46
    assert sum(result.plays.values()) == result.games == 2000


def test_a_batch_without_a_seed_records_one_that_repeats_it():
    first = run_batch(150, 0, 5, 10.0)
    again = run_batch(150, 0, 5, 10.0, seed=first.seed)
    assert first.seed is not None and (first.wins, first.plays) == (again.wins, again.plays)


# ------------------------------------------------------- margin of error -- #

def test_wilson_interval_known_values():
    low, high = wilson_interval(50, 100)
    assert (low, high) == (pytest.approx(40.38, abs=0.01), pytest.approx(59.62, abs=0.01))
    low, high = wilson_interval(0, 10)
    assert low == 0.0 and high == pytest.approx(27.75, abs=0.01)
    assert wilson_interval(0, 0) == (0.0, 100.0)


def test_more_games_give_a_narrower_margin():
    small = BatchResult(0, 5, 10.0, games=1000, wins=250)
    big = BatchResult(0, 5, 10.0, games=10000, wins=2500)
    assert big.margin_points < small.margin_points / 3


def test_tied_with_best_uses_overlapping_ranges():
    best = BatchResult(0, 5, 10.0, games=1000, wins=300)
    close = BatchResult(0, 6, 10.0, games=1000, wins=285)
    far = BatchResult(0, 7, 10.0, games=1000, wins=200)
    assert tied_with_best([best, close, far]) == {best.key, close.key}
    assert tied_with_best([]) == set()


# --------------------------------------------------------------- parallel -- #

FIELDS = ("games", "wins", "boxes_left_in_wins", "cards_left_in_losses", "plays",
          "inclusive_used", "jokers_drawn", "recoveries")


def same(a: BatchResult, b: BatchResult) -> bool:
    return all(getattr(a, f) == getattr(b, f) for f in FIELDS)


def test_parallel_batch_equals_single_process(monkeypatch):
    monkeypatch.setattr(sim, "PARALLEL_MIN_GAMES", 0)
    serial = run_batch(900, 1, 5, 10.0, seed=21, workers=1)
    parallel = run_batch(900, 1, 5, 10.0, seed=21, workers=2)
    assert same(serial, parallel)


def test_parallel_sweep_with_confirm_equals_single_process(monkeypatch):
    monkeypatch.setattr(sim, "PARALLEL_MIN_GAMES", 0)
    grid = sweep_grid((0, 1), (0, 2), [5.0, 15.0])
    a = run_sweep(60, grid, seed=8, workers=1, confirm=True)
    b = run_sweep(60, grid, seed=8, workers=2, confirm=True)
    assert list(a.results) == list(b.results) and list(a.confirmed) == list(b.confirmed)
    assert all(same(a.results[k], b.results[k]) for k in a.results)
    assert all(same(a.confirmed[k], b.confirmed[k]) for k in a.confirmed)


def test_confirm_phase_replays_the_top_ten_on_fresh_deals():
    grid = sweep_grid((0, 1), (0, 5), [10.0])
    sweep = run_sweep(40, grid, seed=100, confirm=True)
    top = [r.key for r in sweep.ranked()[:10]]
    assert list(sweep.confirmed) == top
    for key, r in sweep.confirmed.items():
        assert r.seed == 100 + 40                 # the first seed it really played
        fresh = run_batch(40 * sim.CONFIRM_FACTOR, *key, seed=r.seed)
        assert same(r, fresh)
    assert all(r.seed == 100 for r in sweep.results.values())
    assert sweep.best.key == sweep.ranked_confirmed()[0].key


def test_stopping_during_the_confirmation_keeps_the_sweep_winner():
    grid = sweep_grid((0, 1), (0, 5), [10.0])
    seen = []
    sweep_games = 40 * len(grid)
    sweep = run_sweep(40, grid, seed=100, confirm=True,
                      progress=lambda d, t: seen.append(d),
                      should_stop=lambda: bool(seen) and seen[-1] > sweep_games + 300)
    assert sweep.stopped and len(sweep.results) == len(grid)
    assert sweep.confirmed == {}                  # half a confirmation is dropped
    assert sweep.best is sweep.ranked()[0]


def test_parallel_run_can_be_stopped(monkeypatch):
    monkeypatch.setattr(sim, "PARALLEL_MIN_GAMES", 0)
    seen = []
    result = run_batch(60_000, 0, 5, 10.0, seed=1, workers=2,
                       progress=lambda d, t: seen.append(d),
                       should_stop=lambda: bool(seen))
    assert result.stopped and 0 < result.games < 60_000


def test_falls_back_to_this_process_when_helpers_fail(monkeypatch):
    from concurrent.futures.process import BrokenProcessPool

    def broken(tasks, workers, on_chunk, should_stop, finished):
        on_chunk(*sim._play_chunk(tasks[0]))   # one chunk finishes, then the pool dies
        finished.add(0)
        raise BrokenProcessPool("helpers died")

    monkeypatch.setattr(sim, "PARALLEL_MIN_GAMES", 0)
    monkeypatch.setattr(sim, "_execute_parallel", broken)
    rescued = run_batch(700, 2, 4, 10.0, seed=5, workers=3)
    assert same(rescued, run_batch(700, 2, 4, 10.0, seed=5, workers=1))


def test_sweep_refuses_more_than_the_configuration_limit(monkeypatch):
    monkeypatch.setattr(sim, "MAX_CONFIGS", 5)
    with pytest.raises(ValueError):
        run_sweep(1, sweep_grid((0, 0), (0, 5), [0.0]), seed=1)


def test_play_out_on_a_finished_game_is_harmless():
    g = play_out(Game.new(0, 3, 9), ThresholdPolicy())
    assert play_out(g, ThresholdPolicy()) is g and g.is_over