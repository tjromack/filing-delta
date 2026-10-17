"""Consolidated headline claims in MD&A vs. the filing's own tagged values (M5, FD-DEC 025 option B). Pure; no model.

A claim is a clause stating a level ("net income was $X") for one of five headline metrics. Each claim ends in
exactly one outcome:

- `matches`: the stated amount equals a consolidated, current-period tagged value of that metric at the stated
  precision ("$6.9 billion" means 6.85 to 6.95 billion).
- `no matching tagged value`: it is checkable, and no such value is within that precision. This is never worded
  "differs" or "incorrect": the claim may use a definition the tag doesn't.
- `non-GAAP wording`: adjusted, organic, excluding, constant currency and the like appear before the amount.
- `not checked`, with a reason: a segment or other subject, another period, or no tagged concept for the metric.

Every claim keeps its exact [start, end) span in the section text.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from decimal import Decimal

from .facts import Fact
from .periods import HEADLINE, duration_class

PHRASES = {
    "revenue": r"(?:total\s+)?(?:net\s+)?(?:operating\s+)?(?:revenues?|sales)",
    "net_income": r"net\s+(?:income|earnings|loss)(?:\s+including\s+noncontrolling\s+interests?)?"
                  r"(?:\s+attributable\s+to\s+[A-Z][\w.&'’ ,-]{1,60}?(?=\s+(?:was|were|of|totaled|amounted)))?",
    "operating_income": r"operating\s+(?:income|profit|loss)",
    "operating_cash_flow": r"(?:net\s+)?cash\s+(?:provided\s+by|from|flows?\s+from|generated\s+(?:by|from))\s+"
                           r"operating\s+activities|operating\s+cash\s+flows?|cash\s+flows?\s+from\s+operations",
    "eps_diluted": r"diluted\s+(?:net\s+)?(?:earnings|income|loss)\s+per\s+(?:common\s+)?share|diluted\s+EPS|"
                   r"earnings\s+per\s+diluted\s+share",
}
VERB = (r"(?:was|were|of|totaled|totalled|amounted\s+to|reached|"
        r"(?:increased|decreased|grew|declined|rose|fell)(?:\s+\d{1,3}(?:\.\d)?\s?%)?\s+to)")
AMOUNT = r"(?P<dollar>\$)\s?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?:\s+(?P<scale>thousand|million|billion))?"
# phrase, then at most a short qualifier, then the verb, then the amount
CLAIM = {m: re.compile(rf"\b(?P<phrase>{p})\b(?P<gap>[^.$;]{{0,30}}?)\s*\b{VERB}\s+(?:approximately\s+|about\s+)?"
                       rf"{AMOUNT}", re.I)
         for m, p in PHRASES.items()}
SCALE = {"thousand": 10**3, "million": 10**6, "billion": 10**9}
NONGAAP = re.compile(r"\b(?:adjusted|organic|excluding|exclusive\s+of|non-?gaap|comparable|core|underlying|"
                     r"managed\s+basis|constant[\s-]currency|pro\s+forma|fully\s+taxable[\s-]equivalent|"
                     r"currency[\s-]neutral)\b", re.I)
# Words allowed directly before the phrase for it to be a consolidated subject. Anything else ("Banking revenue",
# "Marmon's revenues", "segment net sales") is a possible segment or other subject: not checked.
CONSOLIDATED = {"total", "consolidated", "our", "the", "its", "company's", "company’s", "worldwide", "overall",
                "reported", "gaap", "and", "fiscal", "full-year", "annual", "quarterly", "year", "quarter",
                "first-quarter", "second-quarter", "third-quarter", "fourth-quarter", "first", "second", "third",
                "fourth", "full", "in", "during", "for", "a", "an", "record", "were", "was", "is", "are"}
# "had revenues of", "generated net income of": consolidated only when the doer is the company itself.
SUBJECT_VERBS = {"had", "has", "have", "generated", "recorded", "reported", "delivered", "achieved", "posted"}
COMPANY_SUBJECT = {"we", "company", "corporation", "firm", "it"}
GAP_STOP = re.compile(r"\b(?:segment|group|division|business|unit|operations|region|international|from|of\s+the|"
                      r"expense|expenses|cost|costs|tax|taxes|margin|growth|per|volume|mix|price|ratio)\b", re.I)
CHANGE_BEFORE = re.compile(r"\b(?:increase|decrease|growth|decline|change|impact|higher|lower|reduction|"
                           r"benefit|offset|drop|rise)s?\s+(?:in|on|to|of)\s*(?:our\s+|the\s+)?$", re.I)
NEAR = Decimal("0.25")
NAMED_GAP = re.compile(r"\bof\s+(?:the\s+)?[A-Z]|\b[A-Z][a-z]+\b")   # "net sales of Florsheim Australia were"
QUARTER_WORD = {"Q1": "first", "Q2": "second", "Q3": "third", "Q4": "fourth"}
YEAR = re.compile(r"\b(?:fiscal\s+(?:year\s+)?)?((?:19|20)\d\d)\b", re.I)
YTD = re.compile(r"\b(?:six|nine)\s+months|first\s+half|year[\s-]to[\s-]date|first\s+(?:six|nine)\s+months\b", re.I)
QTR = re.compile(r"\b(first|second|third|fourth)[\s-]quarter|\bthree\s+months|\bquarter(?:ly)?\b", re.I)


@dataclass(frozen=True)
class Claim:
    start: int
    end: int
    text: str
    metric: str
    amount_text: str
    value: str                    # the stated value as a decimal string, signed (a "net loss" is negative)
    tolerance: str                # half a unit of the stated precision
    period_basis: str             # "explicit" | "implicit"
    outcome: str                  # matches | no matching tagged value | non-GAAP wording | not checked
    reason: str
    matched: str | None = None    # concept and period of the matching fact
    tagged: tuple = ()            # the candidate tagged values (concept, period class, value)

    def to_json(self) -> dict:
        d = asdict(self)
        d["tagged"] = [list(t) for t in self.tagged]
        return d


def sentences(text: str):
    """(start, end) spans of sentences: split on . ! ? followed by space + capital/quote, and on paragraph breaks."""
    pos = 0
    for m in re.finditer(r"(?<=[.!?])\s+(?=[A-Z“\"(])|\n\n+", text):
        yield pos, m.start()
        pos = m.end()
    yield pos, len(text)


def _stated(num: str, scale: str | None) -> tuple[Decimal, Decimal]:
    n = Decimal(num.replace(",", ""))
    sc = SCALE.get((scale or "").lower(), 1)
    dec = len(num.split(".")[1]) if "." in num else 0
    return n * sc, Decimal(sc) / (Decimal(10) ** dec) / 2


def heading_before(text: str, pos: int, reach: int = 600) -> str:
    """The nearest short, unpunctuated paragraph before pos ("Year-to-date results", "Quarterly results")."""
    for para in reversed(re.split(r"\n\n+", text[max(0, pos - reach):pos])[:-1]):
        p = para.strip()
        if p and len(p) <= 60 and not p.endswith((".", ":", ";")):
            return p
    return ""


MONTHS = {m: i for i, m in enumerate("january february march april may june july august september october "
                                     "november december".split(), 1)}


def month_day(text: str | None) -> tuple[int, int] | None:
    """The cover's fiscal-year-end as displayed: '--12-31', '12/31', '1/31', 'December 31', 'January 31'."""
    t = (text or "").strip().lower()
    m = re.fullmatch(r"--(\d\d)-(\d\d)", t) or re.fullmatch(r"(\d{1,2})/(\d{1,2})", t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.fullmatch(r"([a-z]+)\s+(\d{1,2})", t)
    if m and m.group(1) in MONTHS:
        return MONTHS[m.group(1)], int(m.group(2))
    return None


def fiscal_year(period_end: str, form: str, fye: str | None) -> str:
    """The fiscal year a period belongs to, by the year the fiscal year ends in. A 10-K's period end is the fiscal
    year end. A 10-Q falls in the fiscal year ending next on the fiscal-year-end month-day (`dei:CurrentFiscalYearEndDate`,
    "--01-31"), with a week of slack for 52/53-week years: Walmart's quarter ended 2025-04-30 is fiscal 2026. The
    cover's own `DocumentFiscalYearFocus` isn't used: Weyco's FY2021 10-K tags it 2020."""
    y, md = int(period_end[:4]), period_end[5:]
    parsed = month_day(fye)
    if form == "10-K" or parsed is None:
        return str(y)
    m, d = parsed
    pm, pd = int(md[:2]), int(md[3:])
    return str(y if (pm, pd) <= (m, min(d + 7, 31)) else y + 1)


def _period(sent: str, a_start: int, a_end: int, current_years: set[str], form: str,
            fp: str | None, heading: str = "") -> tuple[str, str, str]:
    """('current'|'other', 'explicit'|'implicit', span): for a 10-Q, span is 'quarter', 'ytd' or 'either'.
    Year and quarter cues come from the sentence; the nearest heading can also set quarter vs. year-to-date."""
    after = sent[a_end:a_end + 45]
    before = sent[:a_start]
    years_after = [m for m in YEAR.finditer(after)]
    years_before = [m for m in YEAR.finditer(before)]
    year = (years_after[0] if years_after else (years_before[-1] if years_before else None))
    if year is None:
        year = YEAR.search(heading)          # a section headed "2023" or "2019 compared with 2018"
    span = "either"
    window = before[-80:] + after + " | " + heading
    if form == "10-Q":
        if YTD.search(window):
            span = "ytd"
        elif QTR.search(window):
            q = QTR.search(window).group(1)
            if q and fp in QUARTER_WORD and q.lower() != QUARTER_WORD[fp]:
                return "other", "explicit", span
            span = "quarter"
    if year is None:
        return "current", "implicit", span
    return ("current" if year.group(1) in current_years else "other"), "explicit", span


def _is_year(w: str) -> bool:
    return bool(re.fullmatch(r"(?:19|20)\d\d", w))


def find_claims(text: str, facts: list[Fact], period_end: str, form: str, fy: str,
                fp: str | None = None) -> list[Claim]:
    """fy: the fiscal year (fiscal_year()). A year in the text counts as current if it is the fiscal year or, in a
    10-Q, the calendar year of the period end ("three months ended April 30, 2025" in Walmart's fiscal 2026)."""
    current_years = {fy} | ({period_end[:4]} if form == "10-Q" else set())
    want = ("annual",) if form == "10-K" else ("quarter", "half", "nine_months")
    current = [f for f in facts if not f.dims and f.value is not None and f.end == period_end
               and duration_class(f.start, f.end) in want]
    out: list[Claim] = []
    seen: set[int] = set()
    for s0, s1 in sentences(text):
        sent = text[s0:s1]
        for metric, rx in CLAIM.items():
            for m in rx.finditer(sent):
                a = s0 + m.start("phrase")
                if a in seen:
                    continue
                seen.add(a)
                phrase = m.group("phrase")
                value, tol = _stated(m.group("num"), m.group("scale"))
                if "loss" in phrase.lower():
                    value = -value
                before = sent[:m.start("phrase")]
                if CHANGE_BEFORE.search(before):
                    continue                           # "an increase in revenue of $X" states a change, not a level
                if GAP_STOP.search(m.group("gap")):
                    continue                           # "sales and marketing expense was", "revenue growth of"
                clause = re.split(r"[;:]|,\s", before)[-1]
                prev = re.findall(r"[\w’'&.-]+", clause)
                prev_word = prev[-1].lower() if prev else ""
                base = dict(start=s0 + m.start(), end=s0 + m.end(), text=sent[m.start():m.end()], metric=metric,
                            amount_text=sent[m.start("dollar"):m.end()], value=str(value), tolerance=str(tol))
                if NONGAAP.search(clause + " " + phrase + m.group("gap")):
                    out.append(Claim(**base, period_basis="-", outcome="non-GAAP wording", reason="non-GAAP term"))
                    continue
                if prev_word in SUBJECT_VERBS and len(prev) > 1 and prev[-2].lower() in COMPANY_SUBJECT:
                    prev_word = ""
                if prev_word and prev_word not in CONSOLIDATED and not _is_year(prev_word):
                    out.append(Claim(**base, period_basis="-", outcome="not checked",
                                     reason=f"segment or other subject ('{prev[-1]} {phrase}')"))
                    continue
                if NAMED_GAP.search(m.group("gap")):
                    out.append(Claim(**base, period_basis="-", outcome="not checked",
                                     reason=f"segment or other subject ('{phrase}{m.group('gap')}')"))
                    continue
                when, basis, span = _period(sent, m.start("dollar"), m.end(), current_years, form, fp,
                                            heading_before(text, s0))
                if when == "other":
                    out.append(Claim(**base, period_basis=basis, outcome="not checked", reason="another period"))
                    continue
                unit = "USD/shares" if metric == "eps_diluted" else "USD"
                concepts = HEADLINE[metric]
                if metric == "net_income" and "noncontrolling" in phrase.lower():
                    concepts = ("us-gaap:ProfitLoss",)
                elif metric == "net_income" and "attributable" in phrase.lower():
                    concepts = tuple(c for c in concepts if c != "us-gaap:ProfitLoss")
                cands = [f for f in current if f.concept in concepts and f.unit == unit]
                if form == "10-Q" and span != "either":
                    cands = [f for f in cands if (duration_class(f.start, f.end) == "quarter") == (span == "quarter")]
                tagged = tuple(sorted({(f.concept, duration_class(f.start, f.end), f.value) for f in cands}))
                if not cands:
                    out.append(Claim(**base, period_basis=basis, outcome="not checked",
                                     reason="no tagged value for the metric and period", tagged=tagged))
                    continue
                hit = [f for f in cands if abs(Decimal(f.value) - value) <= tol]
                if hit:
                    f = hit[0]
                    out.append(Claim(**base, period_basis=basis, outcome="matches", reason="",
                                     matched=f"{f.concept} {duration_class(f.start, f.end)}", tagged=tagged))
                elif all(abs(abs(value) - abs(Decimal(f.value))) > NEAR * abs(Decimal(f.value)) for f in cands):
                    # Segment results often carry their subject in a heading pages earlier ("Net income was $3.0
                    # billion" under a business-line heading). An amount nowhere near the consolidated value is
                    # treated as another scope, not as a mismatch.
                    out.append(Claim(**base, period_basis=basis, outcome="not checked",
                                     reason=f"amount not within {NEAR:.0%} of the consolidated value (likely a "
                                            "segment or other scope)", tagged=tagged))
                else:
                    out.append(Claim(**base, period_basis=basis, outcome="no matching tagged value", reason="",
                                     tagged=tagged))
    return sorted(out, key=lambda c: c.start)
