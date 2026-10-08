# Section-parser design (M0)

**Status:** approved 2026-10-08 (FD-DEC 010). Implementation is M2.
**Scope:** extract **Item 1A (Risk Factors)** and **Item 7 (MD&A)** from 10-K primary documents, and
**Part II Item 1A** and **Part I Item 2 (MD&A)** from 10-Qs. Produce canonical text with stable offsets, a
recorded outcome for every (filing, section), and enough evidence to audit each decision.

This is the layer where the build "silently breaks" (playbook p. 28). The design's job is to make every break
loud: a wrong boundary must either fail a cross-check or be listed in the failure log.

---

## 1. What the sample showed

18 primary documents from 11 filers, fetched 2026-10-08 with the declared User-Agent and cached under `data/m0/`.
Every observation below can be reproduced with `tools/m0_survey/` (see its README).

| Filer | Form · period | Accession | HTML era |
|---|---|---|---|
| Apple | 10-K FY2025 · 10-K FY2016 · 10-Q Q3 FY2026 | 0000320193-25-000079 · 0001628280-16-020309 · 0000320193-26-000020 | iXBRL · pre-iXBRL · iXBRL |
| JPMorgan Chase | 10-K FY2025 · 10-Q Q2 2026 | 0001628280-26-008131 · 0001628280-26-054343 | iXBRL |
| Exxon Mobil | 10-K FY2025 | 0000034088-26-000045 | iXBRL |
| Ford | 10-K FY2025 | 0000037996-26-000015 | iXBRL |
| Walmart | 10-K FY2026 (Jan FYE) | 0000104169-26-000055 | iXBRL |
| Weyco Group | 10-K FY2025 · 10-K FY2015 · 10-Q Q2 2026 | 0001104659-26-027690 · 0001144204-16-087188 · 0001104659-26-092615 | iXBRL · pre-iXBRL · iXBRL |
| Berkshire Hathaway | 10-K FY2025 · 10-K FY2016 | 0001193125-26-083899 · 0001193125-17-056969 | iXBRL · pre-iXBRL |
| General Electric | 10-K FY2025 · 10-K FY2018 | 0000040545-26-000008 · 0000040545-19-000014 | iXBRL · pre-iXBRL |
| Pfizer | 10-K FY2025 | 0000078003-26-000026 | iXBRL |
| Coca-Cola | 10-K FY2025 | 0001628280-26-010047 | iXBRL |
| Netflix | 10-K FY2025 | 0001065280-26-000034 | iXBRL |

### Four layout archetypes

| Archetype | Where seen | What the parser has to do |
|---|---|---|
| **A. Linear item headings** | Apple ×3, Coca-Cola, Netflix, Walmart, Weyco ×3, Ford, Pfizer, Berkshire ×2 (13 of 18) | Find the heading, and end the section at the next item heading. |
| **B. In-document pointer stub** | JPM 10-K (Item 7: "…appears on pages 46–160"), Exxon (Item 7: "Reference is made to … the Financial Section") | Item 7 is a one-sentence pointer. The real MD&A is elsewhere, under a named heading. Follow it. |
| **C. Cross-reference index** | GE FY2025, GE FY2018 | The body has no "Item 1A" heading at all. Items appear only in a *Form 10-K Cross Reference Index* at the end, mapped to printed page numbers ("Risk Factors 24-31", "MD&A 7-22"). |
| **D. Pointer to another filing** | JPM 10-Q Part II Item 1A ("Refer to Part I, Item 1A … of JPMorganChase's 2025 Form 10-K") | The section exists, but its whole content is a reference out. This is a real state, not a parse failure. |

### Heading variation (all from archetype A)
- **Split across table cells.** In Apple FY2016, Walmart, Pfizer and Berkshire FY2016, `Item 1A.` and `Risk Factors`
  are separate `<td>`s in one row. Cells must be joined per row before matching.
- **Punctuation and spacing.** Seen: `Item 1A. Risk Factors`, `ITEM 1A RISK FACTORS` (no period, Weyco),
  `Item 1A.Risk Factors` (no space, Netflix), `ITEM 1A. Risk Factors.` (trailing period, Ford), and
  `Item 1A` / `Item 7` without a period (Ford TOC).
- **Bold is not reliable.** JPM's real headings are not bold. Exxon's and Pfizer's are bold inside tables. Bold can
  be a tiebreaker, never a requirement.

### Things that look like headings but aren't
- **Table of contents.** Every 10-K except GE's lists the items near the top, often as `<a href="#…">` links. These
  must never be taken as section starts.
