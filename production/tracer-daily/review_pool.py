"""Bounded incremental source review. No reservation, generation or publication."""
import csv,json,time,hashlib,fcntl,concurrent.futures as cf
from pathlib import Path
from collections import Counter,defaultdict
from urllib.parse import urlparse
import source_cache as sc,content_engine as ce,prepare
ROOT=Path(__file__).resolve().parent
DATA=Path('/data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily')
POOL=DATA/'2026-11-24-keywords.csv'; MANIFEST=DATA/'2026-11-24-source.json'
CACHE=ROOT/'cache/source-probes.json'; RECEIPT=DATA/'2026-11-25-pool-review.json'
POLICY=ROOT.parents[1]/'website-remove-jeana-20261123'
PROXY='http://127.0.0.1:18199'
def main():
 lock=open(ROOT/'state/prepare.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 manifest=json.loads(MANIFEST.read_text());digest=ce._verified(POOL,manifest['sha256'])
 keys,slugs=prepare.collect_occupied(POLICY,'pool-review-only')
 cache={r['source_url']:r for r in json.loads(CACHE.read_text())}
 eligible,counts=ce.select_candidates(POOL,MANIFEST,CACHE,keys,slugs,POLICY)
 baseline=len(eligible); target=baseline+4000
 policy=ce._load(POLICY/'scripts/tracer_keyword_policy.py');slugify=ce._load(POLICY/'scripts/prepare_hudl_tracer_batch.py').slugify
 allowed={}
 for row in csv.DictReader(POOL.open(encoding='utf-8-sig')):
  k=row['keyword'].strip();key=k.casefold()
  if row['status']=='available' and key not in keys and slugify(k) not in slugs and not ce.EXCLUDE.search(k) and not policy.rejection_reason(k):allowed[key]=k
 urls=defaultdict(set)
 for s in manifest['sources']:
  p=Path(s['local_path']);p=p if p.is_absolute() else MANIFEST.parent/p;ce._verified(p,s['sha256'])
  for row in csv.DictReader(p.open(encoding='utf-8-sig')):
   key=row.get('Keyword','').strip().casefold();u=row.get('URL','')
   if key in allowed and sc._allowed(u) and (urlparse(u).hostname.endswith('hudl.com') or ce.research_context(u,allowed[key])):
    if cache.get(u,{}).get('http')!=200:urls[u].add(key)
 # Prioritize evidence serving several basketball terms; preserve unrelated-intent gates.
 pending=sorted(urls,key=lambda u:(-len(urls[u]),0 if 'basketball' in u else 1,u))
 stats=Counter();started=time.time();last=0
 guard={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [DATA/'2026-11-24-receipt.json',ROOT/'state/tracer-daily-20261124.reservation.json'] if p.exists()}
 def checkpoint(stage='fetching',classify=True):
  nonlocal eligible,counts,last
  prepare.save(CACHE,list(cache.values()))
  if classify:eligible,counts=ce.select_candidates(POOL,MANIFEST,CACHE,keys,slugs,POLICY)
  unresolved=sum(v for k,v in counts.items() if k.startswith('unresolved_'))
  result=dict(stage=stage,pool_path=str(POOL),source_manifest=str(MANIFEST),pool_sha256=digest,pool_rows=manifest['rows'],selection_counts=counts,eligible_count=len(eligible),baseline_eligible=baseline,newly_verified=max(0,len(eligible)-baseline),target_newly_verified=4000,fetch_success=stats['success'],fetch_failed=stats['failed'],fetch_completed=sum(stats.values()),source_urls_queued=len(pending),remaining_unverified=unresolved,last_progress_at=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),elapsed_seconds=round(time.time()-started),proxy=PROXY,cache_entries=len(cache),batch_guard_sha256=guard,published=False,shortage_alert=False)
  prepare.save(RECEIPT,result);prepare.save(ROOT/'cache/pool-review-20261125-eligible.json',eligible);last=time.time();print(json.dumps({k:result[k] for k in ['stage','eligible_count','newly_verified','fetch_success','fetch_failed','remaining_unverified']}),flush=True)
 checkpoint()
 with cf.ThreadPoolExecutor(max_workers=16) as ex:
  it=iter(pending);active={};stop=False
  def submit():
   try:u=next(it)
   except StopIteration:return
   active[ex.submit(sc.fetch_one,u,PROXY)]=u
  for _ in range(16):submit()
  while active:
   done,_=cf.wait(active,timeout=2,return_when=cf.FIRST_COMPLETED)
   for f in done:
    u=active.pop(f);r=f.result();old=cache.get(u)
    if old:r['failure_history']=old.get('failure_history',[])+[{k:v for k,v in old.items() if k!='failure_history'}]
    if r.get('http')==200:r['extracted_text_sha256']=hashlib.sha256(r.get('text_excerpt','').encode()).hexdigest()
    cache[u]=r;stats['success' if r.get('http')==200 else 'failed']+=1
    if not stop:submit()
   if time.time()-last>=45:
    checkpoint();stop=len(eligible)>=target
   if stop:
    for f in list(active):
     if f.cancel():active.pop(f)
 checkpoint('completed' if len(eligible)>=target else 'sources_exhausted_unresolved')
 for p,h in guard.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h,'Protected batch changed: '+p
if __name__=='__main__':main()
