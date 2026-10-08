"""Heading grammar, page furniture, and TOC detection (design §1 and §2.1 step 3, §2.2 signal 1)."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass

from .blocks import Block

_ITEM = re.compile(
    r"^(?:part\s+(?P<part>iv|i{1,3})\b[\s.,:;\-–—]*)?"
    r"item[\s.]*(?P<num>\d{1,2})(?P<suf>[a-c])?(?![0-9])(?:(?<=[a-c])|(?![a-z]))"
    r"\s*[.:\-–—]?\s*(?P<title>.*)$",
    re.I,
)
# "Parts I and II" (JPM) is a part heading too; it must end the section before it, not trail inside it.
_PART = re.compile(
    r"^parts?\s+(?P<part>iv|i{1,3})\b(?:\s+(?:and|&)\s+(?:iv|i{1,3})\b)?(?:[\s.,:;\-–—]+(?P<rest>.*))?$", re.I)

# Keyword the heading's title must contain (near its start) for each item. Empty title (bare "Item 7.") is accepted.
TITLES_10K = {
    "1": ("business",), "1a": ("risk factors",), "1b": ("unresolved",), "1c": ("cybersecurity",),
    "2": ("propert",), "3": ("legal",), "4": ("mine safety", "submission of matters", "reserved", "removed"),
    "5": ("market",), "6": ("selected", "reserved", "[reserved]"), "7": ("management",),
    "7a": ("quantitative",), "8": ("financial statements",), "9": ("changes in",), "9a": ("controls",),
    "9b": ("other information",), "9c": ("disclosure regarding",), "10": ("directors",), "11": ("executive",),
    "12": ("security ownership",), "13": ("certain relationships",), "14": ("principal account",),
    "15": ("exhibit",), "16": ("form 10-k summary", "summary"),
}
TITLES_10Q = {
    ("i", "1"): ("financial statements",), ("i", "2"): ("management",), ("i", "3"): ("quantitative",),
    ("i", "4"): ("controls",), ("ii", "1"): ("legal",), ("ii", "1a"): ("risk factors",),
    ("ii", "2"): ("unregistered",), ("ii", "3"): ("defaults",), ("ii", "4"): ("mine safety", "reserved", "removed"),
    ("ii", "5"): ("other information",), ("ii", "6"): ("exhibit",),
}

MAX_HEADING_LEN = 220
_TRAILING_PAGE = re.compile(r"(?:\s|^)(?:page\s+)?(?:[a-z]-)?\d{1,3}(?:\s*[-–,]\s*(?:[a-z]-)?\d{1,3})*\s*$", re.I)
_PAGE_ONLY = re.compile(
    r"^(?:[-–—\s]*(?:page\s+)?(?:[a-z]{1,2}\s*-\s*)?\d{1,3}[-–—\s]*|[ivxlc]{1,6}|page \d+ of \d+)$", re.I)
_TOC_TEXT = re.compile(r"^(?:\(?back to\)?\s+)?(?:table\s+of\s+contents|index|contents|return to (?:table of contents|top))$", re.I)
_FOOTER_FORM = re.compile(r"(?:(?:19|20)\d\d\s+)?form\s+10-[kq]\b", re.I)


def page_number(text: str, lenient: bool = False) -> int | None:
    """The page number in a footer like '24', '- 24 -', 'Page 24', 'K-24', '2025 FORM 10-K 23', '24 2025 FORM 10-K'.

    ``lenient`` is for blocks already known to be running footers: years, quarter tokens ('2Q') and form names are
    stripped, and one remaining 1–3 digit number is the page ('GE 2020 FORM 10-K 44', '2025 2Q FORM 10-Q 5').
    """
    t = _FOOTER_FORM.sub(" ", text).strip()
    if _PAGE_ONLY.match(t):
        m = re.search(r"(\d{1,3})(?!.*\d)", t)
        return int(m.group(1)) if m else None
    if lenient and len(text) <= 80:
        rest = re.sub(r"\b(?:19|20)\d\d\b|\b[1-4]q\b|\bq[1-4]\b", " ", t, flags=re.I)
        nums = re.findall(r"\b\d{1,3}\b", rest)
        if len(nums) == 1 and len(re.sub(r"[\W\d_]", "", rest)) <= 30:
            return int(nums[0])
    return None


_CONTINUED = re.compile(r"\((?:continued|cont['’]?d)\)\s*$", re.I)


def norm_title(s: str) -> str:
    s = s.lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", s).strip(" .,;:-–—")


@dataclass(frozen=True)
class ItemHeading:
    block: int
    part: str | None        # "i" / "ii" when written in the heading itself
    item: str               # "1a", "7", ...
    title: str


def heading_text(b: Block) -> str:
    """The text a heading test sees: the whole table row when the block is a row's first non-empty cell."""
    return b.row_text if b.row is not None else b.text


def match_item(text: str) -> tuple[str | None, str, str] | None:
    if len(text) > MAX_HEADING_LEN:
        return None
    m = _ITEM.match(text.strip())
    if not m:
        return None
    item = (m.group("num") + (m.group("suf") or "")).lower()
    return ((m.group("part") or "").lower() or None, item, m.group("title") or "")


def title_ok(item: str, title: str, keywords: tuple[str, ...]) -> bool:
    t = norm_title(_TRAILING_PAGE.sub("", title))
    if not t:
        return True
    head = t[:70]
    return any(k in head for k in keywords)


def furniture(blocks: list[Block]) -> set[int]:
    return furniture_detail(blocks)[0]


