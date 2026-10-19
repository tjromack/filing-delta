"""The answer type and the citation verifier (M6, design pin 5). Pure.

Every answer is `Answer(text, citations ≥ 1)` or `Abstain(reason)`; there is no third case. A citation is
(accession, section, char start, char end, quote), and it is valid only if the stored section's text over
[start, end) is the quote, character for character. If any citation in an answer fails, the whole answer
becomes an abstention: a partly verified answer is never shown.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Union


@dataclass(frozen=True)
class Citation:
    accession: str
    section: str        # "10K_1A" | "10K_7" | "10Q_P1_2" | "10Q_P2_1A"
    start: int
    end: int
    quote: str


@dataclass(frozen=True)
class Answer:
    text: str
    citations: tuple[Citation, ...]

    def __post_init__(self) -> None:
        if not self.citations:
            raise ValueError("an Answer needs at least one citation; abstain instead")
        if not self.text.strip():
            raise ValueError("an Answer needs text")


@dataclass(frozen=True)
class Abstain:
    reason: str


Result = Union[Answer, Abstain]

UNVERIFIED = "citation could not be verified"


def check(c: Citation, sections: Mapping[tuple[str, str], str]) -> str | None:
    """None if the citation is real, else why not."""
    text = sections.get((c.accession, c.section))
    if text is None:
        return f"{c.accession} {c.section} is not in the corpus"
    # start < end with equal text below also rules out an empty quote; 0 <= start stops Python's negative slicing
    # from "matching" the section's tail.
    if not (0 <= c.start < c.end <= len(text)):
        return f"offsets [{c.start}, {c.end}) outside the section (length {len(text)})"
    if text[c.start:c.end] != c.quote:
        return "the section's text at those offsets is not the quote"
    return None


def verify(text: str, citations: list[Citation], sections: Mapping[tuple[str, str], str]) -> tuple[Result, list[str]]:
    """Answer only if every citation checks; otherwise Abstain, with every failure listed for the run log."""
    problems = [f"citation {i + 1}: {p}" for i, c in enumerate(citations) if (p := check(c, sections))]
    if not citations:
        problems.append("no citations")
    if problems or not text.strip():
        return Abstain(UNVERIFIED), problems or ["empty answer text"]
    return Answer(text.strip(), tuple(citations)), []


def locate(quote: str, unit_start: int, unit_text: str, accession: str, section: str) -> Citation | None:
    """A quote copied from a retrieved passage -> a citation with absolute offsets in the section, or None if the
    quote is not an exact substring of that passage. No normalization of any kind (design §2)."""
    if not quote:
        return None
    i = unit_text.find(quote)
    if i < 0:
        return None
    return Citation(accession, section, unit_start + i, unit_start + i + len(quote), quote)
