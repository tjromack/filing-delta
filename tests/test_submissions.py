"""Submissions paging and corpus selection."""
from __future__ import annotations

import json
from pathlib import Path

import httpx

from filing_delta.edgar import CorpusSpec, EdgarClient, Filing, all_filings, select

ROOT = Path(__file__).resolve().parents[1]
SPEC = CorpusSpec(ciks=(1,), k_period_from="2018-01-01", k_period_to="2025-12-31",
                  q_filed_from="2025-01-01", q_filed_to="2026-09-30")


def block(*rows):
    cols = ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument", "isInlineXBRL")
    return {c: [r[i] for r in rows] for i, c in enumerate(cols)}


def test_all_filings_merges_paged_history_and_dedupes(tmp_path):
    recent = block(("0001-26-000001", "2026-02-01", "2025-12-31", "10-K", "a.htm", 1),
                   ("0001-19-000001", "2019-02-01", "2018-12-31", "10-K", "b.htm", 0))
    older = block(("0001-19-000001", "2019-02-01", "2018-12-31", "10-K", "b.htm", 0),   # overlaps the recent block
                  ("0001-18-000001", "2018-02-01", "2017-12-31", "10-K", "c.htm", 0))
    pages = {
        "https://data.sec.gov/submissions/CIK0000000001.json":
            {"name": "Test Co", "filings": {"recent": recent, "files": [{"name": "CIK0000000001-submissions-001.json"}]}},
        "https://data.sec.gov/submissions/CIK0000000001-submissions-001.json": older,
    }
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=json.dumps(pages[str(r.url)]).encode()))
    client = EdgarClient("Test test@example.com", tmp_path, transport=transport, sleep=lambda s: None)
    got = all_filings(client, 1)
    assert [f.accession for f in got] == ["0001-18-000001", "0001-19-000001", "0001-26-000001"]
    assert all(f.company == "Test Co" for f in got)


def test_history_pages_entirely_before_the_window_are_not_requested(tmp_path):
    recent = block(("0001-26-000001", "2026-02-01", "2025-12-31", "10-K", "a.htm", 1))
    head = {"name": "Test Co", "filings": {"recent": recent, "files": [
        {"name": "CIK0000000001-submissions-001.json", "filingFrom": "2016-01-01", "filingTo": "2019-06-30"},
        {"name": "CIK0000000001-submissions-002.json", "filingFrom": "2001-01-01", "filingTo": "2015-12-31"},
    ]}}
    seen = []

    def handler(r):
        seen.append(str(r.url))
        body = head if r.url.path.endswith("CIK0000000001.json") else block()
        return httpx.Response(200, content=json.dumps(body).encode())

    client = EdgarClient("Test test@example.com", tmp_path, transport=httpx.MockTransport(handler), sleep=lambda s: None)
    all_filings(client, 1, filed_since="2018-01-01")
    assert not any("002" in u for u in seen)
    assert any("001" in u for u in seen)


def f(form, report, filed, acc="x"):
    return Filing(cik=1, form=form, report_date=report, filing_date=filed, accession=acc,
                  primary_document="d.htm", is_ixbrl=True)


def test_select_applies_windows_inclusively_and_excludes_amendments():
    filings = [
        f("10-K", "2017-12-31", "2018-02-01", "k-out-early"),
        f("10-K", "2018-01-31", "2018-03-20", "k-in-first"),       # Walmart-style January FYE on the boundary
        f("10-K", "2025-12-31", "2026-02-10", "k-in-last"),
        f("10-K", "2026-01-31", "2026-03-13", "k-out-late"),
        f("10-K/A", "2020-12-31", "2021-04-01", "k-amend"),
        f("10-Q", "2024-12-31", "2024-12-31", "q-out-early"),
        f("10-Q", "2025-03-31", "2025-01-01", "q-in-first"),
        f("10-Q", "2026-06-30", "2026-09-30", "q-in-last"),
        f("10-Q/A", "2025-06-30", "2025-08-01", "q-amend"),
        f("8-K", "2025-06-30", "2025-07-01", "eightk"),
    ]
    assert {x.accession for x in select(filings, SPEC)} == {"k-in-first", "k-in-last", "q-in-first", "q-in-last"}


def test_url_strips_accession_dashes():
    x = Filing(cik=320193, form="10-K", report_date="2025-09-27", filing_date="2025-10-31",
               accession="0000320193-25-000079", primary_document="aapl-20250927.htm", is_ixbrl=True)
    assert x.url == "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm"


def test_locked_corpus_file_parses():
    spec = CorpusSpec.load(ROOT / "corpus.toml")
    assert len(spec.ciks) == 11 and len(set(spec.ciks)) == 11
    assert (spec.k_period_from, spec.k_period_to) == ("2018-01-01", "2025-12-31")
    assert (spec.q_filed_from, spec.q_filed_to) == ("2025-01-01", "2026-09-30")
