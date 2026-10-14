# M4 design: the material/cosmetic labeling guide and classifier plan

**Status:** proposed 2026-10-14, awaiting Trevor's approval. No labeling or model code before approval.

The diff (M3) says *what* changed between two filings. M4 adds one judgment per change: **does it matter to a
reader tracking this company's disclosed risks, or is it cosmetic?** That is the only model judgment in the diff
half (pin 3). It is scored against Trevor's labels, with the confusion matrix published.

---

## 1. Scope

| In scope | Out of scope (and why) |
|---|---|
| **Item 1A Risk Factors** changes: 10-K year over year and 10-Q (Part II Item 1A): **5,623 changes** | **Item 7 MD&A** (25,500 changes): mostly numbers rolling forward each year. Judging whether a financial number matters is financial analysis, which the README says this tool doesn't claim. FD-DEC 016 already routes MD&A numbers to an audited cross-check at M5. MD&A diffs are still published, just unclassified. |
| Statuses: reworded, moved *with edits*, split, merged, added, removed | Unchanged, and moved *without* edits: no text changed, so there's nothing to judge. Reported as-is. |

Risk-factor drift is the analyst workflow the playbook names ("what a company newly admits it's afraid of, and what
it quietly stopped saying").

## 2. The labeling guide (what Trevor labels against, and what the model is told)

**The question:** *If you were tracking this company's risk disclosures, would you want this change flagged?*

### MATERIAL: the change alters what the company is telling you about its risks

| Code | Meaning | Generic example |
|---|---|---|
| `new_risk` | A risk, exposure, dependency or event not disclosed before | *added:* "We depend on a single supplier for our advanced chips." |
| `removed_risk` | A previously disclosed risk or event no longer mentioned | *removed:* the paragraph on a government investigation |
| `severity` | Likelihood or severity language strengthened or weakened | "could adversely affect" → "has materially adversely affected"; "may" → "will" |
| `realized` | A hypothetical risk is now described as having happened | "a cyberattack could disrupt…" → "in 2025 we experienced a cyberattack that disrupted…" |
| `specifics` | A new concrete detail: a named event, country, product, counterparty, regulation | "changes in trade policy" → "tariffs imposed by the U.S. on imports from China" |
| `quantity` | A number describing the exposure changed meaningfully | "15% of revenue from China" → "24% of revenue from China" |
| `legal_status` | An investigation, lawsuit or regulatory matter opened, settled, decided or closed | "is subject to an investigation" → "settled the investigation for $X" |

### COSMETIC: the same message, presented differently

| Code | Meaning | Generic example |
|---|---|---|
| `rewording` | Same meaning in different words; sentences split, merged or reordered | "Our business may be harmed if…" → "If…, our business may be harmed." |
| `date_rollforward` | Only a year or period label changed, and the claim itself is the same | "In fiscal 2024 we…" → "In fiscal 2025 we…" (same statement) |
| `cross_reference` | Page, note or section references; renamed defined terms | "see Note 12" → "see Note 13"; "JPMorgan Chase" → "JPMorganChase" |
| `formatting` | Typography, capitalisation, punctuation, headings restyled | "RISKS RELATED TO OUR BUSINESS" → "Risks Related to Our Business" |
| `restructure` | Text moved, split or merged with no change in content | a paragraph moved to a different heading unchanged in substance |

### Tie-break rules
1. **When in doubt between severity and rewording, ask whether the *hedge* changed.** "may" → "could" is
   cosmetic; "may" → "has" is material.
2. **A number change is material if it describes the risk itself** (exposure size, share, count of incidents).
   It's cosmetic if it's a date, a page reference, or a count unrelated to the risk.
3. **Added or removed text is material by default**, unless it is boilerplate (a generic lead-in like "The risks
   below are not the only ones we face"), a heading, or clearly restated elsewhere. For added/removed items the
   sheet shows the closest paragraph on the other side, if any, so you can see a restatement.
4. **Judge only what is shown.** Don't look up whether the risk is important in the real world. The question is
   about the disclosure text, not the company.
5. **"Unsure" is a valid label.** It is counted and published, never guessed into a class.

What this doesn't mean: "material" here is a **text-change category for a reader of risk disclosures. It is not a
legal or accounting materiality determination**, and the README says so.

## 3. The labeled sets

- **Stratified sample of 150 changes** across statuses (reworded by similarity band, added, removed, moved-edited,
  split/merge, formatting-only, numbers-only) and across all 11 companies, sampled deterministically.
- **Split before anyone looks at the model's output: 30 dev / 120 test.** The prompt may be refined on the dev set
  only. The test set is scored once, at the end. Refining the prompt on the test set would be grading my own work.
- **What Trevor sees:** company, years, status, the OLD and NEW text (or the closest counterpart for an
  added/removed item), and the word-level changes highlighted. No model output. **He labels:** material / cosmetic /
  unsure, plus an optional code from the tables above.
- **Effort:** about 30–60 s per item, so roughly 1.5–2.5 hours for 150, in two sittings (dev first, then test).

## 4. The classifier

- **Separate stage** (`filing_delta/classify/`). It reads diff records and writes classifications next to them. It
  never changes the diff (pin 3).
- **One deterministic rule, measured like the model:** `formatting_only` changes (618 of the 5,623; the case and
  punctuation fact from M3) are labeled cosmetic without a model call. Its accuracy is reported separately on the
  labeled formatting-only items. Nothing else is decided by rule.
- **Model:** `ANTHROPIC_MODEL`, default `claude-sonnet-5-5` (CLAUDE.md pin). The system prompt is the guide in
  §2 (prompt-cached). Structured output: `{label, code, rationale (≤ 30 words), evidence}`. `evidence` must be an
  **exact substring** of the old or new text, verified in code, the same rule as M6 citations. A label whose
  evidence fails verification is recorded as `unverified` and counted, not accepted.
- **Sonnet 5.5 can't be made deterministic** (non-default sampling settings are rejected), so reproducibility comes
  from **recording every response** under a request hash in `data/model-cache/` (FD-DEC 007). A cold run replays
  the recordings with no key, and the published confusion matrix reproduces exactly.
- **Comparison:** the same test set on `claude-haiku-5-5` (about $0.10 / $0.50 per MTok). It's cheap and answers
  "how much model does this need", the multi-model comparison the playbook lists.

## 5. Cost (estimate, to be replaced by measured usage)

The 5,623 changes are about 6.9 M characters, roughly 1.75 M tokens of pair text. The guide adds about 2 K tokens per
request, served from cache. At Sonnet 5.5 prices ($2 / $10 per MTok, cache reads $0.20), a full run is **about
$10–30**, mostly output and reasoning tokens. The Batches API halves that. The 150-item dev/test runs cost about $1.
Actual usage is logged from `response.usage` and published.

## 6. What gets published (the M4 gate)

- A **confusion matrix** on the 120 test items, with precision/recall for "material", agreement, and bootstrap CIs.
- **Error analysis:** every disagreement with its rationale and the human label, grouped by code.
- The dev/test split and the prompt version, hashed, so the numbers trace to an exact prompt.
- The Haiku vs Sonnet comparison.
- The full-corpus classification of all 5,623 Item 1A changes, reproducible keylessly from recorded responses.

## 7. What I need from Trevor

1. **Approve or change** the definitions in §2 (codes, examples, tie-break rules). Once labeling starts, they're
   frozen.
2. **Approve the scope** (Item 1A only) and the label sample (150, split 30 / 120).
3. **API access** before the model runs. Either an `ANTHROPIC_API_KEY` in `.env` (gitignored), or `ant auth login`.
   No key is needed for the labeling step.
