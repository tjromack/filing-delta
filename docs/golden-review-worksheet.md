# Golden review worksheet

Fill in **Verdict** for each entry with one of `CONFIRMED`, `WRONG-START`, `WRONG-END`, `WRONG-BOTH`,
`WRONG-KIND` or `UNSURE`. Write **Notes** in your own words: what you saw, and where in the filing. The
process is in the chat; the boundary context for each entry is in `docs/golden-review.md`.

Search tips: EDGAR pages are long. Use Ctrl+F with the search strings below. If a string doesn't hit, search a
shorter piece of it: curly quotes, dashes and line breaks often differ between the filing and the extracted
text.

## 1. BERKSHIRE HATHAWAY INC · 10-Q · period 2026-06-30 · 10-Q Part I Item 2 (MD&A) · HARD

- Filing: <https://www.sec.gov/Archives/edgar/data/1067983/000119312526341032/brka-20260630.htm>
- Parser says: `ok` / `full` · 77,553 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `Results of Operations`
- Search for the **end**: `of securities or the industries in which we do business.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 2. EXXON MOBIL CORP · 10-K · period 2025-12-31 · 10-K Item 7 (MD&A) · HARD

- Filing: <https://www.sec.gov/Archives/edgar/data/34088/000003408826000045/xom-20251231.htm>
- Parser says: `ok` / `full` · 117,253 characters · reasons: `followed_pointer, running_header_extent`
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `FORWARD-LOOKING STATEMENTS`
- Search for the **end**: `a description of open tax years are summarized in Note 15.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 3. GENERAL ELECTRIC CO · 10-K · period 2018-12-31 · 10-K Item 1A (Risk Factors) · HARD

- Filing: <https://www.sec.gov/Archives/edgar/data/40545/000004054519000014/ge10-k2018.htm>
- Parser says: `ok` / `full` · 48,985 characters · reasons: `anchor_only, single_signal, xref_index, end_from_index_pages, page_range_verified`
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The following discussion of risk factors contains`
- Search for the **end**: `about legal proceedings and other loss contingencies.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 4. GENERAL ELECTRIC CO · 10-K · period 2018-12-31 · 10-K Item 7 (MD&A) · HARD

- Filing: <https://www.sec.gov/Archives/edgar/data/40545/000004054519000014/ge10-k2018.htm>
- Parser says: `ok` / `full` · 324,270 characters · reasons: `anchor_only, single_signal, xref_index, end_from_index_pages, page_range_verified`
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The consolidated financial statements of General Electric`
- Search for the **end**: `the credit rating agencies measure GE industrial leverage.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 5. GENERAL ELECTRIC CO · 10-K · period 2025-12-31 · 10-K Item 1A (Risk Factors) · HARD

- Filing: <https://www.sec.gov/Archives/edgar/data/40545/000004054526000008/ge-20251231.htm>
- Parser says: `ok` / `full` · 61,592 characters · reasons: `anchor_only, single_signal, xref_index, toc_group_end, run_in_heading, page_range_verified`
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `RISK FACTORS. The following discussion of the material`
- Search for the **end**: `about legal proceedings and other loss contingencies.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 6. GENERAL ELECTRIC CO · 10-K · period 2025-12-31 · 10-K Item 7 (MD&A) · HARD

- Filing: <https://www.sec.gov/Archives/edgar/data/40545/000004054526000008/ge-20251231.htm>
- Parser says: `ok` / `full` · 71,259 characters · reasons: `anchor_only, single_signal, xref_index, toc_group_end, run_in_heading, page_range_verified`
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `MANAGEMENT’S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION`
- Search for the **end**: `incentive plan and performance stock units granted in 2025.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 7. JPMORGAN CHASE & CO · 10-K · period 2025-12-31 · 10-K Item 7 (MD&A) · HARD

