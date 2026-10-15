# filing-delta — build log

A running, dated record of the process, decisions, learnings, and what broke as filing-delta is built. **This is the
primary raw material for the case study.** Keep it specific, and only give numbers that were measured. Per
`CLAUDE.md`, keeping it current is part of each milestone's definition of done.

Entry template: **What happened · Decisions · Learnings · What broke (+ fix) · Open/next.**

## Index (kept current)

| Milestone | Commit | Headline (measured) | The break worth telling |
|---|---|---|---|
| Phase 0 · scaffold | `b01f044` | — | — |
| M0 · parser design | `0c9f22e` | 18 docs / 11 filers surveyed; 4 layout archetypes | Item 7 is a one-sentence pointer at JPM and Exxon |
| M1 · EDGAR client | `df70a0d` | 144 filings / 681 MB; warm re-run = 0 requests; 25 tests | 90 of 245 cold requests were paged history (71 JPM) |
| M2 · section parser | `9338d76` | 270/272 present sections ok (99.3%), 16 absent, 2 failed (exhibit); 28 goldens proposed | lxml reused element ids and merged table rows; two furniture rules deleted real content |
| M3 · paragraph diff | `105e3db` | 176 pairs diffed; aligner precision 0.83 / recall 0.80 vs 70 human labels (instance) | the diff's edge flags caught JPM's MD&A losing its last page; the labeling question was ambiguous |

---

## 2026-10-08 — Phase 0 (scaffold + kickoff)

### What happened
- Started **BUILD 3** of the portfolio slate, *SEC filings drift & grounded QA*, working name `filing-delta`, from
  the playbook v3 kickoff packet (pp. 27–28). The repo is `C:/dev/filing-delta`, remote `tjromack/filing-delta`
  (private until it clears §01 at 14+).
- Scaffolded from the packet before any feature code: `CLAUDE.md`, `README.md`, `TODO.md`, `DECISIONS.md`, this log,
  `.gitignore`, and `.env.example`. The doc conventions were carried over from clear-pricer (B2).

### Decisions (FD-DEC 001–008)
- Decided 001–006: scope and stack; a deterministic diff with the model only downstream; verification-first; an
  httpx + truststore EDGAR client with an injectable transport (chosen over `curl`, so the 429 storm is a unit test);
  cite-or-abstain as a type; spancheck from PyPI, with the model id from env.
