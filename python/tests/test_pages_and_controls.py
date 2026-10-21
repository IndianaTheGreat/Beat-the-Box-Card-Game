"""
==============================================
ONE-WINDOW APP, CALL BUTTONS AND RESIZING TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_pages_and_controls.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.1 CHANGES (2026-10-20):
- Calls offered in the new button order (▲= ▲ ▼ ▼=; keys D W S A).
- Show odds (Ctrl+O) and Show counts (Ctrl+K) are separate switches;
  Ctrl+P / Ctrl+L and picking a view turn on the one they need; the
  toolbar shortens their labels when narrow.
- Every page fits and settles with its Advanced charts showing too; only
  scroll panels that are on screen are checked.

VERSION 1.0 CHANGES (2026-10-20):
- New. The calls the game offers (greyed-out buttons) and why, the button
  order and colours, the "Show odds & counts" switch, the sidebar pages
  (kept state, keys only on the page showing, no pop-up windows), the
  in-page New Game panel, in-page errors and confirmations, and resizing.
- Every page fits and settles at the smallest window size and at a
  1366 x 768 laptop size: nothing is cut off (a panel too tall for the
  window scrolls), and the layout stops changing (no resize loops).
- The Settings page reloads, cancels (button or Escape) and saves only
  what changed; the Simulator picks up a CPU cores change; Clear forgets a
  pending big-run warning; Use Best leaves a running Simulator alone; Ctrl
  shortcuts don't fire while typing, but clicking a read-only field (cards
  left) doesn't switch them off; cards re-centre on a width change; a
  cleared message leaves no gap.
- Every side panel's scrollbar matches what it holds after switching side
  views and after an error message (nothing unreachable at the bottom).

DESCRIPTION:
-----------
The offered_calls tests run anywhere. The window tests need Tk and a
display and skip without one (on headless Linux, run under xvfb-run).

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)
- tkinter and a display for the window tests

KEY FUNCTIONS:
-------------
- app -> fixture: the one-window app in a fresh Toplevel
- toplevels(root) -> every extra window open under the root (should be none)
- press(app, root, key) -> sends a key to the app window
- settle(root) -> runs the event loop until it is idle; returns how many
  events that took (a resize loop never gets there)
- reachable(widget, window) -> fully inside the window, or inside a panel
  that scrolls to it

CLI USAGE:
---------
# From the python/ folder
python -m pytest tests/test_pages_and_controls.py
"""

import random

import pytest

from btb.engine import (
    HIGHER, HIGHER_EQUAL, INCLUSIVE_CALLS, JOKER_USE_INCLUSIVE, LOWER, LOWER_EQUAL,
    NO_INCLUSIVE_LEFT, NOTHING_HIGHER, NOTHING_LOWER, OFFER_ORDER, PLAIN_CALLS, RANKS, Card,
    RulesError, call_blocked_reason, odds_against, offered_calls, standard_deck,
)
from conftest import pump
from helpers import card, game


# ------------------------------------------------------ calls the game offers -- #

def test_offered_calls_leave_out_dead_calls_on_a_2_and_an_ace():
    assert offered_calls(card("2"), 3) == (HIGHER_EQUAL, HIGHER, LOWER_EQUAL)
    assert offered_calls(card("A"), 3) == (HIGHER_EQUAL, LOWER, LOWER_EQUAL)
    assert offered_calls(card("8"), 3) == (HIGHER_EQUAL, HIGHER, LOWER, LOWER_EQUAL)


def test_offered_calls_drop_inclusive_calls_when_none_are_left():
    assert offered_calls(card("8"), 0) == (HIGHER, LOWER)
    assert offered_calls(card("2"), 0) == (HIGHER,)
    assert offered_calls(card("A"), 0) == (LOWER,)


def test_a_joker_gets_inclusive_calls_while_any_are_left_then_plain_calls():
    assert offered_calls(Card.joker(), 1) == INCLUSIVE_CALLS
    assert offered_calls(Card.joker(), 0) == PLAIN_CALLS   # so the joker can still be played


