"""
==============================================
V1 BUG REGRESSION TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_bugs.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

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
pytest
# Headless Linux, to include the GUI tests
xvfb-run pytest
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
    assert gui.cards_remaining_var.get() == "Cards remaining: 45"
    assert gui.drawn_combo["values"].count("🃏") == 1  # two jokers, one entry
    gui.drawn_var.set("🃏")
    gui.box_clicked(3)
    gui.make_call(HIGHER_EQUAL)
    assert gui.cards_remaining_var.get() == "Cards remaining: 44"
    assert gui.inclusive_var.get() == "Inclusive calls: 2"
    assert "🃏" in gui.drawn_combo["values"]  # the second joker is still there
    assert gui.box_buttons[3].cget("text") == "🃏"
    gui.undo()
    assert gui.inclusive_var.get() == "Inclusive calls: 3"


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
    assert no_dialogs and no_dialogs[-1][1] == "You beat the box!"
    gui.game = game(["A"] * 9, ["2"] * 9 + ["3"])
    for pos in range(9):
        gui.box_clicked(pos)
        gui.make_call(HIGHER)
    assert no_dialogs[-1][1] == "The box wins"


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
    from btb.gui_game import COLORS, PlayerGUI
    import tkinter as tk
    gui = PlayerGUI(tk.Toplevel(tk_root))
    assert not hasattr(gui, "card_button_click")
    assert not hasattr(gui, "select_card") and not hasattr(gui, "init_styles")
    gui.game = game(["4", "9"], ["J", "2", "3"])
    gui.refresh()
    assert gui.call_buttons[HIGHER].instate(["disabled"])
    gui.box_clicked(0)
    assert gui.selected == 0 and gui.box_buttons[0].cget("bg") == COLORS["selected"]
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
    assert gui.cards_window is not None and gui.cards_window.winfo_exists()
    assert "Total" in gui.cards_text.get("1.0", "end") and " 43" in gui.cards_text.get("1.0", "end")