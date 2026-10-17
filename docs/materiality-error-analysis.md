# Materiality classifier: error analysis (M4)

Scope: 10-K Item 1A and 10-Q Part II Item 1A changes, 11 companies, filing pairs with report dates from 2018-01-31 to
2026-03-28. Classifier: `claude-sonnet-5-5`, prompt `1fd1c7e5bb42` (frozen on dev, FD-DEC 022). "Material" is a
labeled text-change category (`docs/design/materiality.md`), not a legal or accounting materiality determination.

Every figure here comes from a committed file and a command:

| figure | source | command |
|---|---|---|
| blind test result | `docs/materiality-eval-test.md` | `python tools/run_materiality.py test --offline` |
| Haiku comparison | `docs/materiality-eval-test-haiku.md` | same, with `ANTHROPIC_MODEL=claude-haiku-5-5` |
| adjudicated (secondary) | `docs/materiality-eval-test-adjudicated.md` | `python tools/score_recheck.py` |
| full corpus, two models | `docs/materiality-corpus.md` | `python tools/classify_corpus.py report --compare claude-haiku-5-5` |

## Headline (blind, scored once)

Agreement 89/115 (77%). "Material": precision **0.89** (95% CI 0.81–0.96), recall **0.80** (0.68–0.89),
stratum-weighted. Haiku 5.5 on the same set: 0.84 / 0.77, with overlapping intervals, at about 1/20 of the cost.

The 26 disagreements split into 17 missed "material" and 9 false "material". The classifier under-calls more than it
over-calls.

## Where it goes wrong

**1. Restructured text (the main source of misses).** 9 of the 17 misses carry the classifier code `restructure`.
Split/merged changes scored 3/9. The classifier finds the moved text elsewhere in the section and calls the change a
restatement (tie-break rule 3 and the classifier notes). Trevor labels a restructured passage material when the
restructuring also adds or drops disclosure.

**2. Updated figures (3 of the 9 false alarms).** In three numbers-only changes (an investment portfolio size, an
industry loss estimate, debt and content-liability balances) the classifier applied the guide's `quantity` code:
a number describing the exposure itself. Trevor labels these year-over-year updates cosmetic.

**3. Removed text is the least stable label.** On the full corpus Sonnet and Haiku agree on 77.0% of changes (kappa
0.58) but only 59% on removed text, where Haiku answers "unsure" on 244 of 848. This is model-to-model consistency,
not accuracy, but it marks the same area where the human and the classifier split most.

What works: formatting-only changes (the rule path, no model) scored 10/10, and near-identical rewordings
(similarity 0.95–1.00) scored 11/11.

## The information-gap hypothesis, tested

After the blind run, the misses looked like an information gap. The classifier had been shown restatement context
(where else in the section the moved text appears), but the labeling sheet showed only OLD and NEW. Trevor
relabeled all 26 disagreements with that context and without the classifier's label.

- Kept his blind label: **17**. Moved to the classifier's label: **7**. Now unsure: **2**.
- Of the 9 items that had restatement context, he kept his label on **7**, including all 6 split/merged items.

So the hypothesis mostly fails. The restructure misses are not explained by what the labeler couldn't see. They are a
genuine difference in how the guide is read: whether text that reappears elsewhere still counts as new disclosure
once its framing changes. The adjudicated numbers (85% agreement, precision 0.94, recall 0.90) are published only
as a secondary figure. Only disagreements were revisited, and the labeler knew it, so they can only flatter the
classifier.

## What this means for using the labels

- A "cosmetic" label on a restructured passage is the classifier's least reliable call. The read view should
  show the restatement context next to it so a reader can judge for themselves.
- A "material" label on a figure-only update reflects the guide's `quantity` rule, which a reader may not share.
- Labels on removed text should be read as the least stable across models.

The prompt is not re-tuned on these findings. The test set has been used once, and tuning against it would make it a
second dev set. Any guide change would need a new decision and a fresh blind sample.
