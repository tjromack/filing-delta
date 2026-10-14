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
**Status:** The limit is decided. The cross-check is *proposed* and will be decided at M5.

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
