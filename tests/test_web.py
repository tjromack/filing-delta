"""The read view (M8): pages render from the real data, citations are exact, limits are stated, no key means no model.

Needs data/ (fetch, parse, diff, the M4 corpus report and the M6 QA run); skipped without it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "qa" / "run.jsonl").exists() or
                                not (ROOT / "data" / "diffs").exists(), reason="needs data/ (see tools/reproduce.py)")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from filing_delta.web import create_app
    return TestClient(create_app(ROOT))


def test_every_page_states_the_limits(client):
    for url in ("/", "/company/320193", "/questions", "/questions/QA01", "/ask"):
        r = client.get(url)
        assert r.status_code == 200, url
        assert "unaudited narrative" in r.text and "Nothing here is investment advice or a forecast" in r.text, url


def test_home_lists_the_corpus(client):
    r = client.get("/")
    for name in ("Apple Inc.", "Walmart Inc.", "JPMORGAN CHASE &amp; CO"):
        assert name in r.text                       # escaped, never raw
    assert r.text.count('href="/company/') == 11


def test_pair_page_shows_changes_with_labels_and_exact_spans(client):
    stem = "320193_10K_1A_2022-09-24__2023-09-30"
    r = client.get(f"/pair/{stem}")
    assert r.status_code == 200 and "<del>" in r.text and 'class="chip material"' in r.text
    assert "new chars" in r.text and "sec.gov/Archives" in r.text
    material_only = client.get(f"/pair/{stem}?material=1").text
    assert material_only.count('class="card"') < r.text.count('class="card"')
    assert 'class="chip cosmetic"' not in material_only


def test_pair_rejects_path_tricks(client):
    assert client.get("/pair/..%2F..%2Fpyproject").status_code == 404
    assert client.get("/pair/nope").status_code == 404


def test_question_page_highlights_the_exact_cited_span(client):
    run = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "data" / "qa" / "run.jsonl").read_text(encoding="utf-8").splitlines()}
    qid = next(q for q, t in sorted(run.items()) if t["result"]["type"] == "answer")
    c = run[qid]["result"]["citations"][0]
    text = (ROOT / "data" / "sections" / c["accession"] / f"{c['section']}.txt").read_text(encoding="utf-8")
    assert text[c["start"]:c["end"]] == c["quote"]
    from html import escape
    assert f"<mark>{escape(c['quote'])}</mark>" in client.get(f"/questions/{qid}").text


def test_refusals_show_as_refusals(client):
    run = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "data" / "qa" / "run.jsonl").read_text(encoding="utf-8").splitlines()}
    qid = next(q for q, t in sorted(run.items()) if t["stage"] == "scope")
    r = client.get(f"/questions/{qid}").text
    assert ">abstained<" in r and "<mark>" not in r


def test_without_a_key_nothing_calls_a_model(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert "needs" in client.get("/ask").text and "<form" not in client.get("/ask").text
    assert client.post("/ask", data={"q": "What does Apple say about China?"}).status_code == 403
