# filing-delta — decisions log

> Append-only. A point-in-time record of the calls made, so they aren't re-litigated. Author: Trevor J. Romack.
> This is BUILD 3 of the portfolio slate: SEC filings drift & grounded QA.
> Format: **Decision · Alternative rejected · Why.** Entries marked *Proposed* await approval.

## FD-DEC 001 — Scope, home, and stack (2026-10-08)
**Status:** Decided (from the playbook v3 kickoff packet, pp. 27–28).

- **Decision:** ingest 10-K, 10-Q and 8-K filings from EDGAR. Diff the narrative sections (Item 1A, Item 7) period
  over period and classify each change as material or cosmetic. Answer grounded questions over the corpus with span
  citations, or abstain. Python. The repo lives at `C:/dev/filing-delta`, remote `tjromack/filing-delta`, private
  until it clears §01 at 14+.
- **Alternative rejected:** a TypeScript build. S1 and B4 carry the TypeScript signal, and B3 reuses `spancheck`
  (Python) directly.
- **Why:** B3 is the second regulated vertical, and it produces B4's finance corpus. Half of it is deterministic,
  which gives the cleanest available story about where a model was used and where it deliberately wasn't.

## FD-DEC 002 — The diff is deterministic; the model judges only after it (2026-10-08)
**Status:** Decided (playbook pin).

- **Decision:** parsing, paragraph alignment and the diff contain no model calls and are golden-file tested.
  Material/cosmetic classification is a downstream stage that reads the diff's output and is scored against hand labels.
- **Alternative rejected:** asking a model to "compare these two risk-factor sections." That's cheaper to build, but
  it's untestable, non-reproducible and can't be cited.
- **Why:** the diff is the evidence, and evidence has to be reproducible. Only the judgment stage gets the model, and
  that stage is scored.

