"""
==============================================
STRATEGY AND SIMULATION TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_strategy_and_sim.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Tests for btb.strategy and btb.sim.

DESCRIPTION:
-----------
Policy choices (thresholds, jokers, recovery pick, scan-order
independence), reproducible seeded batches, progress reaching 100%,
stopping, input validation and all-0% sweeps.

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)
- tkinter and a display for GUI tests only; they skip otherwise

CLI USAGE:
---------
# From the python/ folder
pytest
# Headless Linux, to include the GUI tests
xvfb-run pytest
"""

import pytest

from btb.engine import HIGHER, HIGHER_EQUAL, LOWER, LOWER_EQUAL, Game
from btb.sim import float_range, run_batch, run_sweep, sweep_grid
from btb.strategy import ThresholdPolicy, play_out
from helpers import card, cards, fail, game


# ----------------------------------------------------------------- policy -- #

def test_policy_plays_the_safest_plain_call():
    g = game(["8", "8", "8", "8", "8", "8", "8", "8", "A"], ["2", "3", "4", "Q"])
    move = ThresholdPolicy(threshold=100).choose_move(g)
    assert (move.position, move.call) == (8, LOWER) and move.probability == 1.0


def test_policy_spends_inclusive_only_above_the_threshold():
    # Box 8 against a pile of 2, 8, 9, Q: Higher 50%, Higher/Equal 75%.
    g = game(["8"] * 9, ["2", "8", "9", "Q"], inclusive=1)
    assert ThresholdPolicy(threshold=30).choose_move(g).call == HIGHER
    assert ThresholdPolicy(threshold=20).choose_move(g).call == HIGHER_EQUAL


def test_policy_inclusive_on_box_joker_when_a_box_has_failed():
    g = game(["7", "🃏", "A"], ["2", "3", "4"], inclusive=1)
    fail(g, 0)
    move = ThresholdPolicy(threshold=100).choose_move(g)
    assert (move.position, move.call) == (1, HIGHER_EQUAL)


def test_policy_holds_box_joker_in_reserve_with_nothing_to_recover():
    g = game(["🃏", "A"], ["2", "3"], inclusive=3)
    move = ThresholdPolicy(threshold=0).choose_move(g)
    assert move.position != 0


def test_policy_plays_the_joker_when_it_is_the_last_live_box():
    g = game(["2"] * 8 + ["🃏"], ["2"] * 8 + ["5", "6"])
    for pos in range(8):
        fail(g, pos)
    move = ThresholdPolicy().choose_move(g)
    assert move.position == 8


def test_policy_decision_does_not_depend_on_scan_order():
    # The same cards in reversed box order must lead to the same card being
    # played with the same call (old bug: inclusive moves were compared
    # against a best-so-far that depended on which box was scanned first).
    box = ["5", "9", "7", "J", "4", "8", "6", "10", "3"]
    pile = ["2", "K", "8", "7", "9", "Q", "5", "A"]
    a = game(box, pile, inclusive=2)
    b = Game.from_cards(list(reversed(a.box)), list(a.draw_pile), 2)
    for threshold in (0, 5, 15, 40):
        ma = ThresholdPolicy(threshold).choose_move(a)
        mb = ThresholdPolicy(threshold).choose_move(b)
        assert a.box[ma.position].rank == b.box[mb.position].rank
        assert ma.call == mb.call and ma.probability == mb.probability


def test_policy_recovers_the_most_useful_box_not_the_highest_position():
    g = game(["2", "8", "7", "7"], ["A", "5", "3", "7", "9", "4"], inclusive=1)
    g.play(0, LOWER)       # 2 fails on A
    g.play(1, HIGHER)      # 8 fails on 5
    g.play(3, HIGHER)      # 7 fails on 3
    r = g.play(2, LOWER_EQUAL)  # 7 on 7: recovery
    assert r.recovery_pending
    assert ThresholdPolicy().choose_recovery(g) == 0  # the 2, not box 3's 7


