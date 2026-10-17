"""Freeze the claim matcher and draw the hand-label sample (M5, FD-DEC 025 option B).

    python tools/claims_sample.py --freeze   # once: record the matcher version in tests/golden/claims_matcher.json
    python tools/claims_sample.py            # draw tests/golden/claims_sample.json (refuses if labels exist)

The sample is stratified by the matcher's outcome (and, for `not checked`, its reason), sampled deterministically
(sha256 order, round-robin across companies), and stored with the matcher's answer. The labeling page never shows
that answer. Scoring (tools/score_claims.py) refuses to run under any other matcher version.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.xbrl.claims_run import matcher_version  # noqa: E402
from filing_delta.xbrl.facts import Fact  # noqa: E402
from filing_delta.xbrl.periods import HEADLINE, duration_class  # noqa: E402

FROZEN = ROOT / "tests" / "golden" / "claims_matcher.json"
SAMPLE = ROOT / "tests" / "golden" / "claims_sample.json"
QUOTA = {"matches": 40, "no matching tagged value": 999, "non-GAAP wording": 999,
         "not checked: segment or other subject": 20, "not checked: amount not within 25% of the consolidated value": 15,
         "not checked: another period": 8, "not checked: no tagged value for the metric and period": 4}


def stratum(c: dict) -> str:
    return c["outcome"] if c["outcome"] != "not checked" else f"not checked: {c['reason'].split(' (')[0]}"


def tagged_for_display(fr: dict, metric: str) -> list[dict]:
    """Every consolidated value this filing tags for its own period under the metric's concepts, whatever the
    matcher would pick: annual for a 10-K, quarter and year-to-date for a 10-Q."""
    want = ("annual",) if fr["form"] == "10-K" else ("quarter", "half", "nine_months")
    unit = "USD/shares" if metric == "eps_diluted" else "USD"
    out = []
    for f in map(Fact.from_json, fr["facts"]):
        if f.concept in HEADLINE[metric] and f.unit == unit and not f.dims and f.value is not None \
                and f.end == fr["period_end"] and duration_class(f.start, f.end) in want:
            out.append({"concept": f.concept, "start": f.start, "end": f.end,
                        "period": duration_class(f.start, f.end), "value": f.value})
    return sorted(out, key=lambda x: (x["concept"], x["period"]))


def main() -> None:
    if "--freeze" in sys.argv:
        if FROZEN.exists():
            raise SystemExit(f"{FROZEN.name} exists; the matcher is already frozen.")
        FROZEN.write_text(json.dumps({"matcher_version": matcher_version(), "frozen": date.today().isoformat()},
                                     indent=1) + "\n", encoding="utf-8", newline="\n")
        print("frozen", matcher_version())
        return
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))["matcher_version"]
    if matcher_version() != frozen:
        raise SystemExit(f"matcher {matcher_version()} != frozen {frozen}; the sample is drawn from the frozen rules.")
    if SAMPLE.exists() and any(i.get("label") for i in json.loads(SAMPLE.read_text(encoding="utf-8"))["items"]):
        raise SystemExit(f"{SAMPLE.name} already holds labels; refusing to redraw.")
    pool, pop = defaultdict(list), defaultdict(int)
    facts = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "data" / "facts").glob("*.json")}
    for p in sorted((ROOT / "data" / "claims").glob("*.json")):
        r = json.loads(p.read_text(encoding="utf-8"))
        if not r["claims"]:
            continue
        text = (ROOT / "data" / "sections" / r["accession"] / f"{r['section']}.txt").read_text(encoding="utf-8")
        for c in r["claims"]:
            s = stratum(c)
            pop[s] += 1
            pool[s].append((r, c, text))
    chosen = []
    for s, quota in QUOTA.items():
        items = sorted(pool[s], key=lambda x: hashlib.sha256(f"{x[0]['accession']}:{x[1]['start']}".encode()).hexdigest())
        by_co = defaultdict(list)
        for x in items:
            by_co[x[0]["company"]].append(x)
        picked = []
        while len(picked) < min(quota, len(items)):
            for co in sorted(by_co):
                if by_co[co] and len(picked) < quota:
                    picked.append(by_co[co].pop(0))
        chosen += [(s, *x) for x in picked]
    from filing_delta.xbrl.claims import heading_before
    out = []
    for s, r, c, text in chosen:
        sent_start = max(text.rfind("\n\n", 0, c["start"]), text.rfind(". ", 0, c["start"] - 1))
        out.append({"key": f"{r['accession']}:{c['start']}", "stratum": s, "accession": r["accession"],
                    "company": r["company"], "form": r["form"], "period_end": r["period_end"],
                    "fiscal_year": r.get("fiscal_year"), "fiscal_period": r.get("fiscal_period"),
                    "section": r["section"], "start": c["start"], "end": c["end"], "claim": c["text"],
                    "metric": c["metric"], "heading": heading_before(text, c["start"], 1500),
                    "before": text[max(0, c["start"] - 500):c["start"]], "after": text[c["end"]:c["end"] + 250],
                    "tagged": tagged_for_display(facts[r["accession"]], c["metric"]),
                    "matcher": {"outcome": c["outcome"], "reason": c["reason"], "matched": c["matched"]},
                    "label": None})
        assert sent_start >= -1
    out.sort(key=lambda x: hashlib.sha256((x["key"] + ":id").encode()).hexdigest())
    for n, x in enumerate(out, 1):
        x["id"] = f"C{n:03d}"
    SAMPLE.write_text(json.dumps({"matcher_version": frozen, "population": dict(pop), "items": out},
                                 indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    got = defaultdict(int)
    for x in out:
        got[x["stratum"]] += 1
    print(f"{len(out)} claims sampled from {sum(pop.values())}:", dict(got))


if __name__ == "__main__":
    main()