def furniture_detail(blocks: list[Block]) -> tuple[set[int], set[int]]:
    """Indexes of page furniture: page numbers, TOC back-links, '(Continued)' and repeated running headers/footers.

    Running headers are recognized structurally, not by content: short, non-table text that recurs at least three
    times *next to a page break*. Repetition alone would also catch legitimate repeated subheadings.
    """
    out: set[int] = set()
    running: set[int] = set()
    near_break: set[int] = set()
    for b in blocks:
        if b.page_break_before:
            for j in range(max(0, b.idx - 4), min(len(blocks), b.idx + 4)):
                near_break.add(j)
    has_breaks = bool(near_break)
    row_cells = Counter(b.row for b in blocks if b.row is not None)
    for b in blocks:
        t = b.text
        lone = b.row is None or row_cells[b.row] == 1
        # A bare number is a page number only next to a page break (or, in a document with no page-break markup at
        # all, outside any multi-cell table row). Otherwise it is data: a table cell like "994" must stay.
        if page_number(t) is not None and lone and (b.idx in near_break or not has_breaks):
            out.add(b.idx)
        elif _TOC_TEXT.match(t) or (len(t) <= 160 and _CONTINUED.search(t)):
            out.add(b.idx)
    key = lambda t: re.sub(r"\d+", "#", t.lower())  # noqa: E731  ("Page 12" and "Page 13" share a key)
    page_of: list[int] = []
    n = 0
    for b in blocks:
        n += b.page_break_before
        page_of.append(n)
    # A running header/footer recurs on near-consecutive pages. Repetition alone is not enough: JPM's 2020 10-K has
    # a real "COVID-19 Pandemic" subheading at three page tops, far apart, and it must stay in the text.
    by_key: dict[str, list[int]] = defaultdict(list)
    for b in blocks:
        if b.idx in near_break and len(b.text) <= 160 and not b.in_table:
            by_key[key(b.text)].append(b.idx)
    for idxs in by_key.values():
        if len(idxs) < 3:
            continue
        chain = [idxs[0]]
        for i in idxs[1:]:
            if page_of[i] - page_of[chain[-1]] <= 2:
                chain.append(i)
                continue
            if len(chain) >= 3:
                out.update(chain)
                running.update(chain)
            chain = [i]
        if len(chain) >= 3:
            out.update(chain)
            running.update(chain)
    # Footer rows laid out as tables ("Apple Inc. | Q3 2026 Form 10-Q | 20"): same rule, keyed on the row.
    rkey = Counter(key(b.row_text) for b in blocks if b.idx in near_break and b.in_table and len(b.row_text) <= 160
                   and re.search(r"\d", b.row_text))
    for b in blocks:
        if b.idx in near_break and b.in_table and len(b.row_text) <= 160 and rkey[key(b.row_text)] >= 3 \
                and re.search(r"form\s+10-[kq]|\|", b.row_text, re.I):
            out.add(b.idx)
    return out, running


def is_toc_entry(b: Block, blocks: list[Block]) -> bool:
    """A heading-shaped block that is really a table-of-contents line: it links somewhere, or ends in a page number."""
    if b.is_link or b.links:
        return True
    row = [x for x in blocks[max(0, b.idx - 6): b.idx + 8] if b.row is not None and x.row == b.row]
    if any(x.is_link or x.links for x in row):
        return True
    text = heading_text(b)
    m = match_item(text)
    title = m[2] if m else text
    return bool(_TRAILING_PAGE.search(title)) and bool(re.search(r"[a-z]{3}", title, re.I))


def item_headings(blocks: list[Block], furn: set[int], running: set[int] = frozenset()) -> list[ItemHeading]:
    """Every block that reads as an Item heading and is not furniture or a TOC entry. One per table row.

    Exception: when a filer repeats an Item heading as its running page header (Berkshire's 10-Q prints
    "Item 2. Management's Discussion…" atop every MD&A page), the *first* occurrence is the real heading.
    """
    out: list[ItemHeading] = []
    seen_rows: set[int] = set()
    seen_running: set[str] = set()
    for b in blocks:
        if b.idx in furn:
            k = norm_title(b.text)
            if b.idx not in running or k in seen_running or not match_item(b.text) or _CONTINUED.search(b.text):
                continue
            seen_running.add(k)
        if b.row is not None:
            if b.row in seen_rows:
                continue
        m = match_item(heading_text(b))
        if not m:
            continue
        if b.row is not None:
            seen_rows.add(b.row)
        if is_toc_entry(b, blocks):
            continue
        part, item, title = m
        out.append(ItemHeading(block=b.idx, part=part, item=item, title=title))
    return out


def part_markers(blocks: list[Block], furn: set[int]) -> list[tuple[int, str]]:
    """(block, 'i'|'ii') for PART headings that are not TOC entries."""
    out = []
    seen_rows: set[int] = set()
    for b in blocks:
        if b.idx in furn or (b.row is not None and b.row in seen_rows):
            continue
        text = heading_text(b)
        m = _PART.match(text.strip()) if len(text) <= 120 else None
        if not m:
            m2 = match_item(text)
            if m2 and m2[0]:
                if b.row is not None:
                    seen_rows.add(b.row)
                if not is_toc_entry(b, blocks):
                    out.append((b.idx, m2[0]))
            continue
        if b.row is not None:
            seen_rows.add(b.row)
        if not is_toc_entry(b, blocks):
            out.append((b.idx, m.group("part").lower()))
    return out
