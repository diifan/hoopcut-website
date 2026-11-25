#!/usr/bin/env python3
"""Prepare a reserved daily batch; never merge or assign production domains."""
import argparse, concurrent.futures, csv, datetime as dt, fcntl, hashlib, json, os
import pathlib, re, shutil, subprocess, sys, time, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parent
PROJECT_ROOT=ROOT.parents[1]

def read(p): return json.loads(pathlib.Path(p).read_text())
def save(p,data):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');os.replace(t,p)
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def validate_day(value):
 if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('day must be YYYY-MM-DD')
 return dt.date.fromisoformat(value).isoformat()
def validate_count(pages,target):
 if len(pages)!=target:raise ValueError(f'Expected {target} pages, got {len(pages)}')
 if len({p['keyword'].casefold() for p in pages})!=target or len({p['slug'] for p in pages})!=target:raise ValueError('Duplicate keyword or slug')
def validate_deployment(d,project_id):
 if d.get('projectId')!=project_id or d.get('target')!='production' or d.get('readyState')!='READY':raise ValueError('Deployment project/environment/state mismatch')
 if any(x in ('hoopcut.ai','www.hoopcut.ai') for x in d.get('alias',[])):raise ValueError('Prepared deployment unexpectedly has live domain')
 return d

def parse_deploy_result(result):
 try:
  data=json.loads(result)
 except json.JSONDecodeError:
  matches=re.findall(r'https://[^\s]+\.vercel\.app',result)
  if not matches:raise ValueError('Vercel output lacks deployment identity; reconcile metadata')
  return None,matches[-1]
 if not isinstance(data,dict):raise ValueError('Unexpected Vercel response')
 data=data.get('deployment',data)
 deployment_id=data.get('id') or data.get('uid');url=data.get('url')
 if not deployment_id and not url:raise ValueError('Vercel response lacks deployment identity; reconcile metadata')
 return deployment_id,url

def occupied(reservations,exclude_batch_id=None):
 keys=set();slugs=set()
 for r in reservations:
  if r.get('batch_id')==exclude_batch_id:continue
  keys.update(k.casefold() for k in r.get('keywords',[]));slugs.update(r.get('slugs',[]))
 return keys,slugs

def collect_occupied(worktree,batch_id):
 reservations=[]
 for f in (ROOT/'state').glob('*.reservation.json'):reservations.append(read(f))
 keys,slugs=occupied(reservations,batch_id)
 files=set(PROJECT_ROOT.glob('website*/content/shot-tracer/batches/*/*.json'))
 files.update((worktree/'content/shot-tracer').glob('*.json'))
 for f in files:
  if f.parent.name==batch_id:continue
  data=read(f)
  if not isinstance(data,list):continue
  for p in data:
   if not isinstance(p,dict) or 'slug' not in p:continue
   if p.get('keyword'):keys.add(p['keyword'].casefold())
   if p['slug']:slugs.add(p['slug'])
 return keys,slugs

