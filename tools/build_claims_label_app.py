"""Build the keyboard labeling page for the claim-check sample (published as a private artifact, M5).

    python tools/build_claims_label_app.py      # -> data/labeling/claim-check-labeler.html

Embeds tests/golden/claims_sample.json without the matcher's answers: the labeler sees the claim, its context and
the filing's tagged values, never what the matcher decided. Labels save one document per item to the artifact's
`db` (collection `claims`) and are read back with tools/score_claims.py --import.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWN = ("id", "company", "form", "period_end", "fiscal_year", "fiscal_period", "metric", "heading", "before",
         "claim", "after", "tagged")


def main() -> None:
    sample = json.loads((ROOT / "tests" / "golden" / "claims_sample.json").read_text(encoding="utf-8"))
    items = [{k: it[k] for k in SHOWN} for it in sample["items"]]
    assert not any("matcher" in it or "stratum" in it for it in items)
    payload = json.dumps({"items": items, "collection": "claims"}, ensure_ascii=False).replace("</", "<\\/")
    html = (ROOT / "tools" / "claims_label_template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    dest = ROOT / "data" / "labeling" / "claim-check-labeler.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8", newline="\n")
    print(f"{len(items)} claims -> {dest.relative_to(ROOT)} ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
