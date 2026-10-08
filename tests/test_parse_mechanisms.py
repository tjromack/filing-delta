"""Section parser: one test per mechanism found in the M0 survey and the M2 corpus runs.

The fixtures are small HTML documents built to reproduce the *shape* of a real filing's layout (the filer each
one is modeled on is named), with the prose shortened. Every regression found during M2 has a test here.
"""
from __future__ import annotations

from filing_delta.parse import parse_document
from filing_delta.parse.blocks import flatten
from filing_delta.parse.headings import furniture_detail, page_number

LOREM = ("The company faces risks that could adversely affect its business, results of operations and financial "
         "condition, including competition, regulation and macroeconomic conditions. ") * 40  # ~6,500 chars


def html(*body: str) -> bytes:
    return ("<html><body>" + "".join(body) + "</body></html>").encode("ascii", "xmlcharrefreplace")


def p(t: str, **style: str) -> str:
    st = ";".join(f"{k.replace('_', '-')}:{v}" for k, v in style.items())
    return f'<p style="{st}">{t}</p>' if st else f"<p>{t}</p>"


def brk() -> str:
    return '<div style="page-break-after:always"></div>'


def page(n: int, *content: str, header: str | None = None) -> str:
    """One printed page: optional running header, content, footer page number, page break."""
    return "".join(([p(header)] if header else []) + list(content) + [p(str(n)), brk()])


def toc(*entries: tuple[str, str, str]) -> str:
    rows = "".join(f'<tr><td><a href="#{a}">{item}</a></td><td><a href="#{a}">{title}</a></td>'
                   f'<td><a href="#{a}">{pg}</a></td></tr>' for item, title, pg, a in entries)
    return f"<table>{rows}</table>"


def tenk(**sections: str) -> bytes:
    """A linear 10-K (archetype A) with a linked TOC."""
    return html(
        toc(("Item 1.", "Business", "3", "i1"), ("Item 1A.", "Risk Factors", "5", "i1a"),
            ("Item 7.", "Management’s Discussion and Analysis", "20", "i7"), ("Item 8.", "Financial Statements", "40", "i8")),
        brk(),
        f'<p id="i1"><b>Item 1. Business</b></p>', p(LOREM[:500]),
        f'<p id="i1a"><b>Item 1A. Risk Factors</b></p>', sections.get("risk", p(LOREM)),
        '<p><b>Item 1B. Unresolved Staff Comments</b></p>', p("None."),
        f'<p id="i7"><b>Item 7. Management’s Discussion and Analysis of Financial Condition</b></p>',
        sections.get("mda", p(LOREM)),
        '<p><b>Item 7A. Quantitative and Qualitative Disclosures About Market Risk</b></p>', p("See Note 9."),
        f'<p id="i8"><b>Item 8. Financial Statements and Supplementary Data</b></p>', p(LOREM[:300]),
    )


# --- decoding and the block stream ----------------------------------------------------------------------------------

def test_c1_numeric_reference_is_remapped_through_windows_1252():
    """Weyco FY2015 / Berkshire FY2016: '&#146;' must become ’, not the U+0092 control character."""
    fl = flatten(b"<html><body><p>Management&#146;s Discussion</p></body></html>")
    assert fl.blocks[0].text == "Management’s Discussion"
    assert fl.c1_remapped == 1


def test_zero_width_spaces_are_whitespace():
    """Weyco's iXBRL filings pad with U+200B; left in, they'd break exact-substring citations."""
    fl = flatten(html(p("Risk&#8203; factors&#8203;&#8203; apply")))
    assert fl.blocks[0].text == "Risk factors apply"


def test_text_beside_child_blocks_is_not_dropped():
    fl = flatten(html("<div>Lead text <div>child block</div> trailing text</div>"))
    assert [b.text for b in fl.blocks] == ["Lead text", "child block", "trailing text"]


