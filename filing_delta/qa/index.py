"""Units to search, and BM25 over them (M6, docs/design/qa.md §2.3).

`catalog` and `units_for` read data/ (the parsed sections and the M5 facts records, for fiscal year and quarter).
`bm25` is pure. Units are the M3 segmenter's paragraphs and data tables, each an exact [start, end) span of the
stored section text. A unit's nearest preceding heading is added to its *search* text only, never to what can be
cited.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from ..diff.segment import segment
from ..xbrl.claims import fiscal_year
from .scope import ALIASES, Filing

K1, B = 1.5, 0.75
TOP_K = 8
STOP = set("""a an and are as at be been but by can could did do does for from had has have how in into is it its
of on or our over say says said than that the their them they this to was were what when where which while who why
will with would about after any between both during each more most other some such these those through under up
company companys company's filing filings report reports annual quarterly 10 k q form item fiscal year years quarter
mention mentions mentioned describe describes discuss discusses discussed state states stated""".split())


@dataclass(frozen=True)
class Unit:
    accession: str
    section: str
    start: int
    end: int
    kind: str
    heading: str
    text: str


def stem(t: str) -> str:
    """A light, deterministic suffix strip so inflections meet: revenue/revenues -> revenu, increase/increased/
    increases/increasing -> increas, risk/risks -> risk. Words of four letters or fewer are left alone."""
    t = re.sub(r"['’]s$", "", t)
    if len(t) <= 4:
        return t
    for suf in ("ing", "ies", "ed", "es", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 3 and not (suf == "s" and t.endswith("ss")):
            t = t[: -len(suf)] + ("y" if suf == "ies" else "")
            break
    return t[:-1] if t.endswith("e") and len(t) > 4 else t


def tokens(s: str) -> list[str]:
    return [stem(t) for t in re.findall(r"[a-z0-9]+(?:['’][a-z]+)?", s.lower()) if t not in STOP and not t.isdigit()]


def query_tokens(q: str) -> list[str]:
    """The question's content words: company names, tickers, years and question words removed."""
    low = q
    for _, names, tickers in ALIASES.values():
        for n in names + tickers:
            low = re.sub(rf"(?i)(?<![\w-]){re.escape(n)}(?:['’]s)?(?![\w-])", " ", low)
    return tokens(low)


