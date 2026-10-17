"""XBRL facts (M5): transforms, period alignment, the two sources, and facts-are-never-narrative."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from filing_delta.xbrl import Fact, dec_str, duration_class, extract, facts_for, headline, render, role
from filing_delta.xbrl.inline import parse_value, words_to_number

ROOT = Path(__file__).resolve().parents[1]
MINI = (ROOT / "tests" / "fixtures" / "xbrl" / "mini.xhtml").read_bytes()


@pytest.fixture(scope="module")
def mini():
    return extract(MINI, "0000021344-26-000001")


def get(ix, concept, end="2026-07-03", start="2026-04-04", dims=()):
    return next(f for f in ix.facts if f.concept == concept and f.end == end and f.start == start and f.dims == dims)


# --- value transforms -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text,fmt,want", [
    ("13,380", "ixt:num-dot-decimal", "13380"), ("0.88", "ixt:numdotdecimal", "0.88"), ("1,234", None, "1234"),
    ("—", "ixt:fixed-zero", "0"), ("-", "ixt:zerodash", "0"), ("no", "ixt:fixed-zero", "0"),
    ("twenty-five", "ixt-sec:numwordsen", "25"), ("No", "ixt-sec:numwordsen", "0"), ("one hundred", "ixt-sec:numwordsen", "100"),
    ("1.234,5", "ixt:num-comma-decimal", "1234.5"),
])
def test_value_transforms(text, fmt, want):
    assert dec_str(parse_value(text, fmt)) == want


def test_unreadable_values_are_none_not_zero():
    assert parse_value("n/a", "ixt:num-dot-decimal") is None
    assert parse_value("12", "ixt:some-new-format") is None
    assert words_to_number("several") is None


def test_dec_str_is_canonical():
    assert dec_str("13380000000") == dec_str(13380000000) == "13380000000"   # never 1.338E+10
    assert dec_str(2.97) == dec_str("2.970") == "2.97"
    assert dec_str("-0") == "0"


# --- extraction ---------------------------------------------------------------------------------------------------

def test_scale_sign_units_dimensions(mini):
    assert get(mini, "us-gaap:Revenues").value == "13380000000"
    assert get(mini, "us-gaap:OtherNonoperatingIncomeExpense").value == "-87000000"        # sign="-" in parentheses
    assert get(mini, "us-gaap:AssetImpairmentCharges").value == "0"                        # dash means zero
    assert get(mini, "us-gaap:EarningsPerShareDiluted").unit == "USD/shares"
    us = get(mini, "us-gaap:Revenues", dims=(("srt:StatementGeographicalAxis", "ko:USMember"),))
    assert us.value == "2426000000"
    assert get(mini, "us-gaap:NumberOfOperatingSegments").value == "25"
    assert get(mini, "us-gaap:LongTermDebt", start=None).value is None                      # xsi:nil stays nil


def test_rounded_duplicate_keeps_the_precise_value(mini):
    # "$4.9 billion" (decimals -8) comes first, in prose; 4,861 million (decimals -6) in the table. They agree at -8:
    # one fact, the precise one, and no conflict.
    assert get(mini, "us-gaap:UnrecognizedTaxBenefits", start=None).value == "4861000000"
    assert not [i for i in mini.issues if i["concept"] == "us-gaap:UnrecognizedTaxBenefits"]


def test_conflicts_and_orphans_are_reported_not_dropped(mini):
    problems = {(i["concept"], i["problem"].split(":")[0]) for i in mini.issues}
    assert ("us-gaap:Goodwill", "conflicting duplicate") in problems                      # 18,100 vs 18,200
    assert ("us-gaap:Liabilities", "missing context") in problems
    assert get(mini, "us-gaap:Goodwill", start=None).value == "18200000000"               # first kept, conflict logged


def test_dei_period_end_comes_from_the_document(mini):
    assert mini.dei["DocumentPeriodEndDate"] == {"text": "July 3, 2026", "end": "2026-07-03"}
    assert mini.dei["DocumentFiscalPeriodFocus"]["text"] == "Q2"


# --- period alignment ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("start,end,want", [
    ("2026-04-04", "2026-07-03", "quarter"),       # Coca-Cola 13-week quarter (91 days)
    ("2025-09-28", "2026-01-03", "quarter"),       # a 14-week quarter (98 days)
    ("2026-01-01", "2026-07-03", "half"),          # year-to-date at Q2
    ("2024-02-01", "2025-01-31", "annual"),        # Walmart's January fiscal year end
    ("2022-09-25", "2023-09-30", "annual"),        # Apple's 53-week fiscal 2023 (371 days)
    ("2026-01-01", "2026-02-15", "other"),
    (None, "2026-07-03", "instant"),
])
def test_duration_classes(start, end, want):
    assert duration_class(start, end) == want


def test_roles():
    f = Fact("us-gaap:Revenues", "1", "USD", "2025-03-29", "2025-06-27")
    assert role(f, "2026-07-03") == "comparative"
    assert role(Fact("us-gaap:Assets", "1", "USD", None, "2026-07-03"), "2026-07-03") == "current"


def test_headline_10q(mini):
    h = headline(mini.facts, "2026-07-03", "10-Q")
    assert h["revenue"] == {"status": "ok", "concept": "us-gaap:Revenues", "value": "13380000000",
                            "values": ["13380000000"], "start": "2026-04-04", "end": "2026-07-03", "period": "quarter"}
    assert h["operating_cash_flow"]["period"] == "half" and h["operating_cash_flow"]["value"] == "3912000000"
    assert h["total_assets"]["value"] == "104557000000"
    assert h["net_income"] == {"status": "not tagged"}                 # absent is "not tagged", never zero
    assert h["eps_diluted"]["value"] == "0.88"


def test_headline_ignores_dimensions_and_comparatives():
    facts = [Fact("us-gaap:Revenues", "5", "USD", "2026-04-04", "2026-07-03", dims=(("a", "b"),)),
             Fact("us-gaap:Revenues", "7", "USD", "2025-03-29", "2025-06-27")]
    assert headline(facts, "2026-07-03", "10-Q")["revenue"] == {"status": "not tagged"}


# --- company-facts API --------------------------------------------------------------------------------------------

def test_companyfacts_keeps_only_the_accession():
    doc = {"facts": {"us-gaap": {"EarningsPerShareDiluted": {"units": {"USD/shares": [
        {"start": "2024-01-01", "end": "2024-12-31", "val": 2.95, "accn": "B", "form": "10-K/A", "fy": 2024},
        {"start": "2024-01-01", "end": "2024-12-31", "val": 2.97, "accn": "A", "form": "10-K", "fy": 2024},
        {"start": "2023-01-01", "end": "2023-12-31", "val": 2.50, "accn": "B", "form": "10-K/A", "fy": 2024},
    ]}}}}}
    (f,) = facts_for(doc, "A")
    assert (f.concept, f.value, f.unit, f.source) == ("us-gaap:EarningsPerShareDiluted", "2.97", "USD/shares",
                                                      "companyfacts")


# --- never narrative ----------------------------------------------------------------------------------------------

def test_render_always_carries_provenance():
    f = Fact("us-gaap:Revenues", "13380000000", "USD", "2026-04-04", "2026-07-03", accession="X")
    assert "unaudited interim financial statements" in render(f, "10-Q")
    assert "audited financial statements" in render(f, "10-K") and "unaudited" not in render(f, "10-K")
    with pytest.raises(ValueError):
        render(f, "8-K")


def test_facts_have_no_text_span():
    assert not {"text", "start_char", "char_start", "section"} & set(Fact.__dataclass_fields__)


@pytest.mark.parametrize("pkg", ["parse", "diff", "classify"])
def test_narrative_stages_never_import_xbrl(pkg):
    for p in (ROOT / "filing_delta" / pkg).rglob("*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
                assert not any("xbrl" in n for n in names), f"{p.name} imports XBRL facts"
