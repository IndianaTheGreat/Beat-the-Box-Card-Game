"""
==============================================
DOCUMENTATION CONSISTENCY TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_docs.py
Status: ACTIVE
Version: 1.1
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 254 passed)

VERSION 1.1 CHANGES (2026-10-20):
- docs/CARD_COUNTING.md joins the checks: its count table must match the
  engine, its #anchor links must work, and the README must link to it.
- The guide's rules for a 7 and a 9 (when the count beats the card's own
  lean) and the Basic-count identity are checked against the engine's
  odds on random piles.

VERSION 1.0 CHANGES (2026-10-20):
- New. Keeps RULES.md, STRATEGY.md, docs/GUIDE.md, the README and the
  in-app text in step with the engine and with each other.
- Every #anchor link in STRATEGY.md, docs/GUIDE.md and the README points
  at a real heading (GitHub's anchor rules, emoji included).

DESCRIPTION:
-----------
  * The card-count tables in RULES.md, STRATEGY.md, docs/CARD_COUNTING.md
    and the in-app strategy guide all match engine.COUNT_TABLES.
  * Every strategy section in the app has a matching heading in
    STRATEGY.md.
  * Every keyboard shortcut appears in the README and in docs/GUIDE.md.
  * The README links to all three guides, and the tool guide covers all
    four tools.
  * Every theme is listed in docs/GUIDE.md.

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)
- Standard library: re, pathlib, unicodedata, urllib.parse

KEY FUNCTIONS:
-------------
- markdown_count_table(doc) -> the count table rows from a Markdown file
- github_anchor(heading) -> the #anchor GitHub gives a heading
- anchors(doc) -> every anchor a Markdown file defines

CLI USAGE:
---------
# From the python/ folder
pytest tests/test_docs.py
"""

import re
import unicodedata
from pathlib import Path
from urllib.parse import quote, unquote

import pytest

from btb import text
from btb.engine import COUNT_TABLES, JOKER_RANK, RANKS