def scheduled_publish_time():
 cfg=read('/data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily/config.json')
 return f"{cfg.get('hour',12):02}:{cfg.get('minute',30):02}"

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--day',required=True);ap.add_argument('--pool',required=True,type=pathlib.Path);ap.add_argument('--source-manifest',required=True,type=pathlib.Path);ap.add_argument('--receipt',required=True,type=pathlib.Path);ap.add_argument('--target',type=int,default=2000);args=ap.parse_args()
 day=validate_day(args.day)
 if args.target<=0:raise ValueError('target must be positive')
 cfg=read(ROOT/'config.json');batch='tracer-daily-'+day.replace('-','');repo=pathlib.Path(cfg['repository']);worktree=PROJECT_ROOT/('website-'+batch);out=ROOT/'runs'/day;out.mkdir(parents=True,exist_ok=True)
 state=ROOT/'state';state.mkdir(exist_ok=True);lock=open(state/'prepare.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 old=read(args.receipt) if args.receipt.exists() else {}
 if old.get('worktree'):worktree=pathlib.Path(old['worktree'])
 if old and (old.get('day')!=day or old.get('batch_id')!=batch):raise ValueError('Receipt belongs to another batch')
 r=old or {'day':day,'batch_id':batch,'generated_count':0,'urls':[],'published':False,'ready_for_promotion':False,'checks':{},'blockers':[]}
 r.update(prepared_project_id=cfg['project_id'],production_environment=True,worktree=str(worktree),promotion_not_before=day+'T'+scheduled_publish_time()+':00+08:00')
 def checkpoint(stage,**fields):
  r.update(fields);r['stage']=stage;r['checks']['last_progress_at']=dt.datetime.now(dt.timezone.utc).isoformat();save(args.receipt,r);print(json.dumps({'stage':stage,'generated_count':r.get('generated_count'),**fields},ensure_ascii=False)[:1000],flush=True)
 def run(argv,cwd=None,name='command',timeout=1800,capture=False):
  cwd=worktree if cwd is None else cwd
  log=out/(name+'.log')
  if log.exists():shutil.copy2(log,log.with_name(log.stem+'-'+str(time.time_ns())+'.log'))
  tries=6 if name in ('fetch-main','refresh-main') else 1
  for attempt in range(tries):
   if attempt:time.sleep(min(2 ** (attempt-1),8))
   try:p=subprocess.run([str(a) for a in argv],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=min(timeout,60) if tries>1 else timeout,env=(dict(os.environ,HTTP_PROXY=cfg['proxy'],HTTPS_PROXY=cfg['proxy'],http_proxy=cfg['proxy'],https_proxy=cfg['proxy']) if str(argv[0])==cfg['vercel'] else None))
   except subprocess.TimeoutExpired as exc:
    if tries==1:raise
    p=subprocess.CompletedProcess(argv,124,'','Transport timeout')
   with log.open('a') as stream:stream.write(f'Attempt {attempt+1}/{tries}\n'+p.stdout+'\n'+p.stderr+'\n')
   if p.returncode==0:break
   if tries>1:
    r['checks']['repository_retry']={'attempt':attempt+1,'limit':tries,'exit':p.returncode}
    checkpoint('retrying_repository_transport',error='仓库连接暂时失败，正在自动重试')
  if p.returncode and name in ('fetch-main','refresh-main'):
   # If transport fails fetching objects, reuse only an exact live-verified local main.
   probe=subprocess.run(['git','-c','http.proxy=','-c','http.version=HTTP/1.1','ls-remote','https://github.com/diifan/hoopcut-website.git','refs/heads/main'],cwd=repo,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=90)
   local=subprocess.run(['git','rev-parse','origin/main'],cwd=repo,stdout=subprocess.PIPE,text=True,check=True).stdout.strip()
   fields=probe.stdout.split()
   if probe.returncode==0 and len(fields)==2 and fields[1]=='refs/heads/main' and fields[0]==local:
    r['checks']['live_main_fallback']={'commit':local,'verified_at':dt.datetime.now(dt.timezone.utc).isoformat(),'exact_match':True}
    return probe.stdout.strip()
  if p.returncode:raise RuntimeError(f'{name}: exit {p.returncode}; see {log}')
  return p.stdout.strip()
 git=['git','-c','http.proxy='+os.environ.get('HOOPCUT_GIT_PROXY',cfg['proxy']),'-c','http.version=HTTP/1.1','-c','http.postBuffer=524288000']
 def api(path,name):return json.loads(run([cfg['vercel'],'api',path,'--scope',cfg['scope']],name=name,timeout=120))
 def aliases():
  return {domain:api('/v4/aliases/'+domain,'domain-'+domain).get('deploymentId') for domain in ['hoopcut.ai','www.hoopcut.ai']}
 try:
  if r.get('published'):checkpoint('already_published');return 0
  run(git+['fetch','origin','main'],repo,'fetch-main',180);base=run(['git','rev-parse','origin/main'],repo,'base-sha')
  if r.get('ready_for_promotion') and r.get('base_commit')==base:
   d=api('/v13/deployments/'+r['prepared_deployment_id'],'resume-deployment');validate_deployment(d,cfg['project_id']);validate_count(read(r['pages_path']),args.target);checkpoint('already_prepared');return 0
  if r.get('ready_for_promotion'):
   r.setdefault('superseded_preparations',[]).append({k:r.get(k) for k in ['base_commit','commit','prepared_deployment_id','prepared_deployment_url']})
   r['checks']['build']='pending';r['checks']['seo']='pending'
   r.pop('prepared_deployment_id',None);r.pop('prepared_deployment_url',None)
  checkpoint('syncing_main',ready_for_promotion=False,blockers=[],error=None)
  if worktree.exists() and r.get('base_commit') and r['base_commit']!=base:
   worktree=PROJECT_ROOT/('website-'+batch+'-'+base[:8]);r['worktree']=str(worktree)
  if not worktree.exists():run(['git','worktree','add','-b','prepare/'+batch+'-'+base[:8],str(worktree),base],repo,'worktree-add')
  dirty=run(['git','diff','--name-only'],name='existing-worktree-diff')
  if dirty:raise RuntimeError('Existing preparation worktree has tracked modifications; preserved without overwrite: '+dirty[:500])
  baseline_xml=run(['git','show',base+':sitemap.xml'],name='initial-baseline-sitemap')
  baseline_urls=sorted(x.text for x in ET.fromstring(baseline_xml).findall('{*}url/{*}loc'))
  baseline_path=args.receipt.with_name(day+'-baseline.json');save(baseline_path,baseline_urls);r['baseline_path']=str(baseline_path.resolve())
  r['base_commit']=base;r['pages_path']=str(worktree/'content/shot-tracer/batches'/batch/'pages.json')
  resumable=(r.get('commit') and r.get('checks',{}).get('build')=='passed' and r.get('checks',{}).get('seo')=='passed' and sha(args.pool)==r.get('pool_sha256') and pathlib.Path(r['pages_path']).exists() and sha(r['pages_path'])==r.get('pages_sha256') and run(['git','rev-parse','HEAD'],name='resume-head')==r['commit'])
  if not resumable:
   # Snapshot supplied current pool and verified source-manifest; source exports remain read-only.
   snapshot=out/'keywords.csv';shutil.copy2(args.pool,snapshot);shutil.copy2(args.source_manifest,out/'source-manifest.json');r['pool_sha256']=sha(snapshot);r['source_manifest_path']=str(args.source_manifest.resolve())
   from content_engine import select_candidates,build_shard
   keys,slugs=collect_occupied(worktree,batch)
   reservation_file=state/(batch+'.reservation.json')
   from source_cache import refresh_cache
   checkpoint('refreshing_source_cache')
   cached_eligible,cached_counts=select_candidates(snapshot,args.source_manifest,ROOT/cfg['cache_path'],keys,slugs,worktree/'scripts')
   if len(cached_eligible)>=args.target:
    cache_counts={'reused_verified_eligible':len(cached_eligible),'refresh_skipped_sufficient_verified_cache':True}
   else:
    cache_counts=refresh_cache(snapshot,args.source_manifest,ROOT/cfg['cache_path'],keys,slugs,worktree/'scripts',proxy=cfg['proxy'],max_workers=8)
   r['checks']['source_cache_refresh']=cache_counts
   eligible,counts=select_candidates(snapshot,args.source_manifest,ROOT/cfg['cache_path'],keys,slugs,worktree/'scripts')
   reservation=read(reservation_file) if reservation_file.exists() else None
   if reservation:
    selected=reservation['selected'];validate_count([{'keyword':x['keyword'],'slug':x['slug']} for x in selected],args.target)
    if any(x['keyword'].casefold() in keys or x['slug'] in slugs for x in selected):raise ValueError('Reserved selection now conflicts with another batch')
   else:selected=eligible[:args.target]
   r.update(eligible_count=len(eligible),shortfall=max(0,args.target-len(selected)),eligible_remaining_after_reservation=max(0,len(eligible)-len(selected)))
   r['checks']['selection_counts']=counts
   unresolved=sum(v for k,v in counts.items() if k.startswith('unresolved_') and isinstance(v,int))
   r['next_day_pool_warning']={'verification_complete':unresolved==0,'unresolved':unresolved,'required':unresolved==0 and r['eligible_remaining_after_reservation']<args.target,'for_day':(dt.date.fromisoformat(day)+dt.timedelta(days=1)).isoformat(),'eligible_remaining':r['eligible_remaining_after_reservation'],'shortfall':max(0,args.target-r['eligible_remaining_after_reservation']),'delivery_owner':'controller; SEO-Agent group mention to Cao Shiyu'}
   if len(selected)<args.target and unresolved:
    r['next_day_pool_warning']['required']=False
    checkpoint('source_evidence_incomplete',generated_count=0,error='来源抓取尚未完成，不能判定词池不足',blockers=[{'type':'source_fetch_incomplete','unresolved_keywords':unresolved,'eligible_count':len(selected)}]);return 2
   if len(selected)<args.target:
    checkpoint('insufficient_pool',generated_count=0,shortfall=args.target-len(selected),blockers=[{'type':'pool_shortfall','eligible_count':len(selected),'shortfall':args.target-len(selected)}]);return 2
   save(reservation_file,{'batch_id':batch,'day':day,'keywords':[x['keyword'] for x in selected],'slugs':[x['slug'] for x in selected],'selected':selected,'pool_sha256':r['pool_sha256'],'receipt':str(args.receipt.resolve())})
   checkpoint('reserved',eligible_remaining_after_reservation=r['eligible_remaining_after_reservation'])
   workers=[];futures=[]
   with concurrent.futures.ProcessPoolExecutor(max_workers=3) as pool:
    for n in range(3):
     target=out/f'shard-{n}.json';rows=selected[n::3];workers.append({'worker_id':f'shard-{n}','assigned':len(rows),'output_path':str(target),'status':'running'});futures.append(pool.submit(build_shard,rows,worktree,batch,target))
    r['checks']['parallel_workers']=workers;checkpoint('assembling')
    for future in concurrent.futures.as_completed(futures):
     result=future.result();w=next(x for x in workers if x['output_path']==result['output_path']);w.update(status='completed',processed=result['count'],pid=result['pid']);checkpoint('assembling',generated_count=sum(x.get('processed',0) for x in workers))
   pages=[p for n in range(3) for p in read(out/f'shard-{n}.json')['pages']];validate_count(pages,args.target);save(r['pages_path'],pages)
   urls=['https://hoopcut.ai/shot-tracer/'+p['slug'] for p in pages];manifest={'batchId':batch,'status':'authorized_scheduled_release','newPages':len(pages),'newSlugs':[p['slug'] for p in pages],'previewSlugs':[p['slug'] for p in pages],'urls':urls,'promotionNotBefore':r['promotion_not_before'],'releaseApproval':{'source':'User standing authorization: 2000 daily, Asia/Shanghai 12:30; controller promotes prepared deployment only','publication_authorized':True},'keywords':[{'keyword':p['keyword'],'targetPath':'/shot-tracer/'+p['slug'],'intentFit':'adjacent','records':[p['demandEvidence']]} for p in pages]}
   save(worktree/'content/shot-tracer/batch-manifests'/(batch+'.json'),manifest);checkpoint('generated',generated_count=len(pages),urls=urls)
   ignore=worktree/'.vercelignore';ignore_text=ignore.read_text() if ignore.exists() else ''
   for pattern in ['dist/','node_modules/']:
    if pattern not in ignore_text.splitlines():ignore_text+='\n'+pattern+'\n'
   ignore.write_text(ignore_text)
   if not (worktree/'node_modules').exists():run(['npm','ci'],name='npm-ci')
   # Standard resources run on baseline/main source; unrelated generated files are never committed.
   run(['python3','scripts/build_resources.py'],name='resources-build');run(['npm','run','build'],name='production-build');r['checks']['build']='passed'
   run(['python3','scripts/check_site_seo.py'],name='seo-check');r['checks']['seo']='passed'
   sitemap={x.text for x in ET.parse(worktree/'sitemap.xml').findall('{*}url/{*}loc')}
   if not set(urls)<=sitemap:raise ValueError('Batch not fully included in built sitemap')
   baseline=run(['git','show',base+':sitemap.xml'],name='baseline-sitemap');before={x.text for x in ET.fromstring(baseline).findall('{*}url/{*}loc')}
   if set(urls)&before or not before<=sitemap:raise ValueError('Baseline collision or loss')
   r['checks']['routes']={'count':len(urls),'baseline_retained':len(before),'sitemap_count':len(sitemap),'passed':True}
   # Restore only unrelated tracked generator output, retaining it as an audit patch.
   changed=run(['git','diff','--name-only'],name='changed').splitlines();unrelated=[p for p in changed if not (p in ('sitemap.xml','.vercelignore') or p.startswith('shot-tracer/'))]
   if unrelated:
    (out/'unrelated-generated.patch').write_text(run(['git','diff','--']+unrelated,name='unrelated-diff'))
    run(['git','restore','--source=HEAD','--']+unrelated,name='restore-unrelated')
   # Preserve a versioned copy of the preparation tool in the prepared commit.
   tool_dest=worktree/'production/tracer-daily';tool_dest.mkdir(parents=True,exist_ok=True)
   for f in ROOT.glob('*.py'):shutil.copy2(f,tool_dest/f.name)
   if (ROOT/'README.md').exists():shutil.copy2(ROOT/'README.md',tool_dest/'README.md')
   run(['git','add','content/shot-tracer/batches/'+batch,'content/shot-tracer/batch-manifests/'+batch+'.json','shot-tracer','sitemap.xml','.vercelignore','production/tracer-daily'],name='git-add')
   staged=run(['git','diff','--cached','--name-only'],name='staged')
   if staged:run(['git','commit','-q','-m',f'Prepare {day} scheduled Tracer batch ({len(pages)} pages)'],name='commit')
   r['commit']=run(['git','rev-parse','HEAD'],name='commit-sha');r['checks']['pages_sha256']=sha(r['pages_path']);r['pages_sha256']=r['checks']['pages_sha256']
  else:
   checkpoint('resuming_verified_upload')
  run(git+['fetch','origin','main'],repo,'refresh-main',180)
  if run(['git','rev-parse','origin/main'],repo,'refresh-base')!=base:raise RuntimeError('main changed during build; prepared upload withheld')
  # Never push/merge: a remote branch is optional, and direct skip-domain deploy suffices.
  live_before=aliases()
  if not all(live_before.values()):raise ValueError('Cannot prove current production domain deployment IDs')
  r['checks']['domains_before']=live_before;checkpoint('uploading_prepared',published=False)
  # Reconcile a prior uncertain upload by metadata before issuing another deploy.
  ds=api('/v6/deployments?projectId='+cfg['project_id']+'&target=production&limit=100','existing-deployments').get('deployments',[])
  found=next((d for d in ds if d.get('meta',{}).get('swieBatch')==batch and d.get('meta',{}).get('swieCommit')==r['commit']),None)
  if found:deployment_id=found['uid']
  else:
   result=run([cfg['vercel'],'deploy','--prod','--skip-domain','--archive=tgz','--project',cfg['project_id'],'--scope',cfg['scope'],'--yes','--json','--meta','swieBatch='+batch,'--meta','swieCommit='+r['commit']],name='prepared-deploy',timeout=1800)
   deployment_id,url=parse_deploy_result(result)
   if not deployment_id:
    d=api('/v13/deployments/'+url.removeprefix('https://'),'resolve-deployment');deployment_id=d['id']
  r['prepared_deployment_id']=deployment_id;checkpoint('verifying_prepared')
  for attempt in range(60):
   d=api('/v13/deployments/'+deployment_id,'prepared-state')
   if d.get('readyState') in ('READY','ERROR','CANCELED'):break
   time.sleep(5)
  validate_deployment(d,cfg['project_id'])
  if d.get('meta',{}).get('swieBatch')!=batch or d.get('meta',{}).get('swieCommit')!=r['commit']:raise ValueError('Deployment batch/commit metadata mismatch')
  live_after=aliases()
  if live_before!=live_after:raise ValueError('Production domains changed during preparation; do not promote')
  r['checks']['domains_after']=live_after;r['checks']['deployment']={'projectId':d['projectId'],'target':d['target'],'readyState':d['readyState'],'alias':d.get('alias',[])}
  save(out/'prepared-deployment.json',d)
  checkpoint('prepared',prepared_deployment_url='https://'+d['url'],ready_for_promotion=True,published=False,error=None,blockers=[])
  return 0
 except Exception as e:
  r.setdefault('failure_history',[]).append({'at':dt.datetime.now(dt.timezone.utc).isoformat(),'stage':r.get('stage'),'error':str(e)})
  checkpoint('preparation_failed',ready_for_promotion=False,error=str(e),blockers=[{'type':'preparation_error','detail':str(e)}]);return 1
 finally:
  lock.close()
if __name__=='__main__':sys.exit(main())
