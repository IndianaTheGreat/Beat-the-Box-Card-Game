/*
==============================================
BATCH SIMULATION AND SWEEPS (TYPESCRIPT)
==============================================
File Location: Beat-the-Box-Card-Game/extension/src/sim.ts
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (node --test: 80 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. A port of python/btb/sim.py 1.2: seeded batches and sweeps, 95%
  margins of error, the Optimizer's "confirm top results" re-run,
  stopping, progress, and the chart helpers. Every batch and sweep in
  shared/test_vectors.json comes out the same, win for win.

DESCRIPTION:
-----------
Runs many games with the threshold policy (runBatch) or a grid of
settings (runSweep) and collects what the Simulator and Optimizer pages
show. No page code.

DEPENDENCIES:
------------
- ./engine.ts, ./strategy.ts

KEY FUNCTIONS:
-------------
- runBatch(games, jokers, inclusiveCalls, threshold, options) -> BatchResult
- sweepGrid(jokerRange, movesRange, thresholds) -> legal configurations
- runSweep(gamesPerTest, grid, options) -> SweepResult
- wilsonInterval(wins, games) -> [low %, high %]
- tallyMean / tallyMin / tallyMax -> statistics of a tally
- floatRange(start, stop, step) -> inclusive list of numbers
- distribution(tally, low, high) -> [value, % of the total] for charts
- bestCurves(results, x, by) -> group -> best result at each x value
- playChunk(task), chunkSize(games, workers), makeChunks(...) -> the pieces
  a parallel runner (Web Workers) will reuse

ERROR HANDLING:
--------------
Bad settings throw (RangeError for games <= 0, a bad step, too many
configurations; RulesError for jokers or inclusive calls out of range),
as Python raises ValueError. A stopped sweep keeps only finished
configurations, since a partial batch would skew the ranking.

NOTES:
-----
- With a seed, game i uses seed + i (wrapping at 2^32), so every
  configuration in a sweep plays the same deals and results never depend
  on how the work is split. Confirmation runs use the next block of seeds.
- Work is cut into the same chunks as in Python, so Stop and progress
  land in the same places (the shared vectors check this too).
- This file runs everything on one thread. Running chunks in Web Workers
  (several CPU cores) comes with the Simulator page and gives the same
  results, because merging tallies doesn't depend on order.
- floatRange rounds with toFixed, which can differ from Python's round()
  only on an exact decimal tie (a step like 0.0078125). Real steps never
  hit one.
*/

import { Game, maxInclusiveCalls, newSeed, validateSettings } from "./engine.ts";
import { ThresholdPolicy, playOut } from "./strategy.ts";

export type ProgressFn = (done: number, total: number) => void;
export type StopFn = () => boolean;
/** value -> number of games (Python's Counter). */
export type Tally = Map<number, number>;
/** [jokers, inclusive calls, threshold]. */
export type Config = readonly [number, number, number];
export type Parameter = "jokers" | "moves" | "threshold";

export const Z95 = 1.959963984540054;   // 95% two-sided
export const PARALLEL_MIN_GAMES = 4000;  // below this, helpers cost more than they save
export const MAX_CONFIGS = 5000;         // largest sweep the Optimizer will run
export const CONFIRM_TOP = 10;           // configurations re-run by "confirm"
export const CONFIRM_FACTOR = 5;         // ... with this many times the games

/** Text that identifies a configuration (used as a Map key). */
export function configKey(jokers: number, calls: number, threshold: number): string {
  return `${jokers}|${calls}|${threshold}`;
}

// --------------------------------------------------------------------------- //
// Statistics helpers
// --------------------------------------------------------------------------- //

function bump(tally: Tally, value: number, by: number = 1): void {
  tally.set(value, (tally.get(value) ?? 0) + by);
}

export function tallyTotal(tally: Tally): number {
  let n = 0;
  for (const count of tally.values()) n += count;
  return n;
}

export function tallyMean(tally: Tally): number {
  const n = tallyTotal(tally);
  if (!n) return 0;
  let sum = 0;
  for (const [value, count] of tally) sum += value * count;
  return sum / n;
}

export function tallyMin(tally: Tally): number {
  let low: number | null = null;
  for (const [value, count] of tally) if (count && (low === null || value < low)) low = value;
  return low ?? 0;
}

export function tallyMax(tally: Tally): number {
  let high: number | null = null;
  for (const [value, count] of tally) if (count && (high === null || value > high)) high = value;
  return high ?? 0;
}

/** Every whole value from low to high (default: the smallest and largest
 * seen) with its share of the tally in percent; values never seen get 0,
 * so a chart's bars are evenly spaced. */
