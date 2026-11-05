"""Anonymous comments. SQLite for a persistent local/self-hosted service; Postgres on Vercel."""
import contextlib
import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
COOKIE = 'hc_comment_session'
PAGE_SIZE = 20
SCHEMA = [
    'CREATE TABLE IF NOT EXISTS hc_visitors (token_hash TEXT PRIMARY KEY, public_id TEXT NOT NULL UNIQUE)',
    '''CREATE TABLE IF NOT EXISTS hc_comments (id TEXT PRIMARY KEY, video_id TEXT NOT NULL,
       parent_id TEXT REFERENCES hc_comments(id), visitor TEXT NOT NULL REFERENCES hc_visitors(public_id),
       name TEXT NOT NULL, body TEXT NOT NULL, created_at BIGINT NOT NULL,
       request_key TEXT UNIQUE NOT NULL, is_example INTEGER NOT NULL DEFAULT 0)''',
    '''CREATE TABLE IF NOT EXISTS hc_votes (comment_id TEXT NOT NULL REFERENCES hc_comments(id),
       visitor TEXT NOT NULL REFERENCES hc_visitors(public_id), value INTEGER NOT NULL CHECK(value IN (-1,1)),
       PRIMARY KEY(comment_id,visitor))''',
    'CREATE INDEX IF NOT EXISTS hc_comments_video ON hc_comments(video_id,parent_id,created_at)',
    'CREATE INDEX IF NOT EXISTS hc_comments_parent ON hc_comments(parent_id,created_at)',
]


class BadRequest(Exception):
    def __init__(self, message, status=400):
        self.status = status
        super().__init__(message)


class Database:
    def __init__(self, sqlite_path=None, postgres_url=None):
        self.postgres_url = postgres_url or os.environ.get('COMMENTS_DATABASE_URL')
        self.sqlite_path = sqlite_path or os.environ.get('COMMENTS_SQLITE_PATH')
        if not self.postgres_url and not self.sqlite_path:
            raise RuntimeError('Persistent comments database is not configured')
        if os.environ.get('VERCEL') and not self.postgres_url:
            raise RuntimeError('Vercel requires a shared persistent database, not its temporary disk')

    @contextlib.contextmanager
    def connect(self):
        if self.postgres_url:
            import psycopg
            conn = psycopg.connect(self.postgres_url, connect_timeout=8)
        else:
            path = Path(self.sqlite_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path, timeout=15)
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA journal_mode=WAL')
        try:
            for statement in SCHEMA:
                conn.execute(statement)
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def query(self, conn, sql, args=()):
        return conn.execute(sql.replace('?', '%s') if self.postgres_url else sql, args)

    def rows(self, cursor):
        keys = [c[0] for c in cursor.description]
        return [dict(zip(keys, row)) for row in cursor.fetchall()]

    def visitor(self, conn, token):
        if token and re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
            hashed = hashlib.sha256(token.encode()).hexdigest()
            row = self.query(conn, 'SELECT public_id FROM hc_visitors WHERE token_hash=?', (hashed,)).fetchone()
            if row:
                return row[0], None
        token = secrets.token_urlsafe(32)
        public_id = secrets.token_hex(12)
        self.query(conn, 'INSERT INTO hc_visitors(token_hash,public_id) VALUES (?,?)',
                   (hashlib.sha256(token.encode()).hexdigest(), public_id))
        return public_id, token

    def comments(self, conn, video, viewer, parent=None, sort='top', offset=0):
        condition = 'c.parent_id IS NULL' if parent is None else 'c.parent_id=?'
        params = [viewer, video] + ([] if parent is None else [parent])
        order = 'likes DESC,c.created_at DESC,c.id DESC' if sort == 'top' and parent is None else 'c.created_at DESC,c.id DESC'
        sql = '''SELECT c.id,c.video_id,c.parent_id,c.name,c.body,c.created_at,c.is_example,
                 (SELECT COUNT(*) FROM hc_votes v WHERE v.comment_id=c.id AND v.value=1) AS likes,
                 COALESCE((SELECT value FROM hc_votes v WHERE v.comment_id=c.id AND v.visitor=?),0) AS my_vote,
                 (SELECT COUNT(*) FROM hc_comments reply WHERE reply.parent_id=c.id) AS reply_count
                 FROM hc_comments c WHERE c.video_id=? AND '''+condition+' ORDER BY '+order+' LIMIT ? OFFSET ?'
        rows = self.rows(self.query(conn, sql, tuple(params+[PAGE_SIZE+1, offset])))
        more = len(rows) > PAGE_SIZE
        return {'comments': rows[:PAGE_SIZE], 'next_offset': offset+PAGE_SIZE if more else None}

    def count(self, conn, video):
        return self.query(conn, 'SELECT COUNT(*) FROM hc_comments WHERE video_id=?', (video,)).fetchone()[0]

    def post(self, conn, video, viewer, payload):
        body = payload.get('body')
        name = payload.get('name', '')
        if not isinstance(body, str) or not body.strip() or len(body) > 3000 or '\x00' in body:
            raise BadRequest('Write a comment between 1 and 3,000 characters.')
        if not isinstance(name, str) or len(name) > 40 or '\x00' in name:
            raise BadRequest('Your optional name can be up to 40 characters.')
        name = name.strip() or 'Guest '+viewer[:6]
        body = body.strip()
        request_id = payload.get('request_id', '')
        if not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9-]{16,64}', request_id):
            raise BadRequest('Please refresh the page and try again.')
        parent = payload.get('parent_id') or None
        if parent:
            if not isinstance(parent, str):
                raise BadRequest('Invalid reply.')
            row = self.query(conn, 'SELECT parent_id FROM hc_comments WHERE id=? AND video_id=?', (parent, video)).fetchone()
            if not row or row[0]:
                raise BadRequest('That conversation is unavailable.', 404)
        key = viewer+':'+request_id
        existing = self.rows(self.query(conn, 'SELECT id,body,name,parent_id,video_id FROM hc_comments WHERE request_key=?', (key,)))
        if existing:
            row = existing[0]
            if (row['body'],row['name'],row['parent_id'],row['video_id']) != (body,name,parent,video):
                raise BadRequest('This submission has already been used.', 409)
            return row['id']
        comment_id = secrets.token_hex(16)
        self.query(conn, '''INSERT INTO hc_comments(id,video_id,parent_id,visitor,name,body,created_at,request_key)
                          VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(request_key) DO NOTHING''',
                   (comment_id,video,parent,viewer,name,body,int(time.time()*1000),key))
        return self.query(conn, 'SELECT id FROM hc_comments WHERE request_key=?', (key,)).fetchone()[0]

    def vote(self, conn, video, viewer, payload):
        comment_id, value = payload.get('comment_id'), payload.get('value')
        if type(value) is not int or value not in (-1,0,1) or not isinstance(comment_id, str):
            raise BadRequest('Invalid reaction.')
        if not self.query(conn, 'SELECT 1 FROM hc_comments WHERE id=? AND video_id=?', (comment_id,video)).fetchone():
            raise BadRequest('This comment is unavailable.', 404)
        if value:
            self.query(conn, '''INSERT INTO hc_votes(comment_id,visitor,value) VALUES (?,?,?)
                              ON CONFLICT(comment_id,visitor) DO UPDATE SET value=excluded.value''', (comment_id,viewer,value))
        else:
            self.query(conn, 'DELETE FROM hc_votes WHERE comment_id=? AND visitor=?', (comment_id,viewer))
        likes = self.query(conn, 'SELECT COUNT(*) FROM hc_votes WHERE comment_id=? AND value=1', (comment_id,)).fetchone()[0]
        return {'likes':likes,'my_vote':value}


