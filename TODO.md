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
- [ ] Lock the corpus: companies, filing types, exact date range (FD-DEC 008) (proposed; awaiting approval)
- [ ] **Gate:** design doc approved, corpus locked. **← stop**

## M1 — EDGAR client
- [ ] Required `EDGAR_USER_AGENT`; token-bucket rate ceiling (FD-DEC 004); content-addressed cache; back-off honoring `Retry-After`
- [ ] Fetch by CIK and form type through the submissions API; resolve primary documents
- [ ] **Tests:** a simulated 429 storm (injected transport) asserts back-off, an eventual success, and that the rate
      ceiling is never exceeded; a second run against a warm cache makes **zero** network requests
- [ ] **Gate:** locked corpus fetched; re-run = 0 requests (measured). **← stop**

## M2 — section parser (Item 1A, Item 7) with failure logging
- [ ] Implement the approved design; pure core, no I/O
- [ ] Every filing → `ok` / `partial` / `failed` + reason → `docs/parse-failures.md` + parse-success rate
- [ ] **Golden-file tests** on hand-verified section boundaries across filers and eras
- [ ] **Gate:** published parse-success rate over the full corpus; every failure explained. **← stop**

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
