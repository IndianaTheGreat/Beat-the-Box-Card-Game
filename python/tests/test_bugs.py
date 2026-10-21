"""
==============================================
V1 BUG REGRESSION TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_bugs.py
Status: ACTIVE
Version: 1.5
Last Updated: 2026-10-21
Last Tested: 2026-10-21 (pytest: 342 passed)

VERSION 1.5 CHANGES (2026-10-21):
- New, from the 2026-10-21 review: the shortcuts work after cancelling
  New Game or the Assistant's picker, the Assistant forgets the last
  game's flip pick, "1 card left", and numpad 5 is bound for Windows.
- The picker test no longer replaces the error hook on the shared Tk
  root (that hid callback errors from every later test); tk_root in
  conftest.py now collects them and fails the test.

VERSION 1.4 CHANGES (2026-10-20):
- New: the Assistant's card picker no longer freezes the window (run in
  a child process with a time limit), the card grid sizes itself from its
  panel's set width, FlipGuard, and the big and little jokers (either can
  be dealt, the other stays in the pile, both play alike).
- Each joker has its own flip choice ("🃏:big", "🃏:little"); Cards left
  is checked on the new Simple view.
- When the last box fails, the banner still names the call and the card
  that was drawn, after "The box wins".

VERSION 1.3 CHANGES (2026-10-20):
- Ctrl+L turns on the counts switch (cards left is part of the counts),
  and leaves the odds alone.

VERSION 1.2 CHANGES (2026-10-20):
- Game over and cards left are checked on the page (banner, side panel):
  there are no pop-up windows any more.

VERSION 1.1 CHANGES (2026-10-20):
- GUI checks use the new widgets (box_views, flip_choices) and the tile
  values ("45" instead of "Cards remaining: 45").
- New: the lean reading follows all three counts and says when they
  disagree (found in review: it only looked at the Advanced count).

VERSION 1.0 CHANGES (2026-10-20):
- New. One test per bug found in the original v1 suite.

DESCRIPTION:
-----------
Covers the Game Assistant, Game Player, strategy-text and shortcut bugs.
Engine-level tests run anywhere; GUI tests need Tk and a display.

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)
- tkinter and a display for GUI tests only; they skip otherwise

CLI USAGE:
---------
# From the python/ folder
python -m pytest tests/test_bugs.py
# Headless Linux, to include the GUI tests
xvfb-run python3 -m pytest
"""

import pytest

from btb import text
from btb.engine import (
    HIGHER, HIGHER_EQUAL, LOWER, LOWER_EQUAL, Card, Game, standard_deck,
)
from conftest import pump
from helpers import card, cards, fail, game


# ===================================================== Game Assistant (Aid) == #

def aid_game(box, jokers=2, inclusive=3):
    return Game.from_box(cards(*box), jokers=jokers, inclusive_calls=inclusive)


def test_bug_aid_drawn_joker_is_a_success():
    # Old: compare_cards() returned 'equal' for a joker, so Higher/Lower failed.
    g = aid_game(["5", "6", "7", "8", "9", "10", "J", "Q", "K"])
    r = g.play(0, HIGHER, drawn=Card.joker())
    assert r.success and g.box[0].is_joker


def test_bug_aid_joker_in_box_is_a_success():
    g = aid_game(["🃏", "6", "7", "8", "9", "10", "J", "Q", "K"])
    r = g.play(0, LOWER, drawn=card("A♠"))  # A is not lower, but a joker is wild
    assert r.success and g.box[0] == card("A♠")


def test_bug_aid_undo_refunds_the_inclusive_call():
    g = aid_game(["5", "6", "7", "8", "9", "10", "J", "Q", "K"], inclusive=3)
    g.play(3, HIGHER_EQUAL, drawn=card("2♦"))
    assert g.inclusive_left == 2
    g.undo()
    assert g.inclusive_left == 3 and card("2♦") in g.draw_pile


def test_bug_aid_drawing_one_of_two_jokers_leaves_the_other():
    # Old: the deck was filtered by text label, so both "🃏" went at once.
    g = aid_game(["5", "6", "7", "8", "9", "10", "J", "Q", "K"], jokers=2)
    g.play(0, HIGHER, drawn=Card.joker())
    assert sum(c.is_joker for c in g.draw_pile) == 1
    assert len(g.draw_pile) == 44


