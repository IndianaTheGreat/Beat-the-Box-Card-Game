"""
==============================================
RULES.MD TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_rules.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. One test per rule in RULES.md, section by section.

DESCRIPTION:
-----------
The executable spec. The Phase 2 TypeScript port must pass the same cases.
Includes golden seeded deals cross-checked against a JavaScript shuffle.

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

from btb.engine import (
    BOX_SIZE, CALLS, COUNT_TABLES, HIGHER, HIGHER_EQUAL, LOWER, LOWER_EQUAL,
    Card, Game, RulesError, Rng, count_values, max_inclusive_calls,
    shuffled_deck, standard_deck,
)
from helpers import card, cards, fail, game


# ---------------------------------------------------------------- Setup ---- #

@pytest.mark.parametrize("jokers, pile", [(0, 43), (1, 44), (2, 45)])
def test_setup_deals_nine_into_the_box_and_the_rest_to_the_pile(jokers, pile):
    g = Game.new(jokers=jokers, inclusive_calls=0, seed=7)
    assert len(g.box) == BOX_SIZE and all(c is not None for c in g.box)
    assert len(g.draw_pile) == pile
    assert sorted(g.box + g.draw_pile, key=repr) == sorted(standard_deck(jokers), key=repr)


def test_setup_deck_is_52_distinct_cards_plus_jokers():
    deck = standard_deck(2)
    assert len(deck) == 54
    assert len(set(c for c in deck if not c.is_joker)) == 52
    assert sum(c.is_joker for c in deck) == 2


def test_setup_seeded_shuffle_is_reproducible():
    assert shuffled_deck(1, seed=42) == shuffled_deck(1, seed=42)
    assert shuffled_deck(1, seed=42) != shuffled_deck(1, seed=43)


def test_setup_rng_matches_reference_mulberry32():
    # Reference values from the JavaScript Mulberry32 implementation, so the
    # TypeScript port deals identical seeded games.
    rng = Rng(12345)
    assert [rng.next_float() for _ in range(3)] == [
        0.9797282677609473, 0.3067522644996643, 0.484205421525985]


@pytest.mark.parametrize("jokers, seed, box", [
    (0, 1, "K♥ 7♣ Q♥ Q♠ 6♣ 7♦ K♣ 4♣ 8♠"),
    (2, 2026, "6♣ 5♠ 10♣ 3♥ Q♥ A♥ 6♥ J♦ A♦"),
])
def test_setup_seeded_deal_is_pinned(jokers, seed, box):
    # Golden values, cross-checked against a JavaScript Fisher-Yates over
    # Mulberry32 (i from n-1 down to 1, j = floor(rand * (i + 1))) on the
    # standard_deck order (suits ♠♥♦♣, ranks 2..A, then jokers).
    g = Game.new(jokers, 0, seed=seed)
    assert " ".join(str(c) for c in g.box) == box


# ----------------------------------------------------------- Card ranks ---- #

def test_ranks_aces_are_high():
    g = game(["K"], ["A"])
    assert g.play(0, HIGHER).success


def test_ranks_two_is_lowest():
    g = game(["3"], ["2"])
    assert g.play(0, LOWER).success


def test_ranks_suits_do_not_matter():
    g = game(["8♠"], ["8♥"], inclusive=1)
    r = g.play(0, HIGHER_EQUAL)
    assert r.success and r.exact_match


def test_card_labels_round_trip():
    for c in standard_deck(1):
        assert Card.parse(str(c)) == c


# --------------------------------------------------------- Taking a turn --- #

def test_turn_higher_wins_on_strictly_higher():
    assert game(["4♣"], ["J♥"]).play(0, HIGHER).success


def test_turn_lower_wins_on_strictly_lower():
    assert game(["9"], ["5"]).play(0, LOWER).success


def test_turn_correct_call_puts_drawn_card_on_the_box():
    g = game(["4♣"], ["J♥", "3"])
    g.play(0, HIGHER)
    assert g.box[0] == card("J♥")
    assert g.draw_pile == [card("3", 1)]


def test_turn_wrong_call_fails_the_box_holding_the_old_card():
    g = game(["4♣"], ["2♥", "3"])
    r = g.play(0, HIGHER)
    assert not r.success
    assert g.box[0] is None
    assert g.failed == {0: card("4♣")}


def test_turn_failed_box_cannot_be_played():
    g = game(["4♣"], ["2♥", "3"])
    g.play(0, HIGHER)
    with pytest.raises(RulesError):
        g.play(0, LOWER)


@pytest.mark.parametrize("call", [HIGHER, LOWER])
def test_turn_same_rank_on_a_plain_call_is_a_loss(call):
    g = game(["8♦"], ["8♠"])
    r = g.play(0, call)
    assert not r.success and g.failed == {0: card("8♦")}


def test_turn_plain_calls_are_free():
    g = game(["5"], ["9"], inclusive=3)
    g.play(0, HIGHER)
    assert g.inclusive_left == 3


# ------------------------------------------------------- Inclusive calls --- #

@pytest.mark.parametrize("call", [HIGHER_EQUAL, LOWER_EQUAL])
def test_inclusive_tie_counts_as_a_win(call):
    g = game(["8♦"], ["8♠"], inclusive=1)
    assert g.play(0, call).success


def test_inclusive_still_wins_on_strict_direction():
    assert game(["8"], ["Q"], inclusive=1).play(0, HIGHER_EQUAL).success
    assert game(["8"], ["3"], inclusive=1).play(0, LOWER_EQUAL).success


def test_inclusive_call_is_spent_when_it_wins():
    g = game(["5"], ["9"], inclusive=2)
    g.play(0, HIGHER_EQUAL)
    assert g.inclusive_left == 1


def test_inclusive_call_is_spent_when_it_loses():
    g = game(["5"], ["3"], inclusive=2)
    assert not g.play(0, HIGHER_EQUAL).success
    assert g.inclusive_left == 1


def test_inclusive_call_needs_one_left():
    g = game(["5"], ["9"], inclusive=0)
    with pytest.raises(RulesError):
        g.play(0, HIGHER_EQUAL)
    assert len(g.draw_pile) == 1  # nothing was flipped


def test_inclusive_exact_match_earns_a_recovery():
    g = game(["7♥", "5"], ["2", "7♣"], inclusive=1)
    fail(g, 1)
    r = g.play(0, LOWER_EQUAL)
    assert r.success and r.exact_match and r.recovery_earned and r.recovery_pending


def test_inclusive_win_without_exact_match_earns_no_recovery():
    g = game(["7", "5"], ["2", "6"], inclusive=1)
    fail(g, 1)
    r = g.play(0, LOWER_EQUAL)
    assert r.success and not r.recovery_earned and not g.recovery_pending


def test_plain_call_never_earns_a_recovery():
    g = game(["7", "5", "9"], ["2", "J", "Q"])
    fail(g, 1)
    r = g.play(0, HIGHER)
    assert r.success and not r.recovery_earned


# ---------------------------------------------------------------- Jokers --- #

@pytest.mark.parametrize("call", [HIGHER, LOWER])
def test_joker_drawn_plain_call_succeeds(call):
    g = game(["8"], ["🃏"])
    r = g.play(0, call)
    assert r.success and not r.recovery_earned
    assert g.box[0].is_joker  # the joker is placed on the box


@pytest.mark.parametrize("call", [HIGHER_EQUAL, LOWER_EQUAL])
def test_joker_drawn_inclusive_call_succeeds_and_earns_recovery(call):
    g = game(["8", "5"], ["2", "🃏"], inclusive=1)
    fail(g, 1)
    r = g.play(0, call)
    assert r.success and r.exact_match and r.recovery_pending


@pytest.mark.parametrize("call", [HIGHER, LOWER])
def test_joker_in_box_plain_call_succeeds(call):
    g = game(["🃏"], ["5"])
    r = g.play(0, call)
    assert r.success and not r.recovery_earned
    assert g.box[0] == card("5")


@pytest.mark.parametrize("call", [HIGHER_EQUAL, LOWER_EQUAL])
def test_joker_in_box_inclusive_call_succeeds_and_earns_recovery(call):
    # RULES.md Example 4: a joker counts as an exact match for any card.
    g = game(["🃏", "5"], ["2", "5♦"], inclusive=1)
    fail(g, 1)
    r = g.play(0, call)
    assert r.success and r.exact_match and r.recovery_pending
    assert g.box[0] == card("5♦")


def test_joker_drawn_onto_a_box_makes_the_next_play_there_certain():
    g = game(["8"], ["🃏", "8"])
    g.play(0, HIGHER)
    assert g.play(0, LOWER).success  # an 8 "lower" than the joker still wins


# -------------------------------------------------------------- Recovery --- #

def test_recovery_example_3_returns_the_card_it_failed_on():
    # RULES.md Example 3.
    g = game(["7♥", "K♠"], ["5", "7♣", "2"], inclusive=1)
    assert not g.play(1, HIGHER).success
    r = g.play(0, LOWER_EQUAL)
    assert r.success and r.recovery_pending
    assert g.box[0] == card("7♣")  # the play resolved first
    assert g.recover(1) == card("K♠")
    assert g.box[1] == card("K♠") and g.failed == {}
    assert g.play(1, LOWER).success  # "an easy Lower"


def test_recovery_is_chosen_after_the_flip():
    g = game(["7", "5"], ["2", "7"], inclusive=1)
    fail(g, 1)
    r = g.play(0, LOWER_EQUAL)
    # The drawn card is known and on the box before any choice is made.
    assert r.drawn.rank == 7 and g.box[0] == r.drawn and g.recovery_pending


def test_recovery_can_be_skipped():
    g = game(["7", "5"], ["2", "7", "9"], inclusive=1)
    fail(g, 1)
    g.play(0, LOWER_EQUAL)
    g.skip_recovery()
    assert not g.recovery_pending and 1 in g.failed
    g.play(0, HIGHER)  # play continues normally


def test_recovery_one_box_per_match():
    g = game(["7", "5", "6"], ["2", "3", "7", "9"], inclusive=1)
    fail(g, 1)
    fail(g, 2)
    g.play(0, LOWER_EQUAL)
    g.recover(1)
    with pytest.raises(RulesError):
        g.recover(2)
    assert 2 in g.failed


def test_recovery_must_be_resolved_before_the_next_play():
    g = game(["7", "5"], ["2", "7", "9"], inclusive=1)
    fail(g, 1)
    g.play(0, LOWER_EQUAL)
    with pytest.raises(RulesError):
        g.play(0, HIGHER)


def test_recovery_only_targets_a_failed_box():
    g = game(["7", "5"], ["2", "7"], inclusive=1)
    fail(g, 1)
    g.play(0, LOWER_EQUAL)
    with pytest.raises(RulesError):
        g.recover(3)


def test_recovery_no_banking_when_nothing_has_failed():
    # RULES.md Example 5.
    g = game(["7", "5"], ["7", "2", "6"], inclusive=1)
    r = g.play(0, LOWER_EQUAL)
    assert r.success and r.recovery_earned and r.recovery_lost
    assert not r.recovery_pending and not g.recovery_pending
    fail(g, 1)  # a later failure does not unlock the lost recovery
    with pytest.raises(RulesError):
        g.recover(1)


def test_recovery_cannot_be_earned_without_a_success():
    g = game(["7", "5"], ["2", "9"], inclusive=1)
    fail(g, 1)
    r = g.play(0, HIGHER_EQUAL)  # 9 is not equal, but wins; no recovery
    assert r.success and not r.recovery_earned


def test_recovery_on_the_last_card_is_still_offered():
    g = game(["7", "5"], ["2", "7"], inclusive=1)
    fail(g, 1)
    r = g.play(0, LOWER_EQUAL)
    assert r.recovery_pending and not r.game_over and g.won
    g.recover(1)
    assert g.is_over and g.won and g.boxes_left == 9


# -------------------------------------------------------- Winning/losing --- #

def test_win_when_pile_runs_out_with_a_live_box():
    g = game(["5"], ["9"])
    r = g.play(0, HIGHER)
    assert r.game_over and r.won and g.won and not g.lost


def test_win_with_a_single_box_left():
    box = ["2"] * 9
    g = game(box, ["2"] * 8 + ["3"])
    for pos in range(8):
        fail(g, pos)
    assert g.play(8, HIGHER).won


def test_lose_when_all_nine_boxes_fail():
    g = game(["A"] * 9, ["2"] * 9 + ["3"])
    for pos in range(9):
        r = g.play(pos, HIGHER)
    assert r.game_over and not r.won and g.lost and g.cards_left == 1


def test_no_play_after_game_over():
    g = game(["5"], ["9"])
    g.play(0, HIGHER)
    with pytest.raises(RulesError):
        g.play(1, HIGHER)


# --------------------------------------------------------------- Settings --- #

@pytest.mark.parametrize("jokers", [0, 1, 2])
def test_settings_inclusive_limit_is_43_plus_jokers(jokers):
    limit = max_inclusive_calls(jokers)
    assert limit == 43 + jokers
    Game.new(jokers, limit, seed=1)
    with pytest.raises(RulesError):
        Game.new(jokers, limit + 1, seed=1)


@pytest.mark.parametrize("jokers", [-1, 3])
def test_settings_jokers_are_0_to_2(jokers):
    with pytest.raises(RulesError):
        Game.new(jokers, 0, seed=1)


def test_settings_inclusive_calls_cannot_be_negative():
    with pytest.raises(RulesError):
        Game.new(0, -1, seed=1)


# ----------------------------------------------------------- Card counting -- #

RULES_COUNT_TABLE = {  # copied from RULES.md: 2 3 4 5 6 7 8 9 10 J Q K A
    0: [-1, -1, -1, -1, -1, -1, 0, 1, 1, 1, 1, 1, 1],
    1: [-2, -2, -2, -1, -1, -1, 0, 1, 1, 1, 2, 2, 2],
    2: [-3, -3, -2, -2, -1, -1, 0, 1, 1, 2, 2, 3, 3],
}


@pytest.mark.parametrize("method", [0, 1, 2])
def test_counting_tables_match_rules(method):
    assert [COUNT_TABLES[method][r] for r in range(2, 15)] == RULES_COUNT_TABLE[method]


def test_counting_jokers_count_zero():
    assert count_values(Card.joker()) == [0, 0, 0]


def test_counting_the_opening_deal_is_counted():
    g = game(["A", "K", "2", "8", "8", "8", "8", "8", "8"], [])
    assert g.counts == [1 + 1 - 1, 2 + 2 - 2, 3 + 3 - 3]


def test_counting_drawn_cards_are_counted_win_or_lose():
    g = game(["8"] * 9, ["A", "2"])
    g.play(0, HIGHER)  # win, A drawn
    g.play(1, HIGHER)  # lose, 2 drawn
    assert g.counts == [0, 0, 0]  # +1 -1 / +2 -2 / +3 -3


def test_counting_full_deck_sums_to_zero():
    g = Game.new(2, 0, seed=3)
    total = [sum(count_values(c)[m] for c in g.box + g.draw_pile) for m in range(3)]
    assert total == [0, 0, 0]


def test_counting_recovered_card_is_not_counted_again():
    g = game(["7", "K", "8", "8", "8", "8", "8", "8", "8"], ["5", "7"], inclusive=1)
    g.play(1, HIGHER)  # K fails on a 5
    before = list(g.counts)
    g.play(0, LOWER_EQUAL)  # 7 on 7: counted once, as drawn
    after_flip = list(g.counts)
    g.recover(1)  # the K comes back: not counted again
    assert g.counts == after_flip == [b + v for b, v in zip(before, count_values(card("7")))]


# --------------------------------------------------- Undo (tool feature) ---- #

def test_undo_restores_the_full_state():
    g = Game.new(1, 5, seed=11)
    before = (list(g.box), dict(g.failed), list(g.draw_pile), g.inclusive_left,
              list(g.counts), dict(g.stats))
    g.play(0, HIGHER_EQUAL)
    assert g.undo()
    after = (list(g.box), dict(g.failed), list(g.draw_pile), g.inclusive_left,
             list(g.counts), dict(g.stats))
    assert after == before


def test_undo_reverts_a_play_and_its_recovery_together():
    g = game(["7", "5"], ["2", "7", "9"], inclusive=1)
    fail(g, 1)
    g.play(0, LOWER_EQUAL)
    g.recover(1)
    g.undo()
    assert g.box[0] == card("7") and 1 in g.failed and g.inclusive_left == 1
    assert not g.recovery_pending and g.draw_pile[0].rank == 7


def test_undo_with_nothing_to_undo():
    assert game(["5"], ["9"]).undo() is False


# ------------------------------------------------------- Odds (tool feature) #

def test_odds_cover_every_call():
    g = game(["8"], ["2", "8", "9", "A"])
    o = g.odds(0)
    assert (o.higher, o.lower, o.higher_equal, o.lower_equal, o.exact) == (
        0.5, 0.25, 0.75, 0.5, 0.25)
    assert set(CALLS) <= set(vars(o))


def test_odds_for_a_failed_box_is_none():
    g = game(["5"], ["3", "9"])
    fail(g, 0)
    assert g.odds(0) is None