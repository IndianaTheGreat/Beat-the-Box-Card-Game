/*
==============================================
BEAT THE BOX RULES ENGINE (TYPESCRIPT)
==============================================
File Location: Beat-the-Box-Card-Game/extension/src/engine.ts
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (node --test: 80 passed)

VERSION 1.0 CHANGES (2026-10-20):
- New. The Chrome extension's rules engine: a port of
  python/btb/engine.py 1.4 that gives the same answer for every case in
  shared/test_vectors.json (same shuffles, odds, calls, recoveries, undo
  and errors).

DESCRIPTION:
-----------
docs/RULES.md in code, with no page or Chrome code. Every page of the
extension plays through this file, the same way every Python tool plays
through btb/engine.py.

DEPENDENCIES:
------------
- None. Plain TypeScript that runs in Chrome and in Node 22.18 or newer.

KEY FUNCTIONS:
-------------
- Card.of(rank, suit), Card.joker(kind), Card.parse(text) -> shared card
  objects; card.name ("Big Joker"), card.key() ("🃏:big"), card.equals()
- takeCard(cards, card) -> remove one copy (the same joker kind first)
- standardDeck(jokers), shuffledDeck(jokers, seed), shuffle(cards, seed)
- Rng(seed) -> Mulberry32, the same numbers as the Python Rng
- callWins(call, drawn, target), isExactMatch(drawn, target)
- oddsAgainst(target, pile), oddsByRank(hist, total), rankHistogram(pile)
- countValues(card), countLean(count)
- offeredCalls(card, inclusiveLeft), callBlockedReason(card, call, left)
- Game.deal(jokers, inclusiveCalls, seed), Game.fromCards(box, pile, calls),
  Game.fromBox(box, jokers, calls)
- game.play(position, call, drawn?), game.recover(position),
  game.skipRecovery(), game.undo()
- game.odds(position), game.oddsAll(), game.remainingByRank()

ERROR HANDLING:
--------------
Illegal moves throw RulesError and leave the game unchanged, as in Python.
A card that can't exist (rank 15, a suited joker) or text that can't be
read as a card throws a RangeError (Python's ValueError).

NOTES:
-----
- Names follow TypeScript style: Python's draw_pile is drawPile,
  inclusive_left is inclusiveLeft, Game.new is Game.deal. Call names stay
  "higher", "lower", "higher_equal", "lower_equal" because they are data
  (saved settings, exports, the test vectors).
- Cards are shared objects: Card.of(14, "♠") always returns the same one,
  so === works for an exact match. card.equals() ignores the joker kind,
  as Python's == does, so the two jokers play exactly alike.
- Only "erasable" TypeScript is used (no enum, no namespace, no parameter
  properties), so Node runs this file as it is and the build only has to
  strip the types.
*/

// --------------------------------------------------------------------------- //
// Constants
// --------------------------------------------------------------------------- //

export const SUITS = ["♠", "♥", "♦", "♣"] as const;
export type Suit = (typeof SUITS)[number];

/** 2..10, J=11, Q=12, K=13, A=14 (aces high). */
export const RANKS: readonly number[] = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14];
export const JOKER_RANK = 0;
export const JOKER_SYMBOL = "🃏";
/** The two jokers look different on screen but play exactly alike. */
export const JOKER_KINDS = ["big", "little"] as const;
export type JokerKind = (typeof JOKER_KINDS)[number] | "";
export const JOKER_NAMES: Readonly<Record<JokerKind, string>> = {
  big: "Big Joker", little: "Little Joker", "": "Joker",
};
export const BOX_SIZE = 9;
export const MAX_JOKERS = 2;
export const STANDARD_DRAW_PILE = 52 - BOX_SIZE; // 43

export const HIGHER = "higher";
export const LOWER = "lower";
export const HIGHER_EQUAL = "higher_equal";
export const LOWER_EQUAL = "lower_equal";
export type PlainCall = typeof HIGHER | typeof LOWER;
export type InclusiveCall = typeof HIGHER_EQUAL | typeof LOWER_EQUAL;
export type Call = PlainCall | InclusiveCall;
export const PLAIN_CALLS: readonly Call[] = [HIGHER, LOWER];
export const INCLUSIVE_CALLS: readonly Call[] = [HIGHER_EQUAL, LOWER_EQUAL];
export const CALLS: readonly Call[] = [...PLAIN_CALLS, ...INCLUSIVE_CALLS];

