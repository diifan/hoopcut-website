"""LAN review service for user-uploaded video; a single GPU worker.
Run on 112, not a Vercel function. Storage is private and expiring.
"""
import asyncio,hashlib,json,os,secrets,shutil,time,threading,math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import engine
ROOT=Path(os.environ.get('SHOT_TRACER_DATA','/var/lib/swi-codex/xcut-seo-agent/data/web-shot-tracer'))
ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
SITE=Path(__file__).resolve().parents[2]/'dist'
app=FastAPI();pool=ThreadPoolExecutor(max_workers=1);lock=threading.RLock();active=set();uploads={}
MAX_BYTES=512*1024**2;TTL=24*3600
ALLOWED_ORIGINS=set(filter(None,os.environ.get('SHOT_TRACER_ORIGINS','').split(',')))
MAX_PENDING=3


def save(folder,**fields):
 with lock:
  path=folder/'state.json';state=json.loads(path.read_text()) if path.exists() else {}
  state.update(fields,updated_at=time.time());tmp=folder/'state.tmp';tmp.write_text(json.dumps(state));tmp.replace(path)
 return state

def folder_for(job):
 if len(job)!=48 or any(c not in '0123456789abcdef' for c in job):raise HTTPException(404,'Video not found')
 folder=ROOT/job
 if not (folder/'state.json').exists():raise HTTPException(404,'Video expired. Import it again.')
 if job not in active and time.time()-json.loads((folder/'state.json').read_text()).get('created_at',folder.stat().st_mtime)>TTL:
  shutil.rmtree(folder);raise HTTPException(404,'Video expired. Import it again.')
 return folder

def clean():
 for d in ROOT.iterdir():
  if not d.is_dir() or d.name in active:continue
  try:
   state=json.loads((d/'state.json').read_text()) if (d/'state.json').exists() else {}
   expired=time.time()-state.get('created_at',d.stat().st_mtime)>TTL
   if expired:shutil.rmtree(d)
  except (OSError,ValueError):continue

def process(folder,start,end,effect):
 try:
  state=json.loads((folder/'state.json').read_text());same=state.get('trim')==[start,end]
  trim=folder/'trim.mp4';cache=folder/'measured-arcs.json'
  if not same or not trim.exists() or not cache.exists():
   save(folder,stage='trimming',progress=5,error=None,trim=[start,end],renders={})
   engine.trim(folder/'source',trim,start,end)
   work=folder/'analysis'
   if work.exists():shutil.rmtree(work)
   cache.unlink(missing_ok=True)
   save(folder,stage='tracking',progress=15)
   arcs=engine.analyze(trim,work)
  else:arcs=json.loads(cache.read_text())
  if not arcs:
   save(folder,stage='no_shots',progress=100,error='No clear shot found. Try a clip where the ball and hoop stay visible.');return
  target=folder/(effect+'.mp4');save(folder,stage='rendering',progress=70)
  receipt=engine.render(trim,target,arcs,effect,lambda p:save(folder,progress=70+int(29*p)))
  state=json.loads((folder/'state.json').read_text());renders=state.get('renders',{});renders[effect]=receipt
  save(folder,stage='ready',progress=100,effect=effect,renders=renders,error=None)
 except Exception as exc:
  (folder/'failure.json').write_text(json.dumps({'type':type(exc).__name__,'detail':str(exc),'at':time.time()}))
  save(folder,stage='failed',error='Processing failed. Retry this clip or choose another.',progress=0)
 finally:
  with lock:active.discard(folder.name)

