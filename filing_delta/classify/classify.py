"""Classify one Item 1A change as material / cosmetic (M4). A separate stage: it reads diff output, never changes it.

Paths:
- rule: a `formatting_only` change (case/punctuation only, an M3 fact) is cosmetic/formatting with no model call.
  Its accuracy is measured on the labeled formatting-only items like any other path.
- model: the guide-based prompt, structured JSON output, and an evidence quote verified by exact substring match.
  A label whose evidence fails verification is recorded as `unverified`, not accepted.
"""
from __future__ import annotations

import json

from .model import Recorder, model_id
from .prompt import COSMETIC_CODES, MATERIAL_CODES, SCHEMA, prompt_version, system_prompt, user_message

EFFORT = "low"           # classification; measured on the dev set before any test run
MAX_TOKENS = 4000


def build_request(item: dict) -> dict:
    return {
        "model": model_id(),
        "max_tokens": MAX_TOKENS,
        "system": [{"type": "text", "text": system_prompt(), "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user_message(item)}],
        "output_config": {"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
    }


def verify_evidence(out: dict, item: dict) -> bool:
    ev = (out.get("evidence") or "").strip()
    if len(ev.split()) < 2:
        return False
    side = item["old_text"] if out.get("evidence_side") == "old" else item["new_text"]
    return bool(side) and ev in side


def classify(item: dict, recorder: Recorder) -> dict:
    base = {"id": item.get("id"), "prompt_version": prompt_version()}
    if item.get("formatting_only"):
        return {**base, "source": "rule", "outcome": "ok", "label": "cosmetic", "code": "formatting",
                "rationale": "Only case or punctuation changed (M3 formatting_only fact).", "evidence": None,
                "evidence_ok": None, "model": None, "request_key": None}
    request = build_request(item)
    response, key = recorder.complete(request)
    rec = {**base, "source": "model", "model": response.get("model"), "request_key": key,
           "stop_reason": response.get("stop_reason"), "usage": response.get("usage")}
    if response.get("stop_reason") == "refusal":
        return {**rec, "outcome": "refused", "label": None, "code": None, "rationale": None, "evidence": None,
                "evidence_ok": None, "stop_details": response.get("stop_details")}
    try:
        out = json.loads(response["text"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return {**rec, "outcome": "unparseable", "label": None, "code": None, "rationale": None, "evidence": None,
                "evidence_ok": None}
    code_ok = (out["label"] == "material" and out["code"] in MATERIAL_CODES) or \
              (out["label"] == "cosmetic" and out["code"] in COSMETIC_CODES) or out["label"] == "unsure"
    ok = verify_evidence(out, item)
    return {**rec, "outcome": "ok" if ok and code_ok else ("unverified" if not ok else "code_mismatch"),
            "label": out["label"], "code": out["code"], "rationale": out["rationale"], "evidence": out["evidence"],
            "evidence_side": out.get("evidence_side"), "evidence_ok": ok}
