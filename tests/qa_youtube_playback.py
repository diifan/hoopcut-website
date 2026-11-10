import asyncio,json,os,mimetypes
from pathlib import Path
from playwright.async_api import async_playwright
root=Path(__file__).resolve().parents[1]
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(executable_path='/var/lib/swi-codex/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome',args=['--no-sandbox','--autoplay-policy=no-user-gesture-required'],proxy={'server':os.environ['HTTPS_PROXY']})
  page=await b.new_page();events=[]
  async def local(route):
   from urllib.parse import urlsplit
   path=urlsplit(route.request.url).path
   if path=='/api/analytics/events':
    data=route.request.post_data_json;events.extend(data['events']);await route.fulfill(json={'accepted_event_ids':[e['event_id'] for e in data['events']],'duplicate_event_ids':[],'rejected':[]});return
   f=root/'dist'/path.lstrip('/')
   if not f.is_file():f=f.with_suffix('.html')
   if f.is_file():await route.fulfill(path=str(f),content_type=mimetypes.guess_type(str(f))[0] or 'application/octet-stream')
   else:await route.fulfill(status=404,body='')
  await page.route('https://hoopcut.ai/**',local)
  result={'scope':'local built page on intercepted site origin; real YouTube requests via proxy; analytics mock only, no production events'}
  try:
   await page.goto('https://hoopcut.ai/videos/two-pickup-jump-shots-shot-tracer',wait_until='domcontentloaded',timeout=30000)
   await page.locator('iframe[data-analytics-video]').scroll_into_view_if_needed()
   await page.wait_for_timeout(15000)
   frame=next(f for f in page.frames if 'youtube-nocookie.com/embed/' in f.url)
   result['player_text']=(await frame.locator('body').inner_text())[:500]
   await page.locator('iframe[data-analytics-video]').click()
   await page.wait_for_timeout(12000)
   result['player_text']=(await frame.locator('body').inner_text())[:500]
   result['media']=await frame.locator('video').evaluate('(v)=>({time:v.currentTime,paused:v.paused,error:v.error&&v.error.code})')
   result['events']=[e for e in events if e['event_name']=='video_play']
   result['passed']=result['media']['time']>0 and len(result['events'])==1
  except Exception as e:result['passed']=False;result['error_type']=type(e).__name__
  await page.screenshot(path=str(root/'docs/evidence/youtube-playback.png'))
  (root/'docs/evidence/youtube-playback.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));await b.close()
asyncio.run(main())
