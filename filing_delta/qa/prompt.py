"""The answer prompt (M6). Versioned by hash and frozen before the labeled set is run, like the M4 prompt."""
from __future__ import annotations

import hashlib
import json

SYSTEM = """You answer questions about U.S. SEC filings using only the numbered passages you are given. The passages \
are copied exactly from the filings.

Rules:
1. Use only the passages. Never add facts from memory or from outside them.
2. Every point in your answer must be supported by a citation. A citation names one passage (P1, P2, ...) and \
quotes one contiguous run of text from it, copied character for character: keep the passage's own quote marks, \
apostrophes, dashes, capitalization, spacing and punctuation. Quote the shortest run that supports the point, usually \
one sentence or part of one. Never stitch pieces together or paraphrase inside a quote. Use at most 4 citations.
3. If the passages don't contain the answer, set "answerable" to false, give no citations, and say briefly in \
"reason" what is missing. Don't guess, and don't answer a nearby question instead. One exception, rule 8.
4. Report what the filing says, attributed to it ("Apple's 2023 10-K says ..."). Don't give investment advice, \
don't predict what will happen, and don't judge whether anything is good or bad for the company or its stock. A \
filing's own statements about its plans or expectations may be reported as what the filing says.
5. When passages come from two filings, say which filing each point comes from.
6. Keep the answer to one to three sentences.
7. Don't add conclusions of your own ("therefore", "this suggests", "the main driver was"). If the question asks why \
something happened or what drove it, give the reason the filing itself states, quoted. If the passages give figures \
but no stated reason, report the figures and say the passages don't state a reason.
8. "No, but" answers. When the question asks whether the filing discusses, mentions or ties together something \
("Does the 10-K discuss X as a risk?"), or asks what it says about some aspect of a subject the passages do \
discuss, and the passages don't state that thing but do say something directly on the same subject: set \
"answerable" to true and answer in the form "[The filing]'s [section] doesn't say [X]. It does say [Z]." Cite Z \
only. Say "doesn't say" about the sections shown, never that something is absent from the company's filings in \
general. This doesn't apply when the question asks for a specific fact (a number, a name, an amount, a date) that \
isn't there, or when nothing in the passages is on the same subject: then rule 3 applies."""

SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean"},
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {
            "type": "object",
            "properties": {"passage": {"type": "string"}, "quote": {"type": "string"}},
            "required": ["passage", "quote"], "additionalProperties": False}},
        "reason": {"type": "string"},
    },
    "required": ["answerable", "answer", "citations", "reason"],
    "additionalProperties": False,
}

SECTION_LABEL = {"10K_1A": "Item 1A, Risk Factors", "10K_7": "Item 7, Management's Discussion and Analysis",
                 "10Q_P1_2": "Part I, Item 2, Management's Discussion and Analysis",
                 "10Q_P2_1A": "Part II, Item 1A, Risk Factors"}
PASSAGE_MAX = 6000      # a long data table is cut here; a quote from the cut text is still exact in the unit


def filing_label(company: str, form: str, fiscal_year: str, fiscal_period: str, period_end: str) -> str:
    when = f"fiscal {fiscal_year}" if form == "10-K" else f"{fiscal_period} of fiscal {fiscal_year}"
    return f"{company} {form}, {when} (period ended {period_end})"


CHANGE_LABEL = {
    "added": "added in this filing: the paragraph diff found no matching paragraph in the other filing",
    "removed": "dropped from the later filing: the paragraph diff found no matching paragraph in it",
    "reworded": "reworded between the two filings (both versions may be shown)",
    "moved": "moved and edited between the two filings",
    "split": "split into several paragraphs between the two filings",
    "merged": "merged from several paragraphs between the two filings",
}


def user_message(question: str, passages: list[dict], notes: list[str]) -> str:
    parts = [f"Question: {question}", ""]
    if notes:
        parts += ["Note: " + " ".join(notes), ""]
    if any(p.get("change") for p in passages):
        parts += ["Note: these passages are the paragraphs a deterministic paragraph-level diff found changed between "
                  "the two filings, each labeled with what the diff found. A passage labeled \"added\" is new text in "
                  "that filing; one labeled \"dropped\" is text the later filing no longer has.", ""]
    for p in passages:
        head = f"[{p['id']}] {p['filing']} · {SECTION_LABEL[p['section']]}"
        if p.get("change"):
            head += f" · {CHANGE_LABEL[p['change']]}"
        if p["heading"]:
            head += f" · under the heading \"{p['heading']}\""
        parts += [head, p["text"], ""]
    return "\n".join(parts).strip()


def prompt_version() -> str:
    blob = json.dumps({"system": SYSTEM, "schema": SCHEMA, "labels": SECTION_LABEL, "max": PASSAGE_MAX,
                       "change": CHANGE_LABEL,
                       "template": user_message("Q", [{"id": "P1", "filing": "F", "section": "10K_1A",
                                                        "heading": "H", "text": "T", "change": "added"}], ["N"])},
                      sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
