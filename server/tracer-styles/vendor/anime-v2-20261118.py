"""Isolated real-footage visual iteration; reuses website cached measured arc.
No inference, production writes or synthetic events. Impact time explicitly visual-only.
"""
from pathlib import Path
import sys,json,math,subprocess,time,hashlib
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/data/swi-algo/Swi-App-Factory/Hoopcut/shot-tracer-runtime')

import app_draw
app_draw.SETTINGS['tailSeconds']=.8

rows=app_draw.smooth(arc)
OUT=Path(__file__).parent; W,H=1280,720; SS=2
PALETTES=[('#e92d44','#fff4df'),('#eae7d9','#343536'),('#fff9e9','#b7e8e7'),('#171819','#fff7e3'),('#e72c3c','#fff1d9')]
NAMES=['Red Drive','Ace Afterimage','Pure Swish','Manga Ink','Clutch Impact']
def rgba(col,a):return tuple(bytes.fromhex(col.lstrip('#')))+(round(255*max(0,min(1,a))),)
def overlay(t,kind,burst=True):
 im=Image.new('RGBA',(W*SS,H*SS));d=ImageDraw.Draw(im);ink,accent=PALETTES[kind];unit=(W/750*1.8)
 def line(ps,w,col,alpha=1):d.line([tuple(np.asarray(p)*SS) for p in ps],fill=rgba(col,alpha),width=max(1,round(w*SS)),joint='curve')
 def poly(ps,col,alpha=1):d.polygon([tuple(np.asarray(p)*SS) for p in ps],fill=rgba(col,alpha))
 tail=app_draw.tail(rows,t);samples=tail[::max(1,math.ceil(len(tail)/96))];last=None
 for i in range(1,len(samples)):
  birth,p=samples[i];prev,q=samples[i-1]
  if birth-prev>.16:continue
  a=q*[W,H];b=p*[W,H];delta=b-a;n=np.array([-delta[1],delta[0]])/max(.001,np.linalg.norm(delta));age=max(0,t-birth);fresh=max(0,1-age/1.4);alpha=fresh**1.05;w=unit*(1.1+2.5*fresh);bucket=math.floor(birth*24)
  if kind==0:
   line([a,b],w*1.8,'#282126',alpha*.75);line([a,b],w,ink,alpha)
   line([a+n*unit*3,b+n*unit*3],unit*1.1,accent,alpha)
  elif kind==1:
   for offset,al in [(-9,.18),(-6,.28),(-3,.5),(0,1)]:
    shift=n*unit*(offset-age*7);line([a+shift,b+shift],unit*1.2,ink,alpha*al)
   line([a-n*unit,b-n*unit],unit*.7,accent,alpha*.7)
  elif kind==2:
   line([a,b],w*1.9,'#35494a',alpha*.35);line([a,b],unit*1.6,ink,alpha)
  elif kind==3:
   # Flat ink edged in paper white; short dry-brush gaps on the secondary stroke.
   line([a,b],w*2.2,accent,alpha);line([a,b],w*1.2,ink,alpha)
   if bucket%4!=0:line([a+n*unit*4,b+n*unit*4],unit*.8,ink,alpha*.75)
  else:
   line([a,b],w*2.7,'#292126',alpha);line([a,b],w*1.6,ink,alpha)
   line([a+n*unit*3,b+n*unit*3],unit*1.3,accent,alpha)
   line([a-n*unit*4,b-n*unit*4],unit*.7,accent,alpha*.55)
  if bucket!=last and kind in (0,3,4):
   last=bucket;sign=1 if bucket%2 else -1;pos=b+n*sign*unit*(5+age*8)
   line([pos-delta*(1.4+age*2),pos],unit*.8,accent,alpha*.7)
   if kind in (3,4):line([pos+n*sign*unit*3-delta*1.5,pos+n*sign*unit*3],unit*.55,ink,alpha*.5)
 elapsed=t-arc['times'][-1]
 if burst and 0<=elapsed<.45:
  p=elapsed/.45;ease=1-(1-p)**3;al=min(1,p*15)*(1-p)**.8;c=np.asarray(arc['points'][-1])*[W,H]
  def ring(r,col,opacity,flat=.28):line([c+np.array([math.cos(a)*r,math.sin(a)*r*flat]) for a in np.linspace(0,math.tau,65)],unit,col,opacity)
  # Secondary expanding slash wave: delayed, asymmetric, short-lived.
  delay=max(0,(p-.16)/.84);a2=min(1,delay*10)*(1-delay)**1.2
  if kind!=2 and a2>0:
   for j in range(9):
    angle=j*2.399+.16;v=np.array([math.cos(angle),math.sin(angle)*.6]);n=np.array([-v[1],v[0]])
    r=(18+(1-(1-delay)**2)*(18+j%3*5))*unit;q=c+v*r
    length=(4+j%4*2)*(1-delay*.5)*unit
    poly([q-n*unit*.7,q+v*length,q+n*unit*.7],ink if j%3 else accent,a2*.8)
  if kind==2:
   # A narrow net-like downward fan instead of a broad explosion.
   ring((8+ease*15)*unit,ink,al)
   if a2>0:
    ring((6+delay*12)*unit,accent,a2*.7)
    for j in range(4):
     q=c+np.array([(j-1.5)*unit*5,(14+delay*18)*unit]);line([q,q+[0,unit*3]],unit*.7,ink,a2*.65)
   for j in range(7):
    x=(j-3)*unit*3;top=c+np.array([x,0]);end=c+np.array([x*.4,(7+ease*21)*unit]);mid=(top+end)/2+np.array([math.sin(j+p*5)*unit*1.5,0])
    line([top,mid,end],unit*.8,ink,al*.8)
  else:
   count=10 if kind==0 else 16 if kind==1 else 20 if kind==3 else 16
   for j in range(count):
    a=j*math.tau/count+.08*math.sin(j*3);v=np.array([math.cos(a),math.sin(a)*.75]);r=(9+ease*(16+j%4*3))*unit
    start=c+v*r;end=c+v*(r+(5+j%3*4)*(1-.3*p)*unit)
    if kind in (3,4):
     n=np.array([-v[1],v[0]]);poly([start-n*unit*.8,end,start+n*unit*.8],accent,al)
     line([start,end],unit*.6,ink,al)
    else:line([start,end],unit*(1 if kind==0 else .65),ink if j%3 else accent,al)
   ring((8+ease*17)*unit,accent,al*.7)
   if kind in (0,4) and p<.3:
    hit=math.sin(p/.3*math.pi)*.7
    line([c+[-9*unit,0],c+[9*unit,0]],unit*1.1,accent,hit)
    line([c+[0,-6*unit],c+[0,6*unit]],unit*.8,accent,hit)
   if kind==4:
    # Small red cross-hit, not a caption or a persistent star badge.
    r=(7+ease*7)*unit
    ps=[c+np.array([math.cos(j*math.pi/4),math.sin(j*math.pi/4)])*r*(1 if j%2==0 else .25) for j in range(8)]
    poly(ps,ink,al);line(ps+[ps[0]],unit*.8,accent,al)
 return im.resize((W,H),Image.Resampling.LANCZOS)
