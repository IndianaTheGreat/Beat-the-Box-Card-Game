"""
==============================================
SIMULATOR AND OPTIMIZER EXPORTS
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/export.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 218 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Saves Simulator and Optimizer results as CSV (for Excel) or JSON
  (complete, with the settings and seed so a run can be repeated).

DESCRIPTION:
-----------
Turns a BatchResult (Simulator) or SweepResult (Optimizer) into plain
data, then writes it as CSV or JSON. No GUI code.

  Simulator CSV  - one table with columns section, item, value: the
                   settings, the summary, then each distribution (boxes
                   left in wins, cards left in losses, plays, ...).
  Optimizer CSV  - one row per configuration, with the win rate, its 95%
                   range, whether it is tied for best, and the averages.
                   Confirmation runs are extra rows with phase "confirm".
  JSON (both)    - the same data in one file, plus the suite version and
                   the export time.

DEPENDENCIES:
------------
- btb (suite version), btb.sim
- Standard library: csv, json, datetime, pathlib

KEY FUNCTIONS:
-------------
- batch_data(result) / sweep_data(sweep) -> dict (the JSON content)
- batch_rows(result) / sweep_rows(sweep) -> list of rows (the CSV content)
- export(result_or_sweep, path) -> writes .csv or .json by file extension

ERROR HANDLING:
--------------
An unknown file extension raises ValueError. File errors (no permission,
disk full) raise OSError for the window to show.

NOTES:
-----
- CSV files are written as UTF-8 with a byte-order mark so Excel opens them
  correctly. Win rates are percentages (25.6 means 25.6%).
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Union

from . import __version__
from .sim import (
    BatchResult, SweepResult, counter_max, counter_mean, counter_min,
)

DISTRIBUTIONS = (
    ("boxes_left_in_wins", "Boxes left in wins"),
    ("cards_left_in_losses", "Cards left in losses"),
    ("plays", "Plays per game"),
    ("inclusive_used", "Inclusive calls used"),
    ("recoveries", "Recoveries per game"),
    ("jokers_drawn", "Jokers drawn"),
)

SWEEP_COLUMNS = (
    "phase", "rank", "jokers", "inclusive_calls", "threshold", "games", "wins",
    "win_rate", "margin_low", "margin_high", "tied_for_best",
    "avg_boxes_left_in_wins", "avg_plays", "avg_inclusive_used",
    "avg_recoveries", "seed",
)


def _r(value: float, places: int = 4) -> float:
    return round(value, places)


def _settings(result: BatchResult) -> Dict[str, object]:
    return {"jokers": result.jokers, "inclusive_calls": result.inclusive_calls,
            "threshold": result.threshold, "games": result.games,
            "seed": result.seed}


def _summary(result: BatchResult) -> Dict[str, object]:
    low, high = result.margin
    return {
        "games": result.games,
        "wins": result.wins,
        "losses": result.losses,
        "win_rate": _r(result.win_rate),
        "margin_low": _r(low),
        "margin_high": _r(high),
        "stopped_early": result.stopped,
        "avg_boxes_left_in_wins": _r(counter_mean(result.boxes_left_in_wins)),
        "avg_cards_left_in_losses": _r(counter_mean(result.cards_left_in_losses)),
        "avg_plays": _r(counter_mean(result.plays)),
        "min_plays": counter_min(result.plays),
        "max_plays": counter_max(result.plays),
        "avg_inclusive_used": _r(counter_mean(result.inclusive_used)),
        "avg_recoveries": _r(counter_mean(result.recoveries)),
        "avg_jokers_drawn": _r(counter_mean(result.jokers_drawn)),
    }


def _header(tool: str) -> Dict[str, object]:
    return {"tool": tool, "suite_version": __version__,
            "exported": datetime.now(timezone.utc).isoformat(timespec="seconds")}


# ------------------------------------------------------------- Simulator -- #

def batch_data(result: BatchResult) -> Dict[str, object]:
    data = _header("Simulator")
    data["settings"] = _settings(result)
    data["summary"] = _summary(result)
    data["distributions"] = {
        name: {str(k): v for k, v in sorted(getattr(result, name).items())}
        for name, _label in DISTRIBUTIONS}
    return data


def batch_rows(result: BatchResult) -> List[list]:
    rows: List[list] = [["section", "item", "value"]]
    rows += [["settings", k, v] for k, v in _settings(result).items()]
    rows += [["summary", k, v] for k, v in _summary(result).items()]
    for name, _label in DISTRIBUTIONS:
        rows += [[name, k, v] for k, v in sorted(getattr(result, name).items())]
    return rows


# ------------------------------------------------------------- Optimizer -- #

def _sweep_records(sweep: SweepResult) -> List[Dict[str, object]]:
    records = []
    for phase, ranked, tied in (("sweep", sweep.ranked(), sweep.tied()),
                                ("confirm", sweep.ranked_confirmed(),
                                 sweep.tied_confirmed())):
        for rank, r in enumerate(ranked, start=1):
            low, high = r.margin
            records.append({
                "phase": phase, "rank": rank, "jokers": r.jokers,
                "inclusive_calls": r.inclusive_calls, "threshold": r.threshold,
                "games": r.games, "wins": r.wins, "win_rate": _r(r.win_rate),
                "margin_low": _r(low), "margin_high": _r(high),
                "tied_for_best": r.key in tied,
                "avg_boxes_left_in_wins": _r(counter_mean(r.boxes_left_in_wins)),
                "avg_plays": _r(counter_mean(r.plays)),
                "avg_inclusive_used": _r(counter_mean(r.inclusive_used)),
                "avg_recoveries": _r(counter_mean(r.recoveries)),
                "seed": r.seed,
            })
    return records


def sweep_data(sweep: SweepResult) -> Dict[str, object]:
    data = _header("Optimizer")
    best = sweep.best
    data["settings"] = {"games_per_test": sweep.games_per_test, "seed": sweep.seed,
                        "configurations": sweep.planned,
                        "confirmed_top": len(sweep.confirmed),
                        "stopped_early": sweep.stopped}
    data["best"] = None if best is None else {
        "jokers": best.jokers, "inclusive_calls": best.inclusive_calls,
        "threshold": best.threshold, "win_rate": _r(best.win_rate),
        "margin_low": _r(best.margin[0]), "margin_high": _r(best.margin[1]),
        "games": best.games}
    data["results"] = _sweep_records(sweep)
    return data


def sweep_rows(sweep: SweepResult) -> List[list]:
    rows: List[list] = [list(SWEEP_COLUMNS)]
    rows += [[rec[c] for c in SWEEP_COLUMNS] for rec in _sweep_records(sweep)]
    return rows


# ---------------------------------------------------------------- writing -- #

def export(result: Union[BatchResult, SweepResult], path: Union[str, Path]) -> Path:
    """Write `result` to `path`; the extension (.csv or .json) picks the format."""
    path = Path(path)
    suffix = path.suffix.lower()
    is_sweep = isinstance(result, SweepResult)
    if suffix == ".json":
        data = sweep_data(result) if is_sweep else batch_data(result)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    elif suffix == ".csv":
        rows = sweep_rows(result) if is_sweep else batch_rows(result)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerows(rows)
    else:
        raise ValueError("choose a .csv or .json file name")
    return path