def test_bug_aid_dealing_one_of_two_jokers_leaves_the_other_in_the_pile():
    g = aid_game(["🃏", "6", "7", "8", "9", "10", "J", "Q", "K"], jokers=2)
    assert sum(c.is_joker for c in g.draw_pile) == 1
    assert len(g.draw_pile) == 54 - 9


def test_bug_aid_rejects_a_card_not_in_the_deck():
    with pytest.raises(ValueError):
        aid_game(["🃏", "🃏", "🃏", "8", "9", "10", "J", "Q", "K"], jokers=2)


def test_bug_aid_labels_refresh_after_each_play(tk_root, no_dialogs):
    from btb.gui_game import AssistantGUI, GameSettings
    import tkinter as tk
    gui = AssistantGUI(tk.Toplevel(tk_root))
    gui.new_game(GameSettings(jokers=2, inclusive_calls=3),
                 box=cards("5", "6", "7", "8", "9", "10", "J", "Q", "K"))
    assert gui.cards_remaining_var.get() == "45"
    # Each joker has its own entry now: "🃏:big" and "🃏:little".
    assert [k for k in gui.flip_choices() if k.startswith("🃏")] == ["🃏:big", "🃏:little"]
    gui.drawn_var.set("🃏:big")
    gui.box_clicked(3)
    gui.make_call(HIGHER_EQUAL)
    assert gui.cards_remaining_var.get() == "44"
    assert gui.inclusive_var.get() == "2"
    assert "🃏:little" in gui.flip_choices()  # the other joker is still there
    assert "🃏:big" not in gui.flip_choices()
    assert gui.box_views[3].describe() == "🃏"
    gui.undo()
    assert gui.inclusive_var.get() == "3"


# ================================================================ Player ==== #

def test_bug_player_reports_game_over_when_the_pile_runs_out():
    g = game(["5"], ["9"])
    r = g.play(0, HIGHER)
    assert r.game_over and r.won and g.is_over


def test_bug_player_shows_a_game_over_message(tk_root, no_dialogs):
    from btb.gui_game import PlayerGUI
    import tkinter as tk
    gui = PlayerGUI(tk.Toplevel(tk_root))
    gui.game = game(["5"], ["9"])
    gui.box_clicked(0)
    gui.make_call(HIGHER)
    assert "You beat the box!" in gui.banner_var.get() and gui.banner_kind == "good"
    gui.game = game(["K"] * 9, ["2"] * 9 + ["3"])
    for pos in range(9):
        gui.box_clicked(pos)
        gui.make_call(HIGHER)
    assert gui.banner_var.get().startswith("The box wins") and gui.banner_kind == "bad"
    # The losing play stays in view: the call and the card that was drawn.
    assert "Higher on K" in gui.banner_var.get() and "drew 2" in gui.banner_var.get()
    assert "All nine boxes failed" in gui.status_var.get()
    assert no_dialogs == []   # the banner says it; nothing pops up


def test_bug_player_odds_denominator_is_the_pile_size():
    # Old: divided by (total + joker_count), so jokers were counted twice.
    g = game(["8"], ["🃏", "2", "9", "Q"])
    o = g.odds(0)
    assert o.higher == pytest.approx(3 / 4)   # 9, Q, joker
    assert o.lower == pytest.approx(2 / 4)    # 2, joker


def test_bug_player_inclusive_odds_count_jokers_once():
    # Old: jokers were added to higher, lower and equal, so H/E got 2x jokers.
    g = game(["8"], ["🃏", "2", "8", "Q"])
    o = g.odds(0)
    assert o.higher_equal == pytest.approx(3 / 4)  # 8, Q, joker
    assert o.lower_equal == pytest.approx(3 / 4)   # 2, 8, joker
    assert o.exact == pytest.approx(2 / 4)         # 8, joker
    assert o.higher_equal <= 1 and o.lower_equal <= 1


def test_bug_player_joker_in_box_shows_certain_odds():
    g = game(["🃏"], ["2", "8", "A"])
    o = g.odds(0)
    assert (o.higher, o.lower, o.higher_equal, o.lower_equal, o.exact) == (1, 1, 1, 1, 1)


