"""The read view (M8, FD-DEC 036): browse what changed between filings, and the recorded grounded answers.

    filing-delta serve            # http://127.0.0.1:8000

Server-rendered HTML over the files the reports already read (data/diffs, data/sections, data/classify,
data/qa, tests/golden): no database, no JavaScript. Every value is HTML-escaped. With ANTHROPIC_API_KEY set, /ask
answers a new question through the frozen QA pipeline. Without it, the page says so and nothing calls a model.

What the page may say is bounded by pins 5 and 6 and FD-DEC 016: it reports what filings say and how the text
changed, marks Item 1A and Item 7 as management's unaudited narrative, and never offers advice or a forecast.
"""
from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from html import escape
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import HTMLResponse

from ..diff.display import diff_segments
from ..qa.prompt import SECTION_LABEL

SEC_LABEL = {"10K_1A": "10-K Item 1A · Risk Factors", "10K_7": "10-K Item 7 · MD&A",
             "10Q_P1_2": "10-Q Part I Item 2 · MD&A", "10Q_P2_1A": "10-Q Part II Item 1A · Risk Factors"}
COVERAGE = ("10-K Item 1A and Item 7 for fiscal years 2018–2025, and 10-Q Part I Item 2 and Part II Item 1A filed "
            "January 2025 to September 2026, for 11 companies")
LIMITS = ("filing-delta reports what SEC filings say and how their text changed. Item 1A (Risk Factors) and Item 7 "
          "(MD&A) are management's unaudited narrative. \"Material\" is a labeled text-change category, not a legal "
          "or accounting judgment. Nothing here is investment advice or a forecast.")

CSS = """
:root { --paper: #f6f5f1; --sheet: #ffffff; --ink: #1c2027; --muted: #5b6370; --rule: #dcd9d1; --link: #1f4fa3;
  --del: #a3322a; --del-bg: #f6e3e0; --ins: #1f4fa3; --ins-bg: #e2eaf8; --mat: #a3322a; --cos: #2f6b4f; --uns: #8a6a1f;
  --mark: #fbeeb8; --mark-ink: #1c2027;
  --serif: "Source Serif 4", Georgia, serif; --sans: "IBM Plex Sans", "Segoe UI", Arial, sans-serif;
  --mono: "IBM Plex Mono", Consolas, monospace }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --paper: #15171b; --sheet: #1d2025;
  --ink: #e6e4de; --muted: #a2a7b0; --rule: #33373e; --link: #8fb2ee; --del: #ec8f86; --del-bg: #3a2220;
  --ins: #8fb2ee; --ins-bg: #1f2a3d; --mat: #ec8f86; --cos: #7fc6a2; --uns: #d9b75e; --mark: #5a4a12;
  --mark-ink: #f4ecd0; color-scheme: dark } }
:root[data-theme="dark"] { --paper: #15171b; --sheet: #1d2025; --ink: #e6e4de; --muted: #a2a7b0; --rule: #33373e;
  --link: #8fb2ee; --del: #ec8f86; --del-bg: #3a2220; --ins: #8fb2ee; --ins-bg: #1f2a3d; --mat: #ec8f86;
  --cos: #7fc6a2; --uns: #d9b75e; --mark: #5a4a12; --mark-ink: #f4ecd0; color-scheme: dark }
* { box-sizing: border-box }
body { margin: 0; background: var(--paper); color: var(--ink); font: 15px/1.55 var(--sans);
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 0 40px }
.wrap { max-width: 980px; margin: 0 auto; display: grid; gap: 16px }
header { border-bottom: 1px solid var(--rule); padding-block: 16px 10px; display: flex; flex-wrap: wrap; gap: 8px 20px;
  align-items: baseline; justify-content: space-between }
header .brand { font-family: var(--serif); font-weight: 600; font-size: 1.3rem; color: var(--ink); text-decoration: none }
nav { display: flex; gap: 16px; font-size: .92rem }
a { color: var(--link) }
h1 { font-family: var(--serif); font-weight: 600; font-size: 1.5rem; margin: 6px 0 0; text-wrap: balance }
h2 { font-family: var(--serif); font-weight: 600; font-size: 1.15rem; margin: 10px 0 0 }
.muted { color: var(--muted) } .small { font-size: .85rem }
.limits { font-size: .82rem; color: var(--muted); border-top: 1px solid var(--rule); padding-top: 10px }
.tbl { overflow-x: auto }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: .92rem }
th, td { text-align: left; padding: 6px 10px 6px 0; border-bottom: 1px solid var(--rule); vertical-align: top }
th { font: 500 .72rem var(--mono); letter-spacing: .06em; text-transform: uppercase; color: var(--muted) }
.card { background: var(--sheet); border: 1px solid var(--rule); border-radius: 6px; padding: 14px 16px; display: grid;
  gap: 8px; min-width: 0 }
.text { font-family: var(--serif); font-size: 1rem; line-height: 1.65; overflow-wrap: anywhere; max-width: 72ch }
del { color: var(--del); background: var(--del-bg) } ins { color: var(--ins); background: var(--ins-bg); text-decoration: none;
  border-bottom: 2px solid var(--ins) }
.gap { font: .75rem var(--mono); color: var(--muted) }
.ctx { white-space: pre-line }
mark { background: var(--mark); color: var(--mark-ink) }
.chips { display: flex; flex-wrap: wrap; gap: 6px; align-items: baseline }
.chip { font: 500 .72rem var(--mono); letter-spacing: .05em; text-transform: uppercase; padding: 1px 8px;
  border: 1px solid var(--rule); border-radius: 999px }
.chip.material { border-color: var(--mat); color: var(--mat) } .chip.cosmetic { border-color: var(--cos); color: var(--cos) }
.chip.unsure { border-color: var(--uns); color: var(--uns) }
.why { font-size: .9rem; color: var(--muted) }
form.ask { display: flex; flex-wrap: wrap; gap: 8px } form.ask input { flex: 1 1 320px; min-width: 0; padding: 8px 10px;
  font: inherit; border: 1px solid var(--rule); border-radius: 6px; background: var(--sheet); color: var(--ink) }
button { font: inherit; padding: 8px 14px; border: 1px solid var(--rule); border-radius: 6px; background: var(--sheet);
  color: var(--ink); cursor: pointer }
a:focus-visible, button:focus-visible, input:focus-visible { outline: 2px solid var(--link); outline-offset: 2px }
"""


