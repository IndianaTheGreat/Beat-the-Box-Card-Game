"""
==============================================
GUI SMOKE TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_gui.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Smoke tests for the four tool windows and the launcher.

DESCRIPTION:
-----------
Checks that the thin GUIs drive the engine correctly and stay responsive:
keyboard play, recovery on the board, the card picker, background runs
reaching 100%, Stop, input validation, and the garbage-collection guard.
Skipped without Tk or a display.

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

tk = pytest.importorskip("tkinter")

from btb.engine import HIGHER, LOWER_EQUAL, Card
from conftest import pump
from helpers import cards, game


@pytest.fixture
def window(tk_root):
    return tk.Toplevel(tk_root)


def key(gui, root, sequence):
    gui.root.focus_force()
    pump(root)
    gui.root.event_generate(sequence, when="now")


def test_keyboard_selects_with_numpad_layout_and_calls(tk_root, window, no_dialogs):
    from btb.gui_game import PlayerGUI
    gui = PlayerGUI(window)
    gui.game = game(["5", "6", "7", "8", "9", "10", "4", "3", "2"], ["K", "A", "Q"])
    gui.refresh()
    key(gui, tk_root, "<Key-1>")       # bottom-left box = position 6 (a 4)
    assert gui.selected == 6
    key(gui, tk_root, "<Key-w>")       # Higher
    assert gui.game.box[6].rank == 13
    key(gui, tk_root, "<Control-z>")   # Undo
    assert gui.game.box[6].rank == 4
    key(gui, tk_root, "<Control-w>")   # Ctrl+W must NOT count as W
    assert gui.game.box[6].rank == 4


def test_recovery_is_chosen_on_the_board(tk_root, window, no_dialogs):
    from btb.gui_game import COLORS, PlayerGUI
    gui = PlayerGUI(window)
    gui.game = game(["7", "K"], ["5", "7", "9"], inclusive=1)
    gui.refresh()
    gui.box_clicked(1)
    gui.make_call(HIGHER)              # K fails on a 5
    assert gui.box_buttons[1].cget("text") == "Failed"
    gui.box_clicked(0)
    gui.make_call(LOWER_EQUAL)         # 7 on 7: recovery earned
    assert gui.game.recovery_pending
    assert gui.box_buttons[1].cget("text") == "Failed\nK♥"  # show-failed is on
    assert gui.box_buttons[1].cget("bg") == COLORS["recoverable"]
    assert gui.call_buttons[HIGHER].instate(["disabled"])
    gui.box_clicked(1)
    assert gui.game.box[1].rank == 13 and not gui.game.recovery_pending


def test_skip_recovery_button(tk_root, window, no_dialogs):
    from btb.gui_game import GameSettings, PlayerGUI
    gui = PlayerGUI(window)
    gui.settings = GameSettings(show_failed=False)
    gui.game = game(["7", "K"], ["5", "7", "9"], inclusive=1)
    gui.box_clicked(1)
    gui.make_call(HIGHER)
    gui.box_clicked(0)
    gui.make_call(LOWER_EQUAL)
    assert gui.box_buttons[1].cget("text") == "Failed"  # show-failed is off
    gui.skip_button.invoke()
    assert not gui.game.recovery_pending and 1 in gui.game.failed


def test_probability_window_tracks_the_game(tk_root, window, no_dialogs):
    from btb.gui_game import PlayerGUI
    gui = PlayerGUI(window)
    gui.game = game(["8", "🃏"], ["2", "9", "Q", "A"])
    gui.show_probabilities()
    rows = [gui.prob_tree.item(i, "values") for i in gui.prob_tree.get_children()]
    assert rows[0][2:4] == ("75.0%", "25.0%") and rows[1][2] == "100.0%"
    gui.box_clicked(0)
    gui.make_call(HIGHER)              # draws the 2: box 0 fails
    rows = [gui.prob_tree.item(i, "values") for i in gui.prob_tree.get_children()]
    assert rows[0][1] == "Failed"


def test_new_game_with_real_deck(tk_root, window, no_dialogs):
    from btb.gui_game import GameSettings, PlayerGUI
    gui = PlayerGUI(window)
    assert gui.new_game(GameSettings(jokers=2, inclusive_calls=7))
    assert gui.cards_remaining_var.get() == "Cards remaining: 45"
    assert gui.inclusive_var.get() == "Inclusive calls: 7"
    for name in ("show_rules", "show_strategy", "show_keyboard_help"):
        getattr(gui, name)()


def test_assistant_card_picker(tk_root, window, no_dialogs, monkeypatch):
    from btb import gui_game
    gui = gui_game.AssistantGUI(window)
    picked = {}

    def fake_wait(dialog_window):
        # Click A♠ then both jokers, then seven more cards.
        picker = picked["picker"]
        buttons = [w for w in picker.dialog.winfo_children()
                   if isinstance(w, gui_game.ttk.Button) and w.cget("text") != "Cancel"]
        jokers = [b for b in buttons if b.cget("text") == "🃏"]
        assert len(jokers) == 2
        jokers[0].invoke()
        assert jokers[0].instate(["disabled"]) and not jokers[1].instate(["disabled"])
        jokers[1].invoke()
        for b in buttons:
            if picker.result is not None:  # the ninth pick closed the dialog
                break
            if b.cget("text") in ("2♠", "3♠", "4♠", "5♠", "6♠", "7♠", "8♠"):
                b.invoke()

    real_picker = gui_game.CardPickerDialog

    def capture(*args, **kwargs):
        picked["picker"] = real_picker(*args, **kwargs)
        return picked["picker"]

    monkeypatch.setattr(gui_game, "CardPickerDialog", capture)
    monkeypatch.setattr(gui.root, "wait_window", fake_wait)
    assert gui.new_game(gui_game.GameSettings(jokers=2, inclusive_calls=3))
    assert [str(c) for c in gui.game.box] == ["🃏", "🃏", "2♠", "3♠", "4♠", "5♠",
                                              "6♠", "7♠", "8♠"]
    assert "🃏" not in gui.drawn_combo["values"] and gui.game.cards_left == 45
    gui.box_clicked(5)
    gui.make_call(HIGHER)              # no card picked yet
    assert "Pick the card you flipped" in gui.status_var.get()
    gui.drawn_var.set("A♥")
    gui.make_call(HIGHER)
    assert gui.game.box[5] == Card.parse("A♥") and gui.drawn_var.get() == ""
    assert "A♥" not in gui.drawn_combo["values"]


def test_simulator_runs_in_background_and_reaches_100(tk_root, window, no_dialogs):
    from btb.gui_sim import SimulatorGUI
    gui = SimulatorGUI(window)
    gui.sims_var.set("300")
    gui.seed_var.set("4")
    gui.start()
    assert gui.stop_button.instate(["!disabled"]) and gui.run_button.instate(["disabled"])
    pump(tk_root, until=lambda: not gui.task.running and gui.result is not None)
    assert gui.progress_var.get() == 100 and gui.result.games == 300
    assert "Wins:" in gui.results_text.get("1.0", "end")
    assert gui.run_button.instate(["!disabled"])
    gui.show_advanced_stats()


def test_simulator_stop_button(tk_root, window, no_dialogs):
    from btb.gui_sim import SimulatorGUI
    gui = SimulatorGUI(window)
    gui.sims_var.set("200000")
    gui.start()
    pump(tk_root, until=lambda: gui.progress_var.get() > 0)
    gui.stop_button.invoke()
    pump(tk_root, until=lambda: gui.result is not None)
    assert gui.result.stopped and gui.result.games < 200_000
    assert "Stopped" in gui.progress_label.cget("text")


@pytest.mark.parametrize("field, value", [
    ("sims_var", "0"), ("sims_var", "abc"), ("threshold_var", "101"),
    ("calls_var", "44"), ("seed_var", "-3"),
])
def test_simulator_rejects_bad_input(tk_root, window, no_dialogs, field, value):
    from btb.gui_sim import SimulatorGUI
    gui = SimulatorGUI(window)
    getattr(gui, field).set(value)
    gui.start()
    assert gui.task is None and no_dialogs[-1][0] == "showerror"


def test_optimizer_runs_in_background_and_reaches_100(tk_root, window, no_dialogs):
    from btb.gui_sim import OptimizerGUI
    gui = OptimizerGUI(window)
    for name, value in (("games", "20"), ("jokers_max", "1"), ("moves_max", "2"),
                        ("threshold_max", "5"), ("step", "5"), ("seed", "1")):
        gui.vars[name].set(value)
    gui.start()
    pump(tk_root, until=lambda: gui.sweep is not None)
    assert gui.progress_var.get() == 100
    assert len(gui.sweep.results) == 2 * 3 * 2
    assert "Top 10" in gui.results_text.get("1.0", "end")
    gui.show_advanced_stats()


def test_optimizer_handles_all_zero_results(tk_root, window, no_dialogs):
    from btb.gui_sim import OptimizerGUI, describe_sweep, describe_sweep_details
    from btb.sim import run_sweep, sweep_grid
    sweep = run_sweep(2, sweep_grid((0, 0), (0, 1), [0.0]), seed=1)
    for r in sweep.results.values():
        r.wins = 0
    assert "0% of its games" in describe_sweep(sweep, 1)
    assert "Best overall" in describe_sweep_details(sweep, 1)


@pytest.mark.parametrize("field, value", [
    ("step", "0"), ("step", "-1"), ("jokers_max", "3"), ("jokers_min", "2"),
    ("moves_min", "11"), ("threshold_max", "101"), ("games", "0"),
])
def test_optimizer_rejects_bad_input(tk_root, window, no_dialogs, field, value):
    from btb.gui_sim import OptimizerGUI
    gui = OptimizerGUI(window)
    gui.vars["jokers_max"].set("1")
    gui.vars[field].set(value)
    gui.start()
    assert gui.task is None and no_dialogs[-1][0] == "showerror"


def test_launcher_opens_every_tool(tk_root, no_dialogs):
    import main
    app = main.MainApplication(tk.Toplevel(tk_root))
    for _name, cls, _blurb in main.TOOLS:
        assert isinstance(app.launch(cls), cls)


def test_worker_thread_holds_no_tk_references(tk_root, window, no_dialogs):
    # If the worker held the last reference to a Tk object, Python would
    # destroy it on the worker thread and Tcl would abort the process
    # ("Tcl_AsyncDelete: async handler deleted by the wrong thread").
    import threading
    from btb.gui_sim import BackgroundTask
    release = threading.Event()

    def work(progress, should_stop):
        release.wait(5)
        return "ok"

    done = []
    task = BackgroundTask(window, work, lambda d, t: None, done.append, done.append)
    cells = [c.cell_contents for c in task.thread._target.__closure__]
    assert not any(isinstance(c, (BackgroundTask, tk.Misc, tk.Variable)) for c in cells)
    release.set()
    pump(tk_root, until=lambda: done == ["ok"])


def test_garbage_is_only_collected_on_the_tk_thread(tk_root, window, no_dialogs):
    # The cyclic GC runs on whichever thread triggers it. Freeing a closed
    # window's Tk objects on the worker thread aborts the process, so
    # automatic collection is paused while a worker runs and resumed after.
    import gc
    import threading
    from btb.gui_sim import BackgroundTask
    assert gc.isenabled()
    release = threading.Event()
    done = []
    task = BackgroundTask(window, lambda p, s: release.wait(5) and "ok",
                          lambda d, t: None, done.append, done.append)
    assert not gc.isenabled()
    release.set()
    pump(tk_root, until=lambda: done == ["ok"])
    assert gc.isenabled() and not task.running


def test_closing_a_window_mid_run_stops_the_worker(tk_root, no_dialogs):
    import gc
    from btb.gui_sim import SimulatorGUI
    gui = SimulatorGUI(tk.Toplevel(tk_root))
    gui.sims_var.set("200000")
    gui.start()
    pump(tk_root, until=lambda: gui.progress_var.get() > 0)
    task = gui.task
    gui.close()
    pump(tk_root, until=lambda: not task.running)
    assert gc.isenabled()