- Filing: <https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm>
- Parser says: `ok` / `full` · 392,752 characters · reasons: `followed_pointer, running_header_extent, filtered_by_stated_pages, page_range_verified`
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The following is Management’s discussion and analysis of`
- Search for the **end**: `Reports on Form 10-Qs, or Current Reports on Form 8-K.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 8. JPMORGAN CHASE & CO · 10-Q · period 2026-06-30 · 10-Q Part I Item 2 (MD&A) · HARD

- Filing: <https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/jpm-20260630.htm>
- Parser says: `ok` / `full` · 275,357 characters · reasons: `anchor_only, single_signal, toc_group_end`
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The following is Management’s discussion and analysis of`
- Search for the **end**: `Reports on Form 10-Q or Current Reports on Form 8-K.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 9. PFIZER INC · 10-K · period 2018-12-31 · 10-K Item 7 (MD&A) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/78003/000007800319000015/pfe-12312018x10kshell.htm>
- Parser says: `failed` / `pointer` · 147 characters · reasons: `exhibit_incorporation`
- Check: the filing's Item 7 says the MD&A is incorporated by reference from a separate exhibit (the annual 'Financial Report'), so there's no MD&A text in this document to extract.
- Search for the statement: `Information required by this item is incorporated by`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 10. Apple Inc. · 10-K · period 2018-09-29 · 10-K Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/320193/000032019318000145/a10-k20189292018.htm>
- Parser says: `ok` / `full` · 55,143 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The following discussion of risk factors contains`
- Search for the **end**: `and cash flows could be materially adversely affected.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 11. Apple Inc. · 10-K · period 2018-09-29 · 10-K Item 7 (MD&A) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/320193/000032019318000145/a10-k20189292018.htm>
- Parser says: `ok` / `full` · 57,466 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `This section and other parts of this Annual Report on Form`
- Search for the **end**: `reporting period could be materially adversely affected.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 12. Apple Inc. · 10-K · period 2025-09-27 · 10-K Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm>
- Parser says: `ok` / `full` · 67,734 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The following summarizes factors that could have a material`
- Search for the **end**: `impact on investor confidence and employee retention.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 13. Apple Inc. · 10-K · period 2025-09-27 · 10-K Item 7 (MD&A) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm>
- Parser says: `ok` / `full` · 18,050 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The following discussion should be read in conjunction with`
- Search for the **end**: `on the Company’s financial condition and operating results.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 14. BERKSHIRE HATHAWAY INC · 10-K · period 2018-12-31 · 10-K Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/1067983/000119312519048926/d678758d10k.htm>
- Parser says: `ok` / `full` · 17,588 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `Berkshire and its subsidiaries (referred to herein as “we,”`
- Search for the **end**: `liquidity and capital resources of these businesses.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 15. BERKSHIRE HATHAWAY INC · 10-K · period 2018-12-31 · 10-K Item 7 (MD&A) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/1067983/000119312519048926/d678758d10k.htm>
- Parser says: `ok` / `full` · 128,991 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `Results of Operations`
- Search for the **end**: `to manage a portion of commodity price risks at BHE.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 16. BERKSHIRE HATHAWAY INC · 10-Q · period 2026-06-30 · 10-Q Part II Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/1067983/000119312526341032/brka-20260630.htm>
- Parser says: `ok` / `pointer` · 538 characters · reasons: `pointer_out`
- Check: The text is the filing's entire statement for this item (a reference to another filing). Nothing more is printed under this heading in the filing.
- Search for the statement: `Our significant business risks are described in Item 1A to`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 17. EXXON MOBIL CORP · 10-K · period 2025-12-31 · 10-K Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/34088/000003408826000045/xom-20251231.htm>
- Parser says: `ok` / `full` · 35,710 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `ExxonMobil’s financial and operating results are subject to`
- Search for the **end**: `the factors discussed above and elsewhere in this report.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 18. FORD MOTOR CO · 10-K · period 2025-12-31 · 10-K Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/37996/000003799626000015/f-20251231.htm>
- Parser says: `ok` / `full` · 93,118 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `We have listed below the material risk factors applicable`
- Search for the **end**: `or take other actions, such as remunerating customers.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 19. FORD MOTOR CO · 10-K · period 2025-12-31 · 10-K Item 7 (MD&A) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/37996/000003799626000015/f-20251231.htm>
- Parser says: `ok` / `full` · 156,005 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `Key Trends and Economic Factors Affecting Ford and the`
- Search for the **end**: `see Note 3 of the Notes to the Financial Statements.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 20. JPMORGAN CHASE & CO · 10-K · period 2025-12-31 · 10-K Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/19617/000162828026008131/jpm-20251231.htm>
- Parser says: `ok` / `full` · 112,554 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The following discussion sets forth the material risk`
- Search for the **end**: `negative impact on JPMorganChase’s business and operations.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 21. JPMORGAN CHASE & CO · 10-Q · period 2026-06-30 · 10-Q Part II Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/19617/000162828026054343/jpm-20260630.htm>
- Parser says: `ok` / `pointer` · 378 characters · reasons: `pointer_out`
- Check: The text is the filing's entire statement for this item (a reference to another filing). Nothing more is printed under this heading in the filing.
- Search for the statement: `Refer to Part I, Item 1A: Risk Factors on pages 9–31 of`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 22. PFIZER INC · 10-K · period 2018-12-31 · 10-K Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/78003/000007800319000015/pfe-12312018x10kshell.htm>
- Parser says: `ok` / `full` · 93,476 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The statements in this Section describe the major risks to`
- Search for the **end**: `of the world and related U.S. military action overseas.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 23. WEYCO GROUP INC · 10-K · period 2018-12-31 · 10-K Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/106532/000114420419013992/tv515153_10k.htm>
- Parser says: `ok` / `full` · 16,942 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `There are various factors that affect the Company’s`
- Search for the **end**: `to infrastructure, warehouses or distribution centers.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 24. WEYCO GROUP INC · 10-K · period 2018-12-31 · 10-K Item 7 (MD&A) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/106532/000114420419013992/tv515153_10k.htm>
- Parser says: `ok` / `full` · 22,994 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `GENERAL`
- Search for the **end**: `Note 3 of the Notes to Consolidated Financial Statements.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 25. WEYCO GROUP INC · 10-Q · period 2026-06-30 · 10-Q Part I Item 2 (MD&A) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/106532/000110465926092615/weys-20260630x10q.htm>
- Parser says: `ok` / `full` · 25,277 characters · reasons: `single_signal`
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `FORWARD-LOOKING STATEMENTS`
- Search for the **end**: `for at least one year, although there can be no assurances.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 26. WEYCO GROUP INC · 10-Q · period 2026-06-30 · 10-Q Part II Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/106532/000110465926092615/weys-20260630x10q.htm>
- Parser says: `ok` / `absent` · 0 characters · reasons: `item_omitted`
- Check: Open the filing's Part II. Confirm it goes from Item 1 straight to Item 2 (or later) with no Item 1A and no 'Risk Factors' heading.

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 27. Walmart Inc. · 10-K · period 2025-01-31 · 10-K Item 1A (Risk Factors) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/104169/000010416925000021/wmt-20250131.htm>
- Parser says: `ok` / `full` · 97,539 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `The risks described below could, in ways we may or may not`
- Search for the **end**: `associate morale or customer or shareholder support.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## 28. Walmart Inc. · 10-K · period 2025-01-31 · 10-K Item 7 (MD&A) · routine

- Filing: <https://www.sec.gov/Archives/edgar/data/104169/000010416925000021/wmt-20250131.htm>
- Parser says: `ok` / `full` · 59,620 characters
- Check: Start = the section's first real paragraph. End = its last sentence. Next = the following item's heading.
- Search for the **start**: `Overview`
- Search for the **end**: `and the interpretation and application of complex tax laws.`

**Verdict:** 

**Start OK?** ☐ yes ☐ no · **End OK?** ☐ yes ☐ no · **Anything inside that shouldn't be?** ☐ no ☐ yes

**Notes:** 

## Overall

**Calls you'd change** (GE's MD&A excluding 'Other Financial Data'; run-in headings kept, bare title lines dropped; tables as cell text):

**Time spent:** 
