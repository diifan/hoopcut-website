"""Opt-in staging browser/BFF regression; no production traffic or real install."""
import asyncio,json,os,subprocess,socket,http.client,time
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
root=Path(__file__).resolve().parents[1]
origin='http://127.0.0.1:8264'
sock_path=f'/tmp/hoopcut-download-qa-{os.getpid()}.sock'
env={**os.environ,'PORT':'8264','HOOPCUT_PREVIEW_SOCKET':sock_path,'HOOPCUT_STAGING_SECRET_FILE':os.environ['HOOPCUT_STAGING_SECRET_FILE']}
server=subprocess.Popen(['node','server/attribution-preview.js'],cwd=root,env=env,stdout=subprocess.DEVNULL)
async def main():
 for _ in range(100):
  if Path(sock_path).exists():break
  await asyncio.sleep(.1)
 records=[];release=asyncio.Event();pv_pending=asyncio.Event();click_received=asyncio.Event()
 def proxy(req):
  conn=http.client.HTTPConnection('127.0.0.1',timeout=25);s=socket.socket(socket.AF_UNIX);s.settimeout(25);s.connect(sock_path);conn.sock=s
  u=urlsplit(req.url);headers={**req.headers,'host':'127.0.0.1:8264'}
  conn.request(req.method,u.path+('?' + u.query if u.query else ''),body=req.post_data,headers=headers)
  r=conn.getresponse();result=(r.status,dict(r.getheaders()),r.read());conn.close();return result
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path=os.environ.get('CHROME_EXECUTABLE','/var/lib/swi-codex/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome'),args=['--no-sandbox','--no-proxy-server'])
  ctx=await b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
  page=await ctx.new_page()
  async def bridge(route):
   if not route.request.url.startswith(origin):
    if route.request.url.startswith('https://apps.apple.com/'):
     await route.fulfill(status=200,content_type='text/html',body='<p>QA navigation target; no App Store request.</p>')
    else:await route.abort()
    return
   api='/api/analytics/events' in route.request.url
   data=route.request.post_data_json if api else None
   if api and any(e['event_name']=='page_view' for e in data['events']):
    pv_pending.set();await release.wait() # deterministic slow request, before real BFF forwarding
   status,headers,body=await asyncio.to_thread(proxy,route.request)
   if api:
    record={'status':status,'request':data,'response':json.loads(body),'at':time.time()};records.append(record)
    if any(e['event_name']=='download_clicked' for e in data['events']):click_received.set()
   headers.pop('Transfer-Encoding',None);headers.pop('Connection',None)
   try:await route.fulfill(status=status,headers=headers,body=body)
   except:pass # old document may already have navigated; captured BFF response remains evidence
  await ctx.route('**/*',bridge)
  try:
   await page.goto(origin+'/?utm_source=qa&utm_medium=integration&utm_campaign=mobile_delivery_hotfix_20261110',wait_until='domcontentloaded')
   await asyncio.wait_for(pv_pending.wait(),10)
   clicked=time.monotonic()
   await page.locator('[data-attribution-cta="hero_download"]').tap(no_wait_after=True)
   await asyncio.wait_for(click_received.wait(),10)
   elapsed=time.monotonic()-clicked
   assert not release.is_set(),'click must reach BFF while page_view is held'
   click=next(r for r in records if any(e['event_name']=='download_clicked' for e in r['request']['events']))
   e=next(e for e in click['request']['events'] if e['event_name']=='download_clicked')
   assert e['environment']=='staging' and e['event_id'] in click['response'].get('accepted_event_ids',[]), json.dumps(click)
   assert e['destination_type']=='app_store_fallback'
   await page.wait_for_url('https://apps.apple.com/**')
   release.set();await page.wait_for_timeout(1500)
   # Reload original tab: pending persisted events retry, keeping the original IDs.
   await page.goto(origin+'/privacy.html',wait_until='domcontentloaded');await page.wait_for_timeout(4000)
   assert all(r['status']==200 and not r['response'].get('rejected') for r in records)
   out={'scope':'Chromium mobile emulation; HTTP-over-Unix-socket to real BFF and real Supabase staging; Store target intercepted; not iPhone/public Vercel acceptance','passed':True,'click_accepted_while_pageview_held':True,'click_roundtrip_seconds':round(elapsed,3),'receipts':records}
   (root/'docs/evidence/mobile-download-live-hotfix.json').write_text(json.dumps(out,indent=2))
   print(json.dumps({k:v for k,v in out.items() if k!='receipts'}))
  finally:release.set();await b.close()
try:asyncio.run(main())
finally:server.terminate();server.wait();Path(sock_path).unlink(missing_ok=True)
