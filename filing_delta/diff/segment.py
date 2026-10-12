"""Split a section's canonical text into units: paragraphs, headings, and whole data tables (M3).

Pure. Input is the parser's canonical text plus its block map (char start, char end, block index, table id, row id).
Every unit is a [start, end) span of the canonical text, so later citations can point into it exactly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import key, loose_key

_GLYPH = re.compile(r"^(?:[•●◦▪■□‣∙·\-–—*]|\(?[a-z0-9]{1,3}[.)]|\([a-z0-9]{1,3}\))$", re.I)
_SENTENCE_END = re.compile(r"[.!?:;”\"’')\]]\s*$")
DATA_CELL_MAX = 40          # a data table is mostly short cells (numbers, labels)
DATA_SHORT_FRACTION = 0.6


@dataclass(frozen=True)
class Unit:
    idx: int
    kind: str           # paragraph | heading | table
    start: int
    end: int
    key: str            # comparison key (quotes/dashes/whitespace folded)
    loose: str          # case- and punctuation-insensitive key, for the formatting_only fact


def _data_tables(text: str, bmap: list[tuple]) -> set[int]:
    """Tables that hold data (several rows of mostly short cells, some numeric), not layout."""
    by_table: dict[int, list[tuple]] = {}
    for e in bmap:
        if e[3] is not None:
            by_table.setdefault(e[3], []).append(e)
    out = set()
    for t, cells in by_table.items():
        rows = {c[4] for c in cells}
        texts = [text[c[0]:c[1]] for c in cells]
        short = sum(len(x) <= DATA_CELL_MAX for x in texts) / len(texts)
        if len(rows) >= 2 and short >= DATA_SHORT_FRACTION and any(re.search(r"\d", x) for x in texts):
            out.add(t)
    return out


def segment(text: str, bmap: list[tuple]) -> list[Unit]:
    if not text:
        return []
    data = _data_tables(text, bmap)
    # 1. Pieces: block spans, with page-break re-joins (separated by a single space) merged back together.
    pieces: list[list] = []          # [start, end, table, row]
    for s, e, _idx, table, row in (tuple(x) for x in bmap):
        if pieces and text[pieces[-1][1]:s] == " ":
            pieces[-1][1] = e
            continue
        pieces.append([s, e, table, row])
    # 2. Group: a whole data table is one unit; a layout-table row is one unit; a lone bullet glyph joins its text.
    groups: list[list] = []          # [start, end, kind_hint]
    for s, e, table, row in pieces:
        prev = groups[-1] if groups else None
        if table in data:
            if prev and prev[2] == ("table", table):
                prev[1] = e
                continue
            groups.append([s, e, ("table", table)])
            continue
        if table is not None and prev and prev[2] == ("row", table, row):
            prev[1] = e
            continue
        if prev and prev[2][0] != "table" and _GLYPH.match(text[prev[0]:prev[1]]):
            prev[1] = e
            prev[2] = ("row", table, row) if table is not None else ("text",)
            continue
        groups.append([s, e, ("row", table, row) if table is not None else ("text",)])
    units = []
    for i, (s, e, hint) in enumerate(groups):
        t = text[s:e]
        if hint[0] == "table":
            kind = "table"
        elif len(t) <= 120 and not _SENTENCE_END.search(t):
            kind = "heading"
        else:
            kind = "paragraph"
        units.append(Unit(idx=i, kind=kind, start=s, end=e, key=key(t), loose=loose_key(t)))
    return units