def test_the_calls_left_out_never_do_better():
    # Lower on a 2 / Higher on an A can only win on a joker, and the opposite
    # call wins on that joker too: greying them out never costs a game.
    rng = random.Random(7)
    for _ in range(300):
        pile = standard_deck(2)
        rng.shuffle(pile)
        pile = pile[:rng.randint(1, 45)]
        two, ace = odds_against(Card(2, "♠"), pile), odds_against(Card(14, "♠"), pile)
        assert two.lower <= two.higher and ace.higher <= ace.lower


def test_offered_calls_are_a_guard_rail_not_a_rule():
    g = game(["2"], ["5", "9"])
    assert g.play(0, LOWER).success is False   # the engine still allows it


def test_call_blocked_reason_names_why_and_matches_offered_calls():
    assert call_blocked_reason(card("2"), LOWER, 3) == NOTHING_LOWER
    assert call_blocked_reason(card("A"), HIGHER, 3) == NOTHING_HIGHER
    assert call_blocked_reason(card("8"), LOWER_EQUAL, 0) == NO_INCLUSIVE_LEFT
    assert call_blocked_reason(Card.joker(), HIGHER, 2) == JOKER_USE_INCLUSIVE
    assert call_blocked_reason(Card.joker(), HIGHER, 0) is None
    assert call_blocked_reason(card("2"), LOWER_EQUAL, 1) is None
    with pytest.raises(RulesError):
        call_blocked_reason(card("8"), "sideways", 1)
    for c in [Card(r, "♠") for r in RANKS] + [Card.joker()]:
        for left in (0, 1):
            assert offered_calls(c, left) == tuple(
                call for call in OFFER_ORDER if call_blocked_reason(c, call, left) is None)


# ------------------------------------------------------------- window tests -- #

@pytest.fixture
def app(tk_root):
    import tkinter as tk
    import main
    return main.MainApplication(tk.Toplevel(tk_root))


def toplevels(root):
    import tkinter as tk
    found = []
    for child in root.winfo_children():
        if isinstance(child, tk.Toplevel):
            found.append(child)
        found.extend(toplevels(child))
    return found


def press(app, root, key):
    app.root.focus_force()
    pump(root)
    app.root.event_generate(key, when="now")


def test_call_buttons_are_paired_by_direction(tk_root, app, no_dialogs):
    player = app.show_page("player")
    order = sorted(player.call_buttons, key=lambda c: int(player.call_buttons[c].grid_info()["column"]))
    assert order == [HIGHER_EQUAL, HIGHER, LOWER, LOWER_EQUAL]     # ▲= ▲ ▼ ▼=
    styles = {c: str(player.call_buttons[c].cget("style")) for c in order}
    assert styles[HIGHER] == styles[HIGHER_EQUAL] and styles[HIGHER].endswith("CallUp.TButton")
    assert styles[LOWER] == styles[LOWER_EQUAL] and styles[LOWER].endswith("CallDown.TButton")


def test_messages_for_dead_calls_only_suggest_calls_you_have(tk_root, app, no_dialogs):
    player = app.show_page("player")
    player.game = game(["2", "A", "🃏"], ["5", "9", "K"], inclusive=0)
    player.box_clicked(0)
    player.make_call(LOWER)
    assert "Lower or Equal" not in player.status_var.get()     # none left to suggest
    player.game.inclusive_left = 2
    player.make_call(LOWER)
    assert "Lower or Equal" in player.status_var.get()


def test_joker_hint_promises_a_recovery_only_when_a_box_has_failed(tk_root, app, no_dialogs):
    player = app.show_page("player")
    player.game = game(["🃏", "8"], ["K", "Q", "K"], inclusive=2)
    player.box_clicked(0)
    assert "nothing to recover" in player.status_var.get()
    player.box_clicked(1)
    player.make_call(LOWER)                                  # 8 -> K: box 1 fails
    player.box_clicked(0)
    assert "plus a recovery" in player.status_var.get()


