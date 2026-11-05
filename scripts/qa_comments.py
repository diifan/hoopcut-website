import asyncio,json,os,subprocess,urllib.parse,time
from pathlib import Path
import httpx
from playwright.async_api import async_playwright
cfg={k:v for k,v in os.environ.items() if k.startswith('COMMENTS_')}
assert urllib.parse.urlsplit(cfg.get('COMMENTS_DATABASE_URL','')).path.endswith('_test'), 'Use only a dedicated *_test database'
out=Path(os.environ.get('COMMENTS_TEST_OUTPUT','reports/video-comments'));out.mkdir(parents=True,exist_ok=True)
cfg['COMMENTS_SOCKET']=str(out.resolve()/'http.sock');cfg['COMMENTS_ALLOWED_ORIGINS']='http://127.0.0.1:8767'
env={**os.environ,**cfg,'PREVIEW_PREFIX':''}
async def main():
 async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(uds=cfg['COMMENTS_SOCKET']),trust_env=False,timeout=20) as http:
  async with async_playwright() as p:
   browser=await p.chromium.launch(executable_path=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'),args=['--no-sandbox'])
   errors=[];checks=[]
   async def route(r):
    if not r.request.url.startswith('http://127.0.0.1:8767'):
     await r.abort();return
    resp=await http.request(r.request.method,r.request.url.replace('http://127.0.0.1:8767','http://localhost'),headers={k:v for k,v in r.request.headers.items() if k not in ['host','accept-encoding']},content=r.request.post_data_buffer)
    await r.fulfill(status=resp.status_code,headers={k:v for k,v in resp.headers.items() if k not in ['content-length','content-encoding','transfer-encoding']},body=resp.content)
   a=await browser.new_context(viewport={'width':1440,'height':1000});b=await browser.new_context(viewport={'width':390,'height':844})
   for c in [a,b]:await c.route('**/*',route)
   page=await a.new_page();q=await b.new_page()
   for pg in [page,q]:pg.on('pageerror',lambda e:errors.append(str(e)))
   url='http://127.0.0.1:8767/videos/two-pickup-jump-shots-shot-tracer'
   await page.goto(url);await page.get_by_text('Start the conversation',exact=True).wait_for()
   compose=page.locator('[data-comment-composer]')
   await compose.get_by_label('Add a comment',exact=True).fill('[QA] A real comment <script>alert(1)</script>')
   await compose.get_by_label('Name (optional)').fill('Court guest')
   await compose.get_by_role('button',name='Comment',exact=True).click()
   await page.get_by_text('[QA] A real comment <script>alert(1)</script>',exact=True).wait_for();checks.append('nickname post and safe text rendering')
   await q.goto(url);await q.get_by_text('Court guest',exact=True).wait_for();assert await q.get_by_role('button',name='Delete',exact=True).count()==0;checks.append('cross-browser persistence and author controls')
   await q.get_by_role('button',name='Like comment by Court guest',exact=True).click()
   await q.get_by_role('button',name='Remove like from comment by Court guest',exact=True).wait_for();await q.reload();await q.get_by_role('button',name='Remove like from comment by Court guest',exact=True).wait_for();checks.append('reaction persists after reload')
   await page.get_by_role('button',name='Reply',exact=True).click();await page.get_by_label('Add a reply',exact=True).fill('[QA] reply')
   await page.locator('form').filter(has=page.get_by_label('Add a reply',exact=True)).get_by_role('button',name='Reply',exact=True).click()
   await page.get_by_text('[QA] reply',exact=True).wait_for();await page.locator('.comment-replies-toggle').first.click()
   await page.locator('.comment-row').first.get_by_role('button',name='Reply',exact=True).first.click();await page.get_by_label('Add a reply',exact=True).fill('[QA] collapsed reply')
   await page.locator('form').filter(has=page.get_by_label('Add a reply',exact=True)).get_by_role('button',name='Reply',exact=True).click();await page.get_by_text('[QA] collapsed reply',exact=True).wait_for();checks.append('reply and collapsed-thread regression')
   await q.get_by_role('button',name='Report',exact=True).click();await q.get_by_role('button',name='Send report',exact=True).click();await q.get_by_text('Report received. Thank you.',exact=True).wait_for();checks.append('report without hiding content')
   await page.reload();await page.get_by_text('Court guest',exact=True).wait_for()
   await page.locator('.comments-sort summary').click();await page.get_by_role('button',name='Top comments',exact=True).click();await page.get_by_text('Court guest',exact=True).wait_for();checks.append('top sort loads successfully')
   for width in [320,390,768,1440]:
    await page.set_viewport_size({'width':width,'height':1000})
    await page.locator('[data-video-comments]').scroll_into_view_if_needed()
    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
    frame=await page.locator('.watch-player iframe').bounding_box();assert abs(frame['width']/frame['height']-9/16)<.02,(width,frame)
    await page.screenshot(path=str(out/f'page-{width}.png'))
   checks.append('320/390/768/1440 layouts and 9:16 player geometry')
   page.on('dialog',lambda d:d.accept())
   await page.get_by_role('button',name='Delete',exact=True).first.click();await page.get_by_text('[Comment deleted]',exact=True).wait_for();checks.append('author deletion')
   assert await page.locator('#video-context').count()==1
   assert not errors,errors
   checks.append('editorial rendered and no JS errors')
   await browser.close();print(json.dumps(checks));(out/'browser-results.json').write_text(json.dumps(checks,indent=2))
log=(out/'server.log').open('w');proc=subprocess.Popen(['node','server/comments-preview.js'],env=env,stdout=log,stderr=log)
try:
 for _ in range(40):
  if Path(cfg['COMMENTS_SOCKET']).exists():break
  time.sleep(.1)
 asyncio.run(main())
finally:
 proc.terminate();proc.wait();log.close()
 subprocess.run(['node','--input-type=module','-e',"import {database,closeDatabase} from './lib/comments.js';await database().query('TRUNCATE hc_comments,hc_comment_rates,hc_comment_reports,hc_comment_actions CASCADE');await closeDatabase();"],env=env,check=True)
