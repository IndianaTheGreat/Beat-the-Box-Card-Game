"""
==============================================
TEST HELPERS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/helpers.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 135 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Builders for hand-made game states.

DESCRIPTION:
-----------
Cards are written as text ("8♠", "A♥", "🃏"). Suits rarely matter, so a
short form like "8" picks a suit for you.

KEY FUNCTIONS:
-------------
- card(text), cards(*texts) -> Card objects
- game(box, pile, inclusive) -> Game; box padded with 2s to nine cards
- fail(game, position) -> forces a box to fail on the next flip
"""

from btb.engine import BOX_SIZE, Card, Game

_FILLER_SUITS = "♠♥♦♣"


def card(text: str, suit_hint: int = 0) -> Card:
    if text in ("🃏", "joker", "JK"):
        return Card.joker()
    if text[-1] in "♠♥♦♣":
        return Card.parse(text)
    return Card.parse(text + _FILLER_SUITS[suit_hint % 4])


def cards(*texts: str) -> list:
    return [card(t, i) for i, t in enumerate(texts)]


def game(box, pile, inclusive: int = 0) -> Game:
    """box: up to 9 card texts (padded with 2s, which are easy to keep alive
    by calling Higher). pile: card texts, top first."""
    box = list(box) + ["2"] * (BOX_SIZE - len(box))
    return Game.from_cards(cards(*box), cards(*pile), inclusive)


def fail(g: Game, position: int) -> None:
    """Force box `position` to fail on its next flip by calling the wrong way.
    Uses the top card of the pile."""
    target = g.box[position]
    top = g.draw_pile[0]
    call = "lower" if top.rank >= target.rank else "higher"
    result = g.play(position, call)
    assert not result.success