def test_shortcuts_are_listed_in_button_order():
    from btb import text
    calls = {"higher": HIGHER, "higher_equal": HIGHER_EQUAL, "lower": LOWER,
             "lower_equal": LOWER_EQUAL}
    listed = [(keys, calls[action]) for keys, _desc, action, _seq in text.SHORTCUTS
              if action in calls]
    assert [call for _keys, call in listed] == list(OFFER_ORDER)   # the buttons' order
    assert [keys for keys, _call in listed] == ["D", "W", "S", "A"]


def test_dead_calls_are_greyed_out_and_explained(tk_root, app, no_dialogs):
    player = app.show_page("player")
    player.game = game(["2", "A", "🃏"], ["5", "9", "K", "3"], inclusive=1)
    player.box_clicked(0)                                  # a 2
    assert player.call_buttons[LOWER].instate(["disabled"])
    assert not player.call_buttons[HIGHER].instate(["disabled"])
    player.make_call(LOWER)                                 # e.g. pressing S
    assert "Nothing is lower than a 2" in player.status_var.get()
    assert player.game.cards_left == 4                      # nothing was played
    player.box_clicked(1)                                   # an A
    assert player.call_buttons[HIGHER].instate(["disabled"])
    player.box_clicked(2)                                   # a joker, 1 call left
    assert [c for c, b in player.call_buttons.items() if not b.instate(["disabled"])] == [
        HIGHER_EQUAL, LOWER_EQUAL]
    player.make_call(HIGHER)
    assert "joker" in player.status_var.get().lower() and player.game.cards_left == 4
    player.game.inclusive_left = 0
    player.refresh()
    assert not player.call_buttons[HIGHER].instate(["disabled"])   # joker playable again


def test_show_odds_and_show_counts_are_separate_switches(tk_root, app, no_dialogs):
    player = app.show_page("player")
    player.game = game(["8"], ["2", "9", "Q", "A"])
    player.refresh()
    pump(tk_root)
    assert player.aids_hint.winfo_manager() == "pack" and not player.aids.winfo_manager()
    assert player.box_views[0].footer_right == ""
    press(app, tk_root, "<Control-o>")                      # odds only
    assert player.box_views[0].footer_right == "▲75% ▼25%"
    assert player.side_view.get() == "odds" and player.odds_frame.winfo_manager() == "pack"
    assert not player.count_frame.winfo_manager()
    assert "Ctrl+K" in player.aids_note_var.get()           # says how to get the counts
    press(app, tk_root, "<Control-k>")                      # and counts
    assert player.counts_var.get() and player.aids_note_var.get() == ""
    press(app, tk_root, "<Control-o>")                      # counts only: no odds anywhere
    assert player.box_views[0].footer_right == ""
    assert player.side_view.get() == "count" and player.count_frame.winfo_manager() == "pack"
    assert "Ctrl+O" in player.aids_note_var.get()
    press(app, tk_root, "<Control-p>")                      # Ctrl+P turns the odds back on
    assert player.odds_var.get() and player.side_view.get() == "odds"
    press(app, tk_root, "<Control-k>")
    press(app, tk_root, "<Control-l>")                      # Ctrl+L turns the counts back on
    assert player.counts_var.get() and player.side_view.get() == "cards"
    assert player.cards_remaining_var.get() == "4"           # tiles always show


def test_picking_a_hidden_view_turns_its_switch_on(tk_root, app, no_dialogs):
    player = app.show_page("player")
    player.game = game(["8"], ["2", "9", "Q", "A"])
    player.odds_var.set(True)
    player.on_odds_changed()
    count_button = player.view_buttons[0]                   # "Count & plays"
    count_button.invoke()
    assert player.counts_var.get() and player.side_view.get() == "count"


