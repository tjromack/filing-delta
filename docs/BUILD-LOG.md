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
| M4 · materiality classifier | `8df0811` (approved) | blind test, scored once: agreement 77%, precision 0.89 / recall 0.80 vs 122 human labels; 5,623 corpus changes, Sonnet–Haiku agreement 77.0% (kappa 0.58), $7.95 | the information-gap explanation for the misses was tested by a re-check and mostly failed: a guide-reading difference, not missing context |
| M5 · XBRL facts join | `7da4250` (approved) | inline vs. company-facts API: 65,243/65,243 values equal; 1,085 MD&A headline claims, 194 match, 878 not checkable (segments, other periods) | suggestion-assisted labels came back 0/99 overrides at 5 s each: no evidence, reported as such |
| M6 · grounded QA | `3c9b650` + v2 (approved) | 35/35 answers verified exact; 23/23 correct abstentions; recall@8 36/37 against a model-jury key (58/60 jurors agreed) | labeling in the claude.ai viewer failed; a local labeling server and a model jury replaced it; misses are "no, but" questions |
| M7 · spancheck | `9357eca` + v3 (approved) | v3: provenance 89/89; answers entailed by their own citations 59/60 (51 in v2); p50 2.6 s; $0.38 per 60 | 9 answers add true but uncited details; the exact-substring verifier can't see that, the judge can |

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

---

## 2026-10-16 — M4 part 2 (blind test scored once; Haiku comparison)

### What happened
- Trevor labeled all 122 test items in the keyboard page (about 79 active minutes, median 16 s per item): 68 M,
  50 C, 4 U, no codes or notes. Imported into the sheet and committed (`fa12731`) **before** any test-set model
  output existed.
- His stated rule of thumb: wholly new or wholly removed text is material, including long or much longer paragraphs
  on a related disclosure. That's the guide's default for added/removed text (tie-break 3), applied broadly.
- **One scored run, frozen prompt `1fd1c7e5bb42`, Sonnet 5.5:** agreement 89/115 (77%). "Material": precision
  **0.89** (95% CI 0.81–0.96), recall **0.80** (0.68–0.89), stratum-weighted. 3 answers not scored (2 unverified
  evidence, 1 code mismatch). $0.41.
- **Haiku 5.5, same prompt and set:** 84/114 (74%), precision 0.84 (0.74–0.94), recall 0.77 (0.65–0.87), 4
  unverified, **$0.02**. The confidence intervals overlap almost entirely.

### Learnings
- **Dev and test erred in opposite directions.** On dev (labels suggested by Claude) the classifier over-called
  "material". On the blind test it under-called it: 17 misses against 9 false alarms. Claude-suggested dev labels
  and an independent human differ systematically, which is exactly why FD-DEC 021 kept the test set blind.
- **The misses concentrate where the labeler and the classifier saw different things.** Split/merged changes
  scored 3/9, and 11 of the 17 misses are coded `restructure`. The classifier was given restatement context (where
  else in the section the text appears), while the labeling sheet showed only the OLD and NEW paragraph. A merged
  paragraph that grew from 136 to 1,484 characters looks like new disclosure without that context and a restatement
  with it. Labels, like predictions, depend on what the labeler is shown.
- Formatting-only (the rule path, no model) was 10/10. Near-identical rewordings (0.95–1.00) were 11/11.

### Open / next
- Decisions for Trevor: (1) an optional adjudication pass on the disagreements, with the context the classifier saw,
  published *beside* the blind numbers and never replacing them; (2) the model and cost for the full 5,623-change run.

### 2026-10-16 — full-corpus run (Sonnet 5.5 + Haiku 5.5, Message Batches)
- Trevor's decisions: (1) adjudicate the 26 disagreements with the classifier's context, published as a secondary
  number beside the blind one (re-check page built, labels pending); (2) classify the whole corpus with both models.
- `tools/classify_corpus.py` builds every in-frame change (5,623, which matches the sampling frame), skips anything
  already recorded, and submits the rest in 2,000-request batches. `collect --wait` polls, then writes each result
  into `data/model-cache` under the same request hash the synchronous path uses (`Recorder.record`, unit-tested
  to replay identically). All 9,708 batch requests succeeded, with no errors or expirations.
