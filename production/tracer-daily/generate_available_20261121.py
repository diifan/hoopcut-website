import sys,json,pathlib,concurrent.futures,fcntl,hashlib,datetime,importlib.util
ROOT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from prepare import read,save,collect_occupied,validate_count
from content_engine import select_candidates,build_shard
lock=open(ROOT/'state/prepare.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
b=pathlib.Path('/data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily');rp=b/'2026-11-21-receipt.json';r=read(rp);w=pathlib.Path(r['worktree']);batch=r['batch_id'];out=ROOT/'runs/2026-11-21'
keys,slugs=collect_occupied(w,batch)
selected,counts=select_candidates(b/'2026-11-21-keywords.csv',b/'2026-11-21-source.json',ROOT/'cache/source-probes.json',keys,slugs,w/'scripts')
assert selected
r.update(stage='assembling_available',requested_daily_target=2000,authorized_generation_scope='All currently eligible keywords; user instruction 2026-11-21',ready_for_promotion=False,published=False)
r['checks']['selection_counts']=counts;save(rp,r)
workers=[]
with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:
 futures=[]
 for n in range(3):
  path=out/f'available-shard-{n}.json';rows=selected[n::3];workers.append({'worker_id':f'available-{n}','assigned':len(rows),'output_path':str(path)});futures.append(pool.submit(build_shard,rows,w,batch,path))
 for f in concurrent.futures.as_completed(futures):
  res=f.result();worker=next(x for x in workers if x['output_path']==res['output_path']);worker.update(processed=res['count'],pid=res['pid'],status='completed')
pages=[p for x in workers for p in read(x['output_path'])['pages']]
validate_count(pages,len(selected))
for p in pages:
 p['status']='draft'
 p['releaseApproval']['source']='Standing publication authorization retained; current instruction generates all eligible pages. This artifact is an unpublished draft.'
save(r['pages_path'],pages)
urls=['https://hoopcut.ai/shot-tracer/'+p['slug'] for p in pages]
save(w/'content/shot-tracer/batch-manifests'/f'{batch}.json',{'batchId':batch,'status':'draft','newPages':len(pages),'previewSlugs':[p['slug'] for p in pages],'urls':urls})
save(ROOT/'state'/f'{batch}.reservation.json',{'day':r['day'],'batch_id':batch,'keywords':[x['keyword'] for x in selected],'slugs':[x['slug'] for x in selected],'selected':selected,'receipt':str(rp),'pool_sha256':r['pool_sha256']})
r.update(generated_count=len(pages),urls=urls,eligible_count=len(selected),eligible_remaining_after_reservation=0,shortfall=max(0,2000-len(pages)),pages_sha256=hashlib.sha256(pathlib.Path(r['pages_path']).read_bytes()).hexdigest(),stage='drafts_generated',blockers=[])
r['checks']['parallel_workers']=workers;r['checks']['last_progress_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save(rp,r)
print('GENERATED',len(pages),flush=True)
sys.path.insert(0,str(w/'scripts'))
spec=importlib.util.spec_from_file_location('batch_builder',w/'scripts/build_shot_tracer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.build(root=w,preview_batch=batch)
for p in pages:
 html=(w/'shot-tracer'/(p['slug']+'.html')).read_text()
 assert 'noindex' in html and 'https://hoopcut.ai/shot-tracer/'+p['slug'] in html
r['checks']['draft_render']={'status':'passed','count':len(pages),'canonical_and_noindex':True};r['stage']='drafts_rendered';r['final_summary']=f'All {len(pages)} eligible keywords generated and rendered as local unpublished drafts; daily 2000 target remains separate.';save(rp,r)
print('RENDER_CHECK_PASSED',len(pages),flush=True)