def test_play_out_decides_recovery_after_the_flip():
    g = game(["7", "8"], ["5", "7", "9"], inclusive=1)
    g.play(1, HIGHER)  # 8 fails on a 5
    g.play(0, LOWER_EQUAL)  # exact match
    assert g.recovery_pending
    play_out(g, ThresholdPolicy())
    assert g.is_over and 1 not in g.failed and g.stats["recoveries"] == 1


def test_play_out_finishes_every_game():
    for seed in range(200):
        g = play_out(Game.new(2, 5, seed), ThresholdPolicy(5))
        assert g.is_over and (g.won or g.lost)


# ------------------------------------------------------------- simulation -- #

def test_batch_is_reproducible_with_a_seed():
    a = run_batch(200, 1, 5, 5.0, seed=9)
    b = run_batch(200, 1, 5, 5.0, seed=9)
    assert (a.wins, a.plays) == (b.wins, b.plays)


def test_batch_progress_reaches_100_percent():
    calls = []
    run_batch(333, 0, 3, 5.0, seed=1, progress=lambda d, t: calls.append((d, t)))
    assert calls[-1] == (333, 333)


def test_batch_can_be_stopped():
    seen = []
    result = run_batch(10_000, 0, 3, 5.0, seed=1,
                       progress=lambda d, t: seen.append(d),
                       should_stop=lambda: len(seen) >= 2)
    assert result.stopped and 0 < result.games < 10_000


def test_batch_rejects_bad_settings():
    with pytest.raises(ValueError):
        run_batch(0, 0, 5, 5.0)
    with pytest.raises(ValueError):
        run_batch(10, 0, 44, 5.0)  # 44 > 43 with no jokers


def test_float_range_is_exact_and_inclusive():
    assert float_range(0, 1, 0.1) == [round(i / 10, 6) for i in range(11)]
    assert float_range(2.5, 2.5, 1) == [2.5]


@pytest.mark.parametrize("step", [0, -0.5])
def test_float_range_rejects_non_positive_step(step):
    with pytest.raises(ValueError):
        float_range(0, 10, step)


def test_sweep_grid_skips_illegal_combinations():
    grid = sweep_grid((0, 2), (43, 45), [5.0])
    assert grid == [(0, 43, 5.0), (1, 43, 5.0), (1, 44, 5.0),
                    (2, 43, 5.0), (2, 44, 5.0), (2, 45, 5.0)]


def test_sweep_progress_counts_only_legal_combinations_and_reaches_100():
    grid = sweep_grid((0, 1), (43, 44), [0.0, 5.0])
    calls = []
    sweep = run_sweep(20, grid, seed=3, progress=lambda d, t: calls.append((d, t)))
    assert len(sweep.results) == len(grid) == 6
    assert calls[-1] == (20 * 6, 20 * 6)


def test_sweep_reports_a_best_even_when_every_win_rate_is_zero():
    # With no inclusive calls and few games, 0% everywhere is possible; the
    # old optimizer then had best_params = None and crashed.
    grid = sweep_grid((0, 0), (0, 0), [0.0, 1.0])
    sweep = run_sweep(1, grid, seed=0)
    for r in sweep.results.values():
        r.wins = 0
    assert sweep.best is not None and sweep.best.win_rate == 0.0
    assert set(sweep.best_by("threshold")) == {0.0, 1.0}


def test_sweep_stop_keeps_only_finished_configurations():
    grid = sweep_grid((0, 0), (0, 5), [5.0])
    seen = []
    sweep = run_sweep(50, grid, seed=1, progress=lambda d, t: seen.append(d),
                      should_stop=lambda: bool(seen) and seen[-1] >= 120)
    assert sweep.stopped
    assert all(r.games == 50 for r in sweep.results.values())
    assert 0 < len(sweep.results) < len(grid)