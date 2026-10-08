# filing-delta — decisions log

> Append-only. A point-in-time record of the calls made, so they aren't re-litigated. Author: Trevor J. Romack.
> This is BUILD 3 of the portfolio slate: SEC filings drift & grounded QA.
> Format: **Decision · Alternative rejected · Why.** Entries marked *Proposed* await approval.

## FD-DEC 001 — Scope, home, and stack (2026-10-08)
**Status:** Decided (from the playbook v3 kickoff packet, pp. 27–28).

- **Decision:** ingest 10-K, 10-Q and 8-K filings from EDGAR. Diff the narrative sections (Item 1A, Item 7) period
  over period and classify each change as material or cosmetic. Answer grounded questions over the corpus with span
  citations, or abstain. Python. The repo lives at `C:/dev/filing-delta`, remote `tjromack/filing-delta`, private
  until it clears §01 at 14+.
- **Alternative rejected:** a TypeScript build. S1 and B4 carry the TypeScript signal, and B3 reuses `spancheck`
  (Python) directly.
- **Why:** B3 is the second regulated vertical, and it produces B4's finance corpus. Half of it is deterministic,
  which gives the cleanest available story about where a model was used and where it deliberately wasn't.

## FD-DEC 002 — The diff is deterministic; the model judges only after it (2026-10-08)
**Status:** Decided (playbook pin).

- **Decision:** parsing, paragraph alignment and the diff contain no model calls and are golden-file tested.
  Material/cosmetic classification is a downstream stage that reads the diff's output and is scored against hand labels.
- **Alternative rejected:** asking a model to "compare these two risk-factor sections." That's cheaper to build, but
  it's untestable, non-reproducible and can't be cited.
- **Why:** the diff is the evidence, and evidence has to be reproducible. Only the judgment stage gets the model, and
  that stage is scored.

