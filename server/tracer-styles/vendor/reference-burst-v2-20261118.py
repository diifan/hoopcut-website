"""Isolated real-footage visual iteration; reuses website cached measured arc.
No inference, production writes or synthetic events. Impact time explicitly visual-only.
"""
from pathlib import Path
import sys,json,math,subprocess,time,hashlib
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path('/data/swi-algo/Swi-App-Factory/Hoopcut/shot-tracer-runtime')

import app_draw
app_draw.SETTINGS['tailSeconds']=.8

rows=app_draw.smooth(arc)
OUT=Path(__file__).parent; W,H=1280,720; SS=2
PALETTES=[('#63ff8c','#e7fff0'),('#ff651d','#fff0a3'),('#69dfff','#efffff'),('#37b8ff','#f1faff'),('#28e6ca','#ff8550'),('#e83933','#fff1d2')]
NAMES=['Green Release','Heat Check','Ice Cold','Voltage','Street Ink','Court Manga']
fontpath='/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf'
font=ImageFont.truetype(fontpath,round(21*(W/750*1.8)*SS))
def rgba(col,a):return tuple(bytes.fromhex(col.lstrip('#')))+(round(255*max(0,min(1,a))),)
def impact_v2(kind,elapsed):
 canvas=Image.new('RGBA',(W*SS,H*SS));unit=(W/750*1.8)
 if not 0<=elapsed<.45:return canvas
 p=elapsed/.45;ease=1-(1-p)**3;fade=min(1,p*15)*(1-p)**.65
 center=np.asarray(arc['points'][-1])*[W,H];ink,accent=PALETTES[kind]
 def layer():return Image.new('RGBA',canvas.size)
 def compose(im):
  nonlocal canvas
  canvas=Image.alpha_composite(canvas,im)
 def stroke(im,pts,col,w,a):
  ImageDraw.Draw(im).line([tuple(np.asarray(q)*SS) for q in pts],fill=rgba(col,a),width=max(1,round(w*unit*SS)),joint='curve')
 def polygon(im,pts,col,a):ImageDraw.Draw(im).polygon([tuple(np.asarray(q)*SS) for q in pts],fill=rgba(col,a))
 def ellipse(im,c,rx,ry,col,a,width=0):
  box=((c[0]-rx)*SS,(c[1]-ry)*SS,(c[0]+rx)*SS,(c[1]+ry)*SS)
  d=ImageDraw.Draw(im)
  if width:d.ellipse(box,outline=rgba(col,a),width=max(1,round(width*unit*SS)))
  else:d.ellipse(box,fill=rgba(col,a))
 def ring(im,r,col,a,flat=.35,w=1.8):
  stroke(im,[center+np.array([math.cos(t)*r,math.sin(t)*r*flat]) for t in np.linspace(0,math.tau,81)],col,w,a)
 # Localized soft flash; no full-frame flashing. Composite glow behind vector detail.
 glow=layer();ellipse(glow,center,(16+ease*18)*unit,(8+ease*12)*unit,ink,fade*.65)
 compose(glow.filter(ImageFilter.GaussianBlur(7*unit*SS)))
 detail=layer()
 if kind==0:
  ring(detail,(10+ease*40)*unit,ink,fade,w=2.5)
  ring(detail,(5+ease*29)*unit,accent,fade*.85,w=1.4)
  for j in range(14):
   angle=j*math.tau/14;v=np.array([math.cos(angle),math.sin(angle)*.4]);q=center+v*(10+ease*42)*unit
   q+=np.array([0,-math.sin(p*math.pi)*(5+j%3*3)*unit])
   stroke(detail,[q,q+np.array([0,-(3+3*(1-p))*unit])],accent if j%3==0 else ink,1.4,fade)
 elif kind==1:
  # Curled, tapered flame ribbons, with asynchronous tips and brighter internal tongues.
  for j in range(9):
   theta=j*math.tau/9;v=np.array([math.cos(theta),math.sin(theta)*.65]);n=np.array([-v[1],v[0]])
   length=(18+ease*(22+j%3*6))*unit
   spine=[center+v*length*u+n*math.sin(u*5+p*7+j)*unit*9*u+np.array([0,-p*p*12*unit*u]) for u in np.linspace(0,1,22)]
   widths=[(1-u)**.7*(4+3*math.sin(u*math.pi))*unit for u in np.linspace(0,1,22)]
   left=[q+n*w for q,w in zip(spine,widths)];right=[q-n*w for q,w in zip(spine,widths)]
   polygon(detail,left+right[::-1],ink,fade*.9)
   stroke(detail,spine[:16],accent,1.8,fade*.85)
  ring(detail,(8+ease*38)*unit,ink,fade*.8,w=1.2)
  for j in range(18):
   a=j*2.399;v=np.array([math.cos(a),math.sin(a)]);q=center+v*(12+ease*(25+j%5*5))*unit+np.array([0,-p*15*unit])
   stroke(detail,[q,q-v*unit*(2+3*(1-p))],accent,1,fade)
 elif kind==2:
  # Rotating asymmetric ice facets leave the center clear, falling as they disperse.
  for j in range(15):
   a=j*2.399;v=np.array([math.cos(a),math.sin(a)*.7]);q=center+v*(8+ease*(22+j%4*7))*unit+np.array([0,p*p*16*unit]);ang=a+p*(1 if j%2 else -1)*2
   axis=np.array([math.cos(ang),math.sin(ang)]);normal=np.array([-axis[1],axis[0]]);r=(3+j%4)*(1-.45*p)*unit
   pts=[q-axis*r*1.4,q+normal*r*.55,q+axis*r,q-normal*r*.35]
   polygon(detail,pts,ink,fade*.8);polygon(detail,[pts[0],q,pts[1]],accent,fade)
   stroke(detail,[pts[0],pts[2]],accent,.7,fade)
  ring(detail,(5+ease*40)*unit,accent,fade*.55,w=1)
  for j in range(8):
   a=j*math.tau/8;q=center+np.array([math.cos(a),math.sin(a)*.4])*(10+ease*20)*unit
   stroke(detail,[q+[-2*unit,0],q+[2*unit,0]],accent,.8,fade)
   stroke(detail,[q+[0,-2*unit],q+[0,2*unit]],accent,.8,fade)
 elif kind==3:
  bolts=layer()
  for j in range(9):
   a=j*math.tau/9+.12*math.sin(p*8);v=np.array([math.cos(a),math.sin(a)*.65]);n=np.array([-v[1],v[0]]);r=(20+ease*35)*unit
   pts=[center+v*r*u+n*math.sin(k*2.7+j+int(p*7))*unit*5*u for k,u in enumerate(np.linspace(.1,1,8))]
   stroke(bolts,pts,ink,4,fade*.55);stroke(detail,pts,accent,1.1,fade)
   for k in (3,5):stroke(detail,[pts[k],pts[k]+n*unit*8+v*unit*3,pts[k]+n*unit*12+v*unit*10],ink,.9,fade)
  compose(bolts.filter(ImageFilter.GaussianBlur(unit*SS*1.5)))
 else:
  r=(14+ease*26)*unit
  pts=[]
  for j in range(22):
   a=j*math.tau/22;length=r*((.85+.18*math.sin(j*3.1)) if j%2==0 else .5)
   pts.append(center+np.array([math.cos(a)*length,math.sin(a)*length*.7]))
  stroke(detail,pts+[pts[0]],'#171514',4,fade);polygon(detail,pts,ink,fade)
  stroke(detail,pts+[pts[0]],accent,1.2,fade)
  for j in range(14):
   a=j*2.399;v=np.array([math.cos(a),math.sin(a)*.7]);q=center+v*(28+ease*28)*unit
   stroke(detail,[q,q+v*unit*(5+j%4)],accent if j%2 else ink,1.3,fade)
  # Typography pops quickly, then drifts a little; no stationary detached title.
  label='SWISH!' if kind==4 else 'CLUTCH!';fs=round((17+5*min(1,p*7))*unit*SS)
  f=ImageFont.truetype(fontpath,fs);pos=center+np.array([12,-25-p*7])*unit
  ImageDraw.Draw(detail).text(tuple(pos*SS),label,font=f,fill=rgba(accent,fade),stroke_width=round(unit*SS*1.5),stroke_fill=rgba('#171514',fade))
 compose(detail)
 return canvas