def video_ids():
    # Generated alongside watch pages; the private content directory is not deployed.
    return set(json.loads((ROOT/'api/video-ids.json').read_text()))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond(write=False)

    def do_POST(self):
        self.respond(write=True)

    def respond(self, write=False):
        token = None
        try:
            query = parse_qs(urlsplit(self.path).query)
            video = query.get('video', [''])[0]
            if video not in video_ids():
                raise BadRequest('This video is unavailable.',404)
            if write:
                origin = self.headers.get('Origin')
                allowed = {'https://hoopcut.ai','https://www.hoopcut.ai'}
                if not os.environ.get('VERCEL'):
                    allowed.add('http://'+self.headers.get('Host',''))
                if (origin and origin not in allowed) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                    raise BadRequest('Open this video on HoopCut to comment.',403)
                if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                    raise BadRequest('A JSON submission is required.',415)
                try:
                    length = int(self.headers.get('Content-Length','0'))
                    if not 0 < length <= 20000:
                        raise ValueError()
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload,dict):
                        raise ValueError()
                except (ValueError,UnicodeDecodeError):
                    raise BadRequest('Invalid submission.',400)
            cookies = SimpleCookie()
            cookies.load(self.headers.get('Cookie',''))
            existing_token = cookies[COOKIE].value if COOKIE in cookies else None
            db = Database()
            with db.connect() as conn:
                viewer, token = db.visitor(conn, existing_token)
                if write:
                    action = payload.get('action','comment')
                    if action == 'comment':
                        result = {'comment_id':db.post(conn,video,viewer,payload),'total':db.count(conn,video)}
                    elif action == 'vote':
                        result = db.vote(conn,video,viewer,payload)
                    else:
                        raise BadRequest('Unknown action.')
                else:
                    sort = query.get('sort',['top'])[0]
                    if sort not in ('top','newest'):
                        raise BadRequest('Invalid sort order.')
                    try:
                        offset = int(query.get('offset',['0'])[0])
                        if not 0 <= offset <= 100000:
                            raise ValueError()
                    except ValueError:
                        raise BadRequest('Invalid page.')
                    parent = query.get('parent',[None])[0]
                    result = db.comments(conn,video,viewer,parent,sort,offset)
                    result.update(total=db.count(conn,video),viewer={'name':'Guest '+viewer[:6]},
                                  preview=bool(os.environ.get('COMMENTS_PREVIEW')))
            self.send_json(200,result,token)
        except BadRequest as e:
            self.send_json(e.status,{'error':str(e)})
        except Exception:
            self.send_json(503,{'error':'Comments are unavailable right now. Please try again shortly.'})

    def send_json(self,status,data,token=None):
        encoded = json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Robots-Tag','noindex, nofollow')
        self.send_header('X-Content-Type-Options','nosniff')
        if token:
            secure = '; Secure' if os.environ.get('VERCEL') else ''
            self.send_header('Set-Cookie',COOKIE+'='+token+'; HttpOnly; SameSite=Lax; Path=/api/comments; Max-Age=31536000'+secure)
        self.send_header('Content-Length',str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
