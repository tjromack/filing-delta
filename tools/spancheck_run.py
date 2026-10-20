"""M7: score the recorded M6 QA run with spancheck (PyPI, pinned), plus a timed re-run for latency.

    python tools/spancheck_run.py latency            # live: re-runs the 60 into a separate cache, timing each (≈$0.35)
    python tools/spancheck_run.py score [--offline]  # spancheck over the scored run; the judge's calls are recorded

The scored run is data/qa/run.jsonl from tools/run_qa.py (pipeline v2, FD-DEC 033). Each trace becomes a spancheck
Output: the answer or abstention (explicit `abstained` flag), the retrieved passages as `contexts`, each citation as
{span, source_id}, and a `sources` map from source_id to the retrieved passage it was quoted from, so provenance is
checked against that passage only. Graders: spancheck's deterministic set (abstention, groundedness, PII, citation
accuracy with lexical support) and the opt-in judge, Opus 5.5, for citation support and answer groundedness. The judge
goes through the project's recorder, so every verdict replays with no key. Writes data/qa/spancheck-audit.json and
docs/spancheck-report.md.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from spancheck import Case, evaluate  # noqa: E402
from spancheck import graders as G  # noqa: E402
from spancheck.core import GradeResult  # noqa: E402
from spancheck.judge import judge_entailment, judge_support, llm_judge  # noqa: E402
from spancheck.span import citation_accuracy, verify_citation  # noqa: E402

from filing_delta.classify.model import Recorder  # noqa: E402
from filing_delta.cli import load_env  # noqa: E402
from filing_delta.qa.ask import ask  # noqa: E402
from filing_delta.qa.index import catalog  # noqa: E402
from filing_delta.qa.prompt import CHANGE_LABEL, SECTION_LABEL, filing_label  # noqa: E402
from filing_delta.qa.scope import ALIASES  # noqa: E402

JUDGE = "claude-opus-5-5"            # not the answering model (claude-sonnet-5-5)
SONNET = (2.0, 10.0, 0.20, 2.50)     # $/MTok in, out, cache read, cache write
OPUS = (4.0, 20.0)
QA = ROOT / "data" / "qa"


def load(name: str) -> dict:
    return json.loads((ROOT / "tests" / "golden" / name).read_text(encoding="utf-8"))


def cache_record(key: str | None, cache: Path) -> dict:
    if not key:
        return {}
    p = cache / key[:2] / f"{key}.json"
    return json.loads(p.read_text(encoding="utf-8"))["response"] if p.exists() else {}


def latency() -> None:
    """A second, timed pass of the frozen pipeline into its own cache. The scored run stays untouched; this pass
    measures latency and how stable the answers are from run to run."""
    load_env()
    qs = sorted(load("qa_questions.json")["questions"], key=lambda q: q["id"])
    scored = {json.loads(l)["id"]: json.loads(l) for l in (QA / "run.jsonl").read_text(encoding="utf-8").splitlines()}
    rec = Recorder(ROOT / "data" / "model-cache-latency")
    cat = catalog(ROOT)
    rows = []
    for q in qs:
        t = time.perf_counter()
        tr = ask(q["question"], ROOT, cat, rec)
        total = round((time.perf_counter() - t) * 1000, 1)
        model_ms = cache_record(tr.get("request_key"), ROOT / "data" / "model-cache-latency").get("latency_ms")
        s = scored[q["id"]]["result"]
        rows.append({"id": q["id"], "total_ms": total, "model_ms": model_ms, "result": tr["result"]["type"],
                     "same_type_as_scored": tr["result"]["type"] == s["type"],
                     "same_citations_as_scored": tr["result"].get("citations") == s.get("citations")})
        print(f"{q['id']} {total:8.0f} ms  {tr['result']['type']:7} same={rows[-1]['same_type_as_scored']}", flush=True)
    (QA / "latency.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


class RecordedJudge:
    """spancheck's provider seam (`provider(prompt) -> text`), through the recorder: replays with no key."""

    def __init__(self, offline: bool):
        self.rec = Recorder(ROOT / "data" / "model-cache", offline=offline)
        self.model = JUDGE
        self.usd = 0.0
        self.calls = 0

    def __call__(self, prompt: str) -> str:
        resp, _ = self.rec.complete({"model": JUDGE, "max_tokens": 4000, "output_config": {"effort": "low"},
                                     "messages": [{"role": "user", "content": prompt}]})
        u = resp.get("usage") or {}
        self.usd += ((u.get("input_tokens") or 0) * OPUS[0] + (u.get("output_tokens") or 0) * OPUS[1]) / 1e6
        self.calls += 1
        return resp.get("text") or ""


