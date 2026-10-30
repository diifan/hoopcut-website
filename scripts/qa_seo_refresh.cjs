/* Local-only checks for the October 30 editorial refresh. */
const fs=require('fs'),path=require('path'),os=require('os');
const {chromium}=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const base='http://127.0.0.1:8767';
const out=path.resolve(__dirname,'../../seo/agent/runs/2026-10-30');
fs.mkdirSync(out,{recursive:true});
const routes=['how-to-make-a-basketball-highlight-video','how-to-add-shot-tracer-to-basketball-video','how-to-make-a-basketball-recruiting-video'];
const assert=(ok,message)=>{if(!ok)throw Error(message);};
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 try{
  const context=await browser.newContext();const page=await context.newPage();
  const errors=[],broken=[],results=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)broken.push({url:r.url(),status:r.status()});});
  for(const width of [320,390,768,1440]){
   await page.setViewportSize({width,height:900});
   for(const slug of routes){
    const route='/blog/'+slug;
    const response=await page.goto(base+route);
    assert(response.status()===200,'HTTP '+route);
    assert(response.headers()['x-robots-tag'].includes('noindex'),'Local draft protection');
    await page.waitForFunction(()=>[...document.querySelectorAll('link[rel=stylesheet]')].every(l=>l.sheet));
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Overflow '+width+' '+route);
    assert(await page.locator('h1').count()===1,'One H1 '+route);
    assert(await page.locator('link[rel=canonical]').getAttribute('href')==='https://hoopcut.ai'+route,'Canonical '+route);
    const graphs=await page.locator('script[type="application/ld+json"]').evaluateAll(nodes=>nodes.flatMap(n=>{const s=JSON.parse(n.textContent);return s['@graph']||[s];}));
    assert(graphs.some(n=>n['@type']==='BlogPosting'&&n.dateModified.startsWith('2026-10-30')),'Article modified date '+route);
    assert(graphs.some(n=>n['@type']==='BreadcrumbList'),'Breadcrumb schema '+route);
    assert(await page.locator('.breadcrumbs [aria-current=page]').count()===1,'Visible breadcrumb '+route);
    assert(await page.locator('.product-note a').getAttribute('href').then(h=>h.endsWith('/id6824860341')),'Official app CTA '+route);
    if(width===390||width===1440)await page.screenshot({path:path.join(out,slug+'-'+width+'.png')});
    const gallery=page.locator('.evidence-gallery');
    const images=[];
    if(await gallery.count()){
     assert(await page.locator('.on-this-page a[href="#visual-example"]').count()===1,'Gallery in table of contents');
     for(const image of await gallery.locator('img').all()){
      await image.scrollIntoViewIfNeeded();
      await image.evaluate(img=>img.decode());
      const state=await image.evaluate(img=>({src:img.currentSrc,width:img.naturalWidth,rendered:img.getBoundingClientRect().width,alt:img.alt,loading:img.loading,sizes:img.sizes}));
      assert(state.width>0&&state.alt.length>20&&state.loading==='lazy','Decoded descriptive image '+route);
      assert(state.src.includes('/assets/optimized/'),'Responsive WebP '+route);
      images.push(state);
     }
     if(width===390||width===1440)await gallery.screenshot({path:path.join(out,slug+'-gallery-'+width+'.png')});
     const link=gallery.locator('.evidence-grid a').first();
     const destination=await link.getAttribute('href');
     await link.click();await page.waitForURL(base+destination);
     assert(page.url()===base+destination,'Full-size image opens');
     await page.goto(base+route);
    }
    if(width===390&&slug===routes[0]){
     const video=page.locator('.guide-demo video');
     await video.evaluate(v=>v.load());
     await page.waitForFunction(()=>document.querySelector('.guide-demo video').readyState>=1);
     assert(Math.abs(await video.evaluate(v=>v.duration)-52)<.15,'Complete 52-second prepared reel');
    }
    results.push({route,width,images,passed:true});
   }
  }
  assert(!errors.length&&!broken.length,'Runtime errors or missing assets: '+JSON.stringify({errors,broken}));
  fs.writeFileSync(path.join(out,'browser-qa.json'),JSON.stringify({passed:true,results,errors,broken},null,2)+'\n');
  console.log('PASS: three guides at four widths; metadata/schema, breadcrumbs, decoded responsive images, full-size links, App Store CTA and complete prepared video.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
