# TODO — the build spine

Phased milestones. Each one ends at a **verification artifact + a BUILD-LOG entry + a commit + a stop for approval**.
The order follows the kickoff-packet spine (playbook v3, p. 28), with one change: the prompt seed says to design the
section parser first, because that's where this build silently breaks. So M0 is a design milestone that ships no
feature code.

Acceptance bar: §01 at **14+/16**, with **no zero on gates 1, 2, 4 or 6**. Gate 7 (real input) is held hardest.
Decisions already settled: `DECISIONS.md` FD-DEC 001–006.

---

## Phase 0 — scaffold (this session)
- [x] `CLAUDE.md` — design pins + banked gotchas + definition of done
- [x] `README.md` — the promise, who it's for, what it does not do, quickstart stub, how it's verified (`[TKTK]` until real)
- [x] `TODO.md` — this spine
- [x] `DECISIONS.md` — FD-DEC 001–008
- [x] `docs/BUILD-LOG.md` — the journal, first entry
- [x] `.gitignore` (`data/` in full, EDGAR + model caches, `.env`, venv, build artifacts) · `.env.example`
- [x] `git init` + first commit + push to `tjromack/filing-delta` (private). **← stop for approval**

## M0 — section-parsing design + corpus lock (design only, no feature code)
- [x] Pull a stratified sample of real filings by hand (`curl`, declared UA, into `data/`): several filers, filer
      agents and HTML eras, 10-K and 10-Q. 18 docs / 11 filers (`tools/m0_fetch.py`, `tools/m0_survey/`)
- [x] Catalog how Item 1A / Item 7 boundaries actually appear (TOC links vs. headings, table-wrapped headings,
      "Item 1A." vs. "ITEM 1A —", page-break artifacts, items incorporated by reference, a 10-Q Part II Item 1A
      that only says "no material changes")
- [x] `docs/design/section-parser.md` — strategy, outcome model (`ok`/`partial`/`failed` + reasons), offsets
      contract (the char spans that citations depend on), and golden-fixture plan
- [x] Lock the corpus: companies, filing types, exact date range (FD-DEC 008)
- [x] **Gate:** design doc approved, corpus locked (2026-10-08).

## M1 — EDGAR client ✅ (2026-10-08)
- [x] Required `EDGAR_USER_AGENT`; rate ceiling 5 req/s (FD-DEC 004); content-addressed, sha256-checked cache; back-off honoring `Retry-After`
- [x] Fetch by CIK and form type through the submissions API (paged history; pre-window pages skipped); primary documents resolved
- [x] **Tests (25):** a simulated 429 storm (injected transport, fake clock) asserts back-off, Retry-After, an eventual success and a global
      pause; the rate ceiling is never exceeded; 403 is never retried; 404/storm responses are not cached; warm cache = **zero** requests;
      offline mode never touches the network; a corrupted cache entry is detected. Mutation-checked (2 of 3 mutants killed; the 3rd is equivalent)
- [x] **Gate:** locked corpus fetched: 144 filings (88 10-K, 56 10-Q), 681 MB, `corpus/manifest.csv`; warm re-run = 0 network requests,
      manifest byte-identical. **← stop**

## M2 — section parser (Item 1A, Item 7) with failure logging ✅ (2026-10-08; goldens confirmed 2026-10-12)
- [x] Implement the approved design; pure core, no I/O (`filing_delta/parse/`: blocks → headings/furniture → locate)
- [x] Every filing → `ok` / `partial` / `failed` (+ `absent`, FD-DEC 012) + reasons → `docs/parse-failures.md` +
      `docs/parse-report.md` (`filing-delta parse`, byte-reproducible)
- [x] 22 mechanism tests, one per layout mechanism, plus a regression test for every bug found during M2
- [x] **Golden-file tests**: 28 sections from 14 filings across every archetype and era (`tests/golden/sections.json`)
- [x] **Trevor confirms the 28 golden boundaries** against the filings (2026-10-12): all 28 confirmed, no issues.
- [x] **Gate:** parse-success rate over the full corpus is published (270/272 present = 99.3%; 16 absent; the 2
      failures are Pfizer FY2018–19 exhibit incorporation, explained). **← stop**