export function distribution(tally: Tally, low?: number | null, high?: number | null): [number, number][] {
  const total = tallyTotal(tally);
  if (!total) return [];
  const from = low ?? tallyMin(tally);
  const to = high ?? tallyMax(tally);
  const out: [number, number][] = [];
  for (let value = from; value <= to; value++) out.push([value, 100 * (tally.get(value) ?? 0) / total]);
  return out;
}

/** 95% range for the true win rate, in percent (Wilson score interval).
 * Better than "rate +/- 1.96 x standard error" near 0% and 100%. */
export function wilsonInterval(wins: number, games: number, z: number = Z95): [number, number] {
  if (games <= 0) return [0, 100];
  const p = wins / games;
  const z2 = z * z;
  const denom = 1 + z2 / games;
  const centre = (p + z2 / (2 * games)) / denom;
  const half = z * Math.sqrt(p * (1 - p) / games + z2 / (4 * games * games)) / denom;
  return [100 * Math.max(0, centre - half), 100 * Math.min(1, centre + half)];
}

/** Python's round(x, digits) (they differ only on an exact decimal tie). */
function roundTo(x: number, digits: number): number {
  return Number(x.toFixed(digits));
}

/** Inclusive range of numbers, free of accumulated rounding error. */
export function floatRange(start: number, stop: number, step: number): number[] {
  if (!(step > 0)) throw new RangeError("step must be greater than 0");
  if (stop < start) throw new RangeError("range end must not be below its start");
  const count = Math.trunc(roundTo((stop - start) / step, 9)) + 1;
  const out: number[] = [];
  for (let i = 0; i < count; i++) {
    if (start + i * step <= stop + 1e-9) out.push(roundTo(start + i * step, 6));
  }
  return out;
}

/** Every legal [jokers, inclusive calls, threshold] combination. */
export function sweepGrid(jokerRange: readonly [number, number], movesRange: readonly [number, number],
  thresholds: readonly number[]): Config[] {
  const grid: Config[] = [];
  for (let jokers = jokerRange[0]; jokers <= jokerRange[1]; jokers++) {
    const top = Math.min(movesRange[1], maxInclusiveCalls(jokers));
    for (let moves = movesRange[0]; moves <= top; moves++) {
      for (const threshold of thresholds) grid.push([jokers, moves, threshold]);
    }
  }
  return grid;
}

// --------------------------------------------------------------------------- //
// Results
// --------------------------------------------------------------------------- //

/** Totals for many games with one setting. Per-game values are tallies
 * (value -> games), so memory never grows with the number of games. */
export class BatchResult {
  readonly jokers: number;
  readonly inclusiveCalls: number;
  readonly threshold: number;
  games = 0;
  wins = 0;
  boxesLeftInWins: Tally = new Map();
  cardsLeftInLosses: Tally = new Map();
  plays: Tally = new Map();
  inclusiveUsed: Tally = new Map();
  jokersDrawn: Tally = new Map();
  recoveries: Tally = new Map();
  stopped = false;
  seed: number | null;

  constructor(jokers: number, inclusiveCalls: number, threshold: number, seed: number | null = null) {
    this.jokers = jokers;
    this.inclusiveCalls = inclusiveCalls;
    this.threshold = threshold;
    this.seed = seed;
  }

  get key(): string {
    return configKey(this.jokers, this.inclusiveCalls, this.threshold);
  }

  get config(): Config {
    return [this.jokers, this.inclusiveCalls, this.threshold];
  }

  get losses(): number {
    return this.games - this.wins;
  }

  /** Percent of games won; 0 when no games were played. */
  get winRate(): number {
    return this.games ? 100 * this.wins / this.games : 0;
  }

  /** 95% range for the true win rate, in percent. */
  get margin(): [number, number] {
    return wilsonInterval(this.wins, this.games);
  }

  /** Half the width of the 95% range: the "+/-" shown to players. */
  get marginPoints(): number {
    const [low, high] = this.margin;
    return (high - low) / 2;
  }

  add(game: Game): void {
    this.games += 1;
    if (game.won) {
      this.wins += 1;
      bump(this.boxesLeftInWins, game.boxesLeft);
    } else {
      bump(this.cardsLeftInLosses, game.cardsLeft);
    }
    bump(this.plays, game.stats.plays);
    bump(this.inclusiveUsed, game.stats.inclusiveUsed);
    bump(this.jokersDrawn, game.stats.jokersDrawn);
    bump(this.recoveries, game.stats.recoveries);
  }

  /** Add another part of the same batch (order never matters). */
  merge(other: BatchResult): void {
    this.games += other.games;
    this.wins += other.wins;
    for (const name of TALLIES) {
      for (const [value, count] of other[name]) bump(this[name], value, count);
    }
  }
}

const TALLIES = ["boxesLeftInWins", "cardsLeftInLosses", "plays", "inclusiveUsed",
  "jokersDrawn", "recoveries"] as const;

