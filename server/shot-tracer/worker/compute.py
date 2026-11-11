"""No-network child. Only this job directory is writable."""
import json,sys,hashlib,time,shutil
from pathlib import Path
import engine
root=Path(sys.argv[1]);task=json.loads((root/'task.json').read_text());t=time.monotonic()
def stage(name,progress):
 p=root/'progress.tmp';p.write_text(json.dumps({'stage':name,'progress':progress}));p.replace(root/'progress.json')
def finish(result):
 result['elapsed_seconds']=round(time.monotonic()-t,3);(root/'result.json').write_text(json.dumps(result))
try:
 stage('probing',5);video=engine.probe(root/'source')
 if not (0<video['duration']<=3600 and 0<video['width']<=7680 and 0<video['height']<=7680):raise ValueError('invalid_video')
 if task['operation']=='probe':finish({'state':'imported','video':video})
 else:
  start,end=task['trim'];effect=task['effect'];key=hashlib.sha256(json.dumps([start,end,'makemiss-tracer-selected-v3',task.get('hoop')]).encode()).hexdigest()
  work=root/key;work.mkdir(exist_ok=True)
  if not (work/'measured-arcs.json').exists():
   stage('trimming',5)
   # A confirmed hoop changes analysis, not the source range. Reuse the exact
   # encoded trim from preflight; never reuse arcs across different hoops.
   range_key=hashlib.sha256(json.dumps([start,end,'trim-x264-v1']).encode()).hexdigest()
   shared=root/('trim-'+range_key+'.mp4')
   if not shared.exists():
    temporary=shared.with_suffix('.part.mp4');engine.trim(root/'source',temporary,start,end);temporary.replace(shared)
   if not (work/'trim.mp4').exists():
    import os
    os.link(shared,work/'trim.mp4')
   if (work/'analysis').exists():shutil.rmtree(work/'analysis')
   stage('tracking',15);arcs=engine.analyze(work/'trim.mp4',work/'analysis',task.get('hoop'))
  else:arcs=json.loads((work/'measured-arcs.json').read_text())
  if isinstance(arcs,dict):finish({'state':'needs_hoop','selection':arcs['selection']})
  elif not arcs:finish({'state':'no_shots'})
  else:
   stage('rendering',70);output=root/'result.mp4'
   receipt=engine.render(work/'trim.mp4',output,arcs,effect,lambda p:stage('rendering',70+int(29*p)))
   receipt.update(size_bytes=output.stat().st_size,model_version='hoopcut-makemiss-tracer-selected-v3',renderer_version='web-nvenc-v2')
   finish({'state':'ready','render':receipt})
except Exception as e:
 import traceback;traceback.print_exc();finish({'state':'failed','error_code':'invalid_video' if task['operation']=='probe' else 'processing_failed','error_type':type(e).__name__})
