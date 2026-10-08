"""Flatten filing HTML into an ordered stream of text blocks (design §2.1 steps 1–2).

A *block* is a maximal run of inline text between block-level boundaries. Text is never dropped: text sitting
directly inside a block that also has block children becomes its own block. That avoids the classic leaf-only
extractor bug, where a `<div>` holding both text and a child `<div>` silently loses the text. Pure: bytes in,
blocks out.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from lxml import etree, html

BLOCK_TAGS = frozenset({
    "p", "div", "td", "th", "li", "tr", "table", "tbody", "thead", "h1", "h2", "h3", "h4", "h5", "h6",
    "center", "blockquote", "ul", "ol", "dl", "dt", "dd", "body", "html", "section", "article", "pre", "hr",
    "caption",
})
SKIP_TAGS = frozenset({"script", "style", "head", "title", "meta", "link"})
_WS = re.compile(r"[\s  -​  　﻿]+")
_PAGE_BREAK = re.compile(r"page-break-(before|after)\s*:\s*always|break-(before|after)\s*:\s*page", re.I)
_BOLD = re.compile(r"font-weight\s*:\s*(bold|[6-9]00)", re.I)
_HIDDEN = re.compile(r"display\s*:\s*none", re.I)
_INDENT = re.compile(r"(?:padding-left|margin-left|text-indent)\s*:\s*(-?[\d.]+)", re.I)

# HTML5 maps numeric references in the C1 range through Windows-1252; lxml decodes them literally.
_C1 = {i: bytes([i]).decode("cp1252", errors="replace") for i in range(0x80, 0xA0)}
_C1_RE = re.compile("[\u0080-\u009f]")


def remap_c1(text: str) -> tuple[str, int]:
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        ch = _C1[ord(m.group())]
        return " " if ch == "�" else ch

    return _C1_RE.sub(sub, text), n


@dataclass
class Block:
    idx: int
    text: str
    in_table: bool = False
    row: int | None = None          # sequence number of the enclosing <tr>, if any
    cell: int = 0                   # position of the cell within its row
    bold: bool = False
    is_link: bool = False           # all of the text is inside <a href>
    ids: tuple[str, ...] = ()       # id/name anchors that resolve to this block
    page_break_before: bool = False
    row_text: str = ""              # all cells of the row, joined (filled in after flattening)
    path: str = ""                  # source element path, for the read view
    links: tuple[str, ...] = field(default=())  # internal #targets linked from this block
    indent: float = 0.0             # summed left padding/margin/indent of enclosing elements (TOC hierarchy)


@dataclass
class Flattened:
    blocks: list[Block]
    c1_remapped: int
    id_to_block: dict[str, int]


def decode(raw: bytes) -> str:
    """Declared charset if any, else strict UTF-8, else Windows-1252. Never Latin-1 (design §2.1)."""
    m = re.search(rb"""charset\s*=\s*["']?([A-Za-z0-9_\-]+)""", raw[:4096], re.I)
    if m:
        try:
            return raw.decode(m.group(1).decode("ascii"))
        except (LookupError, UnicodeDecodeError):
            pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def parse_html(raw: bytes) -> etree._Element:
    text = decode(raw)
    # XML declarations are rejected by lxml when given str input.
    text = re.sub(r"^\s*<\?xml[^>]*\?>", "", text)
    return html.document_fromstring(text, parser=html.HTMLParser(huge_tree=True, remove_comments=True))


def _local(tag: object) -> str:
    return tag.split("}")[-1].split(":")[-1].lower() if isinstance(tag, str) else ""