def test_bug_player_recovery_does_not_double_count_the_card():
    g = game(["7", "K", "8", "8", "8", "8", "8", "8", "8"], ["5", "7"], inclusive=1)
    g.play(1, HIGHER)
    g.play(0, LOWER_EQUAL)
    before = list(g.counts)
    g.recover(1)
    assert g.counts == before


def test_bug_player_keys_and_undo_before_a_game_do_not_crash(tk_root, no_dialogs):
    from btb.gui_game import AssistantGUI, PlayerGUI
    import tkinter as tk
    for cls in (PlayerGUI, AssistantGUI):
        gui = cls(tk.Toplevel(tk_root))
        gui.box_clicked(4)
        for call in (HIGHER, LOWER, HIGHER_EQUAL, LOWER_EQUAL):
            gui.make_call(call)
        gui.undo()
        gui.skip_recovery()
        gui.show_probabilities()
        gui.show_remaining_cards()
        gui.root.focus_force()
        pump(tk_root)
        for seq in ("<KeyPress-w>", "<KeyPress-5>", "<Control-z>", "<Control-p>"):
            gui.root.event_generate(seq.replace("KeyPress-", "Key-"), when="now")
        assert gui.game is None and "New Game" in gui.status_var.get()


def test_bug_player_single_click_handler_selects_then_calls(tk_root, no_dialogs):
    # Old: two card_button_click definitions (the second silently won) plus
    # dead select_card/init_styles. Now one handler selects, a call plays.
    from btb.gui_game import PlayerGUI
    import tkinter as tk
    gui = PlayerGUI(tk.Toplevel(tk_root))
    assert not hasattr(gui, "card_button_click")
    assert not hasattr(gui, "select_card") and not hasattr(gui, "init_styles")
    gui.game = game(["4", "9"], ["J", "2", "3"])
    gui.refresh()
    assert gui.call_buttons[HIGHER].instate(["disabled"])
    gui.box_clicked(0)
    assert gui.selected == 0 and gui.box_views[0].state == "selected"
    assert not gui.call_buttons[HIGHER].instate(["disabled"])
    gui.make_call(HIGHER)
    assert gui.game.box[0] == card("J♠")


# ======================================================= Strategy & keys ==== #

def test_bug_strategy_text_reads_the_count_the_right_way():
    guide = text.STRATEGY_GUIDE
    assert "POSITIVE count" in guide and "MORE LOW" in guide
    pos = guide.index("POSITIVE count")
    assert guide.index("Lean LOWER", pos) < guide.index("NEGATIVE count")
    assert "Lean HIGHER" in guide[guide.index("NEGATIVE count"):]


def test_bug_count_sign_matches_what_remains():
    # A positive count means high cards have been seen, so more LOW cards
    # remain in the pile (the old strategy text said the opposite).
    g = Game.from_box(cards("A", "A", "A", "A", "K", "K", "K", "K", "Q"), 0, 0)
    assert all(c > 0 for c in g.counts)
    low = sum(1 for c in g.draw_pile if 2 <= c.rank <= 7)
    high = sum(1 for c in g.draw_pile if c.rank >= 9)
    assert low > high


def test_count_lean_follows_rules_md():
    from btb.engine import count_lean
    assert count_lean(3) == LOWER       # high cards seen -> more low cards left
    assert count_lean(-2) == HIGHER
    assert count_lean(0) is None


def test_bug_lean_message_reads_all_three_counts(tk_root, no_dialogs):
    # A, 7 and 6 make the Basic count -1 (lean Higher) but the Advanced count
    # +1 (lean Lower). The old message only read the Advanced count.
    from btb.gui_game import PlayerGUI
    import tkinter as tk
    gui = PlayerGUI(tk.Toplevel(tk_root))
    g = Game.from_cards(cards("A", "7", "6", "8", "8", "8", "8", "8", "8"), cards("2", "3"))
    assert g.counts == [-1, 0, 1]    # Basic, Weighted, Advanced
    gui.game = g
    gui.refresh()
    assert [v.get() for v in gui.count_vars] == ["-1 ▲", "0", "+1 ▼"]
    assert gui.lean_var.get() == "The counts disagree: no clear lean"
    assert PlayerGUI.lean_message([LOWER, None, LOWER]).endswith("lean Lower ▼")
    assert PlayerGUI.lean_message([None, None, None]) == "Even count: no lean"


