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
PALETTES=[('#ff8c1f','#ffeba6'),('#8026d9','#e0adff'),('#0dccf2','#e6ffff'),('#33e6ff','#ff80e0'),('#40454d','#d9e0e6'),('#00f2ff','#ff26bf')]
NAMES=['Arcane Spark','Kinetic Pulse','Plasma Jet','Prism Shards','Ink Smoke','Holo Glitch']
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
def rgba(color,alpha):return tuple(bytes.fromhex(color.lstrip('#')))+(round(255*max(0,min(1,alpha))),)
def overlay(t,kind,burst=True):
 im=Image.new('RGBA',(W*SS,H*SS));d=ImageDraw.Draw(im);primary,accent=PALETTES[kind];unit=(W/750*1.8);width=10*unit
 def line(a,b,w,color,alpha):d.line([tuple(np.asarray(a)*SS),tuple(np.asarray(b)*SS)],fill=rgba(color,alpha),width=max(1,round(w*SS)))
 tail=app_draw.tail(rows,t);last_bucket=None
 if len(tail)>1:
  samples=tail[::max(1,math.ceil(len(tail)/96))]
  if samples[-1][0]!=tail[-1][0]:samples.append(tail[-1])
  for i in range(1,len(samples)):
   prev,point=samples[i-1],samples[i]
   if point[0]-prev[0]>.16:continue
   a=prev[1]*[W,H];b=point[1]*[W,H];age=max(0,t-point[0]);fresh=max(0,1-age/1.4);alpha=fresh**.8
   delta=b-a;length=max(.001,np.linalg.norm(delta));tangent=delta/length;normal=np.array([-delta[1],delta[0]])/length;bucket=math.floor(point[0]*24);phase=point[0]*30
   def off(p,x):return p+normal*x
   if kind==0:
    line(a,b,width*1.5,primary,alpha*.28);line(a,b,width*.3,primary,alpha);line(a,b,width*.18,accent,alpha)
   elif kind==1:
    line(a,b,width,primary,alpha*.35);line(a,b,width*.4,primary,alpha)
    line(off(a,math.sin(phase)*width*.4),off(b,math.sin(phase+.2)*width*.4),width*.15,accent,alpha*.8)
   elif kind==2:
    for w,al,col in [(1.8,.25,primary),(1,.45,primary),(.45,.8,primary),(.16,1,accent)]:line(a,b,width*w,col,alpha*al)
    line(off(a,math.sin(phase)*width*.6),off(b,math.sin(phase+.2)*width*.6),width*.12,accent,alpha*.55)
   elif kind==3:line(a,b,width*.35,accent,alpha*.8)
   elif kind==4:
    for strand in range(3):
     p=phase*.55+strand*2.1+age*4;spread=width*(.3+age*2)
     line(off(a,math.sin(p)*spread),off(b,math.sin(p+.15)*spread),width*(.3+age),primary,alpha*.32)
     line(off(a,math.sin(p)*spread),off(b,math.sin(p+.15)*spread),width*.18,accent,alpha*.45)
   elif bucket%5!=0:
    line(off(a,-width*.22),off(b,-width*.22),width*.18,primary,alpha);line(off(a,width*.22),off(b,width*.22),width*.15,accent,alpha*.9)
   if bucket==last_bucket:continue
   last_bucket=bucket;side=1 if bucket%2==0 else -1;drift=width*age*4;p=b+normal*side*drift+np.array([0,age*age*width*6])
   if kind in (1,3):
    r=width*(.8 if kind==3 else .3)*fresh
    polygon(d,[p-tangent*r,p+normal*r*.65,p+tangent*r*1.4],rgba(primary if bucket%2==0 else accent,alpha))
    line(p,p+tangent*r,max(.5,unit),'#ffffff',alpha*.75)
   elif kind in (0,5):line(p,p+np.array([width if kind==5 else side*width*.35,0 if kind==5 else width*.5]),max(.7,unit),accent,alpha)
 elapsed=t-arc['times'][-1]
 if burst and 0<=elapsed<.45:
  phase=elapsed/.45;c=np.array(arc['points'][-1])*[W,H];alpha=min(1,phase*10)*(1-phase)**.7;r=(16+phase*38)*unit
  def ring(radius,col,broken):
   for i in range(100):
    if broken and i%5>=3:continue
    a=i*math.tau/100;b=(i+1)*math.tau/100
    line(c+np.array([math.cos(a)*radius,math.sin(a)*radius*.48]),c+np.array([math.cos(b)*radius,math.sin(b)*radius*.48]),unit*2.4,col,alpha)
  if kind==0:ring(r,primary,True);ring(r*.7,accent,True)
  elif kind==1:ring(r,primary,False);ring(r*.8,accent,False)
  elif kind==5:ring(r,primary,True);ring(r*.85,accent,True)
  elif kind==4:
   for j in range(3):ring(r*(.65+j*.15),accent if j==1 else primary,True)
  def at(x,y):return c+np.array([x,y])*unit
  def stroke(pts,col,w=2):
   for a,b in zip(pts,pts[1:]):line(a,b,w*unit,col,alpha)
  reach=18+phase*48
  for i in range(16):
   angle=i*math.pi/8;dx=math.cos(angle);dy=math.sin(angle);color=primary if i%2==0 else accent
   if kind==0:
    a=angle+phase*.8;x=math.cos(a)*reach;y=math.sin(a)*reach*.55
    stroke([at(x-3,y),at(x+3,y)],color,1.5);stroke([at(x,y-4),at(x,y+4)],color,1.5)
    if i%2==0:stroke([at(dx*reach*.65,dy*reach*.36),at(dx*reach*.85,dy*reach*.47)],accent)
   elif kind==1 and i%2==0:
    r1=reach*(1+(i%3)*.12)
    stroke([at(dx*r1,dy*r1*.6),at(dx*(r1+12),dy*(r1+12)*.6)],color,3)
    stroke([at(dx*r1-dy*4,dy*r1*.6+dx*4),at(dx*r1+dy*4,dy*r1*.6-dx*4)],accent,1)
   elif kind==2:
    x=(i-7.5)*4;height=(16+phase*44)*(.6+abs(math.sin(i*2.1))*.6)
    stroke([at(x*.25,5),at(x*.7,-height*.5),at(x+math.sin(phase*9+i)*5,-height)],color,2.3)
    if i%3==0:stroke([at(x*.25,5),at(x*.7,-height*.5)],'#ffffff',1)
   elif kind==3:
    r1=reach*(.7+(i%3)*.22);p=at(dx*r1,dy*r1*.65+phase*phase*20)
    particle(d,p,(5+i%3-phase*2)*unit,2,angle+phase*3,rgba(color,alpha))
    stroke([p,p-np.array([dx,dy])*7*unit],'#ffffff',.8)
   elif kind==4 and i<8:
    pts=[]
    for j in range(13):
     t=j/12;a=angle*2+t*1.7+phase;r1=reach*(.25+t*.65);pts.append(at(math.cos(a)*r1,math.sin(a)*r1*.55-phase*18))
    stroke(pts,primary,5);stroke(pts,accent,1.3)
   elif kind==5 and i<8:
    y=(i-3.5)*8;x=math.sin(i*4+math.floor(phase*12))*reach*.4
    stroke([at(x-reach*.45,y),at(x+reach*.45,y)],color,3 if i%2==0 else 1)
  if kind==1:ring(r*1.35,accent,True)
  if kind==5:
   r1=reach*.85
   for sx in [-1,1]:
    for sy in [-1,1]:stroke([at(sx*(r1-10),sy*r1*.65),at(sx*r1,sy*r1*.65),at(sx*r1,sy*(r1*.65-10))],accent)

 return im.resize((W,H),Image.Resampling.LANCZOS)
