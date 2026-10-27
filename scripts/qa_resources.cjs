/* Local-only browser QA in a separate temporary profile. No logged-in browser access. */
const path=require('path'),fs=require('fs'),os=require('os');
const dep=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=require(path.join(dep,'playwright'));
const sharp=require(path.join(dep,'sharp'));
const root=path.resolve(__dirname,'..'), out=path.join(root,'reports/batch-one');fs.mkdirSync(out,{recursive:true});
const resources=JSON.parse(fs.readFileSync(path.join(root,'content/blog/batch-one-resources.json'))).resources;
const guides=['how-to-film-basketball-games','record-basketball-practice-alone','basketball-senior-night-poster-ideas','basketball-senior-night-gift-ideas','basketball-senior-night-table-ideas'];
const paths=[...resources.map(r=>'/templates/'+r.slug),...guides.map(s=>'/blog/'+s)];
const assert=(condition,text)=>{if(!condition)throw Error(text);};
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage();const errors=[],broken=[],results=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('response',res=>{if(res.url().startsWith('http://127.0.0.1:8767') && res.status()>=400)broken.push({url:res.url(),status:res.status()});});
 for(const route of paths){
  const response=await page.goto('http://127.0.0.1:8767'+route);
  assert(response.status()===200,'HTTP '+route);
  assert(response.headers()['x-robots-tag']?.includes('noindex'),'Preview index protection '+route);
  await page.locator('h1').waitFor();await page.evaluate(()=>document.fonts.ready);
  await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});
  assert(await page.locator('h1').count()===1,'H1 '+route);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Desktop overflow '+route);
  const item=resources.find(r=>route.endsWith('/'+r.slug));
  if(item){
   if(item.kind==='graphic'){
    await page.locator('[data-field="0"]').fill('Alex & Taylor <Test>');
    assert((await page.locator('#slot-0').textContent())==='Alex & Taylor <Test>','SVG safe text '+route);
    for(const format of ['svg','png']){
      const waiting=page.waitForEvent('download');await page.locator(`[data-export="${format}"]`).click();const download=await waiting;
      const dest=path.join(out,download.suggestedFilename());await download.saveAs(dest);
      if(format==='svg'){const xml=fs.readFileSync(dest,'utf8');assert(xml.includes('Alex &amp; Taylor &lt;Test&gt;'),'Escaped SVG '+route);}
      else {const meta=await sharp(dest).metadata();assert(meta.width>=1000 && meta.height>=675,'PNG dimensions '+route);}
    }
   } else {
    const original=await page.locator('#resource-table tbody tr').count();
    await page.locator('#add-row').click();assert(await page.locator('#resource-table tbody tr').count()===original+1,'Add row '+route);
    const last=page.locator('#resource-table tbody tr').last();await last.locator('textarea').first().fill('=1+1');
    if(item.kind==='budget'){
      assert((await page.locator('#budget-total').innerText()).includes('$30.00'),'Initial budget');
      await last.locator('textarea').nth(1).fill('2');await last.locator('textarea').nth(2).fill('3');await last.locator('textarea').nth(3).fill('1');
      assert((await page.locator('#budget-total').innerText()).includes('$37.00'),'Budget recalculation');
      await last.locator('textarea').nth(2).fill('-4');
      assert(await last.locator('textarea').nth(2).getAttribute('aria-invalid')==='true','Budget validation');
      await last.locator('textarea').nth(2).fill('3');
    }
    const waiting=page.waitForEvent('download');await page.locator('[data-export="csv"]').click();const download=await waiting;
    const dest=path.join(out,download.suggestedFilename());await download.saveAs(dest);
    assert(fs.readFileSync(dest,'utf8').includes("'=1+1"),'CSV formula treated as text '+route);
    await last.locator('[data-remove]').click();assert(await page.locator('#resource-table tbody tr').count()===original,'Remove row '+route);
   }
   await page.locator('#reset-resource').click();
   if(item.kind==='graphic')assert(await page.locator('[data-field="0"]').inputValue()===item.fields[0][1],'Reset graphic '+route);
   else assert(await page.locator('#resource-table tbody tr').count()===item.rows.length,'Reset rows '+route);
   await page.evaluate(()=>window.dispatchEvent(new Event('beforeprint')));
   assert(await page.locator('.print-output').count()===1,'Print output '+route);
   await page.emulateMedia({media:'print'});
   assert(await page.locator('.print-output').isVisible(),'Print visibility '+route);
   if(['basketball-senior-night-poster','basketball-media-day-interview-cards','basketball-senior-gift-budget'].includes(item.slug))await page.pdf({path:path.join(out,item.slug+'.pdf'),format:'A4',printBackground:true});
   await page.emulateMedia({media:'screen'});
  }
  const video=page.locator('video');await video.scrollIntoViewIfNeeded();
  await video.evaluate(v=>{v.load();v.muted=true;return v.play();});
  await page.waitForFunction(()=>document.querySelector('video').currentTime>0.15,{},{timeout:15000});
  assert(await video.evaluate(v=>v.duration>8.9&&v.duration<9.1),'Video duration '+route);
  await video.evaluate(v=>{v.pause();v.currentTime=6;});
  await page.waitForFunction(()=>Math.abs(document.querySelector('video').currentTime-6)<.1);
  assert(await page.locator('track').getAttribute('srclang')==='en','Video captions '+route);
  await page.setViewportSize({width:390,height:844});await page.evaluate(()=>scrollTo(0,0));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile overflow '+route);
  if(['/templates/basketball-senior-night-poster','/templates/basketball-clip-log','/templates/basketball-senior-gift-budget','/templates/basketball-media-day-interview-cards','/blog/how-to-film-basketball-games','/blog/basketball-senior-night-table-ideas'].includes(route)){
    await page.screenshot({path:path.join(out,route.split('/').pop()+'-mobile.png'),fullPage:true});
    await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:path.join(out,route.split('/').pop()+'-desktop.png'),fullPage:true});
  }
  await page.setViewportSize({width:1440,height:1000});results.push({path:route,http:200,mobileOverflow:false,video:'played and seeked',editor:item?.kind||'guide'});console.log('PASS',route);
 }
 // Progressive enhancement: essential content and original downloads work without JS.
 const plain=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
 for(const slug of ['basketball-senior-night-poster','basketball-clip-log']){
  const p=await plain.newPage();await p.goto('http://127.0.0.1:8767/templates/'+slug);assert(await p.locator('.fallback-download a').isVisible(),'No-JS original download');assert(await p.locator('noscript').isVisible(),'No-JS guidance');await p.close();
 }
 assert(errors.length===0,'Browser errors '+JSON.stringify(errors));assert(broken.length===0,'Broken resources '+JSON.stringify(broken));
 fs.writeFileSync(path.join(root,'reports/batch-one-browser.json'),JSON.stringify({status:'pass',results,errors,broken},null,2)+'\n');
 await browser.close();console.log('All 20 local pages passed editor/download/print/video/mobile checks.');
})().catch(e=>{console.error(e);process.exit(1);});
