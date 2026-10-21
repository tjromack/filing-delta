"""Command line: `filing-delta fetch` pulls the locked corpus and writes corpus/manifest.csv."""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from pathlib import Path

from .edgar import CorpusSpec, EdgarClient, all_filings, select
from .xbrl.companyfacts import companyfacts_url

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "edgar-cache"
MANIFEST = ROOT / "corpus" / "manifest.csv"
MANIFEST_COLUMNS = ("cik", "company", "form", "report_date", "filing_date", "accession", "primary_document",
                    "is_ixbrl", "bytes", "sha256", "url")


def load_env(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader: KEY=VALUE lines. Real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def cmd_fetch(args: argparse.Namespace) -> int:
    spec = CorpusSpec.load(ROOT / "corpus.toml")
    with EdgarClient(os.environ.get("EDGAR_USER_AGENT"), CACHE_DIR, offline=args.offline) as client:
        rows = []
        for cik in spec.ciks:
            chosen = select(all_filings(client, cik, spec.earliest_filing_date), spec)
            k = sum(f.form == "10-K" for f in chosen)
            q = sum(f.form == "10-Q" for f in chosen)
            client.get(companyfacts_url(cik))   # XBRL company facts (M5 fallback + cross-check), cached like the rest
            name = chosen[0].company if chosen else str(cik)
            print(f"{name[:28]:28} 10-K={k:2} 10-Q={q:2}", flush=True)
            for f in chosen:
                body = client.get(f.url).body
                rows.append({"cik": f.cik, "company": f.company, "form": f.form, "report_date": f.report_date,
                             "filing_date": f.filing_date, "accession": f.accession,
                             "primary_document": f.primary_document, "is_ixbrl": int(f.is_ixbrl),
                             "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "url": f.url})
        s = client.stats
    rows.sort(key=lambda r: (r["cik"], r["form"], r["report_date"], r["accession"]))
    MANIFEST.parent.mkdir(exist_ok=True)
    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} filings -> {MANIFEST.relative_to(ROOT)}")
    print(f"network requests: {s.network_requests}  cache hits: {s.cache_hits}  retries: {s.retries}  "
          f"rate-limit sleep: {s.slept_seconds:.1f}s")
    return 0


def cmd_parse(args: argparse.Namespace) -> int:
    from .parse.report import run, write_reports

    rows = run(ROOT, CACHE_DIR, ROOT / "data" / "sections")
    write_reports(rows, ROOT / "docs")
    present = [r for r in rows if r.form_kind != "absent"]
    ok = sum(r.outcome == "ok" for r in present)
    print(f"{len(rows)} sections ({len(present)} present): ok {ok}, "
          f"partial {sum(r.outcome == 'partial' for r in present)}, failed {sum(r.outcome == 'failed' for r in present)}"
          f" -> docs/parse-report.md, docs/parse-failures.md")
    return 0


def cmd_golden(args: argparse.Namespace) -> int:
    from datetime import date

    from .parse.golden import propose, rederive

    if args.rederive:
        refreshed, failing = rederive(ROOT, CACHE_DIR, date.today().isoformat())
        print(f"refreshed (paragraph breaks only): {refreshed or 'none'}")
        print(f"still failing (words or outcome changed; needs a human): {failing or 'none'}")
        return 1 if failing else 0
    n, confirmed = propose(ROOT, CACHE_DIR)
    print(f"{n} golden sections ({confirmed} human-confirmed, {n - confirmed} proposed) -> tests/golden/sections.json,"
          f" docs/golden-review.md")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    from .diff.run import run

    recs = run(ROOT / "data" / "sections", ROOT / "data" / "diffs", ROOT / "docs")
    full = [r for r in recs if r["state"] == "full -> full"]
    print(f"{len(recs)} pairs ({len(full)} diffed, {sum(bool(r['flags']) for r in full)} flagged) -> data/diffs/,"
          f" docs/diff-report.md")
    return 0


def cmd_facts(args: argparse.Namespace) -> int:
    from .xbrl.run import run

    with EdgarClient(os.environ.get("EDGAR_USER_AGENT"), CACHE_DIR, offline=args.offline) as client:
        recs = run(ROOT, client, ROOT / "data" / "facts", ROOT / "docs")
        s = client.stats
    print(f"{len(recs)} filings -> data/facts/, docs/xbrl-report.md (network requests: {s.network_requests})")
    return 0


def cmd_claims(args: argparse.Namespace) -> int:
    from .xbrl.claims_run import matcher_version, run

    recs = run(ROOT / "data" / "sections", ROOT / "data" / "facts", ROOT / "data" / "claims", ROOT / "docs")
    print(f"{sum(len(r['claims']) for r in recs)} claims in {len(recs)} filings (matcher {matcher_version()}) -> "
          "data/claims/, docs/claims-report.md")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .web import create_app

    print(f"filing-delta read view: http://127.0.0.1:{args.port}/  (Ctrl+C to stop)", flush=True)
    uvicorn.run(create_app(ROOT), host="127.0.0.1", port=args.port, log_level="warning")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    """The cold-start path (rubric gate 6): from a fresh clone to the read view in one command, with no API key.

    Downloads and verifies the data release, rebuilds only what the read view reads (sections, diffs, the
    classifier's corpus labels and the recorded QA run, all from cached and recorded responses), then serves it.
    Steps whose outputs already exist are skipped, so a second run starts the server straight away. Regenerated
    reports come out byte-identical to the committed ones (tools/reproduce.py checks all of them).
    """
    import subprocess

    py = sys.executable
    env = {**os.environ, "ANTHROPIC_API_KEY": "", "PYTHONIOENCODING": "utf-8"}
    env.pop("ANTHROPIC_MODEL", None)
    data = ROOT / "data"
    steps = [
        ("download and verify the data release (63 MB)", [py, "tools/fetch_release.py"], data / "model-cache"),
        ("check the EDGAR cache (no network)", [py, "-m", "filing_delta.cli", "fetch", "--offline"], None),
        ("parse sections", [py, "-m", "filing_delta.cli", "parse"], data / "sections" / "results.jsonl"),
        ("diff year over year", [py, "-m", "filing_delta.cli", "diff"], data / "diffs"),
        ("classifier labels (recorded)", [py, "tools/classify_corpus.py", "report", "--compare", "claude-haiku-5-5"],
         data / "classify" / "corpus-claude-sonnet-5-5.jsonl"),
        ("question answers (recorded)", [py, "tools/run_qa.py", "--offline"], data / "qa" / "run.jsonl"),
    ]
    for label, cmd, done in steps:
        if done is not None and done.exists():
            print(f"  ✓ {label} (already done)", flush=True)
            continue
        print(f"  … {label}", flush=True)
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-2000:], sep="\n")
            return 1
    return cmd_serve(args)


