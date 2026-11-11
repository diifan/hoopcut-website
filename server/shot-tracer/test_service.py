"""Isolated API contract checks; engine task mocked ONLY in these tests."""
import tempfile,os,unittest,json
from pathlib import Path
from unittest.mock import patch
os.environ['SHOT_TRACER_DATA']=tempfile.mkdtemp(prefix='hoopcut-tracer-test-')
from fastapi.testclient import TestClient
import service
class Contract(unittest.TestCase):
 def setUp(self):self.client=TestClient(service.app)
 def job(self):
  folder=service.ROOT/('a'*48);folder.mkdir(exist_ok=True);service.save(folder,stage='imported',video={'duration':50},renders={});return folder
 def test_invalid_media(self):self.assertEqual(self.client.post('/api/shot-tracer/jobs',content=b'bad').status_code,422)
 def test_trim_limit(self):
  self.job()
  for start,end in [(0,31),(-1,20),(20,15),(30,60),(0,float('inf'))]:
   raw=json.dumps({'start':start,'end':end,'effect':'firework'})
   self.assertEqual(self.client.post('/api/shot-tracer/jobs/'+'a'*48+'/process',content=raw,headers={'content-type':'application/json'}).status_code,422)
 def test_effect_allowlist(self):
  self.job();self.assertEqual(self.client.post('/api/shot-tracer/jobs/'+'a'*48+'/process',json={'start':0,'end':30,'effect':'../../source'}).status_code,422)
 def test_no_duplicate_work(self):
  self.job()
  with patch.object(service.pool,'submit') as submit:
   for _ in range(2):self.assertEqual(self.client.post('/api/shot-tracer/jobs/'+'a'*48+'/process',json={'start':0,'end':30,'effect':'firework'}).status_code,200)
   self.assertEqual(submit.call_count,1)
  service.active.clear()
 def test_locked_export_denied(self):
  folder=self.job();service.save(folder,renders={'ice':{'sha256':'test'}})
  self.assertEqual(self.client.get('/api/shot-tracer/jobs/'+'a'*48+'/media/ice?download=true').status_code,403)
 def test_same_file_preview_and_export(self):
  folder=self.job();(folder/'firework.mp4').write_bytes(b'test-rendered-file');service.save(folder,renders={'firework':{'sha256':'fixture'}})
  p='/api/shot-tracer/jobs/'+'a'*48+'/media/firework'
  self.assertEqual(self.client.get(p).content,self.client.get(p+'?download=true').content)
 def test_cross_origin(self):self.assertEqual(self.client.post('/api/shot-tracer/jobs',content=b'x',headers={'origin':'https://elsewhere.test'}).status_code,403)
 def test_bad_json_and_wrong_shape(self):
  self.job()
  url='/api/shot-tracer/jobs/'+'a'*48+'/process'
  for raw in ['{','null','[]','{"start":0,"end":10,"effect":[]}']:
   self.assertEqual(self.client.post(url,content=raw,headers={'content-type':'application/json'}).status_code,422)
 def test_reuses_completed_effect(self):
  folder=self.job();(folder/'firework.mp4').write_bytes(b'render')
  service.save(folder,trim=[0,20],renders={'firework':{'sha256':'test'}},stage='ready')
  with patch.object(service.pool,'submit') as submit:
   r=self.client.post('/api/shot-tracer/jobs/'+'a'*48+'/process',json={'start':0,'end':20,'effect':'firework'})
   self.assertEqual(r.json()['stage'],'ready');submit.assert_not_called()
 def test_expiry_uses_creation_not_last_poll(self):
  import time
  folder=self.job();service.save(folder,created_at=time.time()-service.TTL-1)
  self.assertEqual(self.client.get('/api/shot-tracer/jobs/'+'a'*48).status_code,404)
 def test_health(self):
  self.assertEqual(self.client.get('/api/shot-tracer/health').status_code,200)
 def test_no_paths_exposed(self):
  self.job();s=self.client.get('/api/shot-tracer/jobs/'+'a'*48).json();self.assertNotIn('source_sha256',s);self.assertNotIn('source',s)
if __name__=='__main__':unittest.main()
