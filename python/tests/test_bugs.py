"""
==============================================
V1 BUG REGRESSION TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_bugs.py
Status: ACTIVE
Version: 1.4
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 308 passed)

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
    errors = []
    tk_root.report_callback_exception = lambda *exc: errors.append(exc)
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
    assert errors == []


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