"""One question end to end: scope, retrieve, answer, verify (M6, docs/design/qa.md §2).

Returns a trace: what was scoped and retrieved, the recorded model response, and the final `Answer | Abstain`. Model
calls go through the M4 Recorder (keyed by request hash), so a recorded run replays with no key.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..classify.model import Recorder, model_id
from .answer import Abstain, Answer, Citation, UNVERIFIED, locate, verify
from .index import TOP_K, bm25, changed_spans, query_tokens, rank_changes, units_for
from .prompt import PASSAGE_MAX, SCHEMA, SECTION_LABEL, SYSTEM, filing_label, prompt_version, user_message
from .scope import ALIASES, Filing, scope

EFFORT = "low"
MAX_TOKENS = 4000


def build_request(question: str, passages: list[dict], notes: list[str]) -> dict:
    return {
        "model": model_id(),
        "max_tokens": MAX_TOKENS,
        "system": [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": user_message(question, passages, notes)}],
        "output_config": {"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
    }


def result_json(r: Answer | Abstain) -> dict:
    if isinstance(r, Abstain):
        return {"type": "abstain", "reason": r.reason}
    return {"type": "answer", "text": r.text,
            "citations": [{"accession": c.accession, "section": c.section, "start": c.start, "end": c.end,
                           "quote": c.quote, "claim": c.claim} for c in r.citations]}


def ask(question: str, root: Path, catalog: list[Filing], recorder: Recorder) -> dict:
    trace = {"question": question, "prompt_version": prompt_version(), "model": None, "request_key": None}
    s = scope(question, catalog)
    if s.abstain:
        return {**trace, "stage": "scope", "scope": None, "retrieved": [], "problems": [],
                "result": result_json(Abstain(s.abstain))}
    units, texts = units_for(root, s.filings, s.sections)
    spans = changed_spans(root, s.filings) if s.change else None
    top = rank_changes(question, units, spans, TOP_K) if spans else bm25(query_tokens(question), units, TOP_K)
    by_acc = {f.accession: f for f in s.filings}
    passages = []
    for n, (score, u) in enumerate(top, 1):
        f = by_acc[u.accession]
        passages.append({"id": f"P{n}", "accession": u.accession, "section": u.section, "start": u.start,
                         "end": u.end, "score": score, "heading": u.heading, "text": u.text[:PASSAGE_MAX],
                         "change": spans.get((u.accession, u.section, u.start, u.end)) if spans else None,
                         "filing": filing_label(ALIASES[f.cik][0], f.form, f.fiscal_year, f.fiscal_period,
                                                f.period_end)})
    trace.update(scope={"filings": [f.accession for f in s.filings], "sections": list(s.sections),
                        "change": s.change, "notes": s.notes},
                 retrieved=[{k: p[k] for k in ("id", "accession", "section", "start", "end", "score", "change")}
                            for p in passages])
    if not passages:
        return {**trace, "stage": "retrieve", "problems": [],
                "result": result_json(Abstain("Nothing in the scoped filings matches the question's terms."))}
    response, key = recorder.complete(build_request(question, passages, s.notes))
    trace.update(model=response.get("model"), request_key=key, usage=response.get("usage"),
                 stop_reason=response.get("stop_reason"))
    if response.get("stop_reason") == "refusal":
        return {**trace, "stage": "model", "problems": ["model refused"],
                "result": result_json(Abstain("The model declined to answer."))}
    try:
        out = json.loads(response["text"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return {**trace, "stage": "model", "problems": ["unparseable response"],
                "result": result_json(Abstain(UNVERIFIED))}
    trace["raw"] = out
    if not out.get("answerable"):
        return {**trace, "stage": "model", "problems": [],
                "result": result_json(Abstain("The filings in scope don't answer this. " + (out.get("reason") or "")
                                              .strip()))}
    pid = {p["id"]: p for p in passages}
    cites: list[Citation] = []
    problems: list[str] = []
    for i, c in enumerate(out.get("citations") or [], 1):
        p = pid.get(c.get("passage"))
        loc = locate(c.get("quote") or "", p["start"], p["text"], p["accession"], p["section"],
                     c.get("claim") or "") if p else None
        if loc is None:
            problems.append(f"citation {i}: quote is not an exact substring of {c.get('passage')}")
        else:
            cites.append(loc)
    if problems:
        return {**trace, "stage": "verify", "problems": problems, "result": result_json(Abstain(UNVERIFIED))}
    result, vp = verify(out.get("answer") or "", cites, texts)
    trace.update(stage="verify", problems=vp, result=result_json(result))
    if isinstance(result, Answer):
        used = sorted({(c.accession, c.section) for c in result.citations})
        trace["provenance"] = "; ".join(f"{pid_label(passages, a, sec)}, {SECTION_LABEL[sec]}" for a, sec in used) + \
            ". Item 1A and Item 7 are management's unaudited narrative."
    return trace


def pid_label(passages: list[dict], accession: str, section: str) -> str:
    return next(p["filing"] for p in passages if p["accession"] == accession and p["section"] == section)
