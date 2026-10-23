#!/usr/bin/env python3
"""Local static preview with the production clean-URL convention. No external calls."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import argparse

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        self.serve_clean_url(head_only=False)

    def do_HEAD(self):
        self.serve_clean_url(head_only=True)

    def serve_clean_url(self, head_only):
        original = self.path
        url = urlsplit(original)
        path = url.path
        if path.endswith('.html') or (path.endswith('/') and path != '/'):
            clean = path[:-5] if path.endswith('.html') else path.rstrip('/')
            if clean.endswith('/index'):
                clean = clean[:-6] or '/'
            self.send_response(308)
            self.send_header('Location', urlunsplit(('', '', clean, url.query, '')))
            self.end_headers()
            return
        candidate = ROOT / path.lstrip('/')
        if path == '/blog':
            self.path = '/blog/index.html'
        elif not candidate.is_file() and candidate.with_suffix('.html').is_file():
            self.path = path + '.html'
        if head_only:
            super().do_HEAD()
        else:
            super().do_GET()
        self.path = original


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    print(f'Preview: http://127.0.0.1:{args.port}/blog', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