class _Walker:
    def __init__(self) -> None:
        self.blocks: list[Block] = []
        self.buf: list[tuple[str, bool, bool]] = []  # (text, bold, in_link)
        self.pending_ids: list[str] = []
        self.pending_links: list[str] = []
        self.pending_break = False
        self.block_stack: list[etree._Element] = []
        self.table_depth = 0
        self.row_stack: list[int] = []
        self.cell_counter: list[int] = []
        self.cell_stack: list[int] = []
        self.c1 = 0
        self.row_seq = 0
        self.indent_stack: list[float] = []

    def add_text(self, text: str | None, bold: bool, in_link: bool) -> None:
        if text:
            self.buf.append((text, bold, in_link))

    def flush(self) -> None:
        if not self.buf:
            return
        raw = "".join(t for t, _, _ in self.buf)
        text = _WS.sub(" ", raw).strip()
        if text:
            text, n = remap_c1(text)
            self.c1 += n
            text = _WS.sub(" ", text).strip()
        if text:
            visible = [(t, b, a) for t, b, a in self.buf if t.strip()]
            el = self.block_stack[-1] if self.block_stack else None
            self.blocks.append(Block(
                idx=len(self.blocks), text=text, in_table=self.table_depth > 0,
                row=self.row_stack[-1] if self.row_stack else None,
                cell=self.cell_stack[-1] if self.cell_stack else 0,
                bold=all(b for _, b, _ in visible), is_link=all(a for _, _, a in visible),
                ids=tuple(self.pending_ids), page_break_before=self.pending_break,
                path=el.getroottree().getpath(el) if el is not None else "",
                links=tuple(self.pending_links), indent=sum(self.indent_stack),
            ))
            self.pending_ids, self.pending_links, self.pending_break = [], [], False
        self.buf = []

    def walk(self, el: etree._Element, bold: bool, in_link: bool) -> None:
        tag = _local(el.tag)
        if not tag or tag in SKIP_TAGS:
            return
        style = el.get("style") or ""
        # ix:header holds hidden XBRL metadata; anything display:none is not part of the reader's document.
        if _HIDDEN.search(style) or str(el.tag).lower().startswith("ix:header"):
            return
        is_block = tag in BLOCK_TAGS
        ind = sum(max(0.0, float(v)) for v in _INDENT.findall(style) if v.replace(".", "", 1).lstrip("-").isdigit())
        if ind and is_block:
            self.flush()
        self.indent_stack.append(ind)
        if _PAGE_BREAK.search(style) or tag == "hr":
            self.flush()
            self.pending_break = True
        for key in (el.get("id"), el.get("name") if tag == "a" else None):
            if key:
                self.pending_ids.append(key)
        b = bold or tag in ("b", "strong") or bool(_BOLD.search(style))
        href = el.get("href") or ""
        a = in_link or (tag == "a" and bool(href))
        if tag == "a" and href.startswith("#"):
            self.pending_links.append(href[1:])
        if is_block:
            self.flush()
            self.block_stack.append(el)
        if tag == "table":
            self.table_depth += 1
        if tag == "tr":
            # A counter, not id(el): lxml reuses ids of garbage-collected element proxies, which merged
            # unrelated rows (found on GE and Exxon during M2).
            self.row_seq += 1
            self.row_stack.append(self.row_seq)
            self.cell_counter.append(0)
        if tag in ("td", "th"):
            if self.cell_counter:
                self.cell_counter[-1] += 1
            self.cell_stack.append(self.cell_counter[-1] if self.cell_counter else 0)
        if tag == "br":
            self.add_text(" ", b, a)
        self.add_text(el.text, b, a)
        for child in el:
            self.walk(child, b, a)
            # A child's tail is inline text belonging to *this* element's context.
            self.add_text(child.tail, b, in_link)
        if tag in ("td", "th") and self.cell_stack:
            self.flush()
            self.cell_stack.pop()
        if tag == "tr":
            self.flush()
            self.row_stack.pop()
            self.cell_counter.pop()
        if tag == "table":
            self.flush()
            self.table_depth -= 1
        if is_block:
            self.flush()
            self.block_stack.pop()
        if ind and is_block:
            self.flush()
        self.indent_stack.pop()
        if _PAGE_BREAK.search(style) and "after" in style.lower():
            self.pending_break = True


def flatten(raw: bytes) -> Flattened:
    root = parse_html(raw)
    w = _Walker()
    import sys
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old, 20000))
    try:
        w.walk(root, False, False)
        w.flush()
    finally:
        sys.setrecursionlimit(old)
    blocks = w.blocks
    # Row text: every cell of a table row, joined, so split-cell headings ("Item 1A." | "Risk Factors") match.
    rows: dict[int, list[Block]] = {}
    for blk in blocks:
        if blk.row is not None:
            rows.setdefault(blk.row, []).append(blk)
    for blk in blocks:
        blk.row_text = " ".join(x.text for x in rows[blk.row]) if blk.row is not None else blk.text
    id_to_block: dict[str, int] = {}
    for blk in blocks:
        for k in blk.ids:
            id_to_block.setdefault(k, blk.idx)
    return Flattened(blocks=blocks, c1_remapped=w.c1, id_to_block=id_to_block)
