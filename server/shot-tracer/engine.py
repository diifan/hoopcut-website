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

def analyze(source,work,hoop=None):
 import time
 started=time.monotonic()
 code=(AGENT/'app/analyze_short.py').read_text()
 old=' from source_quality import require_review\n quality=require_review(a.source)'
 assert old in code
 code=code.replace(old," quality={'scope':'web_upload','duration_gate_seconds':30}")
 start=code.index(' if a.dynamic_scene:')
 end=code.index(" sdk=base/'delivery_copy'",start)
 native=code[code.index(" run([sys.executable,base/'code/run_native.py']",start):end]
 if hoop is None:
  replacement=" status.update(status='selection_ready');(root/'status.json').write_text(json.dumps(status))\n"
 else:
  (work.parent/'selected-hoop.json').write_text(json.dumps(hoop))
  replacement=""" chosen=json.loads((root.parent/'selected-hoop.json').read_text())
 cap=cv2.VideoCapture(str(base/'input/input_3min.mp4'));count=int(cap.get(7));cap.release()
 assert 0<=chosen['frame']<count
 metadata=dict(video=str(base/'input/input_3min.mp4'),frames=count,fps=25,rim=chosen['rim'],rim_score=chosen['score'],rim_source='user_confirmed_detector_candidate',reference_frame=chosen['frame'])
 (base/'input/selected_scene.json').write_text(json.dumps(metadata))
 shutil.copy2(Path(__file__).parent/'selected_scene.py',base/'code/selected_scene.py')
 q=base/'code/run_native.py';t=q.read_text();t=t.replace('from run_hc_half_persistent_overlay import PersistentHalfScene','from selected_scene import SelectedHoopScene')
 t=t.replace("PersistentHalfScene(ROOT/'input/automatic_half_scene_metadata.json',args.video,cap)","SelectedHoopScene(ROOT/'input/selected_scene.json',args.video,cap)");q.write_text(t)
"""+native+" status.update(status='native_ready');(root/'status.json').write_text(json.dumps(status))\n"
 code=code[:start]+replacement+code[code.index('\ndef eval_fraction',end):]
 assert 'run_adaptive' not in code and "root/'people'" not in code
 import shutil
 shutil.copy2(Path(__file__).with_name('selected_scene.py'),work.parent/'selected_scene.py')
 adapter=work.parent/'analyze-makemiss-only.py';adapter.write_text(code)
 env=dict(os.environ,PYTHONPATH=str(AGENT/'app')+os.pathsep+os.environ.get('PYTHONPATH',''))
 with (work.parent/'inference.log').open('w') as log:
  subprocess.run([sys.executable,str(adapter),'--source',str(source),'--work',str(work),'--evidence-only'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
 native_seconds=time.monotonic()-started
 status=json.loads((work/'status.json').read_text())
 libs=[str(p) for root in ['/data/envs/swi-crawler-research/lib/python3.10/site-packages/nvidia','/data/swi-algo/hc-external-gt/runtime/nvidia','/data/envs/torch-cu130/lib/python3.10/site-packages/nvidia'] for p in Path(root).glob('*/lib')]
 env['LD_LIBRARY_PATH']=':'.join(libs)+':'+env.get('LD_LIBRARY_PATH','')
 if hoop is None:
  subprocess.run([sys.executable,str(Path(__file__).with_name('hoop_candidates.py')),str(work/'native-input')],env=env,check=True,timeout=180)
  return {'selection':json.loads((work/'native-input/hoop-candidates.json').read_text())}
 if status['status']=='no_make_candidates':arcs=[]
 else:
  libs=[str(p) for root in ['/data/envs/swi-crawler-research/lib/python3.10/site-packages/nvidia','/data/swi-algo/hc-external-gt/runtime/nvidia','/data/envs/torch-cu130/lib/python3.10/site-packages/nvidia'] for p in Path(root).glob('*/lib')]
  env['LD_LIBRARY_PATH']=':'.join(libs)+':'+env.get('LD_LIBRARY_PATH','')
  subprocess.run([sys.executable,str(Path(__file__).with_name('tracer_only.py')),str(work)],env=env,check=True,timeout=180)
  arcs=json.loads((work.parent/'measured-arcs.json').read_text())
 (work.parent/'measured-arcs.json').write_text(json.dumps(arcs))
 (work/'pipeline-receipt.json').write_text(json.dumps({'pipeline':'makemiss+tracer','people_analysis':False,'native_seconds':native_seconds,'analysis_seconds':time.monotonic()-started,'arcs':len(arcs)}))
 return arcs

def draw(frame,time,arcs,effect):
 arcs=[arc for arc in arcs if arc['times'][0]<=time<=arc['times'][-1]+.18]
 if not arcs:return frame
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
 enc=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r','30','-i','pipe:0','-an','-c:v','h264_nvenc','-preset','p4','-cq','26','-pix_fmt','yuv420p',str(silent)],stdin=subprocess.PIPE)
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
