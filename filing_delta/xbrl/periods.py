"""Period alignment (M5): which facts describe the filing's own period, and of what length. Pure.

The filing's period end comes from the document itself (dei:DocumentPeriodEndDate's context), never from the
company-facts `fy`/`fp` fields, which describe the filing that reported a row rather than the period it covers.
Durations are classed by length with room for 52/53-week fiscal years (Coca-Cola's Q2 2026 runs 2026-04-04 to
2026-07-03; Walmart's fiscal year ends January 31).
"""
from __future__ import annotations

from datetime import date

from .facts import Fact

# Inclusive day counts. A 13-week quarter is 91 days and a 14-week one 98; a 52/53-week year is 364/371.
CLASSES = (("quarter", 84, 98), ("half", 175, 189), ("nine_months", 266, 280), ("annual", 357, 371))

# Headline concepts, in preference order (the first present wins, and the choice is recorded).
HEADLINE = {
    "revenue": ("us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
                "us-gaap:SalesRevenueNet", "us-gaap:RevenuesNetOfInterestExpense"),   # the last: banks' net revenue
    # attributable to the parent first; ProfitLoss (which includes noncontrolling interests) last
    "net_income": ("us-gaap:NetIncomeLoss", "us-gaap:NetIncomeLossAvailableToCommonStockholdersBasic",
                   "us-gaap:ProfitLoss"),
    "operating_income": ("us-gaap:OperatingIncomeLoss",),
    "eps_diluted": ("us-gaap:EarningsPerShareDiluted",),
    "total_assets": ("us-gaap:Assets",),
    "cash": ("us-gaap:CashAndCashEquivalentsAtCarryingValue",
             "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
    "operating_cash_flow": ("us-gaap:NetCashProvidedByUsedInOperatingActivities",
                            "us-gaap:NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
}
INSTANT = {"total_assets", "cash"}
UNIT = {"eps_diluted": "USD/shares"}


def days(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def duration_class(start: str | None, end: str) -> str:
    if start is None:
        return "instant"
    n = days(start, end)
    for name, lo, hi in CLASSES:
        if lo <= n <= hi:
            return name
    return "other"


def role(fact: Fact, period_end: str) -> str:
    """'current' if the fact ends on the filing's period end, else 'comparative' (earlier) or 'later'."""
    if fact.end == period_end:
        return "current"
    return "comparative" if fact.end < period_end else "later"


def headline(facts: list[Fact], period_end: str, form: str) -> dict[str, dict]:
    """The consolidated (no-dimension), current-period headline values. A metric the filer doesn't tag is reported as
    not tagged, never as zero. 10-K flows: the annual duration. 10-Q flows: the fiscal quarter, or the year-to-date
    duration when no quarter is tagged (cash-flow statements are year-to-date only); `period` says which."""
    wants = ("annual",) if form == "10-K" else ("quarter", "half", "nine_months")
    out: dict[str, dict] = {}
    for metric, concepts in HEADLINE.items():
        unit = UNIT.get(metric, "USD")
        hit = None
        for want in (("instant",) if metric in INSTANT else wants):
            for c in concepts:
                cands = [f for f in facts if f.concept == c and f.unit == unit and not f.dims
                         and f.value is not None and role(f, period_end) == "current"
                         and duration_class(f.start, f.end) == want]
                if cands:
                    hit = (c, cands)
                    break
            if hit:
                break
        if hit is None:
            out[metric] = {"status": "not tagged"}
            continue
        c, cands = hit
        vals = sorted({f.value for f in cands})
        out[metric] = {"status": "ok" if len(vals) == 1 else "ambiguous", "concept": c, "value": vals[0],
                       "values": vals, "start": cands[0].start, "end": cands[0].end,
                       "period": duration_class(cands[0].start, cands[0].end)}
    return out