export const CALL_LABELS: Readonly<Record<Call, string>> = {
  higher: "Higher",
  lower: "Lower",
  higher_equal: "Higher or Equal",
  lower_equal: "Lower or Equal",
};

const RANK_LABELS: Readonly<Record<number, string>> = { 11: "J", 12: "Q", 13: "K", 14: "A" };
const LABEL_RANKS: Readonly<Record<string, number>> = { J: 11, Q: 12, K: 13, A: 14, "1": 14 };
const SUIT_ALIASES: Readonly<Record<string, Suit>> = { S: "♠", H: "♥", D: "♦", C: "♣" };

/** A move that breaks the rules (failed box, no calls left, ...). */
export class RulesError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "RulesError";
  }
}

export function isCall(value: unknown): value is Call {
  return typeof value === "string" && (CALLS as readonly string[]).includes(value);
}

function checkCall(call: string): asserts call is Call {
  if (!isCall(call)) throw new RulesError(`unknown call "${call}"`);
}

// --------------------------------------------------------------------------- //
// Cards and decks
// --------------------------------------------------------------------------- //

/** Python's int() for plain ASCII text: spaces around it, a sign, and
 * single underscores between digits are allowed. */
const PYTHON_INT = /^\s*[+-]?\d+(?:_\d+)*\s*$/;

export class Card {
  readonly rank: number;
  readonly suit: Suit | "";
  readonly kind: JokerKind;

  static #shared = new Map<string, Card>();

  private constructor(rank: number, suit: Suit | "", kind: JokerKind) {
    this.rank = rank;
    this.suit = suit;
    this.kind = kind;
    Object.freeze(this);
  }

  /** The card with this rank and suit. Jokers are Card.of(0) or Card.joker(). */
  static of(rank: number, suit: string = "", kind: string = ""): Card {
    const id = `${rank}|${suit}|${kind}`;
    const known = Card.#shared.get(id);
    if (known) return known;
    if (rank === JOKER_RANK) {
      if (suit) throw new RangeError("a joker has no suit");
      if (!Object.hasOwn(JOKER_NAMES, kind)) throw new RangeError(`unknown joker kind "${kind}"`);
    } else if (kind) {
      throw new RangeError("only a joker has a kind");
    } else if (!RANKS.includes(rank) || !(SUITS as readonly string[]).includes(suit)) {
      throw new RangeError(`invalid card: rank=${rank} suit="${suit}"`);
    }
    const card = new Card(rank, suit as Suit | "", kind as JokerKind);
    Card.#shared.set(id, card);
    return card;
  }

  static joker(kind: JokerKind = ""): Card {
    return Card.of(JOKER_RANK, "", kind);
  }

  get isJoker(): boolean {
    return this.rank === JOKER_RANK;
  }

  /** "Big Joker", "Little Joker", "Joker" or the label ("A♥"). */
  get name(): string {
    return this.isJoker ? JOKER_NAMES[this.kind] : this.label();
  }

  get rankLabel(): string {
    if (this.isJoker) return "Joker";
    return RANK_LABELS[this.rank] ?? String(this.rank);
  }

  label(): string {
    return this.isJoker ? JOKER_SYMBOL : `${this.rankLabel}${this.suit}`;
  }

  /** Text that tells every physical card apart, jokers included:
   * "A♥", "🃏:big", "🃏:little". Card.parse reads it back. */
  key(): string {
    return this.isJoker && this.kind ? `${JOKER_SYMBOL}:${this.kind}` : this.label();
  }

  toString(): string {
    return this.label();
  }

  /** Same rank and suit. The joker kind is ignored, as in the rules. */
  equals(other: Card | null | undefined): boolean {
    return other != null && other.rank === this.rank && other.suit === this.suit;
  }