- Proposed 007: recorded model responses, shipped in the release, for a keyless cold run (Gate 6).
- Open 008: the corpus (companies, date range, and 8-K's role). It will be locked at M0 after looking at real
  filings.

### Learnings
- The TODO order departs from the packet spine in one place. The section-parser design (M0) comes before the EDGAR
  client (M1), per the prompt seed. The design needs real filings to look at, so M0 pulls a hand sample with `curl`.

### What broke
- Nothing yet.

### Open / next
- Approval of the scaffold. Then M0: show the section-parsing design before implementing it.
- Open questions: the FD-DEC 008 corpus, FD-DEC 007 approval, and the license.

---

## 2026-10-08 — M0 (section-parser design + corpus proposal)

### What happened
- The scaffold was approved. FD-DEC 007 (keyless replay) and MIT (FD-DEC 009) were accepted as defaults.
- Fetched 11 submissions JSONs, then an 18-document sample (11 filers; 10-K and 10-Q; iXBRL and pre-iXBRL; several
  filer agents) with `tools/m0_fetch.py`: curl, declared UA, ≤2 req/s, everything cached under `data/m0/`.
- Surveyed every Item/named heading and every TOC anchor (`tools/m0_survey/`), then wrote
  `docs/design/section-parser.md`.

### Decisions
- FD-DEC 008 corpus *proposed*: 11 filers chosen by layout archetype, 10-K FY2018–FY2025, 10-Qs filed 2025-01-01 →
  2026-09-30. GE is kept on purpose as the stress case.
- FD-DEC 010 *proposed*: heading scan + TOC anchors, reconciled; explicit handling for pointer stubs,
  cross-reference indexes and pointers out; canonical text kept separate from the folded diff key; lxml.

### Learnings
- **Four layout archetypes, not one.** 13 of 18 are linear item headings. JPM and Exxon make Item 7 a one-sentence
  pointer ("appears on pages 46–160" / "Reference is made to … the Financial Section"). GE has no Item headings in
  the body at all, only a cross-reference index at the back mapped to printed page numbers. The JPM 10-Q's Part II
  Item 1A just points to the 10-K.
- **A naive "find Item 7" would silently grab a one-sentence stub for JPM and Exxon.** That's exactly the silent
  break the playbook warned about, found in the sample before any code was written.
- **Running headers are everywhere** (Ford "(Continued)" ×50 in Item 7; JPM's MD&A header ×39). They would be both
  false section starts and noise in the diff.
- **`&#146;` in older filer-agent HTML** decodes to U+0092, not `’` (Weyco FY2015: 299; Berkshire FY2016: 484). Any
  quote-style change would show up as a text "change" unless the decode remaps it and the diff folds quotes.
- TOC anchors resolve in 17 of 18 documents, but GE FY2018 has a dangling one and one that points into the front
  matter. They're a second signal, not the truth.
- `uv pip install --native-tls` works through the TLS-inspecting proxy (new banked gotcha).

### What broke (+ fix)
- The `�` characters in the first survey output looked like a mojibake problem. It was only the Windows console;
  the files are pure ASCII with entities. A byte-level check sorted it out and turned up the real problem
  (`&#146;`).

### Open / next
- **Stop:** approval of the parser design and the corpus lock (FD-DEC 008, 010).
- Then M1: the EDGAR client (rate limiter, cache, 429-storm test).

---

## 2026-10-08 — M1 (EDGAR client + locked corpus fetched)

### What happened
- Corpus (FD-DEC 008) and parser design (FD-DEC 010) approved and locked.
- Built `filing_delta/edgar/`. A `RateLimiter` (5 req/s, injectable clock). A `ResponseCache`: per-URL, sha256-checked
  on read, atomic writes, only 200s cached. `EdgarClient`: a required "Name email" User-Agent; cache → limiter →
  network → retry; equal-jitter exponential back-off; `Retry-After` honored in both delta-seconds and HTTP-date form
  and applied as a *global* limiter pause; 403 never retried; an offline mode. `submissions.py`: recent plus paged
  history, de-duplicated by accession, with pure `select()` against `corpus.toml`. A `filing-delta fetch` CLI writes
  `corpus/manifest.csv`.
- 25 tests, all with a scripted `httpx.MockTransport` and a fake clock (no network, no real sleeping; the suite
  runs in 0.24 s).
- Fetched the locked corpus: **144 filings (88 10-K, 56 10-Q), 681 MB**. Every filer has exactly 8 10-Ks. The 10-Qs
  are 5 per filer, except Apple's 6 (its fiscal quarters put two filings in January). The cold fetch made 245 requests
  with 0 retries, and 19.1 s of the run time was rate-limit sleep.

### Decisions
- FD-DEC 004 is now complete: a **5 req/s** ceiling, the global pause on `Retry-After`, and no retry on 403.
- FD-DEC 011: 10-Ks are windowed by *period of report*, so every filer gets 8 whatever its FYE, and amendments are
  excluded. `corpus/manifest.csv` (committed) is the record of exactly what was ingested.

### Learnings
- **Most of the cold fetch's requests weren't filings.** 90 of 245 were paged submissions history, 71 of them JPM's
  alone. (JPM files enormous numbers of structured-note prospectuses.) Each page lists its `filingFrom`/`filingTo`,
  so pages that end before the window are now skipped. Under the new rule the warm offline re-run touched 215 URLs
  (144 docs + 11 heads + 60 pages), so 30 requests are saved on any future cold fetch. The manifest was unchanged.
- Only **12 of 144** documents are pre-iXBRL; issuers adopted iXBRL faster than the FY2018 window start suggested.
  The pre-iXBRL era is therefore thin. The parser goldens should include several of those 12 on purpose.
- `uv pip install -e ".[dev]" --native-tls` works for the whole dependency set through the proxy.

### What broke (+ fix)
- Nothing broke in the client itself. The first test run was green, so I mutation-checked it rather than trust it:
  ignoring `Retry-After` → 2 tests fail; retrying 403 → 1 fails. Replacing the global limiter pause with an inline
  sleep → **0 fail**. That's an *equivalent* mutant in a single-threaded client (both delay the next request
  identically), not a gap. It would stop being equivalent if fetching ever went concurrent, and then that test
  needs a concurrent variant.

### Open / next
- **Stop:** approval of M1.
- Then M2: implement the approved section parser, with hand-verified boundary goldens (Trevor confirms them) and the
  published parse-success rate.

---

## 2026-10-08 — M2 (section parser + published parse rate)

### What happened
- M1 approved. Built `filing_delta/parse/` to the approved design:
  - `blocks.py`: decoding, C1 remap, and a block stream that never drops text sitting beside child blocks.
  - `headings.py`: the heading grammar, furniture, and TOC detection.
  - `locate.py`: two signals reconciled, archetypes B/C/D, the outcome model, and the sanity gates.
  - `report.py` / `golden.py`: published outputs.
  - New CLI commands: `filing-delta parse` and `filing-delta golden`.
- Ran the parser over all 144 filings after every change and read the failures in the filings themselves before
  touching code. The first full pass had 10 failed and 41 partial sections. The final pass has
  **270 of 272 present sections `ok` (99.3%)**, 16 verified-absent, 0 partial, and 2 failed. The two failures are
  Pfizer FY2018–19, whose MD&A is incorporated from the annual "Financial Report" exhibit, as design §3 anticipated.
- **The 99.3% is the parser grading itself through its sanity gates. It is not proof.** So I read the first and
  last characters of every 10-K section. That turned up two more defects (a trailing "Parts I and II" heading in
  JPM's Item 1A, and title lines left at the top of GE 2018–19) and cleared one suspect: Netflix 2019's MD&A really
  does end on a table. The real check is the 28 golden boundaries, which Trevor confirms in `docs/golden-review.md`.
- Tests: 22 mechanism tests plus 28 golden sections plus a hygiene test, on top of M1's 25. The suite has 77 tests.

### Decisions
- FD-DEC 012 (`absent` kind), 013 (pointer → running-header extent, checked against stated pages), 014
  (TOC-group end; GE's index as the check), 015 (furniture rules tightened). Design §5 lists the amendments.

### Learnings
- **The page check earned its keep.** Once GE's cross-reference index page ranges were compared with the page
  footers inside each slice, every boundary rule that looked fine by eye but was wrong got caught: GE's MD&A cut at
  its first subsection, JPM 2019–20 picking up the MD&A header on pages outside the MD&A, and GE 2018–19's flat TOC.
- **Two "furniture" rules were deleting real content.** One treated any bare number as a page number, which ate
  table cells. The other treated anything repeated three times near a page break as a running header, which ate
  JPM's "COVID-19 Pandemic" subheading. Both now need structural evidence (FD-DEC 015). Removing text is the
  dangerous operation, so it needs the strictest rules.
- **The 10-Q Part II Item 1A is often simply not there** (Exxon, Ford, Weyco 2026). Which section kinds can exist
  turned out to be a design question, not a parsing detail.
- Real layouts beat the design's guesses in a few places. JPM prints its MD&A title once, then ~38 pages of segment
  headers, then the title again on alternate pages. Berkshire repeats the Item 2 heading as the running header. GE
  runs its headings into the first paragraph.

### What broke (+ fix)
- **lxml proxy ids.** Table rows were keyed by `id()` of lxml element proxies, which lxml reuses after garbage
  collection, so unrelated rows merged. That produced GE's "Item 1C. Cybersecurity 23 Part III" and Exxon's missing
  headings. Fixed with a row counter; `test_rows_are_never_merged_across_tables` builds 3,000 tables to keep it
  fixed.
- **Backspace characters in regex source.** Patching code through a shell heredoc turned `\b` into 0x08, three
  times, and the regexes silently stopped matching (the GE page check found nothing; the Part-entry rule never
  fired). Fixed with the Edit tool. Now a CLAUDE.md gotcha plus `test_repo_hygiene.py`.
- **A silently skipped check.** The first index page check never ran on GE, because its rows say "7-22" without the
  word "pages". Fixed, and a range that can't be checked is now recorded as `page_range_not_stated` instead of
  passing quietly.
- **The tightened title-line rule.** A fixture showed a one-sentence pointer stub starting with "Management's
  discussion and analysis…" being dropped as a "title". The corpus escaped only because JPM's stubs are long. The
  rule now requires a bare title (title plus at most 60 characters, no sentence).
- **A false alarm on coverage.** Weyco's 94–98% "text coverage" was 3,422 zero-width spaces that my metric counted
  and the block stream rightly treats as whitespace.

### Open / next
- **Stop:** Trevor confirms (or corrects) the 28 golden boundaries in `docs/golden-review.md`, then approves M2.
- Then M3: paragraph segmentation and the deterministic period-over-period diff.

### 2026-10-08 — M2 review note (Trevor)
- MD&A isn't credible on its own unless the audited sections back it. Recorded as FD-DEC 016: an explicit
  "unaudited narrative" limit in the README now, plus a proposed M5 option to reconcile MD&A numeric claims
  against audited XBRL facts. A good catch for the case study: it sharpens what "material change" can and can't mean.

---

## 2026-10-12 — M2 closed (golden boundaries confirmed)

### What happened
- Trevor reviewed the 28 proposed golden boundaries (14 filings, every archetype and era) against the EDGAR filings,
  using `docs/golden-review-worksheet.md` as the procedure. He confirmed all 28 and reported "no alarming notes
  overall". The confirmation was given in the session, not written into the worksheet, so the per-entry record is
  `"status": "confirmed"` plus a dated note in `tests/golden/sections.json`.
- The golden tests now enforce human-confirmed boundaries, not just the parser's own output: 77 tests pass.

### Learnings
- Trevor's question afterwards ("what exactly is the purpose at this point?") is worth keeping for the case study.
  The goldens are the only check in M2 that isn't the parser grading itself. The 99.3% rate comes from the parser's
  own sanity gates, and the goldens are what make it believable. Next time, explain the *why* of a human-review step
  before asking for it, not after.

### Open / next
- M2 is done pending Trevor's approval to start M3: paragraph segmentation and the deterministic diff.

---

## 2026-10-12 — M3 part 1 (diff built; thresholds waiting on human labels)

### What happened
- M2 closed and M3 started. The parser's block map now carries table and row ids (text unchanged, all 28 goldens
  still pass).
- Built `filing_delta/diff/`:
  - `segment.py`: paragraph, heading and data-table units, each an exact canonical span.
  - `normalize.py`: comparison keys that treat quote style, dash style and whitespace as equal.
  - `align.py`: exact → global fuzzy (≥ 0.5) → gap pass (≥ 0.35) → max-weight in-order chain → split/merge.
  - `run.py`: pairing, anomaly flags, `docs/diff-report.md`.
- `filing-delta diff`: 200 pairs, 176 diffed paragraph by paragraph, 24 recorded as state changes.
- **Trevor asked whether there would be more chances to confirm the parsing is right.** This milestone answered it
  on its first run: the diff's edge flags exposed a parser boundary error that M2's own checks had passed (below).
- Tests: 17 synthetic diff tests plus 3 corpus invariants. The suite has 97 tests.

### Decisions
- FD-DEC 017 (units, keys, pairing), 018 (thresholds from human labels; pending), 019 (a pointer's stated page range
  is exact).

### Learnings
- **The diff is a second check on the parser.** A boundary that is wrong by one page is invisible inside one filing
  but shows up as text appearing and disappearing at the edge of the section from year to year.
- **The aligner decides the headline claim.** "Removed + added" versus "reworded" is the difference between "newly
  disclosed" and "the same risk, rewritten". Three concrete failure shapes appeared in one Walmart pair. The
  thresholds therefore come from a blind, stratified human labeling sample, not from tuning on the examples I found.
- **Expansion breaks ratio similarity.** An old paragraph wholly contained in a new one twice its length scores 0.345.
  Containment is now a candidate measure in the labeling sample.

### What broke (+ fix)
- **JPM's MD&A lost its last page in 5 of 8 years.** The end came from the last running header, and JPM prints that
  header on alternate pages. M2's one-page tolerance (meant for GE's index) hid it. Fix: end at the stated last page,
  exact check for stated pointer ranges (FD-DEC 019). The JPM 2021 remainder turned out to be JPM's own stated range
  excluding the forward-looking statements that year.
- **Two weak tests.** The first diff tests passed with the ordering weight removed and with the global fuzzy pass
  removed. One test case couldn't tell weighted from unweighted ordering, and the new gap pass covered for the global
  pass. Added targeted tests; all 5 mutants are now killed.
- **Shell quoting again.** A `python -c` one-liner with Windows backslashes failed to parse. Probes are now script
  files in the scratchpad.

### Open / next
- **Stop:** Trevor labels the 70 pairs in `docs/alignment-labeling.md`. Then thresholds are set from
  `tools/eval_alignment.py`, the diff is re-run, flags are re-checked, precision/recall are published, and M3 is
  committed for the gate.

---

## 2026-10-12 — M3 part 2 (labels in; a segmentation fix; a question about what the labels mean)

### What happened
- Trevor labeled all 70 pairs (67 Y/N, 3 '?') and added notes. One note ("NEW cuts off early… others too") led to a
  systematic check: 4.8% of paragraph units ended mid-sentence. The cause was the parser re-joining a page-split
  sentence only when the continuation started lowercase ("…information on the" | "Company's…" stayed split). Fixed
  with a capitalised-continuation rule, limited to page breaks, paragraph-length blocks, and non-heading,
  non-list, non-table continuations.
- The fix changed 3 confirmed golden texts by exactly one paragraph break each. Golden entries now carry a
  whitespace-insensitive `words_sha256`, and `filing-delta golden --rederive` refreshes a confirmed entry *only* if
  its words are unchanged. The 3 were verified against the confirmed texts and refreshed. Anything else still fails
  and needs a human.
- Before the fix changed unit numbering, the labeled texts were frozen into `tests/golden/alignment_sample.json`, so
  the evaluator maps labels to current units by text.
- Threshold set provisionally to 0.35 (pairwise rule: precision/recall 0.90/0.90 against the labels). But the aligner
  *as it runs* scores 0.94/0.71. The gap comes from 1:1 matching: a labeled "Y" partner is often already the better
  partner of a different old paragraph.

### Learnings
- **Reading the labels shows the labeling question was ambiguous.** Several Y labels pair *the same template about a
  different subject* (North America vs Asia Pacific unit-case volume; India refranchising vs Odwalla discontinuation).
  Trevor's notes say "similar type of disclosure". For a "newly disclosed" tool, a new event in an old template is
  new. The instructions said "same disclosure… not a new topic", which doesn't separate *type* from *instance*
  clearly. Asked Trevor to decide the criterion rather than reinterpreting his labels myself.
- Mid-sentence endings: what remains is ~950 lead-ins to bullet lists (by design: each bullet is its own unit so a
  new bullet is visible) and ~210 (0.7%) splits without a page break. Recorded as a known limitation.

### Open / next
- Trevor: the label criterion (type vs instance). Then re-score, finalize the threshold, publish, and add the labels
  as a regression test.

---

## 2026-10-14 — M3 closed (instance labels, whole-aligner threshold, published precision/recall)

### What happened
- Trevor chose the *instance* criterion (a new event or subject in an old template is new information) and
  re-judged his 54 Y/? pairs: 34 Y, 11 T (same template, different instance), 9 N. One label was written in a
  note field ("N") and recorded as N. His first-pass labels are kept.
- Under instance labels, every single-cutoff rule was weak (ratio ≥ 0.35: precision 0.72). The whole aligner does
  better because its 1:1 matching resolves templates, so it was swept as it runs (`tools/sweep_alignment.py`, 35
  filing pairs re-diffed in memory per threshold). F1 is about 0.82 from 0.35 to 0.45, then 0.74 at 0.50. Set
  **REWORD_MIN = 0.40**, the middle of the plateau.
- Published: **precision 0.83 (95% CI 0.74–0.93), recall 0.80 (0.66–0.93)**, stratum-weighted, with a stratified
  bootstrap (2,000 resamples, fixed seed). `tests/test_alignment_labels.py` holds those as a floor. 98 tests pass.
- Re-checked the flags at 0.40: 7, all explained (`docs/diff-anomalies.md`). Walmart FY2025's ESG rewording (0.36/0.38)
  stays a reported miss, and is deliberately not tuned away.
- The capitalised page-break join (part 2) now accounts for 2,934 joins corpus-wide (all join kinds).

### Decisions
- FD-DEC 018 resolved: the instance criterion, the whole-aligner sweep, 0.40, and containment rejected (it lowered
  precision at every setting for at most +0.01 recall).

### Learnings
- **The labeling question decided more than the threshold did.** Under "same type" the best rule scored 0.90/0.90;
  under "same instance", which is the one the product claims, the same data scored around 0.82. The definition was
  the real design decision, and only the user could make it.
- **Pairwise metrics mislead when the system pairs one-to-one.** A pair can be "similar enough" and still correctly
  unmatched because each paragraph has a better partner. Measure the whole system as it runs.
- **Error classes, not more tuning.** The 16 remaining disagreements group into template false-matches, split/merge
  on short boilerplate, and heavy rewordings below 0.40. These go into the README limits, not into another round of
  fitting the same 70 labels.

### What broke (+ fix)
- **Backticks in a double-quoted shell string.** A `python -c "..."` used to write DECISIONS text containing
  `docs/...` paths made bash execute four repo files as shell scripts. Markdown `>` lines became redirections and
  created one empty stray file (`CONSOLIDATED`), and the paths were replaced with their output. Checked the damage:
  the stray file was deleted; Trevor's relabel file was verified to contain exactly his labels (its diff is only his 53
  labels plus the A40 N); four DECISIONS references were restored with the Edit tool; the evaluation and sweep were
  regenerated (identical numbers). Banked in CLAUDE.md.

