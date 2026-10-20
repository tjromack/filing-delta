"""The QA answer-key jury (M6, FD-DEC 031): two models label all 60 questions from the full scoped sections.

    python tools/qa_jury.py submit            # one Message Batches request per question per juror (needs a key)
    python tools/qa_jury.py collect [--wait]  # results into data/model-cache under the request hash
    python tools/qa_jury.py report            # offline: data/qa/jury.json + agreement summary

Each juror reads the full text of every section in the question's scope: the pipeline's deterministic scoping, never
its retrieval or its answers. It returns a state (answerable, not_answerable, unsure, wrong_filing, reject), exact
quotes from the sections and a short answer. Quotes are mapped to the sentences that contain them, which is the
same sentence-level gold the labeling page produces. The two jurors agree when their states match and, for
answerable, their sentences overlap. Trevor reviews only the disagreements (tools/build_qa_label_app.py review).

Jurors: claude-opus-5-5 and claude-fable-5-1. Neither is the pipeline's answering model (claude-sonnet-5-5), so the
key isn't written by the model it scores.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.classify.model import Recorder, anthropic_client, message_record, request_key  # noqa: E402
from filing_delta.cli import load_env  # noqa: E402
from filing_delta.qa.index import catalog  # noqa: E402
from filing_delta.qa.prompt import SECTION_LABEL, filing_label  # noqa: E402
from filing_delta.qa.scope import ALIASES, scope  # noqa: E402

JURORS = ("claude-opus-5-5", "claude-fable-5-1")
STATE = "data/qa/jury-batches.json"
EFFORT = "medium"
MAX_TOKENS = 16000
STATES = ("answerable", "not_answerable", "unsure", "wrong_filing", "reject")

SYSTEM = """You are building an answer key for questions about U.S. SEC filings. You are shown a question and the \
full text of the filing sections it is about (labeled S1, S2, ...). Your answer key will be used to grade another \
system, so be careful and literal.

Decide exactly one state:
- "answerable": the sections shown contain the answer. Give the shortest quotes that contain it, copied character \
for character from one section each, usually one sentence each. Quote every place needed if the answer needs \
several. Write a short answer in plain words.
- "not_answerable": the sections shown don't contain the answer. This includes requests for investment advice or \
predictions, and questions about a company or period whose filing isn't shown. Searching the text carefully to \
confirm the answer is absent is the job here; don't guess, and don't answer a nearby question instead.
- "wrong_filing": the question names a filing or section that isn't among those shown (for example it compares a \
10-Q with a 10-K and only 10-Qs are shown), so its answer would be in a filing you can't see.
- "unsure": you genuinely can't tell whether the text answers it.
- "reject": the question is ambiguous or badly worded.

Use only the text shown, never outside knowledge. For a question about what changed between two filings, compare \
the two filings' text and quote the new (or dropped) text from the filing where it appears."""

