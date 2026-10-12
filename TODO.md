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

## M3 — paragraph diff + alignment
- [ ] Paragraph segmentation; alignment across periods (unchanged / reworded / moved / added / removed)
- [ ] **Golden-file diff tests** + a determinism test (byte-identical output across runs)
- [ ] **Gate:** diff over the full corpus, with golden tests green. **← stop**

## M4 — material/cosmetic classifier + hand labels + confusion matrix
- [ ] Labeling guide (what "material" means here, with examples), written **before** labeling
- [ ] Hand-labeled set, done by Trevor; a model never labels its own eval set; stratified across change types
- [ ] Classifier stage: separate and separately testable, with model id from `ANTHROPIC_MODEL`, responses recorded (FD-DEC 007)
- [ ] **Publish the confusion matrix** + error analysis (where it's wrong, and why)
- [ ] **Gate:** a reproducible, keyless confusion matrix. **← stop**

## M5 — XBRL company facts join
- [ ] Company-facts endpoint through the same client; join selected facts to filing periods as context
- [ ] **Tests:** period alignment (fiscal vs. calendar, amendments); facts never presented as narrative
- [ ] **Decide FD-DEC 016:** reconcile MD&A numeric claims against audited XBRL facts (*reconciles* / *differs*
      / *non-GAAP or untagged*), with a published reconciliation rate scored on a hand-labeled sample
- [ ] **Gate:** join verified on the corpus. **← stop**

## M6 — retrieval + grounded QA (cite or abstain)
- [ ] Index over parsed sections, keeping offsets
- [ ] `Answer | Abstain` type; exact-substring citation verifier; any unverifiable answer becomes an abstention (FD-DEC 005)
- [ ] Hand-labeled QA set (answerable + plausible unanswerable), done by Trevor
- [ ] **Gate:** the verifier is tested against forged citations. **← stop**

## M7 — spancheck run
- [ ] Score citation accuracy, abstention correctness, hallucination rate, cost and latency with `spancheck` (PyPI)
- [ ] Publish the report + error analysis, including where the judge disagrees
- [ ] (Optional) multi-provider comparison through the provider interface
- [ ] **Gate:** a reproducible spancheck report, published. **← stop**

## M8 — read view + try-it path + clean clone
- [ ] FastAPI + a small read view: section diff, with the material/cosmetic label and the source span
- [ ] Release artifact: EDGAR cache + model-response cache for the locked corpus
- [ ] One-command keyless cold run; a clean-clone GitHub Action (Gate 1 badge)
- [ ] README filled in with real numbers and stated coverage; one screenshot
- [ ] **Gate:** a cold clone on a fresh runner reproduces the published numbers. **← stop**

## M9 — labeled QA pairs exported for B4
- [ ] Export the answerable/unanswerable pairs, each with source document, span, label and labeler note (B4's item schema)
- [ ] **Gate:** export validates against the B4 schema. **← stop**

## M10 — case study + rubric self-score
- [ ] Self-score against §01 (target 14+, no zero on 1/2/4/6); fix the gaps
- [ ] `docs/CASE-STUDY.md` on the §06 template, with the parse-failure log as its spine; every number checked against its source
- [ ] **Gate:** 14+/16. Only then does it go on the site.
