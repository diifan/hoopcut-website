#!/usr/bin/env python3
"""Preview the real dist build locally, with clean URLs and HTTP noindex."""
import argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
import preview_site

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8772);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]/'dist'
    if not (root/'tools/basketball-court-diagram.html').is_file():raise SystemExit('Run npm run build first.')
    preview_site.ROOT=root
    print('Court tools preview: http://127.0.0.1:'+str(args.port)+'/tools/basketball-court-diagram',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),preview_site.Handler).serve_forever()
