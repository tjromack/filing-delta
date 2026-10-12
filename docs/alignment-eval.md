# Alignment evaluation

Human labels: 67 Y/N, 3 '?', 0 unlabeled, out of 70 sampled pairs.
Estimates are weighted by each stratum's share of the 6,100 candidate pairs (raw counts in brackets).

## Labels by stratum

| Stratum | Population | Labeled | Y | N |
|---|---|---|---|---|
| ratio 0.25-0.35 · containment <0.6 | 807 | 10 | 4 | 6 |
| ratio 0.25-0.35 · containment >=0.6 | 325 | 9 | 5 | 4 |
| ratio 0.35-0.5 · containment <0.6 | 888 | 8 | 7 | 1 |
| ratio 0.35-0.5 · containment >=0.6 | 850 | 10 | 7 | 3 |
| ratio 0.5-0.6 · containment <0.6 | 273 | 10 | 9 | 1 |
| ratio 0.5-0.6 · containment >=0.6 | 927 | 10 | 9 | 1 |
| ratio 0.6-0.75 · containment >=0.6 | 2,030 | 10 | 10 | 0 |

## Rules

| Rule | Precision | Recall | F1 | raw tp/fp/fn/tn |
|---|---|---|---|---|
| aligner when labeled (ratio ≥ 0.5, gap ≥ 0.35) | 0.94 | 0.66 | 0.78 | 28/3/23/13 |
| **aligner as it runs now** | 0.94 | 0.71 | 0.81 | 31/3/20/13 |
| ratio >= 0.35 | 0.90 | 0.90 | 0.90 | 42/6/9/10 |
| ratio >= 0.35 or containment >= 0.6 | 0.88 | 0.94 | 0.91 | 47/10/4/6 |
| ratio >= 0.35 or containment >= 0.7 | 0.89 | 0.91 | 0.90 | 44/8/7/8 |
| ratio >= 0.35 or containment >= 0.8 | 0.89 | 0.91 | 0.90 | 43/8/8/8 |
| ratio >= 0.35 or containment >= 0.9 | 0.90 | 0.91 | 0.90 | 43/7/8/9 |
| ratio >= 0.4 | 0.91 | 0.86 | 0.89 | 40/5/11/11 |
| ratio >= 0.4 or containment >= 0.6 | 0.88 | 0.91 | 0.90 | 46/10/5/6 |
| ratio >= 0.4 or containment >= 0.7 | 0.90 | 0.89 | 0.90 | 43/7/8/9 |
| ratio >= 0.4 or containment >= 0.8 | 0.90 | 0.88 | 0.89 | 42/7/9/9 |
| ratio >= 0.4 or containment >= 0.9 | 0.91 | 0.87 | 0.89 | 41/6/10/10 |
| ratio >= 0.45 | 0.93 | 0.73 | 0.82 | 33/4/18/12 |
| ratio >= 0.45 or containment >= 0.6 | 0.89 | 0.87 | 0.88 | 44/9/7/7 |
| ratio >= 0.45 or containment >= 0.7 | 0.92 | 0.83 | 0.87 | 40/6/11/10 |
| ratio >= 0.45 or containment >= 0.8 | 0.92 | 0.81 | 0.86 | 38/6/13/10 |
| ratio >= 0.45 or containment >= 0.9 | 0.92 | 0.77 | 0.84 | 36/5/15/11 |
| ratio >= 0.5 | 0.96 | 0.62 | 0.76 | 28/2/23/14 |
| ratio >= 0.5 or containment >= 0.6 | 0.88 | 0.78 | 0.83 | 40/9/11/7 |
| ratio >= 0.5 or containment >= 0.7 | 0.91 | 0.74 | 0.82 | 36/6/15/10 |
| ratio >= 0.5 or containment >= 0.8 | 0.93 | 0.70 | 0.80 | 33/5/18/11 |
| ratio >= 0.5 or containment >= 0.9 | 0.96 | 0.67 | 0.78 | 31/3/20/13 |
| ratio >= 0.55 | 1.00 | 0.53 | 0.69 | 18/0/33/16 |
| ratio >= 0.55 or containment >= 0.6 | 0.88 | 0.74 | 0.81 | 33/8/18/8 |
| ratio >= 0.55 or containment >= 0.7 | 0.93 | 0.68 | 0.79 | 28/4/23/12 |
| ratio >= 0.55 or containment >= 0.8 | 0.95 | 0.61 | 0.74 | 23/3/28/13 |
| ratio >= 0.55 or containment >= 0.9 | 0.99 | 0.57 | 0.72 | 21/1/30/15 |
| ratio >= 0.6 | 1.00 | 0.41 | 0.58 | 10/0/41/16 |
| ratio >= 0.6 or containment >= 0.6 | 0.88 | 0.73 | 0.80 | 31/8/20/8 |
| ratio >= 0.6 or containment >= 0.7 | 0.92 | 0.60 | 0.73 | 22/4/29/12 |
| ratio >= 0.6 or containment >= 0.8 | 0.94 | 0.52 | 0.67 | 17/3/34/13 |
| ratio >= 0.6 or containment >= 0.9 | 0.98 | 0.47 | 0.63 | 14/1/37/15 |