def page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · filing-delta</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}</style></head><body><div class="wrap">
<header><a class="brand" href="/">filing-delta</a><nav><a href="/">Companies</a><a href="/questions">Questions</a>
<a href="/ask">Ask</a></nav></header>
{body}
<p class="limits">{escape(LIMITS)} Coverage: {escape(COVERAGE)}.</p>
</div></body></html>""")


def create_app(root: Path) -> FastAPI:
    app = FastAPI(title="filing-delta", docs_url=None, redoc_url=None)

    @lru_cache(maxsize=None)
    def manifest() -> dict[str, dict]:
        with (root / "corpus" / "manifest.csv").open(encoding="utf-8") as f:
            return {r["accession"]: r for r in csv.DictReader(f)}

    @lru_cache(maxsize=None)
    def diffs() -> list[dict]:
        out = []
        for p in sorted((root / "data" / "diffs").glob("*.json")):
            r = json.loads(p.read_text(encoding="utf-8"))
            out.append({"stem": p.stem, "cik": r["cik"], "company": r["company"], "section": r["section"],
                        "old": r["old"], "new": r["new"], "state": r["state"], "counts": r.get("counts", {})})
        return out

    @lru_cache(maxsize=None)
    def labels() -> dict[str, dict]:
        p = root / "data" / "classify" / "corpus-claude-sonnet-5-5.jsonl"
        return {json.loads(l)["id"]: json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()} if p.exists() else {}

    @lru_cache(maxsize=256)
    def section_text(acc: str, sec: str) -> str:
        return (root / "data" / "sections" / acc / f"{sec}.txt").read_text(encoding="utf-8")

    @lru_cache(maxsize=None)
    def qa() -> tuple[dict, dict, dict]:
        g = root / "tests" / "golden"
        qs = {q["id"]: q for q in json.loads((g / "qa_questions.json").read_text(encoding="utf-8"))["questions"]}
        key = {k["id"]: k for k in json.loads((g / "qa_key.json").read_text(encoding="utf-8"))["key"]}
        runp = root / "data" / "qa" / "run.jsonl"
        run = {json.loads(l)["id"]: json.loads(l) for l in runp.read_text(encoding="utf-8").splitlines()} \
            if runp.exists() else {}
        return qs, key, run

    def sec_link(acc: str, text: str) -> str:
        m = manifest().get(acc)
        return f'<a href="{escape(m["url"])}" rel="noopener" target="_blank">{escape(text)}</a>' if m else escape(text)

    @app.get("/", response_class=HTMLResponse)
    def home():
        by_co: dict[int, dict] = {}
        for d in diffs():
            c = by_co.setdefault(d["cik"], {"company": d["company"], "pairs": 0, "filings": set()})
            c["pairs"] += d["state"] == "full -> full"
            c["filings"].update([d["old"]["accession"], d["new"]["accession"]])
        rows = "".join(f'<tr><td><a href="/company/{cik}">{escape(c["company"])}</a></td><td>{len(c["filings"])}</td>'
                       f'<td>{c["pairs"]}</td></tr>' for cik, c in sorted(by_co.items(), key=lambda x: x[1]["company"].lower()))
        n_mat = sum(1 for l in labels().values() if l.get("outcome") == "ok" and l.get("label") == "material")
        return page("What changed", f"""<h1>What a company newly disclosed, dropped, or reworded</h1>
