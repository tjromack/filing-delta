"""Classify every Item 1A change in the corpus with the frozen prompt (M4 full run), via the Message Batches API.

    python tools/classify_corpus.py submit            # batch every unrecorded request for $ANTHROPIC_MODEL (needs a key)
    python tools/classify_corpus.py collect [--wait]  # fetch ended batches into data/model-cache (needs a key)
    python tools/classify_corpus.py report [--compare <model>]   # offline: replays recorded responses only

The population is the M4 sampling frame (tools/materiality_sample.py): every changed unit of every full -> full
10-K Item 1A and 10-Q Part II Item 1A pair. Requests are byte-identical to the synchronous path (build_request), and
each batch result is written to the same request-hash cache, so `report` replays everything with no key. Batch ids
are kept in data/classify/batches.json, so an interrupted run resumes instead of paying twice.

`report` writes data/classify/corpus-<model>.jsonl and docs/materiality-corpus.md: label distribution by stratum,
outcome counts, measured cost, and (with --compare) the agreement between two models. Agreement between two models
is a consistency figure, not an accuracy figure; accuracy is the blind test set (docs/materiality-eval-test.md).
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from filing_delta.classify.classify import EFFORT, build_request, classify  # noqa: E402
from filing_delta.classify.context import restatement_context  # noqa: E402
from filing_delta.classify.model import Recorder, anthropic_client, message_record, model_id, request_key  # noqa: E402
from filing_delta.classify.prompt import prompt_version  # noqa: E402
from filing_delta.cli import load_env  # noqa: E402
from materiality_sample import LABEL, QUOTA, stratum  # noqa: E402
from run_materiality import LABEL_SECTION, PRICES  # noqa: E402

CACHE = ROOT / "data" / "model-cache"
STATE = ROOT / "data" / "classify" / "batches.json"
CHUNK_REQUESTS, CHUNK_BYTES = 2000, 100_000_000   # well under the 100,000-request / 256 MB batch limits
BATCH_DISCOUNT = 0.5


def corpus_items() -> list[dict]:
    """Every in-frame change as a classifier item, in file/op order. Deterministic."""
    sec = ROOT / "data" / "sections"
    items = []
    for f in sorted(glob.glob(str(ROOT / "data" / "diffs" / "*.json"))):
        rec = json.loads(Path(f).read_text(encoding="utf-8"))
        if rec["state"] != "full -> full" or rec["section"] not in LABEL:
            continue
        to = (sec / rec["old"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
        tn = (sec / rec["new"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
        for k, op in enumerate(rec["ops"]):
            s = stratum(op)
            if s is None:
                continue
            old_text = "\n\n".join(to[rec["old_units"][i][1]:rec["old_units"][i][2]] for i in op["old"])
            new_text = "\n\n".join(tn[rec["new_units"][j][1]:rec["new_units"][j][2]] for j in op["new"])
            items.append({"id": f"{Path(f).stem}#{k}", "stratum": s, "section": rec["section"],
                          "company": rec["company"], "section_label": LABEL_SECTION[rec["section"]],
                          "old_date": rec["old"]["report_date"], "new_date": rec["new"]["report_date"],
                          "status": op["status"], "old_text": old_text, "new_text": new_text,
                          "context": restatement_context(rec, op, to, tn),
                          "formatting_only": s == "formatting_only"})
    return items


def check_frozen() -> None:
    frozen = json.loads((ROOT / "tests" / "golden" / "materiality_prompt.json").read_text(encoding="utf-8"))
    if prompt_version() != frozen["prompt_version"]:
        raise SystemExit(f"prompt version {prompt_version()} != frozen {frozen['prompt_version']} (FD-DEC 022).")


def load_state() -> list[dict]:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else []


def save_state(state: list[dict]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")


def submit() -> None:
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    rec = Recorder(CACHE)
    state = load_state()
    pending = {k for b in state if not b.get("collected") for k in b["keys"]}
    todo, seen = [], set()
    for it in corpus_items():
        if it["formatting_only"]:
            continue
        req = build_request(it)
        key = request_key(req)
        if key in seen or key in pending or rec.has(req):
            continue
        seen.add(key)
        todo.append((key, req))
    print(f"{model_id()}: {len(todo)} requests to submit ({len(pending)} already in open batches)")
    client = anthropic_client()
    chunk, size = [], 0
    for n, (key, req) in enumerate(todo, 1):
        chunk.append((key, req))
        size += len(json.dumps(req, ensure_ascii=False).encode("utf-8"))
        if len(chunk) == CHUNK_REQUESTS or size > CHUNK_BYTES or n == len(todo):
            batch = client.messages.batches.create(requests=[
                Request(custom_id=k, params=MessageCreateParamsNonStreaming(**r)) for k, r in chunk])
            state.append({"id": batch.id, "model": model_id(), "prompt_version": prompt_version(),
                          "keys": [k for k, _ in chunk], "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                          "collected": False})
            save_state(state)   # after every batch, so an interruption never loses a paid-for batch id
            print(f"  submitted {batch.id}: {len(chunk)} requests ({size / 1e6:.1f} MB)", flush=True)
            chunk, size = [], 0


def collect(wait: bool) -> None:
    rec = Recorder(CACHE)
    client = anthropic_client()
    state = load_state()
    requests = None
    while True:
        open_ = [b for b in state if not b.get("collected")]
        for b in open_:
            batch = client.messages.batches.retrieve(b["id"])
            if batch.processing_status != "ended":
                c = batch.request_counts
                print(f"  {b['id']} {batch.processing_status}: {c.processing} processing, {c.succeeded} succeeded",
                      flush=True)
                continue
            if requests is None:   # key -> request, to store each result beside the exact request that produced it
                saved = os.environ.get("ANTHROPIC_MODEL")
                requests = {}
                for m in {x["model"] for x in state}:
                    os.environ["ANTHROPIC_MODEL"] = m
                    for it in corpus_items():
                        if not it["formatting_only"]:
                            req = build_request(it)
                            requests[request_key(req)] = req
                if saved is None:
                    os.environ.pop("ANTHROPIC_MODEL", None)
                else:
                    os.environ["ANTHROPIC_MODEL"] = saved
            kinds = Counter()
            for r in client.messages.batches.results(b["id"]):
                kinds[r.result.type] += 1
                if r.result.type == "succeeded":
                    resp = message_record(r.result.message)
                    resp["via"] = "batch"
                    rec.record(requests[r.custom_id], resp)
                elif r.result.type == "errored":
                    kinds[f"errored:{r.result.error.type}"] += 1
            b["collected"], b["results"] = True, dict(kinds)
            save_state(state)
            print(f"  {b['id']} ended: {dict(kinds)}", flush=True)
        if not wait or all(b.get("collected") for b in state):
            break
        time.sleep(60)
    left = [b["id"] for b in state if not b.get("collected")]
    print("all batches collected" if not left else f"still open: {left}")


def kappa(pairs: list[tuple[str, str]]) -> float:
    n = len(pairs)
    po = sum(a == b for a, b in pairs) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb[k] for k in ca) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def run_model(items: list[dict], model: str) -> list[dict]:
    os.environ["ANTHROPIC_MODEL"] = model
    rec = Recorder(CACHE, offline=True)
    out = []
    for it in items:
        r = classify(it, rec)
        r.update({"id": it["id"], "stratum": it["stratum"], "section": it["section"], "company": it["company"]})
        out.append(r)
    dest = ROOT / "data" / "classify" / f"corpus-{model}.jsonl"
    dest.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    return out


def cost_of(results: list[dict], model: str) -> tuple[float, int]:
    """Measured usage at list price, batch-discounted for batch results. Only responses recorded by a batch count:
    the few the labeled sets already paid for synchronously are reused, not re-bought."""
    pi, po, pcr, pcw = PRICES.get(model, (float("nan"),) * 4)
    usd, n, seen = 0.0, 0, set()
    for r in results:
        if r["source"] != "model" or not r.get("request_key") or r["request_key"] in seen:
            continue                      # identical changes share one request, paid for once
        seen.add(r["request_key"])
        p = CACHE / r["request_key"][:2] / f"{r['request_key']}.json"
        resp = json.loads(p.read_text(encoding="utf-8"))["response"]
        if resp.get("via") != "batch":
            continue
        u = resp["usage"]
        usd += BATCH_DISCOUNT * ((u.get("input_tokens") or 0) * pi + (u.get("output_tokens") or 0) * po
                                 + (u.get("cache_read_input_tokens") or 0) * pcr
                                 + (u.get("cache_creation_input_tokens") or 0) * pcw) / 1e6
        n += 1
    return usd, n


def report(compare: str | None) -> None:
    check_frozen()
    items = corpus_items()
    models = [model_id()] + ([compare] if compare else [])
    res = {m: run_model(items, m) for m in models}
    olds = sorted(it["old_date"] for it in items)
    news = sorted(it["new_date"] for it in items)
    strata = Counter(it["stratum"] for it in items)
    sec = Counter(it["section"] for it in items)
    lines = ["# Materiality: full corpus", "",
             f"Every changed unit in the Item 1A frame: **{len(items):,} changes** across "
             f"{len({it['company'] for it in items})} companies (10-K Item 1A: {sec['10K_1A']:,}; 10-Q Part II Item "
             f"1A: {sec['10Q_P2_1A']:,}), from filing pairs whose report dates run {olds[0]} to {news[-1]}. Prompt "
             f"version `{prompt_version()}` (frozen, FD-DEC 022) · effort `{EFFORT}` · Message Batches API.", "",
             "Generated by `tools/classify_corpus.py report"
             + (f" --compare {compare}" if compare else "") + "`, which replays recorded responses only (no key). "
             "These labels describe how each change was classified, not what it means for the company. Their measured "
             "accuracy is the blind test set (`docs/materiality-eval-test.md`); nothing on this page is an accuracy "
             "figure.", ""]
    for m in models:
        rs = res[m]
        oc = Counter(r["outcome"] for r in rs)
        usd, nb = cost_of(rs, m)
        distinct = len({r["request_key"] for r in rs if r["source"] == "model"})
        lab = Counter(r["label"] for r in rs if r["outcome"] == "ok")
        lines += [f"## `{m}`", "",
                  f"- Outcomes: {dict(sorted(oc.items()))} (rule path: {sum(r['source'] == 'rule' for r in rs)}).",
                  f"- Labels (outcome `ok`): {dict(sorted(lab.items()))}.",
                  f"- Measured cost of this run: **${usd:.2f}** for {nb:,} batch responses (list price, 50% batch "
                  f"discount); {distinct - nb} responses were reused from earlier recorded runs. The "
                  f"{sum(r['source'] == 'model' for r in rs):,} model-path changes need {distinct:,} distinct requests "
                  "(byte-identical changes share one).", "",
                  "| stratum | changes | material | cosmetic | unsure | not answered |", "|---|---|---|---|---|---|"]
        for s in QUOTA:
            sr = [r for r in rs if r["stratum"] == s]
            c = Counter(r["label"] if r["outcome"] == "ok" else "x" for r in sr)
            lines.append(f"| {s} | {strata[s]:,} | {c['material']:,} | {c['cosmetic']:,} | {c['unsure']:,} | "
                         f"{c['x']:,} |")
        lines.append("")
    if compare:
        a, b = models
        ra, rb = {r["id"]: r for r in res[a]}, {r["id"]: r for r in res[b]}
        both = [i["id"] for i in items if ra[i["id"]]["source"] == "model" and ra[i["id"]]["outcome"] == "ok"
                and rb[i["id"]]["outcome"] == "ok"]
        pairs = [(ra[i]["label"], rb[i]["label"]) for i in both]
        cm = Counter(pairs)
        agree = sum(x == y for x, y in pairs)
        labs = ("material", "cosmetic", "unsure")
        lines += [f"## Agreement: `{a}` vs `{b}`", "",
                  f"Model-path changes both models answered (`ok`): **{len(pairs):,}**. The "
                  f"{sum(r['source'] == 'rule' for r in res[a]):,} formatting-only changes take the rule path and "
                  "are identical by construction, so they are left out.", "",
                  f"- Raw agreement: **{agree:,}/{len(pairs):,}** ({agree / len(pairs):.1%}); Cohen's kappa "
                  f"**{kappa(pairs):.2f}**.", "",
                  f"| {a} \\ {b} | " + " | ".join(labs) + " |", "|---|---|---|---|"]
        for x in labs:
            lines.append(f"| **{x}** | " + " | ".join(f"{cm[(x, y)]:,}" for y in labs) + " |")
        lines += ["", "| stratum | both answered | agree | agreement |", "|---|---|---|---|"]
        by = defaultdict(list)
        for i in both:
            by[ra[i]["stratum"]].append(ra[i]["label"] == rb[i]["label"])
        for s in QUOTA:
            if by[s]:
                lines.append(f"| {s} | {len(by[s]):,} | {sum(by[s]):,} | {sum(by[s]) / len(by[s]):.0%} |")
        lines.append("")
    (ROOT / "docs" / "materiality-corpus.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print("\n".join(lines))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_env()
    cmd = sys.argv[1]
    check_frozen()
    if cmd == "submit":
        submit()
    elif cmd == "collect":
        collect("--wait" in sys.argv)
    elif cmd == "report":
        report(sys.argv[sys.argv.index("--compare") + 1] if "--compare" in sys.argv else None)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
