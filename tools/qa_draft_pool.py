"""Pick the source passages Claude drafts answerable questions from (M6, FD-DEC 028). Deterministic.

    python tools/qa_draft_pool.py      # -> data/qa/draft_pool.json, and prints each passage

Stratified so no company, section or year dominates: for every company, three passages from different filings and
sections, in sha256 order. Paragraphs only, 40 to 250 words (a full thought, short enough to label). The pool is
drawn before any question is written, so the passages aren't picked for being easy.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from filing_delta.qa.index import catalog, units_for  # noqa: E402
from filing_delta.qa.scope import ALIASES  # noqa: E402

PER_COMPANY = 3
SECTIONS = ("10K_1A", "10K_7", "10Q_P1_2", "10Q_P2_1A")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cat = catalog(ROOT)
    pool = []
    for cik in sorted(ALIASES):
        filings = [f for f in cat if f.cik == cik]
        units, _ = units_for(ROOT, filings, SECTIONS)
        cands = [u for u in units if u.kind == "paragraph" and 40 <= len(u.text.split()) <= 250]
        cands.sort(key=lambda u: hashlib.sha256(f"{u.accession}:{u.section}:{u.start}".encode()).hexdigest())
        picked, used = [], set()
        for u in cands:
            if (u.accession in {p.accession for p in picked}) or (u.section, len(picked)) in used:
                continue
            if sum(p.section == u.section for p in picked) >= 2:
                continue
            picked.append(u)
            used.add((u.section, len(picked)))
            if len(picked) == PER_COMPANY:
                break
        by = {f.accession: f for f in filings}
        for u in picked:
            f = by[u.accession]
            pool.append({"company": ALIASES[cik][0], "accession": u.accession, "form": f.form,
                         "fiscal_year": f.fiscal_year, "fiscal_period": f.fiscal_period, "section": u.section,
                         "start": u.start, "end": u.end, "heading": u.heading, "text": u.text})
    out = ROOT / "data" / "qa" / "draft_pool.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pool, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for n, p in enumerate(pool, 1):
        print(f"\n### D{n:02d} {p['company']} {p['form']} {p['fiscal_period']} {p['fiscal_year']} {p['section']} "
              f"[{p['heading'][:60]}]\n{p['text']}")
    print(f"\n{len(pool)} passages -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
