# Alignment evaluation

Human labels: 70 Y/N, 0 '?', 0 unlabeled, out of 70 sampled pairs.
Estimates are weighted by each stratum's share of the 6,100 candidate pairs (raw counts in brackets).

## Labels by stratum

| Stratum | Population | Labeled | Y | N |
|---|---|---|---|---|
| ratio 0.25-0.35 · containment <0.6 | 807 | 10 | 2 | 8 |
| ratio 0.25-0.35 · containment >=0.6 | 325 | 10 | 1 | 9 |
| ratio 0.35-0.5 · containment <0.6 | 888 | 10 | 7 | 3 |
| ratio 0.35-0.5 · containment >=0.6 | 850 | 10 | 4 | 6 |
| ratio 0.5-0.6 · containment <0.6 | 273 | 10 | 5 | 5 |
| ratio 0.5-0.6 · containment >=0.6 | 927 | 10 | 5 | 5 |
| ratio 0.6-0.75 · containment >=0.6 | 2,030 | 10 | 10 | 0 |

## Rules

| Rule | Precision | Recall | F1 | raw tp/fp/fn/tn |
|---|---|---|---|---|
| aligner when labeled (ratio ≥ 0.5, gap ≥ 0.35) | 0.86 | 0.78 | 0.82 | 25/6/9/30 |
| **aligner as it runs now** | 0.83 | 0.80 | 0.82 | 26/8/8/28 |
| ratio >= 0.35 | 0.72 | 0.95 | 0.82 | 31/19/3/17 |
| ratio >= 0.35 or containment >= 0.6 | 0.68 | 0.96 | 0.80 | 32/28/2/8 |
| ratio >= 0.35 or containment >= 0.7 | 0.70 | 0.95 | 0.81 | 31/24/3/12 |
| ratio >= 0.35 or containment >= 0.8 | 0.70 | 0.95 | 0.81 | 31/23/3/13 |
| ratio >= 0.35 or containment >= 0.9 | 0.71 | 0.95 | 0.81 | 31/22/3/14 |
| ratio >= 0.4 | 0.74 | 0.90 | 0.81 | 29/17/5/19 |
| ratio >= 0.4 or containment >= 0.6 | 0.69 | 0.93 | 0.79 | 31/27/3/9 |
| ratio >= 0.4 or containment >= 0.7 | 0.72 | 0.93 | 0.81 | 30/22/4/14 |
| ratio >= 0.4 or containment >= 0.8 | 0.72 | 0.93 | 0.81 | 30/21/4/15 |
| ratio >= 0.4 or containment >= 0.9 | 0.72 | 0.90 | 0.80 | 29/20/5/16 |
| ratio >= 0.45 | 0.78 | 0.81 | 0.80 | 25/13/9/23 |
| ratio >= 0.45 or containment >= 0.6 | 0.69 | 0.89 | 0.78 | 29/26/5/10 |
| ratio >= 0.45 or containment >= 0.7 | 0.74 | 0.88 | 0.80 | 28/20/6/16 |
| ratio >= 0.45 or containment >= 0.8 | 0.76 | 0.88 | 0.81 | 28/18/6/18 |
| ratio >= 0.45 or containment >= 0.9 | 0.77 | 0.86 | 0.81 | 27/16/7/20 |
| ratio >= 0.5 | 0.81 | 0.69 | 0.75 | 20/10/14/26 |
| ratio >= 0.5 or containment >= 0.6 | 0.68 | 0.79 | 0.73 | 25/25/9/11 |
| ratio >= 0.5 or containment >= 0.7 | 0.73 | 0.78 | 0.76 | 24/19/10/17 |
| ratio >= 0.5 or containment >= 0.8 | 0.76 | 0.76 | 0.76 | 23/16/11/20 |
| ratio >= 0.5 or containment >= 0.9 | 0.80 | 0.74 | 0.77 | 22/13/12/23 |
| ratio >= 0.55 | 0.88 | 0.62 | 0.73 | 14/4/20/32 |
| ratio >= 0.55 or containment >= 0.6 | 0.69 | 0.76 | 0.73 | 21/21/13/15 |
| ratio >= 0.55 or containment >= 0.7 | 0.75 | 0.73 | 0.74 | 19/14/15/22 |
| ratio >= 0.55 or containment >= 0.8 | 0.81 | 0.68 | 0.74 | 17/10/17/26 |
| ratio >= 0.55 or containment >= 0.9 | 0.86 | 0.66 | 0.75 | 16/7/18/29 |
| ratio >= 0.6 | 1.00 | 0.54 | 0.70 | 10/0/24/36 |
| ratio >= 0.6 or containment >= 0.6 | 0.69 | 0.76 | 0.72 | 20/20/14/16 |
| ratio >= 0.6 or containment >= 0.7 | 0.79 | 0.68 | 0.73 | 16/11/18/25 |
| ratio >= 0.6 or containment >= 0.8 | 0.86 | 0.63 | 0.73 | 14/7/20/29 |
| ratio >= 0.6 or containment >= 0.9 | 0.96 | 0.61 | 0.74 | 13/3/21/33 |