def entailed_by_citations(provider, name="answer_entailed_by_citations", threshold=0.5):
    """Is the whole answer entailed by the text it cites (all its quotes together)? Not by everything retrieved:
    only the cited spans. Built on spancheck's own judge_entailment and versioned prompt."""
    def g(case, output):
        if output.abstained:
            return GradeResult(name, 1.0, True, "abstained (nothing to judge)")
        # Each quote with the label that travels with every citation in the pipeline's output: which filing and
        # section it's from, and the diff's finding for change questions. Without it a judge can't confirm
        # "Pfizer's 2023 10-K says ..." or "... added in 2021" even when the quote is exactly right.
        premise = " \n ".join(f"[{c.get('label', '')}] {c['span']}" for c in output.citations)
        v = judge_entailment(output.answer, premise, provider=provider, model=JUDGE)
        return GradeResult(name, round(v["score"], 3), v["score"] >= threshold, v["reason"])
    return g


def outputs(run_file: str = "run.jsonl") -> tuple[list, dict]:
    """Cases and Outputs from a recorded run. For the dev slice there's no key: each case is marked answerable as
    the pipeline answered it, so only citation and grounding graders mean anything there."""
    dev = run_file != "run.jsonl"
    qs = {q["id"]: q for q in load("qa_questions.json")["questions"]}
    key = {k["id"]: k for k in load("qa_key.json")["key"]}
    lat = {}
    if (QA / "latency.jsonl").exists():
        lat = {json.loads(l)["id"]: json.loads(l) for l in (QA / "latency.jsonl").read_text(encoding="utf-8").splitlines()}
    texts: dict[str, str] = {}

    def section(acc: str, sec: str) -> str:
        k = f"{acc}|{sec}"
        if k not in texts:
            texts[k] = (ROOT / "data" / "sections" / acc / f"{sec}.txt").read_text(encoding="utf-8")
        return texts[k]

    by_acc = {f.accession: f for f in catalog(ROOT)}
    cases, outs = [], {}
    for n, line in enumerate((QA / run_file).read_text(encoding="utf-8").splitlines(), 1):
        t = json.loads(line)
        if dev:
            t["id"] = f"DEV{n:02d}"
        qid, r = t["id"], t["result"]
        contexts, sources = [], {}
        for p in t["retrieved"]:
            ptext = section(p["accession"], p["section"])[p["start"]:p["end"]]
            contexts.append(ptext)
            sources[f"{p['accession']}|{p['section']}|{p['start']}-{p['end']}"] = ptext
        cites = []
        for c in r.get("citations") or []:
            src = next((sid for sid in sources if sid.startswith(f"{c['accession']}|{c['section']}|")
                        and int(sid.rsplit("|", 1)[1].split("-")[0]) <= c["start"]
                        and c["end"] <= int(sid.rsplit("-", 1)[1])), None)
            p = next((p for p in t["retrieved"] if src == f"{p['accession']}|{p['section']}|{p['start']}-{p['end']}"), {})
            f = by_acc.get(c["accession"])
            label = (filing_label(ALIASES[f.cik][0], f.form, f.fiscal_year, f.fiscal_period, f.period_end)
                     + " · " + SECTION_LABEL[c["section"]]) if f else ""
            if p.get("change"):
                label += " · " + CHANGE_LABEL[p["change"]]
            cite = {"span": c["quote"], "source_id": src, "label": label}
            if c.get("claim"):                       # v3: the citation names the claim it supports
                cite["claim"] = c["claim"]
            cites.append(cite)
        u = t.get("usage") or {}
        cost = ((u.get("input_tokens") or 0) * SONNET[0] + (u.get("output_tokens") or 0) * SONNET[1]
                + (u.get("cache_read_input_tokens") or 0) * SONNET[2]
                + (u.get("cache_creation_input_tokens") or 0) * SONNET[3]) / 1e6
        outs[qid] = {"answer": r.get("text") or r.get("reason") or "", "abstained": r["type"] == "abstain",
                     "contexts": contexts, "citations": cites, "sources": sources,
                     "usage": {"input_tokens": u.get("input_tokens") or 0, "output_tokens": u.get("output_tokens") or 0,
                               "cost_usd": round(cost, 6)},
                     "latency_ms": (lat.get(qid) or {}).get("total_ms"), "stage": t["stage"]}
        if dev:
            cases.append(Case(qid, qid, category="dev", meta={"answerable": r["type"] == "answer", "author": "dev",
                                                              "question": t["question"]}))
            continue
        cases.append(Case(qid, qid, category=key[qid]["state"],
                          meta={"answerable": key[qid]["state"] == "answerable", "author": qs[qid]["author"],
                                "question": qs[qid]["question"], "key_provenance": key[qid]["provenance"]}))
    return sorted(cases, key=lambda c: c.id), outs


