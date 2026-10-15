"""Classify a labeled set and score it against the human labels (M4).

    python tools/run_materiality.py dev            # calls the API for anything not yet recorded (needs a key)
    python tools/run_materiality.py dev --offline  # replays recorded responses only; no key, no network

Writes data/classify/<set>-<model>.jsonl and docs/materiality-eval-<set>.md: confusion matrix, agreement, a
stratum-weighted precision/recall for "material" with a stratified bootstrap CI, every disagreement with the model's
rationale, the outcome counts (unverified / refused / unparseable), and measured token usage and cost. For the dev
set it also reports how many of Claude's suggested labels Trevor overrode (FD-DEC 021).
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.classify.classify import EFFORT, classify  # noqa: E402
from filing_delta.classify.context import restatement_context  # noqa: E402
from filing_delta.classify.model import Recorder, model_id  # noqa: E402
from filing_delta.classify.prompt import prompt_version  # noqa: E402
from filing_delta.cli import load_env  # noqa: E402

LABEL_SECTION = {"10K_1A": "10-K Item 1A", "10Q_P2_1A": "10-Q Part II Item 1A"}
# $ per million tokens: input, output, cache read, cache write (claude-api skill pricing table, cached 2026-10-06;
# cache write at 1.25x input for the 5-minute TTL). Replace with measured invoices if they differ.
PRICES = {"claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50), "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125)}


def human_labels(split: str) -> dict[str, str]:
    text = (ROOT / "docs" / f"materiality-labels-{split}.md").read_text(encoding="utf-8")
    out = {}
    for block in re.split(r"(?m)^## ", text)[1:]:
        m = re.search(r"\*\*Label:\*\*[ \t]*([MCUmcu])", block)
        if m:
            out[block.split(" ", 1)[0]] = {"M": "material", "C": "cosmetic", "U": "unsure"}[m.group(1).upper()]
    return out


_recs: dict[str, tuple] = {}


def to_item(m: dict) -> dict:
    """A labeled sample item -> classifier input, with restatement context computed from its diff record."""
    if m["file"] not in _recs:
        rec = json.loads((ROOT / "data" / "diffs" / m["file"]).read_text(encoding="utf-8"))
        sec = ROOT / "data" / "sections"
        to = (sec / rec["old"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
        tn = (sec / rec["new"]["accession"] / f"{rec['section']}.txt").read_text(encoding="utf-8")
        _recs[m["file"]] = (rec, to, tn)
    rec, to, tn = _recs[m["file"]]
    op = rec["ops"][m["op"]]
    # The labeled texts are frozen in the sample; the diff they came from must still say the same thing.
    assert (op["old"], op["new"]) == (m["old_units"], m["new_units"]), f"{m['id']}: diff changed since sampling"
    return {"id": m["id"], "company": m["company"], "section_label": LABEL_SECTION[m["section"]],
            "old_date": m["old_date"], "new_date": m["new_date"], "status": m["status"],
            "old_text": m["old_text"], "new_text": m["new_text"],
            "context": restatement_context(rec, op, to, tn),
            "formatting_only": m["stratum"] == "formatting_only"}


def cost(usage_rows: list[dict], model: str) -> float:
    pi, po, pcr, pcw = PRICES.get(model, (float("nan"),) * 4)
    t = Counter()
    for u in usage_rows:
        for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
            t[k] += u.get(k) or 0
    return (t["input_tokens"] * pi + t["output_tokens"] * po + t["cache_read_input_tokens"] * pcr
            + t["cache_creation_input_tokens"] * pcw) / 1e6, dict(t)


def weighted_pr(rows, pop):
    per = Counter(r["stratum"] for r in rows)
    tp = fp = fn = 0.0
    for r in rows:
        w = pop[r["stratum"]] / per[r["stratum"]]
        h, m = r["human"] == "material", r["model"] == "material"
        tp += w * (h and m)
        fp += w * (m and not h)
        fn += w * (h and not m)
    p = tp / (tp + fp) if tp + fp else float("nan")
    rc = tp / (tp + fn) if tp + fn else float("nan")
    return p, rc


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    split = sys.argv[1]
    offline = "--offline" in sys.argv
    load_env()
    frozen = json.loads((ROOT / "tests" / "golden" / "materiality_prompt.json").read_text(encoding="utf-8"))
    if split == "test" and prompt_version() != frozen["prompt_version"]:
        raise SystemExit(f"prompt version {prompt_version()} != frozen {frozen['prompt_version']}: the test set may "
                         "only be scored with the prompt frozen on dev (FD-DEC 022).")
    if split == "test":
        missing = [m["id"] for m in json.loads((ROOT / "tests" / "golden" / "materiality_sample.json").read_text(
            encoding="utf-8"))["items"] if m["split"] == "test" and m["id"] not in human_labels("test")]
        if missing:
            raise SystemExit(f"{len(missing)} test items are unlabeled (e.g. {missing[:5]}). Label the test set "
                             "blind before any model output on it exists.")
    sample = json.loads((ROOT / "tests" / "golden" / "materiality_sample.json").read_text(encoding="utf-8"))
    items = [m for m in sample["items"] if m["split"] == split]
    labels = human_labels(split)
    rec = Recorder(ROOT / "data" / "model-cache", offline=offline)
    model = model_id()
    results = []
    for n, m in enumerate(items, 1):
        r = classify(to_item(m), rec)
        results.append(r)
        print(f"{n:3}/{len(items)} {m['id']} {r['source']:5} {r['outcome']:12} {r['label'] or '-':9} "
              f"{r['code'] or '-'}", flush=True)
    out_dir = ROOT / "data" / "classify"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{split}-{model}.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in results), encoding="utf-8")

    by_id = {m["id"]: m for m in items}
    rows = []
    for r in results:
        h = labels.get(r["id"])
        rows.append({"id": r["id"], "stratum": by_id[r["id"]]["stratum"], "human": h,
                     "model": r["label"] if r["outcome"] == "ok" else f"({r['outcome']})", "r": r})
    scored = [x for x in rows if x["human"] in ("material", "cosmetic") and x["model"] in ("material", "cosmetic",
                                                                                         "unsure")]
    cm = Counter((x["human"], x["model"]) for x in scored)
    agree = sum(x["human"] == x["model"] for x in scored)
    pop = sample["population"]
    p, rc = weighted_pr([x for x in scored if x["model"] != "unsure"], pop)
    rng = random.Random(20261015)
    by_s = defaultdict(list)
    for x in scored:
        if x["model"] != "unsure":
            by_s[x["stratum"]].append(x)
    ps, rs = [], []
    for _ in range(2000):
        boot = [rng.choice(v) for v in by_s.values() for _ in v]
        bp, br = weighted_pr(boot, pop)
        if bp == bp and br == br:
            ps.append(bp)
            rs.append(br)
    ps.sort()
    rs.sort()
    ci = lambda xs: (xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]) if xs else (float("nan"),) * 2  # noqa
    usd, toks = cost([r.get("usage") or {} for r in results if r["source"] == "model"], model)
    outcomes = Counter(r["outcome"] for r in results)
    lines = [f"# Materiality evaluation: {split} set", "",
             f"Model `{model}` · effort `{EFFORT}` · prompt version `{prompt_version()}` · {len(items)} changes · "
             f"labels: `docs/materiality-labels-{split}.md`. Generated by `tools/run_materiality.py {split}`. Model "
             "responses are recorded, so `--offline` reproduces this file with no key.", "",
             "## Confusion matrix (rows: human, columns: classifier)", "",
             "| human \\ classifier | material | cosmetic | unsure | not scored |", "|---|---|---|---|---|"]
    for h in ("material", "cosmetic"):
        hx = [x for x in rows if x["human"] == h]
        ns = sum(1 for x in hx if x["model"] not in ("material", "cosmetic", "unsure"))
        lines.append(f"| **{h}** | {cm[(h, 'material')]} | {cm[(h, 'cosmetic')]} | {cm[(h, 'unsure')]} | {ns} |")
    lines += ["", f"- Agreement: **{agree}/{len(scored)}** ({agree / len(scored):.0%})" if scored else "- (no labels)",
              f"- \"Material\": stratum-weighted precision **{p:.2f}** (95% CI {ci(ps)[0]:.2f}–{ci(ps)[1]:.2f}), "
              f"recall **{rc:.2f}** (95% CI {ci(rs)[0]:.2f}–{ci(rs)[1]:.2f}). Stratified bootstrap, 2,000 "
              "resamples.",
              f"- Outcomes: {dict(sorted(outcomes.items()))}. `unverified` = the evidence quote wasn't an exact "
              "substring; `code_mismatch` = a code from the other class. Neither counts as an answer.",
              f"- Human labels: {dict(Counter(labels.values()))}.",
              f"- Usage: {toks} → **${usd:.2f}** at list price."]
    if split == "dev":
        sug = json.loads((ROOT / "tests" / "golden" / "materiality_dev_suggestions.json").read_text(encoding="utf-8"))
        conv = {"M": "material", "C": "cosmetic", "U": "unsure"}
        over = [k for k, v in sug.items() if labels.get(k) != conv[v["label"]]]
        lines.append(f"- Claude's suggested dev labels overridden by Trevor: **{len(over)}/{len(sug)}** "
                     f"{over or ''} (FD-DEC 021: dev labels were pre-filled, so dev agreement is not an accuracy "
                     "estimate. Only the blind test set is).")
    lines += ["", "## Disagreements", ""]
    for x in rows:
        if x["human"] in ("material", "cosmetic") and x["model"] != x["human"]:
            r = x["r"]
            lines.append(f"- **{x['id']}** ({x['stratum']}) human **{x['human']}** · classifier **{x['model']}** "
                         f"`{r.get('code')}`: {r.get('rationale')}")
    (ROOT / "docs" / f"materiality-eval-{split}.md").write_text("\n".join(lines) + "\n", encoding="utf-8",
                                                               newline="\n")
    print(f"\n{agree}/{len(scored)} agree · outcomes {dict(outcomes)} · ${usd:.2f} · recorded {rec.calls} new, "
          f"{rec.hits} replayed -> docs/materiality-eval-{split}.md")


if __name__ == "__main__":
    main()
