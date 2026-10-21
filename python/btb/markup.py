"""
==============================================
HELP-PAGE MARKUP
==============================================
File Location: Beat-the-Box-Card-Game/python/btb/markup.py
Status: ACTIVE
Version: 1.0
Last Updated: 2026-10-20
Last Tested: 2026-10-20 (pytest: 295 passed, 1 xfailed)

VERSION 1.0 CHANGES (2026-10-20):
- New. Reads the light Markdown-style markup the in-app help text
  (btb/text.py) is written in and turns it into a list of blocks
  (headings, paragraphs, list items, tables, notes, rules) that the
  DocView widget draws as a formatted page.

DESCRIPTION:
-----------
The help pages (How to Play, Strategy, Tool Guide, Shortcuts) are written
in a small subset of Markdown, so they read well as plain text too:

  # Title / ## Section / ### Sub-section     headings
  a paragraph, which may run over             lines that follow each other
  several lines                               join into one paragraph
  - a bullet   (or *)                         list items; indent a line two
  1. a numbered item                          spaces more to continue an item
    - a nested bullet                         or to nest a list
  | Key | What it does |                      a table; the |---| line ends
  |---|---|                                   the header rows
  > a note                                    a highlighted note
  ---                                         a dividing line
  **bold**, `a key or a file name`            inside any text

Card names such as A♥, 10♠ or a bare ♦ are picked out as "card" pieces,
so the page can draw them in card colours.

No Tkinter here, so the tests (and the TypeScript port) can read the help
text on any machine.

DEPENDENCIES:
------------
- Standard library: re, dataclasses, typing

KEY FUNCTIONS:
-------------
- parse(source) -> List[Block]
- spans(text) -> List[(text, style)], style "", "bold", "code" or "card"
- plain_text(source) -> the text with the markup taken out (tests, search)
- table_rows(source) -> every table row as a list of plain cell strings
- headings(source, level) -> the plain text of every heading at a level

NOTES:
-----
- Block kinds: heading (level 1-3), para, item (level 0-2, marker "•" or
  "1."), table (header rows, body rows), note, rule.
- Anything the parser doesn't recognise is kept as an ordinary paragraph,
  so a typo never loses text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple

Span = Tuple[str, str]          # (text, style): style "", "bold", "code" or "card"

CARD = re.compile(r"(?:10|[2-9JQKA])?[♠♥♦♣]")
INLINE = re.compile(r"\*\*(.+?)\*\*|`([^`]+)`")
ITEM = re.compile(r"^( *)(?:[-*]|(\d+)\.) +(.*)$")
HEADING = re.compile(r"^(#{1,3}) +(.*)$")
TABLE_RULE = re.compile(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


@dataclass
class Block:
    kind: str                                   # heading, para, item, table, note, rule
    spans: List[Span] = field(default_factory=list)
    level: int = 0                              # heading 1-3, list nesting 0-2
    marker: str = ""                            # "•" or "1." for list items
    header: List[List[List[Span]]] = field(default_factory=list)   # table header rows
    rows: List[List[List[Span]]] = field(default_factory=list)     # table body rows


def _cards(text: str, style: str) -> List[Span]:
    """Split plain or bold text so card names become their own pieces."""
    out: List[Span] = []
    last = 0
    for match in CARD.finditer(text):
        if match.start() > last:
            out.append((text[last:match.start()], style))
        out.append((match.group(), "card"))
        last = match.end()
    if last < len(text):
        out.append((text[last:], style))
    return out


def spans(text: str) -> List[Span]:
    """Inline markup: **bold**, `code`, and card names."""
    out: List[Span] = []
    last = 0
    for match in INLINE.finditer(text):
        out += _cards(text[last:match.start()], "")
        if match.group(1) is not None:
            out += _cards(match.group(1), "bold")
        else:
            out.append((match.group(2), "code"))
        last = match.end()
    out += _cards(text[last:], "")
    return [(t, s) for t, s in out if t]


def _cells(line: str) -> List[List[Span]]:
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [spans(cell.strip()) for cell in inner.split("|")]


def parse(source: str) -> List[Block]:
    """Turn help-page markup into blocks (see the module notes)."""
    blocks: List[Block] = []
    lines = source.strip("\n").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip():
            i += 1
            continue
        heading = HEADING.match(line)
        if heading:
            blocks.append(Block("heading", spans(heading.group(2).strip()),
                                level=len(heading.group(1))))
            i += 1
            continue
        if line.strip() == "---":
            blocks.append(Block("rule"))
            i += 1
            continue
        if line.lstrip().startswith("|"):
            table = Block("table")
            rows: List[List[List[Span]]] = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                if TABLE_RULE.match(lines[i].strip()):
                    table.header, rows = rows, []
                else:
                    rows.append(_cells(lines[i]))
                i += 1
            table.rows = rows
            blocks.append(table)
            continue
        if line.startswith(">"):
            words = []
            while i < len(lines) and lines[i].startswith(">"):
                words.append(lines[i][1:].strip())
                i += 1
            blocks.append(Block("note", spans(" ".join(w for w in words if w))))
            continue
        item = ITEM.match(line)
        if item:
            indent = len(item.group(1))
            words = [item.group(3).strip()]
            i += 1
            # Continuation lines: indented further than the marker, not a new item.
            while (i < len(lines) and lines[i].strip()
                   and len(lines[i]) - len(lines[i].lstrip()) > indent
                   and not ITEM.match(lines[i])):
                words.append(lines[i].strip())
                i += 1
            marker = f"{item.group(2)}." if item.group(2) else "•"
            blocks.append(Block("item", spans(" ".join(words)), level=min(2, indent // 2),
                                marker=marker))
            continue
        words = [line.strip()]
        i += 1
        while (i < len(lines) and lines[i].strip() and not HEADING.match(lines[i])
               and not ITEM.match(lines[i]) and not lines[i].lstrip().startswith(("|", ">"))
               and lines[i].strip() != "---"):
            words.append(lines[i].strip())
            i += 1
        blocks.append(Block("para", spans(" ".join(words))))
    return blocks


def _join(parts: List[Span]) -> str:
    return "".join(text for text, _style in parts)


def plain_text(source: str) -> str:
    """The text with its markup taken out, one block per line."""
    lines = []
    for block in parse(source):
        if block.kind == "table":
            for row in block.header + block.rows:
                lines.append("  ".join(_join(cell) for cell in row))
        elif block.kind == "item":
            lines.append(f"{'  ' * block.level}{block.marker} {_join(block.spans)}")
        elif block.kind != "rule":
            lines.append(_join(block.spans))
    return "\n".join(lines)


def table_rows(source: str) -> List[List[str]]:
    """Every table row (headers included) as plain cell strings."""
    rows = []
    for block in parse(source):
        if block.kind == "table":
            rows += [[_join(cell) for cell in row] for row in block.header + block.rows]
    return rows


def headings(source: str, level: int = 2) -> List[str]:
    """The plain text of every heading at `level`."""
    return [_join(b.spans) for b in parse(source) if b.kind == "heading" and b.level == level]