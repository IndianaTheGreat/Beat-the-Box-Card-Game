"""
==============================================
BEAT THE BOX RULES ENGINE
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/engine.py
Status: ACTIVE
Version: 1.4
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 308 passed)

VERSION 1.4 CHANGES (2026-10-20):
- Rule change (docs/RULES.md, "How a box fails"): a failed box keeps the
  card that beat it. The drawn card goes on top of the box card and the
  stack is turned over; a recovery turns it back, so that card comes back
  (Lower on a Q that draws an A recovers as the A, not the Q).
- Jokers have a kind, "big" or "little" (Card.kind, JOKER_KINDS,
  JOKER_NAMES), only so the windows can tell them apart. It is left out of
  equality and hashing, so play, odds, counts and statistics are unchanged.
  standard_deck() makes a big joker, then a little one; new take_card()
  removes the same kind first (dealing or flipping one joker leaves the
  other); Card.name and Card.key() give "Big Joker" and "🃏:big".

VERSION 1.3 CHANGES (2026-10-20):
- OFFER_ORDER (the order the windows show the call buttons, and the
  order offered_calls lists them in) is now Higher or Equal, Higher,
  Lower, Lower or Equal: the two plain calls sit in the middle, each
  inclusive call on the outside of its pair. Presentation only: no rule
  changes, and docs/RULES.md is untouched.

VERSION 1.2 CHANGES (2026-10-20):
- New offered_calls(card, inclusive_left): the calls the game windows
  offer on a box card. Plain Lower on a 2 and plain Higher on an A are left
  out (they never do better than the opposite call); on a joker only the
  inclusive calls are offered while any are left. This is a screen guard
  rail, not a rule: play() still accepts every call RULES.md allows, and
  the simulator strategy is unchanged.
- New call_blocked_reason(card, call, inclusive_left): why a call is not
  offered, as a short code (NO_INCLUSIVE_LEFT, JOKER_USE_INCLUSIVE,
  NOTHING_LOWER, NOTHING_HIGHER). offered_calls is built from it, so the
  greyed-out buttons and the message explaining them can't disagree.

VERSION 1.1 CHANGES (2026-10-20):
- New odds_by_rank(hist, total): the odds for every box rank against one
  pile in a single pass, as plain tuples. The simulator strategy uses it
  instead of rebuilding sums for each box, which is much faster.
- The odds formula now lives only in odds_by_rank; odds_from_histogram
  reads its entry from that table, so the joker and denominator rules are
  still written exactly once.
- Game.boxes_left counts with list.count instead of building a list (it
  runs several times a turn in the simulator).
- New count_lean(count): which call a running count favours (RULES.md,
  "Card Counting"), so the windows don't interpret counts themselves.
- No rule changes.

VERSION 1.0 CHANGES (2026-10-20):
- New. Replaces the game logic that was duplicated across
  BTBGamePlayer.py, BTBGameAid.py and BTBSimulator.py.
- Joker in the box: an inclusive call on it succeeds and earns a recovery.
- Recovery is chosen after the flip, one failed box, may be skipped, and
  is lost when no box has failed (no banking).
- A recovered box returns with the card it failed on; not counted again.
- Odds use the draw pile size as the denominator; jokers counted once.
- Undo is a full state snapshot and refunds inclusive calls.

DESCRIPTION:
-----------
Pure Python implementation of docs/RULES.md, the single source of truth. No
Tkinter imports. Every tool (Player, Assistant, Simulator, Optimizer)
plays through this module, and the Phase 2 TypeScript engine must match
it behaviour for behaviour.

DEPENDENCIES:
------------
- Standard library: random, dataclasses, typing

KEY FUNCTIONS:
-------------
- Card(rank, suit), Card.joker(kind), Card.parse(text) -> card value objects;
  Card.name ("Big Joker"), Card.key() ("🃏:big")
- take_card(cards, card) -> remove one copy (the same joker kind first)
- standard_deck(jokers), shuffled_deck(jokers, seed) -> list of cards
- Rng(seed) -> Mulberry32 PRNG used by the shuffle
- call_wins(call, drawn, target), is_exact_match(drawn, target)
- odds_against(target, pile) -> Odds (higher, lower, higher_equal,
  lower_equal, exact) as fractions 0.0 to 1.0
- odds_by_rank(hist, total) -> fast odds tuples for every rank (simulator)
- count_values(card) -> the card's value under each counting method
- count_lean(count) -> LOWER, HIGHER or None: the call a count favours
- offered_calls(card, inclusive_left) -> calls the windows offer (guard rail)
- call_blocked_reason(card, call, inclusive_left) -> why a call isn't offered
- Game.new(jokers, inclusive_calls, seed) -> shuffled deal
- Game.from_cards(box, pile, inclusive_calls) -> hand-built state (tests)
- Game.from_box(box, jokers, inclusive_calls) -> known box, unknown pile
  order (Game Assistant)
- Game.play(position, call, drawn=None) -> PlayResult
- Game.recover(position), Game.skip_recovery(), Game.undo()
- Game.odds(position), Game.odds_all(), Game.remaining_by_rank()
- Game.won, Game.lost, Game.is_over

ERROR HANDLING:
--------------
Illegal moves (failed box, no inclusive calls left, play while a recovery
is pending, card not in the pile, bad settings) raise RulesError, a
ValueError subclass. The game state is unchanged when one is raised.

NOTES:
-----
- Calls are plain strings: "higher", "lower", "higher_equal", "lower_equal".
- A joker is Card(0, ""). Two jokers are equal values. Card.kind ("big"
  or "little") tells them apart on screen only; it never changes play.
- The shuffle is Mulberry32 + Fisher-Yates, so a seed deals the same game
  in Python and TypeScript. Golden deals are pinned in tests/test_rules.py.
- A recovery earned on the last card can still be used (raises boxes left).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

SUITS = ("♠", "♥", "♦", "♣")
RANKS = tuple(range(2, 15))  # 2..10, J=11, Q=12, K=13, A=14 (aces high)
JOKER_RANK = 0
JOKER_SYMBOL = "🃏"
# The two jokers look different on screen (a big and a little joker), but
# play exactly alike: kind never takes part in equality, odds or statistics.
JOKER_KINDS = ("big", "little")
JOKER_NAMES = {"big": "Big Joker", "little": "Little Joker", "": "Joker"}
BOX_SIZE = 9
MAX_JOKERS = 2
STANDARD_DRAW_PILE = 52 - BOX_SIZE  # 43

HIGHER = "higher"
LOWER = "lower"
HIGHER_EQUAL = "higher_equal"
LOWER_EQUAL = "lower_equal"
PLAIN_CALLS = (HIGHER, LOWER)
INCLUSIVE_CALLS = (HIGHER_EQUAL, LOWER_EQUAL)
CALLS = PLAIN_CALLS + INCLUSIVE_CALLS

CALL_LABELS = {
    HIGHER: "Higher",
    LOWER: "Lower",
    HIGHER_EQUAL: "Higher or Equal",
    LOWER_EQUAL: "Lower or Equal",
}

_RANK_LABELS = {11: "J", 12: "Q", 13: "K", 14: "A"}
_LABEL_RANKS = {"J": 11, "Q": 12, "K": 13, "A": 14, "1": 14}
_SUIT_ALIASES = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}


class RulesError(ValueError):
    """Raised when a move breaks the rules (failed box, no calls left, ...)."""


# --------------------------------------------------------------------------- #
# Cards and decks
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Card:
    """A playing card. Two cards with the same rank and suit are equal.

    Jokers are ``Card(0, "")``. Two jokers in one deck are equal values. Their
    ``kind`` ("big" or "little") is only for showing them apart on screen: it
    is left out of equality and hashing, so it can never change a result.
    """

    rank: int
    suit: str = ""
    kind: str = field(default="", compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.rank == JOKER_RANK:
            if self.suit:
                raise ValueError("a joker has no suit")
            if self.kind not in JOKER_NAMES:
                raise ValueError(f"unknown joker kind {self.kind!r}")
        elif self.kind:
            raise ValueError("only a joker has a kind")
        elif self.rank not in RANKS or self.suit not in SUITS:
            raise ValueError(f"invalid card: rank={self.rank!r} suit={self.suit!r}")

    @classmethod
    def joker(cls, kind: str = "") -> "Card":
        return cls(JOKER_RANK, "", kind)

    @property
    def name(self) -> str:
        """"Big Joker", "Little Joker", "Joker" or the label ("A♥")."""
        return JOKER_NAMES[self.kind] if self.is_joker else self.label()

    def key(self) -> str:
        """Text that tells every physical card apart, jokers included:
        "A♥", "🃏:big", "🃏:little". Card.parse reads it back."""
        return f"{JOKER_SYMBOL}:{self.kind}" if self.is_joker and self.kind else self.label()

    @property
    def is_joker(self) -> bool:
        return self.rank == JOKER_RANK

    @property
    def rank_label(self) -> str:
        if self.is_joker:
            return "Joker"
        return _RANK_LABELS.get(self.rank, str(self.rank))

    def label(self) -> str:
        if self.is_joker:
            return JOKER_SYMBOL
        return f"{self.rank_label}{self.suit}"

    def __str__(self) -> str:
        return self.label()

    @classmethod
    def parse(cls, text: str) -> "Card":
        """Parse "A♠", "10♣", "q♥", "7S", "🃏", "joker", or a joker with its
        kind: "🃏:big", "big joker", "🃏:little", "little joker"."""
        text = text.strip()
        if text == JOKER_SYMBOL or text.lower() in ("joker", "jk"):
            return cls.joker()
        for kind in JOKER_KINDS:
            if text in (f"{JOKER_SYMBOL}:{kind}",) or text.lower() == f"{kind} joker":
                return cls.joker(kind)
        if len(text) < 2:
            raise ValueError(f"cannot parse card {text!r}")
        rank_text, suit = text[:-1].upper(), text[-1]
        suit = _SUIT_ALIASES.get(suit.upper(), suit)
        if rank_text in _LABEL_RANKS:
            rank = _LABEL_RANKS[rank_text]
        else:
            try:
                rank = int(rank_text)
            except ValueError:
                raise ValueError(f"cannot parse card {text!r}") from None
        return cls(rank, suit)


def standard_deck(jokers: int = 0) -> List[Card]:
    """A fresh, unshuffled deck: 52 cards by suit then rank, then the jokers."""
    if not 0 <= jokers <= MAX_JOKERS:
        raise RulesError(f"jokers must be 0-{MAX_JOKERS}")
    deck = [Card(rank, suit) for suit in SUITS for rank in RANKS]
    deck.extend(Card.joker(kind) for kind in JOKER_KINDS[:jokers])
    return deck


def take_card(cards: List[Card], card: Card) -> Card:
    """Remove one copy of `card` from `cards` and return it. A joker of the
    same kind is taken first (so picking the little joker leaves the big
    one), then any equal card."""
    for i, other in enumerate(cards):
        if other == card and other.kind == card.kind:
            return cards.pop(i)
    return cards.pop(cards.index(card))   # ValueError if it isn't there


class Rng:
    """Mulberry32: a tiny 32-bit PRNG that is easy to reproduce in TypeScript."""

    def __init__(self, seed: int) -> None:
        self._state = seed & 0xFFFFFFFF

    def next_uint32(self) -> int:
        self._state = (self._state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self._state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return (t ^ (t >> 14)) & 0xFFFFFFFF

    def next_float(self) -> float:
        """Uniform float in [0, 1)."""
        return self.next_uint32() / 4294967296

    def below(self, n: int) -> int:
        """Uniform integer in [0, n)."""
        return int(self.next_float() * n)


def new_seed() -> int:
    return random.SystemRandom().randrange(2**32)


def shuffle(cards: Sequence[Card], seed: int) -> List[Card]:
    """Fisher-Yates shuffle driven by Mulberry32. Same seed, same order."""
    out = list(cards)
    rng = Rng(seed)
    for i in range(len(out) - 1, 0, -1):
        j = rng.below(i + 1)
        out[i], out[j] = out[j], out[i]
    return out


def shuffled_deck(jokers: int = 0, seed: Optional[int] = None) -> List[Card]:
    return shuffle(standard_deck(jokers), new_seed() if seed is None else seed)


def max_inclusive_calls(jokers: int) -> int:
    """RULES.md: 0 up to 43 + jokers (the size of the draw pile)."""
    return STANDARD_DRAW_PILE + jokers


# --------------------------------------------------------------------------- #
# Card counting (RULES.md, "Card Counting")
# --------------------------------------------------------------------------- #

COUNT_METHOD_NAMES = ("Basic", "Weighted", "Advanced")

COUNT_TABLES: tuple = (
    # Method 1, Basic
    {2: -1, 3: -1, 4: -1, 5: -1, 6: -1, 7: -1, 8: 0,
     9: 1, 10: 1, 11: 1, 12: 1, 13: 1, 14: 1},
    # Method 2, Weighted
    {2: -2, 3: -2, 4: -2, 5: -1, 6: -1, 7: -1, 8: 0,
     9: 1, 10: 1, 11: 1, 12: 2, 13: 2, 14: 2},
    # Method 3, Advanced
    {2: -3, 3: -3, 4: -2, 5: -2, 6: -1, 7: -1, 8: 0,
     9: 1, 10: 1, 11: 2, 12: 2, 13: 3, 14: 3},
)


def count_values(card: Card) -> List[int]:
    """The card's value under each counting method. Jokers count 0."""
    if card.is_joker:
        return [0] * len(COUNT_TABLES)
    return [table[card.rank] for table in COUNT_TABLES]


