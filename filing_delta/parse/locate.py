"""Locate and slice target sections: two signals, reconciled; archetypes B/C/D (design §2.2–2.5).

Pure: a Flattened document plus its form in, one ParseResult per target section out.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .blocks import Block, Flattened
from .headings import (
    TITLES_10K, TITLES_10Q, ItemHeading, furniture_detail, heading_text, is_toc_entry, item_headings, match_item,
    norm_title, page_number, part_markers, title_ok,
)

TARGETS = {"10-K": ("10K_1A", "10K_7"), "10-Q": ("10Q_P1_2", "10Q_P2_1A")}
_SPEC = {  # section -> (part or None, item, named title used for anchors / pointer following)
    "10K_1A": (None, "1a", "risk factors"),
    "10K_7": (None, "7", "management's discussion and analysis"),
    "10Q_P1_2": ("i", "2", "management's discussion and analysis"),
    "10Q_P2_1A": ("ii", "1a", "risk factors"),
}
STUB_MAX_CHARS = 1500
# A full 10-K Item 1A / Item 7 shorter than this is suspicious. Calibrated on the corpus: see docs/parse-report.md.
MIN_FULL_10K_CHARS = 5000
_POINTER = re.compile(
    r"reference is made to|incorporated (?:herein )?by reference|appears? on pages?|refer to|"
    r"see (?:the )?(?:section|discussion|information)|is (?:included|contained|set forth|presented) (?:in|under|on)|"
    r"no material changes|(?:discussed|described|set forth|disclosed) (?:in|under)|carefully consider",
    re.I,
)
_OTHER_FILING = re.compile(r"form 10-k|annual report|proxy statement|form 10-q for", re.I)
_EXHIBIT = re.compile(r"financial report|exhibit 13|annual report to (?:share|stock)holders", re.I)
_XREF_INDEX = re.compile(r"cross[\s-]*reference\s+index", re.I)
_QUOTED = re.compile(r"[“\"]([^”\"]{6,140})[”\"]")
_PAGES = re.compile(r"pages?\s+(\d{1,3})\s*[-–—]\s*(\d{1,3})", re.I)
_ROW_RANGE = re.compile(r"(?<![\d,])(\d{1,3})\s*[-–—]\s*(\d{1,3})(?!\d)")
_PAGE_NUM = re.compile(r"^\D{0,3}(\d{1,3})\D{0,3}$")


@dataclass
class ParseResult:
    section: str
    outcome: str = "failed"              # ok | partial | failed
    form_kind: str = "full"              # full | pointer | absent
    reasons: list[str] = field(default_factory=list)
    start_block: int | None = None       # heading (or title) block; excluded from text
    end_block: int | None = None         # exclusive
    text: str = ""
    evidence: dict = field(default_factory=dict)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    def downgrade(self, reason: str) -> None:
        self.reasons.append(reason)
        if self.outcome == "ok":
            self.outcome = "partial"


@dataclass
class _Doc:
    form: str
    blocks: list[Block]
    furn: set[int]
    running: set[int]
    headings: list[ItemHeading]          # title-valid, non-TOC, with part resolved
    parts: dict[int, str]                # heading block -> part
    part_starts: list[tuple[int, str]]   # live PART markers
    xref_index: int | None
    anchors: list[tuple[int, str, int]]  # (link block, link title text, target block)
    c1: int


def _row_title(blocks: list[Block], h: ItemHeading) -> str:
    m = match_item(heading_text(blocks[h.block]))
    return m[2] if m else ""


def _resolve_parts(form: str, blocks: list[Block], furn: set[int], heads: list[ItemHeading],
                   xref: int | None) -> tuple[list[ItemHeading], dict[int, str], list[tuple[int, str]]]:
    """Keep title-valid headings; give each a part. For 10-Qs the title disambiguates, then PART markers decide."""
    markers = sorted(part_markers(blocks, furn))
    heads = [h for h in heads if xref is None or h.block < xref]
    hb = [h.block for h in heads]
    # A PART marker only counts if a real item heading follows it before the next marker (drops TOC 'PART I' lines).
    live = [(b, p) for i, (b, p) in enumerate(markers)
            if any(b < x < (markers[i + 1][0] if i + 1 < len(markers) else 10**9) for x in hb)]
    out, parts = [], {}
    for h in heads:
        title = h.title or _row_title(blocks, h)
        if form == "10-K":
            if title_ok(h.item, title, TITLES_10K.get(h.item, ("",))):
                out.append(h)
                parts[h.block] = h.part or ""
            continue
        part = h.part
        if part is None and norm_title(title):
            fits = [p for p in ("i", "ii") if (p, h.item) in TITLES_10Q and title_ok(h.item, title, TITLES_10Q[(p, h.item)])]
            if len(fits) == 1:
                part = fits[0]
        if part is None:
            before = [p for b, p in live if b < h.block]
            part = before[-1] if before else None
        if part and (part, h.item) in TITLES_10Q and title_ok(h.item, title, TITLES_10Q[(part, h.item)]):
            out.append(h)
            parts[h.block] = part
    return out, parts, live


def _anchors(fl: Flattened) -> list[tuple[int, str, int]]:
    out = []
    blocks = fl.blocks
    for b in blocks:
        for target in b.links:
            t = fl.id_to_block.get(target)
            if t is None or t <= b.idx:      # backwards links point into front matter, not at sections
                continue
            text = heading_text(b)
            m = match_item(text)
            # TOC rows that say only "Item 2." carry their title in the next block (Pfizer).
            if m and not norm_title(m[2]) and b.idx + 1 < len(blocks):
                text = f"{text} {blocks[b.idx + 1].text}"
            out.append((b.idx, text, t))
    return out


def prepare(fl: Flattened, form: str) -> _Doc:
    blocks = fl.blocks
    furn, running = furniture_detail(blocks)
    xref = next((b.idx for b in blocks if len(b.text) <= 80 and _XREF_INDEX.search(b.text)
                 and not is_toc_entry(b, blocks)), None)
    heads, parts, live = _resolve_parts(form, blocks, furn, item_headings(blocks, furn, running), xref)
    return _Doc(form=form, blocks=blocks, furn=furn, running=running, headings=heads, parts=parts,
                part_starts=live, xref_index=xref, anchors=_anchors(fl), c1=fl.c1_remapped)


def _anchor_targets_for(doc: _Doc, part: str | None, item: str, title: str) -> list[int]:
    out = []
    for _, text, target in doc.anchors:
        if doc.xref_index is not None and target >= doc.xref_index:
            continue
        m = match_item(text)
        if m:
            _, mitem, mtitle = m
            if mitem != item:
                continue
            keys = TITLES_10Q.get((part or "", item), ()) if doc.form == "10-Q" else TITLES_10K.get(item, ())
            if not norm_title(mtitle) or not title_ok(item, mtitle, keys):
                continue
            out.append(target)
        else:
            nt = norm_title(re.sub(r"\s*[\d\s,\-–]*$", "", text))
            if nt.startswith(title) and len(nt) <= len(title) + 70:
                out.append(target)
    return sorted(set(out))


def _text_between(doc: _Doc, start: int, end: int, skip_rows: set[int]) -> tuple[str, int, list[tuple]]:
    """Canonical text of blocks in [start, end), minus furniture and the heading row (design §2.4).

    The block map records, for each block, (char start, char end, block index, table id, row id). M3 uses the
    table and row ids to segment the text into paragraph and table units.
    """
    parts: list[str] = []
    block_map: list[tuple] = []
    joins = 0
    pos = 0
    prev_open = False
    prev_cell = False
    para_len = 0          # length of the paragraph being built (since the last block break)
    crossed = False       # a page break or removed furniture lies between the previous block and this one
    for b in doc.blocks[start:end]:
        if b.idx in doc.furn or (b.row is not None and b.row in skip_rows):
            crossed = True
            continue
        crossed = crossed or b.page_break_before
        t = b.text
        if parts:
            # Re-join a sentence split by a page break (furniture removed between the halves). A lowercase
            # continuation always joins. A capitalised one ("...information on the" | "Firm's ...") joins only across
            # a page break, after a paragraph-length block, and when it doesn't read as a heading, list item or table
            # cell. Found by Trevor during M3 labeling: ~4.8% of paragraphs ended mid-sentence.
            cap_join = (crossed and para_len > 120 and not prev_cell and b.row is None
                        and not (len(t) <= 120 and not re.search(r"[.!?:;]\s*$", t))
                        and not re.match(r"^(?:[•●◦▪■\-–—*]|\(?[a-z0-9]{1,3}[.)]\s|item\s+\d)", t, re.I))
            if prev_open and (t[:1].islower() or cap_join):
                sep = " "
                joins += 1
            else:
                sep = "\n\n"
                para_len = 0
            parts.append(sep)
            pos += len(sep)
        block_map.append((pos, pos + len(t), b.idx, b.table, b.row))
        parts.append(t)
        pos += len(t)
        para_len += len(t)
        prev_open = not re.search(r"[.!?:;”\"’')\]]\s*$", t)
        prev_cell = b.row is not None
        crossed = False
    return "".join(parts), joins, block_map


def _bare_heading(doc: _Doc, h: int) -> bool:
    """'ITEM 1A' alone on its line, with the title ('RISK FACTORS') as the next block (Weyco pre-2020)."""
    m = match_item(heading_text(doc.blocks[h]))
    if not m or norm_title(m[2]) or h + 1 >= len(doc.blocks):
        return False
    nxt = doc.blocks[h + 1]
    keys = {**{k: v for k, v in TITLES_10K.items()}}.get(m[1], ())
    if doc.form == "10-Q":
        keys = sum((v for (p, i), v in TITLES_10Q.items() if i == m[1]), ())
    return nxt.row is None and len(nxt.text) <= 160 and title_ok(m[1], nxt.text, keys)


def _slice(doc: _Doc, res: ParseResult, start: int, end: int, keep_start: bool = False) -> None:
    head = doc.blocks[start]
    skip = {head.row} if head.row is not None and not keep_start else set()
    first = start if keep_start else start + 1
    if first < end and _bare_heading(doc, start):
        first += 1
        res.evidence["title_line"] = start + 1
    elif not keep_start:
        # A title-only first line ("RISK FACTORS" under GE 2018's anchor) is the heading, not content. Left in, it
        # makes the same filer's years differ by a phantom added paragraph.
        nxt = next((b for b in doc.blocks[first:end] if b.idx not in doc.furn), None)
        title = _SPEC[res.section][2]
        # Only a bare title: short, and not a sentence. A one-line pointer stub that *starts* with the title
        # ("Management's discussion and analysis ... appears on pages 46-48.") is content and must stay.
        if nxt is not None and len(nxt.text) <= len(title) + 60 and not re.search(r"[.;]\s+\S|\.$", nxt.text) \
                and norm_title(nxt.text).startswith(title[:20]):
            res.evidence["title_line"] = nxt.idx
            first = nxt.idx + 1
    text, joins, bmap = _text_between(doc, first, end, skip)
    res.start_block, res.end_block, res.text = start, end, text
    res.evidence.update(joins=joins, block_map=bmap, chars=len(text),
                        furniture_removed=sum(1 for i in range(start, end) if i in doc.furn))


def _next_boundary(doc: _Doc, after: int) -> int | None:
    nxt = [h.block for h in doc.headings if h.block > after]
    nxt += [b for b, _ in doc.part_starts if b > after]
    if doc.xref_index is not None and doc.xref_index > after:
        nxt.append(doc.xref_index)
    return min(nxt) if nxt else None


def _block_pages(doc: _Doc) -> dict[int, int]:
    """Page of every block, from page-number footers: a block belongs to the page whose footer follows it."""
    pages: dict[int, int] = {}
    pending: list[int] = []
    for b in doc.blocks:
        pending.append(b.idx)
        if b.idx in doc.furn:
            n = page_number(b.text, lenient=b.idx in doc.running)
            if n is not None:
                for i in pending:
                    pages[i] = n
                pending = []
    return pages


def _running_extent(doc: _Doc, after: int, title: str,
                    page_range: tuple[int, int] | None = None) -> tuple[int, int, int] | None:
    """Pages whose running header names `title`: (first header block, end block, header count).

    The section starts at the first such header and ends at the page break after the last one. Requires at least
    two pages, so a lone heading that happens to sit next to a page break isn't mistaken for a running header.
    """
    want = title[:40]
    if page_range is None:
        occ = [b.idx for b in doc.blocks[after:] if b.idx in doc.running and norm_title(b.text).startswith(want)]
    else:
        # The pointer names its pages (JPM): any short title line on those pages counts, running header or not. JPM
        # prints the title atop the first MD&A page, then segment headers for ~38 pages, then the title again on
        # alternate pages. Lines outside the stated pages are dropped (the title recurs elsewhere in 2019-20).
        pages = _block_pages(doc)
        occ = [b.idx for b in doc.blocks[after:]
               if len(b.text) <= 160 and not b.is_link and norm_title(b.text).startswith(want)
               and page_range[0] - 1 <= pages.get(b.idx, -1) <= page_range[1]]
    if len(occ) < 2:
        return None
    end = next((b.idx for b in doc.blocks[occ[-1] + 1:] if b.page_break_before), None)
    if end is None:
        end = _next_boundary(doc, occ[-1]) or len(doc.blocks)
    # Footers sit just before the break; the page's last content block is included, the next page's header is not.
    return occ[0], end, len(occ)


def _page_numbers(doc: _Doc, start: int, end: int) -> list[int]:
    return [n for b in doc.blocks[start:end]
            if b.idx in doc.furn and (n := page_number(b.text, lenient=b.idx in doc.running)) is not None]


def _verify_pages(doc: _Doc, res: ParseResult, stated: str, index_row: bool = False) -> None:
    """Compare the page numbers printed inside the slice with the range the filing itself states.

    Never silent: if a range is stated but can't be checked, that is recorded as its own reason.
    """
    m = (_ROW_RANGE if index_row else _PAGES).search(stated)
    if res.start_block is None:
        return
    if not m:
        if index_row:
            res.reasons.append("page_range_not_stated")
        return
    lo, hi = int(m.group(1)), int(m.group(2))
    nums = _page_numbers(doc, res.start_block, res.end_block or res.start_block)
    res.evidence["stated_pages"] = [lo, hi]
    res.evidence["observed_pages"] = [min(nums), max(nums)] if nums else []
    # Index ranges (GE) are page-granular: a section can end at the top of its last stated page, so that page's footer
    # falls in the next section. One page of tolerance there. A pointer that names its pages ("appears on pages
    # 46-160", JPM) is held exactly: the M3 diff caught a tolerated one-page shortfall that dropped JPM's last MD&A
    # page in five of eight years.
    tol = 1 if index_row else 0
    if nums and lo - 1 <= min(nums) <= lo + 1 and hi - tol <= max(nums) <= hi:
        res.reasons.append("page_range_verified")
    else:
        res.downgrade("page_range_mismatch")


def _follow_pointer(doc: _Doc, res: ParseResult, stub_text: str, title: str) -> None:
    """Archetype B: the item is a one-line pointer to a named section elsewhere in this document."""
    quoted = [norm_title(q) for q in _QUOTED.findall(stub_text)]
    want = next((q for q in quoted if q[:12] == title[:12]), title)
    stub_end = res.end_block or 0
    res.evidence["pointer_stub"] = stub_text
    res.evidence["pointer_target_title"] = want
    stated = _PAGES.search(stub_text)
    rng = (int(stated.group(1)), int(stated.group(2))) if stated else None
    ext = _running_extent(doc, stub_end, want, rng)
    if ext is None:
        res.outcome, res.text = "failed", stub_text
        res.reasons.append("pointer_target_not_found")
        return
    start, end, n = ext
    reasons = ["followed_pointer", "running_header_extent"]
    if rng:
        reasons.append("filtered_by_stated_pages")
        # The filer named the last page; the section runs to the end of it. Running headers alone stop short when
        # the last page carries none (JPM prints its MD&A header on alternate pages only).
        pages = _block_pages(doc)
        last = [b.idx for b in doc.blocks[start:] if b.idx in doc.furn and pages.get(b.idx) == rng[1]
                and page_number(b.text, lenient=b.idx in doc.running) == rng[1]]
        if last and last[-1] + 1 > end:
            end = last[-1] + 1
            reasons.append("end_at_stated_last_page")
    _slice(doc, res, start, end)
    res.evidence["running_headers"] = n
    res.reasons += reasons
    _verify_pages(doc, res, stub_text)


def _toc_entries(doc: _Doc) -> list[tuple[int, str, int, float]]:
    """(link block, title text, target, indent) for TOC links, skipping page-number links and repeat targets."""
    out = []
    for link, text, target in sorted(doc.anchors):
        if link in doc.furn or (out and out[-1][2] == target):
            continue
        out.append((link, text, target, doc.blocks[link].indent))
    return out


def _toc_page(text: str) -> int | None:
    m = re.search(r"(?<![\d-])(\d{1,3})\s*$", text)
    return int(m.group(1)) if m else None


def _toc_group_end(doc: _Doc, start: int, index_hi: int | None = None) -> tuple[int | None, str]:
    """End of a TOC-anchored section: the next anchor target after its own TOC group.

    The group is the section's own entry plus the entries nested under it, either indented deeper (GE) or, in an
    Item-style TOC, everything up to the next Item or Part entry (JPM's 10-Q lists MD&A subsections under Item 2).
    Ending after the group's *last* target, rather than at the next TOC line, matters when the document order
    differs from the TOC order (JPM's 10-Q prints MD&A before the financial statements).
    """
    entries = _toc_entries(doc)
    own = next((i for i, e in enumerate(entries) if e[2] == start), None)
    if own is None:
        return None, ""
    _, own_text, _, own_indent = entries[own]
    own_is_item = bool(match_item(own_text))
    group = [start]
    rule = "toc_group_end"
    nxt = entries[own + 1] if own + 1 < len(entries) else None
    # Flat = nothing in the next few entries is nested under this one (GE 2018-19 has no hierarchy around MD&A, though
    # one note deep in its financial statements happens to be indented).
    flat_toc = not any(e[3] > own_indent + 0.5 for e in entries[own + 1: own + 9])
    if flat_toc and not own_is_item and index_hi is not None:
        # A TOC with no hierarchy at all (GE 2018-19): the group is every entry that starts *before* the index's last
        # page. An entry starting on that page belongs to the next section (index ranges are page-granular).
        for _, text, target, _ in entries[own + 1:]:
            page = _toc_page(text)
            if page is None or page >= index_hi:
                break
            group.append(target)
        rule = "end_from_index_pages"
        last = max(group)
        after = [e[2] for e in entries if e[2] > last]
        return (min(after) if after else None), rule
    for _, text, target, indent in entries[own + 1:]:
        structural = bool(match_item(text)) or bool(re.match(r"^part\s+(iv|i{1,3})\b", text, re.I))
        if indent > own_indent + 0.5 or (own_is_item and not structural):
            group.append(target)
            continue
        break
    last = max(group)
    after = [e[2] for e in entries if e[2] > last]
    return (min(after) if after else None), rule


def _absent_part_ii_item(doc: _Doc, item: str) -> bool:
    """A 10-Q that skips Part II Item 1A: Part II is present, its other items are found, and none is this one."""
    p2 = [b for b, p in doc.part_starts if p == "ii"]
    if not p2:
        return False
    p2_items = [h for h in doc.headings if doc.parts.get(h.block) == "ii"]
    if len(p2_items) < 2 or any(h.item == item for h in p2_items):
        return False
    region = doc.blocks[p2[0]: (doc.xref_index or len(doc.blocks))]
    return not any(b.idx not in doc.furn and re.match(r"^(?:item\s*1a\W*)?risk\s+factors\b", b.text, re.I)
                   and len(b.text) <= 120 for b in region)


def _xref_row(doc: _Doc, part: str | None, item: str) -> str | None:
    """The cross-reference-index row for an item, if the document has an index (GE)."""
    if doc.xref_index is None:
        return None
    cur_part = None
    for b in doc.blocks[doc.xref_index:]:
        pm = re.match(r"^part\s+(iv|i{1,3})\b", b.text, re.I)
        if pm:
            cur_part = pm.group(1).lower()
        m = match_item(heading_text(b))
        if m and m[1] == item and (part is None or cur_part == part):
            return heading_text(b)
    return None


def locate(doc: _Doc, section: str) -> ParseResult:
    part, item, title = _SPEC[section]
    res = ParseResult(section=section)
    res.evidence["c1_remapped"] = doc.c1
    heads = [h for h in doc.headings if h.item == item and (doc.form == "10-K" or doc.parts.get(h.block) == part)]
    anchors = _anchor_targets_for(doc, part, item, title)
    res.evidence["heading_candidates"] = [h.block for h in heads]
    res.evidence["anchor_targets"] = anchors

    def agrees(h: int) -> bool:
        title_line = h + 1 if _bare_heading(doc, h) else h
        row = doc.blocks[h].row
        return any(a in (h, title_line) or (row is not None and doc.blocks[a].row == row) or (h - 4 <= a < h and all(i in doc.furn or i == a for i in range(a, h)))
                   for a in anchors)

    if heads:
        if len(heads) > 1:
            agreeing = [h for h in heads if agrees(h.block)]
            if len(agreeing) == 1:
                chosen = agreeing[0].block
            else:
                pool = agreeing or heads
                chosen = max(pool, key=lambda h: (_next_boundary(doc, h.block) or len(doc.blocks)) - h.block).block
                res.reasons.append("multiple_candidates")
        else:
            chosen = heads[0].block
        if not anchors:
            res.reasons.append("single_signal")
        elif not agrees(chosen):
            res.reasons.append("signal_conflict")
        res.outcome = "partial" if {"signal_conflict", "multiple_candidates"} & set(res.reasons) else "ok"
        end = _next_boundary(doc, chosen)
        if end is None:
            end = len(doc.blocks)
            res.downgrade("no_end_heading")
        _slice(doc, res, chosen, end)
    elif anchors:
        # No Item heading, only a named TOC anchor (GE's cross-reference layout; JPM's 10-Q MD&A).
        start = anchors[0]
        res.reasons += ["anchor_only", "single_signal"]
        if doc.xref_index is not None:
            res.reasons.append("xref_index")
        row = _xref_row(doc, part, item)
        rng = _ROW_RANGE.search(row) if row else None
        end, rule = _toc_group_end(doc, start, int(rng.group(2)) if rng else None)
        if end is not None:
            res.reasons.append(rule)
            res.outcome = "ok"
        else:
            end = _next_boundary(doc, start) or len(doc.blocks)
            res.reasons.append("end_fallback")
            res.outcome = "partial"
        # GE runs its headings into the first paragraph ("RISK FACTORS. The following discussion..."): keep it.
        run_in = len(doc.blocks[start].text) > 160
        if run_in:
            res.reasons.append("run_in_heading")
        _slice(doc, res, start, end, keep_start=run_in)
        if row:
            res.evidence["xref_row"] = row
            _verify_pages(doc, res, row, index_row=True)
    else:
        row = _xref_row(doc, part, item)
        if row and re.search(r"not applicable", row, re.I):
            res.outcome, res.form_kind = "ok", "absent"
            res.reasons.append("xref_not_applicable")
            res.evidence["xref_row"] = row
        elif doc.form == "10-Q" and part == "ii" and _absent_part_ii_item(doc, item):
            res.outcome, res.form_kind = "ok", "absent"
            res.reasons.append("item_omitted")
        else:
            res.reasons.append("no_heading")
        return res

    # Pointers: exhibit incorporation, archetype D (out to another filing), archetype B (elsewhere in this document).
    if len(res.text) <= STUB_MAX_CHARS and _POINTER.search(res.text):
        if doc.form == "10-K" and _EXHIBIT.search(res.text) and re.search(r"incorporated", res.text, re.I):
            res.outcome, res.form_kind = "failed", "pointer"
            res.reasons.append("exhibit_incorporation")
        elif _OTHER_FILING.search(res.text) and doc.form == "10-Q":
            res.form_kind = "pointer"
            res.reasons.append("pointer_out")
        elif doc.form == "10-K":
            _follow_pointer(doc, res, res.text, title)
    return res


def check(doc: _Doc, results: dict[str, ParseResult]) -> None:
    """Sanity gates (design §2.5)."""
    for r in results.values():
        if r.outcome == "failed" or r.form_kind != "full" or r.start_block is None:
            continue
        inner = [h for h in doc.headings if r.start_block < h.block < (r.end_block or 0)]
        if inner:
            r.evidence["inner_headings"] = [h.block for h in inner]
            r.downgrade("bleed_detected")
        if doc.form == "10-K" and len(r.text) < MIN_FULL_10K_CHARS:
            r.downgrade("too_short")
    if doc.form == "10-K":
        a, b = results.get("10K_1A"), results.get("10K_7")
        both = a and b and a.start_block is not None and b.start_block is not None
        if both and not ({"anchor_only", "followed_pointer"} & (set(a.reasons) | set(b.reasons))):
            if a.start_block > b.start_block:
                a.downgrade("order_violation")
                b.downgrade("order_violation")
        if both and a.start_block < b.start_block < (a.end_block or 0):
            a.downgrade("overlap")


def parse_filing(fl: Flattened, form: str) -> dict[str, ParseResult]:
    doc = prepare(fl, form)
    results = {s: locate(doc, s) for s in TARGETS[form]}
    check(doc, results)
    return results
