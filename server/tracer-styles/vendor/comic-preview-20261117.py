"""Isolated real-footage visual iteration; reuses website cached measured arc.
No inference, production writes or synthetic events. Impact time explicitly visual-only.
"""
from pathlib import Path
import sys,json,math,subprocess,time,hashlib
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/data/swi-algo/Swi-App-Factory/Hoopcut/shot-tracer-runtime')

import app_draw
app_draw.SETTINGS['tailSeconds']=.5

rows=app_draw.smooth(arc)
OUT=Path(__file__).parent; W,H=1280,720; SS=2
PALETTES=[('#ff218b','#ffcf35'),('#16c8eb','#d3ffff'),('#ff700a','#ffe5a5'),('#f5edce','#fff9e7')]
NAMES=['Comic Pop','Splash Brush','Comet Ink','Manga Swish']
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf'
font=ImageFont.truetype(fontpath,round(15*(W/750*1.8)*SS))
def polygon(d,ps,fill,outline=None,width=1):
 q=[(round(x*SS),round(y*SS)) for x,y in ps];d.polygon(q,fill=fill)
 if outline:d.line(q+[q[0]],fill=outline,width=max(1,round(width*SS)),joint='curve')
def particle(d,p,r,kind,a,color):
 def pt(x,y):return(p[0]+math.cos(a)*x-math.sin(a)*y,p[1]+math.sin(a)*x+math.cos(a)*y)
 if kind==0:d.ellipse(((p[0]-r)*SS,(p[1]-r)*SS,(p[0]+r)*SS,(p[1]+r)*SS),fill=color)
 elif kind==1:
  # Teardrop contour (same flat vector primitive as native renderer).
  ps=[pt(0,-2*r)]+[pt(math.sin(t)*r,math.cos(t)*r) for t in np.linspace(-math.pi/2,math.pi/2,12)]+[pt(0,-2*r)]
  polygon(d,ps,color)
 else:polygon(d,[pt(0,-2*r),pt(r,r),pt(-r,r)],color)
def overlay(t,kind,burst=True):
 im=Image.new('RGBA',(W*SS,H*SS));d=ImageDraw.Draw(im);ink,accent=PALETTES[kind];width=10*(W/750*1.8)
 tail=app_draw.tail(rows,t)
 if len(tail)>1:
  runs=[]
  for row in tail:
   if runs and row[0]-runs[-1][-1][0]<=.16:runs[-1].append(row)
   else:runs.append([row])
  for run in runs:
   if len(run)<2:continue
   run=run[::max(1,math.ceil(len(run)/96))];ps=np.array([p*[W,H] for _,p in run]);left=[];right=[]
   for i,p in enumerate(ps):
    delta=ps[min(len(ps)-1,i+1)]-ps[max(0,i-1)];normal=np.array([-delta[1],delta[0]])/max(.001,np.linalg.norm(delta));u=i/(len(ps)-1);half=width*(.12+.88*u**.65)*(max(.18,(1-u)/.15) if u>.85 else 1)/2
    left.append(p+normal*half);right.append(p-normal*half)
   def rgba(color,alpha):return tuple(bytes.fromhex(color.lstrip('#')))+(round(255*alpha),)
   for i in range(1,len(ps)):
    freshness=max(0,min(1,1-(t-run[i][0])/1.4))**2
    polygon(d,[left[i-1],left[i],right[i],right[i-1]],rgba(ink,freshness))
    d.line([tuple(left[i-1]*SS),tuple(left[i]*SS)],fill=rgba(accent,freshness),width=max(1,round(width*.19*SS)))
   last_bucket=None
   for birth,point in run:
    bucket=math.floor(birth*18)
    if bucket==last_bucket:continue
    last_bucket=bucket;age=max(0,t-birth);fresh=max(0,1-age/1.4);side=1 if bucket%2==0 else -1;p=point*[W,H]
    center=(p[0]+side*width*(.3+age*2),p[1]+side*width*.5+age*age*width*8)
    particle(d,center,max(.5,width*.25*fresh),kind,bucket*.8+age*side*2,rgba(accent if bucket%2==0 else ink,fresh*fresh))
 elapsed=t-arc['times'][-1]
 # Visual-only timing uses measured arc end. Not asserted to be a verified made event.
 if burst and 0<=elapsed<.45:
  phase=elapsed/.45;scale=(W/750*1.8);c=np.array(arc['points'][-1])*[W,H];layer=Image.new('RGBA',im.size);b=ImageDraw.Draw(layer)
  if kind in (0,2):
   r=(12+phase*15)*scale;ps=[(c[0]+math.cos(i*math.pi/8)*r*(1 if i%2==0 else .42),c[1]+math.sin(i*math.pi/8)*r*(1 if i%2==0 else .42)) for i in range(16)];polygon(b,ps,accent,ink,2*scale)
  for i in range(8):
   a=i*math.pi/4-math.pi/2;r=(12+phase*28)*scale;p=(c[0]+math.cos(a)*r,c[1]+math.sin(a)*r+phase**2*10*scale)
   particle(b,p,(3.5-phase*2)*scale,kind,a+math.pi/2,ink if i%2==0 else accent)
  if kind in (0,3):b.text(((c[0]+20*scale)*SS,(c[1]-32*scale)*SS),'SWISH!' if kind==0 else 'BUCKET!',font=font,fill=accent,stroke_width=round(scale*SS),stroke_fill='black')
  layer.putalpha(layer.getchannel('A').point(lambda a:round(a*min(1,phase*10)*(1-phase))))
  im=Image.alpha_composite(im,layer)
 return im.resize((W,H),Image.Resampling.LANCZOS)
