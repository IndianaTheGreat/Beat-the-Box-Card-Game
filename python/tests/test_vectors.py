"""
==============================================
SHARED TEST VECTOR TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_vectors.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-21
Last Tested: 2026-10-21 (pytest: 314 passed)

VERSION 1.1 CHANGES (2026-10-21):
- New test_vectors_catch_easy_port_mistakes: the vectors must keep a
  sweep whose thresholds sort differently as text than as numbers, a
  sweep stopped after part of its confirmation finished, and a tally with
  zero entries. Without them, those three mistakes in the TypeScript port
  passed every test (found by breaking the port on purpose).
- Header: added KEY FUNCTIONS and CLI USAGE, like the other test files.

VERSION 1.0 CHANGES (2026-10-20):
- New. Checks shared/test_vectors.json still matches this engine, so the
  answers the TypeScript engine is tested against are never stale.

DESCRIPTION:
-----------
The Chrome extension's engine is tested against shared/test_vectors.json
(see btb/vectors.py). If this test fails, the Python engine's answers
have changed: run "python -m btb.vectors" from the python folder to
rewrite the file, then run the extension's tests too.

DEPENDENCIES:
------------
- btb.vectors
- Standard library: functools, json
- pytest

KEY FUNCTIONS:
-------------
- fresh_vectors() -> the vectors as this engine builds them now (cached)

CLI USAGE:
---------
# From the python/ folder
python -m pytest tests/test_vectors.py

NOTES:
-----
- The comparison is on the parsed JSON, so line endings (Git on Windows
  may turn them into CRLF) don't matter.
"""

import functools
import json

from btb import vectors


@functools.cache
def fresh_vectors() -> dict:
    """Built once per test run (it plays about 2,000 games)."""
    return json.loads(vectors.render())


def test_shared_vectors_file_matches_the_engine():
    assert vectors.VECTORS_PATH.exists(), "run: python -m btb.vectors"
    saved = json.loads(vectors.VECTORS_PATH.read_text(encoding="utf-8"))
    fresh = fresh_vectors()
    stale = [name for name in fresh if saved.get(name) != fresh[name]]
    assert not stale, (f"shared/test_vectors.json is out of date in {stale}: "
                       "run python -m btb.vectors from the python folder")


def test_vectors_reach_the_rare_cases():
    """The scripted games must keep covering the cases most likely to differ
    between the two engines."""
    data = fresh_vectors()
    games = data["games"]
    every = games["dealt"] + games["assistant"] + games["built"]
    plays = [step["value"] for game in every for step in game["steps"]
             if step["do"] == "play" and not step.get("error")]
    assert any(p["recovery_pending"] and p["won"] for p in plays)  # earned on the last card
    assert any(p["recovery_lost"] for p in plays)
    assert any(p["drawn"].startswith("🃏") for p in plays)
    assert any(p["target"].startswith("🃏") for p in plays)
    assert any(p["won"] for p in plays) and any(p["game_over"] and not p["won"] for p in plays)
    done = [step["do"] for game in every for step in game["steps"] if not step.get("error")]
    for action in ("recover", "skip", "undo"):
        assert action in done
    assert sum(1 for game in every for step in game["steps"] if step.get("error")) >= 20
    assert any(run["sweep"]["stopped"] for run in data["sweeps"]["runs"])
    assert any(run["sweep"]["confirmed"] for run in data["sweeps"]["runs"])


def test_vectors_catch_easy_port_mistakes():
    """Cases that only a mistake in the port would get wrong, kept so the
    TypeScript tests can see those mistakes."""
    data = fresh_vectors()
    runs = data["sweeps"]["runs"]

    # Sorting as text instead of as numbers: JavaScript's default sort.
    def sorts_differently_as_text(grid) -> bool:
        thresholds = sorted({config[2] for config in grid})
        return sorted(thresholds, key=str) != thresholds
    assert any(sorts_differently_as_text(run["grid"]) for run in runs)

    # Stop after at least one confirmation re-run finished: the finished
    # re-runs must still be thrown away (docs/GUIDE.md, Optimizer).
    def stopped_mid_confirmation(run) -> bool:
        games = run["games_per_test"]
        first_phase = games * len(run["grid"])
        done = run["progress"]["last"][0]
        return (run["confirm"] and run["sweep"]["stopped"]
                and not run["sweep"]["confirmed"]
                and done - first_phase >= games * 5)
    assert any(stopped_mid_confirmation(run) for run in runs)

    # A value no game reached must not count as the smallest or largest.
    assert any(0 in row["tally"].values() for row in data["stats"]["tallies"])