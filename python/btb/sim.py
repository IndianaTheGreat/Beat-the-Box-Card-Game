"""
==============================================
BATCH SIMULATION AND SWEEPS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/sim.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Replaces the simulation loops in BTBSimulator.py and
  BTBOptimizer.py.
- Progress callback and stop check, so the GUIs can run it on a thread.
- Sweeps count only legal combinations, so progress ends at 100%.
- Best configuration is reported even when every win rate is 0%.
- float_range replaces numpy.arange (numpy is no longer needed).

DESCRIPTION:
-----------
Runs many games with the threshold policy (run_batch) or a grid of
settings (run_sweep) and collects the statistics the windows display.
No GUI code.

DEPENDENCIES:
------------
- btb.engine, btb.strategy
- Standard library: collections, dataclasses, typing

KEY FUNCTIONS:
-------------
- run_batch(games, jokers, inclusive_calls, threshold, seed, progress,
  should_stop) -> BatchResult
- sweep_grid(joker_range, moves_range, thresholds) -> legal combinations
- run_sweep(games_per_test, grid, seed, progress, should_stop) -> SweepResult
- float_range(start, stop, step) -> inclusive list of floats

ERROR HANDLING:
--------------
Bad settings raise ValueError (games <= 0, step <= 0, inclusive calls over
the limit). A stopped sweep keeps only finished configurations, since a
partial batch would skew the ranking.

NOTES:
-----
- With a seed, game i uses seed + i, so every configuration in a sweep
  plays the same deals and the comparison is fair.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from .engine import Game, max_inclusive_calls, validate_settings
from .strategy import ThresholdPolicy, play_out

ProgressFn = Optional[Callable[[int, int], None]]
StopFn = Optional[Callable[[], bool]]


@dataclass
class BatchResult:
    jokers: int
    inclusive_calls: int
    threshold: float
    games: int = 0
    wins: int = 0
    boxes_left_in_wins: Counter = field(default_factory=Counter)
    cards_left_in_losses: Counter = field(default_factory=Counter)
    plays: List[int] = field(default_factory=list)
    inclusive_used: List[int] = field(default_factory=list)
    jokers_drawn: List[int] = field(default_factory=list)
    recoveries: List[int] = field(default_factory=list)
    stopped: bool = False

    @property
    def losses(self) -> int:
        return self.games - self.wins

    @property
    def win_rate(self) -> float:
        """Percent of games won; 0.0 when no games were played."""
        return 100.0 * self.wins / self.games if self.games else 0.0

    def add(self, game: Game) -> None:
        self.games += 1
        if game.won:
            self.wins += 1
            self.boxes_left_in_wins[game.boxes_left] += 1
        else:
            self.cards_left_in_losses[game.cards_left] += 1
        self.plays.append(game.stats["plays"])
        self.inclusive_used.append(game.stats["inclusive_used"])
        self.jokers_drawn.append(game.stats["jokers_drawn"])
        self.recoveries.append(game.stats["recoveries"])


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def counter_mean(counter: Counter) -> float:
    n = sum(counter.values())
    return sum(k * v for k, v in counter.items()) / n if n else 0.0


def run_batch(games: int, jokers: int, inclusive_calls: int, threshold: float,
              seed: Optional[int] = None, progress: ProgressFn = None,
              should_stop: StopFn = None) -> BatchResult:
    """Play `games` games with the threshold policy.

    With a seed, game i uses seed + i, so a batch is fully reproducible.
    """
    if games <= 0:
        raise ValueError("games must be positive")
    validate_settings(jokers, inclusive_calls)
    policy = ThresholdPolicy(threshold)
    result = BatchResult(jokers, inclusive_calls, threshold)
    step = max(1, games // 200)
    for i in range(games):
        if should_stop and should_stop():
            result.stopped = True
            break
        game_seed = None if seed is None else (seed + i) & 0xFFFFFFFF
        result.add(play_out(Game.new(jokers, inclusive_calls, game_seed), policy))
        if progress and ((i + 1) % step == 0 or i + 1 == games):
            progress(i + 1, games)
    return result


def float_range(start: float, stop: float, step: float) -> List[float]:
    """Inclusive range of floats, free of accumulated rounding error."""
    if step <= 0:
        raise ValueError("step must be greater than 0")
    if stop < start:
        raise ValueError("range end must not be below its start")
    count = int(round((stop - start) / step, 9)) + 1
    return [round(start + i * step, 6) for i in range(count)
            if start + i * step <= stop + 1e-9]


def sweep_grid(joker_range: Tuple[int, int], moves_range: Tuple[int, int],
               thresholds: List[float]) -> List[Tuple[int, int, float]]:
    """Every legal (jokers, inclusive calls, threshold) combination."""
    grid = []
    for jokers in range(joker_range[0], joker_range[1] + 1):
        top = min(moves_range[1], max_inclusive_calls(jokers))
        for moves in range(moves_range[0], top + 1):
            for threshold in thresholds:
                grid.append((jokers, moves, threshold))
    return grid


@dataclass
class SweepResult:
    results: Dict[Tuple[int, int, float], BatchResult] = field(default_factory=dict)
    planned: int = 0
    stopped: bool = False

    def ranked(self) -> List[BatchResult]:
        """Best first. Ties keep the sweep's own order (fewest jokers/moves)."""
        return sorted(self.results.values(), key=lambda r: -r.win_rate)

    @property
    def best(self) -> Optional[BatchResult]:
        """The top configuration, even when every win rate is 0%."""
        ranked = self.ranked()
        return ranked[0] if ranked else None

    def best_by(self, parameter: str) -> Dict[object, BatchResult]:
        """Best result for each value of 'jokers', 'moves' or 'threshold'."""
        attr = {"jokers": "jokers", "moves": "inclusive_calls",
                "threshold": "threshold"}[parameter]
        out: Dict[object, BatchResult] = {}
        for r in self.ranked():
            out.setdefault(getattr(r, attr), r)
        return dict(sorted(out.items()))

    def top_by(self, parameter: str, n: int = 5) -> Dict[object, List[BatchResult]]:
        attr = {"jokers": "jokers", "moves": "inclusive_calls",
                "threshold": "threshold"}[parameter]
        out: Dict[object, List[BatchResult]] = {}
        for r in self.ranked():
            bucket = out.setdefault(getattr(r, attr), [])
            if len(bucket) < n:
                bucket.append(r)
        return dict(sorted(out.items()))


def run_sweep(games_per_test: int, grid: List[Tuple[int, int, float]],
              seed: Optional[int] = None, progress: ProgressFn = None,
              should_stop: StopFn = None) -> SweepResult:
    """Run a batch for every grid point. Progress counts games, not tests,
    so the bar moves smoothly and ends at exactly 100%."""
    sweep = SweepResult(planned=len(grid))
    total = games_per_test * len(grid)
    done_before = 0
    for jokers, moves, threshold in grid:
        if should_stop and should_stop():
            sweep.stopped = True
            break

        def inner(done: int, _total: int, base: int = done_before) -> None:
            if progress:
                progress(base + done, total)

        batch = run_batch(games_per_test, jokers, moves, threshold, seed,
                          inner, should_stop)
        if batch.stopped:  # a partial batch would skew the ranking; drop it
            sweep.stopped = True
            break
        sweep.results[(jokers, moves, threshold)] = batch
        done_before += games_per_test
    return sweep