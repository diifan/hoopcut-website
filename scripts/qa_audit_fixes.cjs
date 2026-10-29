/* Behavior checks for approved local audit changes; no external accounts. */
const fs=require('fs'),path=require('path'),os=require('os');
const {chromium}=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const root=path.resolve(__dirname,'..'),out=path.join(root,'reports/audit-fixes');fs.mkdirSync(out,{recursive:true});
const base='http://127.0.0.1:8767';
const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const context=await browser.newContext({acceptDownloads:true});const page=await context.newPage();
 const errors=[],broken=[],external=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)broken.push(r.url());});
 page.on('request',r=>{if(!r.url().startsWith(base)&&/^https?:/.test(r.url()))external.push(r.url());});
 await page.addInitScript(()=>{window.__HOOPCUT_ANALYTICS_DEBUG__=true;window.__localEvents=[];window.addEventListener('hoopcut:analytics-debug',e=>window.__localEvents.push(e.detail));});
 const rows=[];
 for(const width of [320,390,768,1280,1440]){
  await page.setViewportSize({width,height:900});await page.goto(base+'/');
  await page.waitForFunction(()=>[...document.querySelectorAll('link[rel=stylesheet]')].every(l=>l.sheet));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Home overflow '+width);
  const metrics=await page.locator('.hero .copy p').evaluate(el=>({px:parseFloat(getComputedStyle(el).fontSize),bottom:el.getBoundingClientRect().bottom}));
  assert(metrics.px>=14,'Readable hero '+width);
  const cta=await page.locator('.hero .cta').boundingBox();
  assert(cta.y>=metrics.bottom,'Hero CTA overlaps description '+width);
  assert(await page.locator('.hero .cta').getAttribute('href').then(v=>v.startsWith('https://apps.apple.com/')&&v.endsWith('/id6824860341')),'Verified App Store destination');
  assert(await page.locator('.reviews article').count()===3,'Original reviews');
  try { await page.waitForFunction(()=>document.querySelector('#banner-video').currentTime>.15,{},{timeout:15000}); }
  catch(error) { console.log('Autoplay state',width,await page.locator('#banner-video').evaluate(v=>({src:v.currentSrc,paused:v.paused,ready:v.readyState,time:v.currentTime,error:v.error?.message,visibility:document.visibilityState,scroll:scrollY,rect:v.getBoundingClientRect().toJSON()})));throw error; }
  const media=await page.locator('#banner-video').evaluate(v=>({src:v.currentSrc,duration:v.duration}));
  assert(media.src.includes(width<=700?'reel-all-640':'reel-all-960'),'Responsive reel '+width);
  assert(Math.abs(media.duration-52)<.15,'Complete ten-shot reel '+width);
  if(width===390||width===1440)await page.screenshot({path:path.join(out,'home-'+width+'.png'),fullPage:width===390});
  rows.push({width,fontPx:metrics.px,video:media.src.split('/').at(-1),seconds:media.duration});
  console.log('PASS homepage',width);
 }
 await page.locator('[data-player="red"]').click();
 await page.waitForFunction(()=>document.querySelector('#banner-video').currentSrc.includes('reel-red')&&document.querySelector('#banner-video').currentTime>.15);
 assert((await page.locator('#player-status').textContent()).includes('2 made shots'),'Player switch/count');
 await page.setViewportSize({width:390,height:844});
 for(const route of ['/tools','/blog','/templates/basketball-senior-night-poster','/blog/how-to-make-basketball-highlights-for-instagram']){
  await page.goto(base+route);await page.waitForFunction(()=>[...document.querySelectorAll('link[rel=stylesheet]')].every(l=>l.sheet));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile overflow '+route);
  assert(await page.locator('h1').count()===1,'H1 '+route);
  const schemas=await page.locator('script[type="application/ld+json"]').evaluateAll(items=>items.flatMap(s=>JSON.parse(s.textContent)['@graph']||[]));
  assert(schemas.some(n=>n['@type']==='Organization'&&n.legalName==='SWINK AI INC.'),'Rendered organization '+route);
  await page.screenshot({path:path.join(out,route.split('/').at(-1)+'.png'),fullPage:true});
 }
 await page.goto(base+'/templates/basketball-senior-night-poster');
 await page.locator('[data-field="0"]').fill('PRIVATE PERSON 123');
 const wait=page.waitForEvent('download');await page.locator('[data-export="png"]').click();await (await wait).saveAs(path.join(out,'poster-export.png'));
 const events=await page.evaluate(()=>window.__localEvents);
 assert(events.filter(e=>e.name==='tool_start').length===1,'Deduplicate start');
 assert(events.filter(e=>e.name==='export_success'&&e.data.format==='png').length===1,'Export event after PNG created');
 assert(!JSON.stringify(events).includes('PRIVATE PERSON'),'No editor content in analytics');
 await page.goto(base+'/templates/basketball-senior-gift-budget');
 await page.locator('#resource-table tbody tr').first().locator('textarea').nth(1).fill('-1');
 await page.locator('[data-export="csv"]').click();
 assert(!(await page.evaluate(()=>window.__localEvents)).some(e=>e.name==='export_success'),'Failed export must not emit success');
 const noMotion=await browser.newContext({reducedMotion:'reduce',viewport:{width:390,height:844}}),quiet=await noMotion.newPage();
 const quietVideos=[];quiet.on('request',r=>{if(/\.mp4/.test(r.url()))quietVideos.push(r.url());});
 await quiet.goto(base+'/');await quiet.waitForLoadState('load');assert(quietVideos.length===0,'Reduced motion skips background video download');
 await quiet.locator('[data-player="blue"]').click();await quiet.waitForFunction(()=>document.querySelector('#banner-video').currentTime>.1);
 await noMotion.close();
 for(const route of ['/demo/auto-clipping','/demo/shot-tracer']){
  await page.goto(base+route);await page.locator('#center-play').click();
  await page.waitForFunction(()=>document.querySelector('#demo-video').currentTime>.1);
  assert(Math.abs(await page.locator('#demo-video').evaluate(v=>v.duration)-52)<.15,'Demo timing '+route);
  assert(!(await page.locator('#media-error').isVisible()),'Demo playable '+route);
 }
 assert(!errors.length,'JS errors '+JSON.stringify(errors));assert(!broken.length,'Broken local requests '+JSON.stringify(broken));assert(!external.length,'Local preview sent external requests '+JSON.stringify(external));
 // Mock the production hostname and provider script entirely from local files.
 // This validates flags/API shape without contacting a Vercel account.
 const mock=await browser.newContext();
 await mock.route('https://hoopcut.ai/**',async route=>{
  const pathname=new URL(route.request().url()).pathname;
  if(pathname==='/_vercel/insights/script.js')return route.fulfill({contentType:'text/javascript',body:'window.__providerLoaded=true;'});
  let file=path.join(root,pathname==='/'?'index.html':pathname);
  if(!path.extname(file))file+='.html';
  let bytes=fs.readFileSync(file);
  if(file.endsWith('.html'))bytes=Buffer.from(bytes.toString().replace('"enabled": false','"enabled": true').replace('"customEvents": false','"customEvents": true'));
  const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.webp':'image/webp','.mp4':'video/mp4','.jpg':'image/jpeg'};
  await route.fulfill({contentType:types[path.extname(file)]||'application/octet-stream',body:bytes});
 });
 const prod=await mock.newPage();await prod.goto('https://hoopcut.ai/?private=DO_NOT_SEND#hidden');
 await prod.waitForFunction(()=>window.__providerLoaded===true);
 await prod.evaluate(()=>document.addEventListener('click',e=>{if(e.target.closest('a'))e.preventDefault();}));
 await prod.locator('.hero .cta').click();
 const queue=await prod.evaluate(()=>({events:window.vaq.filter(x=>x[0]==='event').map(x=>x[1]),redacted:window.vaq.find(x=>x[0]==='beforeSend')[1]({url:location.href}).url}));
 assert(queue.events.some(e=>e.name==='app_outbound'),'Production event queue');
 assert(queue.redacted==='https://hoopcut.ai/','Strip query and hash');
 assert(!JSON.stringify(queue.events).includes('DO_NOT_SEND'),'No query in event payload');
 await mock.close();
 fs.writeFileSync(path.join(out,'checks.json'),JSON.stringify({status:'pass',home:rows,events,mockedProduction:queue,errors,broken,external,scope:'Local preview and mocked provider only; real Vercel delivery, TLS and Google indexing need separate live validation.'},null,2));
 await browser.close();console.log('PASS: mobile/desktop hero, 4 complete responsive reels, App Store CTA, reviews, rendered schema, PNG export, event privacy/failure handling, reduced motion, both demos; zero external analytics requests.');
})().catch(e=>{console.error(e);process.exit(1);});
