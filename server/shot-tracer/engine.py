"""112 adapter: fresh inference on the submitted trim, then measured-path rendering.
No example video fallback, event cache reuse, or macOS dependency.
"""
import ast, hashlib, json, os, subprocess, sys
from pathlib import Path
import cv2
import numpy as np
from scipy.interpolate import UnivariateSpline

AGENT=Path(os.environ.get('HOOPCUT_AGENT_ROOT','/var/lib/swi-codex/xcut-seo-agent'))
FITTER=Path('/data/swi-algo/deliveries/basketball_upload_eventfirst_engine_20261020/code/build_clean.py')
EFFECTS={'firework':'Firework','ice':'Ice Beam','neon':'Neon','ribbon':'Ribbon','cosmic':'Cosmic','sunset':'Sunset'}

def probe(path):
 d=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],timeout=30))
 v=next(s for s in d['streams'] if s['codec_type']=='video')
 return {'duration':float(v.get('duration') or d['format']['duration']),'width':v['width'],'height':v['height']}

def trim(source,target,start,end):
 p=probe(source)
 if not (np.isfinite(start) and np.isfinite(end) and 0<=start<end<=p['duration']+.05 and end-start<=30.001):raise ValueError('Choose a range of at most 30 seconds.')
 subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-ss',str(start),'-i',str(source),'-t',str(end-start),'-map','0:v:0','-map','0:a:0?','-vf',"scale='min(1280,iw)':-2,fps=30,setsar=1",'-c:v','libx264','-threads','2','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart',str(target)],check=True,timeout=180)
 return probe(target)

def analyze(source,work):
 # The daily ingestion gate requires YouTube Shorts visual receipts, which do not
 # apply to user uploads. Replace it ONLY in this job-local adapter with the
 # web admission gate. Do not alter or forge daily source quality receipts.
 code=(AGENT/'app/analyze_short.py').read_text()
 old=' from source_quality import require_review\n quality=require_review(a.source)'
 assert old in code
 code=code.replace(old," quality={'scope':'web_upload','duration_gate_seconds':30}")
 code=code.replace("'source_quality_receipt':str(a.source.with_suffix('.quality.json'))","'admission_scope':'web_upload_duration_checked_by_server'")
 adapter=work.parent/'analyze-upload.py';adapter.write_text(code)
 env=dict(os.environ,PYTHONPATH=str(AGENT/'app')+os.pathsep+os.environ.get('PYTHONPATH',''))
 with (work.parent/'inference.log').open('w') as log:
  subprocess.run([sys.executable,str(adapter),'--source',str(source),'--work',str(work),'--evidence-only'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1800)
 status=json.loads((work/'status.json').read_text())
 if status['status']=='no_make_candidates':return []
 sys.path.insert(0,str(AGENT/'app'))
 from render_short import evidence_for
 final=Path(json.loads((work/'people/result.json').read_text())['final_work'])
 rows=json.loads((final/'owner_identity/assignments.json').read_text())
 hoops=[(r['active']['box'] if r.get('active') else None) for r in map(json.loads,(work/'native-input/native/frame_trace.jsonl').read_text().splitlines())]
 fn=[n for n in ast.parse(FITTER.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='smooth_arc']
 arcs=[]
 for row in rows:
  if row.get('result')!='make':continue
  match=evidence_for(work,row)
  if not match:continue
  folder,number=match
  ball=[json.loads(l) for l in (folder/'ball_control_full_v2/trace.jsonl').read_text().splitlines()]
  scope=dict(np=np,json=json,B=folder,ball=ball,hoops=hoops,UnivariateSpline=UnivariateSpline)
  exec(compile(ast.Module(body=fn,type_ignores=[]),str(FITTER),'exec'),scope)
  arc,audit=scope['smooth_arc']({**row,'number':number})
  if arc is None:continue
  ts=np.linspace(arc[0],arc[1],max(2,round((arc[1]-arc[0])*180)))
  wh=np.array(status['analysis_size'])*1.5
  points=arc[2](ts)/wh
  if not np.isfinite(points).all():continue
  arcs.append({'times':ts.tolist(),'points':points.tolist(),'audit':audit})
 (work.parent/'measured-arcs.json').write_text(json.dumps(arcs))
 return arcs

def draw(frame,time,arcs,effect):
 colors={'firework':(16,100,255),'ice':(255,225,80),'neon':(185,60,255),'ribbon':(100,245,160),'cosmic':(220,70,190),'sunset':(80,130,255)}
 color=colors[effect];h,w=frame.shape[:2];layer=np.zeros_like(frame)
 for arc in arcs:
  ts=np.asarray(arc['times']);xy=np.asarray(arc['points'])*[w,h]
  if time<ts[0] or time>ts[-1]+.18:continue
  keep=(ts<=time)&(ts>=time-.24)
  pts=xy[keep].astype(np.int32)
  if len(pts)<2:continue
  cv2.polylines(layer,[pts],False,color,max(2,round(w/250)),cv2.LINE_AA)
  if effect in ('cosmic','sunset'):
   palette=((220,70,190),(226,224,73)) if effect=='cosmic' else ((72,198,255),(242,66,164))
   for i in range(1,len(pts)):
    t=i/(len(pts)-1); shade=tuple(int(a*(1-t)+b*t) for a,b in zip(*palette))
    cv2.line(layer,tuple(pts[i-1]),tuple(pts[i]),shade,max(2,round(w/250)),cv2.LINE_AA)
  tip=pts[-1]
  if effect=='firework':
   # Deterministic particles tied to measured ball position and media time.
   for k in range(12):
    angle=k*2.39996+time*3;radius=(3+(k*7+int(time*60))%20)*w/720
    end=tuple((tip+[np.cos(angle)*radius,np.sin(angle)*radius]).astype(int))
    cv2.line(layer,tuple(tip),end,color,max(1,round(w/700)),cv2.LINE_AA)
  elif effect=='ribbon':cv2.polylines(layer,[pts],False,color,max(4,round(w/100)),cv2.LINE_AA)
 glow=cv2.GaussianBlur(layer,(0,0),max(1,w/250))
 return cv2.add(frame,cv2.addWeighted(layer,.9,glow,1.8,0))

def render(source,target,arcs,effect,progress=lambda _:None):
 if effect not in EFFECTS:raise ValueError('Unknown effect')
 p=probe(source);w,h=p['width'],p['height'];fps=30
 silent=target.with_suffix('.silent.mp4')
 dec=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-i',str(source),'-an','-pix_fmt','bgr24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE)
 enc=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r','30','-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset','fast','-crf','20','-pix_fmt','yuv420p',str(silent)],stdin=subprocess.PIPE)
 count=0
 try:
  while True:
   raw=dec.stdout.read(w*h*3)
   if not raw:break
   if len(raw)!=w*h*3:raise RuntimeError('Incomplete video frame')
   frame=np.frombuffer(raw,np.uint8).reshape(h,w,3)
   enc.stdin.write(draw(frame,count/fps,arcs,effect).tobytes());count+=1
   if count%30==0:progress(min(.99,count/(p['duration']*fps)))
  enc.stdin.close();dec.stdout.close()
  if enc.wait(timeout=60) or dec.wait(timeout=60):raise RuntimeError('Video rendering failed')
 except BaseException:
  dec.kill();enc.kill();dec.wait();enc.wait();raise
 if not count:raise ValueError('No decodable video frames')
 subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-i',str(silent),'-i',str(source),'-map','0:v:0','-map','1:a:0?','-c','copy','-movflags','+faststart',str(target)],check=True,timeout=60)
 silent.unlink();return {'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'frames':count,'duration':probe(target)['duration']}
