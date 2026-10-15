"""Pre-fill Claude's suggested labels into the DEV materiality sheet only (FD-DEC 021). Never used on the test set.

    python tools/prefill_dev_suggestions.py

Writes each suggestion after **Label:** and a 'Suggested by Claude' note, and saves the suggestions verbatim to
tests/golden/materiality_dev_suggestions.json. Comparing that file with Trevor's final labels measures how often he
overrode them, which is published next to the dev results.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# id: (label, code, confidence, reason)
SUGGESTIONS = {
    "M007": ("C", "date_rollforward", "low", "Annual update of the reserve size ($115.5B to $120.8B, +4.6%); the risk "
             "statement is unchanged. Borderline under the quantity rule: arguably M if you count the exposure growth."),
    "M012": ("C", "restructure", "medium", "Ages roll forward; the succession sentences removed here reappear "
             "(rewritten) in the split paragraph, see M133, which carries the substantive change."),
    "M023": ("M", "realized", "high", "App Store changes move from required by March 2024 to implemented: U.S. "
             "storefront changes and EU DMA compliance (alternative distribution, payments, fee structures)."),
    "M032": ("M", "removed_risk", "high", "The retail-operations risk factor is dropped entirely; no restatement nearby."),
    "M048": ("M", "specifics", "medium", "Adds new exposures: restricted availability of oil and gas leases, and "
             "policy-driven changes to business or strategy that could reduce returns."),
    "M049": ("C", "restructure", "medium", "Heading broadened to name GHG regulation; the substance is in the body "
             "paragraph (see M129)."),
    "M057": ("M", "specifics", "medium", "New sentence: regulators developing rules for large internationally active "
             "insurance groups (group capital, liquidity, governance)."),
    "M063": ("C", "rewording", "high", "Drops 'Asia, including'; the same countries are listed."),
    "M069": ("C", "rewording", "high", "Drops a lead-in clause and adds 'also'; same claim."),
    "M074": ("C", "rewording", "low", "Adds a program detail (digital marketing assets) and a generic example "
             "(consumer preferences may change); same hedge and same risk. Could be read as minor M specifics."),
    "M075": ("M", "new_risk", "high", "New net-zero / energy-transition risk paragraph, including the company's own "
             "net-zero ambition; not in the prior filing."),
    "M082": ("C", "formatting", "high", "Two commas added."),
    "M086": ("C", "formatting", "high", "Two commas removed."),
    "M092": ("M", "specifics", "medium", "New regulatory developments: the June 2025 G7 statement and January 2026 "
             "OECD guidance largely exempting U.S.-parented groups from Pillar Two (exposure likely reduced)."),
    "M097": ("M", "new_risk", "high", "New risk factor on plastic packaging environmental concerns."),
    "M103": ("C", "restructure", "medium", "Split: the NEW paragraph is the second half of the OLD one, unchanged; the "
             "first half moved to another paragraph."),
    "M108": ("M", "specifics", "low", "Adds 'sanctions' as a named consequence of geopolitical events; small, but a "
             "new concrete exposure. Could be read as C rewording."),
    "M114": ("M", "removed_risk", "high", "The derivative-contracts risk factor heading is removed; no restatement "
             "nearby."),
    "M121": ("C", "restructure", "medium", "The 'Alternative energy' paragraph is restated in the new 'Technology and "
             "low carbon solutions' paragraph (same research and universities point). The new content belongs to that "
             "paragraph, not to this removal."),
    "M124": ("M", "specifics", "high", "Adds the OECD BEPS / global minimum tax proposals and tax-audit exposure."),
    "M127": ("M", "new_risk", "high", "New AI risk factor in the 10-Q."),
    "M128": ("C", "rewording", "high", "'There can be no assurance that such incidents will not have' to 'such "
             "incidents could have': same hedge, reworded."),
    "M129": ("C", "restructure", "low", "Largely restates the old climate paragraph (hurricanes, floods, wildfires; "
             "regulation) with more elaboration; the aligner missed the pairing at 0.22. Could be M specifics for the "
             "insurance-pricing angle."),
    "M130": ("M", "new_risk", "medium", "Adds a culture risk to the key-personnel risk factor: failing to maintain "
             "culture could hurt recruiting and retention."),
    "M133": ("M", "specifics", "high", "The board now names Mr. Abel as Mr. Buffett's replacement; previously "
             "unnamed."),
    "M134": ("M", "specifics", "low", "Adds concerns about perceived health effects of ingredients or packaging "
             "substances, including third-party studies. Otherwise rewording ('sugar-sweetened' to 'sweetened')."),
    "M143": ("C", "date_rollforward", "high", "Only the balance-sheet date changes (September 30, 2023 to September 28, "
             "2024)."),
    "M147": ("M", "removed_risk", "high", "The weather / agricultural commodities (HFCS, citrus) risk paragraph is "
             "removed, with no similar new paragraph."),
}


def main() -> None:
    p = ROOT / "docs" / "materiality-labels-dev.md"
    text = p.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^(?=## M\d{3} )", text)
    seen = set()
    for k, b in enumerate(blocks):
        m = re.match(r"## (M\d{3}) ", b)
        if not m:
            continue
        ident = m.group(1)
        label, code, conf, reason = SUGGESTIONS[ident]
        b = b.replace("**Label:** \n", f"**Label:** {label} {code}\n", 1)
        b = b.replace("**Note (optional):** \n",
                      f"**Note (optional):** \n\n*Suggested by Claude ({conf} confidence): {reason}*\n", 1)
        blocks[k] = b
        seen.add(ident)
    assert seen == set(SUGGESTIONS), set(SUGGESTIONS) ^ seen
    header = blocks[0].replace(
        "The model's output is not shown, and won't be until both sets are labeled.",
        "**Dev set only:** each item is pre-filled with Claude's suggestion (FD-DEC 021). Change the label wherever you "
        "disagree, and say why in the note. The test set stays blank and must be labeled independently.")
    blocks[0] = header
    p.write_text("".join(blocks), encoding="utf-8", newline="\n")
    (ROOT / "tests" / "golden" / "materiality_dev_suggestions.json").write_text(
        json.dumps({k: {"label": v[0], "code": v[1], "confidence": v[2], "reason": v[3]}
                    for k, v in sorted(SUGGESTIONS.items())}, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n")
    from collections import Counter
    print("pre-filled", len(SUGGESTIONS), dict(Counter(v[0] for v in SUGGESTIONS.values())),
          dict(Counter(v[2] for v in SUGGESTIONS.values())))


if __name__ == "__main__":
    main()
