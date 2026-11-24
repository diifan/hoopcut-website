"""Shared, pinned 25-style gallery renderer. Input arcs must be measured.
No impact burst is inferred from the end of a track. Rendering is stateless
across jobs; a renderer instance owns its per-arc style namespaces.
"""
from pathlib import Path
import importlib.util,json,sys
import numpy as np
from PIL import Image,ImageFont
ROOT=Path(__file__).parent
CATALOG=json.loads((ROOT/'catalog.json').read_text())
STYLES={s['id']:s for s in CATALOG['styles']}
spec=importlib.util.spec_from_file_location('gallery_app_draw',ROOT/'vendor/app_draw.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
class Renderer:
 def __init__(self,arcs,width,height,style):
  self.w,self.h=width,height;self.style=STYLES[style];self.modules=[]
  for arc in arcs:
   if len(arc.get('times',[]))<2:continue
   path=ROOT/self.style['renderer'];ns={'__file__':str(path),'arc':arc}
   code=path.read_text().replace('import app_draw','app_draw = _gallery_helper')
   ns['_gallery_helper']=helper;exec(compile(code,str(path),'exec'),ns)
   ns.update(W=width,H=height,arc=arc,rows=helper.smooth(arc));helper.SETTINGS['tailSeconds']=1.4
   if 'fontpath' in ns:ns['font']=ImageFont.truetype(ns['fontpath'],round((21 if 'reference' in self.style['family'] else 15)*width/750*ns['SS']*1.8))
   self.modules.append(ns)
 def overlay(self,t):
  im=Image.new('RGBA',(self.w,self.h))
  for ns in self.modules:
   times=ns['arc']['times']
   if t<times[0] or t>times[-1]+1.4:continue
   im=Image.alpha_composite(im,ns['overlay'](t,self.style['index'],False))
  return im
 def draw(self,frame,t):
  original=Image.fromarray(np.ascontiguousarray(frame[:,:,::-1])).convert('RGBA')
  return np.asarray(Image.alpha_composite(original,self.overlay(t)).convert('RGB'))[:,:,::-1].copy()
