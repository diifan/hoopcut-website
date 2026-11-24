"""Atomic shuffle-bag assignments: balanced exposure, stable retries."""
import sqlite3,secrets,json,time
from pathlib import Path
DEFAULT=Path('/var/lib/swi-codex/xcut-seo-agent/data/tracer-style-experiment.sqlite')
def assign(key,styles,version,scope='video',database=DEFAULT):
 database=Path(database);database.parent.mkdir(parents=True,exist_ok=True)
 ids=[s['id'] for s in styles]
 if len(ids)!=len(set(ids)) or not ids:raise ValueError('Invalid style catalog')
 with sqlite3.connect(database,timeout=30) as db:
  db.execute('CREATE TABLE IF NOT EXISTS assignments(scope TEXT,key TEXT,version TEXT,style TEXT,cycle INTEGER,created REAL,PRIMARY KEY(scope,key))')
  db.execute('CREATE TABLE IF NOT EXISTS bags(scope TEXT,version TEXT,remaining TEXT,cycle INTEGER,last TEXT,PRIMARY KEY(scope,version))')
  db.execute('BEGIN IMMEDIATE')
  old=db.execute('SELECT style,version,cycle,created FROM assignments WHERE scope=? AND key=?',(scope,key)).fetchone()
  if old:return dict(style_id=old[0],catalog_version=old[1],cycle=old[2],selected_at=old[3],assignment_key=key,scope=scope,policy='shuffle-bag-v1')
  row=db.execute('SELECT remaining,cycle,last FROM bags WHERE scope=? AND version=?',(scope,version)).fetchone()
  remaining=json.loads(row[0]) if row else [];cycle=row[1] if row else 0;last=row[2] if row else None
  if not remaining:
   remaining=ids.copy();secrets.SystemRandom().shuffle(remaining);cycle+=1
   if len(remaining)>1 and remaining[0]==last:remaining[0],remaining[1]=remaining[1],remaining[0]
  chosen=remaining.pop(0);stamp=time.time()
  db.execute('INSERT OR REPLACE INTO bags VALUES(?,?,?,?,?)',(scope,version,json.dumps(remaining),cycle,chosen))
  db.execute('INSERT INTO assignments VALUES(?,?,?,?,?,?)',(scope,key,version,chosen,cycle,stamp))
  return dict(style_id=chosen,catalog_version=version,cycle=cycle,selected_at=stamp,assignment_key=key,scope=scope,policy='shuffle-bag-v1')
