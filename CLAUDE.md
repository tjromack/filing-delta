# CLAUDE.md — Operating Contract

Working agreement for building **filing-delta** with Claude Code. Read it before each session. The decisions this
contract assumes are recorded in `DECISIONS.md` (FD-DEC 001–008). Read those first and do not re-open them.

## Purpose

See what a company newly disclosed, quietly dropped, or materially reworded between SEC filings, with every claim
traceable to the exact span it came from. The tool ingests 10-K, 10-Q and 8-K filings from EDGAR, parses out the
narrative sections (Item 1A Risk Factors, Item 7 MD&A), diffs them period over period at paragraph level, and
classifies each change as **material** or **cosmetic**. It then answers grounded questions over the corpus with
span-level citations and **abstains** when the answer isn't in the filings.

This is **BUILD 3** of the portfolio slate: the second regulated vertical, the finance/markets build. It reuses B1
(`spancheck`) for scoring, and its labeled QA pairs become half of B4's benchmark corpus.

## Design pins (do not violate without a DECISIONS entry)

1. **EDGAR fair-access rules are honored exactly.** A declared User-Agent (from `EDGAR_USER_AGENT`; the client
   **refuses to start** without one), a global rate ceiling below SEC's 10 req/s, and **every response cached locally**
   so a re-run costs zero requests. Back-off is tested against a simulated 429 storm. (FD-DEC 004)
2. **The diff layer contains no model calls.** Section parsing, paragraph alignment and the diff are deterministic
   and covered by golden-file tests. The same input gives byte-identical output.
3. **Classification is a separate, separately testable stage.** Material vs. cosmetic is the only model judgment in
   the diff half. It consumes the diff's output and never feeds back into it. It is scored against **hand labels**
   with the confusion matrix published.
4. **Section-parsing failures are logged and surfaced, never silently skipped.** Every filing ends in exactly one
   parse outcome, `ok`, `partial` or `failed`, each with a reason. Failures go to a committed parse-failure log
   (`docs/parse-failures.md`) and count toward a published parse-success rate.
5. **Every answer carries a span citation or abstains. There is no third option.** The answer type is a tagged union:
   `Answer(text, citations≥1)` or `Abstain(reason)`. A citation is (accession number, section, char start, char end),
   and its text must be an **exact substring** of the stored section. Unverifiable citations are converted to an
   abstention, never shown.
6. **No forward-looking claims and no investment advice in any output copy.** The tool reports what the filings say
   and how they changed. It never says what that means for a stock. This applies to the README, the read view, answer
   templates and the case study.
7. **Verification is part of the build.** If the golden-file tests, the confusion matrix or the `spancheck` run
   for a milestone aren't written, that milestone isn't done.

## Banked gotchas (learned on earlier builds; don't rediscover them)

- **TLS-inspecting corporate proxy.** Python `requests`/`httpx` (and Node/uv) fail cert verification on this machine,
  while `curl` (which uses the OS trust store) works. For Python HTTPS, call `truststore.inject_into_ssl()` before any
  client is built. For one-off bulk downloads, prefer `curl`. Don't spend time debugging TLS.
- **Don't patch regex source through a shell heredoc + Python string.** On M2 this wrote `\b` into the
  file as a literal backspace (0x08) and doubled other backslashes, and the regexes silently stopped matching. Use the
  Edit tool for code edits.
- **uv through the proxy:** `uv pip install --native-tls …` works.
- **`spancheck` comes from PyPI** (`pip install spancheck`), pinned in `pyproject.toml`. Do not vendor or fork it.
  If it lacks something, open an issue on spancheck itself.
- **Model id comes from `ANTHROPIC_MODEL`**, defaulting to **`claude-sonnet-5-5`**. `claude-sonnet-5` is deprecated
  and now errors. Never hardcode a model id anywhere except that one default.
- **Hand labels are human labels.** Trevor labels the material/cosmetic set and the answerable/unanswerable QA set.
  A model never produces the labels it is scored against.

## Stack

- Python 3.11+ · `uv` for env/lock · `pytest`
- `httpx` + `truststore` for the EDGAR client (transport is injectable, so the 429 storm is a unit test)
- EDGAR submissions API · full-text search · XBRL company-facts endpoint
- Section parser: `lxml`/`selectolax` on the primary HTML document (exact choice decided in the parser design)
- Paragraph diff + alignment: pure Python, deterministic
- Vector retrieval (local, keyless; chosen at M6)
- `anthropic` SDK for classification and QA, behind a thin provider interface (multi-provider comparison)
- `spancheck` for citation + abstention scoring
- FastAPI + a small read view
- DuckDB for the derived tables (sections, paragraphs, diffs, labels)

## Conventions

- **`data/` is gitignored in full**, including the EDGAR response cache, parsed sections and DB files. Small,
  hand-picked filing excerpts used as **golden fixtures** live in `tests/fixtures/` and are committed. SEC filings
  are public records.
- The parser, aligner and diff are **pure** (no I/O, no clock, no network), so their tests are fast and total.
- **Model calls are cached by request hash** (`data/model-cache/`, shipped as a release artifact). Every published
  number can then be reproduced **without an API key** (FD-DEC 007).
- No secrets in code. Read them from `.env` (gitignored). `.env.example` lists every variable with a placeholder.
- **Commit at each phase boundary** with a readable message. The git history is an interview artifact.
- Update `DECISIONS.md` on every non-trivial choice, with the rejected alternative and the reason.
- Every figure in any doc must be reproducible on request from a command in the repo. Unknowns stay `[TKTK]`.
- State the **filing types and exact date range ingested** wherever coverage is described.

## Session notes: the build journal (every session)

`docs/BUILD-LOG.md` is the dated journal of this build. **Keep it current every session.** It is the primary raw
material for the case study and can't be reconstructed afterwards. Each session appends (or updates) a dated entry
with: **what happened · decisions (→ also `DECISIONS.md`) · learnings · what broke and the fix · what's open/next.**
Write down the process and the judgment calls, not just the numbers. This is part of each milestone's definition of
done.

## Definition of done (per milestone)

- The milestone's checklist in `TODO.md` is complete, and **its verification artifact exists**: golden-file tests,
  a published rate, a confusion matrix, or a `spancheck` report.
- The behaviour is demonstrable from a **clean clone** with no API key, using cached EDGAR and model responses.
- New decisions are recorded, BUILD-LOG is updated, and a commit marks the boundary.
- **Stop and wait for approval before starting the next milestone.**

## Do not

- Do not call EDGAR without the declared User-Agent, the rate limiter, or the cache.
- Do not put a model call anywhere in parsing, alignment or diffing.
- Do not let a parse failure disappear. If it isn't in the log and the rate, it's a bug.
- Do not return an uncited answer, or a citation whose text isn't an exact substring of its section.
- Do not write forward-looking, predictive or investment-advice language in any output or doc.
- Do not commit `data/`, `.env`, or any API key or User-Agent email.
