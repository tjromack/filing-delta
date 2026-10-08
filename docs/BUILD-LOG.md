# filing-delta — build log

A running, dated record of the process, decisions, learnings, and what broke as filing-delta is built. **This is the
primary raw material for the case study.** Keep it specific, and only give numbers that were measured. Per
`CLAUDE.md`, keeping it current is part of each milestone's definition of done.

Entry template: **What happened · Decisions · Learnings · What broke (+ fix) · Open/next.**

## Index (kept current)

| Milestone | Commit | Headline (measured) | The break worth telling |
|---|---|---|---|
| Phase 0 · scaffold | `b01f044` | — | — |

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
