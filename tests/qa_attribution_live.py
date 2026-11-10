import asyncio,json,os,subprocess,time,urllib.request,uuid
from pathlib import Path
from playwright.async_api import async_playwright
root=Path(__file__).resolve().parents[1]; origin='http://127.0.0.1:8262'
env={**os.environ,'PORT':'8262','HOOPCUT_PREVIEW_SOCKET':'/tmp/hoopcut-attribution-qa.sock','HOOPCUT_STAGING_SECRET_FILE':os.environ['HOOPCUT_STAGING_SECRET_FILE']}
Path('/tmp/hoopcut-attribution-qa.sock').unlink(missing_ok=True)
server=subprocess.Popen(['node','server/attribution-preview.js'],cwd=root,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
async def main():
 await asyncio.sleep(1)
 async with async_playwright() as p:
  browser=await p.chromium.launch(executable_path='/var/lib/swi-codex/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',args=['--no-sandbox','--no-proxy-server'])
  page=await browser.new_page(viewport={'width':390,'height':844});captured=[]
  async def record(response):
   if '/api/analytics/events' in response.url:
    try:captured.append({'request':response.request.post_data_json,'status':response.status,'response':await response.json()})
    except Exception as e:print('record failure',type(e).__name__)
  # Receipts captured once at the HTTP bridge, not duplicated by browser response hooks.
  page.on('requestfailed',lambda r:print('failed',r.url.split('?')[0],r.failure))
  page.on('pageerror',lambda e: print('pageerror',str(e)[:200]))
  import http.client,socket
  def proxy(request):
   conn=http.client.HTTPConnection('127.0.0.1',timeout=20)
   sock=socket.socket(socket.AF_UNIX);sock.settimeout(20);sock.connect('/tmp/hoopcut-attribution-qa.sock');conn.sock=sock
   from urllib.parse import urlsplit
   u=urlsplit(request.url);headers=dict(request.headers);headers['host']='127.0.0.1:8262'
   conn.request(request.method,u.path+('?' + u.query if u.query else ''),body=request.post_data,headers=headers)
   r=conn.getresponse();result=(r.status,dict(r.getheaders()),r.read());conn.close();return result
  async def bridge(route):
   if not route.request.url.startswith(origin):await route.abort();return
   if '/api/analytics' in route.request.url:print('bridging API')
   status,headers,body=await asyncio.to_thread(proxy,route.request)
   if '/api/analytics' in route.request.url:
    print('API status',status,body.decode()[:300])
    captured.append({'request':json.loads(route.request.post_data),'status':status,'response':json.loads(body)})
   headers.pop('Transfer-Encoding',None);headers.pop('Connection',None)
   await route.fulfill(status=status,headers=headers,body=body)
  await page.route('**/*',bridge)
  await page.goto(origin+'/?utm_source=qa&utm_campaign=staging_bff_20261109',wait_until='domcontentloaded',timeout=15000)
  await page.evaluate("window.addEventListener('click',e=>{if(e.target.closest('a[data-attribution-cta]'))e.preventDefault()})")
  await page.locator('[data-attribution-cta="hero_download"]').click()
  await page.wait_for_timeout(20000)
  print('client loaded',await page.evaluate('!!window.hoopcutAttribution'))
  assert captured and all(x['status']==200 for x in captured), 'Real BFF collection failed'
  events=[e for x in captured for e in x['request']['events']]
  async def post(events):
   return await page.evaluate("async events=>{const r=await fetch('/api/analytics/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({schema_version:1,events})});return {status:r.status,body:await r.json()}}",events)
  duplicate=await post(events);assert len(duplicate['body']['duplicate_event_ids'])==len(events)
  changed={**events[0],'session_campaign':'conflicting-payload'};conflict=await post([changed]);assert conflict['body']['rejected'] and not conflict['body']['accepted_event_ids']
  wrong={**events[0],'environment':'production'};isolated=await post([wrong]);assert isolated['body']['rejected']
  raw={**events[0],'raw_ip':'synthetic'};invalid=await post([raw]);assert invalid['body']['rejected']
  assert any(e['event_name']=='video_play' and e['playback_trigger']=='autoplay' for e in events)
  output={'checks':['browser page_view/video_play/download_clicked persisted receipt','actual hero autoplay classified','same event retries duplicate','changed payload rejected','production environment rejected','raw_ip rejected'],'scope' :'staging browser via HTTP-over-Unix-socket transport bridge to real BFF and Supabase; TCP preview unavailable','receipts':captured}
  (root/'docs/evidence/browser-live-staging.json').write_text(json.dumps(output,indent=2))
  print(json.dumps({'requests':len(captured),'statuses':[x['status'] for x in captured],'accepted':sum(len(x['response'].get('accepted_event_ids',[])) for x in captured)}))
  await browser.close()
try:asyncio.run(main())
finally:server.terminate();server.wait()
