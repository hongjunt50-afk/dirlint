"""Local-only HTTP server for the dirlint UI. Standard library, no dependencies."""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .core import load_config, scan

WEB_DIR = Path(__file__).parent / "web"
INDEX = WEB_DIR / "index.html"


class Handler(BaseHTTPRequestHandler):
    root: Path = Path(".")
    config: str | None = None

    def log_message(self, fmt, *args):  # quieter than the default
        pass

    def _send(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: dict):
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            try:
                self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
            except OSError:
                self._json(500, {"error": "index.html missing from the installation"})
            return
        if parsed.path == "/api/scan":
            params = parse_qs(parsed.query)
            root = Path(params.get("root", [str(self.root)])[0]).expanduser()
            if not root.is_dir():
                self._json(400, {"error": f"not a directory: {root}"})
                return
            cfg = load_config(self.config)
            if params.get("duplicates", ["0"])[0] in ("1", "true"):
                cfg["rules"]["duplicates"] = True
            try:
                result = scan(root, cfg)
            except Exception as exc:  # surface scan failures to the UI
                self._json(500, {"error": str(exc)})
                return
            self._json(200, result.to_dict())
            return
        if parsed.path == "/api/config":
            cfg = load_config(self.config)
            self._json(200, {"root": str(self.root), "config": cfg})
            return
        self._json(404, {"error": "not found"})


def serve(root: str, config: str | None, port: int, open_browser: bool = True):
    Handler.root = Path(root)
    Handler.config = config
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"dirlint UI  {url}")
    print(f"root        {Handler.root.resolve()}")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