## Disagreements with the aligner as it runs now

`elsewhere:` means the aligner paired the old paragraph with a *different* new paragraph. That can be a second valid counterpart, so those are listed separately from outright misses.

- A04 · GENERAL ELECTRIC CO · 10K_7 · label Y · aligner: unmatched · ratio 0.268 · containment 0.567
- A06 · COCA COLA CO · 10K_7 · label Y · aligner: elsewhere:moved · ratio 0.326 · containment 0.719
- A12 · Walmart Inc. · 10K_7 · label Y · aligner: elsewhere:moved · ratio 0.63 · containment 0.945
- A13 · JPMORGAN CHASE & CO · 10K_7 · label Y · aligner: unmatched · ratio 0.4 · containment 0.867
- A15 · JPMORGAN CHASE & CO · 10K_7 · label Y · aligner: elsewhere:moved · ratio 0.517 · containment 0.523
- A17 · GENERAL ELECTRIC CO · 10K_7 · label Y · aligner: unmatched · ratio 0.283 · containment 0.6
- A18 · GENERAL ELECTRIC CO · 10K_7 · label Y · aligner: unmatched · ratio 0.26 · containment 0.357
- A19 · GENERAL ELECTRIC CO · 10K_7 · label Y · aligner: unmatched · ratio 0.251 · containment 0.611
- A21 · EXXON MOBIL CORP · 10K_7 · label Y · aligner: unmatched · ratio 0.4 · containment 0.45
- A22 · COCA COLA CO · 10K_7 · label Y · aligner: unmatched · ratio 0.559 · containment 0.591
- A29 · GENERAL ELECTRIC CO · 10K_7 · label Y · aligner: unmatched · ratio 0.311 · containment 0.667
- A31 · GENERAL ELECTRIC CO · 10K_7 · label N · aligner: moved · ratio 0.494 · containment 0.704
- A32 · COCA COLA CO · 10K_7 · label Y · aligner: elsewhere:reworded · ratio 0.422 · containment 0.628
- A33 · JPMORGAN CHASE & CO · 10Q_P1_2 · label Y · aligner: elsewhere:reworded · ratio 0.354 · containment 0.875
- A38 · EXXON MOBIL CORP · 10K_7 · label Y · aligner: elsewhere:moved · ratio 0.545 · containment 0.562
- A40 · JPMORGAN CHASE & CO · 10K_7 · label Y · aligner: unmatched · ratio 0.545 · containment 0.562
- A43 · JPMORGAN CHASE & CO · 10K_7 · label Y · aligner: unmatched · ratio 0.291 · containment 0.593
- A46 · JPMORGAN CHASE & CO · 10Q_P1_2 · label Y · aligner: elsewhere:moved · ratio 0.545 · containment 0.714
- A48 · JPMORGAN CHASE & CO · 10K_7 · label N · aligner: moved · ratio 0.537 · containment 0.656
- A51 · BERKSHIRE HATHAWAY INC · 10K_7 · label N · aligner: merged · ratio 0.271 · containment 0.958
- A64 · JPMORGAN CHASE & CO · 10K_7 · label Y · aligner: unmatched · ratio 0.566 · containment 0.625
- A68 · WEYCO GROUP INC · 10Q_P1_2 · label Y · aligner: unmatched · ratio 0.346 · containment 0.35
- A70 · EXXON MOBIL CORP · 10K_7 · label Y · aligner: unmatched · ratio 0.353 · containment 0.508

Items that could not be mapped to current units: none.