def test_toolbar_switches_have_short_labels_when_narrow(tk_root, app, no_dialogs):
    player = app.show_page("player")
    app.root.geometry("960x620")
    pump(tk_root)
    tk_root.after(100)
    pump(tk_root)
    labels = {str(player.odds_check.cget("text")), str(player.counts_check.cget("text"))}
    assert labels == {"Odds", "Counts"}                    # too narrow for the hints
    app.root.geometry("1600x700")
    pump(tk_root)
    tk_root.after(100)
    pump(tk_root)
    assert str(player.counts_check.cget("text")) == "Show counts (Ctrl+K)"


def test_pages_keep_their_state_and_only_the_page_showing_takes_keys(tk_root, app, no_dialogs):
    from btb.gui_game import GameSettings
    player = app.show_page("player")
    player.new_game(GameSettings(0, 5))
    first = list(player.game.box)
    app.show_page("simulator")
    press(app, tk_root, "<Key-5>")                          # Player is hidden: ignored
    press(app, tk_root, "<Key-w>")
    assert player.selected is None and player.game.cards_left == 43
    assert app.show_page("player") is player and player.game.box == first
    press(app, tk_root, "<Key-5>")                          # now it counts
    assert player.selected == 4


def test_typing_in_a_field_does_not_select_boxes(tk_root, app, no_dialogs):
    player = app.show_page("player")
    player.new_game()                                       # opens the New Game panel
    assert player.mode == "setup" and player.setup_panel.frame.winfo_manager() == "pack"
    combo = player.setup_panel.calls_combo
    combo.focus_force()
    pump(tk_root)
    combo.event_generate("<Key-7>", when="now")
    assert player.selected is None and player.mode == "setup"


def test_new_game_panel_checks_input_on_the_page(tk_root, app, no_dialogs):
    player = app.show_page("player")
    player.new_game()
    player.setup_panel.calls_var.set("99")
    player.setup_panel.start()
    assert player.game is None and "0-43" in player.setup_panel.error_label.cget("text")
    player.setup_panel.calls_var.set("4")
    player.setup_panel.joker_var.set("1")
    player.setup_panel.start()
    assert player.mode == "play" and player.game.inclusive_left == 4
    assert player.game.cards_left == 44


def test_nothing_pops_up(tk_root, app, no_dialogs):
    from btb.gui_game import GameSettings
    player = app.show_page("player")
    player.new_game()
    player.new_game(GameSettings(1, 3))
    for action in (player.show_probabilities, player.show_remaining_cards):
        action()
    assert player.prob_tree.get_children()
    for key, page in (("<Control-r>", "rules"), ("<Control-y>", "strategy"),
                      ("<Control-h>", "shortcuts")):
        app.show_page("player")
        press(app, tk_root, key)
        assert app.current == page
    assistant = app.show_page("assistant")
    assistant.new_game(GameSettings(2, 3))
    sim = app.show_page("simulator")
    sim.sims_var.set("abc")
    sim.start()
    sim.show_advanced_stats()
    opt = app.show_page("optimizer")
    opt.export("csv")
    for key in ("guide", "settings", "home"):
        app.show_page(key)
    assert toplevels(app.root) == [] and no_dialogs == []


def test_use_best_switches_to_the_simulator_page(tk_root, app, no_dialogs):
    opt = app.show_page("optimizer")
    for name, value in (("games", "20"), ("jokers_max", "0"), ("moves_max", "2"),
                        ("threshold_max", "10"), ("step", "10"), ("seed", "3")):
        opt.vars[name].set(value)
    opt.confirm_var.set(False)
    opt.cores_var.set("1")
    opt.start()
    pump(tk_root, until=lambda: opt.sweep is not None)
    sim = opt.use_best()
    assert app.current == "simulator" and sim is app.page("simulator")
    assert (int(sim.jokers_var.get()), int(sim.calls_var.get()),
            float(sim.threshold_var.get())) == opt.sweep.best.key
    assert toplevels(app.root) == []


