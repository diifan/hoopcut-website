"""Contract regression: hoop selection must not invalidate the identical trim."""
import json, runpy, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch

class TrimReuse(unittest.TestCase):
 def test_range_reused_but_hoop_analysis_not_reused(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);calls=[]
   def trim(source,target,start,end):calls.append(('trim',start,end));target.write_bytes(b'exact-trim')
   def analyze(source,work,hoop):
    calls.append(('analyze',hoop));work.mkdir();return {'selection':{'candidates':[]}} if hoop is None else [{'times':[0,1]}]
   def render(source,out,arcs,effect,progress):out.write_bytes(b'render');return {}
   engine=types.SimpleNamespace(probe=lambda _:dict(duration=25,width=640,height=360),trim=trim,analyze=analyze,render=render)
   for start,hoop in [(0,None),(0,{'id':'a'}),(1,{'id':'a'}),(1,{'id':'b'})]:
    (root/'task.json').write_text(json.dumps(dict(operation='render',trim=[start,20],effect='firework',hoop=hoop)))
    with patch.dict(sys.modules,engine=engine),patch.object(sys,'argv',['compute.py',str(root)]):runpy.run_path(str(Path(__file__).with_name('compute.py')),run_name='__main__')
    self.assertNotEqual(json.loads((root/'result.json').read_text())['state'],'failed')
   self.assertEqual(sum(c[0]=='trim' for c in calls),2)
   self.assertEqual(sum(c[0]=='analyze' for c in calls),4)
   self.assertEqual(json.loads((root/'result.json').read_text())['render']['renderer_version'],'web-nvenc-v2')
if __name__=='__main__':unittest.main()
