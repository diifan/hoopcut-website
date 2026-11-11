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
  start,end=task['trim'];effect=task['effect'];key=hashlib.sha256(json.dumps([start,end,'makemiss-tracer-v2']).encode()).hexdigest()
  work=root/key;work.mkdir(exist_ok=True)
  if not (work/'measured-arcs.json').exists():
   stage('trimming',5);engine.trim(root/'source',work/'trim.mp4',start,end)
   if (work/'analysis').exists():shutil.rmtree(work/'analysis')
   stage('tracking',15);arcs=engine.analyze(work/'trim.mp4',work/'analysis')
  else:arcs=json.loads((work/'measured-arcs.json').read_text())
  if not arcs:finish({'state':'no_shots'})
  else:
   stage('rendering',70);output=root/'result.mp4'
   receipt=engine.render(work/'trim.mp4',output,arcs,effect,lambda p:stage('rendering',70+int(29*p)))
   receipt.update(size_bytes=output.stat().st_size,model_version='hoopcut-makemiss-tracer-v2',renderer_version='web-v1')
   finish({'state':'ready','render':receipt})
except Exception as e:
 import traceback;traceback.print_exc();finish({'state':'failed','error_code':'invalid_video' if task['operation']=='probe' else 'processing_failed','error_type':type(e).__name__})
