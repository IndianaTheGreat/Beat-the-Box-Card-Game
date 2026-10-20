"""
==============================================
PYTEST FIXTURES
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/conftest.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Shared fixtures for the test suite.

DESCRIPTION:
-----------
Fixtures used across the tests.

KEY FUNCTIONS:
-------------
- tk_root -> hidden Tk root; skips the test when Tk or a display is missing
- no_dialogs -> records message boxes instead of blocking on them
- pump(root, until) -> runs the Tk event loop until a condition is true

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

import os

import pytest


@pytest.fixture
def tk_root():
    """A hidden Tk root for GUI tests. Skips when Tk or a display is missing
    (on Linux CI, run under `xvfb-run pytest`)."""
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"no display for Tk: {exc}")
    root.withdraw()
    yield root
    root.destroy()


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
    import time
    deadline = time.time() + timeout
    while True:
        root.update()
        if until is None or until():
            return
        if time.time() > deadline:
            raise TimeoutError("GUI did not reach the expected state")
        time.sleep(0.01)


os.environ.setdefault("PYTHONHASHSEED", "0")