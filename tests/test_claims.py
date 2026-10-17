"""The headline-claim matcher (M5, FD-DEC 025 option B): scope, period and comparison rules, no model."""
from __future__ import annotations

import pytest

from filing_delta.xbrl import Fact
from filing_delta.xbrl.claims import find_claims, fiscal_year, month_day

FY = [Fact("us-gaap:Revenues", "47061000000", "USD", "2024-01-01", "2024-12-31"),
      Fact("us-gaap:NetIncomeLoss", "10631000000", "USD", "2024-01-01", "2024-12-31"),
      Fact("us-gaap:ProfitLoss", "10700000000", "USD", "2024-01-01", "2024-12-31"),
      Fact("us-gaap:Revenues", "45754000000", "USD", "2023-01-01", "2023-12-31"),
      Fact("us-gaap:Revenues", "9000000000", "USD", "2024-01-01", "2024-12-31", dims=(("seg", "LatAm"),))]


def one(text, facts=FY, period_end="2024-12-31", form="10-K", fy="2024", fp="FY"):
    (c,) = find_claims(text, facts, period_end, form, fy, fp)
    assert text[c.start:c.end] == c.text                       # exact span
    return c


def test_consolidated_claim_matches_at_stated_precision():
    c = one("Net operating revenues were $47,061 million in 2024, compared to $45,754 million in 2023.")
    assert (c.outcome, c.metric, c.matched) == ("matches", "revenue", "us-gaap:Revenues annual")
    assert one("Revenues were $47.1 billion in 2024.").outcome == "matches"         # 47.05-47.15 billion


def test_near_miss_is_no_matching_tagged_value_never_differs():
    c = one("Revenues were $46.2 billion in 2024.")
    assert c.outcome == "no matching tagged value"


def test_segment_subjects_are_not_checked():
    assert one("Latin America revenues were $9.0 billion in 2024.").reason.startswith("segment")
    assert one("Marmon's revenues were $9.0 billion in 2024.").reason.startswith("segment")
    assert one("Net sales of Florsheim Australia were $9.0 billion in 2024.").reason.startswith("segment")


def test_company_as_doer_is_consolidated_but_a_named_doer_is_not():
    assert one("In 2024, we had revenues of $47.1 billion.").outcome == "matches"
    assert one("In 2024, Marmon generated revenues of $47.1 billion.").outcome == "not checked"


def test_amount_far_from_consolidated_is_another_scope():
    # "Net income was $3.0 billion" under a business-line heading: no subject in the sentence.
    c = one("Net income was $3.0 billion, an increase of 4%.")
    assert (c.outcome, c.reason.split(" (")[0]) == ("not checked",
                                                    "amount not within 25% of the consolidated value")


def test_non_gaap_wording():
    assert one("Adjusted net income was $10.6 billion in 2024.").outcome == "non-GAAP wording"
    assert one("Organic revenues were $47.1 billion in 2024.").outcome == "non-GAAP wording"


def test_other_periods_by_year_and_by_heading():
    assert one("Revenues were $45.8 billion in 2023.").reason == "another period"
    assert one("2023\n\nRevenues were $45.8 billion, up 3%.").reason == "another period"


def test_changes_are_not_level_claims():
    assert find_claims("An increase in revenues of $1.3 billion in 2024.", FY, "2024-12-31", "10-K", "2024") == []
    assert find_claims("Revenue growth of $1.3 billion in 2024.", FY, "2024-12-31", "10-K", "2024") == []


def test_net_income_concept_follows_the_phrase():
    # attributable to the parent: never ProfitLoss (which includes noncontrolling interests)
    c = one("Net income attributable to the Company was $10.7 billion in 2024.")
    assert c.outcome == "no matching tagged value" and all(t[0] != "us-gaap:ProfitLoss" for t in c.tagged)
    c = one("Net income including noncontrolling interests was $10.7 billion in 2024.")
    assert c.outcome == "matches" and c.matched == "us-gaap:ProfitLoss annual"


def test_net_loss_is_negative():
    facts = [Fact("us-gaap:NetIncomeLoss", "-8182000000", "USD", "2025-01-01", "2025-12-31")]
    c = one("The net loss attributable to Ford Motor Company was $8,182 million in 2025.", facts, "2025-12-31",
            fy="2025")
    assert (c.value, c.outcome) == ("-8182000000", "matches")


def test_10q_quarter_vs_year_to_date_from_the_heading():
    q = [Fact("us-gaap:NetCashProvidedByUsedInOperatingActivities", "7543000000", "USD", "2026-01-01", "2026-07-03"),
         Fact("us-gaap:Revenues", "13380000000", "USD", "2026-04-04", "2026-07-03"),
         Fact("us-gaap:Revenues", "25852000000", "USD", "2026-01-01", "2026-07-03")]
    kw = dict(facts=q, period_end="2026-07-03", form="10-Q", fy="2026", fp="Q2")
    assert one("Year-to-date results\n\nRevenues were $25.9 billion, up 9%.", **kw).matched == \
        "us-gaap:Revenues half"
    assert one("Revenues were $13.4 billion in the second quarter of 2026.", **kw).matched == \
        "us-gaap:Revenues quarter"
    assert one("Revenues were $12.5 billion in the second quarter of 2025.", **kw).reason == "another period"
    assert one("Net cash provided by operating activities was $7.5 billion for the six months ended July 3, 2026.",
               **kw).outcome == "matches"
    # The heading decides: under "Quarterly results" the year-to-date amount is not the quarter's.
    assert one("Quarterly results\n\nRevenues were $25.9 billion, up 9%.", **kw).outcome == "not checked"


def test_10q_calendar_year_of_the_period_counts_as_current():
    # Walmart's quarter ended April 30, 2025 is in fiscal 2026; the text names the calendar date.
    q = [Fact("us-gaap:Revenues", "165609000000", "USD", "2025-02-01", "2025-04-30")]
    c = one("Total revenues were $165.6 billion for the three months ended April 30, 2025.", q, "2025-04-30",
            "10-Q", "2026", "Q1")
    assert c.outcome == "matches"


@pytest.mark.parametrize("period_end,form,fye,want", [
    ("2025-04-30", "10-Q", "1/31", "2026"),           # Walmart Q1 of fiscal 2026
    ("2025-10-31", "10-Q", "January 31", "2026"),
    ("2024-12-28", "10-Q", "--09-28", "2025"),        # Apple Q1 of fiscal 2025
    ("2026-07-03", "10-Q", "December 31", "2026"),
    ("2025-01-31", "10-K", "--01-31", "2025"),        # Walmart fiscal 2025
    ("2021-12-31", "10-K", "--12-31", "2021"),        # Weyco's cover says 2020; the derivation doesn't use it
    ("2026-03-31", "10-Q", None, "2026"),
])
def test_fiscal_year(period_end, form, fye, want):
    assert fiscal_year(period_end, form, fye) == want


def test_month_day_forms():
    assert month_day("--12-31") == month_day("12/31") == month_day("December 31") == (12, 31)
    assert month_day("September 25") == (9, 25) and month_day("nonsense") is None