### Open / next
- **Stop:** M3 approval. Then M4: the material/cosmetic classifier. It starts with a labeling guide written before
  any labeling, and the hand-labeled set is Trevor's.

---

## 2026-10-15 — M4 part 1 (guide, sheets, dev labels, classifier, frozen prompt)

### What happened
- M4 design approved (FD-DEC 020): Item 1A only (5,623 changes), the guide with 12 codes and 5 tie-break rules, and a
  150-item stratified sample split 28 dev / 122 test.
- Trevor asked whether Claude could pre-fill labels. The answer: yes for dev, no for test. Pre-filling the scored set
  would make the confusion matrix measure Claude against Claude-as-reviewed. Trevor chose "pre-fill dev, test blind"
  (FD-DEC 021) and agreed with all 28 suggestions.
- Built `filing_delta/classify/`:
  - prompt: the guide verbatim, plus a hashed prompt version;
  - recorder: replays responses by request hash, and offline mode fails loudly;
  - classify: the formatting rule, JSON output, and exact-substring evidence;
  - context: restatement context for tie-break rule 3.
- Dev runs on Sonnet 5.5 at low effort: 24/28, then 24/28, then **25/28**. Every evidence quote verified, $0.09–0.10 per
  run. Prompt frozen at `1fd1c7e5bb42` (FD-DEC 022). The offline replay reproduced the dev evaluation byte for byte.