## M3 — paragraph diff + alignment (2026-10-14) — awaiting approval
- [x] Segmentation into paragraph / heading / data-table units; exact canonical spans (FD-DEC 017)
- [x] Alignment: unchanged / reworded / moved / split / merged / added / removed, deterministic, no model
- [x] `filing-delta diff`: 200 pairs (176 diffed) → `data/diffs/` + `docs/diff-report.md`, byte-reproducible
- [x] Edge/churn anomaly flags, each checked by hand → `docs/diff-anomalies.md` (found and fixed JPM's lost last
      MD&A page, FD-DEC 019)
- [x] 17 synthetic diff tests (mutation-checked: 5 of 5 mutants killed) + 3 corpus invariants (coverage, spans,
      byte-identical re-diff)
- [x] **Trevor labeled 70 alignment pairs**, then re-judged 54 under the *instance* criterion; threshold 0.40 set by
      sweeping the whole aligner (FD-DEC 018); precision 0.83 (CI 0.74–0.93) / recall 0.80 (CI 0.66–0.93) published
      in `docs/alignment-eval.md`; `tests/test_alignment_labels.py` holds them as a floor
- [x] Labeling note → page-break join fix for capitalised continuations; goldens re-derived under the words-unchanged
      guard (`filing-delta golden --rederive`)
- [x] **Gate:** diff over the full corpus with human-set thresholds and published aligner precision/recall. **← stop**

## M4 — material/cosmetic classifier + hand labels + confusion matrix (done; approved 2026-10-17)
- [x] Labeling guide written and approved before any labeling (`docs/design/materiality.md`, FD-DEC 020)
- [x] 150-change stratified sample, split 28 dev / 122 test before any model output (`tools/materiality_sample.py`)
- [x] Dev set labeled: Claude-suggested, Trevor reviewed, 0/28 overridden (FD-DEC 021)
- [x] Classifier stage (`filing_delta/classify/`): formatting-only rule + model (`ANTHROPIC_MODEL`, default
      `claude-sonnet-5-5`), structured output, verified evidence spans, recorded responses (FD-DEC 007); restatement
      context; prompt refined on dev only (24 -> 25/28) and frozen at `1fd1c7e5bb42` (FD-DEC 022)
- [x] Trevor labels the **test** set (`docs/materiality-labels-test.md`) before any test-set model output is seen
- [x] Confusion matrix + bootstrap CIs on test, scored once (`docs/materiality-eval-test.md`); Haiku 5.5 comparison
- [x] Full 5,623-change run, Sonnet + Haiku via Message Batches, keyless replay (`docs/materiality-corpus.md`,
      FD-DEC 023)
- [x] Adjudication re-check of the 26 disagreements (Trevor), published beside the blind numbers
      (`docs/materiality-eval-test-adjudicated.md`, FD-DEC 024)
- [x] Error analysis write-up (`docs/materiality-error-analysis.md`); README limits + verification rows
- [x] **Gate:** a reproducible, keyless confusion matrix. **<- stop for approval**

## M5 — XBRL company facts join (done; approved 2026-10-19)
- [x] Survey + design (`docs/design/xbrl-join.md`); inline XBRL first, company-facts fallback (FD-DEC 025)
- [x] Company-facts endpoint through the same client; facts joined to filing periods as context
      (`filing-delta facts` -> `data/facts/`, `docs/xbrl-report.md`): two-source cross-check 65,243/65,243 equal
- [x] **Tests:** period alignment (52/53-week, January FYE, YTD-only cash flow, amendments dropped by accession);
      facts never narrative (provenance on every rendering; parse/diff/classify never import XBRL); mutation-checked
- [x] **Decide FD-DEC 016:** option B, consolidated headline claims with no model (FD-DEC 025)
- [x] Claim matcher (`matches` / `no matching tagged value` / `non-GAAP wording` / `not checked`), frozen at
      `eb36301dae5d`; coverage published (`docs/claims-report.md`). Trevor's labels were suggestion-assisted
      (FD-DEC 026): 0/99 overrides, reported as not independent (`docs/claims-eval.md`); he chose to close as is
