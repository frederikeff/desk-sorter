#!/usr/bin/env python3
"""Serve a sort sheet on this Mac only:  python3 server.py <sheet-name> [port]   (default port 8791)

Open http://127.0.0.1:<port>. Choices are saved to data/<sheet-name>/choices.json.
It listens on 127.0.0.1 only, so nothing is reachable from other machines.
Only files listed in the sheet can be opened. Stop it with Ctrl-C, or by its port: lsof -ti tcp:8791 | xargs kill
"""
import json, os, re, sys, tempfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
SHEET = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8791
DATA = os.path.join(HERE, "data", SHEET)
ITEMS = json.load(open(os.path.join(DATA, "items.json"), encoding="utf-8"))
BY_ID = {i["id"]: i for i in ITEMS["items"]}
CHOICES = os.path.join(DATA, "choices.json")
TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
         ".svg": "image/svg+xml", ".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if ctype == "application/json" else "max-age=3600")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            return self.send(200, open(os.path.join(HERE, "sort.html"), "rb").read(), "text/html; charset=utf-8")
        if p == "/data":
            ch = json.load(open(CHOICES, encoding="utf-8")) if os.path.exists(CHOICES) else {}
            return self.send(200, json.dumps({**ITEMS, "choices": ch}).encode())
        m = re.fullmatch(r"/(thumb|file)/([0-9a-f]{16})", p)
        if not m or m.group(2) not in BY_ID:
            return self.send(404, b"{}")
        it = BY_ID[m.group(2)]
        if m.group(1) == "thumb":
            f = os.path.join(DATA, "thumbs", it["id"] + ".jpg")
            return self.send(200, open(f, "rb").read(), "image/jpeg") if os.path.exists(f) else self.send(404, b"{}")
        return self.file(it["path"], TYPES.get(os.path.splitext(it["path"])[1].lower(), "application/octet-stream"))

    def file(self, path, ctype):  # with Range, so videos can be scrubbed
        size = os.path.getsize(path)
        rng = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        start, end = 0, size - 1
        if rng:
            start = int(rng.group(1) or 0)
            end = min(int(rng.group(2)) if rng.group(2) else size - 1, size - 1)
        length = end - start + 1
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with open(path, "rb") as fh:
            fh.seek(start)
            left = length
            try:
                while left > 0:
                    chunk = fh.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_POST(self):
        if self.path != "/save":
            return self.send(404, b"{}")
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        clean = {k: v for k, v in body.items() if k in BY_ID or k == "_buckets"}
        fd, tmp = tempfile.mkstemp(dir=DATA)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(clean, fh, ensure_ascii=False, indent=0)
        os.replace(tmp, CHOICES)
        self.send(200, json.dumps({"saved": len(clean)}).encode())


print(f"sheet {SHEET}: {len(BY_ID)} files on http://127.0.0.1:{PORT}", flush=True)
ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
