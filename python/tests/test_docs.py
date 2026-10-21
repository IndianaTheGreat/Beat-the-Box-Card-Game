"""
==============================================
DOCUMENTATION CONSISTENCY TESTS
==============================================
File Location: Beat-the-Box-Card-Game/python/tests/test_docs.py
Status: ACTIVE
Version: 1.3
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 308 passed)

VERSION 1.3 CHANGES (2026-10-20):
- The two docs/RULES.md contents links are fixed, so every file's
  anchors are checked with no known failures.

VERSION 1.2 CHANGES (2026-10-20):
- RULES.md and STRATEGY.md now live in docs/; the paths follow them, and
  nothing is left at the old place in the repo root.
- New: every relative link in every Markdown file points at a file that
  exists (before, only links with a #anchor were checked).
- The in-app help is written in markup (btb/markup.py): its count table
  and strategy headings are read with markup.table_rows / headings.
- The in-app text names docs/RULES.md and docs/STRATEGY.md (never the old
  root paths), and the README and guide list Ctrl+K.

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
  * The card-count tables in docs/RULES.md, docs/STRATEGY.md,
    docs/CARD_COUNTING.md and the in-app strategy guide all match
    engine.COUNT_TABLES.
  * Every strategy section in the app has a matching heading in
    docs/STRATEGY.md.
  * Every keyboard shortcut appears in the README and in docs/GUIDE.md.
  * The README links to all three guides, and the tool guide covers all
    four tools.
  * Every theme is listed in docs/GUIDE.md.

DEPENDENCIES:
------------
- pytest (requirements-dev.txt)
- btb.markup, btb.text, btb.engine
- Standard library: re, pathlib, unicodedata, urllib.parse

KEY FUNCTIONS:
-------------
- markdown_count_table(doc) -> the count table rows from a Markdown file
- github_anchor(heading) -> the #anchor GitHub gives a heading
- anchors(doc) -> every anchor a Markdown file defines

CLI USAGE:
---------
# From the python/ folder
python -m pytest tests/test_docs.py
"""

import re
import unicodedata
from pathlib import Path
from urllib.parse import quote, unquote

import pytest

from btb import markup, text
from btb.engine import COUNT_TABLES, JOKER_RANK, RANKS

ROOT = Path(__file__).resolve().parents[2]
RULES = (ROOT / "docs" / "RULES.md").read_text(encoding="utf-8")
STRATEGY = (ROOT / "docs" / "STRATEGY.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "docs" / "GUIDE.md").read_text(encoding="utf-8")
COUNTING = (ROOT / "docs" / "CARD_COUNTING.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

EXPECTED = [[table[r] for r in RANKS] + [0] for table in COUNT_TABLES]  # + joker


def _number(cell: str) -> int:
    return int(cell.strip().replace("−", "-").replace("+", ""))


def markdown_count_table(doc: str) -> list:
    rows = [line for line in doc.splitlines() if line.startswith("| **Method")]
    return [[_number(c) for c in row.strip("|").split("|")[1:]] for row in rows]


@pytest.mark.parametrize("name, doc", [("docs/RULES.md", RULES),
                                       ("docs/STRATEGY.md", STRATEGY),
                                       ("docs/CARD_COUNTING.md", COUNTING)])
def test_markdown_count_tables_match_the_engine(name, doc):
    assert markdown_count_table(doc) == EXPECTED, name
    assert JOKER_RANK == 0  # the last column is the joker


def test_in_app_count_table_matches_the_engine():
    rows = {row[0]: [_number(cell) for cell in row[1:]]
            for row in markup.table_rows(text.STRATEGY_GUIDE)
            if row[0] in ("Basic", "Weighted", "Advanced")}
    assert [rows["Basic"], rows["Weighted"], rows["Advanced"]] == [e[:-1] for e in EXPECTED]
    header = next(row for row in markup.table_rows(text.STRATEGY_GUIDE) if row[0] == "Rank")
    assert header[1:] == ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]


def test_every_in_app_strategy_section_is_in_strategy_md():
    headings = [line.lower() for line in STRATEGY.splitlines() if line.startswith("## ")]
    in_app = markup.headings(text.STRATEGY_GUIDE, level=2)
    for section in text.STRATEGY_SECTIONS:
        assert any(section.lower() in h for h in headings), section
        assert section in in_app, section


def test_in_app_text_points_at_the_docs_folder():
    every_text = [text.RULES_SUMMARY, text.STRATEGY_GUIDE, text.tool_guide(),
                  text.shortcut_help(), *text.TOOL_HELP.values()]
    for body in every_text:
        for name in re.findall(r"[\w/]*(?:RULES|STRATEGY)\.md", body):
            assert name.startswith("docs/"), name
    assert "docs/RULES.md" in text.RULES_SUMMARY and "docs/STRATEGY.md" in text.STRATEGY_GUIDE


def test_every_shortcut_is_documented():
    for keys, *_ in text.SHORTCUTS:
        for key in re.findall(r"Ctrl\+\w|\b[WSDA]\b", keys):
            assert f"`{key}`" in README or key in README, key
            assert key in GUIDE, key


def test_readme_links_both_guides_and_the_guide_covers_every_tool():
    assert "(docs/RULES.md)" in README and "(docs/STRATEGY.md)" in README
    assert "(docs/GUIDE.md)" in README and "(docs/CARD_COUNTING.md)" in README
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


DOCS = {"docs/STRATEGY.md": ROOT / "docs" / "STRATEGY.md",
        "docs/GUIDE.md": ROOT / "docs" / "GUIDE.md",
        "docs/CARD_COUNTING.md": ROOT / "docs" / "CARD_COUNTING.md",
        "README.md": ROOT / "README.md", "docs/RULES.md": ROOT / "docs" / "RULES.md"}


def test_rules_and_strategy_moved_into_docs():
    assert not (ROOT / "RULES.md").exists() and not (ROOT / "STRATEGY.md").exists()
    assert (ROOT / "docs" / "RULES.md").exists() and (ROOT / "docs" / "STRATEGY.md").exists()


@pytest.mark.parametrize("name", sorted(DOCS))
def test_every_relative_link_points_at_a_file(name):
    path = DOCS[name]
    doc = path.read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)\s]*)?\)", doc):
        if re.match(r"[a-z]+:", target):              # http:, https:, mailto:
            continue
        assert (path.parent / unquote(target)).resolve().exists(), f"{name}: {target}"


@pytest.mark.parametrize("name", sorted(DOCS))
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