"""
==============================================
BATCH SIMULATION AND SWEEPS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/sim.py
Status: ACTIVE
Version: 1.2
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.2 CHANGES (2026-10-20):
- New chart helpers, still with no GUI code: distribution(counter, low,
  high) gives every value in a range with its share (missing values as
  0%), and best_curves(results, x, by) gives, for each joker count, the
  best configuration at each threshold (or inclusive-call count). The
  Advanced tabs draw their charts from these.

VERSION 1.1 CHANGES (2026-10-20):
- Memory: per-game lists replaced by tallies (Counter), so a run of ten
  million games uses the same memory as a run of a thousand.
- Accuracy: every result carries a 95% margin of error (Wilson
  interval). SweepResult marks configurations that are statistically tied
  with the best.
- Speed: optional parallel runs on several CPU cores (workers=). Work is
  split into chunks of seeded games, so results are identical however
  the work is split. If helper processes can't start, the run finishes
  in this process instead of failing.
- Optimizer "confirm top results": re-runs the top 10 with 5x more games
  on fresh deals, so a lucky winner gets caught.
- Limits: at most MAX_CONFIGS configurations per sweep.
- A run without a seed now picks one and records it (result.seed), so
  every run can be repeated. Confirmation results record the first seed
  they actually played (seed + games per test).
- Stopping during the confirmation drops the unfinished confirmation, so
  the sweep's own ranking stands instead of a winner picked from a few
  re-runs.

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
- btb.engine, btb.strategy, btb.system
- Standard library: collections, concurrent.futures, dataclasses, math,
  multiprocessing, typing

KEY FUNCTIONS:
-------------
- run_batch(games, jokers, inclusive_calls, threshold, seed, progress,
  should_stop, workers) -> BatchResult
- sweep_grid(joker_range, moves_range, thresholds) -> legal combinations
- run_sweep(games_per_test, grid, seed, progress, should_stop, workers,
  confirm) -> SweepResult
- wilson_interval(wins, games) -> (low %, high %)
- counter_mean / counter_min / counter_max -> statistics of a tally
- float_range(start, stop, step) -> inclusive list of floats
- distribution(counter, low, high) -> [(value, % of the total)] for charts
- best_curves(results, x, by) -> {group: [best result at each x value]}

ERROR HANDLING:
--------------
Bad settings raise ValueError (games <= 0, step <= 0, inclusive calls over
the limit, too many configurations). A stopped sweep keeps only finished
configurations, since a partial batch would skew the ranking. A crashed
helper pool falls back to running the remaining chunks here.

NOTES:
-----
- With a seed, game i uses seed + i, so every configuration in a sweep
  plays the same deals and the comparison is fair. Confirmation runs use
  the next block of seeds (fresh deals).
- Parallel runs use the "spawn" start method on every platform: it is the
  only one Windows has, and it is safe with Tk and threads.
- Small runs (under PARALLEL_MIN_GAMES) stay in this process, because
  starting helper processes costs about a second on Windows.
"""

from __future__ import annotations

import math
import multiprocessing
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .engine import Game, max_inclusive_calls, new_seed, validate_settings
from .strategy import ThresholdPolicy, play_out
from .system import lower_priority

ProgressFn = Optional[Callable[[int, int], None]]
StopFn = Optional[Callable[[], bool]]
Key = Tuple[int, int, float]

SEED_MASK = 0xFFFFFFFF
Z95 = 1.959963984540054          # 95% two-sided
PARALLEL_MIN_GAMES = 4000         # below this, helpers cost more than they save
MAX_CONFIGS = 5000                # largest sweep the optimizer will run
CONFIRM_TOP = 10                  # configurations re-run by "confirm"
CONFIRM_FACTOR = 5                # ... with this many times the games


# --------------------------------------------------------------------------- #
# Statistics helpers
# --------------------------------------------------------------------------- #

def counter_mean(counter: Counter) -> float:
    n = sum(counter.values())
    return sum(k * v for k, v in counter.items()) / n if n else 0.0


def counter_min(counter: Counter) -> int:
    return min((k for k, v in counter.items() if v), default=0)


def counter_max(counter: Counter) -> int:
    return max((k for k, v in counter.items() if v), default=0)