  /** Read "A♠", "10♣", "q♥", "7S", "🃏", "joker", "🃏:big", "big joker"... */
  static parse(input: string): Card {
    const text = input.trim();
    const lower = text.toLowerCase();
    if (text === JOKER_SYMBOL || lower === "joker" || lower === "jk") return Card.joker();
    for (const kind of JOKER_KINDS) {
      if (text === `${JOKER_SYMBOL}:${kind}` || lower === `${kind} joker`) return Card.joker(kind);
    }
    const chars = Array.from(text); // whole characters, as Python counts them
    if (chars.length < 2) throw new RangeError(`cannot parse card "${input}"`);
    const rankText = chars.slice(0, -1).join("").toUpperCase();
    const last = chars[chars.length - 1]!;
    const alias = last.toUpperCase();
    const suit = Object.hasOwn(SUIT_ALIASES, alias) ? SUIT_ALIASES[alias]! : last;
    let rank: number;
    if (Object.hasOwn(LABEL_RANKS, rankText)) {
      rank = LABEL_RANKS[rankText]!;
    } else if (PYTHON_INT.test(rankText)) {
      rank = Number(rankText.replaceAll("_", ""));
    } else {
      throw new RangeError(`cannot parse card "${input}"`);
    }
    return Card.of(rank, suit);
  }
}

/** A fresh, unshuffled deck: 52 cards by suit then rank, then the jokers
 * (big first, then little). */
export function standardDeck(jokers: number = 0): Card[] {
  if (!Number.isInteger(jokers) || jokers < 0 || jokers > MAX_JOKERS) {
    throw new RulesError(`jokers must be 0-${MAX_JOKERS}`);
  }
  const deck: Card[] = [];
  for (const suit of SUITS) for (const rank of RANKS) deck.push(Card.of(rank, suit));
  for (const kind of JOKER_KINDS.slice(0, jokers)) deck.push(Card.joker(kind));
  return deck;
}

/** Remove one copy of `card` from `cards` and return it. A joker of the same
 * kind is taken first (picking the little joker leaves the big one), then
 * any equal card. Throws RangeError when there is none. */
export function takeCard(cards: Card[], card: Card): Card {
  let index = cards.indexOf(card);
  if (index < 0) index = cards.findIndex((other) => other.equals(card));
  if (index < 0) throw new RangeError(`${card.label()} is not there`);
  return cards.splice(index, 1)[0]!;
}

/** Mulberry32: a tiny 32-bit generator, the same numbers as Python's Rng. */
export class Rng {
  #state: number;

  constructor(seed: number) {
    this.#state = seed >>> 0;
  }

  nextUint32(): number {
    this.#state = (this.#state + 0x6d2b79f5) >>> 0;
    let t = this.#state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return (t ^ (t >>> 14)) >>> 0;
  }

  /** Uniform in [0, 1). */
  nextFloat(): number {
    return this.nextUint32() / 4294967296;
  }

  /** Uniform whole number in [0, n). */
  below(n: number): number {
    return Math.floor(this.nextFloat() * n);
  }
}

/** A random 32-bit seed. */
export function newSeed(): number {
  return crypto.getRandomValues(new Uint32Array(1))[0]!;
}

