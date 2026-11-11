"""User-confirmed detector candidate, frozen at the matching analysis frame.
Coordinates are upright analysis pixels; never encoded track coordinates.
Uses the existing native hoop image tracker, not a new tracking algorithm.
"""
import json
from pathlib import Path
import cv2
import numpy as np
from hc_hoop_image_tracker import OriginalHoopImageTracker

class SelectedHoopScene:
    def __init__(self, metadata, video, cap):
        d=json.loads(Path(metadata).read_text())
        if d['rim_source']!='user_confirmed_detector_candidate':raise ValueError('Selection origin')
        if Path(d['video']).resolve()!=Path(video).resolve():raise ValueError('Selection source mismatch')
        if d['frames']!=int(cap.get(7)) or abs(d['fps']-cap.get(5))>1e-6:raise ValueError('Selection sampling mismatch')
        self.frame=int(d['reference_frame']);self.time=self.frame*1000/d['fps']
        cx,cy,w,h=d['rim'];self.box=[cx-w/2,cy-h/2,w,h];self.score=float(d['rim_score']);self.tracker=None
        if not np.isfinite(self.box).all() or min(w,h)<=0 or not 0<=self.score<=1:raise ValueError('Invalid detector candidate')
    def step(self,image,time_ms,**kwargs):
        if time_ms<self.time-.001:return {'active':None,'binding_diagnostic':{'scope':'before_user_selected_reference'}}
        gray=np.ascontiguousarray(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY))
        if self.tracker is None:
            if abs(time_ms-self.time)>.001:raise ValueError('Reference frame mismatch')
            self.tracker=OriginalHoopImageTracker(gray,self.box,self.score)
        r=self.tracker.step(gray)
        return {'active':{'box':r['compensated_box'],'reference_box':self.box,'reference_time':self.time,'id':[self.time,0],
            'flag':r['hoop_flag'],'affine':r['state']['hoop_affine'],'motion':r},
            'binding_diagnostic':{'scope':'user-selected candidate + original persistent hoop tracker','snapshot_id_used_as_reset':False}}
    def close(self):pass
