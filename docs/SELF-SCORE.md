# Self-score against the §01 rubric (M10)

Scored 2026-10-20 against the playbook's eight gates (0, 1 or 2 each; new builds need 14+, with no zero on gates 1,
2, 4 or 6, and gate 7 held hardest). Every piece of evidence below is a file in this repo or a command that
regenerates one. I scored strictly: where a gate's evidence holds only under a condition, the condition is named.

**Total: 16 / 16, conditional on two pre-publication checks** (end of this page). Until the repo is public, a
stranger can't clone it at all, so gates 1 and 6 currently hold for the owner's account only.

| # | Gate | Score | Evidence |
|---|---|---|---|
| 1 | Clean-clone run | 2 | One command reproduces every published number from a fresh clone with no API key: `uv run python tools/fetch_release.py && uv run python tools/reproduce.py` (README *Quickstart*). Verified in a clean container on every push: `.github/workflows/clean-clone.yml` runs it on a fresh Linux runner and fails if any committed report or golden file changes by a byte. |
| 2 | README a stranger can use | 2 | `README.md`: what it does, who it's for, "What this does not let me claim", Quickstart, the one-line try-it command, and two screenshots of the read view (`docs/img/`). |
| 3 | Tests that matter | 2 | 260 tests (`uv run pytest`) aimed at the failure modes the project is about. Forged citations of every kind are caught (16, `tests/test_qa_verify.py`). Every parse outcome carries a reason, and confirmed section boundaries are held by 28 human-confirmed goldens. The EDGAR client survives a simulated 429 storm. The diff is deterministic. The QA pipeline source must match its frozen version. Mutation checks are recorded per milestone in `docs/BUILD-LOG.md`. |
| 4 | Verification evidence | 2 | Named checks with published results, including bad ones: parse rate (`docs/parse-report.md`, `docs/parse-failures.md`), alignment precision/recall against 70 human labels (`docs/alignment-eval.md`), the material/cosmetic confusion matrix against 122 blind human labels plus an error analysis whose first explanation was tested and mostly failed (`docs/materiality-eval-test.md`, `docs/materiality-error-analysis.md`), the two-source XBRL cross-check (`docs/xbrl-report.md`), QA and `spancheck` reports with their misses listed (`docs/qa-eval.md`, `docs/spancheck-report.md`). |
| 5 | Stated limits | 2 | README section "What this does not let me claim": no investment advice; no verification of management's narrative; can't prove absence; the QA key is model-built; no materiality determination in the legal sense; no coverage beyond 10-K (period of report 2018-01-01 to 2025-12-31) and 10-Q (filed 2025-01-01 to 2026-09-30) for 11 companies. |
| 6 | A path to try it | 2 | One line on the card, cold from a fresh clone, no key, account or Docker: `git clone https://github.com/tjromack/filing-delta.git && cd filing-delta && uv run filing-delta demo`. Rehearsed from fresh clones on 2026-10-20. The first two rehearsals failed and were fixed (*Rehearsals* below). The third reached the read view in 254 s and left every committed file unchanged. |
| 7 | Real input | 2 | 144 real SEC EDGAR filings (88 10-K, 56 10-Q; `corpus/manifest.csv`), source cited and fetched under EDGAR's fair-access rules. Messy enough that handling it is the work: four layout archetypes (one-sentence MD&A pointers at JPMorgan and Exxon, GE's cross-reference index with no Item headings), both sides of the inline-XBRL transition, running headers, `&#146;` entities, and an MD&A incorporated from an exhibit (`docs/design/section-parser.md`). No client or personal data. |
| 8 | Demonstrates line | 2 | "separating deterministic diffing from model judgment, then scoring the model half against labels." That's 96 characters, inside the 20–120 range. It names the transferable how and a verification property. |

## Rehearsals of the gate-6 command (2026-10-20)

Each rehearsal used a fresh clone of `main` from GitHub on Windows, run through `uv run --native-tls` for the local
TLS proxy. All three were recorded in `docs/BUILD-LOG.md`.

1. **Failed:** the classifier-labels step wrote into `data/classify/`, which doesn't exist in a fresh clone. Fixed
   in `14fd236`.
2. **Served wrong numbers:** the demo skipped `facts`, so the question catalog was empty, and every question was
   scoped out of the corpus without a word. The rehearsal also changed `docs/qa-eval.md`, which is how it was
   caught. The first fix (`303c3a5`) went into a frozen pipeline file and changed its version, so the next run
   refused to start. Fixed in `95ee209`: the guard now sits outside the frozen files, and a new test pins the
   pipeline version.
3. **Passed:** reached the read view in 254 s, including environment setup and the 63 MB download. The QA21 page
   shows its recorded answer, and `git status` was clean.

## Where a stricter reviewer could take points

- **Gate 4.** The QA accuracy figures are agreement with a model-built key: two models agreed on 58 of 60, and
  Trevor decided the other 2 (FD-DEC 031). The materiality and alignment figures are against one human labeler.
  The claim-matcher labels were suggestion-assisted, with 0 of 99 overridden, so they count as no evidence. All
  three are stated wherever the numbers appear, which is why I kept the 2. A reviewer could still call the QA half
  "checks exist, independent results don't".
- **Gate 6.** The command needs `uv` installed, a standard Python tool, as the README's Quickstart assumes. The demo
  downloads the data release from GitHub using `gh` when it's installed and curl otherwise. Only the `gh` path has
  been exercised, because the repo is private and the curl path needs a public release URL.
- **Gate 1.** CI is the clean container. It runs the full reproduction, not the demo command.

## Before publishing (both needed for gates 1 and 6 to hold for a stranger)

1. Make the repo and the `data-2026-10-20b` release public.
2. From a machine without `gh`, run the one-line command and confirm it serves the read view. That exercises the
   curl fallback (`tools/fetch_release.py --no-gh`).