def test_a_very_large_run_needs_a_second_press(tk_root, app, no_dialogs):
    sim = app.show_page("simulator")
    sim.sims_var.set("3000000")
    sim.cores_var.set("1")
    sim.start()
    assert sim.task is None and "Press Run Simulations again" in sim.message_var.get()
    sim.start()
    assert sim.task is not None
    sim.stop()
    pump(tk_root, until=lambda: not sim.task.running)
    assert no_dialogs == []


def test_advanced_statistics_is_a_tab(tk_root, app, no_dialogs):
    sim = app.show_page("simulator")
    sim.show_advanced_stats()                                # nothing yet: a notice
    assert "Run something first" in sim.message_var.get()
    sim.sims_var.set("100")
    sim.cores_var.set("1")
    sim.start()
    pump(tk_root, until=lambda: sim.result is not None)
    sim.show_advanced_stats()
    assert sim.notebook.select() == str(sim.advanced_tab)
    assert "Plays per game" in sim.advanced_text.get("1.0", "end")


def test_cards_resize_with_the_window(tk_root, app, no_dialogs):
    player = app.show_page("player")
    app.root.geometry("1360x860")
    pump(tk_root)
    tk_root.after(200)
    pump(tk_root)
    big = player.box_views[0].height
    app.root.geometry("980x640")
    pump(tk_root)
    tk_root.after(200)
    pump(tk_root)
    small = player.box_views[0].height
    assert small < big
    view = player.box_views[0]
    view.fit(300, 400)
    big_font = view._size(0.3)
    view.fit(120, 160)
    assert view._size(0.3) < big_font                       # fonts follow the card


def test_closing_the_app_stops_running_work(tk_root, app, no_dialogs):
    sim = app.show_page("simulator")
    sim.sims_var.set("200000")
    sim.cores_var.set("1")
    sim.start()
    pump(tk_root, until=lambda: sim.progress_var.get() > 0)
    task = sim.task
    app.close()
    pump(tk_root, until=lambda: not task.running)


def test_ctrl_shortcuts_do_nothing_while_typing(tk_root, app, no_dialogs):
    player = app.show_page("player")
    player.new_game()                                       # the New Game panel
    combo = player.setup_panel.calls_combo
    combo.focus_force()
    pump(tk_root)
    combo.event_generate("<Control-h>", when="now")         # Tk's own: delete a character
    combo.event_generate("<Control-n>", when="now")
    assert app.current == "player" and player.mode == "setup"


def test_clicking_the_cards_left_text_keeps_the_shortcuts(tk_root, app, no_dialogs):
    from btb.gui_game import GameSettings
    player = app.show_page("player")
    player.new_game(GameSettings(0, 5))
    player.show_remaining_cards()
    player.cards_text.focus_force()                          # what a click does
    pump(tk_root)
    player.cards_text.event_generate("<Key-5>", when="now")
    assert player.selected == 4
    player.cards_text.event_generate("<Control-h>", when="now")
    assert app.current == "shortcuts"


def test_a_cleared_message_leaves_no_gap(tk_root, app, no_dialogs):
    sim = app.show_page("simulator")
    pump(tk_root)
    before = sim.export_buttons[0].winfo_y()
    sim.sims_var.set("abc")
    sim.start()                                              # an error shows...
    pump(tk_root)
    assert sim.message_label.winfo_ismapped()
    sim.clear()                                              # ...and goes away
    pump(tk_root)
    tk_root.after(100)
    pump(tk_root)
    assert sim.export_buttons[0].winfo_y() == before


def test_hidden_side_views_are_filled_when_shown(tk_root, app, no_dialogs):
    from btb.gui_game import GameSettings
    player = app.show_page("player")
    player.new_game(GameSettings(0, 5))
    player.odds_var.set(True)
    player.counts_var.set(True)
    player.on_odds_changed()
    assert player.side_view.get() == "count"
    assert not player.prob_tree.get_children()             # count view: table not filled
    player.show_probabilities()
    assert len(player.prob_tree.get_children()) == 9