@app.post('/api/shot-tracer/jobs')
async def upload(request:Request):
 with lock:
  clean()
  now=time.time();ip=request.client.host if request.client else 'local'
  for key in list(uploads):
   uploads[key]=[t for t in uploads[key] if now-t<3600]
   if not uploads[key]:del uploads[key]
  if len(uploads.get(ip,[]))>=6:raise HTTPException(429,'Upload limit reached. Try again in an hour.')
  uploads.setdefault(ip,[]).append(now)
  if len(active)>=MAX_PENDING:raise HTTPException(429,'Busy right now. Try again shortly.')
  if len(list(ROOT.iterdir()))>=40:raise HTTPException(429,'Storage is busy. Try again later.')
  job=secrets.token_hex(24);folder=ROOT/job;folder.mkdir(mode=0o700);active.add(job)
 try:
  if shutil.disk_usage(ROOT).free<2*1024**3:raise HTTPException(503,'Storage is busy. Try again later.')
  count=0;digest=hashlib.sha256()
  with (folder/'source').open('wb') as f:
   async for chunk in request.stream():
    count+=len(chunk)
    if count>MAX_BYTES:raise HTTPException(413,'Choose a video smaller than 512 MB.')
    digest.update(chunk);f.write(chunk)
  if count==0:raise HTTPException(422,'Choose a non-empty video.')
  info=await asyncio.to_thread(engine.probe,folder/'source')
  if not 0<info['duration']<=3600 or max(info['width'],info['height'])>7680:raise HTTPException(422,'Choose a video up to one hour and 8K.')
  save(folder,created_at=now,stage='imported',progress=0,source_sha256=digest.hexdigest(),video=info,renders={})
  return {'id':job,'video':info}
 except HTTPException:
  shutil.rmtree(folder);raise
 except Exception:
  shutil.rmtree(folder);raise HTTPException(422,'Cannot read this video. Try MP4 or MOV.')
 finally:
  with lock:active.discard(job)

@app.post('/api/shot-tracer/jobs/{job}/process')
async def start(job:str,request:Request):
 folder=folder_for(job)
 try:
  data=await request.json()
  start=float(data['start']);end=float(data['end']);effect=data['effect']
  if not isinstance(effect,str) or not math.isfinite(start) or not math.isfinite(end):raise ValueError()
 except (ValueError,TypeError,KeyError):raise HTTPException(422,'Invalid trim or effect')
 state=json.loads((folder/'state.json').read_text())
 if not (0<=start<end<=state['video']['duration']+.05 and end-start<=30.001) or effect not in engine.EFFECTS:raise HTTPException(422,'Choose at most 30 seconds and an available effect.')
 with lock:
  if job in active:return {'stage':state['stage']}
  if state.get('trim')==[start,end] and effect in state.get('renders',{}) and (folder/(effect+'.mp4')).is_file():
   save(folder,stage='ready',progress=100,effect=effect,error=None)
   return {'stage':'ready'}
  if len(active)>=MAX_PENDING:raise HTTPException(429,'Busy right now. Try again shortly.')
  active.add(job);save(folder,stage='queued',progress=0,error=None)
  pool.submit(process,folder,start,end,effect)
 return {'stage':'queued'}

@app.get('/api/shot-tracer/jobs/{job}')
def status(job:str):
 s=json.loads((folder_for(job)/'state.json').read_text())
 return {k:s.get(k) for k in ['stage','progress','video','effect','trim','error','renders']}

@app.get('/api/shot-tracer/jobs/{job}/media/{effect}')
def media(job:str,effect:str,download:bool=False):
 folder=folder_for(job);s=json.loads((folder/'state.json').read_text())
 if effect not in engine.EFFECTS or effect not in s.get('renders',{}):raise HTTPException(404,'Preview not ready')
 if download and effect!='firework':raise HTTPException(403,'Download the app to unlock this effect.')
 return FileResponse(folder/(effect+'.mp4'),media_type='video/mp4',filename='HoopCut-Firework.mp4' if download else None,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})

@app.middleware('http')
async def headers(request,call_next):
 # Review runs same-origin; cross-site mutation is rejected even on the LAN.
 origin=request.headers.get('origin')
 if request.method=='POST' and origin and origin.rstrip('/') not in ALLOWED_ORIGINS|{str(request.base_url).rstrip('/')}:
  return JSONResponse({'detail':'Same-origin request required'},status_code=403)
 response=await call_next(request);response.headers['Cache-Control']='private, no-store';response.headers['X-Robots-Tag']='noindex, nofollow';return response

@app.get('/api/shot-tracer/health')
def health():
 return {'status':'ok','pending':len(active),'queue_capacity':MAX_PENDING}

@app.on_event('startup')
async def startup():
 for d in ROOT.iterdir():
  if (d/'state.json').exists():
   s=json.loads((d/'state.json').read_text())
   if s.get('stage') in ('queued','trimming','tracking','rendering'):
    save(d,stage='failed',error='Processing interrupted. Please retry.',progress=0)
 async def cleanup_loop():
  while True:
   with lock:clean()
   await asyncio.sleep(60)
 app.state.cleanup=asyncio.create_task(cleanup_loop())

app.mount('/',StaticFiles(directory=str(SITE),html=True),name='site')
