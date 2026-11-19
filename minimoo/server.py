"""Local dashboard: 127.0.0.1 only, token-gated writes."""
from __future__ import annotations
import html
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

class Handler(BaseHTTPRequestHandler):
    store = None
    infer = None
    token = ""

    def log_message(self, *a):
        pass

    def _ok(self, body: str, ctype="text/html; charset=utf-8"):
        b = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/state":
            return self._ok(json.dumps(self._state()), "application/json")
        jobs = self.store.list_jobs(limit=100)
        agents = self.store.list_agents()
        gpu = self.infer.status()
        rows = "".join(
            f"<tr><td>{html.escape(j['id'])}</td><td>{html.escape(j['mission_id'])}"
            f"</td><td>{html.escape(j['state'])}</td><td>{html.escape(j['agent'] or '')}"
            f"</td><td>{html.escape((j['title'] or '')[:80])}</td></tr>" for j in jobs)
        ags = "".join(
            f"<tr><td>{html.escape(a['name'])}</td><td>{html.escape(a['availability'])}"
            f"</td><td>{html.escape(a['current_job'] or '')}</td>"
            f"<td>{html.escape(a['quota_note'] or '')}</td></tr>" for a in agents)
        self._ok(f"""<html><head><title>Minimoo</title></head><body>
<h1>Minimoo 1.0 — local workshop worker</h1>
<h2>GPU</h2><pre>{html.escape(json.dumps(gpu, indent=2))}</pre>
<h2>Agents</h2><table border=1>{ags}</table>
<h2>Jobs (pending/active/blocked/review)</h2><table border=1>
<tr><th>id</th><th>mission</th><th>state</th><th>agent</th><th>title</th></tr>{rows}</table>
<p>Writes require MINIMOO_TOKEN via POST /api/*.</p></body></html>""")

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            args = json.loads(raw.decode() or "{}")
        except Exception:
            args = {}
        if self.token and args.get("token", "") != self.token:
            self.send_response(403)
            self.end_headers()
            return
        try:
            if u.path == "/api/pause":
                out = self.infer.pause(bool(args.get("on", True)))
            elif u.path == "/api/recover":
                out = self.store.recover_stale(actor="dashboard")
                out = {"recovered": len(out)}
            else:
                self.send_response(404)
                self.end_headers()
                return
            self._ok(json.dumps(out), "application/json")
        except Exception as e:
            self._ok(json.dumps({"error": str(e)}), "application/json")

    def _state(self):
        return {"jobs": self.store.list_jobs(limit=100), "agents": self.store.list_agents(),
                "gpu": self.infer.status()}

def serve(store, infer, host: str, port: int, token: str):
    Handler.store = store
    Handler.infer = infer
    Handler.token = token
    httpd = HTTPServer((host, port), Handler)
    return httpd