def count_lean(count: int) -> Optional[str]:
    """The call a running count favours (RULES.md, "Card Counting").

    Positive: high cards have been seen, so more low cards remain -> LOWER.
    Negative: more high cards remain -> HIGHER. Zero: no lean (None).
    """
    if count > 0:
        return LOWER
    if count < 0:
        return HIGHER
    return None


# --------------------------------------------------------------------------- #
# Comparing cards and odds
# --------------------------------------------------------------------------- #

def is_exact_match(drawn: Card, target: Card) -> bool:
    """A joker is an exact match for any card (RULES.md, "Jokers")."""
    return drawn.is_joker or target.is_joker or drawn.rank == target.rank


def call_wins(call: str, drawn: Card, target: Card) -> bool:
    """Whether `call` on `target` succeeds when `drawn` is flipped."""
    if call not in CALLS:
        raise RulesError(f"unknown call {call!r}")
    if drawn.is_joker or target.is_joker:
        return True
    if call == HIGHER:
        return drawn.rank > target.rank
    if call == LOWER:
        return drawn.rank < target.rank
    if call == HIGHER_EQUAL:
        return drawn.rank >= target.rank
    return drawn.rank <= target.rank


LOWEST_RANK, HIGHEST_RANK = RANKS[0], RANKS[-1]