<p class="text">Each 10-K section is compared with the same section of the prior year's 10-K, and each 10-Q with the
same quarter a year earlier, paragraph by paragraph. The comparison is deterministic and uses no model. Risk-factor
changes carry a material or cosmetic label from a classifier scored against hand labels ({n_mat:,} labeled material
across the corpus). Every change links to its exact text in the filing.</p>
<div class="tbl"><table><tr><th>Company</th><th>Filings</th><th>Compared pairs</th></tr>{rows}</table></div>
<p class="small muted">Also: <a href="/questions">60 recorded questions</a> answered with exact citations or a refusal.</p>""")

    @app.get("/company/{cik}", response_class=HTMLResponse)
    def company(cik: int):
        ds = [d for d in diffs() if d["cik"] == cik]
        if not ds:
            raise HTTPException(404, "No filings for that company in this corpus.")
        rows = []
        for d in sorted(ds, key=lambda d: (d["section"], d["new"]["report_date"]), reverse=False):
            c = d["counts"]
            changed = sum(v for k, v in c.items() if k != "unchanged")
            mat = sum(1 for k, l in labels().items() if k.startswith(d["stem"] + "#") and l.get("label") == "material"
                      and l.get("outcome") == "ok")
            link = f'<a href="/pair/{escape(d["stem"])}">{escape(d["old"]["report_date"])} → {escape(d["new"]["report_date"])}</a>' \
                if d["state"] == "full -> full" else escape(f'{d["old"]["report_date"]} → {d["new"]["report_date"]}')
            rows.append(f'<tr><td>{escape(SEC_LABEL[d["section"]])}</td><td>{link}</td>'
                        f'<td>{changed if d["state"] == "full -> full" else escape(d["state"])}</td>'
                        f'<td>{mat if d["section"] in ("10K_1A", "10Q_P2_1A") else "–"}</td></tr>')
        return page(ds[0]["company"], f"""<h1>{escape(ds[0]["company"])}</h1>
