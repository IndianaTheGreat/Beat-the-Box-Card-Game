"""
==============================================
THEME AND NEW-LOOK TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_theme_and_look.py
Status: ACTIVE
Version: 1.2
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.2 CHANGES (2026-10-20):
- Settings save show_counts too, and new pages take both defaults (odds
  and counts) from Settings.

VERSION 1.1 CHANGES (2026-10-20):
- Updated for the one-window app: the theme is chosen on the Settings
  page (the game pages no longer have a View menu), "Nothing to export"
  shows on the page instead of a pop-up, and the banner's wrong-call
  example uses Higher on a K, since Lower on a 2 is now greyed out.

VERSION 1.0 CHANGES (2026-10-20):
- New. Every theme is complete and readable; themes switch live and are
  remembered; the result banner, odds toggle, card widgets, exports,
  "Use Best in Simulator", table sorting and the Settings window work.
- Ctrl+O changes only the open window; Settings holds the default.
- Closed help windows are forgotten and open ones repaint on a switch.
- Advanced Statistics lists every distribution.

DESCRIPTION:
-----------
Theme data tests run anywhere Tk is installed. Window tests need a display
and skip without one (on headless Linux, run under xvfb-run).

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)
- tkinter and a display for the window tests

KEY FUNCTIONS:
-------------
- READABLE -> colour pairs and the contrast each must reach
- window -> fixture: a fresh Toplevel for one tool window
- test_every_theme_is_complete_and_readable -> runs once per theme

CLI USAGE:
---------
# From the python/ folder
python -m pytest tests/test_theme_and_look.py
"""

import re

import pytest

tk = pytest.importorskip("tkinter")

from btb import settings
from btb import theme as themes
from btb.engine import HIGHER, LOWER, LOWER_EQUAL
from conftest import pump
from helpers import game

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# (foreground, background, minimum WCAG contrast). 4.5 = normal text,
# 3.0 = large or bold text and outlines.
READABLE = [
    ("text", "bg", 4.5), ("text", "panel", 4.5), ("muted", "bg", 3.0),
    ("muted", "panel", 3.0), ("red", "card", 4.5), ("black", "card", 4.5),
    ("joker_ink", "joker", 4.5), ("button_text", "button", 4.5),
    ("accent_text", "accent", 4.5), ("field_text", "field", 4.5),
    ("banner_text", "good", 3.0), ("banner_text", "bad", 3.0),
    ("select", "bg", 3.0), ("chart", "panel", 3.0), ("card", "back", 3.0),
]


# ------------------------------------------------------------ theme data -- #

@pytest.mark.parametrize("t", themes.THEMES, ids=lambda t: t.name)
def test_every_theme_is_complete_and_readable(t):
    for name in themes.COLOR_FIELDS:
        assert HEX.match(getattr(t, name)), f"{t.name}.{name}"
    for fg, bg, minimum in READABLE:
        ratio = themes.contrast(getattr(t, fg), getattr(t, bg))
        assert ratio >= minimum, f"{t.name}: {fg} on {bg} is {ratio:.2f}"


def test_themes_have_unique_names_and_a_valid_default():
    names = themes.theme_names()
    assert len(names) == len(set(names)) == 8
    assert themes.get(themes.DEFAULT_THEME).name in names


def test_themes_can_be_picked_by_name_or_number():
    assert themes.get(1) is themes.THEMES[0]
    assert themes.get(5).name == "Midnight"
    assert themes.get("classic light").name == "Classic Light"
    assert themes.get("No Such Theme") is themes.get(themes.DEFAULT_THEME)
    assert themes.get(99) is themes.get(themes.DEFAULT_THEME)


def test_the_remembered_theme_is_used():
    settings.update(theme="Royal Blue")
    assert themes.current().name == "Royal Blue"


def test_contrast_extremes():
    assert themes.contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert themes.contrast("#777777", "#777777") == pytest.approx(1.0)


