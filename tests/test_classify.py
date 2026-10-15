"""M4 classifier stage, offline: a fake provider stands in for the API. No network, no key."""
from __future__ import annotations

import json
import re

import pytest

from filing_delta.classify import prompt as pr
from filing_delta.classify.classify import build_request, classify, verify_evidence
from filing_delta.classify.model import OfflineMiss, Recorder, request_key

ITEM = {
    "id": "X1", "company": "Example Co", "section_label": "10-K Item 1A", "old_date": "2024-12-31",
    "new_date": "2025-12-31", "status": "reworded",
    "old_text": "A cyberattack could disrupt our operations and harm our reputation.",
    "new_text": "In 2025 we experienced a cyberattack that disrupted our operations and harmed our reputation.",
}


class FakeProvider:
    def __init__(self, out: dict | str, stop_reason: str = "end_turn"):
        self.out, self.stop_reason, self.requests = out, stop_reason, []

    def complete(self, request: dict) -> dict:
        self.requests.append(request)
        text = self.out if isinstance(self.out, str) else json.dumps(self.out)
        return {"id": "msg_1", "model": request["model"], "stop_reason": self.stop_reason, "text": text,
                "usage": {"input_tokens": 10, "output_tokens": 5}, "stop_details": None}


def answer(**kw) -> dict:
    return {"label": "material", "code": "realized", "rationale": "The hypothetical attack now happened.",
            "evidence": "In 2025 we experienced a cyberattack", "evidence_side": "new", **kw}


def test_guide_is_the_approved_section_verbatim():
    g = pr.guide_text()
    assert g.startswith("## 2. The labeling guide") and "## 3." not in g
    for code in pr.MATERIAL_CODES + pr.COSMETIC_CODES:
        assert f"`{code}`" in g, code                     # every schema code is defined in the guide
    assert set(re.findall(r"^\| `([a-z_]+)` \|", g, flags=re.M)) == set(pr.MATERIAL_CODES + pr.COSMETIC_CODES)


def test_prompt_version_changes_with_the_guide(monkeypatch):
    v1 = pr.prompt_version()
    monkeypatch.setattr(pr, "guide_text", lambda: "a different guide")
    assert pr.prompt_version() != v1


def test_request_is_keyed_on_its_full_body(tmp_path):
    a, b = build_request(ITEM), build_request({**ITEM, "new_text": ITEM["new_text"] + " More."})
    assert request_key(a) == request_key(json.loads(json.dumps(a)))
    assert request_key(a) != request_key(b)


def test_model_id_comes_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
    assert build_request(ITEM)["model"] == "claude-haiku-5-5"
    monkeypatch.delenv("ANTHROPIC_MODEL")
    assert build_request(ITEM)["model"] == "claude-sonnet-5-5"


def test_recorded_response_is_replayed_without_calling_the_provider(tmp_path):
    fake = FakeProvider(answer())
    first = classify(ITEM, Recorder(tmp_path, provider=fake))
    again = Recorder(tmp_path, offline=True)              # no provider at all
    second = classify(ITEM, again)
    assert len(fake.requests) == 1 and again.hits == 1
    assert (first["label"], first["code"], first["outcome"]) == (second["label"], second["code"], "ok")


def test_offline_miss_fails_loudly(tmp_path):
    with pytest.raises(OfflineMiss):
        classify(ITEM, Recorder(tmp_path, offline=True))


def test_evidence_must_be_an_exact_substring(tmp_path):
    r = classify(ITEM, Recorder(tmp_path, provider=FakeProvider(answer(evidence="we suffered a cyber attack"))))
    assert r["outcome"] == "unverified" and r["evidence_ok"] is False and r["label"] == "material"
    assert verify_evidence(answer(), ITEM) is True
    assert verify_evidence(answer(evidence_side="old"), ITEM) is False      # right words, wrong side


def test_code_must_match_label(tmp_path):
    r = classify(ITEM, Recorder(tmp_path, provider=FakeProvider(answer(code="rewording"))))
    assert r["outcome"] == "code_mismatch"


def test_formatting_only_uses_the_rule_and_no_model(tmp_path):
    fake = FakeProvider(answer())
    r = classify({**ITEM, "formatting_only": True}, Recorder(tmp_path, provider=fake))
    assert (r["source"], r["label"], r["code"]) == ("rule", "cosmetic", "formatting") and fake.requests == []


def test_refusal_and_garbage_are_their_own_outcomes(tmp_path):
    r = classify(ITEM, Recorder(tmp_path / "a", provider=FakeProvider("", stop_reason="refusal")))
    assert r["outcome"] == "refused" and r["label"] is None
    r = classify(ITEM, Recorder(tmp_path / "b", provider=FakeProvider("not json")))
    assert r["outcome"] == "unparseable"


def test_prompt_shows_the_inline_diff_and_context():
    msg = pr.user_message({**ITEM, "context": None})
    assert "[-could disrupt-]" in msg or "[-A" in msg
    added = {**ITEM, "status": "added", "old_text": "", "context": {"side": "old", "similarity": 0.3, "text": "Prior."}}
    m2 = pr.user_message(added)
    assert "OLD text:" not in m2 and "Closest OLD paragraph" in m2 and "Inline diff" not in m2