- `report` runs with no key (replay only) and writes `docs/materiality-corpus.md`. Sonnet: 2,512 material /
  2,964 cosmetic / 74 unsure; 73 changes not answered (67 unverified evidence, 6 code mismatch). Haiku: 2,412 /
  2,665 / 437; 109 not answered. Agreement on the 4,840 model-path changes both answered: **77.0%, kappa 0.58**.
  Cost **$7.50 + $0.45**.

### Learnings
- **Agreement is lowest exactly where the blind test was weakest.** Removed text: 59% agreement, and Haiku answers
  "unsure" on 244 of 848 removed changes against Sonnet's 32. Added text: 75%. Near-identical rewordings and
  numbers-only changes: 82–97%. Wholly new or removed text is where the label depends most on judgment, and it is
  also where Trevor's labels and Sonnet's diverged.
- Haiku calls more rewordings material than Sonnet (666 vs 527 at similarity 0.80–0.95). The largest off-diagonal
  cell is Sonnet cosmetic / Haiku material (425).
- Coverage note: 5,585 of the 5,623 changes are 10-K Item 1A. Only 38 come from 10-Q Part II Item 1A, because most
  10-Qs refer back to the 10-K rather than restating risk factors.

### What broke and the fix
- The first report counted 26 byte-identical changes twice in the cost ($7.52 for "4,867" responses, but only 4,841
  were submitted). Cost now counts each distinct request once.
- `python` on PATH lacks lxml. Tests and the keyless report run under `.venv/Scripts/python`.

### Open / next
- Trevor labels the re-check page, then the adjudicated agreement goes beside the blind numbers.
- M4 gate: error analysis write-up (the information-gap finding goes in the README limits), TODO and README
  verification rows, commit, stop.

### 2026-10-16 — adjudication re-check scored; M4 error analysis
- Trevor relabeled the 26 disagreements with the classifier's restatement context: 17 held, 7 moved to the
  classifier's label, 2 unsure. `tools/score_recheck.py` imports the labels once (it refuses to overwrite) and
  publishes the adjudicated figures (85% · P 0.94 · R 0.90) as secondary, under the blind headline (FD-DEC 024).
- Wrote `docs/materiality-error-analysis.md` and the README verification row and limits.

### Learnings (and a correction)
- **Correction to the M4 part 2 entry.** I attributed the blind misses to an information gap: the classifier saw
  restatement context and the labeling sheet didn't. The re-check tested that and it mostly failed. Shown the
  context, Trevor held 7 of the 9 items that had it, including all 6 split/merged ones. The restructure misses are
  a real difference in reading the guide: the classifier's notes treat restated text as cosmetic, while Trevor
  treats a restructure that adds or drops disclosure as material. A plausible explanation needed a test, and the
  test disagreed with it.
- The remaining false alarms include 3 numbers-only updates the classifier coded `quantity`, which Trevor reads as
  routine updates. Both patterns are guide-boundary disagreements, not random noise.
- The re-check ran at a median of 4 s between labels (blind pass: 16 s). The items were already familiar, but it is
  recorded as a fact on the report.
- No prompt re-tuning on these findings: the test set has been used once.

### Open / next
- M4 gate: stop for Trevor's approval. Next is M5 (XBRL join; decide FD-DEC 016).

### End of day 2026-10-16 — handoff
- State: M4 complete and committed; **waiting for Trevor's approval** before M5. Working tree clean, pushed.
- Reproducibility caveat for the gate: every M4 report replays byte-identically with no key, but only from the
  local `data/model-cache` (gitignored). A clean clone gets it when the cache ships as a release artifact (M8).
- Run project tools with `.venv/Scripts/python`. The system `python` lacks lxml.
- Next session: on approval, start M5 (XBRL company facts through the same EDGAR client; decide FD-DEC 016).

---

## 2026-10-17 — M4 approved; M5 survey and design

### What happened
- Trevor approved M4 ("Fine to proceed. M4 Approved"). That covers the blind result as the headline, the two weak
  spots left as documented limits rather than fixed by re-tuning, and the docs' description of his labels.
- M5 started the way M0 did: survey real data before designing. The company-facts API was fetched for all 11
  companies (11 requests, cached), and three probes were committed so every figure in the design reproduces:
  `tools/xbrl_probe_values.py`, `tools/xbrl_probe_claims.py`, `tools/xbrl_probe_inline.py`.
- Wrote `docs/design/xbrl-join.md`: the join (in scope regardless) and three options for FD-DEC 016, recommending
  B (consolidated headline claims, no model).

