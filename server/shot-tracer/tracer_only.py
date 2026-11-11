"""Ball-only measured-flight tracer. No people, pose, ownership or identity models."""
import json, os, sys, time
from pathlib import Path
import cv2
import numpy as np
from scipy.interpolate import UnivariateSpline

def run(work):
    start=time.monotonic()
    code='/data/swi-algo/hc-external-gt/results/player_identity_review_20260927/code'
    sys.path.insert(0,code)
    libs=[str(p) for root in ['/data/envs/swi-crawler-research/lib/python3.10/site-packages/nvidia','/data/envs/torch-cu130/lib/python3.10/site-packages/nvidia','/data/swi-algo/hc-external-gt/runtime/nvidia'] for p in Path(root).glob('*/lib')]
    # Explicit preloading is needed when invoked from the networkless worker.
    import ctypes
    for name in ['libcublasLt.so.12','libcublas.so.12','libcudnn.so.9']:
        for lib in libs:
            if Path(lib,name).exists():
                ctypes.CDLL(str(Path(lib,name)),mode=ctypes.RTLD_GLOBAL);break
    from hc_ball_nn_provider_native import OriginalBallNNProvider
    from run_hc_dual_video_overlay import GPU
    cv2.setNumThreads(1)
    model=GPU('CoreMLBallDetector','/data/swi-algo/hc-external-gt/models',work,
              gpu_options={'use_tf32':'0','cudnn_conv_algo_search':'HEURISTIC'})
    detector=OriginalBallNNProvider(model.tensor)
    base=work/'native-input'
    traces=[json.loads(s) for s in (base/'native/frame_trace.jsonl').read_text().splitlines()]
    jobs=json.loads((base/'jobs.json').read_text())['jobs']
    cap=cv2.VideoCapture(str(base/'input/input_3min.mp4'))
    w,h=int(cap.get(3)),int(cap.get(4));arcs=[];audits=[]
    for job in jobs:
        ef=job['frame'];lo=max(0,ef-100);hi=min(len(traces)-1,job['callback_frame'],ef+10)
        cap.set(1,lo);images={}
        for f in range(lo,hi+1):
            ok,im=cap.read()
            if not ok:raise ValueError('Incomplete analysis frames')
            images[f]=im
        polys=[p for p in traces[ef]['candidate_polygons'] if p['selected'] and p['trajectory_id']==job['trajectory_id']]
        if not polys:
            audits.append({'request':job['source_request_number'],'status':'no_native_anchor'});continue
        cue=np.asarray(polys[0]['points']).mean(0)
        def detect(f,pred):
            x=int(np.clip(pred[0]-64,0,w-128));y=int(np.clip(pred[1]-64,0,h-128));out=[]
            for b in detector(cv2.cvtColor(images[f][y:y+128,x:x+128],cv2.COLOR_BGR2BGRA),False):
                bx,by,bw,bh=b['xywh'];d=(bw+bh)/2;q=np.array([x+bx+bw/2,y+by+bh/2])
                if not 4<=d<=48 or b['score']<.25 or b['ball_in_hand']:continue
                if np.linalg.norm(q-pred)>max(24,d*2):continue
                out.append(dict(frame=f,xy=q.tolist(),score=float(b['score']),diameter=float(d)))
            return min(out,key=lambda b:np.linalg.norm(np.array(b['xy'])-pred)) if out else None
        path=[];missing=0
        for f in range(ef,lo-1,-1):
            pred=cue.copy()
            if path:
                pred=np.array(path[-1]['xy'])
                if len(path)>=2:
                    samples=path[-6:];t=np.array([b['frame']-path[-1]['frame'] for b in samples]);xy=np.array([b['xy'] for b in samples])
                    cf=np.polyfit(t,xy,2 if len(samples)>=4 else 1)
                    if len(cf)==3:cf[0]=np.clip(cf[0],-1.5,1.5)
                    delta=np.polyval(cf,f-path[-1]['frame'])-pred
                    pred+=np.clip(delta,-35*(path[-1]['frame']-f),35*(path[-1]['frame']-f))
            # Native polygon is a crop proposal, never a rendered observation.
            native=[p for p in traces[f]['candidate_polygons'] if p['selected'] and p['trajectory_id']==job['trajectory_id']]
            if native and (not path or missing):pred=np.asarray(native[0]['points']).mean(0)
            b=detect(f,pred)
            if b:path.append(b);missing=0
            else:missing+=1
            if missing>6:break
        path.sort(key=lambda b:b['frame'])
        if len(path)>=5:
            measured=np.array([b['frame']-ef for b in path]);coords=np.array([b['xy'] for b in path]);cf=np.polyfit(measured,coords,2)
            for f in range(ef+1,hi+1):
                if f-path[-1]['frame']>3:break
                b=detect(f,np.polyval(cf,f-ef))
                if not b:continue
                path.append(b)
                active=traces[f].get('active')
                if active and b['xy'][1]>active['box'][1]+active['box'][3]*.8:break
        audit={'request':job['source_request_number'],'observations':path,'status':'insufficient_measured_flight'}
        if len(path)>=5:
            ff=np.array([b['frame'] for b in path]);xy=np.array([b['xy'] for b in path]);keep=np.ones(len(ff),bool)
            for _ in range(4):
                cf=np.polyfit(ff[keep]-ef,xy[keep],2);err=np.linalg.norm(xy-np.array([np.polyval(cf,f-ef) for f in ff]),axis=1)
                new=err<=max(8,float(np.median(err))*3)
                if new.sum()<5 or np.array_equal(new,keep):break
                keep=new
            accepted=[b for b,k in zip(path,keep) if k]
            # Keep the contiguous measured segment nearest the actual shot, not a held ball.
            groups=[]
            for b in accepted:
                if not groups or b['frame']-groups[-1][-1]['frame']>6:groups.append([])
                groups[-1].append(b)
            accepted=max(groups,key=len)
            if len(accepted)>=5:
                t=np.array([b['frame']/25 for b in accepted]);xy=np.array([b['xy'] for b in accepted]);weights=np.sqrt([b['score'] for b in accepted])
                q=np.linspace(t[0],t[-1],max(2,int(np.ceil((t[-1]-t[0])*180))+1))
                coords=np.column_stack([UnivariateSpline(t,xy[:,j],w=weights,s=len(t),k=3,ext=2)(q) for j in (0,1)])/[w,h]
                if np.isfinite(coords).all():
                    audit.update(status='smoothed_measured_arc',measured_frames=[b['frame'] for b in accepted],start_s=float(t[0]),end_s=float(t[-1]))
                    arcs.append({'times':q.tolist(),'points':coords.tolist(),'audit':{k:v for k,v in audit.items() if k!='observations'}})
        audits.append(audit)
    cap.release()
    (work/'tracer-only-audit.json').write_text(json.dumps({'pipeline':'makemiss+ball_detector+tracer','people_models':[],'ball_detector_calls':model.calls,'cuda_profile':model.profile,'seconds':time.monotonic()-start,'events':audits}))
    return arcs

if __name__=='__main__':
    work=Path(sys.argv[1]); (work.parent/'measured-arcs.json').write_text(json.dumps(run(work)))