# Button order, left to right: the Higher pair, then the Lower pair, with the
# plain calls in the middle (▲= ▲ ▼ ▼=).
OFFER_ORDER = (HIGHER_EQUAL, HIGHER, LOWER, LOWER_EQUAL)

# Why a call is not offered (call_blocked_reason). The windows turn these
# codes into words; the TypeScript port uses the same codes.
NO_INCLUSIVE_LEFT = "no_inclusive_left"
JOKER_USE_INCLUSIVE = "joker_use_inclusive"
NOTHING_LOWER = "nothing_lower"
NOTHING_HIGHER = "nothing_higher"


def call_blocked_reason(card: Card, call: str, inclusive_left: int) -> Optional[str]:
    """Why the game windows don't offer `call` on this box card, or None if
    they do. A screen guard rail, not a rule: play() accepts every call
    RULES.md allows. Left out:
      * inclusive calls when none are left (NO_INCLUSIVE_LEFT);
      * plain calls on a joker while inclusive calls are left: an inclusive
        call is just as certain and can also recover a failed box. With no
        inclusive calls left, the plain calls come back so the joker can be
        played (JOKER_USE_INCLUSIVE);
      * plain Lower on a 2 (NOTHING_LOWER) and plain Higher on an A
        (NOTHING_HIGHER): they can only win on a joker, and the opposite
        call wins on that joker too, so they never do better.
    """
    if call not in CALLS:
        raise RulesError(f"unknown call {call!r}")
    if call in INCLUSIVE_CALLS and inclusive_left <= 0:
        return NO_INCLUSIVE_LEFT
    if card.is_joker:
        return JOKER_USE_INCLUSIVE if call in PLAIN_CALLS and inclusive_left > 0 else None
    if call == LOWER and card.rank == LOWEST_RANK:
        return NOTHING_LOWER
    if call == HIGHER and card.rank == HIGHEST_RANK:
        return NOTHING_HIGHER
    return None


