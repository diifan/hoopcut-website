"""Opt-in protected Vercel staging acceptance; never targets production."""
import asyncio,json,os,re
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from playwright.async_api import async_playwright
root=Path(__file__).resolve().parents[1]
origin='https://hoopcut-website-git-feat-web-attribution-v1-diifans-projects.vercel.app'
async def main():
 bypass=next(iter(json.loads(Path(os.environ['HOOPCUT_PREVIEW_BYPASS_FILE']).read_text())))
 result={'origin':origin,'scope':'real Vercel preview + official SDK + YouTube + Supabase staging; protected access retained','receipts':[],'checks':[]}
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/var/lib/swi-codex/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'],proxy={'server':os.environ['HTTPS_PROXY']})
  ctx=await b.new_context(viewport={'width':390,'height':844})
  async def auth(route):
   await route.continue_(headers={**route.request.headers,'x-vercel-protection-bypass':bypass})
  await ctx.route(origin+'/**',auth)
  page=await ctx.new_page()
  async def record(response):
   if response.url==origin+'/api/analytics/events':
    try:result['receipts'].append({'status':response.status,'request':response.request.post_data_json,'response':await response.json()})
    except:pass
  page.on('response',record)
  try:
   r=await page.goto(origin+'/?utm_source=qa&utm_medium=integration&utm_campaign=public_staging_20261110',wait_until='domcontentloaded',timeout=60000)
   assert r.status==200 and urlsplit(page.url).hostname==urlsplit(origin).hostname
   result['headers']={k:v for k,v in r.headers.items() if k in ['content-security-policy','x-robots-tag','strict-transport-security']}
   await page.wait_for_function('!!window.AF_SMART_SCRIPT',timeout=30000)
   await page.evaluate("window.addEventListener('click',e=>{const a=e.target.closest('a[data-attribution-cta]');if(a){window.qaDestination=a.href;e.preventDefault()}})")
   await page.locator('[data-attribution-cta="hero_download"]').click();await page.wait_for_timeout(5000)
   url=await page.evaluate('qaDestination');q=parse_qs(urlsplit(url).query)
   events=[e for x in result['receipts'] for e in x['request']['events']]
   click=next(e for e in events if e['event_name']=='download_clicked')
   assert q['af_sub1']==[click['click_id']] and q['af_sub5']==['staging'] and q['af_js_web']==['true'] and re.fullmatch(r'\d+_\d+_\d+',q['af_ss_ver'][0])
   result['oneLinkURL']=url;result['sdk_version']=q['af_ss_ver'][0]
   assert all(x['status']==200 and x['response'].get('accepted_event_ids') for x in result['receipts'])
   result['checks'].append('mobile homepage, real SDK and real BFF accepted')
   duplicate=await page.evaluate("async events=>{const r=await fetch('/api/analytics/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({schema_version:1,events})});return {status:r.status,body:await r.json()}}",events)
   assert len(duplicate['body']['duplicate_event_ids'])==len(events)
   result['checks'].append('public BFF retry returns duplicate IDs')
   await page.evaluate('window.AF_SMART_SCRIPT=undefined');await page.locator('[data-attribution-cta="hero_download"]').click();await page.wait_for_timeout(2500)
   assert await page.evaluate('qaDestination')=='https://apps.apple.com/app/id6824860341'
   assert any(e.get('destination_type')=='app_store_fallback' for x in result['receipts'] for e in x['request']['events'])
   result['checks'].append('SDK failure immediately falls back')
   assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   await page.screenshot(path=str(root/'docs/evidence/public-mobile.png'))
   await page.set_viewport_size({'width':1280,'height':900})
   await page.goto(origin+'/videos/two-pickup-jump-shots-shot-tracer',wait_until='domcontentloaded',timeout=60000)
   iframe=page.locator('iframe[data-analytics-video]');await iframe.scroll_into_view_if_needed();await page.wait_for_timeout(15000);await iframe.click();await page.wait_for_timeout(15000)
   frame=next(f for f in page.frames if 'youtube-nocookie.com/embed/' in f.url)
   result['media']=await frame.locator('video').evaluate('(v)=>({time:v.currentTime,error:v.error&&v.error.code})')
   plays=[e for x in result['receipts'] for e in x['request']['events'] if e.get('video_id')=='MLcda_7VYkQ']
   assert result['media']['time']>0 and len({e['event_id'] for e in plays})==1
   result['checks'].append('real YouTube playback and unique video_play via public BFF')
   await page.screenshot(path=str(root/'docs/evidence/public-desktop.png'))
   result['passed']=True
  except Exception as e:result['passed']=False;result['error']=type(e).__name__+': '+str(e)[:250]
  await page.wait_for_timeout(1000)
  (root/'docs/evidence/public-staging.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='receipts'}));await b.close()
asyncio.run(main())