def overlay(t,kind,burst=True):
 im=Image.new('RGBA',(W*SS,H*SS));d=ImageDraw.Draw(im);ink,accent=PALETTES[kind];unit=(W/750*1.8)
 def line(ps,w,col,alpha=1):d.line([tuple(np.asarray(p)*SS) for p in ps],fill=rgba(col,alpha),width=max(1,round(w*SS)),joint='curve')
 def poly(ps,col,alpha=1):d.polygon([tuple(np.asarray(p)*SS) for p in ps],fill=rgba(col,alpha))
 def ring(c,r,col,alpha=1,flat=.45):
  line([c+np.array([math.cos(a)*r,math.sin(a)*r*flat]) for a in np.linspace(0,math.tau,65)],2*unit,col,alpha)
 tail=app_draw.tail(rows,t);samples=tail[::max(1,math.ceil(len(tail)/96))]
 last=None
 for i in range(1,len(samples)):
  birth,p=samples[i];prev,q=samples[i-1]
  if birth-prev>.16:continue
  a=q*[W,H];b=p*[W,H];delta=b-a;n=np.array([-delta[1],delta[0]])/max(.001,np.linalg.norm(delta));age=max(0,t-birth);fresh=max(0,1-age/1.4);alpha=fresh**1.2;phase=birth*35;bucket=math.floor(birth*24);w=unit*(2+4*fresh)
  if kind==0:
   line([a,b],w*2.2,ink,alpha*.18);line([a,b],w,ink,alpha);line([a,b],w*.3,accent,alpha)
  elif kind==1:
   line([a,b],w*1.8,ink,alpha*.3);line([a,b],w,ink,alpha);line([a,b],w*.35,accent,alpha)
   tip=b+n*(math.sin(phase)*unit*(5+14*age))+np.array([0,-age*22*unit]);poly([a,b,tip],ink,alpha*.7)
  elif kind==2:
   line([a,b],w*1.7,ink,alpha*.18);line([a,b],w*.65,accent,alpha)
   line([a+n*3*unit,b+n*3*unit],unit,ink,alpha)
  elif kind==3:
   m=(a+b)/2+n*math.sin(bucket*2.4)*unit*5
   line([a,m,b],w*2,ink,alpha*.22);line([a,m,b],unit*2,accent,alpha)
   if bucket%3==0:line([m,m+n*unit*8,m+n*unit*12-delta*.2],unit,ink,alpha)
  elif kind==4:
   line([a,b],w*1.7,'#111719',alpha);line([a,b],w,ink,alpha);line([a+n*w*.6,b+n*w*.6],unit*1.5,accent,alpha)
  else:
   line([a,b],w*1.8,'#151111',alpha);line([a,b],w,ink,alpha);line([a-n*w*.35,b-n*w*.35],unit*1.3,accent,alpha)
   if bucket%2==0:line([a+n*unit*9-delta*.5,b+n*unit*9],unit*.8,accent,alpha*.6)
  if bucket==last:continue
  last=bucket
  drift=b+n*(1 if bucket%2 else -1)*unit*(4+age*12)+np.array([0,age*age*18*unit]);r=unit*(1+2*fresh)
  if kind==2:poly([drift+[-r,0],drift+[0,-r*2],drift+[r,0],drift+[0,r*2]],ink,alpha)
  elif kind==1:line([drift,drift+[unit*2,-unit*5]],unit,accent,alpha)
  elif kind in (4,5):line([drift,drift+n*unit*3],unit*1.4,accent,alpha)
 if burst:im=Image.alpha_composite(im,impact_v2(kind,t-arc['times'][-1]))
 return im.resize((W,H),Image.Resampling.LANCZOS)
