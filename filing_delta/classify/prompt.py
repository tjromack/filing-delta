"""The classifier's prompt: Trevor's approved labeling guide, verbatim, plus the output contract (FD-DEC 020).

The guide is read from docs/design/materiality.md §2, the same text Trevor labels against, so the model and the
labeler work from one definition. Any edit to the guide, the instructions or the schema changes PROMPT_VERSION, and
with it every request hash, so recorded responses can never silently mix prompt versions.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from ..diff.display import inline_diff

ROOT = Path(__file__).resolve().parents[2]
GUIDE_PATH = ROOT / "docs" / "design" / "materiality.md"

MATERIAL_CODES = ("new_risk", "removed_risk", "severity", "realized", "specifics", "quantity", "legal_status")
COSMETIC_CODES = ("rewording", "date_rollforward", "cross_reference", "formatting", "restructure")


def guide_text() -> str:
    text = GUIDE_PATH.read_text(encoding="utf-8")
    m = re.search(r"^## 2\. .*?(?=^## 3\. )", text, flags=re.M | re.S)
    if not m:
        raise RuntimeError("docs/design/materiality.md §2 not found: the classifier has no guide")
    return m.group(0).strip()


INSTRUCTIONS = """You classify one change between two consecutive SEC filings' Item 1A (Risk Factors) sections, using \
the labeling guide below exactly as a human labeler does. Judge only the text shown.

Output fields:
- label: "material", "cosmetic", or "unsure" (unsure only when the guide genuinely doesn't decide it).
- code: one code from the guide's tables that matches your label, or "none" when the label is "unsure".
- rationale: one sentence, at most 30 words, naming what changed.
- evidence: an exact quotation, copied character for character, of 3 to 25 consecutive words from the OLD or NEW \
text that shows the change. Do not paraphrase, abbreviate or fix punctuation. It is checked by exact string match.
- evidence_side: "old" or "new", whichever text the evidence was copied from.

Reading the change: in a reworded or moved change, [-words-] were deleted and {+words+} were inserted. "… (N \
unchanged words) …" marks an omitted unchanged stretch. Never quote those markers or the omitted text as evidence; \
quote from the OLD or NEW text as given.

LABELING GUIDE
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": ["material", "cosmetic", "unsure"]},
        "code": {"type": "string", "enum": list(MATERIAL_CODES + COSMETIC_CODES) + ["none"]},
        "rationale": {"type": "string"},
        "evidence": {"type": "string"},
        "evidence_side": {"type": "string", "enum": ["old", "new"]},
    },
    "required": ["label", "code", "rationale", "evidence", "evidence_side"],
    "additionalProperties": False,
}


def system_prompt() -> str:
    return INSTRUCTIONS + "\n" + guide_text()


def prompt_version() -> str:
    body = json.dumps({"system": system_prompt(), "schema": SCHEMA, "template": user_message.__doc__},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


def user_message(item: dict) -> str:
    """One change: where it's from, its status, the texts, and (for reworded/moved) the inline diff (template v1)."""
    parts = [f"Company: {item['company']}", f"Section: {item['section_label']}",
             f"Filings: {item['old_date']} (OLD) -> {item['new_date']} (NEW)", f"Change status: {item['status']}", ""]
    if item["old_text"]:
        parts += ["OLD text:", item["old_text"], ""]
    if item["new_text"]:
        parts += ["NEW text:", item["new_text"], ""]
    if item["status"] in ("reworded", "moved") and item["old_text"] and item["new_text"]:
        parts += ["Inline diff (OLD -> NEW):", inline_diff(item["old_text"], item["new_text"]), ""]
    ctx = item.get("context")
    if ctx:
        side = "OLD" if ctx["side"] == "old" else "NEW"
        parts += [f"Closest {side} paragraph elsewhere in this section (similarity {ctx['similarity']}), for "
                  "context only; do not quote it as evidence:", ctx["text"], ""]
    return "\n".join(parts).strip()
