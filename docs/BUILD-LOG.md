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
| M1 · EDGAR client | [TKTK] | 144 filings / 681 MB; warm re-run = 0 requests; 25 tests | 90 of 245 cold requests were paged history (71 JPM) |

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