def test_bug_remaining_cards_shortcut_does_not_clash_with_copy():
    sequences = [s.lower() for *_, seqs in text.SHORTCUTS for s in seqs]
    assert "<control-c>" not in sequences
    assert "<control-l>" in sequences
    keys = [k for k, *_ in text.SHORTCUTS]
    assert len(keys) == len(set(keys))


def test_bug_remaining_cards_shortcut_works(tk_root, no_dialogs):
    from btb.gui_game import PlayerGUI, GameSettings
    import tkinter as tk
    gui = PlayerGUI(tk.Toplevel(tk_root))
    gui.new_game(GameSettings(0, 5))
    gui.root.focus_force()
    pump(tk_root)
    gui.root.event_generate("<Control-l>", when="now")
    assert gui.counts_var.get() and gui.side_view.get() == "cards"   # Ctrl+L turns counts on
    assert not gui.odds_var.get()
    assert gui.cards_frame.winfo_manager() == "pack"          # shown beside the board
    view = gui.cards_view                                     # the Simple table
    texts = [view.canvas.itemcget(i, "text") for i in view.canvas.find_all()
             if view.canvas.type(i) == "text"]
    assert "Total" in texts and "43" in texts

# ================================================== Found on Windows (v1.3) == #

FREEZE_SCRIPT = r"""
import os, sys, time, tempfile
os.environ["BTB_SETTINGS_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, os.getcwd())
import tkinter as tk
from btb.app import App
root = tk.Tk()
app = App(root)
root.geometry("1306x678")
page = app.show_page("assistant")
page.show_setup()
page.setup_panel.joker_var.set("2")
page.setup_panel.calls_var.set("3")
page.setup_panel.start()                     # the nine-card picker, before any drawing
end = time.time() + 1.0
while time.time() < end:
    root.update()
jokers = [b for c, b in page.picker_panel.grid.buttons if c.is_joker]
for button in jokers:
    button.invoke()
root.update()
print("picked", len(page.picker_panel.picked), "jokers")
root.destroy()
"""


