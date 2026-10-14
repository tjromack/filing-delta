# Diff anomalies: every flagged pair, checked by hand

`docs/diff-report.md` flags any pair whose diff looks like a boundary error might: high churn, a run of
added/removed text at the very start or end of a section, or a big length change. Each flag below was checked by
reading the diff (`python tools/show_diff.py data/diffs/<file> --edges 6`) and, where needed, the filing.

The point of this check is that the parser's boundary errors are invisible in the parser's own report but show up
as "added at the end" or "removed at the start" in the diff. It found one real boundary error on its first run.

## Found and fixed: JPMorgan MD&A lost its last page (5 of 8 years)

- **Flag:** JPM 10-K Item 7, 2021→2022, 2022→2023, 2024→2025: `added_at_end` / `removed_at_end`. The
  Forward-Looking Statements section appeared and disappeared at the end of the MD&A from year to year.
- **Cause:** the pointer stub states the MD&A pages ("appears on pages 46–160"), but the section ended at the page
  break after the last *running header*. JPM prints that header on alternate pages only, so when the last MD&A page
  had none, it was cut. The M2 page check didn't catch it because it allowed one page of tolerance (meant for GE's
  index ranges), and the shortfall was exactly one page.
- **Fix (FD-DEC 019):** when the filer states the page range, the section runs to the end of the stated last page,
  and the page check is exact for stated pointer ranges. All 8 JPM years now match their stated pages exactly. The
  goldens were unaffected (the golden JPM year already ended on its last page). The 2022→2023 and 2024→2025 flags
  cleared.

## Filer inconsistency, not a parser error

- **JPM 10-K Item 7, 2020→2021 (`removed_at_end`) and 2021→2022 (`added_at_end`).** In its 2021 10-K, JPM states the
  MD&A "appears on pages 46–154", and that year its Forward-Looking Statements are on page 155, outside its own
  stated range. In every other year the forward-looking statements are inside the stated range. The extraction
  follows the filer's statement. The diff correctly shows the section leaving and returning at the end. A reader
  of these two diffs should know the "removed/added" text is the filer moving a section boundary, not new
  disclosure. Recorded here; no change.

## Genuine content changes

- **Walmart 10-K Item 1A, FY2019→FY2020 (`removed_at_end`):** the Walmex/FCPA investigation paragraphs were dropped
  (that matter was resolved in 2019) and a forum-selection bylaw risk was added.
- **Pfizer 10-K Item 1A, FY2019→FY2020 (`removed_at_start`):** the forward-looking-statements preamble at the top of
  Item 1A was removed and the introduction was rewritten ("This section describes the material risks…").
- **Coca-Cola 10-K Item 7, FY2018→FY2019 (`removed_at_end`):** a block of balance-sheet change explanations
  (assets held for sale, equity method investments, deferred taxes…) at the end of the MD&A was dropped.
- **GE 10-K Item 7, FY2020→FY2021 (`removed_at_end`):** the non-GAAP reconciliation tables at the end of the MD&A were
  restructured (adjusted EPS and industrial net debt tables replaced).
- **Apple 10-Q Part II Item 1A, Q1 FY2025→Q1 FY2026 (`high_churn`, `removed_at_end`):** Apple's 10-Q risk-factor
  section updates whichever risks changed that quarter, so the two quarters cover different risks. Expected for this
  section type.

## Found by reading a flag, handed to labeling

- **Walmart 10-K Item 1A, FY2024→FY2025 (`added_at_end`):** the ESG reputation risk factor was reworded heavily
  (similarity 0.36 and 0.38 for its two paragraphs). The same pair showed the matcher missing an expanded paragraph
  and making two doubtful matches, so thresholds were set from 70 human labels (FD-DEC 018), not from this example.
  At the labeled threshold (0.40) this rewording is still reported as removed + added. **That is a known miss**: one of
  the ~20% of real rewordings the published recall (0.80) accounts for. It was deliberately not tuned away.

## Re-check after the final threshold (0.40, 2026-10-14)

7 pairs flagged. Coca-Cola FY2018→FY2019 cleared: some of its balance-sheet paragraphs now match as rewordings.
Every remaining flag is explained above: JPM 2021 (the filer's own stated range, two pairs), Walmart FY2019→FY2020,
Walmart FY2024→FY2025, Pfizer FY2019→FY2020, GE FY2020→FY2021, and Apple's 10-Q.