def test_a_card_recentres_when_only_the_width_changes(tk_root):
    import tkinter as tk
    from btb import theme
    from btb.widgets import CardView
    window = tk.Toplevel(tk_root)
    view = CardView(window, theme.current())
    view.pack()
    view.fit(400, 200)
    height = view.height
    view.fit(600, 200)                                      # same card, wider space
    assert view.height == height
    x1, _y1, x2, _y2 = view.canvas.bbox("all")
    assert abs((x1 + x2) / 2 - 300) <= 4
    window.destroy()


def test_settings_page_reloads_cancels_and_saves_only_changes(tk_root, app, no_dialogs):
    from btb import settings
    app.show_page("player")
    page = app.show_page("settings")
    page.cores_var.set("1")                                  # not saved...
    app.show_page("home")
    app.show_page("settings")
    assert page.cores_var.get() == "Auto"                    # ...so it's gone on return
    page.theme_var.set("Midnight")
    page.cancel()                                            # Cancel: back where you were
    assert app.current == "home" and settings.get("theme") != "Midnight"
    app.show_page("settings")
    page.odds_var.set(not page.odds_var.get())
    press(app, tk_root, "<Escape>")                          # Escape works like Cancel
    assert app.current == "home"
    app.show_page("settings")
    settings.update(cpu_workers=3)                           # changed elsewhere meanwhile
    page.theme_var.set("Slate")
    page.save()
    assert settings.get("theme") == "Slate" and settings.get("cpu_workers") == 3
    assert page.saved_var.get().startswith("Saved")
    app.show_page("home")
    app.show_page("settings")
    assert page.saved_var.get() == ""


def test_the_simulator_picks_up_cores_changed_in_settings(tk_root, app, no_dialogs):
    sim = app.show_page("simulator")
    assert sim.cores_var.get() == "Auto"
    page = app.show_page("settings")
    page.cores_var.set("2")
    page.save()
    assert app.show_page("simulator").cores_var.get() == "2"
    sim.cores_var.set("1")
    sim._save_cores()
    page = app.show_page("settings")
    assert page.cores_var.get() == "1"                       # and the other way round


def test_clear_forgets_a_pending_big_run_warning(tk_root, app, no_dialogs):
    sim = app.show_page("simulator")
    sim.sims_var.set("3000000")
    sim.cores_var.set("1")
    sim.start()
    assert sim.task is None and "again" in sim.message_var.get()
    sim.clear()
    sim.start()                                              # warns again, doesn't run
    assert sim.task is None and "again" in sim.message_var.get()


def test_use_best_leaves_a_running_simulation_alone(tk_root, app, no_dialogs):
    sim = app.show_page("simulator")
    sim.sims_var.set("200000")
    sim.cores_var.set("1")
    sim.start()
    opt = app.show_page("optimizer")
    for name, value in (("games", "20"), ("jokers_max", "0"), ("moves_max", "1"),
                        ("threshold_max", "0"), ("seed", "3")):
        opt.vars[name].set(value)
    opt.confirm_var.set(False)
    opt.cores_var.set("1")
    opt.start()
    pump(tk_root, until=lambda: opt.sweep is not None)
    assert opt.use_best() is None and "still running" in opt.message_var.get()
    assert app.current == "optimizer" and sim.sims_var.get() == "200000"
    sim.stop()
    pump(tk_root, until=lambda: not sim.task.running)


# ------------------------------------------------- fits at small sizes -- #

def settle(root, limit: int = 3000) -> int:
    """Run the event loop until nothing is left to do; return how many
    events that took (a layout that keeps resizing itself never gets idle)."""
    import _tkinter
    count = 0
    while count < limit and root.tk.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
        count += 1
    return count


