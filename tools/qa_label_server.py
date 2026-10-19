"""Serve the QA labeling pages on this computer and save labels into data/qa/ (M6).

    python tools/qa_label_server.py          # then open http://127.0.0.1:8765/ in your browser

The page is the same one built by tools/build_qa_label_app.py. Opened from here it saves each label with a POST to
this server instead of the claude.ai viewer's store, so nothing between the browser and the page can interfere.
Labels land in data/qa/labels-<collection>.json, written atomically on every save. Listens on 127.0.0.1 only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {"/": "qa-labeler.html", "/labeler": "qa-labeler.html", "/practice": "qa-practice.html"}
OUT = ROOT / "data" / "qa"
PORT = 8765


def store(collection: str) -> Path:
    return OUT / f"labels-{collection}.json"


def read(collection: str) -> dict:
    p = store(collection)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in PAGES:
            self._send(200, (ROOT / "data" / "labeling" / PAGES[self.path]).read_bytes(), "text/html; charset=utf-8")
        elif m := re.fullmatch(r"/labels/(\w+)", self.path):
            self._send(200, json.dumps(read(m.group(1))).encode(), "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        m = re.fullmatch(r"/labels/(\w+)/([A-Za-z0-9]+)", self.path)
        if not m:
            return self._send(404, b"not found", "text/plain")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        coll, ident = m.groups()
        data = read(coll)
        data[ident] = body
        OUT.mkdir(parents=True, exist_ok=True)
        tmp = store(coll).with_suffix(".part")
        tmp.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, store(coll))
        self._send(200, b"{}", "application/json")

    def log_message(self, fmt: str, *args) -> None:
        if "POST" in (args[0] if args else ""):
            sys.stdout.write("saved " + args[0].split()[1] + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Labeling pages: http://127.0.0.1:{PORT}/practice  and  http://127.0.0.1:{PORT}/  (Ctrl+C to stop)",
          flush=True)
    srv.serve_forever()
