"""The answer pipeline end to end with a scripted model (needs data/: parse + facts; skipped without it).

Every path from model output to result: a verified answer, a quote that's off by one character, a second citation
that fails, "not answerable", unparseable output, and a refusal. No API calls.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from filing_delta.classify.model import Recorder
from filing_delta.qa.ask import ask
from filing_delta.qa.index import catalog

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "facts").exists(), reason="needs data/ (parse, facts)")
Q = "What does Weyco's 2023 10-K say about its reliance on foreign manufacturers?"


class Scripted:
    """Answers with whatever `make(passages)` returns; passages are parsed back out of the request."""

    def __init__(self, make, stop_reason="end_turn"):
        self.make, self.stop_reason = make, stop_reason

    def complete(self, request):
        msg = request["messages"][0]["content"]
        passages = dict(re.findall(r"\[(P\d+)\][^\n]*\n(.*?)(?=\n\n\[P\d+\]|\Z)", msg, re.S))
        out = self.make(passages)
        return {"id": "x", "model": request["model"], "stop_reason": self.stop_reason,
                "text": out if isinstance(out, str) else json.dumps(out), "usage": {}, "stop_details": None}


@pytest.fixture(scope="module")
def cat():
    return catalog(ROOT)


def run(make, tmp_path, cat, stop_reason="end_turn"):
    return ask(Q, ROOT, cat, Recorder(tmp_path, provider=Scripted(make, stop_reason)))


def first_sentence(p):
    return p["P1"].split(". ")[0]


def test_exact_quote_is_a_verified_answer_with_provenance(tmp_path, cat):
    t = run(lambda p: {"answerable": True, "answer": "It buys abroad.", "reason": "",
                       "citations": [{"passage": "P1", "quote": first_sentence(p), "claim": "It buys abroad."}]},
            tmp_path, cat)
    r = t["result"]
    assert r["type"] == "answer" and len(r["citations"]) == 1
    c = r["citations"][0]
    assert c["claim"] == "It buys abroad."                     # v3: the claim travels with its citation
    text = (ROOT / "data" / "sections" / c["accession"] / f"{c['section']}.txt").read_text(encoding="utf-8")
    assert text[c["start"]:c["end"]] == c["quote"]
    assert "Weyco 10-K, fiscal 2023" in t["provenance"] and "unaudited" in t["provenance"]


def test_one_character_off_abstains(tmp_path, cat):
    t = run(lambda p: {"answerable": True, "answer": "x", "reason": "",
                       "citations": [{"passage": "P1", "quote": first_sentence(p).replace("e", "E", 1)}]}, tmp_path, cat)
    assert t["result"] == {"type": "abstain", "reason": "citation could not be verified"} and t["stage"] == "verify"


def test_a_failing_second_citation_sinks_the_answer(tmp_path, cat):
    t = run(lambda p: {"answerable": True, "answer": "x", "reason": "",
                       "citations": [{"passage": "P1", "quote": first_sentence(p)},
                                     {"passage": "P2", "quote": "words that are not in the passage"}]}, tmp_path, cat)
    assert t["result"]["type"] == "abstain" and t["problems"] == [
        "citation 2: quote is not an exact substring of P2"]


def test_quote_from_the_wrong_passage_abstains(tmp_path, cat):
    t = run(lambda p: {"answerable": True, "answer": "x", "reason": "",
                       "citations": [{"passage": "P2", "quote": first_sentence(p)}]}, tmp_path, cat)
    assert t["result"]["type"] == "abstain"


def test_not_answerable_abstains_with_the_reason(tmp_path, cat):
    t = run(lambda p: {"answerable": False, "answer": "", "citations": [], "reason": "No figure given."},
            tmp_path, cat)
    assert t["result"] == {"type": "abstain", "reason": "The filings in scope don't answer this. No figure given."}


def test_unparseable_and_refusal_abstain(tmp_path, cat):
    assert run(lambda p: "not json", tmp_path / "a", cat)["result"]["type"] == "abstain"
    t = run(lambda p: "", tmp_path / "b", cat, stop_reason="refusal")
    assert t["result"] == {"type": "abstain", "reason": "The model declined to answer."}


def test_scope_abstentions_never_call_the_model(tmp_path, cat):
    class Boom:
        def complete(self, request):
            raise AssertionError("model called")
    t = ask("Should I buy Weyco stock?", ROOT, cat, Recorder(tmp_path, provider=Boom()))
    assert t["stage"] == "scope" and t["result"]["type"] == "abstain"