def offered_calls(card: Card, inclusive_left: int) -> tuple:
    """The calls the game windows offer on a box card, in button order
    (the ones call_blocked_reason doesn't rule out)."""
    return tuple(call for call in OFFER_ORDER
                 if call_blocked_reason(card, call, inclusive_left) is None)


@dataclass(frozen=True)
class Odds:
    """Chance (0.0-1.0) that each call succeeds against one box card.

    ``exact`` is the chance the flip is an exact match (or a joker), which is
    the chance an inclusive call earns a recovery.
    """

    higher: float
    lower: float
    higher_equal: float
    lower_equal: float
    exact: float

    def for_call(self, call: str) -> float:
        return getattr(self, call)

    def best_plain(self) -> tuple:
        """(call, probability) of the better plain call. Ties go to Higher."""
        if self.lower > self.higher:
            return LOWER, self.lower
        return HIGHER, self.higher

    def best_inclusive(self) -> tuple:
        if self.lower_equal > self.higher_equal:
            return LOWER_EQUAL, self.lower_equal
        return HIGHER_EQUAL, self.higher_equal


CERTAIN = Odds(1.0, 1.0, 1.0, 1.0, 1.0)


def rank_histogram(pile: Sequence[Card]) -> List[int]:
    """Index 0 holds jokers, 2..14 hold each rank."""
    hist = [0] * 15
    for card in pile:
        hist[card.rank] += 1
    return hist


