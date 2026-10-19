"""The M6 gate: the citation verifier rejects forged citations (docs/design/qa.md §3)."""
from __future__ import annotations

import pytest

from filing_delta.qa import Abstain, Answer, Citation, check, locate, verify
from filing_delta.qa.answer import UNVERIFIED

S23 = ("Our operations could be disrupted by cyberattacks. In 2023 we experienced a ransomware attack that "
       "affected a supplier’s systems.")
S22 = "Our operations could be disrupted by cyberattacks. We have not experienced a material attack."
SECTIONS = {("A-23", "10K_1A"): S23, ("A-22", "10K_1A"): S22}


def cite(acc, quote, text=None, shift=0):
    text = text or SECTIONS[(acc, "10K_1A")]
    i = text.find(quote)
    return Citation(acc, "10K_1A", i + shift, i + shift + len(quote), quote)


REAL = cite("A-23", "In 2023 we experienced a ransomware attack")


def test_real_citation_verifies():
    res, problems = verify("A ransomware attack hit a supplier in 2023.", [REAL], SECTIONS)
    assert isinstance(res, Answer) and res.citations == (REAL,) and problems == []


@pytest.mark.parametrize("bad,why", [
    (Citation("A-23", "10K_1A", 0, 10, "We were never attacked"), "fabricated quote"),
    (Citation(REAL.accession, REAL.section, REAL.start, REAL.end, REAL.quote.replace("2023", "2022")),
     "one character altered"),
    (cite("A-23", "In 2023 we experienced a ransomware attack", shift=3), "right text, wrong offsets"),
    (Citation("A-23", "10K_1A", len(S23) - 5, len(S23) + 20, S23[-5:] + "x" * 20), "offsets past the end"),
    (Citation("A-22", "10K_1A", REAL.start, REAL.end, REAL.quote), "real in another filing, cited to this one"),
    (Citation("A-99", "10K_1A", 0, 4, "Our "), "accession not in the corpus"),
    (Citation("A-23", "10K_7", 0, 4, "Our "), "section not in the corpus"),
    (Citation("A-23", "10K_1A", 5, 5, ""), "empty quote"),
    (Citation("A-23", "10K_1A", 10, 4, "x"), "reversed offsets"),
    # Python slicing would make text[-9:len] equal the last nine characters: only the bounds check stops it.
    (Citation("A-23", "10K_1A", -9, len(S23), S23[-9:]), "negative start"),
])
def test_forged_citations_are_rejected(bad, why):
    assert check(bad, SECTIONS) is not None, why
    res, problems = verify("Some answer.", [bad], SECTIONS)
    assert res == Abstain(UNVERIFIED) and problems, why


def test_one_bad_citation_sinks_the_whole_answer():
    forged = Citation("A-23", "10K_1A", 0, 10, "We were never attacked")
    res, problems = verify("Partly supported answer.", [REAL, forged], SECTIONS)
    assert res == Abstain(UNVERIFIED) and len(problems) == 1 and problems[0].startswith("citation 2")


def test_no_citations_abstains():
    assert verify("An answer with no source.", [], SECTIONS)[0] == Abstain(UNVERIFIED)


def test_empty_text_abstains():
    assert verify("  ", [REAL], SECTIONS)[0] == Abstain(UNVERIFIED)


def test_answer_type_admits_no_uncited_answer():
    with pytest.raises(ValueError):
        Answer("text", ())


def test_locate_is_exact_with_no_normalization():
    unit = S23[52:]                                    # a retrieved passage starting mid-section
    c = locate("a supplier’s systems", 52, unit, "A-23", "10K_1A")
    assert c is not None and S23[c.start:c.end] == c.quote and check(c, SECTIONS) is None
    assert locate("a supplier's systems", 52, unit, "A-23", "10K_1A") is None     # straight quote: not the text
    assert locate("ransomware  attack", 52, unit, "A-23", "10K_1A") is None       # whitespace changed
    assert locate("", 52, unit, "A-23", "10K_1A") is None