<div class="tbl"><table><tr><th>Section</th><th>Compared periods</th><th>Changes</th><th>Labeled material</th></tr>
{''.join(rows)}</table></div>
<p class="small muted">A pair that isn't full text on both sides (a 10-Q that refers its risk factors back to the
10-K, say) shows its state instead of a comparison.</p>""")

    @app.get("/pair/{stem}", response_class=HTMLResponse)
    def pair(stem: str, material: int = Query(0)):
        p = root / "data" / "diffs" / f"{stem}.json"
        if "/" in stem or "\\" in stem or not p.exists():
            raise HTTPException(404, "No such comparison.")
        r = json.loads(p.read_text(encoding="utf-8"))
        if r["state"] != "full -> full":
            raise HTTPException(404, "This pair isn't full text on both sides.")
        to, tn = section_text(r["old"]["accession"], r["section"]), section_text(r["new"]["accession"], r["section"])
        cards = []
        for k, op in enumerate(r["ops"]):
            st = op["status"]
            if st == "unchanged" or (st == "moved" and not op.get("facts", {}).get("edited")):
                continue
            lab = labels().get(f"{stem}#{k}")
            if material and not (lab and lab.get("outcome") == "ok" and lab.get("label") == "material"):
                continue
            old = "\n\n".join(to[r["old_units"][i][1]:r["old_units"][i][2]] for i in op["old"])
            new = "\n\n".join(tn[r["new_units"][j][1]:r["new_units"][j][2]] for j in op["new"])
            if st in ("reworded", "moved"):
                body = " ".join(f"<{'del' if t == 'del' else 'ins'}>{escape(s)}</{'del' if t == 'del' else 'ins'}>"
                                if t in ("del", "ins") else f'<span class="gap">… {escape(s)} …</span>' if t == "gap"
                                else escape(s) for t, s in diff_segments(old, new))
            elif st == "added":
                body = f"<ins>{escape(new)}</ins>"
            elif st == "removed":
                body = f"<del>{escape(old)}</del>"
            else:
                body = f'<del>{escape(old)}</del><br><br><ins>{escape(new)}</ins>'
            span = []
            if op["old"]:
                span.append(f'old chars {r["old_units"][op["old"][0]][1]:,}–{r["old_units"][op["old"][-1]][2]:,}')
            if op["new"]:
                span.append(f'new chars {r["new_units"][op["new"][0]][1]:,}–{r["new_units"][op["new"][-1]][2]:,}')
            chips = f'<span class="chip">{escape(st)}</span>'
            why = ""
            if lab and lab.get("outcome") == "ok":
                chips += f'<span class="chip {escape(lab["label"])}">{escape(lab["label"])}</span>' \
                         f'<span class="chip">{escape(lab.get("code") or "")}</span>'
                why = f'<div class="why">{escape(lab.get("rationale") or "")}' + \
                      (f' Evidence: “{escape(lab["evidence"])}”' if lab.get("evidence") else "") + \
                      (" (rule: case or punctuation only)" if lab.get("source") == "rule" else "") + "</div>"
            elif lab:
                chips += f'<span class="chip">label {escape(lab.get("outcome") or "")}</span>'
            cards.append(f'<div class="card"><div class="chips">{chips}<span class="small muted">{escape("; ".join(span))}'
                         f'</span></div><div class="text">{body}</div>{why}</div>')
        is_risk = r["section"] in ("10K_1A", "10Q_P2_1A")
        toggle = (f'<a href="/pair/{escape(stem)}">Show all changes</a>' if material else
                  f'<a href="/pair/{escape(stem)}?material=1">Show only changes labeled material</a>') if is_risk else ""
        return page(f'{r["company"]} {SEC_LABEL[r["section"]]}', f"""<p class="small"><a href="/company/{r['cik']}">{escape(r['company'])}</a></p>
