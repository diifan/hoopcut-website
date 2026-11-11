"""Expose real detector candidates for explicit choice; no stable-cluster fallback."""
import ast,json,hashlib,sys
from pathlib import Path
import cv2,numpy as np

def detect(root):
    native=Path('/data/swi-algo/hc-external-gt/results/shot_trigger_native_v1')
    sys.path[:0]=[str(root/'code'),str(native)]
    from runtime_checked import CheckedGPU
    out=root/'scene_init';out.mkdir(exist_ok=True)
    source=root/'input/input_3min.mp4';cap=cv2.VideoCapture(str(source))
    n=int(cap.get(7));w,h=int(cap.get(3)),int(cap.get(4));fps=cap.get(5)
    if n<1 or fps!=25:raise ValueError('Invalid reference sampling')
    module=ast.parse((native/'test_new_video.py').read_text())
    funcs=[f for f in module.body if isinstance(f,ast.FunctionDef) and f.name in ('prep','find_rim')]
    find=next(f for f in funcs if f.name=='find_rim')
    # Keep original detector/decoder, return candidates before temporal cluster gate.
    stop=next(i for i,node in enumerate(find.body) if isinstance(node,ast.If) and ast.unparse(node.test)=='not boxes')
    find.body=find.body[:stop]+[ast.Return(value=ast.Name(id='boxes',ctx=ast.Load()))]
    models={}
    def session(name):
        if name not in models:models[name]=CheckedGPU(name,'/data/swi-algo/hc-external-gt/models',out)
        return models[name]
    scope={'cv2':cv2,'np':np,'json':json,'session':session}
    exec(compile(ast.fix_missing_locations(ast.Module(body=funcs,type_ignores=[])),str(native/'test_new_video.py'),'exec'),scope)
    rows=scope['find_rim'](cap,n,w,h,out);cap.release()
    candidates=[]
    for frame in sorted({r[0] for r in rows}):
        kept=[]
        for row in sorted((r for r in rows if r[0]==frame),key=lambda r:-r[1]):
            if any(np.linalg.norm(np.array(row[2:4])-np.array(r[2:4]))<max(8,min(row[4],r[4])*.6) for r in kept):continue
            kept.append(row)
            if len(kept)==8:break
        for row in kept:
            fi,score,cx,cy,bw,bh=row
            ident=hashlib.sha256(json.dumps(row).encode()).hexdigest()[:24]
            candidates.append({'id':ident,'frame':fi,'time':fi/25,'box':[(cx-bw/2)/w,(cy-bh/2)/h,bw/w,bh/h], 'rim':[cx,cy,bw,bh],'score':score})
    result={'version':1,'width':w,'height':h,'frames':n,'fps':fps,'candidates':candidates,
            'selection_policy':'explicit_user_confirmation_even_single_candidate'}
    (root/'hoop-candidates.json').write_text(json.dumps(result))
    return result
if __name__=='__main__':detect(Path(sys.argv[1]))