- 113 tests pass (11 classifier + 4 context tests added).

### Learnings
- **The classifier's errors were missing context, not judgment.** The first misses included a paragraph whose
  "removed" text had been moved to another paragraph. A human applies "restated elsewhere" from memory of the section,
  so the classifier had to be given the same view.
- **The model said so when it lacked context.** On the split item it answered "unsure… it may appear elsewhere, which
  isn't shown", which pointed straight at the gap.
- **Where to stop tuning:** after the context fix, the remaining disagreements were exactly the items flagged
  low-confidence while suggesting labels. Fixing those would be fitting the prompt, not improving it.

### What broke (+ fix)
- **The sampler overwrote the labeled dev sheet** when it was re-run to check a refactor. It was restored from git (the
  committed copy held the agreed labels), and the sampler now refuses to overwrite a sheet that contains any label.

### Open / next
- Trevor labels the 122 test items blind. Then: the test run with the frozen prompt, the confusion matrix and error
  analysis, the Haiku 5.5 comparison, and the full 5,623-change run.

### 2026-10-15 — test labeling sped up (keyboard labeling page)
- Trevor found the markdown labeling slow. Options offered: a keyboard page (no rigor cost), a smaller test set
  (wider CIs), or pre-filling (rejected: it would make the published accuracy measure agreement with Claude). He
  chose the keyboard page and kept all 122 items.
- `tools/build_label_app.py` builds the page from the same frozen sample and the same inline diff the sheet uses,
  with no model output. Published as a private artifact. Labels save one document per item to its `db`, owner-only
  (verified: a probe write was read back and was invisible at a lower access level, then deleted).
  `tools/import_app_labels.py` copies them into `docs/materiality-labels-test.md`, refusing to overwrite a differing
  label, so the committed sheet stays the record.