ROOT = Path(__file__).resolve().parents[2]
RULES = (ROOT / "RULES.md").read_text(encoding="utf-8")
STRATEGY = (ROOT / "STRATEGY.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "docs" / "GUIDE.md").read_text(encoding="utf-8")
COUNTING = (ROOT / "docs" / "CARD_COUNTING.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

EXPECTED = [[table[r] for r in RANKS] + [0] for table in COUNT_TABLES]  # + joker


def _number(cell: str) -> int:
    return int(cell.strip().replace("−", "-").replace("+", ""))


def markdown_count_table(doc: str) -> list:
    rows = [line for line in doc.splitlines() if line.startswith("| **Method")]
    return [[_number(c) for c in row.strip("|").split("|")[1:]] for row in rows]


@pytest.mark.parametrize("name, doc", [("RULES.md", RULES), ("STRATEGY.md", STRATEGY),
                                       ("docs/CARD_COUNTING.md", COUNTING)])
def test_markdown_count_tables_match_the_engine(name, doc):
    assert markdown_count_table(doc) == EXPECTED, name
    assert JOKER_RANK == 0  # the last column is the joker


def test_in_app_count_table_matches_the_engine():
    rows = {}
    for line in text.STRATEGY_GUIDE.splitlines():
        parts = line.split()
        if parts and parts[0] in ("Basic", "Weighted", "Advanced") and len(parts) == 14:
            rows[parts[0]] = [_number(p) for p in parts[1:]]
    assert [rows["Basic"], rows["Weighted"], rows["Advanced"]] == [e[:-1] for e in EXPECTED]


def test_every_in_app_strategy_section_is_in_strategy_md():
    headings = [line.lower() for line in STRATEGY.splitlines() if line.startswith("## ")]
    guide_headings = [line.strip() for line in text.STRATEGY_GUIDE.splitlines()
                      if line.strip() and line.strip() == line.strip().upper()
                      and re.search("[A-Z]", line)]
    for section in text.STRATEGY_SECTIONS:
        assert any(section.lower() in h for h in headings), section
        assert section.upper() in guide_headings, section


def test_every_shortcut_is_documented():
    for keys, *_ in text.SHORTCUTS:
        for key in re.findall(r"Ctrl\+\w|\b[WSDA]\b", keys):
            assert f"`{key}`" in README or key in README, key
            assert key in GUIDE, key


def test_readme_links_both_guides_and_the_guide_covers_every_tool():
    assert "STRATEGY.md" in README and "docs/GUIDE.md" in README
    assert "docs/CARD_COUNTING.md" in README
    for tool in ("Game Player", "Game Assistant", "Simulator", "Strategy Optimizer"):
        assert re.search(rf"^## .*{tool}", GUIDE, re.M), tool


def test_every_theme_is_listed_in_the_guide():
    pytest.importorskip("tkinter")
    from btb import theme
    for number, name in enumerate(theme.theme_names(), start=1):
        assert re.search(rf"\| {number} \| \**{name}", GUIDE), name


def test_tool_help_covers_every_tool():
    assert set(text.TOOL_HELP) == {"player", "assistant", "simulator", "optimizer"}


# ------------------------------------------------------------ anchor links -- #

def github_anchor(heading: str) -> str:
    """GitHub's heading anchor: lower-case, keep letters, marks, digits,
    underscores, hyphens and spaces (emoji go, their variation selectors
    stay), then spaces become hyphens."""
    kept = "".join(ch for ch in heading.strip().lower()
                   if ch in " -_" or unicodedata.category(ch)[0] in "LMN")
    return kept.replace(" ", "-")


def anchors(doc: str) -> set:
    found = set()
    in_code = False
    for line in doc.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and re.match(r"#{1,6} ", line):
            found.add(github_anchor(line.lstrip("#")))
    return found


DOCS = {"STRATEGY.md": ROOT / "STRATEGY.md", "docs/GUIDE.md": ROOT / "docs" / "GUIDE.md",
        "docs/CARD_COUNTING.md": ROOT / "docs" / "CARD_COUNTING.md",
        "README.md": ROOT / "README.md", "RULES.md": ROOT / "RULES.md"}


@pytest.mark.parametrize("name", ["STRATEGY.md", "docs/GUIDE.md", "docs/CARD_COUNTING.md",
                                  "README.md"])
def test_every_anchor_link_points_at_a_real_heading(name):
    path = DOCS[name]
    doc = path.read_text(encoding="utf-8")
    for target, anchor in re.findall(r"\]\(([^)#\s]*)#([^)\s]+)\)", doc):
        linked = (path.parent / target).resolve() if target else path
        assert linked.exists(), f"{name}: {target} does not exist"
        wanted = unquote(anchor)
        assert wanted in anchors(linked.read_text(encoding="utf-8")), \
            f"{name}: #{anchor} is not a heading in {linked.name}"


def test_anchor_rules_match_known_github_anchors():
    assert github_anchor(" 🎯 The Goal") == "-the-goal"
    assert quote(github_anchor(" ⚖️ Inclusive Calls")) == "%EF%B8%8F-inclusive-calls"


# ------------------------------------------------- card-counting claims -- #

def test_card_counting_rules_for_7s_8s_and_9s_match_the_engine():
    """docs/CARD_COUNTING.md: Basic count = low left - high left; on an 8,
    Lower is better exactly when the count is positive; on a 7, Lower is
    better only when the count is more than the 7s and 8s left; on a 9,
    Higher is better only when the count is below minus the 8s and 9s left."""
    import random
    from btb.engine import Card, count_values, odds_against, standard_deck
    assert "more than the number of `7`s and `8`s still in the pile" in COUNTING
    assert "below minus the number of `8`s and `9`s still in the pile" in COUNTING
    rng = random.Random(2026)
    for _ in range(2000):
        deck = standard_deck(rng.randint(0, 2))
        rng.shuffle(deck)
        cut = rng.randint(1, len(deck) - 1)
        seen, pile = deck[:cut], deck[cut:]
        basic = sum(count_values(card)[0] for card in seen)
        low = sum(1 for c in pile if not c.is_joker and 2 <= c.rank <= 7)
        high = sum(1 for c in pile if not c.is_joker and c.rank >= 9)
        assert basic == low - high
        left = {r: sum(1 for c in pile if c.rank == r) for r in (7, 8, 9)}
        seven, eight, nine = (odds_against(Card(r, "♠"), pile) for r in (7, 8, 9))
        assert (eight.lower > eight.higher) == (basic > 0)
        assert (seven.lower > seven.higher) == (basic > left[7] + left[8])
        assert (nine.higher > nine.lower) == (basic < -(left[8] + left[9]))