CERTAIN_VALUES = (1.0, 1.0, 1.0, 1.0, 1.0)


def odds_by_rank(hist: Sequence[int], total: int) -> List[Optional[tuple]]:
    """Odds for every possible box card against one pile, in a single pass.

    This is the one place the odds formula lives (RULES.md): a joker in the
    pile wins every call and is an exact match, and the denominator is the
    size of the draw pile.

    Index = the box card's rank (0 = a joker in the box, which is certain).
    Each entry is a plain tuple (higher, lower, higher_equal, lower_equal,
    exact), the same order as the Odds fields. Index 1 is unused (None).
    Returns all None for an empty pile. Plain tuples keep the simulator
    fast; odds_from_histogram wraps one entry in an Odds object.
    """
    table: List[Optional[tuple]] = [None] * 15
    if total <= 0:
        return table
    table[JOKER_RANK] = CERTAIN_VALUES
    jokers = hist[JOKER_RANK]
    cards = sum(hist[2:15])
    below = 0
    for rank in RANKS:
        equal = hist[rank]
        lower = below + jokers
        higher = cards - below - equal + jokers
        table[rank] = (higher / total, lower / total, (higher + equal) / total,
                       (lower + equal) / total, (equal + jokers) / total)
        below += equal
    return table


def odds_from_histogram(target: Card, hist: Sequence[int], total: int) -> Optional[Odds]:
    if total <= 0:
        return None
    if target.is_joker:
        return CERTAIN
    return Odds(*odds_by_rank(hist, total)[target.rank])


def odds_against(target: Card, pile: Sequence[Card]) -> Optional[Odds]:
    """Odds for a box card against a pile whose order is unknown."""
    return odds_from_histogram(target, rank_histogram(pile), len(pile))


# --------------------------------------------------------------------------- #
# Game state
# --------------------------------------------------------------------------- #

@dataclass
class PlayResult:
    position: int
    call: str
    target: Card
    drawn: Card
    success: bool
    exact_match: bool
    recovery_earned: bool    # inclusive call + exact match (or joker)
    recovery_pending: bool   # earned and there is a failed box to bring back
    recovery_lost: bool      # earned but nothing to recover (no banking)
    game_over: bool
    won: bool


@dataclass
class _Snapshot:
    box: List[Optional[Card]]
    failed: Dict[int, Card]
    draw_pile: List[Card]
    inclusive_left: int
    recovery_pending: bool
    counts: List[int]
    stats: Dict[str, int]