def distribution(counter: Counter, low: Optional[int] = None,
                 high: Optional[int] = None) -> List[Tuple[int, float]]:
    """Every whole value from low to high (default: the smallest and largest
    seen) with its share of the tally in percent; values never seen get
    0.0, so a chart's bars are evenly spaced."""
    total = sum(counter.values())
    if not total:
        return []
    low = counter_min(counter) if low is None else low
    high = counter_max(counter) if high is None else high
    return [(value, 100.0 * counter.get(value, 0) / total) for value in range(low, high + 1)]


_ATTRIBUTES = {"jokers": "jokers", "moves": "inclusive_calls", "threshold": "threshold"}


def best_curves(results: Sequence["BatchResult"], x: str,
                by: str = "jokers") -> Dict[object, List["BatchResult"]]:
    """For each value of `by`, the best result at each value of `x`
    ("jokers", "moves" or "threshold"), sorted by x. The best is the highest
    win rate; ties keep the order given (the sweep's own order)."""
    x_attr, by_attr = _ATTRIBUTES[x], _ATTRIBUTES[by]
    best: Dict[object, Dict[object, BatchResult]] = {}
    for r in results:
        line = best.setdefault(getattr(r, by_attr), {})
        point = getattr(r, x_attr)
        if point not in line or r.win_rate > line[point].win_rate:
            line[point] = r
    return {group: [line[point] for point in sorted(line)]
            for group, line in sorted(best.items())}


def wilson_interval(wins: int, games: int, z: float = Z95) -> Tuple[float, float]:
    """95% range for the true win rate, in percent (Wilson score interval).

    Better than "rate +/- 1.96 x standard error" near 0% and 100%, and never
    goes below 0 or above 100.
    """
    if games <= 0:
        return 0.0, 100.0
    p = wins / games
    z2 = z * z
    denom = 1 + z2 / games
    centre = (p + z2 / (2 * games)) / denom
    half = z * math.sqrt(p * (1 - p) / games + z2 / (4 * games * games)) / denom
    return 100 * max(0.0, centre - half), 100 * min(1.0, centre + half)


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #

@dataclass
class BatchResult:
    """Totals for many games with one setting. Per-game values are kept as
    tallies (value -> number of games), so memory never grows with games."""

    jokers: int
    inclusive_calls: int
    threshold: float
    games: int = 0
    wins: int = 0
    boxes_left_in_wins: Counter = field(default_factory=Counter)
    cards_left_in_losses: Counter = field(default_factory=Counter)
    plays: Counter = field(default_factory=Counter)
    inclusive_used: Counter = field(default_factory=Counter)
    jokers_drawn: Counter = field(default_factory=Counter)
    recoveries: Counter = field(default_factory=Counter)
    stopped: bool = False
    seed: Optional[int] = None

    @property
    def key(self) -> Key:
        return (self.jokers, self.inclusive_calls, self.threshold)

    @property
    def losses(self) -> int:
        return self.games - self.wins

    @property
    def win_rate(self) -> float:
        """Percent of games won; 0.0 when no games were played."""
        return 100.0 * self.wins / self.games if self.games else 0.0

    @property
    def margin(self) -> Tuple[float, float]:
        """95% range for the true win rate, in percent."""
        return wilson_interval(self.wins, self.games)

    @property
    def margin_points(self) -> float:
        """Half the width of the 95% range: the "+/-" shown to players."""
        low, high = self.margin
        return (high - low) / 2

    def add(self, game: Game) -> None:
        self.games += 1
        if game.won:
            self.wins += 1
            self.boxes_left_in_wins[game.boxes_left] += 1
        else:
            self.cards_left_in_losses[game.cards_left] += 1
        stats = game.stats
        self.plays[stats["plays"]] += 1
        self.inclusive_used[stats["inclusive_used"]] += 1
        self.jokers_drawn[stats["jokers_drawn"]] += 1
        self.recoveries[stats["recoveries"]] += 1

    def merge(self, other: "BatchResult") -> None:
        """Add another part of the same batch (order never matters)."""
        self.games += other.games
        self.wins += other.wins
        for name in ("boxes_left_in_wins", "cards_left_in_losses", "plays",
                     "inclusive_used", "jokers_drawn", "recoveries"):
            getattr(self, name).update(getattr(other, name))


def tied_with_best(results: Sequence[BatchResult]) -> set:
    """Keys of results whose 95% range overlaps the top result's range.

    `results` must be ranked best first. These are the configurations the
    data can't tell apart from the winner.
    """
    if not results:
        return set()
    best_low = results[0].margin[0]
    return {r.key for r in results if r.margin[1] >= best_low}


# --------------------------------------------------------------------------- #
# Running games in chunks (here or in helper processes)
# --------------------------------------------------------------------------- #