SCHEMA = {
    "type": "object",
    "properties": {
        "state": {"type": "string", "enum": list(STATES)},
        "quotes": {"type": "array", "items": {
            "type": "object", "properties": {"section": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["section", "quote"], "additionalProperties": False}},
        "answer": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["state", "quotes", "answer", "reason"],
    "additionalProperties": False,
}


def items() -> list[dict]:
    cat = catalog(ROOT)
    out = []
    for q in json.loads((ROOT / "tests" / "golden" / "qa_questions.json").read_text(encoding="utf-8"))["questions"]:
        s = scope(q["question"], cat)
        secs = []
        if not s.abstain:
            for f in s.filings:
                for sec in s.sections:
                    if sec in f.sections:
                        secs.append({"key": f"{f.accession}|{sec}", "label": filing_label(
                            ALIASES[f.cik][0], f.form, f.fiscal_year, f.fiscal_period, f.period_end) + " · " +
                            SECTION_LABEL[sec], "text": (ROOT / "data" / "sections" / f.accession / f"{sec}.txt")
                            .read_text(encoding="utf-8")})
        out.append({"id": q["id"], "question": q["question"], "sections": secs})
    return out


def user_message(it: dict) -> str:
    parts = [f"Question: {it['question']}", ""]
    if not it["sections"]:
        parts.append("No filing text is shown for this question: the corpus has no filing matching what it asks "
                     "about, or it asks for advice or a prediction.")
    for n, s in enumerate(it["sections"], 1):
        parts += [f"[S{n}] {s['label']}", s["text"], ""]
    return "\n".join(parts).strip()


def build_request(it: dict, model: str) -> dict:
    return {"model": model, "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": SYSTEM}],
            "messages": [{"role": "user", "content": user_message(it)}],
            "output_config": {"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}}}


# --- sentences: the same splitter as the labeling page, so gold is sentence-level either way -------------------
_SENT = re.compile(r"[.!?;][\"”’)\]]*\s+|\n+")


def sentences(t: str) -> list[tuple[int, int]]:
    out, s = [], 0
    for m in _SENT.finditer(t):
        p = re.match(r"^[.!?;][\"”’)\]]*", m.group(0))
        end = m.start() + (len(p.group(0)) if p else 0)
        if end > s and t[s:end].strip():
            out.append((s, end))
        s = m.end()
    if s < len(t) and t[s:].strip():
        out.append((s, len(t)))
    return out


def find(text: str, quote: str) -> tuple[int, int] | None:
    """Exact first; else whitespace-insensitive (a gold span locates the answer; it isn't a citation)."""
    q = quote.strip()
    if not q:
        return None
    i = text.find(q)
    if i >= 0:
        return i, i + len(q)
    pat = r"\s+".join(re.escape(w) for w in q.split())
    m = re.search(pat, text)
    return (m.start(), m.end()) if m else None


def to_spans(it: dict, out: dict) -> tuple[list[dict], list[str]]:
    spans, misses = [], []
    for c in out.get("quotes") or []:
        try:
            s = it["sections"][int(c["section"].lstrip("Ss")) - 1]
        except (ValueError, IndexError):
            misses.append(f"unknown section {c['section']}")
            continue
        loc = find(s["text"], c["quote"])
        if loc is None:
            misses.append(f"quote not found in {c['section']}: {c['quote'][:60]}")
            continue
        for a, b in sentences(s["text"]):
            if a < loc[1] and loc[0] < b:
                sp = {"key": s["key"], "start": a, "end": b}
                if sp not in spans:
                    spans.append(sp)
    return spans, misses


def submit() -> None:
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    rec = Recorder(ROOT / "data" / "model-cache")
    st = json.loads((ROOT / STATE).read_text(encoding="utf-8")) if (ROOT / STATE).exists() else []
    pending = {k for b in st if not b.get("collected") for k in b["keys"]}
    reqs = []
    for it in items():
        for m in JURORS:
            r = build_request(it, m)
            k = request_key(r)
            if not rec.has(r) and k not in pending:
                reqs.append((k, r))
    print(f"{len(reqs)} jury requests to submit")
    if not reqs:
        return
    client = anthropic_client()
    for m in JURORS:
        chunk = [(k, r) for k, r in reqs if r["model"] == m]
        if not chunk:
            continue
        batch = client.messages.batches.create(requests=[
            Request(custom_id=k, params=MessageCreateParamsNonStreaming(**r)) for k, r in chunk])
        st.append({"id": batch.id, "model": m, "keys": [k for k, _ in chunk], "collected": False,
                   "created": time.strftime("%Y-%m-%dT%H:%M:%S")})
        (ROOT / STATE).write_text(json.dumps(st, indent=1) + "\n", encoding="utf-8")
        print(f"  submitted {batch.id}: {len(chunk)} requests for {m}")


def collect(wait: bool) -> None:
    rec = Recorder(ROOT / "data" / "model-cache")
    client = anthropic_client()
    st = json.loads((ROOT / STATE).read_text(encoding="utf-8"))
    by_key = {request_key(r): r for it in items() for m in JURORS for r in [build_request(it, m)]}
    while True:
        for b in [b for b in st if not b.get("collected")]:
            batch = client.messages.batches.retrieve(b["id"])
            if batch.processing_status != "ended":
                print(f"  {b['id']} {batch.processing_status}: {batch.request_counts.processing} processing", flush=True)
                continue
            kinds = Counter()
            for r in client.messages.batches.results(b["id"]):
                kinds[r.result.type] += 1
                if r.result.type == "succeeded":
                    resp = message_record(r.result.message)
                    resp["via"] = "batch"
                    rec.record(by_key[r.custom_id], resp)
                elif r.result.type == "errored":
                    kinds[f"errored:{r.result.error.type}"] += 1
                    print("   error:", r.custom_id[:12], getattr(r.result.error, "error", r.result.error), flush=True)
            b["collected"], b["results"] = True, dict(kinds)
            (ROOT / STATE).write_text(json.dumps(st, indent=1) + "\n", encoding="utf-8")
            print(f"  {b['id']} ended: {dict(kinds)}", flush=True)
        if not wait or all(b.get("collected") for b in st):
            break
        time.sleep(60)


def report() -> None:
    rec = Recorder(ROOT / "data" / "model-cache", offline=True)
    prices = {"claude-opus-5-5": (2.0, 10.0), "claude-fable-5-1": (5.0, 25.0)}     # batch $/MTok in, out
    rows, usd = [], Counter()
    for it in items():
        row = {"id": it["id"], "question": it["question"], "jurors": {}}
        for m in JURORS:
            resp, _ = rec.complete(build_request(it, m))
            u = resp.get("usage") or {}
            usd[m] += ((u.get("input_tokens") or 0) * prices[m][0] + (u.get("output_tokens") or 0) * prices[m][1]) / 1e6
            if resp.get("stop_reason") == "refusal":
                row["jurors"][m] = {"state": "unsure", "spans": [], "answer": "", "reason": "model refused",
                                    "misses": []}
                continue
            out = json.loads(resp["text"])
            spans, misses = to_spans(it, out)
            if out["state"] == "answerable" and not spans:
                out["state"], out["reason"] = "unsure", "answerable, but no quote could be located: " + out["reason"]
            row["jurors"][m] = {"state": out["state"], "spans": spans, "answer": out["answer"],
                                "reason": out["reason"], "misses": misses}
        a, b = (row["jurors"][m] for m in JURORS)
        overlap = {(s["key"], s["start"]) for s in a["spans"]} & {(s["key"], s["start"]) for s in b["spans"]}
        row["agree"] = a["state"] == b["state"] and (a["state"] != "answerable" or bool(overlap))
        rows.append(row)
    (ROOT / "data" / "qa" / "jury.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n",
                                                   encoding="utf-8")
    agree = sum(r["agree"] for r in rows)
    print(f"agree on {agree}/{len(rows)}; disagreements for Trevor: {len(rows) - agree}")
    for m in JURORS:
        print(f"  {m}: states {dict(Counter(r['jurors'][m]['state'] for r in rows))}, "
              f"unlocated quotes {sum(len(r['jurors'][m]['misses']) for r in rows)}, ${usd[m]:.2f}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_env()
    {"submit": submit, "collect": lambda: collect("--wait" in sys.argv), "report": report}[sys.argv[1]]()


if __name__ == "__main__":
    main()
