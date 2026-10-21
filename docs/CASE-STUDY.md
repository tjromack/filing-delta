# filing-delta: what changed between a company's filings, and where it says so

*Coverage throughout: 10-K filings with a period of report from 2018-01-01 to 2025-12-31 and 10-Q filings filed
2025-01-01 to 2026-09-30, for 11 companies (144 filings, every accession listed in `corpus/manifest.csv`). No 8-Ks:
they were planned for the question set and dropped (FD-DEC 040). Every figure below is reproduced by
`tools/reproduce.py` or comes from the build journal, `docs/BUILD-LOG.md`, which says which is which.*

## The situation

A company's annual report repeats most of last year's risk factors and management discussion, word for word or
nearly. The few paragraphs that are new, gone or rewritten are what a reader actually needs, and they are buried
in a hundred pages of text that didn't change. Comparing the documents by hand takes hours and is easy to get
wrong. A summary that says "the risk factors now emphasize supply-chain concerns" is no help unless the reader can
see the sentence it came from, because the next question is always "where does it say that?" Without a way to
check, a reader either re-reads everything or trusts a paraphrase they can't verify.

## Constraints

- **The source has rules.** SEC's EDGAR asks for a declared identity on every request and at most 10 requests a
  second. The client refuses to start without the identity, holds itself to 5 a second, and caches every response.
  A re-run of the full corpus makes zero requests.
- **The text is unaudited.** Risk factors and MD&A are management's narrative, and MD&A figures are often
  non-GAAP. The tool can report what the text says and how it changed, never whether it is true, and never what it
  means for a stock.
- **A stranger has to be able to check every number without an API key.** Every model response is recorded by
  request hash and shipped as a 63 MB data release, so the published numbers replay exactly.
- **One labeler.** I built this with Claude Code, and every human label is mine, done at gates alongside the build.
  That limits how many labels exist, and it shaped how they were collected (below).

## The design

The design splits on one line: everything that produces evidence is deterministic, and the one stage that makes a
judgment is a model, scored separately.

1. **Parse** the narrative sections out of each filing's HTML. Every section ends in exactly one outcome (`ok`,
   `partial`, `failed` or `absent`) with a reason, and every non-`ok` outcome goes to a committed log.
2. **Diff** each section against the prior period, paragraph by paragraph: added, removed, reworded, moved. No
   model, byte-identical on every run.
3. **Classify** each change as material or cosmetic. This is the only model judgment in the diff half. It reads the
   diff's output, never feeds back into it, and is scored against blind human labels.
4. **Answer questions** with citations that must be exact substrings of the stored section, or abstain. The
   answer type admits nothing else, and one unverifiable citation turns the whole answer into an abstention.

**The rejected alternative:** handing a model both years' sections and asking what changed. It's much less work to
build, but its output can't be tested, won't reproduce, and doesn't point at a span. The deterministic diff is the
evidence, and evidence has to come out the same every time (FD-DEC 002).

## The spine: the parse-failure log

`docs/parse-failures.md` started as a rule ("parse failures are logged, never silently skipped") and ended as the
build's habit. It holds two rows now. How it got there is the story.

Before any parser was written, we surveyed 18 real filings and found four layouts where we'd expected one. JPMorgan and
Exxon make Item 7 a single sentence pointing elsewhere ("appears on pages 46–160"). GE has no Item headings in the
body at all, only a cross-reference index at the back. A naive "find Item 7" would have returned a one-sentence
stub as JPMorgan's entire MD&A and reported success. So the outcome model came first. Pointers, cross-reference
indexes and items a filer marks "not applicable" each became a named outcome, and a section that can't be located
has to say why.

