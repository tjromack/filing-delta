# M6 design: grounded QA that cites or abstains

Status: **proposal, for Trevor's review.** Coverage: the locked corpus. That is 10-K Item 1A and Item 7 with period of
report 2018-01-01 to 2025-12-31, and 10-Q Part I Item 2 and Part II Item 1A filed 2025-01-01 to 2026-09-30, for 11
companies.

## 1. What the survey found (2026-10-19)

| | figure |
|---|---|
| Indexable sections (full text, parse `ok`) | 238 (88 10-K Item 1A, 86 10-K Item 7, 56 10-Q Part I Item 2, 8 10-Q Part II Item 1A) |
| Units (the M3 segmenter's paragraphs, headings and data tables, each an exact span) | 39,158 paragraphs, 11,205 headings, 3,652 tables |
| Paragraph length | median 46 words, 95th percentile 185, longest 962; 2.6 million words in all |

The design problem is **repetition across years**. A risk factor often appears nearly verbatim in eight consecutive
10-Ks (M3 measured this), so a search over the whole corpus returns the right words from the wrong year. Every
answer must cite the filing the question is about.

## 2. The pipeline

```
question ─▶ scope (deterministic) ─▶ retrieve (BM25, in scope) ─▶ answer (model, JSON) ─▶ verify (deterministic) ─▶ Answer | Abstain
              │ out of corpus / advice                                                      │ any quote not exact
              └──────────────────────────────── Abstain(reason) ◀──────────────────────────┘
```

1. **Scope: deterministic, no model.** The question is parsed for company (names and tickers from `corpus.toml`),
   form, and fiscal year or quarter ("2023 10-K", "fiscal 2023", "Q2 2026"), plus an optional section hint ("risk
   factors", "MD&A").
   - A company outside the corpus, or a period outside coverage, abstains immediately, with the reason and no
     model call.
   - A question with no period is scoped to the company's latest filing of the matching form, and the answer says
     which filing it used.
2. **Advice and forecasts abstain by rule** (design pin 6). Requests to buy, sell or hold, for price targets, or
   for what *will* happen to the company or stock get the fixed reason "this tool reports what the filings say; it
   doesn't give investment advice or predictions".
   - Asking what a filing *says* about plans or expectations is allowed: that is reporting the text.
   - The patterns are a short, tested list, and every abstention from them is visible in the run.
3. **Retrieve: BM25** over units within scope (k1 = 1.5, b = 0.75, top 8). It is pure Python, deterministic, and needs
   no key and no download.
   - Embedding search is deferred unless measured retrieval recall (§5) shows BM25 failing.
   - Rejected for now: a local embedding model needs a large download through the TLS proxy and adds
     nondeterminism to tie-breaks, for a gain that hasn't been measured.
4. **Answer: the model** (`ANTHROPIC_MODEL`, default `claude-sonnet-5-5`) sees the passages labeled P1–P8 with their
   filing and section. It returns JSON: `{answerable, answer, citations: [{passage, quote}], reason}`. Instructions:
   - Answer only from the passages.
   - Quote verbatim.
   - Say not answerable rather than guess.
   - No advice or predictions.

   Responses are recorded by request hash (the M4 recorder), so a run replays with no key.
5. **Verify: deterministic.** Every quote must be an **exact substring** of its passage. It is then mapped to
   (accession, section, char start, char end) in the stored section text and re-checked: `text[start:end] == quote`.
   - **If any citation fails, the whole answer becomes `Abstain("citation could not be verified")`.** A partly
     verified answer is never shown (pin 5).
   - The answer type is a tagged union, `Answer(text, citations ≥ 1)` or `Abstain(reason)`, with no third case.
6. **Provenance on every answer:** "From [company]'s [form] for [period], Item 1A / Item 7 (management's unaudited
   discussion)" (FD-DEC 016).

**Exact means exact.** The quote must match character for character, with no folding of curly quotes or dashes. If
the dev runs show the model routinely straightening quotes, the fix goes in the prompt (passages shown verbatim, with
an instruction to copy). Any loosening of the match needs its own decision.

## 3. The verifier's gate tests (forged citations)

The M6 gate is the verifier rejecting each of these, as unit tests:
- a fabricated quote;
- a real quote with one character altered;
- right text, wrong offsets;
- offsets past the end of the section;
- a quote real in another filing but cited to this one;
- a section or accession not in the corpus;
- an empty citation list;
- an answer whose second citation fails while the first passes (it must abstain entirely).

These tests are mutation-checked, like M5's.

## 4. The QA set (FD-DEC 028)

60 questions: **40 answerable, 20 unanswerable.** Every label is Trevor's: answerable or not, the gold span, and a
short gold answer. No system answer is shown while labeling.

| part | count | written by |
|---|---|---|
| Answerable, drafted from sampled passages (stratified by company, section and form; lookup, presence of a risk, a stated figure, a change between two years) | about 28 | Claude drafts the question text; Trevor keeps or rejects it and marks the gold span |
| Answerable, Trevor's own | 12 or more | Trevor |
| Unanswerable by design: a period outside coverage, a company not in the corpus, a plausible detail the filings don't disclose, advice or forecast requests | 20 | drafted by Claude; Trevor confirms each is plausible and unanswerable |

**Order of work:**
1. Trevor writes his 12 or more questions (about 10 minutes).
2. BM25 proposes candidate passages for them. This is the retriever, not the model.
3. All 60 are labeled on one keyboard page (about 45 minutes). Each item shows the question, then candidate
   passages with context. Trevor highlights the answering span, writes a short answer, or marks "not answerable from
   the filings".
4. Three practice items from outside the set come first (the M5 lesson).

The question file is committed before labeling starts, and labels are committed before any QA run on the set. The
set's split by author is published with every result, and exported to Build 4 at M9.

## 5. What M6 measures (M7 then scores with `spancheck`)

- **Retrieval recall@8:** the share of answerable questions whose gold span overlaps a retrieved unit. Deterministic,
  and it tells retrieval misses from answer misses.
- **Verification rate:** the share of model answers whose citations all verify.
- M7 adds citation accuracy, abstention correctness, groundedness, and cost and latency through `spancheck` 0.3.1.

A small dev slice (Claude-written and not part of the 60) tunes the prompt. The prompt is frozen by hash before the
labeled set is run, as in M4.

## 6. Plan once approved

1. `filing_delta/qa/`: scope, index, retrieve, verify. The answer type and the forged-citation tests come first
   (the gate).
2. Answer stage with recorded responses; the dev slice; freeze.
3. Question drafting; Trevor's questions; the labeling page; labels committed.
4. One run on the 60; retrieval recall and verification rate; BUILD-LOG, decisions, commit, stop.
