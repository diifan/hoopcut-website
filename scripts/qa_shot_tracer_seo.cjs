const path=require('node:path');
const fs=require('node:fs');
const os=require('node:os');
const assert=require('node:assert/strict');
const {chromium}=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 try {
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const out=path.join(__dirname,'../reports/shot-tracer-seo');fs.mkdirSync(out,{recursive:true});
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:900});const response=await page.goto('http://127.0.0.1:8794/shot-tracer');
   assert.equal(response.status(),200);assert.match(response.headers()['x-robots-tag'],/noindex/);
   assert.equal(await page.locator('h1').count(),1);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   assert.equal(await page.locator('#status-title').count(),1); // real runtime initialized
   const chooser=page.waitForEvent('filechooser');await page.locator('#choose').click();await chooser;
   await page.locator('summary').first().click();assert.notEqual(await page.locator('details').first().getAttribute('open'),null);
   const schemas=await page.locator('script[type="application/ld+json"]').allTextContents();
   assert.deepEqual(schemas.map(s=>JSON.parse(s)['@type']).sort(),['BreadcrumbList','WebApplication']);
   await page.screenshot({path:path.join(out,`page-${width}.png`),fullPage:true});
  }
  for(const route of ['/tools','/demo/shot-tracer','/blog/how-to-add-shot-tracer-to-basketball-video']){
   await page.goto('http://127.0.0.1:8794'+route);assert.equal(await page.locator('#shot-tracer-upload-link a').getAttribute('href'),'/shot-tracer');
  }
  const response=await page.goto('http://127.0.0.1:8794/shot-tracer/not-a-real-workflow');assert.equal(response.status(),404);
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'qa.json'),JSON.stringify({status:'pass',widths:[1440,390],runtimeInitialized:true,fileChooser:true,faq:true,inboundLinks:3,invalidSlug:404,productionProcessingTested:false},null,2));
  console.log('PASS actual runtime initialization, file chooser, FAQ, schema, desktop/mobile, inbound links and invalid slug');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
