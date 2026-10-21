/*
==============================================
SIMULATION TESTS (TYPESCRIPT)
==============================================
File Location: Beat-the-Box-Card-Game/extension/tests/sim.test.ts
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (node --test: 80 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Checks src/sim.ts against the batches, sweeps (with confirm and
  with Stop), margins of error and chart helpers in
  shared/test_vectors.json, and that a strategy-guide cell comes out the
  same.

DESCRIPTION:
-----------
Same seeds, same games, same wins: the Chrome Simulator and Optimizer
report exactly what the Python ones report.

DEPENDENCIES:
------------
- ../src/sim.ts, ./vectors.ts
- Node built-ins: node:test, node:assert/strict

CLI USAGE:
---------
From the extension folder:

    node --test tests/sim.test.ts
*/

import assert from "node:assert/strict";
import { describe, test } from "node:test";

import {
  BatchResult, CONFIRM_FACTOR, CONFIRM_TOP, MAX_CONFIGS, SweepResult, Z95, bestCurves,
  distribution, floatRange, runBatch, runSweep, sweepGames, sweepGrid, tallyMax, tallyMean,
  tallyMin, wilsonInterval,
} from "../src/sim.ts";
import type { Config, Parameter, Tally } from "../src/sim.ts";
import { VECTORS, batchOf, progressRecorder, stopAfter } from "./vectors.ts";
import type { Json } from "./vectors.ts";

const PARAMETERS: Parameter[] = ["jokers", "moves", "threshold"];

function batch(r: BatchResult): Json {
  return batchOf(r, tallyMean(r.plays), tallyMin(r.plays), tallyMax(r.plays));
}

function tally(object: Record<string, number>): Tally {
  return new Map(Object.entries(object).map(([k, v]) => [Number(k), v]));
}

function sortedConfigs(keys: Set<string>, results: Map<string, BatchResult>): Config[] {
  const configs = [...keys].map((k) => results.get(k)!.config);
  return configs.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
}

/** vectors.py _sweep(). */
function sweepOf(s: SweepResult): Json {
  const configs = (rs: BatchResult[]) => rs.map((r) => r.config);
  const best = s.best;
  return {
    planned: s.planned, stopped: s.stopped, seed: s.seed, games_per_test: s.gamesPerTest,
    results: [...s.results.values()].map(batch),
    ranked: configs(s.ranked()),
    confirmed: [...s.confirmed.values()].map(batch),
    ranked_confirmed: configs(s.rankedConfirmed()),
    best: best === null ? null : best.config,
    tied: sortedConfigs(s.tied(), s.results),
    tied_confirmed: sortedConfigs(s.tiedConfirmed(), s.confirmed),
    best_by: Object.fromEntries(PARAMETERS.map((p) =>
      [p, [...s.bestBy(p)].map(([g, r]) => [g, r.config])])),
    top_by: Object.fromEntries(PARAMETERS.map((p) =>
      [p, [...s.topBy(p, 2)].map(([g, rs]) => [g, configs(rs)])])),
    best_curves: Object.fromEntries(([["threshold", "jokers"], ["moves", "jokers"], ["jokers", "threshold"]] as const)
      .map(([x, by]) => [`${x}_by_${by}`, [...bestCurves(s.ranked(), x, by)].map(([g, rs]) => [g, configs(rs)])])),
  };
}

describe("statistics helpers", () => {
  const S = VECTORS.stats;

  test("margins of error (Wilson interval)", () => {
    assert.equal(Z95, S.z95);
    for (const [wins, games, range] of S.wilson) assert.deepEqual(wilsonInterval(wins, games), range);
  });

  test("threshold ranges", () => {
    for (const [start, stop, step, expected] of S.float_range) {
      if (expected === null) assert.throws(() => floatRange(start, stop, step), RangeError);
      else assert.deepEqual(floatRange(start, stop, step), expected, `${start}..${stop} by ${step}`);
    }
  });

  test("tallies: mean, min, max and chart distribution", () => {
    for (const row of S.tallies) {
      const t = tally(row.tally);
      assert.equal(tallyMean(t), row.mean);
      assert.equal(tallyMin(t), row.min);
      assert.equal(tallyMax(t), row.max);
      assert.deepEqual(distribution(t, row.low, row.high), row.distribution);
    }
  });

  test("sweep grids, sizes and limits", () => {
    for (const row of S.sweep_grid) {
      assert.deepEqual(sweepGrid(row.jokers, row.moves, row.thresholds), row.grid);
    }
    for (const [games, configs, confirm, total] of S.sweep_games) {
      assert.equal(sweepGames(games, configs, confirm), total);
    }
    assert.deepEqual({ max_configs: MAX_CONFIGS, confirm_top: CONFIRM_TOP, confirm_factor: CONFIRM_FACTOR },
      S.limits);
  });
});

describe("batches", () => {
  const B = VECTORS.batches;

  for (const run of B.runs) {
    test(`${run.games} games: ${run.jokers} jokers, ${run.calls} calls, threshold ${run.threshold}, seed ${run.seed}`, () => {
      const progress = progressRecorder();
      const result = runBatch(run.games, run.jokers, run.calls, run.threshold,
        { seed: run.seed, progress: progress.fn });
      assert.deepEqual(batch(result), run.result);
      assert.deepEqual(progress.record(), run.progress);
    });
  }

  test("Stop ends a batch at the same game", () => {
    const s = B.stopped;
    const progress = progressRecorder();
    const result = runBatch(s.games, s.jokers, s.calls, s.threshold,
      { seed: s.seed, progress: progress.fn, shouldStop: stopAfter(s.stop_after_checks) });
    assert.deepEqual(batch(result), s.result);
    assert.deepEqual(progress.record(), s.progress);
  });

  test("bad batch settings are refused", () => {
    for (const [games, jokers, calls, ok] of B.errors) {
      const run = () => runBatch(games, jokers, calls, 10, { seed: 1 });
      if (ok) run();
      else assert.throws(run);
    }
  });

  test("a strategy guide cell: 0 jokers, 5 calls, threshold 10, seed 2026", () => {
    // docs/STRATEGY.md: 27.2% over 5,000 games (1,358 wins in Python).
    const result = runBatch(5000, 0, 5, 10, { seed: 2026 });
    assert.equal(result.wins, 1358);
    assert.equal(result.winRate.toFixed(1), "27.2");
  });
});

describe("sweeps", () => {
  const W = VECTORS.sweeps;

  for (const run of W.runs) {
    const label = `${run.grid.length} configurations x ${run.games_per_test} games, seed ${run.seed}`
      + (run.confirm ? ", confirmed" : "") + (run.stop_after_checks === null ? "" : ", stopped");
    test(label, () => {
      const progress = progressRecorder();
      const sweep = runSweep(run.games_per_test, run.grid, {
        seed: run.seed, confirm: run.confirm, progress: progress.fn,
        shouldStop: run.stop_after_checks === null ? undefined : stopAfter(run.stop_after_checks),
      });
      assert.deepEqual(sweepOf(sweep), run.sweep);
      assert.deepEqual(progress.record(), run.progress);
    });
  }

  test("bad sweeps are refused", () => {
    for (const row of W.errors) {
      const grid: Config[] = Array.from({ length: row.configs }, () => row.first);
      const run = () => runSweep(row.games_per_test, grid, { seed: 1 });
      if (row.ok) run();
      else assert.throws(run);
    }
  });
});