def main(argv: list[str] | None = None) -> int:
    load_env()
    p = argparse.ArgumentParser(prog="filing-delta")
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="fetch the locked corpus (cache-first) and write corpus/manifest.csv")
    f.add_argument("--offline", action="store_true", help="never touch the network; fail on any cache miss")
    f.set_defaults(func=cmd_fetch)
    pa = sub.add_parser("parse", help="parse every cached filing; write docs/parse-report.md + docs/parse-failures.md")
    pa.set_defaults(func=cmd_parse)
    g = sub.add_parser("golden", help="propose golden boundaries for review (never overwrites confirmed ones)")
    g.add_argument("--rederive", action="store_true",
                   help="refresh confirmed entries whose words are unchanged (paragraph-break changes only)")
    g.set_defaults(func=cmd_golden)
    d = sub.add_parser("diff", help="diff each section against the prior period; write docs/diff-report.md")
    d.set_defaults(func=cmd_diff)
    fa = sub.add_parser("facts", help="extract XBRL facts (inline first, company-facts fallback); docs/xbrl-report.md")
    fa.add_argument("--offline", action="store_true", help="never touch the network; fail on any cache miss")
    fa.set_defaults(func=cmd_facts)
    cl = sub.add_parser("claims", help="match MD&A headline claims to tagged values; docs/claims-report.md")
    cl.set_defaults(func=cmd_claims)
    sv = sub.add_parser("serve", help="the read view at http://127.0.0.1:8000 (changes + recorded answers)")
    sv.add_argument("--port", type=int, default=8000)
    sv.set_defaults(func=cmd_serve)
    dm = sub.add_parser("demo", help="fresh clone to read view in one command, no API key (downloads the data release)")
    dm.add_argument("--port", type=int, default=8000)
    dm.set_defaults(func=cmd_demo)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