/** Fisher-Yates driven by Mulberry32. Same seed, same order, in both engines. */
export function shuffle<T>(cards: readonly T[], seed: number): T[] {
  const out = [...cards];
  const rng = new Rng(seed);
  for (let i = out.length - 1; i > 0; i--) {
    const j = rng.below(i + 1);
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}

export function shuffledDeck(jokers: number = 0, seed?: number | null): Card[] {
  return shuffle(standardDeck(jokers), seed ?? newSeed());
}

/** RULES.md: 0 up to 43 + jokers (the size of the draw pile). */
export function maxInclusiveCalls(jokers: number): number {
  return STANDARD_DRAW_PILE + jokers;
}

export function validateSettings(jokers: number, inclusiveCalls: number): void {
  if (!Number.isInteger(jokers) || jokers < 0 || jokers > MAX_JOKERS) {
    throw new RulesError(`jokers must be 0-${MAX_JOKERS}`);
  }
  const limit = maxInclusiveCalls(jokers);
  if (!Number.isInteger(inclusiveCalls) || inclusiveCalls < 0 || inclusiveCalls > limit) {
    throw new RulesError(`inclusive calls must be 0-${limit} with ${jokers} joker(s)`);
  }
}

// --------------------------------------------------------------------------- //
// Card counting (RULES.md, "Card Counting")
// --------------------------------------------------------------------------- //

export const COUNT_METHOD_NAMES = ["Basic", "Weighted", "Advanced"] as const;

/** Index = rank (2..14); 0 and 1 unused. */
const COUNT_TABLES: readonly (readonly number[])[] = [
  //    2   3   4   5   6   7  8  9 10  J  Q  K  A
  [0, 0, -1, -1, -1, -1, -1, -1, 0, 1, 1, 1, 1, 1, 1], // Basic
  [0, 0, -2, -2, -2, -1, -1, -1, 0, 1, 1, 1, 2, 2, 2], // Weighted
  [0, 0, -3, -3, -2, -2, -1, -1, 0, 1, 1, 2, 2, 3, 3], // Advanced
];

/** The card's value under each counting method. Jokers count 0. */
export function countValues(card: Card): number[] {
  return COUNT_TABLES.map((table) => (card.isJoker ? 0 : table[card.rank]!));
}

/** The call a running count favours: positive means high cards have been
 * seen, so more low cards remain (Lower); negative means Higher; 0 none. */
export function countLean(count: number): PlainCall | null {
  if (count > 0) return LOWER;
  if (count < 0) return HIGHER;
  return null;
}

// --------------------------------------------------------------------------- //
// Comparing cards and odds
// --------------------------------------------------------------------------- //

/** A joker is an exact match for any card (RULES.md, "Jokers"). */
export function isExactMatch(drawn: Card, target: Card): boolean {
  return drawn.isJoker || target.isJoker || drawn.rank === target.rank;
}

/** Whether `call` on `target` succeeds when `drawn` is flipped. */
export function callWins(call: Call, drawn: Card, target: Card): boolean {
  checkCall(call);
  if (drawn.isJoker || target.isJoker) return true;
  switch (call) {
    case HIGHER: return drawn.rank > target.rank;
    case LOWER: return drawn.rank < target.rank;
    case HIGHER_EQUAL: return drawn.rank >= target.rank;
    case LOWER_EQUAL: return drawn.rank <= target.rank;
  }
}

export const LOWEST_RANK = RANKS[0]!;
export const HIGHEST_RANK = RANKS[RANKS.length - 1]!;

/** Button order, left to right: ▲= ▲ ▼ ▼= (plain calls in the middle). */
export const OFFER_ORDER: readonly Call[] = [HIGHER_EQUAL, HIGHER, LOWER, LOWER_EQUAL];

/** Why a call is not offered. The pages turn these codes into words. */
export const NO_INCLUSIVE_LEFT = "no_inclusive_left";
export const JOKER_USE_INCLUSIVE = "joker_use_inclusive";
export const NOTHING_LOWER = "nothing_lower";
export const NOTHING_HIGHER = "nothing_higher";
export type BlockedReason =
  | typeof NO_INCLUSIVE_LEFT | typeof JOKER_USE_INCLUSIVE
  | typeof NOTHING_LOWER | typeof NOTHING_HIGHER;

/** Why the game pages don't offer `call` on this box card, or null if they
 * do. A screen guard rail, not a rule: play() accepts every call RULES.md
 * allows. Left out: inclusive calls when none are left; plain calls on a
 * joker while inclusive calls are left; plain Lower on a 2 and plain Higher
 * on an A (they can only win on a joker, where the other call wins too). */
export function callBlockedReason(card: Card, call: Call, inclusiveLeft: number): BlockedReason | null {
  checkCall(call);
  const inclusive = INCLUSIVE_CALLS.includes(call);
  if (inclusive && inclusiveLeft <= 0) return NO_INCLUSIVE_LEFT;
  if (card.isJoker) return !inclusive && inclusiveLeft > 0 ? JOKER_USE_INCLUSIVE : null;
  if (call === LOWER && card.rank === LOWEST_RANK) return NOTHING_LOWER;
  if (call === HIGHER && card.rank === HIGHEST_RANK) return NOTHING_HIGHER;
  return null;
}

/** The calls the game pages offer on a box card, in button order. */
export function offeredCalls(card: Card, inclusiveLeft: number): Call[] {
  return OFFER_ORDER.filter((call) => callBlockedReason(card, call, inclusiveLeft) === null);
}

/** (higher, lower, higher_equal, lower_equal, exact), each 0.0 to 1.0. */
export type OddsTuple = readonly [number, number, number, number, number];

/** Chance (0.0-1.0) that each call succeeds against one box card. `exact`
 * is the chance of an exact match (or a joker): the chance an inclusive
 * call earns a recovery. */
export class Odds {
  readonly higher: number;
  readonly lower: number;
  readonly higherEqual: number;
  readonly lowerEqual: number;
  readonly exact: number;

  constructor(higher: number, lower: number, higherEqual: number, lowerEqual: number, exact: number) {
    this.higher = higher;
    this.lower = lower;
    this.higherEqual = higherEqual;
    this.lowerEqual = lowerEqual;
    this.exact = exact;
    Object.freeze(this);
  }

  static fromTuple(t: OddsTuple): Odds {
    return new Odds(t[0], t[1], t[2], t[3], t[4]);
  }

  forCall(call: Call): number {
    switch (call) {
      case HIGHER: return this.higher;
      case LOWER: return this.lower;
      case HIGHER_EQUAL: return this.higherEqual;
      case LOWER_EQUAL: return this.lowerEqual;
    }
  }

  /** [call, chance] of the better plain call. Ties go to Higher. */
  bestPlain(): [PlainCall, number] {
    return this.lower > this.higher ? [LOWER, this.lower] : [HIGHER, this.higher];
  }

  bestInclusive(): [InclusiveCall, number] {
    return this.lowerEqual > this.higherEqual
      ? [LOWER_EQUAL, this.lowerEqual] : [HIGHER_EQUAL, this.higherEqual];
  }
}

export const CERTAIN = new Odds(1, 1, 1, 1, 1);
const CERTAIN_VALUES: OddsTuple = [1, 1, 1, 1, 1];

/** Index 0 holds jokers, 2..14 hold each rank. */
export function rankHistogram(pile: readonly Card[]): number[] {
  const hist = new Array<number>(15).fill(0);
  for (const card of pile) hist[card.rank]!++;
  return hist;
}

/** Odds for every possible box card against one pile, in one pass. The one
 * place the odds formula lives: a joker in the pile wins every call and is
 * an exact match, and the denominator is the size of the draw pile.
 * Index = the box card's rank (0 = a joker in the box, which is certain);
 * index 1 is unused. All null for an empty pile. */
export function oddsByRank(hist: readonly number[], total: number): (OddsTuple | null)[] {
  const table: (OddsTuple | null)[] = new Array<OddsTuple | null>(15).fill(null);
  if (total <= 0) return table;
  table[JOKER_RANK] = CERTAIN_VALUES;
  const jokers = hist[JOKER_RANK]!;
  let cards = 0;
  for (let rank = 2; rank <= 14; rank++) cards += hist[rank]!;
  let below = 0;
  for (const rank of RANKS) {
    const equal = hist[rank]!;
    const lower = below + jokers;
    const higher = cards - below - equal + jokers;
    table[rank] = [higher / total, lower / total, (higher + equal) / total,
      (lower + equal) / total, (equal + jokers) / total];
    below += equal;
  }
  return table;
}

export function oddsFromHistogram(target: Card, hist: readonly number[], total: number): Odds | null {
  if (total <= 0) return null;
  if (target.isJoker) return CERTAIN;
  return Odds.fromTuple(oddsByRank(hist, total)[target.rank]!);
}

/** Odds for a box card against a pile whose order is unknown. */
export function oddsAgainst(target: Card, pile: readonly Card[]): Odds | null {
  return oddsFromHistogram(target, rankHistogram(pile), pile.length);
}

// --------------------------------------------------------------------------- //
// Game state
// --------------------------------------------------------------------------- //

export interface PlayResult {
  readonly position: number;
  readonly call: Call;
  readonly target: Card;
  readonly drawn: Card;
  readonly success: boolean;
  readonly exactMatch: boolean;
  /** Inclusive call + exact match (or a joker). */
  readonly recoveryEarned: boolean;
  /** Earned, and there is a failed box to bring back. */
  readonly recoveryPending: boolean;
  /** Earned, but nothing to recover (no banking). */
  readonly recoveryLost: boolean;
  readonly gameOver: boolean;
  readonly won: boolean;
}

export interface GameStats {
  plays: number;
  inclusiveUsed: number;
  jokersDrawn: number;
  recoveries: number;
  recoveriesLost: number;
}

interface Snapshot {
  box: (Card | null)[];
  failed: Map<number, Card>;
  drawPile: Card[];
  inclusiveLeft: number;
  recoveryPending: boolean;
  counts: number[];
  stats: GameStats;
}

/** One game of Beat the Box.
 *
 * box[i] is the live card in box i, or null if that box has failed.
 * failed.get(i) is the card that beat box i: the drawn card, on top of the
 * face-down stack. It is the card that comes back on recovery.
 * drawPile[0] is the top of the pile. */
export class Game {
  box: (Card | null)[];
  drawPile: Card[];
  inclusiveLeft: number;
  failed = new Map<number, Card>();
  recoveryPending = false;
  counts: number[] = [0, 0, 0];
  stats: GameStats = { plays: 0, inclusiveUsed: 0, jokersDrawn: 0, recoveries: 0, recoveriesLost: 0 };
  #history: Snapshot[] = [];

  /** A bare game with nothing counted yet. Use Game.deal, Game.fromCards or
   * Game.fromBox instead, which check the deal and count the box. */
  constructor(box: (Card | null)[], drawPile: Card[], inclusiveLeft: number = 0) {
    this.box = box;
    this.drawPile = drawPile;
    this.inclusiveLeft = inclusiveLeft;
  }

  // ----- construction --------------------------------------------------- //

  /** A game from an explicit deal (tests, the hand-built games). */
  static fromCards(box: readonly Card[], drawPile: readonly Card[], inclusiveCalls: number = 0): Game {
    if (box.length !== BOX_SIZE || box.some((card) => card == null)) {
      throw new RulesError(`the box needs exactly ${BOX_SIZE} cards`);
    }
    if (inclusiveCalls < 0) throw new RulesError("inclusive calls cannot be negative");
    const game = new Game([...box], [...drawPile], inclusiveCalls);
    for (const card of box) game.#count(card); // each card counted once, when first seen
    return game;
  }

  /** Shuffle a deck and deal (RULES.md, "Setup"). Python's Game.new. */
  static deal(jokers: number = 0, inclusiveCalls: number = 5, seed?: number | null): Game {
    validateSettings(jokers, inclusiveCalls);
    const deck = shuffledDeck(jokers, seed);
    return Game.fromCards(deck.slice(0, BOX_SIZE), deck.slice(BOX_SIZE), inclusiveCalls);
  }

  /** A game whose box is known but whose pile order is not (the Game
   * Assistant). The pile is the rest of the deck; pass drawn to play(). */
  static fromBox(box: readonly Card[], jokers: number = 0, inclusiveCalls: number = 5): Game {
    validateSettings(jokers, inclusiveCalls);
    const pile = standardDeck(jokers);
    for (const card of box) {
      try {
        takeCard(pile, card); // one copy only (the same joker kind first)
      } catch {
        throw new RulesError(`${card.label()} is not available in this deck`);
      }
    }
    return Game.fromCards(box, pile, inclusiveCalls);
  }

  // ----- read-only views ------------------------------------------------ //

  get livePositions(): number[] {
    const out: number[] = [];
    this.box.forEach((card, i) => { if (card !== null) out.push(i); });
    return out;
  }

  get failedPositions(): number[] {
    return [...this.failed.keys()].sort((a, b) => a - b);
  }

  get boxesLeft(): number {
    let n = 0;
    for (const card of this.box) if (card !== null) n++;
    return n;
  }

  get cardsLeft(): number {
    return this.drawPile.length;
  }

  /** RULES.md: you lose when all nine boxes fail. */
  get lost(): boolean {
    return this.boxesLeft === 0;
  }

  /** RULES.md: the pile runs out and at least one box is alive. */
  get won(): boolean {
    return this.drawPile.length === 0 && this.boxesLeft > 0;
  }

  get isOver(): boolean {
    return this.lost || (this.won && !this.recoveryPending);
  }

  get canUndo(): boolean {
    return this.#history.length > 0;
  }

  odds(position: number): Odds | null {
    const card = this.box[position];
    return card == null ? null : oddsAgainst(card, this.drawPile);
  }

  oddsAll(): (Odds | null)[] {
    const table = oddsByRank(rankHistogram(this.drawPile), this.drawPile.length);
    return this.box.map((card) => {
      const entry = card === null ? null : table[card.rank];
      return entry == null ? null : Odds.fromTuple(entry);
    });
  }

  /** Cards left in the pile by rank (0 = jokers), only ranks present. */
  remainingByRank(): Map<number, number> {
    const out = new Map<number, number>();
    rankHistogram(this.drawPile).forEach((n, rank) => { if (n) out.set(rank, n); });
    return out;
  }

  // ----- moves ---------------------------------------------------------- //

  /** Call on a live box and flip (RULES.md, "Taking a Turn"). `drawn` names
   * the card that came off the pile when its order is unknown (the Game
   * Assistant); otherwise the top card is flipped. */
  play(position: number, call: Call, drawn?: Card | null): PlayResult {
    if (this.isOver) throw new RulesError("the game is over");
    if (this.recoveryPending) throw new RulesError("choose a failed box to recover, or skip, first");
    if (!Number.isInteger(position) || position < 0 || position >= BOX_SIZE) {
      throw new RulesError(`no box at position ${position}`);
    }
    const target = this.box[position] ?? null;
    if (target === null) throw new RulesError("that box has failed");
    checkCall(call);
    const inclusive = INCLUSIVE_CALLS.includes(call);
    if (inclusive && this.inclusiveLeft <= 0) throw new RulesError("no inclusive calls left");
    if (drawn != null && !this.drawPile.some((card) => card.equals(drawn))) {
      throw new RulesError(`${drawn.label()} is not in the draw pile`);
    }

    this.#history.push(this.#snapshot());

    if (inclusive) { // spent when the call is made, win or lose
      this.inclusiveLeft -= 1;
      this.stats.inclusiveUsed += 1;
    }
    const card = drawn == null ? this.drawPile.shift()! : takeCard(this.drawPile, drawn);
    this.stats.plays += 1;
    if (card.isJoker) this.stats.jokersDrawn += 1;
    this.#count(card);

    const success = callWins(call, card, target);
    const exactMatch = isExactMatch(card, target);
    if (success) {
      this.box[position] = card;
    } else {
      // The drawn card goes on top of the box card and the box turns face
      // down; a recovery turns the stack back over, so the card that beat
      // the box is the one that comes back (docs/RULES.md).
      this.box[position] = null;
      this.failed.set(position, card);
    }

    const recoveryEarned = success && inclusive && exactMatch;
    const recoveryPending = recoveryEarned && this.failed.size > 0;
    const recoveryLost = recoveryEarned && !recoveryPending;
    this.recoveryPending = recoveryPending;
    if (recoveryLost) this.stats.recoveriesLost += 1;

    return {
      position, call, target, drawn: card, success, exactMatch, recoveryEarned,
      recoveryPending, recoveryLost, gameOver: this.isOver, won: this.won,
    };
  }

  /** Spend a pending recovery on one failed box (RULES.md, "Recovering").
   * The box comes back with the card that beat it, which was already
   * counted when it was flipped, so the counts don't change. */
  recover(position: number): Card {
    if (!this.recoveryPending) throw new RulesError("no recovery has been earned");
    const card = this.failed.get(position);
    if (card === undefined) throw new RulesError("that box has not failed");
    this.failed.delete(position);
    this.box[position] = card;
    this.recoveryPending = false;
    this.stats.recoveries += 1;
    return card;
  }

  skipRecovery(): void {
    if (!this.recoveryPending) throw new RulesError("no recovery has been earned");
    this.recoveryPending = false;
    this.stats.recoveriesLost += 1;
  }

  /** Undo the last play, including any recovery made with it. */
  undo(): boolean {
    const snap = this.#history.pop();
    if (snap === undefined) return false;
    this.box = snap.box;
    this.failed = snap.failed;
    this.drawPile = snap.drawPile;
    this.inclusiveLeft = snap.inclusiveLeft;
    this.recoveryPending = snap.recoveryPending;
    this.counts = snap.counts;
    this.stats = snap.stats;
    return true;
  }

  // ----- internals ------------------------------------------------------ //

  #count(card: Card): void {
    countValues(card).forEach((value, i) => { this.counts[i]! += value; });
  }

  #snapshot(): Snapshot {
    return {
      box: [...this.box], failed: new Map(this.failed), drawPile: [...this.drawPile],
      inclusiveLeft: this.inclusiveLeft, recoveryPending: this.recoveryPending,
      counts: [...this.counts], stats: { ...this.stats },
    };
  }
}