def test_bug_assistant_card_picker_no_longer_freezes_the_window(tk_root):
    # Seen on Windows as "Not responding" (and in the tests, a hang): before
    # the window was drawn, the card grid sized its font from a panel that
    # was only as wide as the grid itself, so big font -> wide panel -> small
    # font -> narrow panel -> big font, forever. Run in a child process with
    # a time limit, so a regression fails here instead of hanging the run.
    import os
    import subprocess
    import sys
    folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    done = subprocess.run([sys.executable, "-c", FREEZE_SCRIPT], cwd=folder, timeout=60,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "picked 2 jokers" in done.stdout


def test_bug_card_grid_sizes_itself_from_the_panel_width_it_was_given(tk_root):
    import tkinter as tk
    from btb import theme as themes
    from btb.widgets import CardGrid, ScrollFrame
    window = tk.Toplevel(tk_root)
    panel = ScrollFrame(window, width=340)
    panel.pack()
    grid = CardGrid(panel.body, themes.current(), lambda c, b: None, jokers=2)
    grid.pack()
    assert grid._room() == 340                     # the set width, before any drawing
    panel.set_width(250)
    assert grid._room() == 250


def test_bug_flip_guard_stops_a_layout_that_keeps_resizing_itself():
    pytest.importorskip("tkinter")
    from btb.widgets import FlipGuard
    guard = FlipGuard()
    allowed = [guard.allow() for _ in range(50)]   # 50 flips in an instant
    assert allowed.count(True) == FlipGuard.MAX_CHANGES and not allowed[-1]


def test_bug_assistant_can_deal_either_joker_into_the_box(tk_root, no_dialogs):
    import tkinter as tk
    from btb.gui_game import AssistantGUI, GameSettings
    gui = AssistantGUI(tk.Toplevel(tk_root))
    gui.new_game(GameSettings(jokers=2, inclusive_calls=3))
    buttons = {c.key(): b for c, b in gui.picker_panel.grid.buttons}
    assert str(buttons["🃏:big"].cget("text")) == "Big Joker"
    assert str(buttons["🃏:little"].cget("text")) == "Little Joker"
    buttons["🃏:little"].invoke()                  # the little one first
    for key in ("2♠", "3♠", "4♠", "5♠", "6♠", "7♠", "8♠", "9♠"):
        buttons[key].invoke()
    assert gui.mode == "play" and gui.game.box[0].kind == "little"
    assert [c.kind for c in gui.game.draw_pile if c.is_joker] == ["big"]   # the other stays
    assert gui.flip_choices().count("🃏:big") == 1 and "🃏:little" not in gui.flip_choices()
    gui.drawn_var.set("🃏:big")
    gui.box_clicked(1)
    gui.make_call(HIGHER)
    assert gui.game.box[1].kind == "big" and "Big Joker" in gui.banner_var.get()


def test_bug_jokers_keep_their_kind_but_play_exactly_alike():
    from btb.engine import JOKER_KINDS, take_card
    big, little = Card.joker("big"), Card.joker("little")
    assert big == little == Card.joker() and hash(big) == hash(little)   # same in play
    assert (big.name, little.name, Card.joker().name) == ("Big Joker", "Little Joker", "Joker")
    assert Card.parse(big.key()).kind == "big" and Card.parse("little joker").kind == "little"
    assert [c.kind for c in standard_deck(2) if c.is_joker] == list(JOKER_KINDS)
    pile = standard_deck(2)
    assert take_card(pile, little).kind == "little"
    assert [c.kind for c in pile if c.is_joker] == ["big"]
    g = Game.new(2, 5, seed=4)
    kinds = sorted(c.kind for c in g.box + g.draw_pile if c.is_joker)
    assert kinds == ["big", "little"]
    with pytest.raises(ValueError):
        Card(5, "♠", "big")                        # only a joker has a kind


def test_bug_a_rebuilt_card_picker_leaves_no_dead_resize_handlers(tk_root, no_dialogs):
    # Found in review: each picker grid bound <Configure> on the side panel,
    # which outlives it, so old grids kept trying to resize destroyed buttons.
    import tkinter as tk
    from btb.gui_game import AssistantGUI, GameSettings
    gui = AssistantGUI(tk.Toplevel(tk_root))
    canvas = gui.side_scroll.canvas
    before = canvas.bind("<Configure>")
    for _ in range(5):
        gui.new_game(GameSettings(jokers=2, inclusive_calls=3))   # a new picker each time
    pump(tk_root)
    assert canvas.bind("<Configure>").count("if {") <= before.count("if {") + 1   # one live picker
    gui.side_scroll.set_width(420)
    pump(tk_root)
    gui.side_scroll.set_width(330)
    pump(tk_root)
    assert tk_root.callback_errors == []   # tk_root also fails the test on any


def test_bug_the_flip_grid_shows_only_the_jokers_in_this_game(tk_root, no_dialogs):
    import tkinter as tk
    from btb.gui_game import AssistantGUI, GameSettings
    gui = AssistantGUI(tk.Toplevel(tk_root))
    shown = lambda: [c.kind for c, b in gui.flip_grid.buttons if c.is_joker and b.winfo_manager()]
    assert shown() == []
    gui.new_game(GameSettings(jokers=1), box=cards("5", "6", "7", "8", "9", "10", "J", "Q", "K"))
    assert shown() == ["big"]
    gui.new_game(GameSettings(jokers=2), box=cards("5", "6", "7", "8", "9", "10", "J", "Q", "K"))
    assert shown() == ["big", "little"]
    gui.new_game(GameSettings(jokers=0), box=cards("5", "6", "7", "8", "9", "10", "J", "Q", "K"))
    assert shown() == []


def test_bug_a_kindless_joker_takes_and_returns_the_card_from_the_pile():
    from btb.engine import take_card
    pile = standard_deck(2)
    taken = take_card(pile, Card.joker())          # no kind asked for: the first joker
    assert taken.kind == "big" and [c.kind for c in pile if c.is_joker] == ["little"]

# ============================================== Found in the 2026-10-21 review == #

def _focused_key(window, root, sequence):
    """Press a key on whatever has the focus now (the way a real key press
    arrives), without first moving the focus back to the window."""
    pump(root)
    target = window.focus_get() or window
    target.event_generate(sequence, when="now")
    pump(root)


@pytest.mark.parametrize("how", ["player", "assistant settings", "assistant picker"])
def test_bug_keys_work_after_cancelling_a_new_game(tk_root, no_dialogs, how):
    # Old: New Game put the focus in the Inclusive calls box, and Cancel left
    # it there (hidden). That box takes typing, so every shortcut was ignored.
    import tkinter as tk
    from btb.gui_game import AssistantGUI, GameSettings, PlayerGUI
    window = tk.Toplevel(tk_root)
    gui = (PlayerGUI if how == "player" else AssistantGUI)(window)
    gui.game = game(["5", "6", "7"], ["K", "A", "Q"])
    gui.refresh()
    window.focus_force()
    gui.new_game()                                   # the settings panel, focus in its box
    pump(tk_root)
    if how == "assistant picker":
        gui.new_game(GameSettings())                 # on to the nine-card picker
        pump(tk_root)
        gui.cancel_pick()
    else:
        gui.cancel_setup()
    _focused_key(window, tk_root, "<Key-7>")         # top-left box
    assert gui.selected == 0
    if how != "player":
        gui.drawn_var.set(gui.game.draw_pile[0].key())   # the Assistant needs the flip
    _focused_key(window, tk_root, "<Key-w>")         # Higher: 5 -> K
    assert gui.game.box[0].rank == 13


def test_bug_assistant_forgets_the_last_games_flip_pick(tk_root, no_dialogs):
    # Old: a flip picked but not played stayed picked in the next game when
    # that card was still in the new pile.
    import tkinter as tk
    from btb.gui_game import AssistantGUI, GameSettings
    gui = AssistantGUI(tk.Toplevel(tk_root))
    box = cards("5", "6", "7", "8", "9", "10", "J", "Q", "2")
    gui.new_game(GameSettings(jokers=0), box=box)
    gui.drawn_var.set(Card.parse("K♥").key())        # picked, never played
    gui.new_game(GameSettings(jokers=0), box=box)
    assert gui.drawn_var.get() == ""


@pytest.mark.parametrize("left, words", [(1, "with 1 card left"), (2, "with 2 cards left")])
def test_bug_losing_message_counts_cards_in_words(tk_root, no_dialogs, left, words):
    # Old: "with 1 cards left".
    import tkinter as tk
    from btb.gui_game import PlayerGUI
    gui = PlayerGUI(tk.Toplevel(tk_root))
    gui.game = game(["K"] * 9, ["2"] * 9 + ["3"] * left)
    gui.refresh()
    for pos in range(9):
        gui.box_clicked(pos)
        gui.make_call(HIGHER)                        # a 2 on a K: fails
    assert gui.game.lost and gui.game.cards_left == left
    assert words in gui.status_var.get()


def test_bug_numpad_5_with_numlock_off_is_bound_for_windows_too(tk_root, no_dialogs):
    # The middle numpad key with NumLock off is KP_Begin on X11 but Clear on
    # Windows; only KP_Begin was bound, so it did nothing on Windows. (A test
    # display can't send a Windows Clear key, so its binding is checked.)
    import tkinter as tk
    from btb.gui_game import KEYPAD_NUMLOCK_OFF, PlayerGUI
    window = tk.Toplevel(tk_root)
    gui = PlayerGUI(window)
    gui.game = game(["5", "6", "7", "8", "9"], ["K"])
    gui.refresh()
    assert KEYPAD_NUMLOCK_OFF["5"] == ("KP_Begin", "Clear")
    assert set(KEYPAD_NUMLOCK_OFF) == set(text.POSITION_KEYS)
    assert "<Key-Clear>" in window.bind()
    window.focus_force()
    _focused_key(window, tk_root, "<KeyPress-KP_Begin>")
    assert gui.selected == text.POSITION_KEYS["5"]


def test_bug_a_tiny_threshold_step_is_refused_before_building_the_list(
        tk_root, no_dialogs, monkeypatch):
    # Old: the Optimizer built every threshold first (3 million for a step of
    # 0.00001, freezing the window) and only then checked the size.
    import tkinter as tk
    from btb import gui_sim
    built = []
    real = gui_sim.float_range
    monkeypatch.setattr(gui_sim, "float_range", lambda *a: built.append(a) or real(*a))
    gui = gui_sim.OptimizerGUI(tk.Toplevel(tk_root))
    for step in ("0.00001", "1e-320"):
        gui.vars["step"].set(step)
        gui.start()
        assert gui.task is None and "configurations" in gui.message_var.get()
    assert built == []


@pytest.mark.parametrize("step", ["nan", "inf", "-inf"])
def test_bug_a_step_that_isnt_a_number_gets_a_message(tk_root, no_dialogs, step):
    # Old: "nan" got past "step <= 0" and crashed inside Tk's callback, so
    # the run silently never started; "inf" said "no legal configurations".
    import tkinter as tk
    from btb.gui_sim import OptimizerGUI
    gui = OptimizerGUI(tk.Toplevel(tk_root))
    gui.vars["step"].set(step)
    gui.start()
    assert gui.task is None
    assert "Threshold step must be a number greater than 0" in gui.message_var.get()


def test_bug_a_big_seed_shows_the_seed_that_was_played(tk_root, no_dialogs):
    # Old: 4294967303 was shown (Seed tile, report, export name) while the run
    # and the exported data used 4294967303 & 0xFFFFFFFF = 7.
    import tkinter as tk
    from btb.gui_sim import OptimizerGUI, SimulatorGUI, _parse_seed
    assert _parse_seed("4294967303") == 7 and _parse_seed("4294967295") == 4294967295
    sim_page = SimulatorGUI(tk.Toplevel(tk_root))
    sim_page.sims_var.set("5")
    sim_page.seed_var.set(str(2**32 + 7))
    sim_page.cores_var.set("1")
    sim_page.start()
    pump(tk_root, until=lambda: sim_page.result is not None)
    assert sim_page.seed == sim_page.result.seed == 7
    assert "seed7" in sim_page.export_name()
    opt = OptimizerGUI(tk.Toplevel(tk_root))
    opt.vars["seed"].set(str(2**33 + 9))
    assert opt.validate()[2] == 9


def test_bug_settings_say_so_when_the_file_cant_be_written(
        tk_root, no_dialogs, monkeypatch):
    # Old: "Saved." even when writing the settings file failed.
    import tkinter as tk
    import main
    from btb import settings
    from btb.gui_sim import SimulatorGUI
    monkeypatch.setattr(settings, "save", lambda values: False)
    app = main.MainApplication(tk.Toplevel(tk_root))
    page = app.show_page("settings")
    page.theme_var.set("Slate")
    page.save()
    assert page.saved_var.get().startswith("Couldn't save")
    sim_page = SimulatorGUI(tk.Toplevel(tk_root))
    sim_page.cores_var.set("1")
    sim_page._save_cores()
    assert "Couldn't save the CPU cores choice" in sim_page.message_var.get()


def test_bug_clear_is_off_while_a_run_is_going(tk_root, no_dialogs):
    # Old: Clear stayed clickable and blanked the page while the run went on.
    import tkinter as tk
    from btb.gui_sim import SimulatorGUI
    gui = SimulatorGUI(tk.Toplevel(tk_root))
    gui.sims_var.set("200000")
    gui.seed_var.set("1")
    gui.cores_var.set("1")
    assert not gui.clear_button.instate(["disabled"])
    gui.start()
    assert gui.task is not None and gui.clear_button.instate(["disabled"])
    gui.stop()
    pump(tk_root, until=lambda: not gui.task.running, timeout=30)
    pump(tk_root, until=lambda: not gui.clear_button.instate(["disabled"]))


def test_bug_never_more_than_61_helpers_on_windows(monkeypatch):
    # Windows can't run a process pool with more than 61 helpers; a PC with
    # more cores crashed the run instead of using 61.
    import sys
    from btb import system
    monkeypatch.setattr(system, "cpu_count", lambda: 128)
    monkeypatch.setattr(system, "scan", lambda: type("Scan", (), {"workers": 96})())
    monkeypatch.setattr(sys, "platform", "win32")
    assert system.resolve_workers("100") == 61
    assert system.resolve_workers("auto") == 61
    assert system.resolve_workers("8") == 8
    monkeypatch.setattr(sys, "platform", "linux")
    assert system.resolve_workers("100") == 100
    assert system.resolve_workers("auto") == 96