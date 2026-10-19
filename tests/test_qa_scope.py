"""Scoping and ranking (M6): the filing a question is about, abstentions before any model call, BM25."""
from __future__ import annotations

import pytest

from filing_delta.qa.index import Unit, bm25, query_tokens
from filing_delta.qa.scope import ADVICE_REASON, Filing, companies, scope

K1A, K7, Q2, Q1A = "10K_1A", "10K_7", "10Q_P1_2", "10Q_P2_1A"
CAT = [Filing("AAPL-22", 320193, "10-K", "2022-09-24", "2022", "FY", (K1A, K7)),
       Filing("AAPL-23", 320193, "10-K", "2023-09-30", "2023", "FY", (K1A, K7)),
       Filing("AAPL-Q1-25", 320193, "10-Q", "2024-12-28", "2025", "Q1", (Q2,)),
       Filing("WMT-25", 104169, "10-K", "2025-01-31", "2025", "FY", (K1A, K7)),
       Filing("WMT-Q1-26", 104169, "10-Q", "2025-04-30", "2026", "Q1", (Q2, Q1A)),
       Filing("WMT-Q2-26", 104169, "10-Q", "2025-07-31", "2026", "Q2", (Q2, Q1A))]


def accs(s):
    return [f.accession for f in s.filings]


@pytest.mark.parametrize("q", [
    "Should I buy Apple stock?", "Is Walmart a good investment?", "What is the price target for AAPL?",
    "Will Apple's revenue go up next year?", "Will Walmart's dividend rise?", "Is Apple overvalued?",
    "Predict the next quarter for Walmart",
])
def test_advice_and_predictions_abstain(q):
    assert scope(q, CAT).abstain == ADVICE_REASON


@pytest.mark.parametrize("q", [
    "What does Apple's 2023 10-K say it expects for gross margin?",     # reporting what the filing says: allowed
    "Does Walmart say revenue will grow in fiscal 2025?",
])
def test_asking_what_a_filing_says_about_the_future_is_allowed(q):
    assert scope(q, CAT).abstain is None


def test_company_not_in_corpus():
    assert scope("What does Microsoft say about cloud competition?", CAT).abstain.startswith(
        "The question doesn't name a company in the corpus")


def test_period_outside_coverage_names_what_is_missing():
    a = scope("What did Apple's 2017 10-K say about China?", CAT).abstain
    assert "fiscal 2017 is outside the corpus" in a


def test_year_picks_the_fiscal_year_filing():
    assert accs(scope("What risks did Apple list in its 2022 10-K?", CAT)) == ["AAPL-22"]
    assert accs(scope("What did Walmart say about e-commerce in fiscal 2025?", CAT)) == ["WMT-25"]


def test_no_period_uses_latest_and_says_so():
    s = scope("What does Apple say about supply chain risk?", CAT)
    assert accs(s) == ["AAPL-23"] and "latest 10-K" in s.notes[0]


def test_quarters():
    assert accs(scope("What did Walmart report in Q1 2026?", CAT)) == ["WMT-Q1-26"]   # fiscal 2026 Q1, not the later Q2
    assert accs(scope("What did Walmart say in its latest 10-Q?", CAT)) == ["WMT-Q2-26"]
    assert accs(scope("What did Apple say in its first-quarter 2025 10-Q about sales?", CAT)) == ["AAPL-Q1-25"]
    assert "fourth quarter is reported in the 10-K" in scope("What did Apple say in Q4 2025?", CAT).abstain


def test_two_years_and_change_intent():
    s = scope("What new risks did Apple add between 2022 and 2023?", CAT)
    assert accs(s) == ["AAPL-22", "AAPL-23"] and s.change and s.sections == (K1A, Q1A)


def test_section_hints():
    assert scope("What risks does Apple describe in 2023?", CAT).sections == (K1A, Q1A)
    assert scope("What drove Apple's revenue in 2023?", CAT).sections == (K7, Q2)
    assert scope("What does Apple's 2023 10-K say about its retail stores?", CAT).sections == (K1A, K7, Q2, Q1A)


def test_section_not_parsed_abstains():
    a = scope("What risks did Apple add in Q1 2025?", CAT).abstain        # Apple's 10-Q has no parsed Part II 1A
    assert a.startswith("Those filings have no parsed text")


def test_company_matching():
    assert companies("What did JP Morgan and Exxon say?") == [19617, 34088]
    assert companies("AAPL and KO") == [320193, 21344]
    assert companies("the ford of a river, apple pie") == [320193, 37996]   # names are names; tickers are exact
    assert companies("a ko'd boxer") == []                                  # lowercase "ko" isn't the ticker


def test_query_tokens_drop_names_years_and_question_words():
    assert query_tokens("What does Apple's 2023 10-K say about supply chain risks in China?") == \
        ["supply", "chain", "risk", "china"]


@pytest.mark.parametrize("words", [("revenue", "revenues"), ("increase", "increased", "increases", "increasing"),
                                   ("risk", "risks"), ("company", "companies"), ("loss", "losses"),
                                   ("tariff", "tariffs")])
def test_stem_joins_inflections(words):
    from filing_delta.qa.index import stem
    assert len({stem(w) for w in words}) == 1, words


def test_stem_leaves_short_words_and_double_s():
    from filing_delta.qa.index import stem
    assert stem("gas") == "gas" and stem("business") == "business" and stem("loss") == "loss"


def test_bm25_ranks_and_breaks_ties_deterministically():
    us = [Unit("A", K1A, 0, 10, "paragraph", "", "supply chain disruption in China"),
          Unit("A", K1A, 20, 30, "paragraph", "", "foreign exchange risk"),
          Unit("A", K1A, 40, 50, "paragraph", "Supply Chain", "outsourcing partners"),
          Unit("A", K1A, 60, 70, "paragraph", "", "supply chain disruption in China")]
    top = bm25(["supply", "chain", "china"], us)
    assert top[0][1].start == 0 and top[1][1].start == 60          # equal scores: earlier span first
    assert all(u.start != 20 for _, u in top)                     # no shared word: not returned
    assert any(u.start == 40 for _, u in top)                     # heading words count for search
