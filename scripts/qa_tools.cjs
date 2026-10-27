/* Validate the local Home -> Tools -> editor -> Blog journey in an isolated profile. */
const fs=require('fs'),path=require('path'),os=require('os');
const {chromium}=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const root=path.resolve(__dirname,'..'),base='http://127.0.0.1:8767';
const output=path.join(root,'reports/tools');fs.mkdirSync(output,{recursive:true});
const assert=(yes,msg)=>{if(!yes)throw Error(msg);};
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],broken=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)broken.push({url:r.url(),status:r.status()});});
 await page.goto(base+'/');
 await page.locator('#site-navigation a[href="/tools"]').click();
 await page.waitForURL(base+'/tools');
 assert(await page.locator('[data-tool]').count()===15,'Tool catalog count');
 const links=[...new Set(await page.locator('[data-tool] h3 a').evaluateAll(a=>a.map(x=>x.getAttribute('href'))))];
 assert(links.length===15,'Unique tool links');
 for(const link of links){const response=await page.request.get(base+link);assert(response.status()===200,'Tool HTTP '+link);assert(response.headers()['x-robots-tag'].includes('noindex'),'Local preview protection');}
 const title=await page.title();assert(title.includes('Basketball Tools'),'Tools title');
 const schema=await page.locator('script[type="application/ld+json"]').textContent();
 assert(JSON.parse(schema)['@graph'].some(x=>x['@type']==='ItemList'&&x.numberOfItems===15),'Tools structured data');
 await page.locator('#tool-search').fill('poster');assert(await page.locator('[data-tool]:visible').count()===1,'Poster search');
 await page.locator('#clear-search').click();await page.locator('[data-filter="design-print"]').click();assert(await page.locator('[data-tool]:visible').count()===6,'Design filter');
 await page.locator('#tool-search').fill('unknown-zzzz');assert(await page.locator('#no-tools').isVisible(),'No-results guidance');
 await page.locator('#clear-search').click();assert(await page.locator('[data-tool]:visible').count()===15,'Clear search/category');
 await page.locator('#tool-search').fill('media day');assert(await page.locator('[data-tool]:visible').count()===2,'Multiword search');await page.locator('#clear-search').click();
 // Load the lazy previews before capturing a full-page visual record.
 await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});
 for(const image of await page.locator('.tool-card img').all()){await image.scrollIntoViewIfNeeded();await image.evaluate(img=>img.decode());}
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(output,'directory-desktop.png'),fullPage:true});
 await page.locator('[data-tool] h3 a[href="/templates/basketball-reel-cover"]').click();
 await page.waitForURL(base+'/templates/basketball-reel-cover');
 await page.locator('.breadcrumbs a[href="/tools"]').click();await page.waitForURL(base+'/tools');
 await page.locator('.blog-header nav a[href="/blog"]').click();await page.waitForURL(base+'/blog');
 assert(await page.locator('#templates .card').count()===3,'Blog has a short tool bridge');
 await page.locator('#templates .section-label a[href="/tools"]').click();await page.waitForURL(base+'/tools');
 await page.setViewportSize({width:390,height:844});
 for(const route of ['/tools','/blog','/demo/auto-clipping','/demo/shot-tracer','/terms','/privacy']){
   await page.goto(base+route);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile overflow '+route);
   if(route==='/tools'){
    await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});
    for(const image of await page.locator('.tool-card img').all()){await image.scrollIntoViewIfNeeded();await image.evaluate(img=>img.decode());}
    await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(output,'directory-mobile.png'),fullPage:true});
   }
 }
 await page.goto(base+'/');
 await page.locator('.nav-toggle').click();assert(await page.locator('.nav-toggle').getAttribute('aria-expanded')==='true','Mobile menu opens');
 await page.locator('#site-navigation a[href="/tools"]').click();await page.waitForURL(base+'/tools');
 await page.goto(base+'/');await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});
 for(const image of await page.locator('#tools img').all()){await image.scrollIntoViewIfNeeded();await image.evaluate(img=>img.decode());}
 await page.locator('#tools').screenshot({path:path.join(output,'home-entry-mobile.png')});
 await page.setViewportSize({width:1440,height:1000});await page.locator('#tools').screenshot({path:path.join(output,'home-entry-desktop.png')});
 const plain=await browser.newContext({javaScriptEnabled:false});const nojs=await plain.newPage();await nojs.goto(base+'/tools');assert(await nojs.locator('[data-tool]:visible').count()===15,'No-JS discovery');assert(!await nojs.locator('#tool-search-controls').isVisible(),'No-JS search hidden');
 assert(errors.length===0,'JS errors '+JSON.stringify(errors));assert(broken.length===0,'Missing assets '+JSON.stringify(broken));
 fs.writeFileSync(path.join(root,'reports/tools-journey.json'),JSON.stringify({status:'pass',toolCount:15,journey:'Home -> Tools -> editor -> Tools -> Blog',search:'poster, media day, empty state and clear',mobile:'menu and layout passed',noJavaScript:'all 15 tools crawlable and accessible',errors,broken},null,2)+'\n');
 await browser.close();console.log('PASS: Tools journey, 15 unique working tools, search/filter/clear, schema, mobile navigation, lazy images, no-JS discovery.');
})().catch(error=>{console.error(error);process.exit(1);});
