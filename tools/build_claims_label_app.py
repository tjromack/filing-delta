"""Build the keyboard labeling page for the claim-check sample (published as a private artifact, M5).

    python tools/build_claims_label_app.py      # -> data/labeling/claim-check-labeler.html

Embeds tests/golden/claims_sample.json with the matcher's answer shown as a suggestion (FD-DEC 026: Trevor chose
suggestion-assisted labeling, trading the independent check for speed). Labels save one document per item to the artifact's
`db` (collection `claims`) and are read back with tools/score_claims.py --import.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOWN = ("id", "company", "form", "period_end", "fiscal_year", "fiscal_period", "metric", "heading", "before",
         "claim", "after", "tagged")


def suggestion(m: dict) -> dict:
    """The matcher's answer in the page's label terms (FD-DEC 026: Trevor chose to see it before answering)."""
    o, r = m["outcome"], m["reason"]
    if o == "matches":
        concept, period = m["matched"].split()
        return {"label": "M", "code": "", "why": f"The amount fits {concept.split(':')[1]} ({period}) at the precision "
                                                 "written, and the sentence reads as the whole company for this period."}
    if o == "no matching tagged value":
        return {"label": "N", "code": "", "why": "Reads as the whole company for this period, but no table value fits "
                                                 "the amount at the precision written."}
    if o == "non-GAAP wording":
        return {"label": "G", "code": "", "why": "Non-GAAP wording (adjusted, organic, excluding…) comes before the "
                                                 "amount."}
    if r.startswith("segment"):
        return {"label": "X", "code": "segment", "why": "The words before the metric name a segment, product, region "
                                                        f"or other subject: {r.split('(', 1)[1].rstrip(')')}."}
    if r.startswith("amount not within"):
        return {"label": "X", "code": "segment", "why": "The amount is nowhere near (more than 25% from) the "
                                                        "whole-company figure, so it is likely a segment or other "
                                                        "scope named in a heading."}
    if r == "another period":
        return {"label": "X", "code": "other_period", "why": "A year or quarter in the sentence or its heading is not "
                                                             "this filing's own period."}
    return {"label": "X", "code": "other_metric", "why": "The filing tags no whole-company value for this metric "
                                                         "and period."}


def main() -> None:
    sample = json.loads((ROOT / "tests" / "golden" / "claims_sample.json").read_text(encoding="utf-8"))
    items = [{**{k: it[k] for k in SHOWN}, "suggest": suggestion(it["matcher"])} for it in sample["items"]]
    assert not any("matcher" in it or "stratum" in it for it in items)
    payload = json.dumps({"items": items, "collection": "claims"}, ensure_ascii=False).replace("</", "<\\/")
    html = (ROOT / "tools" / "claims_label_template.html").read_text(encoding="utf-8").replace("/*__DATA__*/null", payload)
    dest = ROOT / "data" / "labeling" / "claim-check-labeler.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8", newline="\n")
    print(f"{len(items)} claims -> {dest.relative_to(ROOT)} ({len(html) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
