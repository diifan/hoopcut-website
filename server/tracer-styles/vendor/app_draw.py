"""App drawing-contract adapter for Linux; OpenCV rasterization, not CoreGraphics.
Source contracts: Trajectory.presentationSmooth/tail, TracerRenderer.draw,
SampleProject/edit_project.json. Only the chosen palette may differ.
"""
from pathlib import Path
import sys,json,math
sys.path.insert(0,str(Path(__file__).parent/'vendor'))
import cv2
cv2.setNumThreads(1)
import numpy as np
SETTINGS=json.loads(Path(__file__).with_name('settings.json').read_text())
_CACHE={}
def smooth(arc):
    # Same run boundaries and four-pass robust quadratic as Trajectory.swift.
    t=np.asarray(arc['times'],dtype=float);p=np.asarray(arc['points'],dtype=float)
    valid=np.isfinite(t)&np.isfinite(p).all(axis=1)&(p>=0).all(axis=1)&(p<=1).all(axis=1)
    t,p=t[valid],p[valid];order=np.argsort(t,kind='stable');t,p=t[order],p[order]
    result=[]
    for indices in np.split(np.arange(len(t)),np.where(np.diff(t)>.16)[0]+1):
        if not len(indices):continue
        ts,ps=t[indices],p[indices]
        if len(ts)<5 or ts[-1]-ts[0]<=.001:
            result.extend(zip(ts,ps));continue
        u=(ts-ts[0])/(ts[-1]-ts[0]);weights=np.ones(len(ts));v=np.column_stack([np.ones(len(ts)),u,u*u])
        for _ in range(4):
            matrix=v.T@(weights[:,None]*v);rhs=v.T@(weights[:,None]*ps)
            if abs(np.linalg.det(matrix))<1e-15:break
            coefficients=np.linalg.solve(matrix,rhs)
            errors=np.linalg.norm(v@coefficients-ps,axis=1);median=np.sort(errors)[len(errors)//2];cutoff=max(.001,median*2.5)
            weights=np.minimum(1,cutoff/np.maximum(errors,1e-9))
        else:
            count=max(len(ts)-1,math.ceil((ts[-1]-ts[0])*120));q=np.linspace(0,1,count+1)
            xy=np.column_stack([np.ones(len(q)),q,q*q])@coefficients
            result.extend(zip(ts[0]+q*(ts[-1]-ts[0]),xy));continue
        result.extend(zip(ts,ps))
    return result

def tail(rows,time):
    if len(rows)<2 or not rows[0][0]<=time<=rows[-1][0]+.04:return []
    life=SETTINGS['tailSeconds'];ts=np.array([r[0] for r in rows]);out=[r for r in rows if time-life<=r[0]<=time]
    def interp(t):
        i=np.searchsorted(ts,t,side='right')
        if i==0 or i>=len(rows):return None
        a,b=rows[i-1],rows[i];dt=b[0]-a[0]
        if not 0<dt<=.16 or t<=a[0]:return None
        return (t,a[1]+(b[1]-a[1])*((t-a[0])/dt))
    edge,head=interp(time-life),interp(time)
    if edge is not None:out.insert(0,edge)
    if head is not None:out.append(head)
    return out

def overlay(width,height,time,arcs,effect):
    # Premultiplied float RGBA, bounded local rasterization, 3x edge supersampling.
    output=np.zeros((height,width,4),np.float32)
    stops=np.asarray(SETTINGS['palettes'][effect]);positions=SETTINGS['gradientLocations'];fade=SETTINGS['tailFade'];stroke=max(1.2,width/640*2)*SETTINGS['thickness']
    def over(dst,src):
        dst[:]=src+dst*(1-src[:,:,3:4])
    for arc in arcs:
        key=id(arc)
        if key not in _CACHE:_CACHE[key]=(arc,smooth(arc))
        rows=tail(_CACHE[key][1],time);runs=[]
        for t,p in rows:
            if runs and t-runs[-1][-1][0]<=.16:runs[-1].append((t,p))
            else:runs.append([(t,p)])
        for run in runs:
            if len(run)<2:continue
            ps=np.array([p for _,p in run])*[width,height];samples=[ps[0]]
            for i in range(1,len(ps)):
                start=samples[-1];control=ps[i]
                if i+1<len(ps):
                    end=(control+ps[i+1])/2
                    for step in range(1,9):
                        t=step/8;u=1-t;samples.append(u*u*start+2*u*t*control+t*t*end)
                else:samples.append(control)
            points=np.asarray(samples);dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))];progress=dist/max(.0001,dist[-1]);alphas=np.minimum(1,progress/fade)
            glow=stroke*4*SETTINGS['glowIntensity'];margin=int(math.ceil(glow*2+stroke*2+3))
            x0=max(0,int(np.floor(points[:,0].min()))-margin);y0=max(0,int(np.floor(points[:,1].min()))-margin)
            x1=min(width,int(np.ceil(points[:,0].max()))+margin);y1=min(height,int(np.ceil(points[:,1].max()))+margin)
            if x1<=x0 or y1<=y0:continue
            S=3;rw=(x1-x0)*S;rh=(y1-y0)*S;points=(points-[x0,y0])*S
            def fill(scale,white=False):
                before=np.vstack([points[0],points[:-1]]);after=np.vstack([points[1:],points[-1]])
                delta=after-before;length=np.maximum(.0001,np.linalg.norm(delta,axis=1));half=stroke*S*scale*(.12+.88*alphas)/2
                normal=np.column_stack([-delta[:,1],delta[:,0]])/length[:,None]*half[:,None];poly=np.vstack([points+normal,(points-normal)[::-1]])
                clip=np.zeros((rh,rw),np.uint8);cv2.fillPoly(clip,[np.rint(poly*16).astype(np.int32)],255,cv2.LINE_AA,shift=4)
                out=np.zeros((rh,rw,4),np.float32)
                for i in range(1,len(points)):
                    thick=max(1,round(stroke*S*scale*2));pad=thick+2
                    lo=np.floor(np.minimum(points[i-1],points[i])-pad).astype(int);hi=np.ceil(np.maximum(points[i-1],points[i])+pad+1).astype(int)
                    xx=max(0,lo[0]);yy=max(0,lo[1]);xe=min(rw,hi[0]);ye=min(rh,hi[1])
                    if xe<=xx or ye<=yy:continue
                    mask=np.zeros((ye-yy,xe-xx),np.uint8);a=tuple(np.rint((points[i-1]-[xx,yy])*16).astype(int));b=tuple(np.rint((points[i]-[xx,yy])*16).astype(int))
                    cv2.line(mask,a,b,255,thick,cv2.LINE_AA,shift=4)
                    cv2.circle(mask,a,max(1,round(thick*8)),255,-1,cv2.LINE_AA,shift=4);cv2.circle(mask,b,max(1,round(thick*8)),255,-1,cv2.LINE_AA,shift=4)
                    alpha=(mask.astype(np.float32)/255)*(clip[yy:ye,xx:xe].astype(np.float32)/255)*alphas[i]*(.65 if white else 1)
                    color=np.ones(3) if white else np.array([np.interp(progress[i],positions,stops[:,j]) for j in range(3)])
                    roi=out[yy:ye,xx:xe];roi[:,:,:3]=color*alpha[:,:,None]+roi[:,:,:3]*(1-alpha[:,:,None]);roi[:,:,3]=alpha+roi[:,:,3]*(1-alpha)
                return out
            body=fill(1);a=cv2.GaussianBlur(body[:,:,3],(0,0),max(.1,glow*S/2))*.7*min(1,SETTINGS['glowIntensity'])
            layer=np.zeros_like(body);layer[:,:,:3]=a[:,:,None]*stops[-1];layer[:,:,3]=a
            over(layer,body);over(layer,fill(.32,True));layer=cv2.resize(layer,(x1-x0,y1-y0),interpolation=cv2.INTER_AREA)
            over(output[y0:y1,x0:x1],layer)
    alpha=output[:,:,3:4];rgb=np.divide(output[:,:,:3],alpha,out=np.zeros_like(output[:,:,:3]),where=alpha>1e-8)
    return np.rint(np.concatenate([rgb,alpha],axis=2)*255).clip(0,255).astype(np.uint8)
def draw(frame,time,arcs,effect):
    if not any(len(a['times'])>=2 and a['times'][0]<=time<=a['times'][-1]+.04 for a in arcs):return frame
    h,w=frame.shape[:2];image=overlay(w,h,time,arcs,effect);a=image[:,:,3:4].astype(np.float32)/255
    return np.rint(image[:,:,:3][:,:,::-1]*a+frame*(1-a)).clip(0,255).astype(np.uint8)