## Headline

**Aligner as it runs: precision 0.83 (95% CI 0.74–0.93), recall 0.80 (95% CI 0.66–0.93)**, stratum-weighted, against 70 human labels (instance criterion). Stratified bootstrap, 2,000 resamples, fixed seed.

## Disagreements with the aligner as it runs now

`elsewhere:` means the aligner paired the old paragraph with a *different* new paragraph. That can be a second valid counterpart, so those are listed separately from outright misses.

- A02 · Apple Inc. · 10K_1A · label N · aligner: moved · ratio 0.405 · containment 0.708
- A12 · Walmart Inc. · 10K_7 · label Y · aligner: elsewhere:moved · ratio 0.63 · containment 0.945
- A19 · GENERAL ELECTRIC CO · 10K_7 · label Y · aligner: unmatched · ratio 0.251 · containment 0.611
- A21 · EXXON MOBIL CORP · 10K_7 · label Y · aligner: unmatched · ratio 0.4 · containment 0.45
- A23 · GENERAL ELECTRIC CO · 10K_7 · label N · aligner: moved · ratio 0.576 · containment 0.63
- A31 · GENERAL ELECTRIC CO · 10K_7 · label N · aligner: moved · ratio 0.494 · containment 0.704
- A33 · JPMORGAN CHASE & CO · 10Q_P1_2 · label Y · aligner: unmatched · ratio 0.354 · containment 0.875
- A34 · JPMORGAN CHASE & CO · 10K_7 · label N · aligner: reworded · ratio 0.505 · containment 0.727
- A43 · JPMORGAN CHASE & CO · 10K_7 · label Y · aligner: unmatched · ratio 0.291 · containment 0.593
- A46 · JPMORGAN CHASE & CO · 10Q_P1_2 · label Y · aligner: elsewhere:moved · ratio 0.545 · containment 0.714
- A48 · JPMORGAN CHASE & CO · 10K_7 · label N · aligner: moved · ratio 0.537 · containment 0.656
- A51 · BERKSHIRE HATHAWAY INC · 10K_7 · label N · aligner: merged · ratio 0.271 · containment 0.958
- A59 · JPMORGAN CHASE & CO · 10K_7 · label N · aligner: reworded · ratio 0.583 · containment 0.8
- A68 · WEYCO GROUP INC · 10Q_P1_2 · label Y · aligner: unmatched · ratio 0.346 · containment 0.35
- A69 · GENERAL ELECTRIC CO · 10K_7 · label N · aligner: merged · ratio 0.254 · containment 1.0
- A70 · EXXON MOBIL CORP · 10K_7 · label Y · aligner: unmatched · ratio 0.353 · containment 0.508

Items that could not be mapped to current units: none.

## Whole-aligner threshold sweep

The aligner re-run at each threshold on the 43 filing pairs the sample comes from, scored as it runs (1:1 competition included):

| REWORD_MIN | Precision | Recall | F1 | raw tp/fp/fn/tn |
|---|---|---|---|---|
| 0.30 | 0.80 | 0.82 | 0.81 | 27/10/7/26 |
| 0.35 | 0.83 | 0.80 | 0.82 | 26/8/8/28 |
| 0.40 | 0.83 | 0.80 | 0.82 | 26/8/8/28 |
| 0.45 | 0.85 | 0.78 | 0.81 | 25/7/9/29 |
| 0.50 | 0.85 | 0.66 | 0.74 | 20/6/14/30 |
| 0.55 | 0.90 | 0.61 | 0.73 | 15/4/19/32 |
| 0.60 | 0.97 | 0.55 | 0.70 | 12/2/22/34 |