def score(offline: bool) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_env()
    cases, outs = outputs()
    judge = RecordedJudge(offline)
    graders = [G.abstention_correct(), G.groundedness(), G.no_pii(),
               citation_accuracy(claim_split=True),
               citation_accuracy(name="citation_accuracy_judged", claim_split=True,
                                 support_fn=judge_support(provider=judge, model=JUDGE)),
               llm_judge(provider=judge, model=JUDGE, name="groundedness_judged"),
               entailed_by_citations(judge)]
    run = evaluate(cases, lambda qid: {k: v for k, v in outs[qid].items() if k != "stage"}, graders=graders)
    # latency: evaluate() times this replay (microseconds); the real figures come from the timed re-run
    for cr in run.results:
        cr.output.latency_ms = outs[cr.case_id]["latency_ms"]
    audit = run.audit_log(str(QA / "spancheck-audit.json"))
    by_g = run.scorecard().by_grader()
    cl = run.cost_latency()
    # per-citation: lexical vs judged support, side by side
    rows, dis = [], []
    for cr in run.results:
        o = cr.output
        if o.abstained:
            continue
        for c in o.citations:
            lex = verify_citation(c, o.contexts, o.answer, sources=o.sources, claim_split=True)
            jud = verify_citation(c, o.contexts, o.answer, sources=o.sources, claim_split=True,
                                  support_fn=judge_support(provider=judge, model=JUDGE))
            rows.append((cr.case_id, lex, jud))
            if lex.claim_supported != jud.claim_supported:
                dis.append((cr.case_id, c["span"], lex, jud))
    prov_ok = sum(l.span_found for _, l, _ in rows)
    lines = ["# spancheck report (M7)", "",
             f"`spancheck` {__import__('spancheck').__version__} (PyPI, pinned) scoring the recorded M6 run of pipeline "
             f"`{load('qa_pipeline.json')['pipeline_version']}` on the 60-question set. Coverage: 10-K Item 1A and Item 7 for "
             "fiscal 2018–2025, and 10-Q Part I Item 2 and Part II Item 1A filed January 2025 to September 2026, for 11 "
             "companies. Generated by `tools/spancheck_run.py score`; `--offline` reproduces it from recorded responses, "
             "judge verdicts included. The full per-case audit log is `data/qa/spancheck-audit.json`.", "",
             "**The answer key is model-built** (FD-DEC 031): two jurors agreed on 58/60, and Trevor decided 2. "
             f"The judge is `{JUDGE}`, not the answering model, and is uncalibrated against human labels (see Limits).", "",
             "## Scorecard", "", "| grader | pass rate | mean score | n | what it checks |", "|---|---|---|---|---|"]
    what = {"abstention_correct": "abstains exactly when the key says not answerable",
            "groundedness": "share of answer words found in retrieved passages ≥ 0.6 (lexical proxy)",
            "no_pii": "no email, phone or SSN in the answer",
            "citation_accuracy": "every citation found verbatim in its named passage, and lexically covering its claim",
            "citation_accuracy_judged": "same provenance; support judged by the model (entailment)",
            "groundedness_judged": "the model judges the answer entailed by the retrieved passages",
            "answer_entailed_by_citations": "the model judges the whole answer entailed by its cited quotes together"}
    for g, s in by_g.items():
        lines.append(f"| `{g}` | {s['pass_rate']:.0%} | {s['score']:.2f} | {s['n']} | {what.get(g, '')} |")
    lines += ["", f"- Citations checked: {len(rows)}. Provenance (span verbatim in its named passage): "
                  f"**{prov_ok}/{len(rows)}**. This is the deterministic half; the pipeline's own exact-offset verifier "
                  "already guaranteed it.",
              f"- Support, lexical vs judged: lexical passes {sum(l.claim_supported for _, l, _ in rows)}/{len(rows)}, "
              f"judged passes {sum(j.claim_supported for _, _, j in rows)}/{len(rows)}; they disagree on **{len(dis)}**.",
              "", "## Cost and latency", "",
              f"- Answering (Sonnet 5.5): {cl['cost']['input_tokens']:,} input and {cl['cost']['output_tokens']:,} output "
              f"tokens, **${cl['cost']['cost_usd']:.2f}** for 60 questions (cache tokens priced in).",
              f"- Latency, end to end per question, from the timed re-run: p50 **{(cl['latency']['p50_ms'] or 0) / 1000:.1f} s**, "
              f"p95 **{(cl['latency']['p95_ms'] or 0) / 1000:.1f} s**, max {(cl['latency']['max_ms'] or 0) / 1000:.1f} s "
              f"(n={cl['latency']['n']}; scope-time abstentions take milliseconds)." if cl["latency"]["n"] else
              "- Latency: not measured (run `tools/spancheck_run.py latency`).",
              f"- Judge (Opus 5.5): {judge.calls} calls this run, ${judge.usd:.2f} at list price "
              "(0 calls when every verdict is replayed)."]
    if (QA / "latency.jsonl").exists():
        lat = [json.loads(l) for l in (QA / "latency.jsonl").read_text(encoding="utf-8").splitlines()]
        same = sum(r["same_type_as_scored"] for r in lat)
        lines.append(f"- Run-to-run stability (timed re-run vs. the scored run): same answer/abstain decision on "
                     f"**{same}/{len(lat)}**; identical citations on {sum(r['same_citations_as_scored'] for r in lat)}/{len(lat)}.")
    lines += ["", "## Where the graders fail, and why", ""]
    for g in by_g:
        fails = [cr for cr in run.results for gr in cr.grades if gr.grader == g and not gr.passed]
        if not fails:
            continue
        lines += [f"### `{g}`: {len(fails)} failing", ""]
        for cr in fails:
            gr = next(x for x in cr.grades if x.grader == g)
            lines.append(f"- **{cr.case_id}** ({cr.meta['author']}, key {cr.category}): {gr.detail[:220]}")
        lines.append("")
    if dis:
        lines += ["## Where the judge and the lexical proxy disagree", "",
                  "| case | span | lexical | judged |", "|---|---|---|---|"]
        for cid, span, l, j in dis:
            lines.append(f"| {cid} | {span[:110].replace('|', '/')} | {'supported' if l.claim_supported else 'not'} "
                         f"({l.support}) | {'supported' if j.claim_supported else 'not'} ({j.support}) |")
        lines.append("")
    # Answers the graders pass but whose quotes never touch the key's passage. For an absence ("no, but") answer that
    # means the "doesn't say" half may be false: retrieval missed text that was there.
    key = {k["id"]: k for k in load("qa_key.json")["key"]}
    off = []
    for line in (QA / "run.jsonl").read_text(encoding="utf-8").splitlines():
        t = json.loads(line)
        k, r = key[t["id"]], t["result"]
        if k["state"] != "answerable" or r["type"] != "answer":
            continue
        gold = {(s["key"], s["start"], s["end"]) for s in k["spans"]}
        hit = False
        for c in r["citations"]:
            ck = f"{c['accession']}|{c['section']}"
            for g in gold:
                gt = (ROOT / "data" / "sections" / g[0].split("|")[0] / f"{g[0].split('|')[1]}.txt").read_text(
                    encoding="utf-8")[g[1]:g[2]]
                if (g[0] == ck and g[1] < c["end"] and c["start"] < g[2]) or \
                        (g[0].split("|")[0] == c["accession"] and (c["quote"] in gt or (len(gt) > 40 and gt in c["quote"]))):
                    hit = True
        if not hit:
            off.append((t["id"], r["text"]))
    if off:
        lines += ["## Passing answers that miss the key's passage", "",
                  "These pass every grader above, but none of their quotes touches the passage the answer key points "
                  "to. For an absence (\"no, but\") answer, that means the \"doesn't say\" half may be false: retrieval "
                  "missed text that was there, and no grader here can see it.", ""]
        lines += [f"- **{i}**: {txt[:300]}" for i, txt in off] + [""]
    lines += ["## Limits", "",
              "- The key is model-built (FD-DEC 031), so these are agreement figures, not an independent measurement.",
              "- The judge isn't calibrated on this corpus. `spancheck` asks for a human gold set before a judge is "
              "trusted; its disagreements with the lexical proxy above are where calibration would start.",
              "- Groundedness (lexical) and citation support (lexical) are word-overlap proxies: paraphrase lowers them "
              "and a negation can fool them. That's why the judged versions are reported beside them.",
              "- \"No, but\" answers (FD-DEC 033) assert an absence. A citation can support the \"it does say Z\" "
              "half but never the \"doesn't say X\" half, so support graders score them against their best-matching "
              "sentence (`claim_split`)."]
    (ROOT / "docs" / "spancheck-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    print(f"\njudge calls: {judge.calls} (new {judge.rec.calls}, replayed {judge.rec.hits})")
    _ = audit


def dev(offline: bool) -> None:
    """Tuning aid: the citation graders over the dev slice (data/qa/dev.jsonl), never over the scored 60."""
    sys.stdout.reconfigure(encoding="utf-8")
    load_env()
    cases, outs = outputs("dev.jsonl")
    judge = RecordedJudge(offline)
    run = evaluate(cases, lambda qid: {k: v for k, v in outs[qid].items() if k != "stage"},
                   graders=[citation_accuracy(name="citation_accuracy_judged", claim_split=True,
                                              support_fn=judge_support(provider=judge, model=JUDGE)),
                            entailed_by_citations(judge)])
    for g, s in run.scorecard().by_grader().items():
        print(f"{g}: pass {s['pass_rate']:.0%} (n={s['n']})")
    for cr in run.results:
        for gr in cr.grades:
            if not gr.passed:
                print(f"  {cr.case_id} {gr.grader}: {gr.detail[:200]} | {cr.meta['question'][:60]}")
    print(f"judge calls {judge.calls}, ${judge.usd:.2f}")


if __name__ == "__main__":
    {"latency": lambda: latency(), "score": lambda: score("--offline" in sys.argv),
     "dev": lambda: dev("--offline" in sys.argv)}[sys.argv[1]]()
