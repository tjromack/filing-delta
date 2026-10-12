# filing-delta

**See what a company newly disclosed, quietly dropped, or materially reworded between filings — with every claim
traceable to the exact span it came from.**

> **Status: under construction.** Nothing below is a result yet. The quickstart, coverage and verification numbers
> are filled in as each milestone ships (see `TODO.md`). Unknowns are marked `[TKTK]`.

## What it does

1. **Fetches** 10-K, 10-Q and 8-K filings from SEC EDGAR, honoring EDGAR's fair-access rules: a declared
   User-Agent, a rate limit, and a local cache so a re-run makes zero requests.
2. **Parses** the narrative sections (Item 1A Risk Factors, Item 7 MD&A) out of decades of inconsistent filer HTML.
   Every parse failure is logged and counted, never skipped silently.
3. **Diffs** each section period over period at paragraph level: added, removed, reworded, moved. This step is
   **fully deterministic and uses no model.**
4. **Classifies** each change as *material* or *cosmetic*. This is the only model judgment in the diff, and it is
   scored against hand labels.
5. **Answers questions** over the corpus with span-level citations. When the answer isn't in the filings, it
   **abstains**. Every answer either cites an exact span or declines.

## Who it's for

Anyone who has to read the same company's risk factors year after year and wants to know what *changed*: analysts,
compliance and audit reviewers, researchers. It's also for engineers who want a worked example of separating
deterministic processing from model judgment, and scoring the model half.

## What it does not do

- **It is not investment advice.** It reports what filings say and how the text changed. It makes no judgment about
  what that means for a security, and nothing it outputs is forward-looking.
- **It doesn't verify what management says.** Item 1A and Item 7 (MD&A) are unaudited management narrative,
  and MD&A figures are often non-GAAP. The tool shows what the text says and how it changed, not whether it is
  accurate. Only the audited financial statements carry that weight.
- **It doesn't claim financial-analysis expertise.** "Material" here is a labeled text-change category, not a legal
  or accounting materiality determination.
- **It doesn't cover anything outside its ingested corpus.** Coverage: **10-K** with a period of report from 2018-01-01 to
  2025-12-31, and **10-Q** filed 2025-01-01 to 2026-09-30, for **11 companies** (`corpus.toml`; every accession in
  `corpus/manifest.csv`). Amendments are excluded. Questions outside that range get an abstention.
- It doesn't parse exhibits, financial statements or XBRL tables as narrative. XBRL company facts are joined as
  context only.

## Quickstart

[TKTK — a one-command, keyless cold run from a fresh clone, using the released EDGAR + model-response cache.]

## How it's verified

| Check | What it proves | Result |
|---|---|---|
| Golden-file parser tests | Section boundaries are found correctly across filers and HTML eras | 28 sections / 14 filings; human confirmation pending (`docs/golden-review.md`) |
| Published parse-success rate + failure log | Parse failures are surfaced, not hidden | 270 of 272 present sections `ok` (99.3%), 16 verified-absent, 2 failed (exhibit incorporation): `docs/parse-report.md` |
| Golden-file diff tests | The diff is deterministic and correct on known pairs | [TKTK] |
| Material/cosmetic confusion matrix vs. hand labels | How good the model judgment is, and where it's wrong | [TKTK] |
| `spancheck` citation + abstention report | Answers cite real spans and abstain when they should | [TKTK] |
| Simulated 429 storm | The EDGAR client backs off and recovers without breaking fair access | Passing (`tests/test_edgar_client.py`); warm re-run of the full corpus = 0 requests |

## Data

All inputs are **public SEC EDGAR filings**. No private, client or personal data is used. EDGAR's fair-access
policy is followed: a declared User-Agent, a rate ceiling below SEC's limit, and cached responses.

## License

MIT. See `LICENSE`.

[![M8ven Score](https://m8ven.ai/badge/mcp/tjromack-clear-pricer-mcp-7v9m47?v=8a242f1dd1bd8ec6970fc4d7a8896075)](https://m8ven.ai/mcp/tjromack-clear-pricer-mcp-7v9m47?s=readme)
