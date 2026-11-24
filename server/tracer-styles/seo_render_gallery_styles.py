"""112-only 25-style renderer. Random choice is durable; arcs are measured, never gallery fixtures."""
import fcntl,hashlib,json,math,pathlib,secrets,subprocess,sys,time
import cv2,numpy as np
from PIL import Image,ImageFont
from render_short import evidence_for
ROOT=pathlib.Path('/data/swi-algo/Swi-App-Factory/Hoopcut/production/tracer-styles')
CATALOG=ROOT/'catalog.json'
sys.path.insert(0,str(ROOT/'vendor'))
import app_draw
ASSET=pathlib.Path('/var/lib/swi-codex/xcut-seo-agent/assets/hoopcut-bounce-orange-portrait.mp4')
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def ff(args):subprocess.run(['ffmpeg','-nostdin','-v','error','-y',*map(str,args)],check=True,timeout=600)
def preflight(out):
 c=json.loads(CATALOG.read_text())
 for p,digest in c['sha256'].items():
  if sha(p)!=digest:raise ValueError('Style renderer changed; revalidate catalog: '+p)
 if len(c['styles'])!=25:raise ValueError('Expected approved gallery catalog')
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 (out/'renderer-preflight.json').write_text(json.dumps({'status':'passed','catalog':str(CATALOG),'catalog_sha256':sha(CATALOG),'style_count':25,'host':'112','mac_required':False},indent=2));return c

def choose(out,source_sha,catalog):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 with (out/'style.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  p=out/'style-choice.json'
  if p.exists():
   r=json.loads(p.read_text())
   if r['source_sha256']!=source_sha or r['catalog_sha256']!=sha(CATALOG):raise ValueError('Existing style receipt source/catalog mismatch; do not redraw')
   return r
  from tracer_style_assignment import assign
  assignment=assign(source_sha,catalog['styles'],catalog['version'])
  style=next(s for s in catalog['styles'] if s['id']==assignment['style_id'])
  r={'source_sha256':source_sha,'catalog_sha256':sha(CATALOG),'version':catalog['version'],'style':style,'selected_at':assignment['selected_at'],'assignment':assignment,'retry_policy':'reuse same style'}
  p.write_text(json.dumps(r,indent=2));return r

def module(arc,w,h,style):
 code=pathlib.Path(style['renderer']).read_text();ns={'__file__':style['renderer'],'arc':arc}
 exec(compile(code,style['renderer'],'exec'),ns)
 ns.update(W=w,H=h,arc=arc,rows=app_draw.smooth(arc));app_draw.SETTINGS['tailSeconds']=1.4
 if 'fontpath' in ns:ns['font']=ImageFont.truetype(ns['fontpath'],round((21 if 'reference' in style['family'] else 15)*w/750*ns['SS']*1.8))
 return ns

def overlay(ns,t,k,end,w,h,impact):
 trail=ns['overlay'](t,k,False)
 if impact and 0<=t-end<.65:
  saved=ns['rows'];ns['rows']=[]
  try:burst=ns['overlay'](end+(t-end)*.45/.65,k,True)
  finally:ns['rows']=saved
  cx,cy=np.asarray(ns['arc']['points'][-1])*[w,h];scale=1.4
  burst=burst.transform((w,h),Image.Transform.AFFINE,(1/scale,0,cx*(1-1/scale),0,1/scale,cy*(1-1/scale)),Image.Resampling.BICUBIC)
  burst.putalpha(burst.getchannel('A').point(lambda a:min(255,round(a*1.3))))
  trail=Image.alpha_composite(trail,burst)
 return trail

def measured_jobs(root,source):
 # Same accepted make and identity evidence as the existing daily renderer.
 work=pathlib.Path(json.loads((root/'people/result.json').read_text())['final_work']);rows=json.loads((work/'owner_identity/assignments.json').read_text())
 duration=float(json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(source)]))['format']['duration'])-.08
 overrides=json.loads((root/'clip-overrides.json').read_text()) if (root/'clip-overrides.json').exists() else {}
 jobs=[]
 for r in rows:
  if r.get('result')!='make':continue
  ev=evidence_for(root,r)
  if ev is None:continue
  folder,local=ev
  path=json.loads((folder/f'attack_defense_owner_full_v8_r2/ball_backtrack_{local:02}.json').read_text())['path']
  balls=[json.loads(l) for l in (folder/'ball_control_full_v2/trace.jsonl').read_text().splitlines()]
  points={int(b['frame']):b['xy'] for b in path if not b.get('human',{}).get('reject') and b.get('score',0)>=.15}
  for f in range(r['attempt_frame'],min(len(balls),r['result_frame']+1)):
   b=balls[f].get('observed_ball')
   if b and b.get('score',0)>=.15:points[f]=b['xy']
  lo=min([r['attempt_frame']]+list(points));start=max(0,lo/25-1);end=min(duration,r['result_frame']/25+.7)
  o=overrides.get(str(r['number']),{});start=max(start,o.get('start',start));end=min(end,o.get('end',end))
  times=[];xy=[]
  rise=(r.get('rise') or {}).get('frame')
  if rise is None:continue
  for f,p in sorted(points.items()):
   if f>=rise and f/25>=float(o.get('flight_start_seconds',0)) and start<=f/25<=min(end,r['result_frame']/25) and np.isfinite(p).all() and 0<=p[0]<=720 and 0<=p[1]<=1280:times.append(f/25);xy.append([p[0]/720,p[1]/1280])
  if len(times)<4 or end<=start:continue
  # No fabricated rim anchor; burst only when final measured ball is near detected rim.
  impact=False
  trace=root/'native-input/native/frame_trace.jsonl'
  hoops=[json.loads(l).get('active') for l in trace.read_text().splitlines()]
  idx=min(len(hoops)-1,r['result_frame']);hoop=hoops[idx]
  if hoop:
   x,y,bw,bh=hoop['box'];impact=bool(abs(x+bw/2-xy[-1][0]*720)<=max(20,bw) and abs(y+bh/2-xy[-1][1]*1280)<=max(25,bh*2) and abs(times[-1]-r['result_frame']/25)<.2)
  jobs.append({'number':r['number'],'clipStart':start,'clipEnd':end,'arc':{'times':times,'points':xy},'impact_verified':impact,'evidence':str(folder),'event_frame':r['result_frame'],'analysis_fps':25})
 if not jobs:raise ValueError('No accepted measured made-shot arcs')
 return jobs

