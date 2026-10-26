#!/usr/bin/env python3
"""Local static preview with the production clean-URL convention. No external calls."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import argparse
import re

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_head(self):
        # Seeking an MP4 needs byte ranges; SimpleHTTPRequestHandler does not serve them.
        self._range_remaining = None
        path = Path(self.translate_path(self.path))
        if path.suffix.lower() != '.mp4' or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        raw = self.headers.get('Range')
        start, end = 0, size - 1
        if raw:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', raw)
            if not match or not any(match.groups()):
                self.send_error(416, 'Invalid byte range')
                return None
            left, right = match.groups()
            if left:
                start = int(left)
                end = min(int(right), size - 1) if right else size - 1
            else:
                start = max(0, size - int(right))
            if start >= size or start > end:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return None
        source = path.open('rb')
        source.seek(start)
        self.send_response(206 if raw else 200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        if raw:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        self._range_remaining = end - start + 1
        return source

    def copyfile(self, source, outputfile):
        remaining = getattr(self, '_range_remaining', None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        try:
            while remaining > 0:
                chunk = source.read(min(65536, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A media seek legitimately cancels the previous response.

    def end_headers(self):
        # Local previews must never be indexed, even when source markup is release-ready.
        self.send_header('X-Robots-Tag', 'noindex, nofollow')
        super().end_headers()

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
