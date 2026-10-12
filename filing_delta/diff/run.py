"""Pair consecutive filings, diff each section, write data/diffs/ and the published docs/diff-report.md (M3).

Pairs: 10-K to the previous 10-K of the same company (Item 1A, Item 7). 10-Q to the same fiscal quarter one year
earlier (Part I Item 2, Part II Item 1A): consecutive quarters of MD&A differ by design, so year-over-year is the
like-for-like comparison. A pair where either side isn't full text (pointer, absent, failed) is recorded as a state
change without a paragraph diff.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .align import Op, align
from .segment import segment

LABEL = {"10K_1A": "10-K Item 1A", "10K_7": "10-K Item 7", "10Q_P1_2": "10-Q Part I Item 2",
         "10Q_P2_1A": "10-Q Part II Item 1A"}
# Anomaly thresholds: a pair crossing any of these is listed for a human look (possible boundary error upstream).
HIGH_CHURN = 0.6          # share of characters added + removed
EDGE_CHARS = 2000         # a run of added/removed text this long at the very start or end of a section
EDGE_SHARE = 0.15         # ...or this share of the section
LENGTH_RATIO = (0.5, 2.0)


def _load(sections_dir: Path) -> list[dict]:
    return [json.loads(line) for line in (sections_dir / "results.jsonl").read_text(encoding="utf-8").splitlines()]


def _pairs(rows: list[dict]) -> list[tuple[dict, dict]]:
    by: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by[(r["cik"], r["section"])].append(r)
    out = []
    for (_, section), rs in sorted(by.items()):
        rs.sort(key=lambda r: r["report_date"])
        if section.startswith("10K"):
            out += list(zip(rs, rs[1:]))
        else:
            for b in rs:
                bd = date.fromisoformat(b["report_date"])
                for a in rs:
                    if 350 <= (bd - date.fromisoformat(a["report_date"])).days <= 380:
                        out.append((a, b))
    return out


def _text(sections_dir: Path, r: dict) -> str:
    return (sections_dir / r["accession"] / f"{r['section']}.txt").read_text(encoding="utf-8")


def _edge_runs(ops: list[Op], units, side: str) -> tuple[int, int]:
    """Characters in the run of added (side=new) / removed (side=old) units at the very start and end."""
    status = "added" if side == "new" else "removed"
    ids = {i: op.status for op in ops for i in (op.new if side == "new" else op.old)}
    lead = 0
    for u in units:
        if ids.get(u.idx) != status:
            break
        lead += u.end - u.start
    trail = 0
    for u in reversed(units):
        if ids.get(u.idx) != status:
            break
        trail += u.end - u.start
    return lead, trail


def diff_pair(a: dict, b: dict, ta: str, tb: str) -> dict:
    rec = {"cik": a["cik"], "company": a["company"], "section": a["section"],
           "old": {k: a[k] for k in ("accession", "report_date", "form_kind", "outcome", "sha256")},
           "new": {k: b[k] for k in ("accession", "report_date", "form_kind", "outcome", "sha256")}}
    full = all(r["form_kind"] == "full" and r["outcome"] != "failed" for r in (a, b))
    if not full:
        rec["state"] = f"{a['form_kind'] if a['outcome'] != 'failed' else 'failed'} -> " \
                       f"{b['form_kind'] if b['outcome'] != 'failed' else 'failed'}"
        rec["ops"] = []
        return rec
    ua, ub = segment(ta, a["block_map"]), segment(tb, b["block_map"])
    ops = align(ta, ua, tb, ub)
    chars = Counter()
    count = Counter()
    for op in ops:
        count[op.status] += 1
        if op.status == "added":
            chars["added"] += sum(ub[j].end - ub[j].start for j in op.new)
        elif op.status == "removed":
            chars["removed"] += sum(ua[i].end - ua[i].start for i in op.old)
    total = len(ta) + len(tb)
    churn = (chars["added"] + chars["removed"]) / total if total else 0.0
    lead_add, trail_add = _edge_runs(ops, ub, "new")
    lead_rem, trail_rem = _edge_runs(ops, ua, "old")
    flags = []
    if churn > HIGH_CHURN:
        flags.append("high_churn")
    for name, n, size in (("added_at_start", lead_add, len(tb)), ("added_at_end", trail_add, len(tb)),
                          ("removed_at_start", lead_rem, len(ta)), ("removed_at_end", trail_rem, len(ta))):
        if n >= EDGE_CHARS or (size and n / size >= EDGE_SHARE):
            flags.append(name)
    ratio = len(tb) / len(ta) if ta else 0
    if not LENGTH_RATIO[0] <= ratio <= LENGTH_RATIO[1]:
        flags.append("length_ratio")
    rec.update(state="full -> full", units={"old": len(ua), "new": len(ub)}, counts=dict(sorted(count.items())),
               chars=dict(sorted(chars.items())), churn=round(churn, 4), length_ratio=round(ratio, 4), flags=flags,
               old_units=[[u.kind, u.start, u.end] for u in ua], new_units=[[u.kind, u.start, u.end] for u in ub],
               ops=[asdict(o) for o in ops])
    return rec


def run(sections_dir: Path, out_dir: Path, docs: Path) -> list[dict]:
    rows = _load(sections_dir)
    recs = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for a, b in _pairs(rows):
        rec = diff_pair(a, b, _text(sections_dir, a), _text(sections_dir, b))
        name = f"{a['cik']}_{a['section']}_{a['report_date']}__{b['report_date']}.json"
        body = json.dumps(rec, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        (out_dir / name).write_text(body, encoding="utf-8", newline="\n")
        rec["_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        rec["_file"] = name
        recs.append(rec)
    write_report(recs, docs)
    return recs


def write_report(recs: list[dict], docs: Path) -> None:
    full = [r for r in recs if r["state"] == "full -> full"]
    lines = [
        "# Diff report",
        "",
        "Generated by `filing-delta diff` from the parsed sections. Deterministic: regenerating it on the same inputs",
        "reproduces this file byte for byte. No model is involved anywhere in the diff (pin 2).",
        "",
        "Pairs: each 10-K against the same company's previous 10-K; each 10-Q against the same fiscal quarter a year",
        "earlier. Units are paragraphs, headings and whole data tables.",
        "",
        "## Pairs",
        "",
        f"{len(recs)} pairs; {len(full)} with full text on both sides, diffed paragraph by paragraph. The others are",
        "state changes (pointer, absent, failed):",
        "",
        "| State | Pairs |", "|---|---|",
    ]
    for state, n in sorted(Counter(r["state"] for r in recs).items()):
        lines.append(f"| {state} | {n} |")
    tot = Counter()
    for r in full:
        tot.update(r["counts"])
    lines += ["", "## Unit outcomes across all full pairs", "", "| Status | Units |", "|---|---|"]
    for k in ("unchanged", "reworded", "moved", "split", "merged", "added", "removed"):
        lines.append(f"| {k} | {tot.get(k, 0):,} |")
    lines += ["", "## Every full pair", "",
              "| Company | Section | Old → new | Units old/new | unchanged | reworded | moved | split | merged | added |"
              " removed | churn | flags |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(full, key=lambda r: (r["company"], r["section"], r["new"]["report_date"])):
        c = r["counts"]
        lines.append(
            f"| {r['company']} | {LABEL[r['section']]} | {r['old']['report_date']} → {r['new']['report_date']} | "
            f"{r['units']['old']}/{r['units']['new']} | {c.get('unchanged', 0)} | {c.get('reworded', 0)} | "
            f"{c.get('moved', 0)} | {c.get('split', 0)} | {c.get('merged', 0)} | {c.get('added', 0)} | "
            f"{c.get('removed', 0)} | {r['churn']:.1%} | {', '.join(r['flags'])} |")
    flagged = [r for r in full if r["flags"]]
    lines += ["", "## Flagged pairs", "",
              f"{len(flagged)} of {len(full)} full pairs cross an anomaly threshold (churn > {HIGH_CHURN:.0%}; added or"
              f" removed text ≥ {EDGE_CHARS:,} chars or {EDGE_SHARE:.0%} of the section at its very start or end;"
              f" length ratio outside {LENGTH_RATIO[0]}–{LENGTH_RATIO[1]}). Each one is checked by hand. A boundary"
              " error upstream shows up here first. Findings are in `docs/diff-anomalies.md`.", ""]
    for r in sorted(flagged, key=lambda r: (r["company"], r["section"], r["new"]["report_date"])):
        lines.append(f"- {r['company']} · {LABEL[r['section']]} · {r['old']['report_date']} → "
                     f"{r['new']['report_date']} · {', '.join(r['flags'])} · `{r['_file']}`")
    (docs / "diff-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
