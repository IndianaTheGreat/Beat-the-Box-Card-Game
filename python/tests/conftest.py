"""
==============================================
PYTEST FIXTURES
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/conftest.py
Status: ACTIVE
Version: 1.2
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.2 CHANGES (2026-10-20):
- Fixes the test run freezing on Windows ("Not responding" windows, then
  a skip after Ctrl+C). The run used to create and destroy a new Tk
  window per GUI test, and creating the second one could hang. Now there
  is ONE hidden Tk root for the whole run (created the first time a GUI
  test needs it). After each GUI test, clean_up() closes every window the
  test opened, lets running Simulator/Optimizer work wind down, cancels
  anything still scheduled, and resets the theme listeners and the list
  of scroll panels, so the next test starts from a clean root.
- The skip message says why Tk is missing (not installed, or no display).

VERSION 1.1 CHANGES (2026-10-20):
- New autouse fixture isolated_settings: every test gets its own empty
  settings folder (BTB_SETTINGS_DIR) and a fresh theme state, so tests
  never read or change your real settings.

VERSION 1.0 CHANGES (2026-10-20):
- New. Shared fixtures for the test suite.

DESCRIPTION:
-----------
Fixtures used across the tests.

KEY FUNCTIONS:
-------------
- tk_root -> the hidden Tk root shared by the whole run; skips the test
  when Tk or a display is missing; cleans up after the test
- session_root() -> that root (created on first use)
- clean_up(root) -> closes windows and drains pending work (tk_root's
  teardown; tests call it to check it)
- no_dialogs -> records message boxes instead of blocking on them
- isolated_settings (automatic) -> a private settings folder per test
- pump(root, until) -> runs the Tk event loop until a condition is true

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)
- tkinter and a display for GUI tests only; they skip otherwise

CLI USAGE:
---------
# From the python/ folder
python -m pytest
# Headless Linux, to include the GUI tests
xvfb-run python3 -m pytest

NOTES:
-----
- Why one root: Tk is not built to be started and stopped over and over
  in one program. On Windows, creating a new Tk after destroying one
  sometimes never returns. The app itself only ever makes one root.
- pytest.ini sets faulthandler_timeout, so a test that hangs prints a
  traceback of every thread instead of freezing silently.
"""

import gc
import os
import sys
import time

import pytest

_ROOT = None            # the one Tk root for the whole run
_ROOT_PROBLEM = None    # why it couldn't be made, if it couldn't


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Point btb.settings at a fresh folder and forget the active theme."""
    monkeypatch.setenv("BTB_SETTINGS_DIR", str(tmp_path / "settings"))
    theme = sys.modules.get("btb.theme")
    if theme is not None:
        theme.reset()
    yield tmp_path / "settings"
    theme = sys.modules.get("btb.theme")
    if theme is not None:
        theme.reset()


def session_root():
    """The hidden Tk root shared by every GUI test (made on first use).
    Skips the calling test when Tk is missing or can't open a window."""
    global _ROOT, _ROOT_PROBLEM
    try:
        import tkinter as tk
    except ImportError:
        pytest.skip("Tkinter is not installed for this Python")
    if _ROOT is None and _ROOT_PROBLEM is None:
        try:
            _ROOT = tk.Tk()
        except tk.TclError as exc:
            _ROOT_PROBLEM = str(exc)
        else:
            _ROOT.withdraw()
    if _ROOT_PROBLEM is not None:
        pytest.skip(f"Tk can't open a window here ({_ROOT_PROBLEM}); "
                    "on headless Linux run the tests under xvfb-run")
    return _ROOT


def _pending_after(root) -> list:
    """Ids of every callback still scheduled with after / after_idle."""
    try:
        return list(root.tk.splitlist(root.tk.call("after", "info")))
    except Exception:
        return []


def _running_work() -> int:
    """How many Simulator/Optimizer workers are still winding down."""
    gui_sim = sys.modules.get("btb.gui_sim")
    return gui_sim._GcPause.active if gui_sim is not None else 0


def clean_up(root, timeout: float = 15.0) -> None:
    """Leave the shared root as a new test expects it: no windows, nothing
    scheduled, no worker running, garbage collection back on."""
    import tkinter as tk
    for child in list(root.winfo_children()):
        try:
            child.destroy()
        except tk.TclError:
            pass
    # A run whose window closed stops its worker on its next poll: let
    # those polls happen. Then give quick follow-ups (idle re-checks) a
    # moment, and cancel whatever is still scheduled (a long timer, say).
    deadline = time.monotonic() + timeout
    while _running_work() and time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)
    settle_until = time.monotonic() + 0.2
    while _pending_after(root) and time.monotonic() < settle_until:
        root.update()
        time.sleep(0.005)
    for after_id in _pending_after(root):
        try:
            root.after_cancel(after_id)
        except (tk.TclError, ValueError):
            pass
    gui_sim = sys.modules.get("btb.gui_sim")
    if gui_sim is not None and gui_sim._GcPause.active:
        gui_sim._GcPause.active = 0               # a worker that never answered
        if gui_sim._GcPause.was_enabled:
            gc.enable()
    widgets = sys.modules.get("btb.widgets")
    if widgets is not None:
        widgets._SCROLL_FRAMES.clear()
    theme = sys.modules.get("btb.theme")
    if theme is not None:
        theme.reset()
    root.update()


@pytest.fixture
def tk_root():
    """The hidden Tk root for GUI tests. Skips when Tk or a display is
    missing (on headless Linux, run under xvfb-run). Every window a test
    opens is closed afterwards."""
    root = session_root()
    from btb import theme
    theme.use(root)                  # the default theme (settings are fresh)
    yield root
    clean_up(root)


def pytest_sessionfinish(session, exitstatus):
    """Close the shared root once every test has run."""
    global _ROOT
    if _ROOT is not None:
        try:
            clean_up(_ROOT, timeout=5.0)
            _ROOT.destroy()
        except Exception:
            pass
        _ROOT = None


@pytest.fixture
def no_dialogs(monkeypatch):
    """Record message boxes instead of blocking on them."""
    from tkinter import messagebox
    shown = []
    for name in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(messagebox, name,
                            lambda title, msg, _n=name, **kw: shown.append((_n, title, msg)))
    monkeypatch.setattr(messagebox, "askyesno", lambda *a, **k: True)
    return shown


def pump(root, until=None, timeout: float = 10.0):
    """Run the Tk event loop until `until()` is true (or for one pass)."""
    deadline = time.time() + timeout
    while True:
        root.update()
        if until is None or until():
            return
        if time.time() > deadline:
            raise TimeoutError("GUI did not reach the expected state")
        time.sleep(0.01)


os.environ.setdefault("PYTHONHASHSEED", "0")