#!/usr/bin/env python3
"""Serve actual dist plus a private local-only review, all HTTP noindex."""
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import preview_site
ROOT=Path(__file__).resolve().parents[1]
class Handler(preview_site.Handler):
 def do_GET(self):
  if urlsplit(self.path).path=='/__review/homecourt':
   data=(ROOT/'reports/homecourt/review.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
  else:super().do_GET()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8773);args=p.parse_args();preview_site.ROOT=ROOT/'dist'
 assert (preview_site.ROOT/'homecourt.html').is_file(),'Build first'
 print(f'Local HomeCourt preview: http://127.0.0.1:{args.port}/homecourt',flush=True)
 ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