function attribute(result: BatchResult, parameter: Parameter): number {
  switch (parameter) {
    case "jokers": return result.jokers;
    case "moves": return result.inclusiveCalls;
    case "threshold": return result.threshold;
  }
}

function sortedByNumber<T>(map: Map<number, T>): Map<number, T> {
  return new Map([...map].sort((a, b) => a[0] - b[0]));
}

/** Keys of results whose 95% range overlaps the top result's range.
 * `results` must be ranked best first. */
export function tiedWithBest(results: readonly BatchResult[]): Set<string> {
  if (results.length === 0) return new Set();
  const bestLow = results[0]!.margin[0];
  return new Set(results.filter((r) => r.margin[1] >= bestLow).map((r) => r.key));
}

/** For each value of `by`, the best result at each value of `x`, sorted by
 * x. The best is the highest win rate; ties keep the order given. */
export function bestCurves(results: readonly BatchResult[], x: Parameter,
  by: Parameter = "jokers"): Map<number, BatchResult[]> {
  const best = new Map<number, Map<number, BatchResult>>();
  for (const r of results) {
    const group = attribute(r, by);
    let line = best.get(group);
    if (!line) best.set(group, line = new Map());
    const point = attribute(r, x);
    const held = line.get(point);
    if (held === undefined || r.winRate > held.winRate) line.set(point, r);
  }
  const out = new Map<number, BatchResult[]>();
  for (const [group, line] of sortedByNumber(best)) out.set(group, [...sortedByNumber(line).values()]);
  return out;
}

// --------------------------------------------------------------------------- //
// Running games in chunks
// --------------------------------------------------------------------------- //

export interface ChunkTask {
  readonly taskId: number;
  readonly jokers: number;
  readonly calls: number;
  readonly threshold: number;
  readonly firstSeed: number;
  readonly count: number;
}

/** Play one chunk of seeded games (here, or later in a Web Worker). */
export function playChunk(task: ChunkTask): BatchResult {
  const policy = new ThresholdPolicy(task.threshold);
  const part = new BatchResult(task.jokers, task.calls, task.threshold);
  for (let i = 0; i < task.count; i++) {
    part.add(playOut(Game.deal(task.jokers, task.calls, (task.firstSeed + i) >>> 0), policy));
  }
  return part;
}

/** Small chunks keep progress smooth and Stop quick; parallel runs use
 * bigger chunks so each helper spends its time playing, not talking. */
export function chunkSize(games: number, workers: number): number {
  if (workers <= 1) return Math.max(1, Math.min(250, Math.floor(games / 200) || 1));
  return Math.max(200, Math.min(1000, Math.ceil(games / (workers * 16))));
}

export function makeChunks(taskId: number, jokers: number, calls: number, threshold: number,
  seed: number, firstGame: number, games: number, size: number): ChunkTask[] {
  const tasks: ChunkTask[] = [];
  for (let start = 0; start < games; start += size) {
    tasks.push({ taskId, jokers, calls, threshold,
      firstSeed: (seed + firstGame + start) >>> 0, count: Math.min(size, games - start) });
  }
  return tasks;
}

/** Run every task in order. Returns true if it was stopped early. */
function execute(tasks: readonly ChunkTask[], onChunk: (task: ChunkTask, part: BatchResult) => void,
  shouldStop?: StopFn): boolean {
  for (const task of tasks) {
    if (shouldStop?.()) return true;
    onChunk(task, playChunk(task));
  }
  return false;
}

export interface RunOptions {
  /** Same seed, same games. Left out, one is picked and kept in result.seed. */
  seed?: number | null;
  progress?: ProgressFn;
  shouldStop?: StopFn;
}

/** Play `games` games with the threshold policy. Game i uses seed + i. */
export function runBatch(games: number, jokers: number, inclusiveCalls: number, threshold: number,
  options: RunOptions = {}): BatchResult {
  if (!(games > 0)) throw new RangeError("games must be positive");
  validateSettings(jokers, inclusiveCalls);
  const seed = options.seed == null ? newSeed() : options.seed >>> 0;
  const result = new BatchResult(jokers, inclusiveCalls, threshold, seed);
  const tasks = makeChunks(0, jokers, inclusiveCalls, threshold, seed, 0, games, chunkSize(games, 1));
  let done = 0;
  result.stopped = execute(tasks, (_task, part) => {
    result.merge(part);
    done += part.games;
    options.progress?.(done, games);
  }, options.shouldStop);
  return result;
}

// --------------------------------------------------------------------------- //
// Sweeps
// --------------------------------------------------------------------------- //

export class SweepResult {
  /** In grid order, keyed by configKey. */
  results = new Map<string, BatchResult>();
  confirmed = new Map<string, BatchResult>();
  planned: number;
  stopped = false;
  seed: number | null;
  gamesPerTest: number;