- **Running page headers.** Ford repeats `Item 1A. Risk Factors (Continued)` (×14) and `Item 7. … (Continued)` (×50).
  Berkshire repeats `Management's Discussion and Analysis` (×29), JPM (×39) and Exxon (×32). These are page
  furniture. They must not become section starts, and they must be removed from body text so they don't pollute
  paragraphs and the diff.
- **Other page furniture.** Bare page numbers (`24`), `Table of Contents` back-links (Exxon, every page), and footers
  like `Apple Inc. | Q3 2026 Form 10-Q | 20`.
- **"Risk factors related to…" subheadings** (Weyco, Netflix) live *inside* Item 1A. They are not boundaries.

### 10-Q specifics
- `Item 2` appears twice: Part I Item 2 is MD&A, and Part II Item 2 is "Unregistered Sales of Equity Securities". So
  10-Q parsing has to track **Part**.
- Part II Item 1A ranges from a full risk-factor section (Apple 10-Q, with complete text) to a one-line pointer
  (JPM, archetype D).

### TOC anchors are a second, independent signal
In 17 of 18 documents, the TOC has `href="#id"` links for the target sections that resolve to elements in the
document. The Weyco 10-Q has no internal links at all. **Anchors can also be wrong:** in GE FY2018, one MD&A link
dangles (no matching id), and another resolves to position 0.010, inside the front matter. So anchors are a signal,
not the truth. In Exxon, the TOC has **two** MD&A links: Item 7 points to the stub, and the Financial Section TOC
points to the real MD&A. That's archetype B, visible in the anchors.

### Encoding
- All 18 files are pure ASCII, with every non-ASCII character written as an entity.
- **The older filer agents write apostrophes as `&#146;`** (Weyco FY2015: 299 occurrences; Berkshire FY2016: 484).
  That's a numeric reference into the C1 control range, and lxml decodes it literally to U+0092 instead of `’`.
  HTML5 says to map it through Windows-1252. **This must be fixed during decoding.** Otherwise `Management’s` and
  `Management\x92s` will diff as a change, and citation substrings won't match what a reader sees.
- Walmart writes straight `'` in places where other filers write `&#8217;` (`’`). The same filer can switch styles
  between years, for example after a filer-agent change (Weyco used four different filer-agent prefixes in 12 years).
  The **diff** has to fold quote and dash styles. The **citation text** has to keep the source characters.

---

## 2. Design

### 2.1 Pipeline (pure functions, no I/O, no clock, no network)

```
bytes ──decode──▶ DOM ──flatten──▶ Block stream ──locate──▶ Boundaries ──slice──▶ Section(text, offsets, evidence)
                                      │                        ▲
                                      └── furniture detection ─┘
```

1. **`decode(bytes) → str`.** Use the declared charset if there is one. Otherwise strict UTF-8, otherwise
   Windows-1252. Never Latin-1. After entity expansion, **remap C1 controls U+0080–U+009F through Windows-1252**
   (so `&#146;` becomes `’`). Record the remap count as evidence.
2. **`flatten(dom) → [Block]`.** Remove the hidden `ix:header`. Emit *leaf* blocks (`p`, `div`, `td`/`th`, `li`,
   `h1`–`h6` with no block descendants) in document order. Each Block carries: index, whitespace-collapsed text,
   `in_table`, `row_text` (all cells of the enclosing `<tr>` joined by a space), `bold`, `is_link`, `ids` (ids or
   names on the block or its descendants), and the source element path for the read view.
3. **`furniture(blocks) → set[index]`.** Mark page furniture: bare page numbers (including `K-24`-style), `Table of
   Contents` back-links, short text repeated ≥3 times (running headers, footers), and any text ending in
   `(Continued)`. Furniture is excluded from both boundary detection and section text, and the count is kept as
   evidence.
4. **`locate(blocks, form) → Boundaries`.** See 2.2.
5. **`slice(blocks, boundaries) → Section`.** See 2.4.

### 2.2 Locating boundaries: two independent signals, then reconcile

**Signal 1: heading scan.** Match `row_text` (falling back to `text`) against a heading grammar:
`^(PART\s+[IV]+\W*)?ITEM\s*(\d+[A-C]?)\s*[.:\-—–]?\s*(title)?`, case-insensitive, NBSP-tolerant, with the title
checked against a per-item title list (`risk factors`, `management['’]s discussion and analysis…`). A candidate
must be short (< ~150 chars), not furniture, not a link, and positioned **after** the TOC region. The TOC region
ends at the last block that is a link to an item heading, or at the last block of a dense run of item listings.
For 10-Qs, a `PART I` / `PART II` marker sets the part context.