<h1>{escape(SEC_LABEL[r['section']])}: {escape(r['old']['report_date'])} → {escape(r['new']['report_date'])}</h1>
<p class="small muted">Old: {sec_link(r['old']['accession'], r['old']['accession'])} · New:
{sec_link(r['new']['accession'], r['new']['accession'])} · {len(cards)} change(s) shown. {toggle}</p>
<p class="small muted">Deleted words are struck through, inserted words underlined; long unchanged stretches are
collapsed. Labels on risk-factor changes come from the classifier (claude-sonnet-5-5, prompt frozen at 1fd1c7e5bb42),
scored against blind hand labels: precision 0.89, recall 0.80 for "material" (docs/materiality-eval-test.md).</p>
{''.join(cards) or '<p class="muted">No changes match.</p>'}""")

    def render_answer(t: dict, key: dict | None) -> str:
        r = t["result"]
        if r["type"] == "abstain":
            guard = ('<div class="why">Withheld by rule: the question asks for a figure, and an answer that the '
                     'filing doesn\'t state it would not answer it (FD-DEC 038).</div>') \
                if t.get("stage") == "absence_guard" else ""
            out = f'<div class="card"><div class="chips"><span class="chip">abstained</span></div>' \
                  f'<div class="text">{escape(r["reason"])}</div>{guard}</div>'
        else:
            cites = []
            for c in r["citations"]:
                text = section_text(c["accession"], c["section"])
                a, b = max(0, c["start"] - 300), min(len(text), c["end"] + 300)
                ctx = escape(text[a:c["start"]]) + "<mark>" + escape(text[c["start"]:c["end"]]) + "</mark>" + \
                    escape(text[c["end"]:b])
                m = manifest().get(c["accession"], {})
                cites.append(f'<div class="card"><div class="small">{sec_link(c["accession"], (m.get("company") or "") + " " + (m.get("form") or "") + " " + (m.get("report_date") or ""))}'
                             f' · {escape(SECTION_LABEL[c["section"]])} · chars {c["start"]:,}–{c["end"]:,}</div>'
                             + (f'<div class="why">Supports: {escape(c["claim"])}</div>' if c.get("claim") else "")
                             + f'<div class="text ctx">…{ctx}…</div></div>')
            absent = ""
            if (t.get("raw") or {}).get("absence"):
                sp = t.get("second_pass") or {}
                tried = ", ".join(sp.get("search_terms") or []) or ", ".join(sp.get("missed_terms") or [])
                absent = ('<div class="why">This answer says the passages searched don\'t state something. Before '
                          'answering, the tool searched again for other wording'
                          + (f' ({escape(tried)})' if tried else '') +
                          '. A search can still miss text phrased differently, so treat "doesn\'t say" as '
                          '"wasn\'t found", not proof of absence.</div>')
            out = f'<div class="card"><div class="chips"><span class="chip">answer</span>' + \
                  ('<span class="chip unsure">says something isn\'t there</span>' if absent else '') + \
                  f'</div><div class="text">{escape(r["text"])}</div>{absent}' + \
                  (f'<div class="small muted">{escape(t.get("provenance") or "")}</div>' if t.get("provenance") else "") + \
                  f'</div><h2>Citations ({len(r["citations"])}), each an exact span of the filing</h2>{"".join(cites)}'
        if key:
            out += f'<p class="small muted">Answer key: {escape(key["state"].replace("_", " "))} ' \
                   f'({escape(key["provenance"])}; the key is model-built, FD-DEC 031).</p>'
        return out

    @app.get("/questions", response_class=HTMLResponse)
    def questions():
        qs, key, run = qa()
        rows = "".join(f'<tr><td><a href="/questions/{qid}">{qid}</a></td><td>{escape(q["question"])}</td>'
                       f'<td>{escape(run[qid]["result"]["type"]) if qid in run else "–"}</td>'
                       f'<td>{escape(key[qid]["state"].replace("_", " "))}</td></tr>' for qid, q in sorted(qs.items()))
        return page("Questions", f"""<h1>60 questions, answered with exact citations or refused</h1>
<p class="text">The recorded run of the frozen pipeline. Every answer cites spans whose text is checked character for
character against the stored filing section; if a check fails, the answer is withheld. Requests for advice or
predictions, and questions outside the corpus, are refused.</p>
<div class="tbl"><table><tr><th>ID</th><th>Question</th><th>System</th><th>Answer key</th></tr>{rows}</table></div>""")

    @app.get("/questions/{qid}", response_class=HTMLResponse)
    def question(qid: str):
        qs, key, run = qa()
        if qid not in qs or qid not in run:
            raise HTTPException(404, "No such recorded question.")
        return page(qid, f'<p class="small"><a href="/questions">All questions</a></p><h1>{escape(qs[qid]["question"])}</h1>'
                         + render_answer(run[qid], key.get(qid)))

    @app.get("/ask", response_class=HTMLResponse)
    def ask_form():
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return page("Ask", """<h1>Ask a question</h1><p class="text">Asking a new question calls a model, so it needs
ANTHROPIC_API_KEY set where the server runs. Without one, the <a href="/questions">60 recorded questions</a> show
exactly what the pipeline does: exact citations, or a refusal.</p>""")
        return page("Ask", """<h1>Ask a question</h1><form class="ask" method="post" action="/ask">
<input name="q" id="q" placeholder="e.g. What does Apple's 2024 10-K say about supply chain risks?" required>
<button type="submit">Ask</button></form><p class="small muted">Name the company and, ideally, the filing year.
Questions asking for advice or predictions are refused.</p>""")

    @app.post("/ask", response_class=HTMLResponse)
    def ask_post(q: str = Form(...)):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(403, "No API key configured on this server.")
        from ..classify.model import Recorder
        from ..qa.ask import ask
        from ..qa.guard import load_catalog as catalog
        t = ask(q[:500], root, catalog(root), Recorder(root / "data" / "model-cache"))
        return page("Answer", f'<p class="small"><a href="/ask">Ask another</a></p><h1>{escape(q[:500])}</h1>'
                              + render_answer(t, None))

    return app