  constructor(planned: number = 0, seed: number | null = null, gamesPerTest: number = 0) {
    this.planned = planned;
    this.seed = seed;
    this.gamesPerTest = gamesPerTest;
  }

  /** Best first. Ties keep the sweep's own order (fewest jokers/moves). */
  ranked(): BatchResult[] {
    return [...this.results.values()].sort((a, b) => b.winRate - a.winRate);
  }

  rankedConfirmed(): BatchResult[] {
    return [...this.confirmed.values()].sort((a, b) => b.winRate - a.winRate);
  }

  /** The top configuration, even when every win rate is 0%. When the top
   * results were confirmed, the confirmed winner. */
  get best(): BatchResult | null {
    const confirmed = this.rankedConfirmed();
    const ranked = confirmed.length ? confirmed : this.ranked();
    return ranked[0] ?? null;
  }

  /** Keys statistically tied with the sweep's top result. */
  tied(): Set<string> {
    return tiedWithBest(this.ranked());
  }

  tiedConfirmed(): Set<string> {
    return tiedWithBest(this.rankedConfirmed());
  }

  /** Best result for each value of "jokers", "moves" or "threshold". */
  bestBy(parameter: Parameter): Map<number, BatchResult> {
    const out = new Map<number, BatchResult>();
    for (const r of this.ranked()) {
      const value = attribute(r, parameter);
      if (!out.has(value)) out.set(value, r);
    }
    return sortedByNumber(out);
  }

  topBy(parameter: Parameter, n: number = 5): Map<number, BatchResult[]> {
    const out = new Map<number, BatchResult[]>();
    for (const r of this.ranked()) {
      const value = attribute(r, parameter);
      let bucket = out.get(value);
      if (!bucket) out.set(value, bucket = []);
      if (bucket.length < n) bucket.push(r);
    }
    return sortedByNumber(out);
  }
}

/** Total games a sweep will play (used for progress and the size check). */
export function sweepGames(gamesPerTest: number, configs: number, confirm: boolean): number {
  const extra = confirm ? Math.min(CONFIRM_TOP, configs) * gamesPerTest * CONFIRM_FACTOR : 0;
  return gamesPerTest * configs + extra;
}

export interface SweepOptions extends RunOptions {
  /** Re-run the top results with five times the games on fresh deals. */
  confirm?: boolean;
}

/** Run a batch for every grid point, then (with confirm) re-run the top
 * results on fresh deals. Progress counts games, so it ends at 100%. */
export function runSweep(gamesPerTest: number, grid: readonly Config[],
  options: SweepOptions = {}): SweepResult {
  if (!(gamesPerTest > 0)) throw new RangeError("games per test must be positive");
  if (grid.length > MAX_CONFIGS) {
    throw new RangeError(`that sweep has ${grid.length.toLocaleString("en-US")} configurations; `
      + `the limit is ${MAX_CONFIGS.toLocaleString("en-US")}`);
  }
  for (const [jokers, moves] of grid) validateSettings(jokers, moves);
  const seed = options.seed == null ? newSeed() : options.seed >>> 0;
  const sweep = new SweepResult(grid.length, seed, gamesPerTest);
  const total = sweepGames(gamesPerTest, grid.length, options.confirm ?? false);
  let done = 0;

  const runPhase = (keys: readonly Config[], firstGame: number, games: number) => {
    const firstSeed = (seed + firstGame) >>> 0;
    const parts = keys.map(([j, m, th]) => new BatchResult(j, m, th, firstSeed));
    const size = chunkSize(games, 1);
    const tasks = keys.flatMap(([j, m, th], i) => makeChunks(i, j, m, th, seed, firstGame, games, size));
    const stopped = execute(tasks, (task, part) => {
      parts[task.taskId]!.merge(part);
      done += part.games;
      options.progress?.(done, total);
    }, options.shouldStop);
    // Keep only finished configurations, in grid order: a partial batch
    // would skew the ranking.
    const finished = new Map<string, BatchResult>();
    for (const part of parts) if (part.games === games) finished.set(part.key, part);
    return { finished, stopped };
  };

  const first = runPhase(grid, 0, gamesPerTest);
  sweep.results = first.finished;
  sweep.stopped = first.stopped;
  if (options.confirm && !sweep.stopped && sweep.results.size > 0) {
    const top = sweep.ranked().slice(0, CONFIRM_TOP).map((r) => r.config);
    // Fresh deals: the block of seeds right after the ones already used.
    const second = runPhase(top, gamesPerTest, gamesPerTest * CONFIRM_FACTOR);
    sweep.stopped = second.stopped;
    // A half-finished confirmation would pick a winner from a few re-runs;
    // keep it only when every top configuration was re-run.
    sweep.confirmed = second.stopped ? new Map() : second.finished;
  }
  return sweep;
}