def test_rows_are_never_merged_across_tables():
    """Regression: row identity used id() of lxml proxies, which lxml reuses; unrelated rows merged (GE, Exxon)."""
    tables = "".join(f"<table><tr><td>R{i}A</td><td>R{i}B</td></tr></table><p>between {i}</p>" for i in range(3000))
    fl = flatten(html(tables))
    for b in fl.blocks:
        if b.text.startswith("R"):
            n = b.text[1:-1]
            assert b.row_text == f"R{n}A R{n}B"


def test_hidden_ixbrl_header_is_skipped():
    fl = flatten(html('<div style="display:none"><ix:header>hidden facts</ix:header></div>', p("visible")))
    assert [b.text for b in fl.blocks] == ["visible"]


# --- furniture --------------------------------------------------------------------------------------------------------

def test_page_number_formats():
    assert page_number("24") == 24
    assert page_number("- 24 -") == 24
    assert page_number("K-24") == 24
    assert page_number("Page 3") == 3
    assert page_number("2025 FORM 10-K 23") == 23
    assert page_number("24 2025 FORM 10-K") == 24
    assert page_number("GE 2020 FORM 10-K 44") is None                 # strict: has a company token
    assert page_number("GE 2020 FORM 10-K 44", lenient=True) == 44     # ...but fine for a known running footer
    assert page_number("2025 2Q FORM 10-Q 5", lenient=True) == 5
    assert page_number("FORM 10-K") is None


def test_numeric_table_cells_are_data_not_page_numbers():
    """Regression: any bare 1-3 digit block was furniture, deleting numbers from MD&A tables."""
    doc = html(page(1, p(LOREM[:200]), "<table><tr><td>Net income</td><td>994</td><td>812</td></tr></table>"),
               page(2, p(LOREM[:200])), page(3, p(LOREM[:200])))
    fl = flatten(doc)
    furn, _ = furniture_detail(fl.blocks)
    texts = {fl.blocks[i].text for i in furn}
    assert "994" not in texts and "812" not in texts
    assert {"1", "2", "3"} <= texts


def test_running_header_needs_consecutive_pages():
    """Regression: JPM 2020's real 'COVID-19 Pandemic' subheading sat atop three far-apart pages and was deleted."""
    pages = []
    for n in range(1, 31):
        content = [p("COVID-19 Pandemic")] if n in (3, 14, 27) else []
        pages.append(page(n, *content, p(LOREM[:300]), header="Annual Report"))
    fl = flatten(html(*pages))
    furn, running = furniture_detail(fl.blocks)
    covid = [b.idx for b in fl.blocks if b.text == "COVID-19 Pandemic"]
    header = [b.idx for b in fl.blocks if b.text == "Annual Report"]
    assert len(covid) == 3 and not set(covid) & furn
    assert set(header) <= running


# --- archetype A: linear headings ---------------------------------------------------------------------------------

def test_linear_10k_with_toc():
    res = parse_document(tenk(), "10-K")
    assert res["10K_1A"].outcome == "ok" and res["10K_1A"].reasons == []
    assert res["10K_1A"].text.startswith("The company faces risks")
    assert res["10K_7"].outcome == "ok"
    assert "Unresolved" not in res["10K_1A"].text and "Quantitative" not in res["10K_7"].text


def test_split_cell_heading_and_title_line_excluded():
    """Apple FY2016 / Walmart / Weyco pre-2020: 'Item 1A.' and 'Risk Factors' are separate cells of one row."""
    doc = html(
        toc(("Item 1A.", "Risk Factors", "5", "rf")),
        brk(),
        '<table><tr><td>ITEM 1A</td><td><a name="rf"></a>RISK FACTORS</td></tr></table>', p(LOREM),
        '<table><tr><td>ITEM 1B</td><td>UNRESOLVED STAFF COMMENTS</td></tr></table>', p("None."),
        '<p>ITEM 7 MANAGEMENT’S DISCUSSION AND ANALYSIS</p>', p(LOREM),
        '<p>ITEM 8 FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA</p>',
    )
    r = parse_document(doc, "10-K")["10K_1A"]
    assert r.outcome == "ok", r.reasons                  # the anchor in the heading's own row agrees
    assert not r.text.startswith("RISK FACTORS")