def catalog(root: Path) -> list[Filing]:
    rows = [json.loads(l) for l in (root / "data" / "sections" / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    have: dict[str, list[str]] = {}
    for r in rows:
        if r["form_kind"] == "full" and r["outcome"] != "failed":
            have.setdefault(r["accession"], []).append(r["section"])
    out = []
    for p in sorted((root / "data" / "facts").glob("*.json")):
        fr = json.loads(p.read_text(encoding="utf-8"))
        dei = fr.get("dei") or {}
        fy = fiscal_year(fr["period_end"], fr["form"], (dei.get("CurrentFiscalYearEndDate") or {}).get("text"))
        fp = "FY" if fr["form"] == "10-K" else ((dei.get("DocumentFiscalPeriodFocus") or {}).get("text") or "")
        out.append(Filing(fr["accession"], fr["cik"], fr["form"], fr["period_end"], fy, fp,
                          tuple(sorted(have.get(fr["accession"], [])))))
    return out


def units_for(root: Path, filings: list[Filing], sections: tuple[str, ...]) -> tuple[list[Unit], dict]:
    """Searchable units for the scoped filings, plus the section texts they point into (for the verifier)."""
    want = {(f.accession, s) for f in filings for s in sections if s in f.sections}
    rows = [json.loads(l) for l in (root / "data" / "sections" / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    units: list[Unit] = []
    texts: dict[tuple[str, str], str] = {}
    for r in rows:
        if (r["accession"], r["section"]) not in want:
            continue
        text = (root / "data" / "sections" / r["accession"] / f"{r['section']}.txt").read_text(encoding="utf-8")
        texts[(r["accession"], r["section"])] = text
        heading = ""
        for u in segment(text, r["block_map"]):
            if u.kind == "heading":
                heading = text[u.start:u.end]
                continue
            units.append(Unit(r["accession"], r["section"], u.start, u.end, u.kind, heading, text[u.start:u.end]))
    units.sort(key=lambda u: (u.accession, u.section, u.start))
    return units, texts


def changed_spans(root: Path, filings: list[Filing]) -> dict[tuple[str, str, int, int], str] | None:
    """For a "what changed between these two filings" question: span -> M3 diff status (added, removed, reworded,
    split, merged, moved) for every unit the diff marks as changed between them. None if the corpus has no diff for
    the pair (the years aren't consecutive, say), in which case retrieval falls back to both filings in full."""
    accs = {f.accession for f in filings}
    if len(accs) != 2:
        return None
    spans: dict[tuple[str, str, int, int], str] = {}
    found = False
    for p in (root / "data" / "diffs").glob("*.json"):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if {rec["old"]["accession"], rec["new"]["accession"]} != accs or rec["state"] != "full -> full":
            continue
        found = True
        for op in rec["ops"]:
            if op["status"] == "unchanged" or (op["status"] == "moved" and not op.get("facts", {}).get("edited")):
                continue
            for i in op["old"]:
                spans[(rec["old"]["accession"], rec["section"], *rec["old_units"][i][1:3])] = op["status"]
            for j in op["new"]:
                spans[(rec["new"]["accession"], rec["section"], *rec["new_units"][j][1:3])] = op["status"]
    return spans if found else None


ADD_INTENT = re.compile(r"\b(?:add|added|adds|new|newly|introduc\w*|begin|began|start\w*)\b", re.I)
REMOVE_INTENT = re.compile(r"\b(?:remove|removed|drop|dropped|delete|deleted|no\s+longer|stop\w*|omit\w*)\b", re.I)
CHANGE_WORDS = {stem(w) for w in "add added adds new newly remove removed drop dropped change changed changes differ "
                                 "different longer delete deleted introduce introduced ks".split()}


def rank_changes(question: str, units: list[Unit], spans: dict, k: int = TOP_K) -> list[tuple[float, Unit]]:
    """A change question ranks the diff's changed units: added ones first for "what was added", removed ones first
    for "what was dropped". Within that, BM25 on the question's topic words (change words removed), then position."""
    want = {"added"} if ADD_INTENT.search(question) and not REMOVE_INTENT.search(question) else \
        {"removed"} if REMOVE_INTENT.search(question) and not ADD_INTENT.search(question) else None
    changed = [u for u in units if (u.accession, u.section, u.start, u.end) in spans]
    topic = [t for t in query_tokens(question) if t not in CHANGE_WORDS]
    scores = {id(u): s for s, u in bm25(topic, changed, k=len(changed))} if topic else {}
    first = lambda u: 0 if want is None or spans[(u.accession, u.section, u.start, u.end)] in want else 1  # noqa: E731
    order = sorted(changed, key=lambda u: (first(u), -scores.get(id(u), 0.0), u.accession, u.section, u.start))
    return [(scores.get(id(u), 0.0), u) for u in order[:k]]


def bm25(query: list[str], units: list[Unit], k: int = TOP_K) -> list[tuple[float, Unit]]:
    """Top-k units by BM25 over heading + unit text. Ties break on (accession, section, start): deterministic."""
    if not units or not query:
        return []
    docs = [Counter(tokens(u.heading + " " + u.text)) for u in units]
    n = len(docs)
    avg = sum(sum(d.values()) for d in docs) / n
    df = Counter(t for d in docs for t in d)
    scored = []
    for u, d in zip(units, docs):
        dl = sum(d.values())
        s = 0.0
        for t in set(query):
            if t in d:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * d[t] * (K1 + 1) / (d[t] + K1 * (1 - B + B * dl / avg))
        if s > 0:
            scored.append((round(s, 9), u))
    scored.sort(key=lambda x: (-x[0], x[1].accession, x[1].section, x[1].start))
    return scored[:k]
