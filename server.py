"""
The Gift — host server.

One process serves the whole library with a real front door: a landing page
(counts computed from disk), browsable directory listings, and the files
themselves with honest MIME types. Python 3 stdlib only — no packages, no
build step. Binds 0.0.0.0 by default (override with GIFT_HOST) so LAN
visitors can reach it — e.g. the RNK box at 192.168.1.202.

  python3 server.py                 # serve on 0.0.0.0:8770
  GIFT_PORT=8080 python3 server.py  # different port

Dot-directories (.git, .claude, …) and the private model/ folder are never
served. Bulk/programmatic access should use git or rsync, not HTTP range
requests — there is no resume support by design.

  GET /                → landing page (library counts, links to browse)
  GET /<path>/         → browsable listing
  GET /<path>/<file>   → the file (text/* UTF-8 for readable formats)
"""

import html
import hashlib
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

PORT = int(os.environ.get("GIFT_PORT", "8770"))
HOST = os.environ.get("GIFT_HOST", "0.0.0.0")
ROOT = Path(__file__).resolve().parent

# never exposed over HTTP, whatever the request
HIDDEN = {".git", ".claude", ".freebuff", "model", "deploy", "__pycache__"}

READABLE_MIME = {
    ".txt": "text/plain; charset=utf-8",
    ".py": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".conf": "text/plain; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Gift — a free library</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #070b14; color: #e7f4f8;
         font: 17px/1.6 system-ui, sans-serif; }}
  main {{ max-width: 880px; margin: 0 auto; padding: clamp(28px, 6vw, 72px) 20px; }}
  .eyebrow {{ font-size: 12px; letter-spacing: .18em; text-transform: uppercase;
              color: #2ee6c8; margin: 0 0 10px; }}
  h1 {{ font-size: clamp(38px, 7vw, 64px); line-height: 1.05; margin: 0 0 14px; }}
  .lede {{ color: #8aa3b3; max-width: 56ch; margin: 0 0 40px; }}
  .doors {{ display: grid; gap: 14px; }}
  a.door {{ display: block; padding: 20px 22px; background: #0d1520;
            border: 1px solid rgba(231,244,248,.1); color: inherit;
            text-decoration: none; }}
  a.door:hover {{ border-color: rgba(46,230,200,.45); }}
  a.door h2 {{ margin: 0 0 6px; font-size: 22px; color: #e7f4f8; }}
  a.door p {{ margin: 0; color: #8aa3b3; font-size: 15px; }}
  .foot {{ margin-top: 44px; color: #8aa3b3; font-size: 14px; }}
  .foot a {{ color: #2ee6c8; }}
</style>
</head>
<body>
<main>
  <p class="eyebrow">RNK Studios · Open</p>
  <h1>The Gift</h1>
  <p class="lede">
    A personal library of free, public-domain and openly-licensed Bible
    translations and study resources, pulled together from established
    open-data projects. Nothing paywalled, DRM'd, or account-gated.
  </p>

  <div class="doors">
    <a class="door" href="/Bibles/formats/text/">
      <h2>Bibles — plain text · {text_count} translations</h2>
      <p>One UTF-8 .txt per translation, across ~50 languages. Start with
         AKJV, ASV, Webster — the full list is the listing itself.</p>
    </a>
    <a class="door" href="/Bibles/formats/python/">
      <h2>Bibles — by book &amp; language · {python_dirs} folders</h2>
      <p>The same texts organised per book and per language — {python_files}
         files, useful for scripting and programmatic reading.</p>
    </a>
    <a class="door" href="/Bibles/formats/correlate/">
      <h2>Bibles — correlate data</h2>
      <p>Cross-reference / alignment data accompanying the translations.</p>
    </a>
    <a class="door" href="/Study%20Guides/">
      <h2>Study Guides · {sword_count} SWORD modules</h2>
      <p>Classic public-domain commentaries and reference works (Matthew
         Henry, JFB, Strong's, Nave's …) in the CrossWire SWORD format.</p>
    </a>
  </div>

  <p class="foot">
    Free to use — mostly public domain; a few modules carry their own
    per-file notes. See the <a href="/README.md">README</a> and
    <a href="/LICENSE">LICENSE</a>. Bulk access: use git or rsync, not HTTP.
  </p>
</main>
</body>
</html>
"""


def count_visible(d, predicate=lambda p: True):
    try:
        return sum(1 for e in os.scandir(d) if e.name not in HIDDEN and not e.name.startswith(".") and predicate(e))
    except OSError:
        return 0


def landing_page():
    text_count = count_visible(ROOT / "Bibles/formats/text", lambda e: e.name.endswith(".txt"))
    py_dir = ROOT / "Bibles/formats/python"
    python_dirs = count_visible(py_dir)
    python_files = _cached_py_files(py_dir)
    sword_count = count_visible(ROOT / "Study Guides/Commentaries and Reference/mods.d", lambda e: e.name.endswith(".conf"))
    return PAGE.format(text_count=text_count, python_dirs=python_dirs,
                       python_files=f"{python_files:,}", sword_count=sword_count).encode("utf-8")


_py_files_cache = None


def _cached_py_files(d):
    """Recursive .py count — the library is static while serving, so compute once."""
    global _py_files_cache
    if _py_files_cache is None:
        n = 0
        for base, dirs, files in os.walk(d):
            dirs[:] = [x for x in dirs if x not in HIDDEN and not x.startswith(".")]
            n += sum(1 for f in files if f.endswith(".py"))
        _py_files_cache = n
    return _py_files_cache


class Handler(BaseHTTPRequestHandler):
    server_version = "TheGift/1.0"  # sys_version (Python version) is not advertised

    timeout = 60  # drop stuck connections instead of pinning a thread forever

    def version_string(self):
        return self.server_version

    def _send(self, code, body, content_type, cache_control=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if cache_control:
            self.send_header("Cache-Control", cache_control)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _not_found(self):
        self._send(404, b'{"error": "not found"}', "application/json; charset=utf-8")

    def do_GET(self):
        self._handle()

    def do_HEAD(self):
        self._handle()

    def _handle(self):
        if self.command not in ("GET", "HEAD"):
            return self._not_found()
        # keep the encoded form for redirects, decode for the filesystem
        raw_path, _, query = self.path.partition("?")
        raw_path = raw_path.split("#", 1)[0]
        path = unquote(raw_path)
        if path == "/" or path == "/index.html":
            return self._send(200, landing_page(), "text/html; charset=utf-8",
                              cache_control="no-cache")
        if path == "/healthz":
            return self._send(200, b'{"ok": true}\n', "application/json; charset=utf-8",
                              cache_control="no-store")

        try:
            candidate = (ROOT / os.path.normpath(path.lstrip("/"))).resolve()
        except (ValueError, OSError):
            return self._not_found()
        if not str(candidate).startswith(str(ROOT) + os.sep) and candidate != ROOT:
            return self._not_found()  # traversal guard
        if candidate.is_file():
            return self._send_file(candidate)
        if candidate.is_dir():
            parts = [p for p in path.split("/") if p]
            rel = Path(*parts) if parts else Path()
            if any(part in HIDDEN or part.startswith(".") for part in parts):
                return self._not_found()
            if not raw_path.endswith("/"):
                # canonicalise directories to a trailing slash so relative links work
                self.send_response(301)
                self.send_header("Location", raw_path + "/" + ("?" + query if query else ""))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            return self._send_listing(candidate, rel)
        return self._not_found()

    @staticmethod
    def _etag(data):
        return '"' + hashlib.md5(data).hexdigest() + '"'

    def _send_file(self, candidate):
        if any(part in HIDDEN or part.startswith(".") for part in candidate.relative_to(ROOT).parts):
            return self._not_found()
        try:
            body = candidate.read_bytes()
        except OSError:
            return self._not_found()
        ctype = READABLE_MIME.get(candidate.suffix.lower()) \
            or mimetypes.guess_type(str(candidate))[0] \
            or "application/octet-stream"
        etag = self._etag(body)
        cache_control = "public, max-age=604800"  # library files are static; a week bounds staleness
        if etag in {t.strip() for t in self.headers.get("If-None-Match", "").split(",")}:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", cache_control)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", cache_control)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_listing(self, d, rel):
        try:
            entries = [e for e in os.scandir(d) if e.name not in HIDDEN and not e.name.startswith(".")]
        except OSError:
            return self._not_found()
        dirs = sorted((e for e in entries if e.is_dir()), key=lambda e: e.name.lower())
        files = sorted((e for e in entries if not e.is_dir()), key=lambda e: e.name.lower())

        def href_for(e):
            name = html.escape(e.name, quote=True)
            return f"{name}/" if e.is_dir() else name

        crumbs = '<a href="/">The Gift</a>'
        acc = ""
        for part in rel.parts:
            acc += "/" + html.escape(part, quote=True)
            crumbs += f' / <a href="{acc}/">{html.escape(part)}</a>'

        rows = ""
        for e in dirs:
            size = "—"
            rows += f'<tr><td><a href="{href_for(e)}">{html.escape(e.name)}/</a></td><td class="s">{size}</td></tr>'
        for e in files:
            try:
                size = f"{e.stat().st_size / 1_048_576:.1f} MB"
            except OSError:
                size = "—"
            rows += f'<tr><td><a href="{href_for(e)}">{html.escape(e.name)}</a></td><td class="s">{size}</td></tr>'

        body = LISTING.format(title=html.escape(str(rel) if str(rel) != "." else "browse"),
                              crumbs=crumbs, rows=rows).encode("utf-8")
        self._send(200, body, "text/html; charset=utf-8")

    def log_message(self, fmt, *args):
        pass  # a quiet public server


LISTING = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — The Gift</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; background: #070b14; color: #e7f4f8;
          font: 16px/1.5 ui-monospace, monospace; }}
  main {{ max-width: 880px; margin: 0 auto; padding: 32px 20px 64px; }}
  .crumbs a {{ color: #2ee6c8; text-decoration: none; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 18px; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid rgba(231,244,248,.08); }}
  td.s {{ text-align: right; color: #8aa3b3; white-space: nowrap; }}
  a {{ color: #e7f4f8; text-decoration: none; }}
  a:hover {{ color: #2ee6c8; }}
</style>
</head>
<body>
<main>
  <p class="crumbs">{crumbs}</p>
  <table>{rows}</table>
</main>
</body>
</html>
"""


if __name__ == "__main__":
    print(f"The Gift: serving {ROOT} on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