**Signal 2: TOC anchors.** Resolve `href="#x"` links whose row text names a target item or title to the element
with `id`/`name` = x, and then to the first block at or after it.

**Reconcile.**
- Both agree on the start (same block, or within a few blocks of only furniture or empty text): **start confirmed**.
- Only one signal exists, as in the Weyco 10-Q with no links: use it, mark `single_signal`.
- They disagree: **prefer the heading scan** only if the anchor target's block isn't itself a heading. Otherwise the
  outcome is `partial` with reason `signal_conflict`, and both candidates are recorded.
- **End** = the start of the next item heading in document order (Item 1B/1C/2 after 1A; Item 7A/8 after 7; for
  10-Qs, Part I Item 3/4 or Part II Item 2+). The end is never derived from page numbers alone.

### 2.3 Archetypes B, C, D

- **B, pointer stub.** After slicing, if a section body is shorter than a stub threshold *and* matches the
  cross-reference grammar (`reference is made to`, `appears on pages`, `refer to`, `incorporated herein by
  reference`, `see … section`), then **follow it**. Find the named heading it quotes (e.g. `Management's
  Discussion and Analysis`) as a non-furniture, non-TOC heading after the stub, also using any second TOC anchor
  for that title (Exxon). End the section at the next heading of equal or higher rank in that part's own TOC, or
  else at the next top-level named section. Record `resolution = "followed_pointer"` together with the stub text.
  If the target can't be found, the outcome is `failed` with reason `pointer_target_not_found`, and the stub text
  is kept.