### Learnings
- **The company-facts API lags.** Coca-Cola, Exxon and Ford have nothing filed after 2026-05-04, so their July 10-Qs
  have no facts there. The inline XBRL already in the cached documents covers 132 of 144 filings, exactly by
  accession, and the July filings are among them.
- **The company-facts API drops dimensional facts.** 85% of JPMorgan FY2019's numeric facts carry a segment or
  geography dimension, and most MD&A claims are about segments.
- **Value-only matching is noise.** Half of all MD&A dollar amounts "match" some fact from the same filing, because a
  rounded "$6.9 billion" spans $100M. Concept-aware matching narrows the 1,056 headline claims to 198 consolidated
  matches; segment claims need judgment.
- **10-Q statements are unaudited interim statements**, a correction to FD-DEC 016's "audited XBRL" wording. Labels
  must say which kind a fact came from.

### Open / next
- Trevor chooses the FD-DEC 016 option (A context only / B consolidated, no model / C model-extracted).
- Then: the extractor and period alignment with golden fixtures, the two-source cross-check report, and (if B) the
  claim matcher and the labeled sample.

### 2026-10-17 — M5 part 1: the facts join
- Trevor chose option B for FD-DEC 016 (recorded as FD-DEC 025, with the source decision).
- `filing_delta/xbrl/`:
  - `inline.py` is a pure extractor, with transforms for every format the corpus uses (scanned first: seven
    formats, filer-specific unit ids).
  - `periods.py` covers duration classes and the headline set. `companyfacts.py` is the fallback. `facts.py`
    holds the Fact type and its provenance rendering.
  - `filing-delta facts` writes `data/facts/` and `docs/xbrl-report.md`. The run makes 0 network requests and
    is byte-identical across runs.
- **Result:** 296,557 distinct facts from 144 filings, 0 extraction issues, and 132/132 document period ends
  matching EDGAR. The two independent sources agree on **65,243 of 65,243** values.

### What broke and the fix
- **First cross-check: 99.83%, not 100%.** The 113 differences were all one pattern: a fact tagged twice in the
  same filing, rounded in prose ("$4.9 billion", decimals -8) and exact in a table (4,861 million). The extractor
  kept whichever came first and logged 602 "conflicts". XBRL treats those as consistent duplicates, so the
  precise one now wins. Issues fell to 0 and agreement to 100%.
- **Pfizer FY2019 had 77 facts**, only the cover page: its statements are in Exhibit 13, outside the primary
  document. Rule: when most of a filing's company-facts values are missing inline, use company-facts for that
  filing and record why. It is the only such filing.
- **10-Q operating cash flow "not tagged" in 31 filings** was wrong: cash-flow statements are year-to-date only.
  10-Q flows now fall back to year-to-date, labeled as such.
- JPMorgan's 10-Qs tag total net revenue as `RevenuesNetOfInterestExpense`, and Ford FY2018 tags cash flow only as
  the continuing-operations variant. Both were added as later-preference concepts, and the concept used is
  recorded per filing.
- **A mutation check caught two weak tests.** The fixture listed the precise value first, so plain equality
  passed. And the company-facts accession filter survived because the right row came first. Both fixtures were
  reordered; all 9 mutations are now caught.

### Learnings
- The genuine "not tagged" gaps are structural: banks, insurers, Exxon, GE and Pfizer don't tag operating income,
  and Berkshire doesn't tag diluted EPS. They show as "not tagged", never as zero.
- 2,257 consolidated values were restated between filings (127 headline). The report surfaces them without
  choosing a winner.

### Open / next
- The claim matcher (option B), its sample, Trevor's labels, and the published precision and coverage. Then the gate.

### 2026-10-17 — M5 part 2: the claim matcher, frozen; sample ready for blind labels
- `filing_delta/xbrl/claims.py` is the option-B matcher: pure and deterministic, with an exact span for every
  claim. `filing-delta claims` writes `data/claims/` and `docs/claims-report.md`.