def test_continued_running_headers_are_not_headings_and_leave_the_text():
    """Ford: 'Item 1A. Risk Factors (Continued)' atop every page. Regression: its first copy was taken as a heading."""
    pages = [page(5, '<p id="rf"><b>ITEM 1A. Risk Factors.</b></p>', p(LOREM[:2500]))]
    pages += [page(n, p(LOREM[:2500]), header="Item 1A. Risk Factors (Continued)") for n in (6, 7, 8)]
    doc = html(toc(("Item 1A.", "Risk Factors", "5", "rf")), brk(), *pages,
               '<p><b>ITEM 1B. Unresolved Staff Comments.</b></p>', p("None."),
               '<p><b>ITEM 7. Management’s Discussion and Analysis.</b></p>', p(LOREM),
               '<p><b>ITEM 8. Financial Statements.</b></p>')
    r = parse_document(doc, "10-K")["10K_1A"]
    assert r.outcome == "ok", r.reasons
    assert "(Continued)" not in r.text
    assert len(r.text) > 9000


def test_sentence_split_by_page_break_is_rejoined():
    pages = [page(5, '<p id="rf"><b>Item 1A. Risk Factors</b></p>', p(LOREM[:3000] + "the supply of"))]
    pages += [page(6, p("components could be interrupted. " + LOREM[:3000]))]
    doc = html(toc(("Item 1A.", "Risk Factors", "5", "rf")), brk(), *pages,
               "<p>Item 1B. Unresolved Staff Comments</p>", "<p>Item 7. Management’s Discussion</p>", p(LOREM),
               "<p>Item 8. Financial Statements</p>")
    r = parse_document(doc, "10-K")["10K_1A"]
    assert "the supply of components could be interrupted." in r.text
    assert r.evidence["joins"] == 1


def test_toc_lines_are_never_section_starts():
    r = parse_document(tenk(), "10-K")["10K_1A"]
    assert r.evidence["heading_candidates"] == [r.start_block]       # the linked TOC row was not a candidate


# --- archetype B: pointer stub followed by running-header extent ---------------------------------------------------

def test_pointer_stub_is_followed_and_verified_against_stated_pages():
    """JPM: Item 7 says 'appears on pages 46-48'; the MD&A is the run of pages headed with its title."""
    stub = ("Management’s discussion and analysis of financial condition and results of operations, entitled "
            "“Management’s discussion and analysis,” appears on pages 46–48.")
    body = [page(45, p("Five-year stock performance"), p(LOREM[:400]))]
    body += [page(n, p(LOREM[:2500]), header="Management’s discussion and analysis") for n in (46, 47, 48)]
    body += [page(49, p("Management’s report on internal control over financial reporting"), p(LOREM[:400]))]
    doc = html(toc(("Item 1A.", "Risk Factors", "9", "rf"), ("Item 7.", "MD&A", "33", "m")), brk(),
               '<p id="rf">Item 1A. Risk Factors.</p>', p(LOREM),
               "<p>Item 2. Properties.</p>", p("Offices."),
               '<p id="m">Item 7. Management’s Discussion and Analysis of Financial Condition.</p>', p(stub),
               "<p>Item 7A. Quantitative and Qualitative Disclosures About Market Risk.</p>", p("Refer to MD&A."),
               "<p>Item 8. Financial Statements and Supplementary Data.</p>", p("See pages 50-90."), brk(),
               *body)
    r = parse_document(doc, "10-K")["10K_7"]
    assert r.outcome == "ok", r.reasons
    assert {"followed_pointer", "running_header_extent", "page_range_verified"} <= set(r.reasons)
    assert r.evidence["observed_pages"] == [46, 48]
    assert "internal control" not in r.text and "Five-year" not in r.text


