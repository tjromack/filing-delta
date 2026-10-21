"""One question end to end: scope, retrieve, answer, verify (M6, docs/design/qa.md §2).

Returns a trace: what was scoped and retrieved, the recorded model response, and the final `Answer | Abstain`. Model
calls go through the M4 Recorder (keyed by request hash), so a recorded run replays with no key.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..classify.model import Recorder, model_id
from .answer import Abstain, Answer, Citation, UNVERIFIED, locate, verify
from .index import TOP_K, bm25, changed_spans, query_tokens, rank_changes, tokens, units_for
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
    first = answer_from(question, passages, s.notes, texts, recorder)
    trace.update(first)
    # v4 (FD-DEC 038): an answer that claims something is absent ("doesn't say X") is only as good as the search
    # behind it, and filings often name a thing in other words. So before an absence answer stands, search again:
    # for the other phrasings the model listed for what it didn't find, and for question words that occur in the
    # filings but in none of the retrieved passages. Add the best new passages and ask once more.
    raw = first.get("raw") or {}
    if first["result"]["type"] == "answer" and raw.get("absence"):
        alt = [t for phrase in (raw.get("search_terms") or [])[:6] for t in tokens(phrase)]
        missing = sorted(set(missed_terms(question, units, top)) | set(alt))
        if missing:
            seen = {(u.accession, u.section, u.start) for _, u in top}
            pool = [u for u in units if (u.accession, u.section, u.start) not in seen
                    and set(tokens(u.heading + " " + u.text)) & set(missing)]
            extra = bm25(alt + query_tokens(question), pool, EXTRA_K)
            if extra:
                more = []
                for n, (score, u) in enumerate(extra, len(passages) + 1):
                    f = by_acc[u.accession]
                    more.append({"id": f"P{n}", "accession": u.accession, "section": u.section, "start": u.start,
                                 "end": u.end, "score": score, "heading": u.heading, "text": u.text[:PASSAGE_MAX],
                                 "change": spans.get((u.accession, u.section, u.start, u.end)) if spans else None,
                                 "filing": filing_label(ALIASES[f.cik][0], f.form, f.fiscal_year, f.fiscal_period,
                                                        f.period_end)})
                note = (f"Passages {more[0]['id']}–{more[-1]['id']} were added by a second search for other wording "
                        f"of what was asked ({', '.join((raw.get('search_terms') or [])[:6]) or ', '.join(missing)}). "
                        "Check them before saying the filing doesn't say something.")
                second = answer_from(question, passages + more, s.notes + [note], texts, recorder)
                trace["second_pass"] = {"missed_terms": missing, "search_terms": raw.get("search_terms") or [],
                                        "first": {k: first.get(k) for k in (
                    "stage", "result", "request_key", "usage", "model")},
                    "added": [{k: p[k] for k in ("id", "accession", "section", "start", "end", "score", "heading")}
                              for p in more]}
                for k in ("raw", "provenance", "problems", "stop_reason"):
                    trace.pop(k, None)
                trace.update(second)
                trace["retrieved"] = trace["retrieved"] + trace["second_pass"]["added"]
    # FD-DEC 033's boundary, enforced here rather than left to the model (FD-DEC 038): a question asking for a
    # specific figure that the filing doesn't state gets a refusal, never "doesn't say X; does say Y".
    if trace["result"]["type"] == "answer" and (trace.get("raw") or {}).get("absence") and FIGURE_Q.search(question):
        first_sentence = trace["result"]["text"].split(". ")[0].rstrip(".") + "."
        trace["absence_guard"] = {"answer_withheld": trace["result"]}
        trace["stage"] = "absence_guard"
        trace["result"] = result_json(Abstain("The filings in scope don't state this figure. " + first_sentence))
        trace.pop("provenance", None)
    return trace


EXTRA_K = 4
# Questions that ask for a specific figure: how much / how many, or a price, amount, salary, bonus, units, breakeven.
FIGURE_Q = re.compile(r"\bhow\s+(?:much|many)\b|\b(?:price|amount|salary|salaries|bonus(?:es)?|units?|unit\s+sales|"
                      r"breakeven|break-even|spend|spent)\b", re.I)


def missed_terms(question: str, units: list, top: list) -> list[str]:
    """Question words (stemmed) that occur somewhere in the scoped filings but in none of the retrieved passages."""
    q = set(query_tokens(question))
    in_scope = set()
    for u in units:
        in_scope |= q & set(tokens(u.heading + " " + u.text))
    retrieved = set()
    for _, u in top:
        retrieved |= set(tokens(u.heading + " " + u.text))
    return sorted(in_scope - retrieved)


def answer_from(question: str, passages: list[dict], notes: list[str], texts: dict, recorder: Recorder) -> dict:
    """One model call over the given passages, then exact-substring verification. Returns trace fields."""
    response, key = recorder.complete(build_request(question, passages, notes))
    out_t = {"model": response.get("model"), "request_key": key, "usage": response.get("usage"),
             "stop_reason": response.get("stop_reason")}
    if response.get("stop_reason") == "refusal":
        return {**out_t, "stage": "model", "problems": ["model refused"],
                "result": result_json(Abstain("The model declined to answer."))}
    try:
        out = json.loads(response["text"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return {**out_t, "stage": "model", "problems": ["unparseable response"],
                "result": result_json(Abstain(UNVERIFIED))}
    out_t["raw"] = out
    if not out.get("answerable"):
        return {**out_t, "stage": "model", "problems": [],
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
        return {**out_t, "stage": "verify", "problems": problems, "result": result_json(Abstain(UNVERIFIED))}
    result, vp = verify(out.get("answer") or "", cites, texts)
    out_t.update(stage="verify", problems=vp, result=result_json(result))
    if isinstance(result, Answer):
        used = sorted({(c.accession, c.section) for c in result.citations})
        out_t["provenance"] = "; ".join(f"{pid_label(passages, a, sec)}, {SECTION_LABEL[sec]}" for a, sec in used) + \
            ". Item 1A and Item 7 are management's unaudited narrative."
    return out_t


def pid_label(passages: list[dict], accession: str, section: str) -> str:
    return next(p["filing"] for p in passages if p["accession"] == accession and p["section"] == section)