- I developed the rules by reading samples of each outcome myself, with no labels involved. Each round found a
  real failure mode:
  1. **Implicit segment subjects.** JPMorgan's business-line sections open with "Net income was $3.0 billion",
     and the subject is in a heading pages earlier. 154 false "no matching" results. Fix: an amount nowhere near
     (more than 25% from) the consolidated value goes to `not checked`, as another scope.
  2. **Period cues in headings.** "Year-to-date results", "Quarterly results", and Exxon's bare-year headings
     ("2023") over prior-year paragraphs. The nearest short heading now feeds the period decision. A unit test
     then caught that `\bquarter\b` never matched "Quarterly".
  3. **The wrong net-income concept.** "Attributable to Ford" was compared with `ProfitLoss`, which includes
     noncontrolling interests. Ford tags the attributable figure as
     `NetIncomeLossAvailableToCommonStockholdersBasic`. Concepts now follow the phrase's own qualifier, and all 7
     Ford "mismatches" disappeared.
  4. **Fiscal year.** Walmart's quarter ended April 30, 2025 is fiscal 2026, and Weyco's FY2021 10-K cover tags
     `DocumentFiscalYearFocus` as 2020, a filer error. The fiscal year is now derived from the period end and the
     fiscal-year-end date, which covers wherever the cover shows it ("--12-31", "1/31", "December 31").
- Frozen at matcher `eb36301dae5d` (`tests/golden/claims_matcher.json`) before sampling. Unit tests: 21, all
  16 mutations caught.
- **Corpus result under the frozen rules:** 1,085 headline claims. 194 `matches`, 1 `no matching tagged value`,
  12 `non-GAAP wording`, 878 `not checked` (572 segment or other subject, 224 far from consolidated, 71 another
  period, 11 no tagged value).
- **Sample:** 100 claims stratified by outcome and reason (`tests/golden/claims_sample.json`). The labeling page
  shows the claim, its context and the tagged values, never the matcher's answer. Published privately, with the
  db store owner-only (probe write read back, invisible at `interact`, then deleted). `tools/score_claims.py`
  is written before any labels exist.

### Learnings
- On this corpus, consolidated headline figures in MD&A agree with the tagged statements wherever the matcher
  can be sure of scope and period. The interesting number is how much it *can't* check: 81% of headline claims
  are about segments, other periods, or a scope the sentence doesn't name. Option C (segments) is where coverage
  would come from.
- The rounding window ("$6.9 billion" covers ±$50M) is what makes a match meaningful *after* concept and period
  are fixed. Before that, it matched noise (the §1 probe).

### Open / next
- Trevor labels the 100 claims. Then score once, write it up, update README/TODO/DECISIONS, commit, stop at the
  M5 gate.