- [x] **Gate:** join verified on the corpus (two-source cross-check; outputs byte-identical offline). **← stop for approval**

## M6 — retrieval + grounded QA (cite or abstain) (done; approved 2026-10-20)
- [x] Design approved (`docs/design/qa.md`); deterministic scoping, BM25 over exact-offset units, change questions
      ranked from the M3 diff (FD-DEC 029)
- [x] `Answer | Abstain` type; exact-substring citation verifier; any unverifiable answer becomes an abstention
- [x] QA set: 60 questions (48 drafted + Trevor's 12; FD-DEC 028). Answer key from a two-model jury (Opus 5.5 +
      Fable 5.1, 58/60 agreed) with Trevor deciding the 2 disagreements (FD-DEC 031; replaces "done by Trevor")
- [x] One run of the frozen pipeline (`docs/qa-eval.md`): 35/35 answers verified, 23/23 correct abstentions,
      retrieval recall@8 36/37; misses are two "no, but" questions (FD-DEC 032)
- [x] **Gate:** the verifier is tested against forged citations (16 gate tests, all mutations caught). **← stop**

## M7 — spancheck run (done; approved 2026-10-20; v3 applied)
- [x] Score citation accuracy, abstention correctness, hallucination rate, cost and latency with `spancheck` 0.3.1
      (PyPI): `tools/spancheck_run.py`, judge Opus 5.5 through the recorder; timed re-run for latency
- [x] Publish the report + error analysis, including where the judge disagrees (`docs/spancheck-report.md`)
- [ ] (Optional) multi-provider comparison through the provider interface: not done (the jury in M6 already
      compares two models on the key; deferred)
- [x] **Gate:** a reproducible spancheck report (byte-identical offline, all 214 judge verdicts replayed). **← stop**

## M8 — read view + try-it path + clean clone (done; approved 2026-10-21)
- [x] FastAPI + a small read view: section diff, with the material/cosmetic label and the source span
      (`filing-delta serve`; plus the 60 recorded answers with highlighted citations; Ask only with a key)
- [x] Release artifact: EDGAR cache + model-response cache for the locked corpus (`data-2026-10-20`, 63 MB,
      private; `release/manifest.json`)
- [x] One-command keyless cold run (`tools/fetch_release.py` + `tools/reproduce.py`); a clean-clone GitHub
      Action with badge
- [x] README filled in with real numbers and stated coverage; two screenshots
- [x] **Gate:** a cold clone on a fresh runner reproduces the published numbers: CI run 39523066842 (v3) and 39527545724 (v4, release data-2026-10-20b),
      byte for byte, no API key. **← stop**

## M9 — labeled QA pairs exported for B4 (approved)
- [x] Export the answerable/unanswerable pairs, each with source document, span, label and labeler note
      (`export/b4-finance-qa.jsonl`, 60 items; `docs/b4-export.md`)
- [x] B4's item schema: none existed yet, so proposed here (`schemas/b4-qa-item.schema.json` v1.0, FD-DEC 039)
- [x] **Gate:** export validates against the schema, plus every span re-read and every section hash re-checked;
      12 forge/break tests; regenerated byte for byte by `tools/reproduce.py`. **← stop**

## M10 — case study + rubric self-score
- [x] Self-score against §01 (target 14+, no zero on 1/2/4/6); fix the gaps (`docs/SELF-SCORE.md`: 16/16)
  - [x] Gaps fixed: README overclaims (8-K, "decades"; FD-DEC 040); one-line keyless `filing-delta demo` (gate 6),
        rehearsed from fresh clones until clean (two bugs found and fixed; FD-DEC 041)
- [x] `docs/CASE-STUDY.md` on the §06 template, with the parse-failure log as its spine; every number checked against its source
- [x] Repo + release public; one-line demo passed cold on macOS; curl fallback run (2026-10-22)
- [ ] **Gate:** 14+/16 (self-scored 16/16), Trevor's approval; then the site page (`draft: false`). **← stop**
