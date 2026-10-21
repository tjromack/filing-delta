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
from filing_delta.qa.guard import load_catalog
from filing_delta.qa.index import catalog
from filing_delta.qa.version import pipeline_version

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


def test_missed_terms_are_question_words_in_scope_but_not_retrieved():
    from filing_delta.qa.ask import missed_terms
    from filing_delta.qa.index import Unit
    units = [Unit("A", "10K_1A", 0, 9, "paragraph", "", "membership growth was strong"),
             Unit("A", "10K_1A", 10, 19, "paragraph", "", "we limit shared viewing outside a household"),
             Unit("A", "10K_1A", 20, 29, "paragraph", "", "unrelated text")]
    top = [(1.0, units[0])]
    q = "What does Netflix's 2023 10-K say about the effect of paid sharing on membership growth?"
    assert missed_terms(q, units, top) == ["shar"]        # in the filing, not retrieved; "paid" is in neither
    assert missed_terms(q, units, [(1.0, units[0]), (1.0, units[1])]) == []


def test_absence_answer_with_missed_words_gets_a_second_look(tmp_path, cat):
    calls = []

    def make(p):
        calls.append(len(p))
        return {"answerable": True, "answer": "The 10-K doesn't say X. It does say this.", "reason": "", "absence": True,
                "search_terms": ["pension", "retirement plan"],      # other wording the model offers for X
                "citations": [{"passage": "P1", "quote": first_sentence(p), "claim": "It does say this."}]}
    q = "What does Weyco's 2023 10-K say about tariffs on footwear imported from Vietnam?"
    t = ask(q, ROOT, cat, Recorder(tmp_path, provider=Scripted(make)))
    sp = t["second_pass"]                             # an absence claim with other wording: always a second look
    assert len(calls) == 2 and calls[1] > calls[0] and "pension" in sp["missed_terms"]
    assert len(t["retrieved"]) == calls[1] and sp["first"]["result"]["type"] == "answer"
    from filing_delta.qa.index import tokens
    for a in sp["added"]:                              # every added passage holds a word the second search was for
        text = (ROOT / "data" / "sections" / a["accession"] / f"{a['section']}.txt").read_text(
            encoding="utf-8")[a["start"]:a["end"]]
        assert set(tokens(a["heading"] + " " + text)) & set(sp["missed_terms"])
    # an answer that doesn't claim an absence never triggers a second look
    calls.clear()
    t2 = ask(q, ROOT, cat, Recorder(tmp_path / "b", provider=Scripted(
        lambda p: {"answerable": True, "answer": "It says this.", "reason": "", "absence": False,
                   "citations": [{"passage": "P1", "quote": first_sentence(p), "claim": "It says this."}]})))
    assert "second_pass" not in t2


@pytest.mark.parametrize("q,figure", [
    ("How much did Coca-Cola spend on Super Bowl advertising according to its 2022 10-K?", True),
    ("What does Exxon's 2023 10-K say its breakeven oil price is for its Guyana projects?", True),
    ("How many iPhones did Apple sell in fiscal 2023, according to its 10-K?", True),
    ("What does Apple's 2023 10-K say Tim Cook's salary was?", True),
    ("Does Walmart's fiscal 2025 10-K discuss climate-related litigation as a risk?", False),
    ("Does Pfizer's 2021 10-K discuss COVID-19 vaccine pricing pressure?", False),
])
def test_figure_questions_are_recognized(q, figure):
    from filing_delta.qa.ask import FIGURE_Q
    assert bool(FIGURE_Q.search(q)) == figure


def test_absence_answer_to_a_figure_question_is_refused(tmp_path, cat):
    t = ask("How much does Weyco's 2023 10-K say it paid per pair of shoes?", ROOT, cat, Recorder(
        tmp_path, provider=Scripted(lambda p: {
            "answerable": True, "answer": "The 10-K doesn't say a price per pair. It does say it buys abroad.",
            "reason": "", "absence": True, "search_terms": [],
            "citations": [{"passage": "P1", "quote": first_sentence(p), "claim": "It buys abroad."}]})))
    assert t["result"]["type"] == "abstain" and t["result"]["reason"].startswith("The filings in scope don't state")
    assert t["absence_guard"]["answer_withheld"]["type"] == "answer"
    # the same answer without the absence flag stands
    t2 = ask("How much does Weyco's 2023 10-K say it paid per pair of shoes?", ROOT, cat, Recorder(
        tmp_path / "b", provider=Scripted(lambda p: {
            "answerable": True, "answer": "It buys abroad.", "reason": "", "absence": False, "search_terms": [],
            "citations": [{"passage": "P1", "quote": first_sentence(p), "claim": "It buys abroad."}]})))
    assert t2["result"]["type"] == "answer"


def test_scope_abstentions_never_call_the_model(tmp_path, cat):
    class Boom:
        def complete(self, request):
            raise AssertionError("model called")
    t = ask("Should I buy Weyco stock?", ROOT, cat, Recorder(tmp_path, provider=Boom()))
    assert t["stage"] == "scope" and t["result"]["type"] == "abstain"


def test_missing_facts_is_an_error_not_an_empty_scope(tmp_path):
    """M10 demo rehearsal: without data/facts the catalog came back empty and every question scoped out."""
    (tmp_path / "data" / "sections").mkdir(parents=True)
    (tmp_path / "data" / "sections" / "results.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="filing-delta facts"):
        load_catalog(tmp_path)


def test_pipeline_source_matches_the_frozen_version():
    """Any edit to a file that decides an answer changes the version; the scored run is only valid for the frozen one."""
    frozen = json.loads((ROOT / "tests" / "golden" / "qa_pipeline.json").read_text(encoding="utf-8"))
    assert pipeline_version() == frozen["pipeline_version"]