- **C, cross-reference index.** Detect `FORM 10-K CROSS REFERENCE INDEX` (GE). Use the front TOC's named-section
  anchors (`Risk Factors` → GE's link resolves) for the start. Validate against the index's printed page range by
  mapping page-number furniture blocks to positions. The end is the next front-TOC anchor. GE is the hardest case
  in the sample, so the default expectation is `partial` with reason `page_range_unverified` until the page-map
  check passes. **Proposal:** keep GE in the corpus *as* the stress case. Its outcomes, whatever they turn out to
  be, are published in the failure log.
- **D, pointer out of the filing.** Keep the section with `form = "pointer"` and its text, as outcome `ok`. The
  diff and QA layers treat "no update; refers to the 10-K" as its own state. It is not an empty section and not a
  failure. The pointer is never followed into another filing.

### 2.4 The offsets contract (what citations depend on)

- `Section.text` is **canonical text**: non-furniture blocks between the boundaries, whitespace-collapsed within a
  block, and joined by `\n\n` at block breaks. Characters are preserved as decoded (after the C1 remap). No case
  folding, no quote folding.
- A **paragraph join rule** handles pages that break mid-sentence. If removing furniture leaves a block that doesn't
  end in terminal punctuation, followed by a block that starts lowercase, join them with a single space instead of
  `\n\n`. This matters for M3's paragraph diff, and each join is counted as evidence.
- Every citation (M6) is `(accession, section_id, char_start, char_end)` into `Section.text`. The verifier checks
  that the cited string equals `Section.text[char_start:char_end]`. `Section.text` and its sha256 are persisted, so
  offsets can never drift under a re-parse without the hash changing.
- `Section.block_map` maps character ranges back to source block element paths, so the read view can highlight
  the original HTML.
- **The comparison key is separate.** The diff (M3) compares a *folded* form: quotes, dashes and whitespace
  normalized, NFKC. It reports changes against canonical offsets. Quote-style churn therefore never shows up as a
  "change", while citations still show the source's own characters.

### 2.5 Outcome model (pin 4: nothing silently skipped)

Every (filing, section) gets exactly one record:

```
ParseResult {
  accession, form, section: "10K_1A" | "10K_7" | "10Q_P2_1A" | "10Q_P1_2",
  outcome:   "ok" | "partial" | "failed",
  form_kind: "full" | "pointer",                    # D is ok+pointer
  reasons:   [ "single_signal" | "signal_conflict" | "followed_pointer" | "pointer_target_not_found"
             | "page_range_unverified" | "too_short" | "bleed_detected" | "no_heading" | "order_violation" | … ],
  evidence:  { heading_block, anchor_block, end_block, furniture_removed, c1_remapped, joins, char_len, sha256 },
}
```

**Sanity gates run on every `ok`** and downgrade it to `partial` if any of them trips:
- **bleed:** another item heading appears inside the section;
- **order:** 1A starts before 7 in a 10-K;
- **length:** a `full` Item 1A or Item 7 is shorter than a floor (the floor gets calibrated from the corpus and
  documented, not guessed);
- **coverage:** sections must not overlap.

**Published metrics:** the parse-success rate (`ok` / total) per section and per archetype, plus
`docs/parse-failures.md` with one line per non-`ok` record, each with its reason and the stub or heading text.

### 2.6 Golden fixtures and tests

- **Boundary goldens, verified by hand.** For each golden filing, `tests/golden/sections.yaml` records the
  accession, section, first ~80 chars, last ~80 chars, char length and sha256 of the canonical text. The tool
  *proposes* each boundary, and **Trevor confirms** it by reading the filing. That's the same rule as the hand
  labels: the parser never grades itself.
- **Golden set** (proposed): one filing per archetype × era, at least 12 sections. Apple FY2025 and FY2016 (A),
  Ford FY2025 (A + running headers), Weyco FY2015 (A + `&#146;`), Weyco 10-Q (no anchors), JPM 10-K (B), Exxon (B
  with a double anchor), GE FY2025 (C), JPM 10-Q (D), Walmart (A, straight quotes, non-December FYE).
- **Full filings aren't committed** (1–13 MB each). Golden tests read them from the EDGAR cache, which ships in the
  release artifact. **Small committed fixtures** (`tests/fixtures/*.html`, a few KB each) are excerpts cut from
  real filings for unit tests of each mechanism: split-cell headings, `(Continued)` headers, a C1 entity, a pointer
  stub, a cross-reference index, and a 10-Q Part II `Item 2` collision.
- **Property tests:** decoding is idempotent, `Section.text` never contains a furniture string, and the same bytes
  always produce byte-identical `ParseResult` and text (the determinism pin).

### 2.7 Library choice

**lxml** (`lxml.html`). It's already proven against all 18 sample files, it's tolerant of malformed legacy HTML,
and it gives fast XPath for id resolution. **Rejected:** BeautifulSoup (an order of magnitude slower on 13 MB JPM
documents for no gain), and selectolax (faster, but a weaker API for ancestor queries, which TOC-row and
table-cell joining need). Note that `uv pip install --native-tls` works through the proxy.

---

## 3. Explicitly out of scope for the parser

- Exhibits and financial statements. The Exhibit 13 annual-report pattern (MD&A incorporated from an exhibit) did
  not appear in this sample. If it shows up in the corpus, it gets a `failed: exhibit_incorporation` record, not a
  silent fetch.
- Pre-2001 `.txt` filings.
- 8-K item parsing. 8-Ks enter only the QA corpus (FD-DEC 008 proposal).

## 4. Risks I'm not yet sure about

- **Archetype C page mapping** may be too fragile across years. The fallback is front-TOC anchors with a `partial`
  outcome. The failure log will show which way it went.
- **The stub threshold and length floor** need calibrating on the full corpus, and they'll be documented with the
  distribution that justified them.
- **Sub-heading ranks inside a followed pointer** (where JPM's MD&A ends) depend on the in-document TOC structure.
  JPM states the page range ("pages 46–160"), so the page map can act as a cross-check there.

---

## 5. Amendments during implementation (M2, 2026-10-08)

The approved design held. Running it over the full corpus refined it in these places; each is a DECISIONS entry:

- **A third section kind, `absent`** (FD-DEC 012): a verified omission is neither a success nor a failure.
- **Following a pointer uses running-header extent** (FD-DEC 013), checked against any page range the pointer states.
- **TOC-anchored sections end after their TOC group** (FD-DEC 014), with GE's cross-reference index as the check.
- **Furniture rules tightened** (FD-DEC 015) after two rules were found deleting real content.
- **Running headers that are Item headings.** Berkshire's 10-Q prints "Item 2. Management's Discussion…" atop every
  MD&A page, so the first occurrence is the heading. "(Continued)" headers never are.
- **Title lines and run-in headings.** A bare title line directly under the heading or anchor ("RISK FACTORS") is
  excluded from the text. A run-in heading paragraph ("RISK FACTORS. The following…", GE 2020+) is kept.
- **The archetype C page check** turned out to be practical: GE's footers read "2025 FORM 10-K 23",
  "GE 2020 FORM 10-K 44" or "2025 2Q FORM 10-Q 5", and the lenient footer reader handles all three.
- **Exhibit incorporation was real** (Pfizer FY2018–19). It is `failed: exhibit_incorporation`, as §3 anticipated.
