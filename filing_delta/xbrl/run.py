"""`filing-delta facts`: extract every corpus filing's XBRL facts, cross-check the two sources, write the report.

Writes data/facts/<accession>.json and docs/xbrl-report.md. Inline XBRL is the primary source and the company-facts
API the fallback (FD-DEC 025). Wherever both exist, every company-facts value for the accession is compared with the
inline value of the same concept, unit and period: two independent paths to one number.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .companyfacts import companyfacts_url, facts_for
from .facts import Fact
from .inline import extract
from .periods import HEADLINE, duration_class, headline


def run(root: Path, client, out_dir: Path, docs_dir: Path) -> list[dict]:
    manifest = list(csv.DictReader((root / "corpus" / "manifest.csv").open(encoding="utf-8")))
    out_dir.mkdir(parents=True, exist_ok=True)
    cf_docs: dict[int, dict] = {}
    recs = []
    for r in manifest:
        cik = int(r["cik"])
        if cik not in cf_docs:
            cf_docs[cik] = json.loads(client.get(companyfacts_url(cik)).body)
        cf = facts_for(cf_docs[cik], r["accession"])
        rec = {"accession": r["accession"], "cik": cik, "company": r["company"], "form": r["form"],
               "report_date": r["report_date"], "issues": [], "duplicates": 0, "dei": {}}
        if r["is_ixbrl"] == "1":
            ix = extract(client.get(r["url"]).body, r["accession"])
            facts, rec["source"] = ix.facts, "inline"
            rec.update(issues=ix.issues, duplicates=ix.duplicates, dei=ix.dei)
            dei_end = (ix.dei.get("DocumentPeriodEndDate") or {}).get("end")
            rec["period_end"] = dei_end or r["report_date"]
            rec["period_end_source"] = "dei:DocumentPeriodEndDate" if dei_end else "manifest (no dei period end)"
        else:
            facts, rec["source"] = cf, "companyfacts"
            rec["period_end"], rec["period_end_source"] = r["report_date"], "manifest (EDGAR period of report)"
        rec["period_matches_manifest"] = rec["period_end"] == r["report_date"]
        rec["cross_check"] = cross_check(facts, cf) if rec["source"] == "inline" else None
        cc = rec["cross_check"]
        if cc and len(cc["missing_inline"]) > cc["compared"]:
            # Most of the filing's tagged values aren't in the primary document: its financial statements are in an
            # exhibit (Pfizer FY2019: Exhibit 13). Use the company-facts API for this filing and say why.
            facts, rec["source"] = cf, "companyfacts"
            rec["source_reason"] = (f"statements outside the primary document: {len(cc['missing_inline'])} "
                                    f"company-facts values not inline, {cc['compared']} inline")
        rec["headline"] = headline(facts, rec["period_end"], r["form"])
        rec["n_facts"] = len(facts)
        rec["n_dimensional"] = sum(bool(f.dims) for f in facts)
        (out_dir / f"{r['accession']}.json").write_text(
            json.dumps({**rec, "facts": [f.to_json() for f in facts]}, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n")
        recs.append({**rec, "_facts": facts})
    write_report(recs, docs_dir)
    for rec in recs:
        rec.pop("_facts")
    return recs


def cross_check(inline: list[Fact], cf: list[Fact]) -> dict:
    """Every company-facts value for this accession vs. the inline value with the same key."""
    if not cf:
        return {"status": "not in company-facts API", "compared": 0, "equal": 0, "differ": [], "missing_inline": []}
    by_key = {f.key(): f for f in inline if not f.dims}
    differ, missing, equal = [], [], 0
    for f in cf:
        g = by_key.get(f.key())
        if g is None:
            missing.append(f.concept)
        elif g.value == f.value:
            equal += 1
        else:
            differ.append({"concept": f.concept, "start": f.start, "end": f.end, "inline": g.value,
                           "companyfacts": f.value})
    return {"status": "compared", "compared": equal + len(differ), "equal": equal, "differ": differ,
            "missing_inline": missing}


def restatements(recs: list[dict]) -> list[dict]:
    """The same consolidated concept, unit and period carrying different values in different filings."""
    seen: dict[tuple, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for rec in recs:
        for f in rec["_facts"]:
            if not f.dims and f.value is not None:
                seen[(rec["cik"], f.concept, f.unit, f.start, f.end)][f.value].append(rec["accession"])
    out = []
    for (cik, concept, unit, start, end), vals in seen.items():
        if len(vals) > 1:
            out.append({"cik": cik, "concept": concept, "unit": unit, "start": start, "end": end,
                        "values": {v: sorted(a) for v, a in sorted(vals.items())}})
    return out


def write_report(recs: list[dict], docs_dir: Path) -> None:
    n = len(recs)
    src = Counter(r["source"] for r in recs)
    forms = Counter(r["form"] for r in recs)
    dates = sorted(r["report_date"] for r in recs)
    issues = sum(len(r["issues"]) for r in recs)
    pm = [r for r in recs if not r["period_matches_manifest"]]
    moved = [r for r in recs if r.get("source_reason")]
    cc = [r["cross_check"] for r in recs if r["cross_check"] and r["cross_check"]["status"] == "compared"]
    comp, eq = sum(c["compared"] for c in cc), sum(c["equal"] for c in cc)
    miss = sum(len(c["missing_inline"]) for c in cc)
    not_in_api = [r for r in recs if r["cross_check"] and r["cross_check"]["status"] != "compared"]
    rest = restatements(recs)
    head_rest = [x for x in rest if any(x["concept"] in cs for cs in HEADLINE.values())]
    lines = ["# XBRL facts report", "",
             f"Every corpus filing: **{n}** ({forms['10-K']} 10-K with period of report {dates[0]} to "
             f"{max(r['report_date'] for r in recs if r['form'] == '10-K')}, {forms['10-Q']} 10-Q), 11 companies. "
             "Generated by `filing-delta facts` from cached responses only. 10-K statements are audited; 10-Q "
             "statements are unaudited interim statements. These are financial-statement values shown as context, "
             "never as narrative (FD-DEC 025).", "",
             "## Extraction", "",
             f"- Source: inline XBRL in the filing **{src['inline']}**, company-facts API **{src['companyfacts']}** "
             "(the older non-inline 10-Ks, plus any inline filing whose statements sit in an exhibit; consolidated "
             "facts only)" + ("; moved to company-facts: " + "; ".join(
                 f"{r['company']} {r['form']} {r['report_date']} ({r['source_reason']})" for r in moved)
                 if moved else "") + ".",
             f"- Facts: **{sum(r['n_facts'] for r in recs):,}** distinct numeric facts, "
             f"{sum(r['n_dimensional'] for r in recs):,} with a segment or other dimension. "
             f"{sum(r['duplicates'] for r in recs):,} repeated tags collapsed (same key, same value).",
             f"- Unreadable values or conflicting duplicates: **{issues}** (listed below).",
             f"- Period end from the document's own `dei:DocumentPeriodEndDate`: "
             f"{sum(r['period_end_source'].startswith('dei') for r in recs)} of {src['inline'] + len(moved)} "
             "inline-XBRL documents; "
             f"disagreements with EDGAR's period of report: **{len(pm)}**"
             + (": " + ", ".join(f"{r['company']} {r['form']} {r['report_date']} -> {r['period_end']}" for r in pm)
                if pm else "") + ".", "",
             "## Two-source cross-check (inline vs. company-facts API, same accession)", "",
             f"- Values compared: **{comp:,}**; equal: **{eq:,}** ({eq / comp:.2%})." if comp else "- none compared",
             f"- Company-facts values with no inline fact of the same key: {miss:,}"
             + (f", of which {sum(len(r['cross_check']['missing_inline']) for r in moved):,} are from the filing(s) "
                "moved to company-facts above" if moved else "") + ".",
             f"- Inline filings absent from the company-facts API: {len(not_in_api)}"
             + (" (" + ", ".join(f"{r['company']} {r['form']} {r['report_date']}" for r in not_in_api) + ")"
                if not_in_api else "") + ".", ""]
    diffs = [(r, d) for r in recs if r["cross_check"] for d in r["cross_check"].get("differ", [])]
    if diffs:
        lines += ["| filing | concept | period | inline | company-facts |", "|---|---|---|---|---|"]
        for r, d in diffs[:40]:
            lines.append(f"| {r['company']} {r['form']} {r['report_date']} | {d['concept']} | "
                         f"{d['start'] or ''}–{d['end']} | {d['inline']} | {d['companyfacts']} |")
        if len(diffs) > 40:
            lines.append(f"| … {len(diffs) - 40} more | | | | |")
        lines.append("")
    lines += ["## Headline values (consolidated, current period)", "",
              "10-K: the fiscal year. 10-Q: the fiscal quarter, or year-to-date where no quarter is tagged (cash flow "
              "statements are year-to-date only). *not tagged* means none of the metric's concepts "
              "(`filing_delta/xbrl/periods.py`) is tagged for the period; it is never shown as zero.", "",
              "| metric | ok | of which 10-Q year-to-date | ambiguous | not tagged (filings) |", "|---|---|---|---|---|"]
    for m in HEADLINE:
        c = Counter(r["headline"][m]["status"] for r in recs)
        ytd = sum(r["headline"][m].get("period") in ("half", "nine_months") for r in recs)
        nt = [f"{r['company'].split()[0].title()} {r['form']} {r['report_date'][:7]}" for r in recs
              if r["headline"][m]["status"] == "not tagged"]
        nt_s = f"{len(nt)}" + (f": {', '.join(nt)}" if 0 < len(nt) <= 8 else
                               f" ({', '.join(f'{k} {v}' for k, v in Counter(x.split()[0] for x in nt).most_common())})"
                               if nt else "")
        lines.append(f"| {m} | {c['ok']} | {ytd} | {c['ambiguous']} | {nt_s} |")
    lines += ["", "## Restated comparatives", "",
              f"The same consolidated concept and period with different values in different filings: **{len(rest):,}** "
              f"keys, {len(head_rest)} of them headline concepts. Surfaced, not resolved.", ""]
    if head_rest:
        lines += ["| company (CIK) | concept | period | values (accessions) |", "|---|---|---|---|"]
        name = {r["cik"]: r["company"] for r in recs}
        for x in head_rest[:30]:
            vals = "; ".join(f"{v} ({', '.join(a)})" for v, a in x["values"].items())
            lines.append(f"| {name[x['cik']]} | {x['concept']} | {x['start'] or ''}–{x['end']} "
                         f"({duration_class(x['start'], x['end'])}) | {vals} |")
        lines.append("")
    if issues:
        lines += ["## Extraction issues", "", "| filing | concept | context | text | problem |", "|---|---|---|---|---|"]
        for r in recs:
            for i in r["issues"]:
                lines.append(f"| {r['company']} {r['form']} {r['report_date']} | {i['concept']} | {i['context']} | "
                             f"{i['text']} | {i['problem']} |")
        lines.append("")
    (docs_dir / "xbrl-report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
