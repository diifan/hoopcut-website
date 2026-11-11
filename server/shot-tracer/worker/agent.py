"""HoopCut outbound pull worker; one job, bounded runtime and own GPU memory watchdog."""
import os,json,time,hashlib,signal,subprocess,threading,shutil,fcntl
from pathlib import Path
import httpx,psutil
from sandbox import command
CONFIG=json.loads(Path(os.environ['HC_TRACER_CONFIG']).read_text());ROOT=Path(CONFIG['root']);ROOT.mkdir(parents=True,exist_ok=True,mode=0o700);(ROOT/'jobs').mkdir(exist_ok=True,mode=0o700)
lock=(ROOT/'agent.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
BASE=CONFIG['endpoint'];KEY=CONFIG['worker_key'];ENV=CONFIG.get('environment','staging')
class LostLease(Exception):pass
def call(action,id='',data=None):
 headers={'Content-Type':'application/json'}
 if '/functions/v1/' in BASE:headers['x-hc-worker']=KEY
 else:headers['Authorization']='Bearer '+KEY
 with httpx.Client(timeout=20,follow_redirects=False) as c:r=c.post(BASE,headers=headers,json={'environment':ENV,'action':action,'id':id,'data':data or {}})
 if r.status_code in (409,410):raise LostLease()
 if r.status_code!=200:raise RuntimeError('bridge_http_'+str(r.status_code))
 return r.json()
def gpu_free():
 raw=subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],timeout=10,text=True);return int(raw.strip().splitlines()[0])
def own_gpu(proc):
 try:pids={proc.pid,*[p.pid for p in psutil.Process(proc.pid).children(recursive=True)]}
 except psutil.NoSuchProcess:return 0
 raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits'],timeout=10,text=True)
 return sum(int(row.split(',')[1].strip()) for row in raw.splitlines() if row and row.split(',')[0].strip().isdigit() and int(row.split(',')[0]) in pids and row.split(',')[1].strip().isdigit())
def terminate(proc):
 try:children=psutil.Process(proc.pid).children(recursive=True)
 except psutil.NoSuchProcess:children=[]
 for p in reversed(children):
  try:p.kill()
  except psutil.NoSuchProcess:pass
 try:os.killpg(proc.pid,signal.SIGKILL)
 except ProcessLookupError:pass
 proc.wait(timeout=10)
def process(task):
 folder=ROOT/'jobs'/task['id'];folder.mkdir(exist_ok=True,mode=0o700)
 cancel=threading.Event();done=threading.Event();progress={'stage':'downloading','progress':0};lease={'lease':task['lease']};proc=None
 def beat():
  while not done.is_set():
   try:call('heartbeat',task['id'],{**lease,**progress})
   except LostLease:cancel.set();return
   except Exception:cancel.set();return
   done.wait(15)
 thread=threading.Thread(target=beat,daemon=True);thread.start()
 try:
  source=folder/'source';download_started=time.monotonic()
  if not source.exists() or source.stat().st_size!=task['size_bytes']:
   tmp=folder/'source.part';count=0
   with httpx.stream('GET',task['source_url'],timeout=60,follow_redirects=False) as r:
    if r.status_code!=200:raise RuntimeError('download_failed')
    with tmp.open('wb') as f:
     for part in r.iter_bytes(256*1024):
      if cancel.is_set():raise LostLease()
      if time.monotonic()-download_started>600:raise TimeoutError()
      count+=len(part)
      if count>task['size_bytes'] or count>536870912:raise ValueError('source_limit')
      f.write(part)
   if count!=task['size_bytes']:raise ValueError('source_length')
   tmp.replace(source)
  local={k:v for k,v in task.items() if k not in ('source_url','lease')};(folder/'task.json').write_text(json.dumps(local))
  (folder/'result.json').unlink(missing_ok=True);(folder/'progress.json').unlink(missing_ok=True)
  peak=0;started=time.monotonic()
  with (folder/'compute.log').open('w') as log:
   proc=subprocess.Popen(command(folder),stdout=log,stderr=log,start_new_session=True)
   while proc.poll() is None:
    if cancel.is_set():raise LostLease()
    if time.monotonic()-started>1200:raise TimeoutError()
    mem=own_gpu(proc);peak=max(peak,mem)
    # Once admitted, GPU pressure is telemetry only; never preempt a website job.
    # Resource availability gates new admissions below, not work already running.
    try:progress.update(json.loads((folder/'progress.json').read_text()))
    except (OSError,ValueError):pass
    time.sleep(1)
  if proc.returncode:raise RuntimeError('compute_failed')
  result=json.loads((folder/'result.json').read_text())
  if result['state']=='ready':
   progress.update(stage='returning',progress=99);a=call('artifact',task['id'],lease)
   path=folder/'result.mp4'
   with path.open('rb') as f,httpx.Client(timeout=180,follow_redirects=False) as c:
    r=c.put(a['upload_url'],content=f,headers={'Content-Type':'video/mp4','Content-Length':str(path.stat().st_size)})
   if r.status_code not in (200,201):raise RuntimeError('upload_failed')
   result['render']['path']=a['path']
  if cancel.is_set():raise LostLease()
  call('finish',task['id'],{**lease,**result})
  receipt={k:result[k] for k in ('state','elapsed_seconds','error_code') if k in result};receipt.update(job_id=task['id'],peak_gpu_mib=peak,finished_at=time.time());(folder/'agent-receipt.json').write_text(json.dumps(receipt));print(json.dumps(receipt),flush=True)
 except LostLease:print(json.dumps({'job_id':task['id'],'state':'lease_lost'}),flush=True)
 except Exception as e:
  code='resource_limit' if isinstance(e,(MemoryError,TimeoutError)) else 'processing_failed'
  try:call('finish',task['id'],{**lease,'state':'failed','error_code':code})
  except Exception:pass
  print(json.dumps({'job_id':task['id'],'state':'failed','error_type':type(e).__name__}),flush=True)
 finally:
  done.set()
  if proc is not None and proc.poll() is None:terminate(proc)
  thread.join(timeout=22)
  for name in ['source.part','result.mp4']:(folder/name).unlink(missing_ok=True)
def main():
 last_clean=0
 while True:
  try:
   if time.time()-last_clean>300:
    call('cleanup');last_clean=time.time()
    for d in (ROOT/'jobs').iterdir():
     if d.is_dir() and time.time()-d.stat().st_mtime>86400:shutil.rmtree(d)
   if shutil.disk_usage(ROOT).free<5*1024**3 or gpu_free()<12288:time.sleep(10);continue
   task=call('poll').get('task')
   if task:process(task)
   else:time.sleep(5)
  except Exception as e:print(json.dumps({'worker_error':type(e).__name__}),flush=True);time.sleep(10)
if __name__=='__main__':main()
