"""Preview-only bounded Python smoke test; NOT a Shot Tracer performance result."""
from http.server import BaseHTTPRequestHandler
import hashlib,json,os,time,sys
class handler(BaseHTTPRequestHandler):
 def do_GET(self):
  if os.environ.get('VERCEL_ENV')!='preview':
   self.send_response(404);self.end_headers();return
  start=time.perf_counter();data=b'HoopCut-preview-test'*4096
  for _ in range(128):digest=hashlib.sha256(data).hexdigest()
  body=json.dumps({'scope':'preview_python_smoke_only','environment':'preview','python':sys.version.split()[0],'bounded_cpu_ms':round((time.perf_counter()-start)*1000,3),'checksum':digest,'inference_executed':False,'production_data_accessed':False}).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('X-Robots-Tag','noindex, nofollow');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
