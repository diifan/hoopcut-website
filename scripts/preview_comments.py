#!/usr/bin/env python3
"""Loopback preview with a real shared SQLite store; optional explicitly labelled fixtures."""
import argparse
import hashlib
import importlib.util
import json
import os
import secrets
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,unquote
from posixpath import normpath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from preview_site import Handler as Static
spec=importlib.util.spec_from_file_location('comments_api',ROOT/'api/comments.py')
api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)


class Handler(Static,api.handler):
    def private(self):
        path=normpath(unquote(urlsplit(self.path).path))
        return any(part.startswith('.') for part in path.split('/') if part) or path.startswith(('/api/','/reports/','/scripts/','/content/')) or path=='/requirements.txt'

    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/api/comments':
            return api.handler.do_GET(self)
        if self.private():
            return self.send_error(404)
        return Static.do_GET(self)

    def do_POST(self):
        if urlsplit(self.path).path=='/api/comments':
            return api.handler.do_POST(self)
        return self.send_error(405)

    def do_HEAD(self):
        if self.private():
            return self.send_error(404)
        return Static.do_HEAD(self)

    def end_headers(self):
        if urlsplit(self.path).path=='/api/comments':
            return BaseHTTPRequestHandler.end_headers(self)
        return Static.end_headers(self)


def seed_examples():
    db=api.Database()
    with db.connect() as conn:
        # Local fixtures only; never seed a production database.
        if db.postgres_url or os.environ.get('VERCEL'):
            raise RuntimeError('Example comments are restricted to local SQLite previews')
        examples=json.loads((ROOT/'scripts/comment_examples.json').read_text())
        video=next(iter(api.video_ids()))
        ids=[]
        for i,example in enumerate(examples):
            key='local-example:'+str(i)
            old=db.query(conn,'SELECT id FROM hc_comments WHERE request_key=?',(key,)).fetchone()
            if old:
                ids.append(old[0]);continue
            viewer,_=db.visitor(conn,None)
            comment_id=secrets.token_hex(16);ids.append(comment_id)
            parent=ids[example['reply_to']] if 'reply_to' in example else None
            db.query(conn,'''INSERT INTO hc_comments(id,video_id,parent_id,visitor,name,body,created_at,request_key,is_example)
                            VALUES (?,?,?,?,?,?,?,?,1)''',
                     (comment_id,video,parent,viewer,example['name'],example['body'],int(time.time()*1000)-example['minutes_ago']*60000,key))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8769)
    parser.add_argument('--database',default=str(ROOT/'reports/comments-preview.sqlite3'))
    parser.add_argument('--examples',action='store_true');args=parser.parse_args()
    os.environ['COMMENTS_SQLITE_PATH']=str(Path(args.database).resolve())
    os.environ['COMMENTS_PREVIEW']='1'
    if args.examples:seed_examples()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print('Preview: http://127.0.0.1:'+str(server.server_address[1])+'/videos/two-pickup-jump-shots-shot-tracer',flush=True)
    server.serve_forever()
