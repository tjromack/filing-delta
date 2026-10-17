"""Numeric facts from an inline XBRL document (M5, FD-DEC 025). Pure: bytes in, facts out; no I/O, no clock.

Every `ix:nonFraction` becomes a Fact: concept, value (after `format`, `scale` and `sign`), unit, decimals, period,
dimensions. A value the transforms can't read is reported in `issues` with its concept and context, never dropped
silently. Duplicates (the same fact repeated in a statement and a note) collapse into one; the same key with two
different values is reported as a conflict.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from lxml import etree

from .facts import Fact, dec_str

IX = ("http://www.xbrl.org/2013/inlineXBRL", "http://www.xbrl.org/2008/inlineXBRL")
XBRLI = "http://www.xbrl.org/2003/instance"
XBRLDI = "http://xbrl.org/2006/xbrldi"
ZERO_FORMATS = {"fixed-zero", "zerodash", "nocontent", "fixedzero"}
NUMBER_FORMATS = {"num-dot-decimal", "numdotdecimal", "numcommadot", "num-comma-decimal", "numcommadecimal"}
DEI_KEYS = ("DocumentType", "DocumentPeriodEndDate", "DocumentFiscalPeriodFocus", "DocumentFiscalYearFocus",
            "AmendmentFlag", "CurrentFiscalYearEndDate")

_SMALL = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen".split())}
_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if i > 1}


def words_to_number(text: str) -> int | None:
    """ixt-sec:numwordsen: 'no', 'none', 'two', 'twenty-five', 'one hundred'. None if not a number in words."""
    t = text.strip().lower()
    if t in ("no", "none", "not", "zero", "nil"):
        return 0
    total = cur = 0
    seen = False
    for w in re.split(r"[\s-]+", t.replace(" and ", " ")):
        if w in _SMALL:
            cur += _SMALL[w]
        elif w in _TENS:
            cur += _TENS[w]
        elif w == "hundred" and seen:
            cur *= 100
        elif w in ("thousand", "million", "billion") and seen:
            total += cur * {"thousand": 10**3, "million": 10**6, "billion": 10**9}[w]
            cur = 0
        else:
            return None
        seen = True
    return total + cur if seen else None


def parse_value(text: str, fmt: str | None) -> Decimal | None:
    """The displayed text -> an unscaled, unsigned number under its ixt transform. None if unreadable."""
    local = (fmt or "").split(":")[-1].lower()
    t = text.strip()
    if local in ZERO_FORMATS:
        return Decimal(0)
    if local == "numwordsen":
        n = words_to_number(t)
        return Decimal(n) if n is not None else None
    if local in ("num-comma-decimal", "numcommadecimal"):
        t = t.replace(".", "").replace(" ", "").replace(",", ".")
    elif local in NUMBER_FORMATS or not local:
        t = t.replace(",", "").replace(" ", "")
    else:
        return None
    if not re.fullmatch(r"\d+(\.\d+)?|\.\d+", t):
        return None
    try:
        return Decimal(t)
    except InvalidOperation:
        return None


def _taxonomy(ns: str | None, prefix: str) -> str:
    if ns:
        m = re.search(r"fasb\.org/(us-gaap|srt)/|xbrl\.sec\.gov/(dei|ecd|ffd|invest|cyd|country|currency)/", ns)
        if m:
            return m.group(1) or m.group(2)
    return prefix


def _qname(el, qname: str) -> str:
    prefix, _, local = qname.rpartition(":")
    return f"{_taxonomy(el.nsmap.get(prefix or None), prefix)}:{local}"


def _measure(el) -> str:
    """xbrli:unit -> 'USD', 'shares', 'USD/shares', 'pure' (local names, as the company-facts API spells them)."""
    loc = lambda m: (m.text or "").strip().split(":")[-1]  # noqa: E731
    div = el.find(f"{{{XBRLI}}}divide")
    if div is not None:
        num = [loc(m) for m in div.iterfind(f"{{{XBRLI}}}unitNumerator/{{{XBRLI}}}measure")]
        den = [loc(m) for m in div.iterfind(f"{{{XBRLI}}}unitDenominator/{{{XBRLI}}}measure")]
        return "*".join(num) + "/" + "*".join(den)
    return "*".join(loc(m) for m in el.iterfind(f"{{{XBRLI}}}measure"))


def precision(f: Fact) -> float:
    """The `decimals` attribute as a number: INF (exact) is the most precise; missing is treated as exact."""
    d = f.decimals
    return float("inf") if d in (None, "INF") else int(d)


def consistent(a: Fact, b: Fact) -> bool:
    """XBRL duplicates are consistent when equal after rounding to the coarser one's decimals (4,861,000,000 and
    4,900,000,000 at decimals -8 both round to 4.9E+9)."""
    if a.value == b.value:
        return True
    if a.value is None or b.value is None:
        return False
    d = min(precision(a), precision(b))
    if d == float("inf"):
        return False
    q = Decimal(1).scaleb(-int(d))
    return Decimal(a.value).quantize(q, ROUND_HALF_UP) == Decimal(b.value).quantize(q, ROUND_HALF_UP)


@dataclass
class InlineFacts:
    facts: list[Fact]
    dei: dict[str, dict]                    # key -> {"text", "end"}: the cover-page values and their context end
    issues: list[dict] = field(default_factory=list)
    duplicates: int = 0


def extract(body: bytes, accession: str) -> InlineFacts:
    root = etree.fromstring(body, etree.XMLParser(huge_tree=True, recover=True, resolve_entities=False))
    contexts: dict[str, tuple] = {}
    for cx in root.iter(f"{{{XBRLI}}}context"):
        per = cx.find(f"{{{XBRLI}}}period")
        inst = per.findtext(f"{{{XBRLI}}}instant")
        period = (None, inst.strip()) if inst else (per.findtext(f"{{{XBRLI}}}startDate").strip(),
                                                   per.findtext(f"{{{XBRLI}}}endDate").strip())
        dims = [(_qname(m, m.get("dimension")), _qname(m, (m.text or "").strip()))
                for m in cx.iter(f"{{{XBRLDI}}}explicitMember")]
        dims += [(_qname(m, m.get("dimension")), "".join(m.itertext()).strip())
                 for m in cx.iter(f"{{{XBRLDI}}}typedMember")]
        contexts[cx.get("id")] = (period, tuple(sorted(dims)))
    units = {u.get("id"): _measure(u) for u in root.iter(f"{{{XBRLI}}}unit")}

    dei: dict[str, dict] = {}
    for ns in IX:
        for el in root.iter(f"{{{ns}}}nonNumeric"):
            name = _qname(el, el.get("name", ""))
            if name.startswith("dei:") and name[4:] in DEI_KEYS and name[4:] not in dei:
                ctx = contexts.get(el.get("contextRef"))
                dei[name[4:]] = {"text": " ".join("".join(el.itertext()).split()),
                                 "end": ctx[0][1] if ctx else None}

    out: dict[tuple, Fact] = {}
    issues: list[dict] = []
    dup = 0
    for ns in IX:
        for el in root.iter(f"{{{ns}}}nonFraction"):
            concept = _qname(el, el.get("name", ""))
            ctx = contexts.get(el.get("contextRef"))
            unit = units.get(el.get("unitRef"))
            text = "".join(el.itertext())
            if ctx is None or unit is None:
                issues.append({"concept": concept, "context": el.get("contextRef"), "text": text.strip()[:40],
                               "problem": "missing context" if ctx is None else "missing unit"})
                continue
            nil = el.get("{http://www.w3.org/2001/XMLSchema-instance}nil") in ("true", "1")
            if nil:
                value = None
            else:
                raw = parse_value(text, el.get("format"))
                if raw is None:
                    issues.append({"concept": concept, "context": el.get("contextRef"), "text": text.strip()[:40],
                                   "problem": f"unreadable under format {el.get('format')}"})
                    continue
                value = raw.scaleb(int(el.get("scale") or 0))
                if el.get("sign") == "-":
                    value = -value
            (start, end), dims = ctx
            f = Fact(concept=concept, value=None if value is None else dec_str(value),
                     unit=unit, start=start, end=end, dims=dims, decimals=el.get("decimals"),
                     accession=accession, source="inline")
            key = f.key()
            if key in out:
                if consistent(out[key], f):
                    dup += 1
                    if precision(f) > precision(out[key]):   # "$4.9 billion" in prose, 4,861 in the table: keep 4,861
                        out[key] = f
                else:
                    issues.append({"concept": concept, "context": el.get("contextRef"), "text": text.strip()[:40],
                                   "problem": f"conflicting duplicate: {out[key].value} vs {f.value}"})
                continue
            out[key] = f
    return InlineFacts(facts=sorted(out.values(), key=Fact.sort_key), dei=dei, issues=issues, duplicates=dup)