def test_exhibit_incorporation_fails_honestly():
    """Pfizer FY2018-19: MD&A incorporated from the annual Financial Report exhibit; never fetched silently."""
    stub = p("Information required by this item is incorporated by reference from the discussion under the heading "
             "Financial Review in our 2018 Financial Report.")
    r = parse_document(tenk(mda=stub), "10-K")["10K_7"]
    assert (r.outcome, r.form_kind) == ("failed", "pointer")
    assert "exhibit_incorporation" in r.reasons


# --- 10-Q: parts, pointer-out (D), absent ----------------------------------------------------------------------------

def tenq(p2_items: list[str], risk_text: str | None = None) -> bytes:
    parts = ["<p>PART I. FINANCIAL INFORMATION</p>", "<p>Item 1. Financial Statements</p>", p(LOREM[:500]),
             "<p>Item 2. Management’s Discussion and Analysis of Financial Condition</p>", p(LOREM),
             "<p>Item 3. Quantitative and Qualitative Disclosures About Market Risk</p>", p("None."),
             "<p>Item 4. Controls and Procedures</p>", p("Effective."),
             "<p>PART II. OTHER INFORMATION</p>"]
    titles = {"1": "Legal Proceedings", "1A": "Risk Factors", "2": "Unregistered Sales of Equity Securities",
              "5": "Other Information", "6": "Exhibits"}
    for it in p2_items:
        parts += [f"<p>Item {it}. {titles[it]}</p>", p(risk_text if it == "1A" and risk_text else "Nothing to report.")]
    return html(*parts)


def test_10q_part_ii_item_2_is_not_mistaken_for_mda():
    res = parse_document(tenq(["1", "1A", "2", "6"], risk_text=LOREM[:3000]), "10-Q")
    assert res["10Q_P1_2"].outcome == "ok"
    assert res["10Q_P1_2"].text.startswith("The company faces risks")
    assert "Unregistered" not in res["10Q_P1_2"].text


def test_10q_pointer_out_to_the_10k():
    stub = ("In addition to the other information set forth in this report, you should carefully consider the factors"
            " discussed in Part I, Item 1A of our Annual Report on Form 10-K for the year ended December 31, 2025.")
    r = parse_document(tenq(["1", "1A", "2", "6"], risk_text=stub), "10-Q")["10Q_P2_1A"]
    assert (r.outcome, r.form_kind) == ("ok", "pointer")
    assert r.text == stub


def test_10q_without_part_ii_item_1a_is_absent_not_failed():
    """Exxon / Ford: Part II jumps from Item 1 to Item 2. Verified omission, counted separately from success."""
    r = parse_document(tenq(["1", "2", "5", "6"]), "10-Q")["10Q_P2_1A"]
    assert (r.outcome, r.form_kind) == ("ok", "absent")
    assert r.reasons == ["item_omitted"]


def test_running_header_item_heading_counts_once():
    """Berkshire 10-Q: 'Item 2. Management's Discussion…' is printed atop every MD&A page; the first is the heading."""
    head = "Item 2. Management’s Discussion and Analysis of Financial Condition and Results of Operations"
    pages = [page(n, p(LOREM[:2000]), header=head) for n in (20, 21, 22, 23)]
    doc = html("<p>PART I</p>", "<p>Item 1. Financial Statements</p>", p(LOREM[:500]), brk(), *pages,
               "<p>Item 3. Quantitative and Qualitative Disclosures About Market Risk</p>", p("None."),
               "<p>PART II</p>", "<p>Item 1. Legal Proceedings</p>", p("None."), "<p>Item 6. Exhibits</p>")
    r = parse_document(doc, "10-Q")["10Q_P1_2"]
    assert r.outcome == "ok", r.reasons
    assert r.text.count("The company faces risks") >= 4 and head not in r.text