# --------------------------------------------------------------- windows -- #

@pytest.fixture
def window(tk_root):
    return tk.Toplevel(tk_root)


def test_switching_theme_restyles_open_windows_and_is_remembered(tk_root, window, no_dialogs):
    from btb.gui_game import PlayerGUI
    gui = PlayerGUI(window)
    gui.game = game(["5", "9"], ["K", "2"])
    gui.refresh()
    themes.set_theme("Classic Light", tk_root)
    light = themes.get("Classic Light")
    assert gui.theme is light and gui.box_views[0].theme is light
    assert str(gui.root.cget("background")) == light.bg
    assert settings.get("theme") == "Classic Light"
    window.destroy()
    themes.set_theme(3, tk_root)                  # closed windows are skipped
    assert settings.get("theme") == "Casino Red"


def test_banner_shows_the_call_and_the_result(tk_root, window, no_dialogs):
    from btb.gui_game import PlayerGUI
    gui = PlayerGUI(window)
    gui.game = game(["5", "9"], ["K", "2", "7", "3"])
    gui.box_clicked(0)
    gui.make_call(HIGHER)                         # 5 -> K: correct
    assert gui.banner_var.get().startswith("Higher on 5") and "drew K" in gui.banner_var.get()
    assert gui.banner_kind == "good" and "Correct" in gui.banner_var.get()
    assert str(gui.banner_label.cget("background")) == gui.theme.good
    gui.box_clicked(1)
    gui.make_call(LOWER)                          # 9 -> 2: correct
    gui.box_clicked(0)
    gui.make_call(HIGHER)                         # K -> 7: wrong
    assert gui.banner_kind == "bad" and "Wrong" in gui.banner_var.get()
    assert gui.history_list.size() == 3 and "✗" in gui.history_list.get("end")
    gui.undo()
    assert gui.history_list.size() == 2 and gui.banner_kind == "neutral"


def test_odds_toggle_shows_odds_under_the_cards_and_is_remembered(tk_root, window, no_dialogs):
    from btb.gui_game import PlayerGUI
    gui = PlayerGUI(window)
    gui.game = game(["8"], ["2", "9", "Q", "A"])
    gui.refresh()
    assert gui.box_views[0].footer_right == ""    # off by default
    gui.root.focus_force()
    pump(tk_root)
    gui.root.event_generate("<Control-o>", when="now")
    assert gui.odds_var.get() and gui.box_views[0].footer_right == "▲75% ▼25%"
    assert settings.get("show_odds") is False     # Ctrl+O is for this window only
    assert gui.box_views[0].footer_left == "7"    # the box's number key


def test_new_game_windows_start_from_the_settings_default(tk_root, no_dialogs):
    from btb.gui_game import AssistantGUI, PlayerGUI
    settings.update(show_odds=True)
    player = PlayerGUI(tk.Toplevel(tk_root))
    assert player.odds_var.get() is True and player.counts_var.get() is False
    settings.update(show_counts=True)
    assistant = AssistantGUI(tk.Toplevel(tk_root))
    assert assistant.odds_var.get() is True and assistant.counts_var.get() is True


def test_help_windows_repaint_and_closed_ones_are_forgotten(tk_root, window, no_dialogs):
    from btb.gui_game import PlayerGUI
    gui = PlayerGUI(window)
    open_win = gui.show_rules()
    closed_win = gui.show_strategy()
    closed_win.destroy()
    themes.set_theme("Midnight", tk_root)
    assert str(open_win.cget("background")) == themes.get("Midnight").bg
    assert closed_win not in gui._windows and open_win in gui._windows


def test_advanced_statistics_lists_every_distribution():
    from btb.gui_sim import describe_batch_details
    from btb.sim import run_batch
    details = describe_batch_details(run_batch(200, 1, 5, 10.0, seed=3), 3)
    for heading in ("boxes left", "cards left", "Plays per game", "Inclusive calls used",
                    "Recoveries per game", "Jokers drawn per game"):
        assert heading in details, heading


