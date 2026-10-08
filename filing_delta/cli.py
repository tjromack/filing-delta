"""Command line: `filing-delta fetch` pulls the locked corpus and writes corpus/manifest.csv."""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from pathlib import Path

from .edgar import CorpusSpec, EdgarClient, all_filings, select

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
    from .parse.golden import propose

    n, confirmed = propose(ROOT, CACHE_DIR)
    print(f"{n} golden sections ({confirmed} human-confirmed, {n - confirmed} proposed) -> tests/golden/sections.json,"
          f" docs/golden-review.md")
    return 0


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
    g.set_defaults(func=cmd_golden)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
