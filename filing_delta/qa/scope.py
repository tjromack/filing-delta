"""Scope a question to filings before anything is retrieved (M6, docs/design/qa.md §2.1–2.2). Pure; no model.

The same risk factor can sit in eight consecutive 10-Ks, so retrieval runs only inside the filing(s) the question is
about. A question that names no corpus company, asks about a period outside coverage, or asks for advice or a
prediction abstains here, with its reason and no model call.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Names and tickers people use, by CIK. Tickers match case-sensitively; Ford's "F" is left out (too ambiguous).
ALIASES = {
    320193: ("Apple", ["apple"], ["AAPL"]),
    21344: ("Coca-Cola", ["coca-cola", "coca cola", "coke"], ["KO"]),
    1065280: ("Netflix", ["netflix"], ["NFLX"]),
    104169: ("Walmart", ["walmart", "wal-mart"], ["WMT"]),
    78003: ("Pfizer", ["pfizer"], ["PFE"]),
    37996: ("Ford", ["ford", "ford motor"], []),
    106532: ("Weyco", ["weyco"], ["WEYS"]),
    1067983: ("Berkshire Hathaway", ["berkshire"], ["BRK", "BRK.A", "BRK.B"]),
    19617: ("JPMorgan Chase", ["jpmorgan", "jp morgan", "j.p. morgan", "chase"], ["JPM"]),
    34088: ("Exxon Mobil", ["exxon", "exxonmobil"], ["XOM"]),
    40545: ("General Electric", ["general electric"], ["GE"]),
}
COVERAGE = ("10-K for fiscal years 2018 to 2025 and 10-Qs filed January 2025 to September 2026, for Apple, "
            "Coca-Cola, Netflix, Walmart, Pfizer, Ford, Weyco, Berkshire Hathaway, JPMorgan Chase, Exxon Mobil and "
            "General Electric")
ADVICE_REASON = ("This tool reports what the filings say. It doesn't give investment advice or predictions.")

# Always advice: buy/sell/hold, price targets, valuation verdicts.
ADVICE = re.compile(r"\bshould\s+(?:i|we|you|investors?)\s+(?:buy|sell|hold|short|invest|own)\b|"
                    r"\b(?:buy|sell|short)\s+(?:the\s+)?(?:stock|shares?)\b|\bprice\s+target\b|"
                    r"\b(?:good|bad|safe|smart)\s+(?:investment|buy|stock)\b|\b(?:under|over)valued\b|"
                    r"\bworth\s+(?:buying|investing)\b", re.I)
# Predictions, unless the question asks what a filing says about the future.
PREDICT = re.compile(r"\bwill\b[^.?!]{0,50}?\b(?:go(?:es)?\s+(?:up|down)|rise|fall|increase|decrease|drop|beat|miss|"
                     r"outperform|underperform|grow|recover|go\s+bankrupt|be\s+(?:higher|lower|profitable)|"
                     r"cut|raise)\b|"
                     r"\bwill\s+(?:the\s+)?(?:stock|shares?|share\s+price)\b|"
                     r"\b(?:predict|forecast)\s+(?:the|its|their|next)\b", re.I)
REPORTING = re.compile(r"\b(?:say|says|said|state|states|stated|disclose|discloses|disclosed|describe|describes|"
                       r"mention|mentions|according\s+to|report|reports|expect|expects|warn|warns)\b", re.I)
YEAR = re.compile(r"\b(?:fiscal\s+(?:year\s+)?|fy\s?'?)?((?:19|20)\d\d)\b", re.I)
QUARTER = re.compile(r"\bq([1-4])\b|\b(first|second|third|fourth)[\s-]quarter\b", re.I)
QWORD = {"first": "1", "second": "2", "third": "3", "fourth": "4"}
RISK = re.compile(r"\brisk", re.I)
MDA = re.compile(r"\bmd&a\b|management['’]s\s+discussion|results\s+of\s+operations|\bliquidity\b", re.I)
# Questions about performance figures and their drivers belong to MD&A unless they ask about risks.
PERF = re.compile(r"\b(?:revenues?|sales|net\s+income|earnings|operating\s+income|margins?|cash\s+flows?|"
                  r"capital\s+(?:spending|expenditures?|investments?)|expenses?|dividends?|drove|driven|drivers?)\b",
                  re.I)
# ...but only when the question asks for a figure or a driver. "Did weight-loss drugs reduce its sales?" is about a
# risk the filing describes, not an MD&A figure.
FIGURE = re.compile(r"\b(?:drove|driven|drivers?|why|how\s+much|how\s+many|what\s+(?:was|were)|increased?|"
                    r"decreased?|grew|growth|declined?|amount|total)\b", re.I)
CHANGE = re.compile(r"\b(?:add|added|adds|new|newly|remove|removed|drop|dropped|change|changed|changes|differ|"
                    r"different|no\s+longer)\b", re.I)


@dataclass(frozen=True)
class Filing:
    accession: str
    cik: int
    form: str              # 10-K | 10-Q
    period_end: str
    fiscal_year: str
    fiscal_period: str     # FY | Q1 | Q2 | Q3
    sections: tuple[str, ...]


@dataclass
class Scope:
    filings: list[Filing] = field(default_factory=list)
    sections: tuple[str, ...] = ()
    abstain: str | None = None
    notes: list[str] = field(default_factory=list)
    change: bool = False       # "what was added/removed between two years": search only the units the M3 diff changed


def companies(q: str) -> list[int]:
    found = []
    low = q.lower()
    for cik, (_, names, tickers) in ALIASES.items():
        if any(re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", low) for n in names) or \
                any(re.search(rf"(?<![\w.]){re.escape(t)}(?![\w])", q) for t in tickers):
            found.append(cik)
    return found


def scope(q: str, catalog: list[Filing]) -> Scope:
    if ADVICE.search(q) or (PREDICT.search(q) and not REPORTING.search(q)):
        return Scope(abstain=ADVICE_REASON)
    ciks = companies(q)
    if not ciks:
        return Scope(abstain=f"The question doesn't name a company in the corpus. Coverage: {COVERAGE}.")
    years = sorted({m.group(1) for m in YEAR.finditer(q)})
    qm = QUARTER.search(q)
    quarter = (qm.group(1) or QWORD[qm.group(2).lower()]) if qm else None
    form = "10-Q" if (quarter or re.search(r"\b10-?q\b|\bquarterly\b", q, re.I)) else "10-K"
    if re.search(r"\b10-?k\b|\bannual\s+report\b", q, re.I) and not quarter:
        form = "10-K"
    if quarter == "4":
        return Scope(abstain="The fourth quarter is reported in the 10-K, not a 10-Q; ask about the 10-K for that "
                             f"fiscal year. Coverage: {COVERAGE}.")
    if RISK.search(q) and not MDA.search(q):
        sections = ("10K_1A", "10Q_P2_1A")
    elif (MDA.search(q) or (PERF.search(q) and FIGURE.search(q))) and not RISK.search(q):
        sections = ("10K_7", "10Q_P1_2")
    else:
        sections = ("10K_1A", "10K_7", "10Q_P1_2", "10Q_P2_1A")
    out = Scope(sections=sections, change=bool(CHANGE.search(q)) and len(years) >= 2)
    for cik in ciks:
        mine = sorted((f for f in catalog if f.cik == cik and f.form == form),
                      key=lambda f: (f.fiscal_year, f.fiscal_period))
        if quarter:
            mine = [f for f in mine if f.fiscal_period == f"Q{quarter}"]
        name = ALIASES[cik][0]
        if years:
            picked = [f for f in mine if f.fiscal_year in years]
            missing = [y for y in years if y not in {f.fiscal_year for f in picked}]
            if missing:
                what = f"{form}" + (f" for Q{quarter}" if quarter else "")
                return Scope(abstain=f"{name}'s {what} for fiscal {', '.join(missing)} is outside the corpus. "
                                     f"Coverage: {COVERAGE}.")
        else:
            picked = mine[-1:]
            if picked:
                f = picked[0]
                out.notes.append(f"No period was given, so this uses {name}'s latest {form} "
                                 f"({f.fiscal_period} fiscal {f.fiscal_year}, period ended {f.period_end}).")
        if not picked:
            return Scope(abstain=f"No {form} for {name} is in the corpus. Coverage: {COVERAGE}.")
        out.filings += picked
    if not any(s in f.sections for f in out.filings for s in sections):
        return Scope(abstain="Those filings have no parsed text for the section asked about (a 10-Q often refers its "
                             "risk factors back to the 10-K).")
    return out
