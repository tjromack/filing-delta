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