The first full pass over the 144 filings had 10 failed and 41 partial sections, as recorded in the journal at the
time (the current code doesn't regenerate that pass). Each one was read in the filing itself before any code
changed. Two of the fixes deleted less, not more. A rule that treated any bare number as a page number had been
eating table cells. A rule that treated text repeated near page breaks as a running header had eaten JPMorgan's
"COVID-19 Pandemic" subheading. Removing text is the dangerous operation, so those rules now need structural
evidence (FD-DEC 015). The final pass: **270 of 272 present sections `ok` (99.3%), 16 verified absent, 2 failed**
(`docs/parse-report.md`). In 184 of the 288 sections, the heading and the table-of-contents anchor agree. Every
other section records the rule that located it.

The two failures are Pfizer's FY2018 and FY2019 MD&A, which are incorporated from an exhibit outside the primary
document. They stay `failed`, with that reason, rather than being fetched from the exhibit by a special case. The
same root cause turned up again three milestones later: Pfizer FY2019's primary document carries only 77 tagged
facts, the cover page, because its statements are in the exhibit too. The financial-data join uses the SEC's
company-facts API for that one filing and records why. One honest row in a log is easier to defend than a special
case nobody can see.

The log's limit is that it only shows what the parser knows it got wrong. 99.3% is the parser grading itself through
its own sanity checks. The two things that made it believable came from outside the parser. I confirmed 28
section boundaries in 14 filings, covering every layout and HTML era, against the filings themselves. And the diff
caught an error the parser had passed: JPMorgan's MD&A had lost its last page in 5 of 8 years, because JPMorgan
prints its running header only on alternate pages. Inside one filing a missing page is invisible. Across years it
shows up as text appearing and disappearing at the edge of the section. The fix ends a pointed-to section at its
stated last page (FD-DEC 019).

The same rule carried into every later stage. A question that can't be answered from the filings abstains with a
reason, as a section that can't be found fails with one. The data release is checked against a committed manifest
before it unpacks. And the reproduction refuses to pass if any committed report changes by a byte.

## How it's verified

All results are in the README's verification table and regenerate on a fresh Linux runner, with no API key, on every
push.

- **Section boundaries:** 28 human-confirmed golden sections. Parse rate as above.
- **Paragraph alignment** (does "reworded" mean the same disclosure, rewritten?): against 70 blind, stratified
  human labels, precision **0.83** (95% CI 0.74–0.93), recall **0.80** (0.66–0.93). The labeling question turned out
  to be ambiguous. "Same type of disclosure" and "same instance" give different answers when a template is reused
  for a new event. I chose the instance criterion, the one the product claims. On the same labels, the best
  simple rule fell from an F1 of about 0.90 to about 0.82. The published figures use the instance criterion.
- **Material vs. cosmetic:** 122 blind human labels, scored once with a frozen prompt. Agreement 77%, "material"
  precision **0.89** (0.81–0.96), recall **0.80** (0.68–0.89). The misses cluster on restructured passages. Our first
  explanation was that the labeler hadn't seen the context the model saw. A re-check, with the context shown, tested
  that and it mostly failed: I held my label on 7 of the 9 items it applied to. The misses are a real
  difference in reading the guide, and they are reported as one (`docs/materiality-error-analysis.md`).
- **Financial data:** values read from each filing's inline XBRL agree with the SEC's company-facts API on **65,243
  of 65,243**. The first cross-check said 99.83%: the extractor kept a rounded duplicate ("$4.9 billion") over the
  exact one. MD&A headline figures are compared against the same filing's tagged values: 194 of 1,085 claims match
  and 878 can't be checked, because they are about segments or other periods. The hand check of that matcher is
  **not evidence**. Labels were made with its answer shown, and 0 of 99 were overridden at about 5 s each (FD-DEC
  026).
- **Questions:** on 60 questions (48 drafted by Claude, 12 written by me), pipeline v4 answered 37 of 37 answerable
  ones, each citing the key's passage, and correctly abstained on 23 of 23. Every citation verified as an exact
  substring. `spancheck` scored 59 of 60 answers as entailed by their own citations. **The answer key is
  model-built:** two models agreed on 58 of 60, I decided the other 2, and both were among the 12 questions I
  wrote, not the 48 Claude drafted. These are agreement figures, not an independent measurement (FD-DEC 031).
- **Exact-span guarantee:** 16 forged-citation tests (fabricated, altered, wrong offsets, wrong filing, one bad
  citation among good). On the real runs, the verifier has rejected nothing real yet. Its value so far is the
  guarantee, not a catch.

## What broke

The wrong assumption that took the most iterations: that a prompt rule could decide when it's safe to say "the
filing doesn't say this."

Questions like "does the 10-K discuss X?" often have the true answer "not in those words, but here's what it says
nearby." Version 2 answered those in that form, quoting the nearby text. On QA21 ("Netflix paid sharing"), that
turned an honest abstention into a confident false one: "the passages never mention paid sharing." Retrieval had
missed the filing's own wording, "multi-household usage." Every grader passed it, because the quote was real and
the answer followed from what was retrieved. Version 4 makes the model list other wordings and searches again
before any "doesn't say" answer. The first lexical check for that was a no-op ("sharing" and "shares" stem to the
same word) and was caught only because the test demanded the case actually trigger. Then the second search
over-answered two questions that asked for a specific figure, by finding nearby figures. The fix there was a rule
in code: a "doesn't say" answer to a figure question is refused (FD-DEC 038).

Each fix moved the failure somewhere else, until the boundary moved out of the prompt and into code. The report
now also lists every answer whose quotes miss the key's passage, so a false absence can't hide inside a 100%
abstention score.

## What this doesn't prove

- It isn't investment advice and makes no forward-looking statement. It reports what filings say and how the text
  changed.
- It doesn't verify management's narrative. Only a narrow slice of MD&A figures is checked against tagged values.
- It can't prove something is absent. "Doesn't say" means "wasn't found," after a second search.
- The question-answering figures are agreement with a model-built key. The classifier and alignment figures are
  agreement with one human labeler.
- "Material" is a labeled text-change category, not a legal or accounting materiality determination.
- It covers nothing beyond the filing types and date range above: no 8-Ks, amendments, exhibits or financial
  statements as narrative.

## What I'd do differently

I'd settle what a label means before anyone labels: the type-versus-instance question cost a second labeling pass,
and it was the real design decision behind the alignment threshold. And I'd treat "the filing doesn't say X" as a
retrieval problem from the start. A claim of absence needs a stronger search guarantee than a positive answer, and
three pipeline versions taught that the slow way.