@dataclass
class Game:
    """One game of Beat the Box.

    ``box[i]`` is the live card in box i, or None if that box has failed.
    ``failed[i]`` is the card that beat box i: the drawn card, on top of
    the face-down stack. It is the card that comes back on recovery.
    ``draw_pile[0]`` is the top of the pile.
    """

    box: List[Optional[Card]]
    draw_pile: List[Card]
    inclusive_left: int = 0
    failed: Dict[int, Card] = field(default_factory=dict)
    recovery_pending: bool = False
    counts: List[int] = field(default_factory=lambda: [0, 0, 0])
    stats: Dict[str, int] = field(default_factory=lambda: {
        "plays": 0, "inclusive_used": 0, "jokers_drawn": 0,
        "recoveries": 0, "recoveries_lost": 0,
    })
    _history: List[_Snapshot] = field(default_factory=list, repr=False)

    # ----- construction --------------------------------------------------- #

    @classmethod
    def from_cards(cls, box: Sequence[Card], draw_pile: Sequence[Card],
                   inclusive_calls: int = 0) -> "Game":
        """Build a game from an explicit deal (tests, the Game Assistant)."""
        if len(box) != BOX_SIZE or any(c is None for c in box):
            raise RulesError(f"the box needs exactly {BOX_SIZE} cards")
        if inclusive_calls < 0:
            raise RulesError("inclusive calls cannot be negative")
        game = cls(box=list(box), draw_pile=list(draw_pile),
                   inclusive_left=inclusive_calls)
        for card in box:  # every card is counted once, when first visible
            game._count(card)
        return game

    @classmethod
    def new(cls, jokers: int = 0, inclusive_calls: int = 5,
            seed: Optional[int] = None) -> "Game":
        """Shuffle a deck and deal a new game (RULES.md, "Setup")."""
        validate_settings(jokers, inclusive_calls)
        deck = shuffled_deck(jokers, seed)
        return cls.from_cards(deck[:BOX_SIZE], deck[BOX_SIZE:], inclusive_calls)

    @classmethod
    def from_box(cls, box: Sequence[Card], jokers: int = 0,
                 inclusive_calls: int = 5) -> "Game":
        """A game whose box is known but whose draw pile order is not.

        The draw pile is the rest of the deck. Callers pass ``drawn=`` to
        ``play`` to say which card actually came off the pile.
        """
        validate_settings(jokers, inclusive_calls)
        pile = standard_deck(jokers)
        for card in box:
            try:
                take_card(pile, card)  # one copy only (the same joker kind first)
            except ValueError:
                raise RulesError(f"{card} is not available in this deck") from None
        return cls.from_cards(box, pile, inclusive_calls)

    # ----- read-only views ------------------------------------------------ #

    @property
    def live_positions(self) -> List[int]:
        return [i for i, card in enumerate(self.box) if card is not None]

    @property
    def failed_positions(self) -> List[int]:
        return sorted(self.failed)

    @property
    def boxes_left(self) -> int:
        return len(self.box) - self.box.count(None)

    @property
    def cards_left(self) -> int:
        return len(self.draw_pile)

    @property
    def lost(self) -> bool:
        """RULES.md: you lose when all nine boxes fail."""
        return self.boxes_left == 0

    @property
    def won(self) -> bool:
        """RULES.md: the pile runs out and at least one box is alive."""
        return not self.draw_pile and self.boxes_left > 0

    @property
    def is_over(self) -> bool:
        return self.lost or (self.won and not self.recovery_pending)

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    def odds(self, position: int) -> Optional[Odds]:
        card = self.box[position]
        if card is None:
            return None
        return odds_against(card, self.draw_pile)

    def odds_all(self) -> List[Optional[Odds]]:
        table = odds_by_rank(rank_histogram(self.draw_pile), len(self.draw_pile))
        out: List[Optional[Odds]] = []
        for card in self.box:
            entry = None if card is None else table[card.rank]
            out.append(None if entry is None else Odds(*entry))
        return out

    def remaining_by_rank(self) -> Dict[int, int]:
        """Cards left in the pile by rank (0 = jokers), only ranks present."""
        hist = rank_histogram(self.draw_pile)
        return {rank: n for rank, n in enumerate(hist) if n}

    # ----- moves ---------------------------------------------------------- #

    def play(self, position: int, call: str,
             drawn: Optional[Card] = None) -> PlayResult:
        """Call on a live box and flip (RULES.md, "Taking a Turn").

        ``drawn`` names the card that came off the pile when its order is
        unknown (the Game Assistant). Otherwise the top card is flipped.
        """
        if self.is_over:
            raise RulesError("the game is over")
        if self.recovery_pending:
            raise RulesError("choose a failed box to recover, or skip, first")
        if not 0 <= position < BOX_SIZE:
            raise RulesError(f"no box at position {position}")
        target = self.box[position]
        if target is None:
            raise RulesError("that box has failed")
        if call not in CALLS:
            raise RulesError(f"unknown call {call!r}")
        inclusive = call in INCLUSIVE_CALLS
        if inclusive and self.inclusive_left <= 0:
            raise RulesError("no inclusive calls left")
        if drawn is not None and drawn not in self.draw_pile:
            raise RulesError(f"{drawn} is not in the draw pile")

        self._history.append(self._snapshot())

        if inclusive:  # spent when the call is made, win or lose
            self.inclusive_left -= 1
            self.stats["inclusive_used"] += 1
        if drawn is None:
            drawn = self.draw_pile.pop(0)
        else:
            drawn = take_card(self.draw_pile, drawn)  # one copy, same joker kind first
        self.stats["plays"] += 1
        if drawn.is_joker:
            self.stats["jokers_drawn"] += 1
        self._count(drawn)

        success = call_wins(call, drawn, target)
        exact = is_exact_match(drawn, target)
        if success:
            self.box[position] = drawn
        else:
            # The drawn card goes on top of the box card and the box turns
            # face down; a recovery turns the stack back over, so the card
            # that beat the box is the one that comes back (docs/RULES.md).
            self.box[position] = None
            self.failed[position] = drawn

        earned = success and inclusive and exact
        pending = earned and bool(self.failed)
        lost = earned and not pending
        self.recovery_pending = pending
        if lost:
            self.stats["recoveries_lost"] += 1

        return PlayResult(
            position=position, call=call, target=target, drawn=drawn,
            success=success, exact_match=exact, recovery_earned=earned,
            recovery_pending=pending, recovery_lost=lost,
            game_over=self.is_over, won=self.won,
        )

    def recover(self, position: int) -> Card:
        """Spend a pending recovery on one failed box (RULES.md, "Recovering").

        The box comes back with the card on top of its stack: the drawn
        card that beat it. That card was already counted when it was
        flipped, so the counts do not change.
        """
        if not self.recovery_pending:
            raise RulesError("no recovery has been earned")
        if position not in self.failed:
            raise RulesError("that box has not failed")
        card = self.failed.pop(position)
        self.box[position] = card
        self.recovery_pending = False
        self.stats["recoveries"] += 1
        return card

    def skip_recovery(self) -> None:
        if not self.recovery_pending:
            raise RulesError("no recovery has been earned")
        self.recovery_pending = False
        self.stats["recoveries_lost"] += 1

    def undo(self) -> bool:
        """Undo the last play, including any recovery made with it."""
        if not self._history:
            return False
        snap = self._history.pop()
        self.box = snap.box
        self.failed = snap.failed
        self.draw_pile = snap.draw_pile
        self.inclusive_left = snap.inclusive_left
        self.recovery_pending = snap.recovery_pending
        self.counts = snap.counts
        self.stats = snap.stats
        return True

    # ----- internals ------------------------------------------------------ #

    def _count(self, card: Card) -> None:
        for i, value in enumerate(count_values(card)):
            self.counts[i] += value

    def _snapshot(self) -> _Snapshot:
        return _Snapshot(
            box=list(self.box), failed=dict(self.failed),
            draw_pile=list(self.draw_pile), inclusive_left=self.inclusive_left,
            recovery_pending=self.recovery_pending, counts=list(self.counts),
            stats=dict(self.stats),
        )


def validate_settings(jokers: int, inclusive_calls: int) -> None:
    if not 0 <= jokers <= MAX_JOKERS:
        raise RulesError(f"jokers must be 0-{MAX_JOKERS}")
    limit = max_inclusive_calls(jokers)
    if not 0 <= inclusive_calls <= limit:
        raise RulesError(f"inclusive calls must be 0-{limit} with {jokers} joker(s)")