### 2026-10-17 — M5 part 3: labels, and the gate
- Trevor didn't feel confident judging scope cold. He first asked whether his own labels were being treated as
  ground truth (they aren't: the report says "agreement with one labeler"), then asked to see a "most likely" answer
  while labeling. I offered reveal-after-a-locked-answer as the option that keeps an independent number, and he
  chose to see suggestions first (FD-DEC 026). C001 had already been explained as a worked example, so it is not
  scored.
- **Result:** 0 of 99 suggestions overridden, median 5 s per label, about 28 active minutes. That is the
  rubber-stamp outcome the decision warned about. The report states it plainly: an anchored upper bound, not an
  estimate of precision. Offered a 20-claim blind spot check; Trevor chose to close as is (FD-DEC 027).
- Gate checks: `filing-delta facts`, `filing-delta claims` and `tools/score_claims.py` regenerate every output
  byte-identically offline; 178 tests pass. README gains two verification rows and a narrowed "doesn't verify
  management" limit.

### Learnings
- **Showing the answer first turned labeling into confirmation.** A third of the time per item of the blind M4 (5 s vs. 16 s)
  pass, and no disagreements at all. Assistance helps a labeler who will push back; it can't create the pushback.
  For a later milestone that needs a number (M6's QA set), labels stay blind by default, with explanation offered
  up front instead of mid-labeling.
- **Explaining one item mid-labeling costs that item.** Worked examples should come from outside the sample.

### Open / next
- M5 gate: stop for Trevor's approval. Next is M6 (retrieval + grounded QA, cite or abstain), where Trevor labels
  the answerable/unanswerable QA set.

---

## 2026-10-19 — M5 approved; M6 survey and design

### What happened
- Trevor approved M5 and started M6. He chose the QA set's make-up: Claude drafts, Trevor labels and adds his own;
  60 questions, 40 answerable and 20 unanswerable (FD-DEC 028).
- `spancheck` 0.3.1 installed from PyPI and pinned (Trevor's B1 package; its `Case` takes `meta.answerable`, and
  outputs carry `contexts`, `citations` and a `sources` map for source-scoped provenance).
- Survey: 238 indexable sections, 39,158 paragraphs, 2.6 million words. Design: `docs/design/qa.md`.

### What broke
- `git push` failed with "Repository not found": the GitHub CLI's active account had switched to another login
  without access to the private repo. Commits stay local until Trevor switches back (`gh auth switch --user tjromack`).

### Learnings
- **Repetition across years is the QA design problem.** The same risk factor sits in up to eight 10-Ks, so
  retrieval is scoped to the asked-about filing deterministically before it ranks anything. Otherwise answers cite
  the right words from the wrong year.

### Open / next
- Trevor reviews `docs/design/qa.md`, then the build starts with the verifier and its forged-citation tests.
- 2026-10-19 (later): Trevor fixed the GitHub login (pushes resumed) and approved `docs/design/qa.md`. His
  question sheet, `docs/qa-questions-trevor.md`, was created so he can write his questions before seeing any drafted
  ones.

## 2026-10-19 — M6 part 1: the pipeline, built, tested, frozen

### What happened
- `filing_delta/qa/` built:
  - `answer.py`: the `Answer | Abstain` type and the exact-substring verifier, the gate.
  - `scope.py`, `index.py`: scoping and BM25.
  - `prompt.py`, `ask.py`: the answer stage through the M4 recorder.
  - `version.py`.
- Tests: 16 forged-citation gate tests, 27 scope and ranking tests, 7 end-to-end pipeline tests with a scripted
  model. Every mutation caught (25 across the stages). Full suite: 228.
- Dev slice (`tools/qa_dev.py`, 14 of my questions, not in the 60): 12 answered and verified, 2 correct
  abstentions. Frozen at pipeline `571c5437f514` (FD-DEC 029). Measured cost $0.30.

### What broke and the fix
- Netflix, round 1: the answer added "membership growth was therefore the main driver", which its quotes didn't
  say. A prompt rule fixed it, and round 2 abstained instead.
- Netflix, round 2: the abstention was right, but for the wrong reason. Retrieval had missed the filing's own
  sentence because nothing was stemmed ("revenue increase" vs. "revenues … increased"). A light stemmer fixed it,
  and round 3 quoted the stated reason.
- Coca-Cola "what new risks were added": BM25 had only change words to rank on. Change questions now rank the M3
  diff's added units first, and passages carry the diff's label. The answer named the sustainability-regulation
  risk and the Pillar Two tax text as new.
- Two mutation survivors in the tests: an empty-quote check that was genuinely redundant (removed), and a bounds
  check whose only distinct job, stopping Python's negative slicing, no test reached (test added). One more
  survivor: the quarter filter was untested because the test catalog had one 10-Q per company.

### Learnings
- **The verifier hasn't had to reject anything real yet:** dev produced 0 failed citations in 12 answers. The
  forged-citation tests are what show it works. The labeled 60 will show whether that holds.
- **The diff and the QA stage compose.** "What changed" questions are where this tool differs from a plain RAG
  system, and the deterministic M3 diff is what answers them.

### Open / next
- Draft the 48 questions (about 28 answerable plus 20 unanswerable by design); Trevor writes his 12 or more.
  Then the practice page and the labeling page.

### 2026-10-19 — M6 part 2: 48 questions drafted
- `tools/qa_draft_pool.py` picked 33 source passages deterministically (3 per company, varied filings and
  sections) before any question was written, so I didn't choose easy passages. Five boilerplate passages
  (forward-looking-statement disclaimers, the risk-factor preamble) were dropped as things no one would ask, plus
  four to balance companies.
- `tools/qa_drafted.py` → `tests/golden/qa_questions.json`:
  - 24 answerable from the pool, across lookup, risk-presence and stated-figure questions.
  - 4 change questions built from risk-factor additions Trevor labeled material in the M4 blind set.
  - 20 unanswerable: 4 outside coverage, 3 non-corpus companies, 4 advice or prediction, and 9 plausible
    undisclosed details. Each undisclosed one was keyword-checked against the scoped section text first; JPMorgan
    names Dimon and "discretionary bonus payments" but gives no amount, a deliberate near-miss.
- Every answerable draft scopes to its source filing and section. One (Weyco, "2023 10-K … end of 2022") names
  two years and pulls in both filings, deliberately, because people ask that way.

### A methodological catch before building the labeling page
- Proposing candidate passages for Trevor's questions with the system's own BM25 would make retrieval recall
  circular: gold spans could only come from what the retriever already found. So the labeling page embeds the
  **full scoped section text** with an in-page search, and Trevor selects gold spans anywhere in it. Drafted
  questions open at their source passage, but any span can be chosen.
- Labeling tools built:
  - `tools/qa_label_template.html` + `tools/build_qa_label_app.py`. The page shows the full scoped section
    text, an in-page search, mouse selection mapped to exact offsets (S adds a span), a short answer, and A / N /
    U / R. Snapshots refresh only the counts, so saving never resets the reader's scroll. About 7 MB with every
    section embedded.
  - The practice page (3 worked items outside the set) is published privately with an owner-only store, checked
    with a probe write.
  - `tools/qa_add_trevor.py` appends Trevor's questions and assigns blind ids, mixing authors.
- 2026-10-19 (later): Trevor wrote his 12 questions. A mix of lookups, risk-presence, change questions (including
  non-consecutive years), a 10-Q vs. 10-K comparison, and two he expects to be unanswerable.
  `tools/qa_add_trevor.py` merged them: 60 questions with shuffled ids QA01–QA60.
- Merging exposed a circularity in the labeling page (FD-DEC 030). It shows only what scoping selected, and QA54
  (Pfizer Q1 2026 10-Q vs. its 2025 10-K) scopes to two Q1 10-Qs with no parsed risk text. A "wrong filing shown"
  label now records such misses so they score as failures.
- The labeling page (6.0 MB, 69 sections) is published privately with an owner-only store, probe-checked. The
  practice page was republished with W.
- **The labeling page failed inside claude.ai's viewer.** Trevor couldn't pick an answer: drag-selecting text did
  nothing usable there, while the same page worked standalone. Three blind fixes (Enter in the answer box, a
  remembered selection, moving the buttons) didn't help, because I couldn't run the page myself. I then installed
  Playwright (local only, not a project dependency) and drove the page in Chrome with real mouse input, standalone
  and inside a sandboxed iframe. Drag-selection works in a plain browser, so the viewer's own selection handling is
  the likely cause; that can't be confirmed from outside claude.ai.
- **Fix:** picking an answer no longer uses text selection. Each section is split into sentences with exact offsets,
  and clicking a sentence toggles it as part of the gold answer. Verified with real clicks in both settings: pick a
  sentence, Enter to save, the N button, Back, a refused A with a visible message. The full 60-question page loads
  in 0.3 s and switches items in at most 0.19 s. A build stamp in the header shows which version the labeler sees.
- **Lesson:** test interactive pages by driving them before shipping, not just by parsing the script. Gold spans are
  now whole sentences, which suits retrieval-recall scoring (overlap) and citation checking (exact text).
- **Labeling moved out of the claude.ai viewer.** Even with sentence clicks and a Pick button, Trevor couldn't set a
  label in the viewer, while the same page works in Chrome standalone and in a sandboxed iframe. Rather than keep
  guessing at an environment I can't test, `tools/qa_label_server.py` (stdlib, 127.0.0.1 only) serves the same page
  locally and saves each label to `data/qa/labels-<collection>.json` with an atomic write. It was verified by
  driving Chrome against the running server: labels saved to disk and survived a reload. The labels get copied into
  a committed golden file before any run, as in M4 and M5.
- **Lesson for M8's read view:** pages meant for real use need testing in the environment they'll run in. An
  artifact viewer is a different environment from a browser tab.

## 2026-10-20 — M6 part 3: the answer key, from a model jury

### What happened
- After the practice page, Trevor found full manual labeling too slow, especially for the multi-year questions,
  and asked about having models label. I explained why a model-built key can't be the independent measure (the
  system answers with Sonnet; a model key measures model agreement) and offered four options. He chose a two-model
  jury with his review of their disagreements (FD-DEC 031).
- `tools/qa_jury.py`: Opus 5.5 and Fable 5.1, each reading the full scoped sections (about 1.7 million tokens per
  juror across the 60), JSON output, quotes mapped to sentence-level gold. A one-question smoke test passed for
  both (they agreed that Apple doesn't disclose Greater China iPhone units). 118 requests submitted via Batches.
- **Jury result:** all 118 batch requests succeeded, and every quote from both jurors was located in the section
  text. The jurors agree on **58 of 60**: all 28 drafted answerable questions answerable, all 20 by-design
  unanswerable ones not answerable. **Both disagreements are among Trevor's own 12** (QA21, Netflix paid sharing;
  QA54, Pfizer's 10-Q vs. 10-K). That bears out FD-DEC 028's caution that model-drafted questions are easy for
  models; the human-written ones are where judgment is needed. Measured cost $16.41 ($4.67 Opus, $11.74 Fable),
  above my $10 estimate because the inputs ran larger than I'd first sized. Committed as
  `tests/golden/qa_jury.json` before any pipeline run on the set.
- A review mode on the labeling page shows both jurors' labels, with their sentences marked in the text. "Use juror
  N" or Trevor's own label; each saved label records which. Tested through the local server with real clicks.

### 2026-10-20 — M6 part 4: the key, the run, the gate
- Trevor decided both jury disagreements, taking juror 2 (Fable) each time: QA21 answerable, citing three Netflix
  risk sentences on enforcing multi-household limits; QA54 not answerable. `tools/qa_key.py` wrote
  `tests/golden/qa_key.json` (37 answerable, 23 not), committed (`86923a4`) before the pipeline ran on the set.
- `tools/run_qa.py`, one pass of the frozen pipeline: 47 model calls, $0.34.
  - 35/35 answers' citations verified exact; 0 withheld.
  - 23/23 correct abstentions (10 model, 13 rule).
  - 35/37 answerable answered; retrieval recall@8 36/37.
  - `--offline` regenerates `docs/qa-eval.md` byte-identically.

### What broke and the fix
- QA58 was scored as citing the wrong passage. Coca-Cola's 2025 10-K repeats its definition of concentrate sales
  volume verbatim, and the answer cited the other copy. The scorer now accepts the same words from the same filing.

### Learnings
- **The two misses are a definitional gap, not a bug.** For "does the filing discuss X" questions where the truth
  is "not explicitly, but it says this nearby", the jury counted the cited nearby text as an answer. The pipeline
  abstains because it can't cite an absence. It's left to Trevor (FD-DEC 032).
- **Mechanics held under real questions.** No citation failed verification, on dev or on the 60. The verifier's
  value so far is as a guarantee, demonstrated by the forged-citation tests, rather than as a filter that has caught
  something real.
- **Labeling cost:** the jury key took Trevor about 5 minutes (2 decisions) and $16.41 in jury calls, against the
  estimated 45 minutes for full labeling. The price: the key is model-built.

### Open / next
- M6 gate: stop for Trevor's approval, plus his call on "no, but". Then M7: `spancheck` scores the recorded run
  (citation provenance and support, abstention, groundedness, cost and latency).

### 2026-10-20 — M6 approved; "no, but" answers (pipeline v2)
- Trevor approved M6 and chose to answer "no, but" questions (FD-DEC 033). Prompt rule 8 answers "[filing]'s
  [section] doesn't say X. It does say Z", citing Z, with a boundary: a specific absent fact (a number, name or
  amount) or nothing on the subject still abstains. Five new dev questions outside the 60 checked both sides of
  the boundary: Walmart climate litigation and Netflix ad plan vs. churn answered "no, but"; the F-150 price,
  Apple and cryptocurrency, and Tim Cook's salary abstained.
- The dev slice also caught a scoping bug. "Does Coca-Cola's 2023 10-K say weight-loss drugs have already reduced
  its sales?" was routed to MD&A only because of "sales", but the text is in the risk factors. Performance words now
  narrow to MD&A only alongside a figure or driver cue (test added, both mutations caught). Re-asked, the answer
  quoted the weight-loss-drug risk sentence in "no, but" form.
- Re-frozen as v2 `117a48a6de87`, with v1 recorded in `tests/golden/qa_pipeline.json`. v2 on the 60: 36/37
  answerable answered (QA52 now "no, but"), 23/23 abstentions still correct, 36/36 citations verified. $0.34 for
  the run, about $0.25 for the extra dev questions.
- **Remaining miss, QA21:** vocabulary. The question says "paid sharing"; the filing says "multi-household usage and
  shared viewing outside of a household". BM25 can't connect them, and adding synonyms for a scored item would be
  tuning on the test. Left as the clearest case for meaning-based search, and noted for M7's error analysis.

---

## 2026-10-20 — M7: spancheck

### What happened
- Read `spancheck` 0.3.1's API from the installed package (`Case`/`Output`/`evaluate`, `citation_accuracy` with
  `sources` scoping and `claim_split`, `judge_support`/`llm_judge`, `audit_log`). Its Anthropic provider defaults to
  `claude-sonnet-5-5`; I used my own provider instead, through the recorder, so the judge replays with no key.