## FD-DEC 003 — Verification is part of the build (2026-10-08)
**Status:** Decided (the portfolio's overriding discipline).

Every milestone ships its check: golden-file tests for parsing and diffing, a published parse-success rate plus
`docs/parse-failures.md`, the material/cosmetic confusion matrix, a 429-storm back-off test, and the `spancheck`
citation/abstention report. If the check isn't written, the milestone isn't done.

## FD-DEC 004 — EDGAR client: httpx + truststore, injectable transport (2026-10-08)
**Status:** Decided.

- **Decision:** build the client on `httpx` with `truststore.inject_into_ssl()`. It has a token-bucket rate limiter
  set conservatively below SEC's 10 req/s ceiling, a required `EDGAR_USER_AGENT` (it refuses to start without one), a
  content-addressed on-disk cache keyed by URL, and exponential back-off with jitter that honors `Retry-After` on
  429/503. The transport is injectable, so tests can replay a scripted 429 storm with no network.
- **Alternative rejected:** shelling out to `curl`, which is the banked proxy workaround clear-pricer used for bulk
  downloads. It works on this machine, but rate limiting, retry semantics and the 429-storm test would all have to
  live outside Python. That makes them harder to test and to read.
- **Why:** the playbook names "REST integration under real rate limits" as a gap this build closes, so the client
  *is* part of the evidence. `curl` stays available for one-off bulk pulls such as golden fixtures.
- **Rate ceiling:** **5 req/s**, half of SEC's 10 (set at M1). `RateLimiter` refuses anything above 10, and
  `test_rate_ceiling_is_never_exceeded` asserts no more than 5 requests in any 1-second window. A 429's
  `Retry-After` pauses the limiter itself, so the wait applies to every request that follows. A 403 is never
  retried, because SEC uses it for undeclared or abusive clients, and retrying would make it worse.

## FD-DEC 005 — Cite-or-abstain is a type, not a prompt instruction (2026-10-08)
**Status:** Decided.

- **Decision:** QA output is a tagged union, `Answer(text, citations≥1) | Abstain(reason)`. A post-generation
  verifier checks that every citation is an exact substring of its stored section at the stated offsets. Any answer
  that fails becomes `Abstain("citation_unverifiable")`.
- **Alternative rejected:** relying on the prompt to make the model cite. That gives no guarantee, and a hallucinated
  citation looks exactly like a real one.
- **Why:** the pin "there is no third option" has to hold even when the model misbehaves.

## FD-DEC 006 — spancheck from PyPI; model id from env (2026-10-08)
**Status:** Decided.

- **Decision:** depend on `spancheck` from PyPI, pinned to a version. The Anthropic model id is read from
  `ANTHROPIC_MODEL`, defaulting to `claude-sonnet-5-5`. Model calls go through a thin provider interface, so a second
  provider can be compared later.
- **Alternative rejected:** vendoring spancheck, which would fork B1 and undercut the claim that it's
  infrastructure. Hardcoding the model id has already broken once (`claude-sonnet-5` was deprecated).

## FD-DEC 007 — Keyless reproducibility via recorded model responses (2026-10-08)
**Status:** Decided (the default was accepted when the scaffold was approved on 2026-10-08).

- **Decision:** cache every model request/response by a hash of (provider, model, prompt, params). Ship the cache,
  together with the EDGAR cache for the locked corpus, as a GitHub Release artifact. A cold clone then reproduces the
  diff, the confusion matrix and the spancheck report **without an API key or a single EDGAR request**. Live mode
  (`--live`) re-runs against the API.
- **Alternative rejected:** making the try-it path require an Anthropic key. §01 Gate 6 scores that a 1, and Gate 6
  can't be zero.
- **Why:** Gate 6 and Gate 1 both need a cold, keyless run. Recorded responses also pin the published numbers to
  exact model outputs.

## FD-DEC 008 — Corpus: companies, filing types, date range (2026-10-08)
**Status:** Decided. Locked 2026-10-08 after the 18-document survey (`docs/design/section-parser.md` §1).

- **Companies (11).** Chosen so that each layout archetype is covered, not by market cap: Apple, Coca-Cola, Netflix,
  Walmart (January FYE), Pfizer, Ford (running headers), Weyco Group (small cap, four filer agents), Berkshire
  Hathaway, JPMorgan Chase (pointer stub, plus a 10-Q that points out to the 10-K), Exxon Mobil (pointer to the
  Financial Section), and General Electric (cross-reference index, the deliberate stress case).
- **10-K:** fiscal years **2018–2025**, eight per company and seven year-over-year diffs. The range crosses the
  2019–2021 iXBRL transition (the parser has to survive both eras) and the FY2019→FY2020 pandemic risk-factor
  rewrite (real, large drift to classify).
- **10-Q:** filed **2025-01-01 → 2026-09-30**. Part II Item 1A and Part I Item 2.
- **Alternative rejected:** the most recent 3 years only. It's cheaper, but it has a single HTML era and no large
  drift event, so it would under-test both the parser and the classifier.
- **Alternative rejected:** dropping GE. It would raise the parse-success rate by hiding the hardest layout.
  Keeping it and publishing its outcome is the point.
- **8-K's role (open):** 8-Ks are event-driven, with no year-over-year counterpart, so they don't fit the diff. The
  proposal is to use them only in the grounded-QA corpus, where they are a good source of unanswerable-but-plausible
  questions. 8-K Item 2.02 points to exhibits, which are out of scope.
- The README will state the exact filing types and date range once this is locked.

## FD-DEC 009 — License: MIT (2026-10-08)
**Status:** Decided (the default was accepted when the scaffold was approved, matching clear-pricer).

## FD-DEC 010 — Section parser: two independent signals, reconciled; lxml (2026-10-08)
**Status:** Decided. Approved 2026-10-08. See `docs/design/section-parser.md`.

- **Decision:** locate boundaries with a heading-grammar scan *and* TOC-anchor resolution, then reconcile them.
  Handle the pointer-stub, cross-reference-index and pointer-out archetypes explicitly. Every (filing, section)
  gets an `ok`/`partial`/`failed` record with reasons and evidence. Canonical text (citation offsets) is kept
  separate from the folded comparison key (the diff). Library: lxml.
- **Alternative rejected:** heading regex alone. The TOC, running headers and archetypes B and C all defeat it
  silently. **Also rejected:** TOC anchors alone. They're missing in the Weyco 10-Q and wrong in GE FY2018.
- **Why:** with two signals, a disagreement becomes a logged `partial` instead of a silently wrong boundary.

## FD-DEC 011 — Corpus windows: 10-K by period of report; amendments excluded (2026-10-08)
**Status:** Decided (M1).

- **Decision:** a 10-K is in the corpus when its *period of report* is in 2018-01-01..2025-12-31. That gives eight
  annual reports per filer whatever the fiscal year end (Apple ends in September, Walmart in January). A 10-Q is in
  when its *filing date* is in 2025-01-01..2026-09-30. Forms are matched exactly, so 10-K/A and 10-Q/A are excluded.
  The windows live in `corpus.toml`, and `corpus/manifest.csv` (committed) lists every accession ingested, with its
  sha256.
- **Alternative rejected:** windows by filing date for 10-Ks. A January-FYE filer then lands its "2025" report in
  2026, and the per-filer year counts stop lining up.
- **Alternative rejected:** including amendments. 10-K/As are often partial (Part III only, or a single exhibit),
  and they'd break year-over-year pairing. If one turns out to restate Item 1A or Item 7, that's a known limitation
  to state, not something to handle silently.
