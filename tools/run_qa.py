"""Run the frozen QA pipeline on the 60-question set and score it against the answer key (M6).

    python tools/run_qa.py            # calls the API for anything not yet recorded (needs a key)
    python tools/run_qa.py --offline  # replays recorded responses only

Writes data/qa/run.jsonl (one trace per question) and docs/qa-eval.md. Refuses to run unless the pipeline version
matches the frozen one and the key exists (it was committed before this ever ran). M7 re-scores the same recorded
run with spancheck.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.classify.model import Recorder  # noqa: E402
from filing_delta.cli import load_env  # noqa: E402
from filing_delta.qa.ask import ask  # noqa: E402
from filing_delta.qa.index import catalog  # noqa: E402
from filing_delta.qa.version import pipeline_version  # noqa: E402

PRICE = (2.0, 10.0, 0.20, 2.50)      # claude-sonnet-5-5 $/MTok: in, out, cache read, cache write (standard)


def wilson(k: int, n: int) -> str:
    if not n:
        return "-"
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c, h = (p + z * z / (2 * n)) / d, z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{p:.0%} ({max(0, c - h):.0%}–{min(1, c + h):.0%})"


def overlaps(a: tuple, spans: list[dict]) -> bool:
    key, s, e = a
    return any(g["key"] == key and g["start"] < e and s < g["end"] for g in spans)


_TEXT: dict[str, str] = {}


def same_text(key: str, quote: str, spans: list[dict]) -> bool:
    """A citation counts as citing the key's passage if it quotes the same words from the same filing, even at
    another position: filings repeat sentences (Coca-Cola's 2025 10-K defines concentrate sales volume twice)."""
    acc = key.split("|")[0]
    for g in spans:
        if g["key"].split("|")[0] != acc:
            continue
        if g["key"] not in _TEXT:
            a, sec = g["key"].split("|")
            _TEXT[g["key"]] = (ROOT / "data" / "sections" / a / f"{sec}.txt").read_text(encoding="utf-8")
        gt = _TEXT[g["key"]][g["start"]:g["end"]]
        if quote in gt or (len(gt) > 40 and gt in quote):
            return True
    return False


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    load_env()
    frozen = json.loads((ROOT / "tests" / "golden" / "qa_pipeline.json").read_text(encoding="utf-8"))
    if pipeline_version() != frozen["pipeline_version"]:
        raise SystemExit(f"pipeline {pipeline_version()} != frozen {frozen['pipeline_version']}")
    qs = {q["id"]: q for q in json.loads((ROOT / "tests" / "golden" / "qa_questions.json")
                                         .read_text(encoding="utf-8"))["questions"]}
    key = {k["id"]: k for k in json.loads((ROOT / "tests" / "golden" / "qa_key.json")
                                          .read_text(encoding="utf-8"))["key"]}
    rec = Recorder(ROOT / "data" / "model-cache", offline="--offline" in sys.argv)
    cat = catalog(ROOT)
    traces, rows = [], []
    for qid in sorted(qs):
        t = ask(qs[qid]["question"], ROOT, cat, rec)
        t["id"] = qid
        traces.append(t)
        k, r = key[qid], t["result"]
        row = {"id": qid, "author": qs[qid]["author"], "category": qs[qid]["category"], "key": k["state"],
               "result": r["type"], "stage": t["stage"]}
        if k["state"] == "answerable":
            row["retrieved_gold"] = any(overlaps((f"{p['accession']}|{p['section']}", p["start"], p["end"]), k["spans"])
                                        for p in t["retrieved"])
            if r["type"] == "answer":
                row["cites_gold"] = any(overlaps((f"{c['accession']}|{c['section']}", c["start"], c["end"]), k["spans"])
                                        or same_text(f"{c['accession']}|{c['section']}", c["quote"], k["spans"])
                                        for c in r["citations"])
        rows.append(row)
        print(f"{qid} key={k['state']:14} -> {r['type']:7} stage={t['stage']:8} "
              f"{'gold retrieved' if row.get('retrieved_gold') else ''}", flush=True)
    d = ROOT / "data" / "qa"
    (d / "run.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False, sort_keys=True) + "\n" for t in traces),
                                 encoding="utf-8")

    ans = [r for r in rows if r["key"] == "answerable"]
    una = [r for r in rows if r["key"] != "answerable"]
    answered = [r for r in ans if r["result"] == "answer"]
    cited = [r for r in answered if r.get("cites_gold")]
    false_abst = [r for r in ans if r["result"] == "abstain"]
    correct_abst = [r for r in una if r["result"] == "abstain"]
    unverified = [t for t in traces if t["stage"] == "verify" and t["result"]["type"] == "abstain"]
    model_answers = [t for t in traces if t["stage"] == "verify"]
    usd = 0.0
    for t in traces:
        u = t.get("usage") or {}
        usd += ((u.get("input_tokens") or 0) * PRICE[0] + (u.get("output_tokens") or 0) * PRICE[1]
                + (u.get("cache_read_input_tokens") or 0) * PRICE[2]
                + (u.get("cache_creation_input_tokens") or 0) * PRICE[3]) / 1e6
    by = defaultdict(Counter)
    for r in rows:
        ok = (r["key"] == "answerable" and r["result"] == "answer") or (r["key"] != "answerable" and r["result"] == "abstain")
        by[r["author"]]["n"] += 1
        by[r["author"]]["ok"] += ok
    lines = ["# Grounded QA evaluation (M6)", "",
             f"Pipeline `{frozen['pipeline_version']}` (prompt `{frozen['prompt_version']}`), `claude-sonnet-5-5`, on the "
             "60-question set (`tests/golden/qa_questions.json`). Coverage: the locked corpus, i.e. 10-K Item 1A and Item 7 for "
             "fiscal 2018–2025, and 10-Q Part I Item 2 and Part II Item 1A filed January 2025 to September 2026, for 11 "
             "companies. Generated by `tools/run_qa.py`; `--offline` reproduces it from recorded responses with no key.", "",
             "**The answer key is model-built** (FD-DEC 031): two jurors, Opus 5.5 and Fable 5.1, labeled all 60 from the "
             "full section text and agreed on 58. Trevor decided the 2 they split on, seeing both labels. These figures are "
             "agreement with that key, not an independent human measurement. Where both jurors are wrong the same way, it "
             "doesn't show.", "",
             "## Results", "",
             f"| | count | rate (95% CI) |", "|---|---|---|",
             f"| Answerable (key) answered | {len(answered)}/{len(ans)} | {wilson(len(answered), len(ans))} |",
             f"| …and the answer cites the key's passage (by position, or the same words in the same filing) | "
             f"{len(cited)}/{len(answered)} | {wilson(len(cited), len(answered))} |",
             f"| Not answerable (key) correctly abstained | {len(correct_abst)}/{len(una)} | {wilson(len(correct_abst), len(una))} |",
             f"| Retrieval found the key's passage (recall@8, answerable) | {sum(r.get('retrieved_gold', False) for r in ans)}/{len(ans)} | "
             f"{wilson(sum(r.get('retrieved_gold', False) for r in ans), len(ans))} |",
             f"| Model answers whose citations all verified | {len(model_answers) - len(unverified)}/{len(model_answers)} | "
             f"{wilson(len(model_answers) - len(unverified), len(model_answers))} |", "",
             f"Correct abstentions by where they happened: {dict(Counter(r['stage'] for r in correct_abst))} (`scope` "
             "is a rule before any model call: advice, a company outside the corpus, a period outside coverage; `model` "
             "is the model finding the passages don't answer it). The `model` ones are the real test of abstention.", "",
             f"Every answer shown cites an exact span or the question abstained. Answers withheld for an unverifiable "
             f"citation: {len(unverified)}. Measured cost of the run: ${usd:.2f} at list price.", "",
             "By author (correct = answered when the key says answerable, abstained when it says not):", ""]
    for a, c in sorted(by.items()):
        lines.append(f"- {a}: {c['ok']}/{c['n']} correct ({wilson(c['ok'], c['n'])})")
    lines += ["", "## Misses", "", "| id | author | key | system | stage | detail |", "|---|---|---|---|---|---|"]
    for r, t in zip(rows, traces):
        bad = (r["key"] == "answerable" and (r["result"] != "answer" or not r.get("cites_gold"))) or \
              (r["key"] != "answerable" and r["result"] == "answer")
        if bad:
            res = t["result"]
            detail = res.get("reason", "") if res["type"] == "abstain" else \
                "answered without citing the key's passage" if r["key"] == "answerable" else "answered: " + res["text"][:120]
            lines.append(f"| {r['id']} | {r['author']} | {r['key']} | {res['type']} | {r['stage']} | "
                         f"{detail[:160].replace('|', '/')}{' (gold not retrieved)' if r['key'] == 'answerable' and not r.get('retrieved_gold') else ''} |")
    (ROOT / "docs" / "qa-eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines[8:]))
    print(f"\nrecorded {rec.calls} new, replayed {rec.hits}")


if __name__ == "__main__":
    main()