## FD-DEC 003 — Verification is part of the build (2026-10-08)
**Status:** Decided (the portfolio's overriding discipline).

Every milestone ships its check: golden-file tests for parsing and diffing, a published parse-success rate plus
`docs/parse-failures.md`, the material/cosmetic confusion matrix, a 429-storm back-off test, and the `spancheck`
citation/abstention report. If the check isn't written, the milestone isn't done.

## FD-DEC 004 — EDGAR client: httpx + truststore, injectable transport (2026-10-08)
**Status:** Decided.

- **Decision:** build the client on `httpx` with `truststore.inject_into_ssl()`. It has a token-bucket rate limiter
  set conservatively below SEC's 10 req/s ceiling, a required `EDGAR_USER_AGENT` (it refuses to start without one), a
  content-addressed on-disk cache keyed by URL, and exponential back-off with jitter that honors `Retry-After` on
  429/503. The transport is injectable, so tests can replay a scripted 429 storm with no network.
- **Alternative rejected:** shelling out to `curl`, which is the banked proxy workaround clear-pricer used for bulk
  downloads. It works on this machine, but rate limiting, retry semantics and the 429-storm test would all have to
  live outside Python. That makes them harder to test and to read.
- **Why:** the playbook names "REST integration under real rate limits" as a gap this build closes, so the client
  *is* part of the evidence. `curl` stays available for one-off bulk pulls such as golden fixtures.
- **Rate ceiling:** **5 req/s**, half of SEC's 10 (set at M1). `RateLimiter` refuses anything above 10, and
  `test_rate_ceiling_is_never_exceeded` asserts no more than 5 requests in any 1-second window. A 429's
  `Retry-After` pauses the limiter itself, so the wait applies to every request that follows. A 403 is never
  retried, because SEC uses it for undeclared or abusive clients, and retrying would make it worse.

## FD-DEC 005 — Cite-or-abstain is a type, not a prompt instruction (2026-10-08)
**Status:** Decided.

- **Decision:** QA output is a tagged union, `Answer(text, citations≥1) | Abstain(reason)`. A post-generation
  verifier checks that every citation is an exact substring of its stored section at the stated offsets. Any answer
  that fails becomes `Abstain("citation_unverifiable")`.
- **Alternative rejected:** relying on the prompt to make the model cite. That gives no guarantee, and a hallucinated
  citation looks exactly like a real one.
- **Why:** the pin "there is no third option" has to hold even when the model misbehaves.

## FD-DEC 006 — spancheck from PyPI; model id from env (2026-10-08)
**Status:** Decided.

- **Decision:** depend on `spancheck` from PyPI, pinned to a version. The Anthropic model id is read from
  `ANTHROPIC_MODEL`, defaulting to `claude-sonnet-5-5`. Model calls go through a thin provider interface, so a second
  provider can be compared later.
- **Alternative rejected:** vendoring spancheck, which would fork B1 and undercut the claim that it's
  infrastructure. Hardcoding the model id has already broken once (`claude-sonnet-5` was deprecated).

## FD-DEC 007 — Keyless reproducibility via recorded model responses (2026-10-08)
**Status:** Decided (the default was accepted when the scaffold was approved on 2026-10-08).

- **Decision:** cache every model request/response by a hash of (provider, model, prompt, params). Ship the cache,
  together with the EDGAR cache for the locked corpus, as a GitHub Release artifact. A cold clone then reproduces the
  diff, the confusion matrix and the spancheck report **without an API key or a single EDGAR request**. Live mode
  (`--live`) re-runs against the API.
- **Alternative rejected:** making the try-it path require an Anthropic key. §01 Gate 6 scores that a 1, and Gate 6
  can't be zero.
- **Why:** Gate 6 and Gate 1 both need a cold, keyless run. Recorded responses also pin the published numbers to
  exact model outputs.

## FD-DEC 008 — Corpus: companies, filing types, date range (2026-10-08)
**Status:** Decided. Locked 2026-10-08 after the 18-document survey (`docs/design/section-parser.md` §1).

- **Companies (11).** Chosen so that each layout archetype is covered, not by market cap: Apple, Coca-Cola, Netflix,
  Walmart (January FYE), Pfizer, Ford (running headers), Weyco Group (small cap, four filer agents), Berkshire
  Hathaway, JPMorgan Chase (pointer stub, plus a 10-Q that points out to the 10-K), Exxon Mobil (pointer to the
  Financial Section), and General Electric (cross-reference index, the deliberate stress case).
- **10-K:** fiscal years **2018–2025**, eight per company and seven year-over-year diffs. The range crosses the
  2019–2021 iXBRL transition (the parser has to survive both eras) and the FY2019→FY2020 pandemic risk-factor
  rewrite (real, large drift to classify).
- **10-Q:** filed **2025-01-01 → 2026-09-30**. Part II Item 1A and Part I Item 2.
- **Alternative rejected:** the most recent 3 years only. It's cheaper, but it has a single HTML era and no large
  drift event, so it would under-test both the parser and the classifier.
- **Alternative rejected:** dropping GE. It would raise the parse-success rate by hiding the hardest layout.
  Keeping it and publishing its outcome is the point.
- **8-K's role (open):** 8-Ks are event-driven, with no year-over-year counterpart, so they don't fit the diff. The
  proposal is to use them only in the grounded-QA corpus, where they are a good source of unanswerable-but-plausible
  questions. 8-K Item 2.02 points to exhibits, which are out of scope.
- The README will state the exact filing types and date range once this is locked.

## FD-DEC 009 — License: MIT (2026-10-08)
**Status:** Decided (the default was accepted when the scaffold was approved, matching clear-pricer).

## FD-DEC 010 — Section parser: two independent signals, reconciled; lxml (2026-10-08)
**Status:** Decided. Approved 2026-10-08. See `docs/design/section-parser.md`.

- **Decision:** locate boundaries with a heading-grammar scan *and* TOC-anchor resolution, then reconcile them.
  Handle the pointer-stub, cross-reference-index and pointer-out archetypes explicitly. Every (filing, section)
  gets an `ok`/`partial`/`failed` record with reasons and evidence. Canonical text (citation offsets) is kept
  separate from the folded comparison key (the diff). Library: lxml.
- **Alternative rejected:** heading regex alone. The TOC, running headers and archetypes B and C all defeat it
  silently. **Also rejected:** TOC anchors alone. They're missing in the Weyco 10-Q and wrong in GE FY2018.
- **Why:** with two signals, a disagreement becomes a logged `partial` instead of a silently wrong boundary.

## FD-DEC 011 — Corpus windows: 10-K by period of report; amendments excluded (2026-10-08)
**Status:** Decided (M1).

- **Decision:** a 10-K is in the corpus when its *period of report* is in 2018-01-01..2025-12-31. That gives eight
  annual reports per filer whatever the fiscal year end (Apple ends in September, Walmart in January). A 10-Q is in
  when its *filing date* is in 2025-01-01..2026-09-30. Forms are matched exactly, so 10-K/A and 10-Q/A are excluded.
  The windows live in `corpus.toml`, and `corpus/manifest.csv` (committed) lists every accession ingested, with its
  sha256.
- **Alternative rejected:** windows by filing date for 10-Ks. A January-FYE filer then lands its "2025" report in
  2026, and the per-filer year counts stop lining up.
- **Alternative rejected:** including amendments. 10-K/As are often partial (Part III only, or a single exhibit),
  and they'd break year-over-year pairing. If one turns out to restate Item 1A or Item 7, that's a known limitation
  to state, not something to handle silently.

## FD-DEC 012 — A third section kind: `absent` (2026-10-08)
**Status:** Decided (M2; an amendment to the FD-DEC 010 design).

- **Decision:** a section the filer verifiably omitted is recorded as `outcome=ok, form_kind=absent`, with the
  evidence that proves the omission. That means either a 10-Q whose Part II items are found without an Item 1A and
  no "risk factors" heading anywhere in Part II (Exxon and Ford 10-Qs from Q2 2025, Weyco 2026), or a
  cross-reference-index row that says "Not applicable" (GE 10-Qs). The published parse-success rate is `ok`/present;
  absent sections are counted in their own column and are neither successes nor failures.
- **Alternative rejected:** recording them as `failed: no_heading`. That turns a correct reading into a failure and
  hides the difference between "the parser couldn't find it" and "the filer didn't include it".
- **Alternative rejected:** counting them as successes. That would inflate the rate with sections that have no text.

## FD-DEC 013 — Following a pointer: running-header extent, checked against stated pages (2026-10-08)
**Status:** Decided (M2).

- **Decision:** when Item 7 is a one-line pointer (JPM, Exxon), the target section is the run of pages whose running
  header carries its title. It starts at the first header and ends at the page break after the last one. If the
  pointer states a page range ("appears on pages 46–160"), title lines on those pages count even when they aren't
  running headers. Occurrences outside the range are dropped. The page numbers printed inside the slice are then
  compared with the stated range, and a mismatch downgrades the result to `partial`.
- **Alternative rejected:** ending at the next TOC anchor. On Exxon that ended the MD&A after 1,300 characters,
  because the first "anchor" was a line in Exxon's Financial Section TOC.
- **Alternative rejected:** ending at the next Item heading. Exxon's and JPM's MD&As sit *after* Item 15, in the
  financial section, so that ran to the end of the document.

## FD-DEC 014 — TOC-anchored sections end after their TOC group (2026-10-08)
**Status:** Decided (M2).

- **Decision:** where a section has no Item heading (GE everywhere; JPM's 10-Q MD&A), the start is its named TOC
  anchor. The end is the next anchor target *after the section's TOC group*: its own entry plus the entries nested
  under it. Nesting means indented deeper (GE 2020+), or, in an Item-style TOC, entries up to the next Item or Part
  line (JPM 10-Q). For a TOC with no hierarchy around the section (GE 2018–19), the group is every entry that starts
  before the last page the cross-reference index gives for the item; that rule is recorded as
  `end_from_index_pages`. GE's index page ranges then verify every GE section against its printed page footers.
- **Alternative rejected:** the next TOC line as the end. That cuts an MD&A at its first subsection (GE 2025:
  472 characters).
- **Alternative rejected:** the next TOC line *in TOC order*. JPM's 10-Q prints the MD&A before the financial
  statements but lists it after them, so this would have swallowed the financial statements.

## FD-DEC 015 — Running headers need consecutive pages; page numbers need a page break (2026-10-08)
**Status:** Decided (M2; both found as content-loss bugs during the corpus runs).

- **Decision:** short text counts as a running header/footer only if it recurs at least three times in a chain of
  occurrences each within two pages of the previous. A bare number counts as a page number only if it sits next to
  a page break (or, in a document with no page-break markup, outside any multi-cell table row).
- **What it fixed:** the earlier "repeated three times near a page break" rule deleted JPM 2020's real "COVID-19
  Pandemic" subheading, which sat atop three pages far apart, and then read it as "page 19". The earlier "any bare
  1–3 digit block" rule deleted numeric cells from MD&A tables (Weyco's MD&A regained 64 characters of numbers).

## FD-DEC 016 — Narrative sections are unaudited; say so, and consider an audited cross-check at M5 (2026-10-08)
**Status:** The limit is decided. The cross-check was decided at M5: option B (FD-DEC 025).

- **Context (Trevor, M2 review):** Item 7 (MD&A) and Item 1A are management's unaudited narrative. MD&A figures are
  often non-GAAP, and they're only as credible as their reconciliation to the audited financial statements (Item 8).
- **Decided now:** the README and every answer that cites these sections say plainly that the source is
  unaudited management discussion. The tool reports what management *said* and how it changed. It never presents
  a narrative claim as a verified fact.
- **Proposed for M5:** XBRL company facts are tagged from the audited financial statements. M5 could go beyond
  "join facts as context" and check numeric claims in MD&A paragraphs (revenue, net income, segment totals)
  against the audited XBRL values for the same period. Each claim would be labeled *reconciles*, *differs* or
  *non-GAAP / not tagged*. The output would be a published reconciliation rate, scored on a hand-labeled sample.
- **Why not now:** M3 (the diff) doesn't depend on it, and adding it now would widen scope before the core is
  done. Deciding at M5 keeps the queue honest.

## FD-DEC 017 — Diff units and pairing (2026-10-12)
**Status:** Decided (M3).

- **Units:** a section is split into paragraphs, headings (short, no sentence-ending punctuation) and whole *data*
  tables (2+ rows of mostly short cells with a number somewhere). A layout table row is one unit. A lone bullet glyph
  joins the text after it, and a sentence re-joined across a page break stays one unit. Every unit is an exact
  [start, end) span of the canonical text, so later citations can point into it.
- **Unchanged** means equal comparison keys (Unicode compatibility forms, quote and dash styles and whitespace are
  treated as equal). Case and punctuation changes are *reworded* with the deterministic fact `formatting_only`.
  Number-only edits get the fact `numbers_only`. These are observations handed to M4, not materiality calls.
- **Pairs:** each 10-K against the same company's previous 10-K. Each 10-Q against the same fiscal quarter a year
  earlier (consecutive quarters of MD&A differ by design). A pair with a pointer/absent/failed side is a state change,
  with no paragraph diff.
- **Alternative rejected:** line- or sentence-level diff. Filers re-wrap and re-split sentences constantly, and a
  paragraph is the unit a reader means by "newly disclosed".
- **Alternative rejected:** DuckDB for diff storage now. JSON per pair is deterministic and diffable in git review.
  DuckDB comes in with the read view (M8).

## FD-DEC 018 — Alignment thresholds come from human labels (2026-10-12)
**Status:** Decided 2026-10-14: **REWORD_MIN = 0.40** (global and gap pass), the *instance* criterion, and the
whole aligner tuned as it runs. Result: precision 0.83 (95% CI 0.74–0.93), recall 0.80 (0.66–0.93) against 70 human
labels. See the *Resolution* below and `docs/alignment-eval.md`.

- **Context:** the aligner's decision between "reworded" and "removed + added" *is* the product's headline claim
  ("newly disclosed"). The first run used a token-sequence ratio of 0.5 everywhere. Reading the flagged pairs showed
  three failure shapes: a heavy in-place rewording (Walmart ESG, 0.36) reported as removed + added; an expanded
  paragraph (Walmart's India enforcement matter, old text wholly inside a paragraph twice its length, ratio 0.345)
  missed because the ratio punishes length change; and a doubtful match on shared legal boilerplate at 0.72.
- **Interim:** a gap pass (both units in the same gap between in-order neighbours) at ratio ≥ 0.35, plus the global
  pass at ≥ 0.5. Both thresholds are provisional.
- **Decision process:** 70 real candidate pairs, sampled by ratio band × containment bin across all 176 diffs (6,100
  candidates) and shown to the labeler blind (no scores, no current decision). Rules are scored by stratum-weighted
  precision and recall. The final thresholds and any containment rule are chosen from that table and published with
  it. The 70 labeled pairs become a regression test for the aligner.
- **Why not tune by eye:** I picked the examples that exposed the problem, so tuning to them would mean grading my
  own work on my own test set.

**Resolution (2026-10-14).**
- **Criterion: same instance.** The first labeling pass showed that "same disclosure" could be read as "same type".
  Several Y labels paired one template about different subjects (North America vs Asia Pacific unit-case volume; India
  refranchising vs the Odwalla exit). Trevor chose the *instance* criterion: a new event or subject in an old template
  is new information. He re-judged his 54 Y/? pairs as Y (same instance) / T (same template, different instance) / N:
  34 Y, 11 T, 9 N. Both passes are kept (`docs/alignment-labeling.md`, `docs/alignment-relabel.md`). T counts as not
  a match. A40's label was written in its note field ("N") and is recorded as N.
- **Tune the whole aligner, not a pairwise rule.** Under the instance criterion every pairwise rule is weak (ratio >= 0.35:
  precision 0.72), because it can't see that a paragraph's best partner is taken by a better match. The aligner's 1:1
  matching resolves templates (North America pairs with North America), so it was swept as it runs
  (`tools/sweep_alignment.py`): F1 is about 0.82 from 0.35 to 0.45 and falls to 0.74 at 0.50. 0.40 is the middle of
  the plateau.
- **Containment rejected.** Adding "or containment >= c" lowered precision at every c for at most +0.01 recall.
- **Known error classes** (`docs/alignment-eval.md`): template paragraphs about different subjects still matched as
  moved or reworded (5 of 8 false positives); split/merge on short boilerplate (2 of 8); heavy rewordings below 0.40 (most
  of the 8 misses; Walmart FY2025's ESG risk factor is one). Not tuned further against the same 70 labels.
- **Regression test:** `tests/test_alignment_labels.py` holds 0.83 / 0.80 as a floor.

## FD-DEC 019 — A pointer's stated page range is exact (2026-10-12)
**Status:** Decided (M3; a fix to FD-DEC 013, found by the M3 diff's edge flags).

- **Decision:** when a pointer states its pages, the section ends at the end of the stated last page, and the page
  check requires the observed range to equal the stated range. The one-page tolerance stays only for
  cross-reference-index ranges (GE), where a section can legitimately end at the top of its last page.
- **What it fixed:** JPM's MD&A lost its last page (the forward-looking statements) in 5 of 8 years. The running
  header that set the end is printed on alternate pages only, and a one-page tolerance hid the shortfall.
- **Learning:** a tolerance added for one layout masked an error in another. Tolerances are now per-mechanism.

## FD-DEC 020 — M4 scope, labeling guide, and dev/test split (2026-10-14)
**Status:** Decided (Trevor approved `docs/design/materiality.md` as written).

- **Scope:** Item 1A changes only (10-K and 10-Q Part II): 5,623 changes. MD&A diffs stay published but unclassified.
  Judging whether a financial number matters is financial analysis, which the README disclaims, and MD&A numbers go to
  the audited cross-check (FD-DEC 016).
- **Guide:** material codes `new_risk`, `removed_risk`, `severity`, `realized`, `specifics`, `quantity`,
  `legal_status`; cosmetic codes `rewording`, `date_rollforward`, `cross_reference`, `formatting`, `restructure`;
  five tie-break rules; "unsure" allowed. Frozen from the start of labeling.
- **Sample:** 150 changes, stratified over 10 change-type strata, round-robin across all 11 companies, sampled
  deterministically (`tools/materiality_sample.py`). Per-stratum rounding gave **28 dev / 122 test** (the plan said
  30/120). The split is fixed in `tests/golden/materiality_sample.json` before any model output exists.
- **Sheet design:** inline word diffs, with long unchanged runs collapsed so every change is visible; added/removed
  items show the closest paragraph on the other side; nothing is cut; no model output shown.
- **Alternative rejected:** labeling MD&A too. That's 4.5x the items, and the judgment it needs is outside what the
  tool claims.

## FD-DEC 021 — Dev labels pre-filled by Claude; test labels stay blind (2026-10-15)
**Status:** Decided (Trevor chose this option; it narrows the CLAUDE.md pin "a model never produces the labels it is
scored against" to the set that is scored).

- **Decision:** the 28 dev items carry Claude's suggested label, code, confidence and reason. Trevor reviews them
  and changes any he disagrees with. The 122 test items stay blank and are labeled independently, before any model
  output on them is shown. The published confusion matrix comes from the test set only.
- **Why this is safe:** the dev set only steers prompt refinement and is never reported as accuracy. Anchoring there
  can make the prompt fit Claude's own reading, but the blind test set measures that, so it can't hide.
- **Disclosure:** the suggestions are saved verbatim (`tests/golden/materiality_dev_suggestions.json`), and the share
  Trevor overrode is published next to the dev results.
- **Alternative rejected:** pre-filling the test set too. The confusion matrix would then measure agreement between
  Claude and Trevor-after-seeing-Claude, with two Claude models on both sides, so it would be circular.
- **Alternative rejected:** keeping both blind. More rigorous on dev, but it costs Trevor time where independence
  buys nothing that's published.

## FD-DEC 022 — Classifier prompt tuned on dev, then frozen (2026-10-15)
**Status:** Decided. Frozen prompt version `1fd1c7e5bb42` (`tests/golden/materiality_prompt.json`).

- **Setup:** `claude-sonnet-5-5` (the default from `ANTHROPIC_MODEL`), effort `low`, JSON-schema output, and the
  approved guide (§2) verbatim as the system prompt. No server-side fallbacks: a silent model swap would mix models
  into numbers published as one model's, and the Batches API rejects the parameter. Refusals are recorded as their own
  outcome instead.
- **Dev iterations (28 items; dev labels were Claude-suggested, 0/28 overridden, FD-DEC 021):**
  1. Guide only: 24/28. All 4 misses were false "material".
  2. Added restatement context (a deleted or inserted passage found in another paragraph of the section; tie-break
     rule 3 can't be applied without it) and classifier notes interpreting the guide on restatement, headings and
     `specifics`: 24/28. M012 fixed; M103 (a split) became "unsure", correctly saying its context wasn't shown.
  3. Extended the context to split/merged changes: **25/28**, all 28 evidence quotes verified, $0.10 for the run.
- **Stopped there.** The 3 remaining disagreements (M049 heading broadening, M074, M129) are the borderline items Claude
  marked low-confidence when suggesting labels. Tuning until they flip would fit the prompt to 28 examples. The blind
  test set will show whether the prompt generalizes.
- **Guards:** `tools/run_materiality.py test` refuses to run under any other prompt version, or while any test item
  is unlabeled. The guide itself was not edited (FD-DEC 020 froze it); the classifier notes are outside the guide.

## FD-DEC 023 — Full corpus classified by two models via the Message Batches API (2026-10-16)
**Status:** Decided (Trevor chose "both" when offered Sonnet-only or Haiku-only). Report: `docs/materiality-corpus.md`.

- **Scope:** all 5,623 changes in the M4 frame (every changed unit of every full -> full 10-K Item 1A and 10-Q Part
  II Item 1A pair), frozen prompt `1fd1c7e5bb42`, with `claude-sonnet-5-5` and `claude-haiku-5-5`. The 618
  formatting-only changes take the rule path; the 5,005 others need 4,979 distinct requests.
- **Batches, not synchronous calls:** half price, and the requests are byte-identical to the synchronous path, so each
  result is stored under the same request hash and replays the same way with no key (unit-tested). Batch ids are
  persisted, so an interrupted run resumes instead of paying twice. Measured: $7.50 (Sonnet) + $0.45 (Haiku).
- **What it is published as:** label distributions and model-to-model agreement (77.0%, kappa 0.58). That is a
  consistency figure, not accuracy; the only accuracy figures are the blind test set's. Corpus labels are never used
  to tune the prompt.
- **Alternative rejected:** one model only. Cheaper by $0.45 or $7.50, but the comparison shows where the label is
  stable across models and where it is fragile (removed text: 59% agreement), which a single run can't.

## FD-DEC 024 — Adjudication re-check: a secondary number, never the headline (2026-10-16)
**Status:** Decided (Trevor chose "secondary number"). Report: `docs/materiality-eval-test-adjudicated.md`.

- **Setup:** the 26 blind-test disagreements, relabeled by Trevor on a separate page (db collection `recheck`) that
  showed the restatement context the classifier saw, but not the classifier's label or rationale. The labels are
  committed verbatim with their timestamps (`tests/golden/materiality_recheck.json`); the blind sheet is untouched.
- **Result:** 17 held, 7 moved to the classifier's label, 2 unsure. Adjudicated: 85% agreement, precision 0.94,
  recall 0.90, published under the blind 77% / 0.89 / 0.80 and labeled secondary.
- **Why secondary:** only disagreements were revisited, and the labeler knew they were disagreements. Both push
  agreement up.
- **What it settled:** the information-gap hypothesis from the blind error analysis. 7 of the 9 items with
  restatement context held, so the restructure misses are a difference in reading the guide, not missing context
  (`docs/materiality-error-analysis.md`). The prompt is not re-tuned on the test set.
- **Alternative rejected:** replacing the blind labels with adjudicated ones. That is the usual way a reported
  accuracy drifts upward.

## FD-DEC 025 — XBRL facts: inline first, company-facts fallback; consolidated headline claims checked with no model (2026-10-17)
**Status:** Decided (Trevor chose option B from `docs/design/xbrl-join.md` §3). Resolves FD-DEC 016.

- **Source:** facts are read from the inline XBRL inside each cached primary document (132 of 144 filings: exact
  accession, segment dimensions included, no new requests). The company-facts API covers the 12 older non-inline
  10-Ks, with non-dimensional facts only. Every fact records its source, and the two are cross-checked wherever both
  exist.
- **Why not company-facts alone:** it was stale for 3 of 11 companies on 2026-10-17 (nothing after 2026-05-04), and
  it drops dimensional facts.
- **Audited vs. interim:** a 10-K's statements are audited; a 10-Q's are unaudited interim statements. Facts carry
  that label. This corrects the "audited XBRL" wording in FD-DEC 016.
- **Claim checking (option B):** only sentences stating a consolidated headline metric for the filing's own period,
  matched by a written lexicon with no model. Outcomes: `matches`, `no matching tagged value`, `non-GAAP wording`,
  `not checked`. It never says "differs" or "incorrect", because a false mismatch would read as an accusation.
  Precision of `matches` and of `no matching tagged value` is scored against Trevor's hand labels on a sample, and
  coverage is published.
- **Alternatives rejected:** A (context only) leaves FD-DEC 016's concern unmeasured. C (model-extracted claims
  including segments) adds a model stage, more labeling, and segment-mapping judgment; it goes to the backlog,
  scoped by the M5 survey.
- **Storage:** derived facts are JSON per accession (`data/facts/`), like `data/diffs/`. DuckDB stays planned for
  the read view rather than being introduced mid-pipeline.

## FD-DEC 026 — Claim labels are suggestion-assisted, not blind (2026-10-17)
**Status:** Decided (Trevor chose "show it before you answer" over two blind options). Applies to the M5 claim
sample only.

- **What:** the labeling page shows the matcher's answer as "most likely", with its reason, before Trevor answers.
  He accepts it (A) or overrides it. Each saved label records what was suggested.
- **Consequence, stated in `docs/claims-eval.md`:** agreement is anchored on the matcher's answer, so it is not an
  independent estimate of the matcher's precision. The headline figure is the override count, as on the M4 dev set
  (FD-DEC 021). C001 was already discussed as a worked example and is not scored.
- **Why accept it here:** most of the matcher's outcome rests on checkable mechanics (the amount against the table,
  a named subject, a year), and Trevor said he wasn't confident judging scope cold. A reader who sees the reason can
  catch a wrong one. Rubber-stamping is the risk, and the guide asks him to run the four checks before accepting.
- **Alternatives rejected (offered):** reveal after a locked blind answer (it keeps an independent number, at the
  cost of a second look per item); fully blind with an end review (the plan before this decision).

## FD-DEC 027 — M5 closed on the join's verification; the claim check is reported as unvalidated beyond its mechanics (2026-10-17)
**Status:** Decided (Trevor chose "close M5 as is" over a 20-claim blind spot check and a blind re-label of all 100).

- **Result behind it:** the suggestion-assisted labels (FD-DEC 026) accepted 99 of 99 suggestions at a median 5 s
  each. With no overrides they can't separate a correct matcher from an accepted suggestion.
- **What carries M5:** the join is verified by two independent sources agreeing on 65,243 of 65,243 values, plus
  mutation-checked tests. The claim matcher is verified by its mechanics only (deterministic rules, 21 tests,
  16/16 mutations caught, a stated-precision window), and the README says so.
- **Consequence:** no precision figure for the claim matcher is presented as measured. If M7/M10 need one, the
  blind spot check is the cheapest route (about 20 claims, about 10 minutes).

## FD-DEC 028 — The QA set: 60 questions, mixed authorship, labels Trevor's (2026-10-19)
**Status:** Decided (Trevor chose "I draft, you label + add" and "60 (40 / 20)").

- **Composition:** 40 answerable and 20 unanswerable. Claude drafts question *text* (about 28 answerable from sampled
  passages, plus the 20 unanswerable by design). Trevor writes 12 or more of his own. Every label is Trevor's:
  answerable or not, the gold span, the short gold answer. That keeps the CLAUDE.md pin (a model never produces the
  labels it is scored against).
- **Disclosure:** each question records its author, and results are reported by author. Model-drafted questions
  tend to suit a model answering them, which is the reason Trevor's own questions are in the set.
- **Blind:** no system answer is shown while labeling (the M5 lesson, FD-DEC 026/027). Explanation comes up front
  on three practice items outside the set.
- **Alternatives rejected (offered):** Trevor writes all 60 (about 2 hours); Claude drafts all and Trevor only labels
  (fastest, every question model-shaped). Sizes 30 (wide intervals) and 100 (about 2 hours).

## FD-DEC 029 — QA pipeline as built, tuned on a dev slice, frozen (2026-10-19)
**Status:** Decided. Frozen at pipeline `571c5437f514`, prompt `32c1f63639d9` (`tests/golden/qa_pipeline.json`).

- **As designed** (`docs/design/qa.md`): deterministic scoping (company, form, fiscal year/quarter, section hint),
  scope-time abstention for advice, predictions, companies outside the corpus and periods outside coverage, BM25 top
  8, `claude-sonnet-5-5` with JSON output, and an exact-substring verifier where one failed citation abstains the
  whole answer.
- **Added during dev, each for a measured failure:**
  1. A rule against the model's own conclusions ("therefore … the main driver"). Netflix's first answer drew one
     that its quotes didn't state.
  2. A light deterministic stemmer. Netflix's stated reason ("revenues … increased … primarily due to …") was missed
     because the question said "revenue … increase".
  3. **Change questions ranked from the M3 diff.** "What risks did Coca-Cola add between 2022 and 2023" has no topic
     words, so BM25 ranked noise. It now ranks the diff's added units first (removed ones for "dropped"). Each
     passage is labeled with the diff's finding, so the model knows a passage is new rather than guessing from
     excerpts.
  4. Performance words (revenue, cash flow, drove...) point to MD&A.
- **Dev result:** of 14 Claude-written questions (never part of the labeled 60), 12 answered with every citation
  verified exact on the first try, 1 correctly abstained by the model (a salary the sections don't contain), and 1
  abstained by rule (buy advice). No curly-quote failures, so exact matching stays exact. Measured cost of all dev
  iterations: $0.30 (35 calls).
- **Alternative rejected:** loosening citation matching (folding quotes or whitespace). Not needed on dev evidence,
  and it would weaken pin 5.

## FD-DEC 030 — The labeling page shows the system's scope, so labels can say "wrong filing shown" (2026-10-19)
**Status:** Decided (a fix found while merging Trevor's questions).

- **Problem:** the page embeds the sections the pipeline's deterministic scoping selects. One of Trevor's
  questions (QA54) compares Pfizer's Q1 2026 10-Q with its 2025 10-K, and scoping reads it as two Q1 10-Qs. If the
  labeler could only label from what scoping picked, a scoping miss would yield gold "not answerable", the system
  would abstain, and the run would score that as correct: circular, like proposing candidates with the retriever.
- **Fix:** a fifth label, **W ("wrong filing shown")**: the answer should be in the corpus, in a filing or section
  the page didn't show. Scoring counts every W as a pipeline miss, never as a correct abstention.
- **Alternative rejected:** embedding every section of every named company (several MB per company, past the page
  limit across 60 items).

## FD-DEC 031 — The QA answer key: a two-model jury, with Trevor reviewing disagreements (2026-10-20)
**Status:** Decided (Trevor chose "jury, you check disagreements" over a jury plus 20 blind human labels, a
jury-only key, and labeling all 60 himself). It narrows the CLAUDE.md rule "hand labels are human labels" for the M6
QA set, and is disclosed wherever M6/M7 results appear.

- **Why:** labeling 60 questions in full, some needing year-over-year reading of long sections, was too manual.
  Trevor asked whether models could do it.
- **The jury:** `claude-opus-5-5` and `claude-fable-5-1` each label all 60 independently from the full scoped
  section text: a state, exact quotes mapped to sentence-level gold, and a short answer. Neither is the pipeline's
  answering model (`claude-sonnet-5-5`), and neither sees the pipeline's retrieval or answers. Requests are recorded
  by hash, so the key replays with no key. `tools/qa_jury.py`.
- **Trevor's part:** where the two jurors disagree (state differs, or no shared answering sentence), he decides,
  seeing both jurors' labels. Where they agree, their label is the key.
- **What the results can claim:** agreement with a model-built key, human-adjudicated only where the models split.
  This is not an independent human measurement. The jurors' blind spots, where both are wrong the same way, go
  unseen. Trevor's review is anchored by seeing the jurors' answers (the M5 lesson, FD-DEC 026/027). M7 reports it
  that way, and the B4 export marks each label's provenance (jury-agreed or Trevor-adjudicated).
- **Alternatives offered and rejected:** jury plus 20 blind human labels, to calibrate the jury (recommended; it
  keeps an independent number at about 15 minutes); a jury-only key; labeling all 60 by hand (about 45 minutes).

## FD-DEC 032 — M6 results, and the open "no, but" question (2026-10-20)
**Status:** Recorded at the M6 gate. The "no, but" behavior is left open for Trevor, not tuned on the scored set.

- **Run** (pipeline `571c5437f514`, one pass, `docs/qa-eval.md`, $0.34):
  - 35/35 model answers had every citation verify exact; none were withheld.
  - 23/23 key-unanswerable questions abstained: 10 by the model, 13 by scope rules.
  - 35/37 key-answerable questions answered, every one citing the key's passage.
  - Retrieval recall@8: 36/37.
- **Scorer fix before reporting:** QA58's answer cited a sentence Coca-Cola's 10-K repeats verbatim at another
  position. A citation now counts as citing the key's passage if it quotes the same words from the same filing.
  This changes the scorer, not the pipeline.
- **Both misses are "no, but" questions** (QA21 Netflix paid sharing; QA52 Exxon climate litigation), both Trevor's.
  The key's answers are of the form "the filing doesn't tie X to Y; it says Z (cited)". The pipeline abstains,
  because it can cite what a filing says but not an absence. Whether a cited "no, but" is an answer or an abstention
  is a product decision. Changing the prompt now would tune on the scored set, so it goes to Trevor: keep abstaining
  (strict reading of pin 5), or answer "the filing doesn't say X; it does say Z" with Z cited (a new dev slice and
  re-freeze before any re-run).
- **What the numbers can claim:** agreement with a model-built key (FD-DEC 031). The 48 drafted questions scored
  48/48 and Trevor's 12 scored 10/12, which repeats FD-DEC 028's warning that model-drafted questions are the easy
  ones.