def render(root,source,out=None):
 root=pathlib.Path(root).resolve();source=pathlib.Path(source).resolve();out=pathlib.Path(out) if out else root/'app-export'
 from source_quality import require_review
 require_review(source)
 c=preflight(out);source_sha=sha(source)
 if (out/'qa.json').exists():
  old=json.loads((out/'qa.json').read_text());p=pathlib.Path(old['export_path'])
  if p.exists() and sha(p)==old['sha256'] and old.get('source_sha256')==source_sha:return old
  raise ValueError('Existing export receipt mismatch; no overwrite')
 choice=choose(out,source_sha,c);style=choice['style'];jobs=measured_jobs(root,source)
 (out/'measured-style-jobs.json').write_text(json.dumps({'source_sha256':source_sha,'jobs':jobs},indent=2))
 clips=[];w,h=1080,1920;started=time.monotonic()
 for j in jobs:
  start,end=j['clipStart'],j['clipEnd'];frames=int((end-start)*30);ns=module(j['arc'],w,h,style)
  silent=out/f'style-{j["number"]}-silent.mp4'
  dec=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-ss',str(start),'-i',str(source),'-an','-vf','scale=1080:1920,fps=30','-frames:v',str(frames),'-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE)
  enc=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r','30','-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p',str(silent)],stdin=subprocess.PIPE)
  try:
   for n in range(frames):
    raw=dec.stdout.read(w*h*3)
    if len(raw)!=w*h*3:raise ValueError('Source EOF')
    im=Image.frombytes('RGB',(w,h),raw).convert('RGBA');t=start+n/30
    im=Image.alpha_composite(im,overlay(ns,t,style['index'],j['arc']['times'][-1],w,h,j['impact_verified'])).convert('RGB')
    enc.stdin.write(im.tobytes())
    if n in [round(((j['arc']['times'][0]+j['arc']['times'][-1])/2-start)*30),round((j['arc']['times'][-1]+.1-start)*30)]:im.save(out/f'shot-{j["number"]}-frame-{n}.jpg')
   enc.stdin.close();dec.stdout.close()
   if enc.wait()!=0 or dec.wait()!=0:raise ValueError('Video render failed')
  except BaseException:enc.kill();dec.kill();enc.wait();dec.wait();raise
  target=out/f'shot-{j["number"]}.mp4'
  info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(source)]))
  if any(s['codec_type']=='audio' for s in info['streams']):ff(['-i',silent,'-ss',start,'-t',frames/30,'-i',source,'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-ar','48000','-ac','2','-shortest',target])
  else:ff(['-i',silent,'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-shortest',target])
  clips.append(target)
 concat=out/'style-concat.txt';concat.write_text(''.join(f"file '{p}'\n" for p in clips));cut=out/'style-cut.mp4';ff(['-f','concat','-safe','0','-i',concat,'-c','copy',cut]);final=out/(source.stem+'-hoopcut.mp4')
 ff(['-i',cut,'-i',ASSET,'-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-filter_complex','[0:v]setsar=1,setpts=PTS-STARTPTS[v0];[0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS[a0];[1:v]setsar=1,setpts=PTS-STARTPTS[v1];[2:a]atrim=duration=3,asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]','-map','[v]','-map','[a]','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',final]);ff(['-i',final,'-f','null','-'])
 qa=dict(status='rendered_visual_review_pending',source_path=str(source),source_sha256=source_sha,export_path=str(final),sha256=sha(final),style=style['id'],style_receipt=str(out/'style-choice.json'),tracer='112 measured paths + gallery V3 style',outro_sha256=sha(ASSET),decode='passed',visual_review='pending',upload_status='not_uploaded',shots=len(jobs),render_seconds=time.monotonic()-started)
 (out/'qa.json').write_text(json.dumps(qa,indent=2));print(json.dumps(qa),flush=True);return qa