# (task id, jokers, inclusive calls, threshold, first seed, number of games)
Task = Tuple[int, int, int, float, int, int]


def _play_chunk(task: Task) -> Tuple[int, BatchResult]:
    """Play one chunk of seeded games. Runs in a helper process or here."""
    task_id, jokers, calls, threshold, first_seed, count = task
    policy = ThresholdPolicy(threshold)
    part = BatchResult(jokers, calls, threshold)
    for i in range(count):
        part.add(play_out(Game.new(jokers, calls, (first_seed + i) & SEED_MASK), policy))
    return task_id, part


def _chunk_size(games: int, workers: int) -> int:
    """Small chunks keep progress smooth and Stop quick; in parallel runs
    chunks are bigger so each helper spends its time playing, not talking."""
    if workers <= 1:
        return max(1, min(250, games // 200 or 1))
    return max(200, min(1000, -(-games // (workers * 16))))


def _chunks(task_id: int, jokers: int, calls: int, threshold: float,
            seed: int, first_game: int, games: int, size: int) -> List[Task]:
    return [(task_id, jokers, calls, threshold,
             (seed + first_game + start) & SEED_MASK, min(size, games - start))
            for start in range(0, games, size)]


def _execute(tasks: List[Task], workers: int,
             on_chunk: Callable[[int, BatchResult], None],
             should_stop: StopFn) -> bool:
    """Run every task, calling on_chunk for each finished one.

    Returns True if the run was stopped early. Results don't depend on the
    order chunks finish in, because merging tallies is order-free.
    """
    finished: set = set()
    if workers > 1 and len(tasks) > 1:
        try:
            return _execute_parallel(tasks, workers, on_chunk, should_stop, finished)
        except (BrokenProcessPool, OSError):
            pass  # helpers could not start or died: finish the rest here
    for index, task in enumerate(tasks):
        if index in finished:
            continue
        if should_stop and should_stop():
            return True
        on_chunk(*_play_chunk(task))
    return False


def _execute_parallel(tasks: List[Task], workers: int,
                      on_chunk: Callable[[int, BatchResult], None],
                      should_stop: StopFn, finished: set) -> bool:
    """Parallel part of _execute. Records finished task indexes in
    `finished`, so a broken pool leaves only unfinished work for the
    fallback. At most two chunks per helper are queued at a time, so Stop
    only waits for the chunks already running."""
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context,
                             initializer=lower_priority) as pool:
        pending = {}
        next_index = 0

        def fill() -> None:
            nonlocal next_index
            while next_index < len(tasks) and len(pending) < workers * 2:
                pending[pool.submit(_play_chunk, tasks[next_index])] = next_index
                next_index += 1

        fill()
        while pending:
            if should_stop and should_stop():
                for future in pending:
                    future.cancel()
                return True
            done, _ = wait(list(pending), timeout=0.1, return_when=FIRST_COMPLETED)
            for future in done:
                index = pending.pop(future)
                task_id, part = future.result()
                finished.add(index)
                on_chunk(task_id, part)
            fill()
    return False


# --------------------------------------------------------------------------- #
# Batches
# --------------------------------------------------------------------------- #

def run_batch(games: int, jokers: int, inclusive_calls: int, threshold: float,
              seed: Optional[int] = None, progress: ProgressFn = None,
              should_stop: StopFn = None, workers: int = 1) -> BatchResult:
    """Play `games` games with the threshold policy.

    Game i uses seed + i, so a batch is fully reproducible. Without a seed
    one is picked and stored in result.seed. workers > 1 spreads big runs
    over helper processes; the result is identical either way.
    """
    if games <= 0:
        raise ValueError("games must be positive")
    validate_settings(jokers, inclusive_calls)
    seed = new_seed() if seed is None else seed & SEED_MASK
    result = BatchResult(jokers, inclusive_calls, threshold, seed=seed)
    workers = workers if games >= PARALLEL_MIN_GAMES else 1
    tasks = _chunks(0, jokers, inclusive_calls, threshold, seed, 0, games,
                    _chunk_size(games, workers))
    done = 0

    def on_chunk(_task_id: int, part: BatchResult) -> None:
        nonlocal done
        result.merge(part)
        done += part.games
        if progress:
            progress(done, games)

    result.stopped = _execute(tasks, workers, on_chunk, should_stop)
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
               thresholds: List[float]) -> List[Key]:
    """Every legal (jokers, inclusive calls, threshold) combination."""
    grid = []
    for jokers in range(joker_range[0], joker_range[1] + 1):
        top = min(moves_range[1], max_inclusive_calls(jokers))
        for moves in range(moves_range[0], top + 1):
            for threshold in thresholds:
                grid.append((jokers, moves, threshold))
    return grid


# --------------------------------------------------------------------------- #
# Sweeps
# --------------------------------------------------------------------------- #

@dataclass
class SweepResult:
    results: Dict[Key, BatchResult] = field(default_factory=dict)
    confirmed: Dict[Key, BatchResult] = field(default_factory=dict)
    planned: int = 0
    stopped: bool = False
    seed: Optional[int] = None
    games_per_test: int = 0

    def ranked(self) -> List[BatchResult]:
        """Best first. Ties keep the sweep's own order (fewest jokers/moves)."""
        return sorted(self.results.values(), key=lambda r: -r.win_rate)

    def ranked_confirmed(self) -> List[BatchResult]:
        return sorted(self.confirmed.values(), key=lambda r: -r.win_rate)

    @property
    def best(self) -> Optional[BatchResult]:
        """The top configuration, even when every win rate is 0%. When the
        top results were confirmed, the confirmed winner."""
        ranked = self.ranked_confirmed() or self.ranked()
        return ranked[0] if ranked else None

    def tied(self) -> set:
        """Sweep keys statistically tied with the sweep's top result."""
        return tied_with_best(self.ranked())

    def tied_confirmed(self) -> set:
        return tied_with_best(self.ranked_confirmed())

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


def sweep_games(games_per_test: int, configs: int, confirm: bool) -> int:
    """Total games a sweep will play (used for progress and the size check)."""
    extra = min(CONFIRM_TOP, configs) * games_per_test * CONFIRM_FACTOR if confirm else 0
    return games_per_test * configs + extra


def run_sweep(games_per_test: int, grid: List[Key],
              seed: Optional[int] = None, progress: ProgressFn = None,
              should_stop: StopFn = None, workers: int = 1,
              confirm: bool = False) -> SweepResult:
    """Run a batch for every grid point, then (with confirm) re-run the top
    results on fresh deals. Progress counts games, so the bar moves smoothly
    and ends at exactly 100%."""
    if games_per_test <= 0:
        raise ValueError("games per test must be positive")
    if len(grid) > MAX_CONFIGS:
        raise ValueError(f"that sweep has {len(grid):,} configurations; "
                         f"the limit is {MAX_CONFIGS:,}")
    for jokers, moves, _threshold in grid:
        validate_settings(jokers, moves)
    seed = new_seed() if seed is None else seed & SEED_MASK
    sweep = SweepResult(planned=len(grid), seed=seed, games_per_test=games_per_test)
    total = sweep_games(games_per_test, len(grid), confirm)
    if total < PARALLEL_MIN_GAMES:
        workers = 1
    done = 0

    def run_phase(keys: List[Key], first_game: int, games: int) -> Tuple[Dict[Key, BatchResult], bool]:
        nonlocal done
        first_seed = (seed + first_game) & SEED_MASK
        parts = {i: BatchResult(*key, seed=first_seed) for i, key in enumerate(keys)}
        size = _chunk_size(games, workers)
        tasks = [t for i, (j, m, th) in enumerate(keys)
                 for t in _chunks(i, j, m, th, seed, first_game, games, size)]

        def on_chunk(task_id: int, part: BatchResult) -> None:
            nonlocal done
            parts[task_id].merge(part)
            done += part.games
            if progress:
                progress(done, total)

        stopped = _execute(tasks, workers, on_chunk, should_stop)
        # Keep only finished configurations, in grid order: a partial batch
        # would skew the ranking.
        finished = {keys[i]: parts[i] for i in range(len(keys)) if parts[i].games == games}
        return finished, stopped

    sweep.results, sweep.stopped = run_phase(list(grid), 0, games_per_test)
    if confirm and not sweep.stopped and sweep.results:
        top = [r.key for r in sweep.ranked()[:CONFIRM_TOP]]
        # Fresh deals: the block of seeds right after the ones already used.
        confirmed, sweep.stopped = run_phase(
            top, games_per_test, games_per_test * CONFIRM_FACTOR)
        # A half-finished confirmation would pick a winner from a few re-runs;
        # keep it only when every top configuration was re-run.
        sweep.confirmed = {} if sweep.stopped else confirmed
    return sweep