def test_card_view_states(tk_root):
    from btb.engine import Card
    from btb.widgets import CardView
    view = CardView(tk_root, themes.current())
    view.show(Card.parse("Q♦"), "selected")
    assert view.describe() == "Q♦" and view.canvas.find_all()
    view.show(None, "failed")
    assert view.describe() == "Failed"
    view.show(None, "recoverable", ghost=Card.parse("2♣"))
    assert view.describe() == "Failed\n2♣"
    view.show(Card.joker(), "live")
    texts = [view.canvas.itemcget(i, "text") for i in view.canvas.find_all()
             if view.canvas.type(i) == "text"]
    assert "JOKER" in texts                       # drawn, not an emoji
    with pytest.raises(ValueError):
        view.show(None, "upside-down")


def test_simulator_exports_through_the_save_dialog(tk_root, window, no_dialogs, tmp_path,
                                                   monkeypatch):
    from btb import gui_sim
    gui = gui_sim.SimulatorGUI(window)
    gui.export("csv")                             # nothing to export yet
    assert gui.message_var.get().startswith("Nothing to export") and no_dialogs == []
    gui.sims_var.set("120")
    gui.seed_var.set("9")
    gui.cores_var.set("1")
    gui.start()
    pump(tk_root, until=lambda: gui.result is not None)
    target = tmp_path / "out.json"
    monkeypatch.setattr(gui_sim.filedialog, "asksaveasfilename", lambda **kw: str(target))
    gui.export("json")
    assert target.exists() and "Saved out.json" in gui.progress_label.cget("text")
    assert "seed9" in gui.export_name()


def test_cores_setting_is_remembered(tk_root, window, no_dialogs):
    from btb.gui_sim import SimulatorGUI
    gui = SimulatorGUI(window)
    assert gui.cores_var.get() == "Auto"
    gui.cores_var.set("1")
    gui._save_cores()
    assert settings.get("cpu_workers") == 1
    assert SimulatorGUI(tk.Toplevel(tk_root)).cores_var.get() == "1"


def test_optimizer_table_sorts_and_best_opens_in_the_simulator(tk_root, window, no_dialogs):
    from btb.gui_sim import OptimizerGUI, SimulatorGUI
    gui = OptimizerGUI(window)
    for name, value in (("games", "30"), ("jokers_max", "0"), ("moves_max", "3"),
                        ("threshold_max", "10"), ("step", "10"), ("seed", "2")):
        gui.vars[name].set(value)
    gui.confirm_var.set(False)
    gui.cores_var.set("1")
    gui.start()
    pump(tk_root, until=lambda: gui.sweep is not None)
    first = [gui.table.set(i, "rank") for i in gui.table.get_children()]
    assert first == [str(n) for n in range(1, 9)]
    gui.sort_table("calls")
    calls = [int(gui.table.set(i, "calls")) for i in gui.table.get_children()]
    assert calls == sorted(calls)
    sim = gui.use_best()
    best = gui.sweep.best
    assert isinstance(sim, SimulatorGUI)
    assert (int(sim.jokers_var.get()), int(sim.calls_var.get()),
            float(sim.threshold_var.get())) == best.key
    assert sim.seed_var.get() == "2"


def test_settings_window_saves_and_switches_theme(tk_root, no_dialogs):
    import main
    app = main.MainApplication(tk.Toplevel(tk_root))
    dialog = app.open_settings()
    dialog.theme_var.set("Slate")
    dialog.odds_var.set(True)
    dialog.counts_var.set(True)
    dialog.cores_var.set("1")
    dialog.save()
    assert settings.load() == {"theme": "Slate", "show_odds": True, "show_counts": True,
                               "cpu_workers": 1}
    assert themes.current().name == "Slate"