def reachable(widget, window) -> bool:
    """Fully inside the window, or inside a side panel that scrolls to it."""
    from btb.widgets import ScrollFrame
    left, top = window.winfo_rootx(), window.winfo_rooty()
    right, bottom = left + window.winfo_width(), top + window.winfo_height()
    x1, y1 = widget.winfo_rootx(), widget.winfo_rooty()
    x2, y2 = x1 + widget.winfo_width(), y1 + widget.winfo_height()
    if x1 < left - 1 or x2 > right + 1:
        return False
    if y2 <= bottom + 1:
        return True
    parent = widget.master
    while parent is not None:
        if isinstance(parent, ScrollFrame):
            return parent.scrolling and parent.visible(widget)
        parent = parent.master
    return False


def scroll_frames(widget):
    """Every ScrollFrame showing on screen (one on a hidden tab isn't laid out)."""
    from btb.widgets import ScrollFrame
    found = [widget] if isinstance(widget, ScrollFrame) and widget.winfo_ismapped() else []
    for child in widget.winfo_children():
        found += scroll_frames(child)
    return found


def scroll_matches(frame) -> bool:
    """The scrollbar shows exactly when the contents are taller than the
    panel, and the scroll area reaches the bottom of the contents."""
    need = frame.body.winfo_reqheight()
    view = frame.canvas.winfo_height()
    region = float(str(frame.canvas.cget("scrollregion")).split()[3])
    return frame.scrolling == (need > view + 1) and region >= need - 1


def important_widgets(app, key):
    page = app.page(key)
    if key in ("player", "assistant"):
        found = list(page.call_buttons.values()) + [v.canvas for v in page.box_views]
        found += [page.heading_label, page.history_list]
        if key == "assistant":
            found += [b for _c, b in page.flip_grid.buttons] + [page.flip_label]
        return found
    if key in ("simulator", "optimizer"):
        found = [page.run_button, page.notebook] + page.export_buttons
        return found + ([page.use_best_button, page.table] if key == "optimizer" else [])
    return []


@pytest.mark.parametrize("size", ["960x620", "1306x678"])
def test_every_page_fits_and_settles(tk_root, app, no_dialogs, size):
    from btb.gui_game import GameSettings
    app.root.geometry(size)
    for key in ("home", "player", "assistant", "simulator", "optimizer", "settings",
                "guide"):
        page = app.show_page(key)
        if key in ("player", "assistant"):
            page.odds_var.set(True)
            page.counts_var.set(True)
            if key == "player":
                page.new_game(GameSettings(1, 5))
            else:
                page.new_game(GameSettings(1, 5))
                for c in ("7♠", "K♥", "3♦", "9♣", "A♠", "2♦", "J♣", "8♥", "5♠"):
                    next(b for cc, b in page.picker_panel.grid.buttons
                         if cc.label() == c).invoke()
            page.on_odds_changed()
        pump(tk_root)
        tk_root.after(150)
        assert settle(tk_root) < 3000, f"{key} keeps re-laying itself out at {size}"
        for widget in important_widgets(app, key):
            assert reachable(widget, app.root), f"{key}: {widget} is cut off at {size}"
        # Change what the panels hold, then check their scrollbars kept up.
        changes = []
        if key in ("player", "assistant"):
            changes = [lambda v=v: (page.side_view.set(v), page.layout_side())
                       for v in ("odds", "cards", "count")]
        elif key in ("simulator", "optimizer"):
            changes = [lambda: page.error("A long message that wraps onto a few lines, "
                                          "to make the settings column taller."),
                       page.clear_message]
        for change in changes:
            change()
            pump(tk_root)
            tk_root.after(50)
            assert settle(tk_root) < 3000
            for frame in scroll_frames(page.frame):
                assert scroll_matches(frame), f"{key}: a panel's scrollbar is stale at {size}"
        if key in ("simulator", "optimizer"):          # the Advanced tab's charts
            page.notebook.select(page.advanced_tab)
            pump(tk_root)
            tk_root.after(100)
            assert settle(tk_root) < 3000, f"{key} Advanced keeps re-laying out at {size}"
            charts = page.advanced_charts
            assert charts.winfo_ismapped() and scroll_matches(charts)
            assert reachable(page.adv_charts[0].canvas, app.root)
            page.notebook.select(0)