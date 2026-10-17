"""Invariants over the real extraction (needs data/: `filing-delta fetch`, then `facts`; skipped without it).

The join's verification is two independent paths agreeing: inline XBRL read from the filing and the SEC's
company-facts API, compared value by value for the same accession (docs/xbrl-report.md).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "data" / "facts"
pytestmark = pytest.mark.skipif(not FACTS.exists(), reason="no data/facts (run filing-delta fetch, then facts)")


@pytest.fixture(scope="module")
def recs():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in FACTS.glob("*.json")}


def test_one_record_per_filing(recs):
    manifest = {r["accession"] for r in csv.DictReader((ROOT / "corpus" / "manifest.csv").open(encoding="utf-8"))}
    assert set(recs) == manifest


def test_period_end_from_the_document_matches_edgar(recs):
    assert all(r["period_matches_manifest"] for r in recs.values())
    assert sum(r["period_end_source"].startswith("dei") for r in recs.values()) == 132


def test_no_unreadable_or_conflicting_values(recs):
    assert [(r["company"], i) for r in recs.values() for i in r["issues"]] == []


def test_two_sources_agree(recs):
    cc = [r["cross_check"] for r in recs.values() if r["cross_check"] and r["cross_check"]["status"] == "compared"]
    assert sum(c["compared"] for c in cc) > 60_000
    assert [d for c in cc for d in c["differ"]] == []


def test_headline_coverage(recs):
    for metric in ("revenue", "net_income", "total_assets", "cash", "operating_cash_flow"):
        missing = [(r["company"], r["report_date"]) for r in recs.values() if r["headline"][metric]["status"] != "ok"]
        assert missing == [], metric


@pytest.mark.parametrize("acc,metric,value,start,period", [
    ("0000320193-23-000106", "revenue", "383285000000", "2022-09-25", "annual"),     # Apple FY2023, 53 weeks
    ("0000104169-25-000021", "revenue", "680985000000", "2024-02-01", "annual"),     # Walmart, January FYE
    ("0000019617-20-000257", "revenue", "115627000000", "2019-01-01", "annual"),     # JPMorgan total net revenue
    ("0000078003-20-000014", "revenue", "51750000000", "2019-01-01", "annual"),      # Pfizer, via company-facts
    ("0001628280-26-050503", "revenue", "13380000000", "2026-04-04", "quarter"),     # Coca-Cola 13-week Q2
    ("0001628280-26-050503", "operating_cash_flow", "7543000000", "2026-01-01", "half"),  # cash flow is YTD only
])
def test_reference_headlines(recs, acc, metric, value, start, period):
    h = recs[acc]["headline"][metric]
    assert (h["value"], h["start"], h["period"]) == (value, start, period)


def test_statements_in_an_exhibit_fall_back_to_companyfacts(recs):
    r = recs["0000078003-20-000014"]                                                 # Pfizer FY2019, Exhibit 13
    assert r["source"] == "companyfacts" and r["source_reason"].startswith("statements outside the primary document")