- **Latency wasn't in the recorded run.** The recorder now stores wall-clock with every new response, and a timed
  re-run into a separate cache measured it. The pipeline's frozen hash stayed unchanged: a trace-field edit to
  `ask.py` was reverted after it changed the hash.
- `tools/spancheck_run.py score` → `docs/spancheck-report.md` (byte-identical offline) and the audit log.

### What broke and the fix
- The report crashed on `Scorecard.by_grader()`, which returns `{score, pass_rate, n}` per grader, not a rate.
- The first "answer vs. its citations" pass failed answers for not "establishing" the filing or the "newly added"
  status. The judge saw bare quotes, without the label each citation carries. With the labels: 49 → 51 of 60.

### Learnings
- **Provenance and grounding are solid; claim-level citation isn't.** Every quote is real (71/71), and answers are
  grounded in what was retrieved (98%). But 9 answers add true details from passages they didn't quote. The cited
  span supports part of the answer, not all of it. An exact-substring verifier can't catch that; an entailment
  judge can. That's the value of M7 over M6's own checks.
- **Per-citation support is low (about 67%) mostly by construction:** answers pack several cited facts into a
  sentence, and claim_split pairs each quote with a whole sentence. Per-claim citations (spancheck's `claim` field)
  would measure this properly.
- **The judge and the lexical proxy disagree on 9 of 71 citations, both ways:** the judge rejects keyword-overlap
  passes (QA07, QA22), and accepts paraphrase that word overlap misses (QA16, QA27). This is where calibrating the
  judge on human labels would start.

### Open / next
- M7 gate: Trevor's approval and his call on v3 (cite every figure and detail, with per-citation claims).

### 2026-10-20 — M7 approved; pipeline v3 (cite every detail)
- Trevor approved M7 and wanted the under-citation fix "at some point", leaving the timing to me. Done before M8
  (FD-DEC 035): M8 packages the published numbers, so changing them afterwards would mean redoing the release.
- `tools/spancheck_run.py dev` scores the dev slice's citations, so tuning never reads the scored 60. v2 dev
  baseline: per-citation support 42%, answer entailed by citations 90%. v3 dev: 84%, 90%.
- v3 on the 60: answers entailed by their own citations **59/60** (from 51); per-citation support 87% (from 67%);
  89/89 provenance; 37/37 answered; 23/23 abstentions; $0.38; p50 2.6 s.
  Judge calls $1.23 (252, 155 new).

### What broke
- **QA21 turned from an honest abstention into a misleading answer:** "the passages … never mention paid
  sharing", after retrieval missed the "multi-household usage" text. Every grader passes it. The report now
  computes and lists answers whose quotes miss the key's passage, so this can't hide in a 100% abstention score.

### Learnings
- **Making answers cite more made them less repeatable** (identical citation sets 47 → 28 of 60), while the
  decisions stayed identical. Stability of *which* quotes isn't the same as stability of *what* is claimed.
- **"No, but" and imperfect retrieval interact badly.** The rule that rescued QA52 produced QA21's false absence.
  An absence claim needs a stronger retrieval guarantee than a positive one.

### Open / next
- M8 design (read view, release artifact, clean-clone run), for Trevor's review before building.

---

## 2026-10-20 — M8 survey and design
- Survey before design: a clean clone needs only the EDGAR cache (731 MB) and the model cache (141 MB), plus the
  timed latencies. Neither cache holds personal data (the User-Agent isn't stored). The full keyless rebuild on
  this machine took about 3.5 minutes, and every committed file in `docs/`, `tests/golden/` and `corpus/` came
  out byte-identical: the reproduction the M8 gate will demand on a fresh runner already holds locally.
- Design: `docs/design/m8.md` covers a one-command reproduce script, a GitHub Release for the data, a clean-clone
  Action, and a FastAPI read view (changes plus recorded questions; live asking only with a key).
