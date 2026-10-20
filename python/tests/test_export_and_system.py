"""
==============================================
EXPORT, RESOURCE SCAN AND SETTINGS TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_export_and_system.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 218 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. CSV and JSON exports, the CPU/memory scan that sizes parallel runs,
  and the remembered settings file. No GUI needed.

DESCRIPTION:
-----------
Exports are written to a temporary folder and read back. auto_workers is
a pure function, so its limits are tested with made-up machines.
Settings tests use the private folder from conftest.isolated_settings.

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)

KEY FUNCTIONS:
-------------
- batch, sweep -> fixtures: one small seeded Simulator and Optimizer run
- test_auto_workers_limits -> made-up machines and the expected helpers

CLI USAGE:
---------
# From the python/ folder
pytest tests/test_export_and_system.py
"""

import csv
import json
import subprocess
import sys

import pytest

from btb import __version__, settings, system
from btb.export import SWEEP_COLUMNS, batch_rows, export, sweep_rows
from btb.sim import run_batch, run_sweep, sweep_grid


# ----------------------------------------------------------------- export -- #

@pytest.fixture(scope="module")
def batch():
    return run_batch(300, 1, 5, 10.0, seed=12)


@pytest.fixture(scope="module")
def sweep():
    return run_sweep(30, sweep_grid((0, 1), (0, 2), [0.0, 10.0]), seed=12, confirm=True)


def test_simulator_csv_has_settings_summary_and_distributions(batch, tmp_path):
    path = export(batch, tmp_path / "run.csv")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["section", "item", "value"]
    sections = {r[0] for r in rows[1:]}
    assert {"settings", "summary", "boxes_left_in_wins", "plays"} <= sections
    summary = {r[1]: r[2] for r in rows if r[0] == "summary"}
    assert int(summary["games"]) == 300 and int(summary["wins"]) == batch.wins
    assert float(summary["margin_low"]) <= batch.win_rate <= float(summary["margin_high"])
    plays = {int(r[1]): int(r[2]) for r in rows if r[0] == "plays"}
    assert sum(plays.values()) == 300


def test_simulator_json_reloads_with_the_same_numbers(batch, tmp_path):
    data = json.loads(export(batch, tmp_path / "run.json").read_text(encoding="utf-8"))
    assert data["tool"] == "Simulator" and data["suite_version"] == __version__
    assert data["settings"] == {"jokers": 1, "inclusive_calls": 5, "threshold": 10.0,
                                "games": 300, "seed": 12}
    assert data["summary"]["wins"] == batch.wins
    assert sum(data["distributions"]["plays"].values()) == 300


def test_optimizer_csv_has_one_row_per_configuration(sweep, tmp_path):
    path = export(sweep, tmp_path / "sweep.csv")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == list(SWEEP_COLUMNS)
    phases = [r["phase"] for r in rows]
    assert phases.count("sweep") == len(sweep.results) == 12
    assert phases.count("confirm") == len(sweep.confirmed) == 10
    top = rows[0]
    assert top["rank"] == "1" and top["tied_for_best"] == "True"
    seeds = {r["phase"]: r["seed"] for r in rows}
    assert seeds == {"sweep": "12", "confirm": str(12 + 30)}  # first seed each row played


def test_optimizer_json_names_the_best_configuration(sweep, tmp_path):
    data = json.loads(export(sweep, tmp_path / "sweep.json").read_text(encoding="utf-8"))
    best = sweep.best
    assert data["tool"] == "Optimizer" and data["settings"]["seed"] == 12
    assert (data["best"]["jokers"], data["best"]["inclusive_calls"],
            data["best"]["threshold"]) == best.key
    assert len(data["results"]) == len(sweep_rows(sweep)) - 1


def test_export_rejects_unknown_file_types(batch, tmp_path):
    with pytest.raises(ValueError):
        export(batch, tmp_path / "run.txt")


def test_batch_rows_list_every_tally(batch):
    names = {r[0] for r in batch_rows(batch)}
    assert {"cards_left_in_losses", "inclusive_used", "recoveries", "jokers_drawn"} <= names


# ------------------------------------------------------------- CPU / memory -- #

@pytest.mark.parametrize("cpus, idle, free_mb, expected", [
    (16, None, None, 12),    # never more than 75% of the cores
    (16, 1.0, None, 12),
    (16, 0.5, None, 7),      # only idle cores, minus one for you
    (16, 0.05, None, 1),     # a busy machine runs in one process
    (16, 1.0, 600, 4),       # about 150 MB per helper
    (4, None, None, 3),      # always one core left free
    (2, None, None, 1),
    (1, 1.0, 10_000, 1),
])
def test_auto_workers_limits(cpus, idle, free_mb, expected):
    assert system.auto_workers(cpus, idle, free_mb) == expected


def test_resolve_workers_clamps_numbers_and_scans_for_auto():
    assert system.resolve_workers(1) == 1
    assert system.resolve_workers(10_000) == system.cpu_count()
    assert 1 <= system.resolve_workers("auto") <= max(1, system.cpu_count() - 1)


def test_scan_reports_something_sensible():
    result = system.scan(sample_s=0.05)
    assert result.cpus >= 1 and result.workers >= 1
    assert result.idle is None or 0.0 <= result.idle <= 1.0
    assert "Auto uses" in result.describe()


def test_lower_priority_never_raises():
    # Run in a child process so this test process keeps its priority.
    code = "from btb.system import lower_priority; lower_priority(); print('ok')"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=str(__import__("pathlib").Path(__file__).parents[1]))
    assert out.stdout.strip() == "ok"


# --------------------------------------------------------------- settings -- #

def test_settings_start_with_the_defaults(isolated_settings):
    assert not settings.settings_path().exists()
    assert settings.load() == settings.DEFAULTS


def test_settings_are_remembered(isolated_settings):
    assert settings.update(theme="Midnight", show_odds=True, cpu_workers=3)
    assert settings.settings_path().parent == isolated_settings
    assert settings.load() == {"theme": "Midnight", "show_odds": True, "cpu_workers": 3}


def test_bad_settings_are_refused_and_bad_files_ignored(isolated_settings):
    with pytest.raises(ValueError):
        settings.update(cpu_workers=0)
    with pytest.raises(ValueError):
        settings.update(colour="blue")
    isolated_settings.mkdir(parents=True, exist_ok=True)
    settings.settings_path().write_text("{not json", encoding="utf-8")
    assert settings.load() == settings.DEFAULTS
    settings.settings_path().write_text(
        json.dumps({"theme": 5, "show_odds": "yes", "cpu_workers": "auto"}), encoding="utf-8")
    assert settings.load() == settings.DEFAULTS