# --- archetype C: cross-reference index (GE) -----------------------------------------------------------------------

def ge_like(indent_subsections: bool = True) -> bytes:
    sub = ' style="padding-left:9pt"' if indent_subsections else ""
    toc_rows = (
        '<table>'
        '<tr><td><a href="#mda">Management’s Discussion and Analysis of Financial Condition and Results of Operations'
        '</a></td><td><a href="#mda">4</a></td></tr>'
        f'<tr><td{sub}><a href="#seg">Segment Operations</a></td><td><a href="#seg">5</a></td></tr>'
        '<tr><td><a href="#rf">Risk Factors</a></td><td><a href="#rf">7</a></td></tr>'
        '<tr><td><a href="#lp">Legal Proceedings</a></td><td><a href="#lp">9</a></td></tr>'
        '<tr><td><a href="#xr">Form 10-K Cross Reference Index</a></td><td><a href="#xr">10</a></td></tr>'
        '</table>')
    footer = lambda n: f"2025 FORM 10-K {n}"  # noqa: E731
    pages = [
        p("TABLE OF CONTENTS") + toc_rows + p(footer(3)) + brk(),
        f'<p id="mda">MANAGEMENT’S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS. '
        f'{LOREM[:2000]}</p>' + p(footer(4)) + brk(),
        f'<p id="seg">SEGMENT OPERATIONS. {LOREM[:2000]}</p>' + p(footer(5)) + brk(),
        p(LOREM[:2000]) + p(footer(6)) + brk(),
        f'<p id="rf">RISK FACTORS. {LOREM[:3000]}</p>' + p(footer(7)) + brk(),
        p(LOREM[:3000]) + p(footer(8)) + brk(),
        f'<p id="lp">LEGAL PROCEEDINGS. See Note 20.</p>' + p(footer(9)) + brk(),
        '<p id="xr">FORM 10-K CROSS REFERENCE INDEX</p><table>'
        "<tr><td>Part I</td></tr>"
        "<tr><td>Item 1A.</td><td>Risk Factors</td><td>7-8</td></tr>"
        "<tr><td>Item 1B.</td><td>Unresolved Staff Comments</td><td>Not applicable</td></tr>"
        "<tr><td>Part II</td></tr>"
        "<tr><td>Item 7.</td><td>Management’s Discussion and Analysis of Financial Condition</td><td>4-6</td></tr>"
        "</table>" + p(footer(10)),
    ]
    return html(*pages)


def test_cross_reference_index_layout():
    res = parse_document(ge_like(), "10-K")
    rf, mda = res["10K_1A"], res["10K_7"]
    assert rf.outcome == "ok" and mda.outcome == "ok", (rf.reasons, mda.reasons)
    assert {"anchor_only", "xref_index", "run_in_heading", "page_range_verified"} <= set(mda.reasons)
    assert mda.evidence["observed_pages"] == [4, 6]               # indented subsection kept inside the MD&A
    assert rf.evidence["observed_pages"] == [7, 8]
    assert rf.text.startswith("RISK FACTORS. The company")          # run-in heading paragraph kept
    assert "LEGAL PROCEEDINGS" not in rf.text


def test_toc_link_to_the_index_is_not_the_index():
    """Regression: GE's front-TOC *link* 'Form 10-K Cross Reference Index' was taken as the index itself, hiding
    every heading after it."""
    res = parse_document(ge_like(), "10-K")
    assert res["10K_1A"].evidence["anchor_targets"]                 # anchors before the real index still count


# --- determinism ------------------------------------------------------------------------------------------------------

def test_same_bytes_same_results():
    raw = ge_like()
    a, b = parse_document(raw, "10-K"), parse_document(raw, "10-K")
    for s in a:
        assert (a[s].text, a[s].outcome, a[s].reasons, a[s].start_block, a[s].end_block) == \
               (b[s].text, b[s].outcome, b[s].reasons, b[s].start_block, b[s].end_block)
