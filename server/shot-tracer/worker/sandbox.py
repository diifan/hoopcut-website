"""Explicit read-only inference dependencies; no relay, credentials or host home."""
from pathlib import Path
APP=Path(__file__).resolve().parent
READONLY=[
 '/data/swi-algo/hc-external-gt/results/motion_contract_20260925_round9/hc_evidence/cvlib',
 '/data/envs/torch-cu130',
 '/data/envs/swi-crawler-research/lib/python3.10/site-packages/nvidia',
 '/data/swi-algo/hc-external-gt/app/09_离线管线/hc_evidence/cvlib',
 '/data/swi-algo/hc-external-gt/models','/data/swi-algo/hc-external-gt/runtime',
 '/data/swi-algo/hc-external-gt/results/shot_trigger_native_v1',
 '/data/swi-algo/hc-external-gt/results/motion_contract_20260925_round8/hc_evidence',
 '/data/swi-algo/hc-external-gt/results/player_identity_review_20260927/code',
 '/data/swi-algo/hc-external-gt/results/dji_v3_smallroi_review_20260927/delivery_copy',
 '/data/swi-algo/deliveries/basketball_upload_eventfirst_engine_20261020/code',
 '/data/swi-algo/deliveries/dji_pose34_standalone_20260927',
 '/data/swi-algo/cloud/hoopcut-cloud-worker_20261021/raw_code',
 '/data/swi-algo/cloud/hoopcut-cloud-worker_20261021/snapshot',
 '/data/swi-algo/cloud/hoopcut-cloud-worker_20261021/profiling',
 '/var/lib/swi-codex/xcut-seo-agent/app',
 '/var/tmp/swi-algo-pauljamison_000_300_20261020/delivery_copy',
 '/var/tmp/swi-algo-ball-reid-review-20261009/calibration',
]
def command(folder):
 folder=folder.resolve()
 if folder.parent.name!='jobs' or len(folder.name)!=48:raise ValueError('invalid job directory')
 cmd=['bwrap','--unshare-all','--die-with-parent','--new-session','--cap-drop','ALL','--ro-bind','/usr','/usr','--symlink','usr/bin','/bin','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64','--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache','--ro-bind','/etc/alternatives','/etc/alternatives','--proc','/proc','--dev','/dev','--tmpfs','/tmp']
 for path in READONLY:
  if Path(path).exists():cmd+=['--ro-bind',str(Path(path).resolve()),path]
 worker=Path('/data/swi-algo/cloud/hoopcut-cloud-worker_20261021')
 for f in worker.glob('*.py'):cmd+=['--ro-bind',str(f),str(f)]
 cmd+=['--ro-bind',str(APP),'/hc-app','--bind',str(folder),str(folder),'--chdir',str(folder),'--clearenv','--setenv','PATH','/data/envs/torch-cu130/bin:/usr/bin:/bin','--setenv','HOME','/tmp','--setenv','OMP_NUM_THREADS','2','--setenv','OPENBLAS_NUM_THREADS','1','--setenv','CUDA_VISIBLE_DEVICES','0','--setenv','PYTHONUNBUFFERED','1','--setenv','YOLO_CONFIG_DIR','/tmp/yolo']
 for name in ['nvidia0','nvidiactl','nvidia-uvm','nvidia-uvm-tools']:
  p=Path('/dev')/name
  if p.exists():cmd+=['--dev-bind',str(p),str(p)]
 return cmd+['/data/envs/torch-cu130/bin/python','/hc-app/compute.py',str(folder)]
