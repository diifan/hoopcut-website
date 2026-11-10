import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
root=Path(__file__).resolve().parents[1]
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/var/lib/swi-codex/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',args=['--no-sandbox','--no-proxy-server'])
  ctx=await b.new_context(viewport={'width':390,'height':844});page=await ctx.new_page();events=[];checks=[]
  async def collect(route):
   data=route.request.post_data_json;events.extend(data['events']);await route.fulfill(json={'accepted_event_ids':[x['event_id'] for x in data['events']],'duplicate_event_ids':[],'rejected':[]})
  async def static(route):
   from urllib.parse import urlsplit
   import mimetypes
   path=urlsplit(route.request.url).path
   f=root/'dist'/path.lstrip('/')
   if path=='/': f=root/'dist/index.html'
   if f.is_file(): await route.fulfill(path=str(f),content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream')
   else: await route.fulfill(status=404,body='')
  await ctx.route('**/*',static)
  await ctx.route('**/api/analytics/events',collect)
  await page.goto('http://127.0.0.1:8259/?utm_source=YouTube&utm_medium=Organic_Social&utm_campaign=Pickup&token=NEVER',wait_until='domcontentloaded');await page.wait_for_timeout(500)
  pv=next(e for e in events if e['event_name']=='page_view');assert pv['session_source']=='youtube' and pv['session_medium']=='organic_social' and pv['session_campaign']=='Pickup' and pv['environment']=='staging' and pv['page_path']=='/' and 'NEVER' not in json.dumps(events);checks.append('UTM whitelist, lowercase, staging, path-only')
  assert len([e for e in events if e['event_name']=='page_view'])==1;checks.append('single initial page view')
  await page.evaluate('''()=>{let a=document.querySelector('[data-attribution-cta="hero_download"]');a.target='_blank';window.addEventListener('click',e=>{window.lastHref=a.href;e.preventDefault()});a.focus();}''')
  await page.keyboard.press('Enter');await page.wait_for_timeout(300)
  click=[e for e in events if e['event_name']=='download_clicked'][-1];assert click['destination_type']=='app_store_fallback' and click['cta_id']=='hero_download';checks.append('keyboard real activation with Store fallback')
  await page.evaluate('''()=>{let e=document.querySelector('#attribution-settings');let c=JSON.parse(e.textContent);c.oneLinkBaseURL='https://hoopcut.onelink.me/SDN0';c.oneLinkHosts=['hoopcut.onelink.me'];e.textContent=JSON.stringify(c)}''')
  # A fresh page has build-like config supplied before script executes, with synthetic SDK only.
  html=(root/'dist/index.html').read_text().replace('"oneLinkBaseURL":null','"oneLinkBaseURL":"https://hoopcut.onelink.me/SDN0"').replace('"oneLinkHosts":[]','"oneLinkHosts":["hoopcut.onelink.me"]')
  await ctx.route('http://127.0.0.1:8259/mock',lambda r:r.fulfill(body=html,content_type='text/html'))
  await page.add_init_script("window.AF_SMART_SCRIPT={generateOneLinkURL:()=>({clickURL:'https://hoopcut.onelink.me/SDN0?gclid=discard&af_js_web=true&af_ss_ver=2_10_4'})}")
  await page.goto('http://127.0.0.1:8259/mock',wait_until='domcontentloaded');await page.wait_for_timeout(300)
  await page.evaluate('''()=>{const a=document.querySelector('[data-attribution-cta="hero_download"]');window.addEventListener('click',e=>{window.lastHref=a.href;e.preventDefault()})}''')
  await page.locator('[data-attribution-cta="hero_download"]').click();await page.wait_for_timeout(300)
  href=await page.evaluate('lastHref');from urllib.parse import urlsplit,parse_qs
  params=parse_qs(urlsplit(href).query);click=[e for e in events if e['event_name']=='download_clicked'][-1];assert params['af_sub1']==[click['click_id']] and params['pid']==['hoopcut_website'] and 'gclid' not in params and click['session_campaign']=='Pickup';checks.append('OneLink click_id equality, parameter allowlist, internal session source preserved')
  old=click['click_id'];await page.locator('[data-attribution-cta="hero_download"]').click();await page.wait_for_timeout(300);assert [e for e in events if e['event_name']=='download_clicked'][-1]['click_id']!=old;checks.append('two activations distinct IDs')
  for bad in ['https://evil.example/SDN0?af_js_web=true&af_ss_ver=2_10_4','https://hoopcut.onelink.me/other?af_js_web=true&af_ss_ver=2_10_4','https://user@hoopcut.onelink.me/SDN0?af_js_web=true&af_ss_ver=2_10_4','https://hoopcut.onelink.me/SDN0?af_js_web=true&af_ss_ver=bad','https://hoopcut.onelink.me/SDN0?af_ss_ver=2_10_4']:
   await page.evaluate('(url)=>window.AF_SMART_SCRIPT.generateOneLinkURL=()=>({clickURL:url})',bad)
   await page.locator('[data-attribution-cta="hero_download"]').click();await page.wait_for_timeout(200)
   assert await page.evaluate('lastHref')=='https://apps.apple.com/app/id6824860341'
   assert [e for e in events if e['event_name']=='download_clicked'][-1]['destination_type']=='app_store_fallback'
  checks.append('untrusted host/path/credentials/version/missing SDK flag fall back')

  await page.evaluate("history.replaceState({},'',location.href)");await page.wait_for_timeout(100);n=len([e for e in events if e['event_name']=='page_view']);await page.evaluate("history.pushState({},'','/new-route')");await page.wait_for_timeout(200);assert len([e for e in events if e['event_name']=='page_view'])==n+1;checks.append('SPA navigation vs same-URL rerender')
  # Real local HTML5 media playback, not a synthetic playing event.
  await page.evaluate("""()=>{const v=document.createElement('video');v.dataset.analyticsVideo='qa-real-video';v.autoplay=true;v.muted=true;v.src='/assets/video/players/all.mp4';document.body.append(v);window.qaVideo=v;}""")
  # Use known playable prepared video served through test route.
  await ctx.route('**/assets/video/players/all.mp4',lambda r:r.fulfill(path=str(root/'assets/video/hoopcut-banner.mp4'),content_type='video/mp4'))
  await page.evaluate('qaVideo.load();qaVideo.play()');await page.wait_for_timeout(600)
  await page.evaluate('qaVideo.pause();qaVideo.play()');await page.wait_for_timeout(200)
  assert len([e for e in events if e.get('video_id')=='qa-real-video'])==1;checks.append('real video playing only, resume deduplicated')
  # Fail transport once, preserve event ID across retries.
  ctx2=await b.new_context();p2=await ctx2.new_page();attempts=[]
  await ctx2.route('**/*',static)
  async def retry_route(route):
   data=route.request.post_data_json;attempts.append(data['events'])
   if len(attempts)==1: await route.fulfill(status=503,json={'error':'test_failure'})
   else: await route.fulfill(json={'accepted_event_ids':[x['event_id'] for x in data['events']],'duplicate_event_ids':[],'rejected':[]})
  await ctx2.route('**/api/analytics/events',retry_route)
  await p2.goto('http://127.0.0.1:8259/privacy.html');await p2.wait_for_timeout(2400)
  assert len(attempts)>=2 and attempts[0][0]['event_id']==attempts[1][0]['event_id']
  assert attempts[0][0]['session_source']=='direct' and attempts[0][0]['session_medium']=='none' and attempts[0][0]['session_campaign']=='website_default';checks.append('503 retry same ID; direct defaults')
  old=attempts[0][0]
  await p2.evaluate("""()=>{const k='hoopcut.attribution.v1.staging';const s=JSON.parse(sessionStorage.getItem(k));s.last=Date.now()-1800001;sessionStorage.setItem(k,JSON.stringify(s));}""")
  await p2.goto('http://127.0.0.1:8259/privacy.html?utm_source=Instagram');await p2.wait_for_timeout(300)
  new=attempts[-1][0];assert new['web_session_id']!=old['web_session_id'] and new['session_source']=='instagram' and new['first_touch_source']=='direct';checks.append('30 minute expiry and first-touch retained')
  ctx3=await b.new_context();await ctx3.add_init_script("Object.defineProperty(window,'sessionStorage',{get(){throw Error('denied')}});Object.defineProperty(window,'localStorage',{get(){throw Error('denied')}})")
  await ctx3.route('**/*',static);denied=[]
  async def denied_route(route):
   data=route.request.post_data_json;denied.extend(data['events']);await route.fulfill(json={'accepted_event_ids':[x['event_id'] for x in data['events']],'duplicate_event_ids':[],'rejected':[]})
  await ctx3.route('**/api/analytics/events',denied_route);p3=await ctx3.new_page();await p3.goto('http://127.0.0.1:8259/privacy.html');await p3.wait_for_timeout(300);assert denied[0]['visitor_scope']=='session';checks.append('disabled storage uses memory without breaking page')
  await b.close();(root/'tests/attribution-browser-results.json').write_text(json.dumps({'checks':checks,'passed':len(checks),'synthetic_only':True},indent=2));print(json.dumps(checks))
asyncio.run(main())
