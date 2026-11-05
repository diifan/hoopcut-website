/* Local candidate checks; no production writes or account sessions. */
const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert/strict');
const {execFileSync}=require('child_process');
const dep=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules');
const {chromium}=require(path.join(dep,'playwright'));const {expect}=require(path.join(dep,'playwright/test'));
const root=path.resolve(__dirname,'..'),out=path.join(root,'reports/video-angles');
const inventory=JSON.parse(fs.readFileSync(path.join(out,'inventory.json'))),base='http://127.0.0.1:8771';
const screenshots=path.join(out,'screenshots');fs.mkdirSync(screenshots,{recursive:true});
let browser;const created=[];
(async()=>{
 browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const a=await browser.newContext({viewport:{width:1280,height:1000}}),b=await browser.newContext({viewport:{width:390,height:844}});
 for(const c of [a,b])await c.route('**/*',r=>new URL(r.request().url()).hostname==='127.0.0.1'?r.continue():r.abort());
 const p=await a.newPage(),q=await b.newPage(),errors=[];for(const x of [p,q])x.on('pageerror',e=>errors.push(e.message));
 const titles=new Set(),descriptions=new Set(),bodies=new Set(),frames=new Set(),threads=new Set();
 for(const item of inventory.pages){
  const response=await p.goto(base+item.path);assert.equal(response.status(),200);assert(response.headers()['x-robots-tag'].includes('noindex'));
  await expect(p.locator('[data-comment-count]')).toHaveText('3 Comments');
  assert.equal(await p.locator('h1').count(),1);assert.equal(await p.locator('h1').textContent(),item.title);
  const title=await p.title(),desc=await p.locator('meta[name=description]').getAttribute('content');
  assert(!titles.has(title)&&!descriptions.has(desc));titles.add(title);descriptions.add(desc);
  assert.equal(await p.locator('link[rel=canonical]').getAttribute('href'),'https://hoopcut.ai'+item.path);
  frames.add(await p.locator('.watch-player iframe').getAttribute('src'));threads.add(await p.locator('[data-video-comments]').getAttribute('data-video-id'));
  assert.equal(await p.locator('.comment-example').count(),3);
  const text=await p.locator('#video-context').innerText();assert(!bodies.has(text));bodies.add(text);
  const graph=await p.locator('script[type="application/ld+json"]').first().textContent();const nodes=JSON.parse(graph)['@graph'];
  assert(nodes.some(x=>x['@type']==='VideoObject'&&x.embedUrl==='https://www.youtube.com/embed/MLcda_7VYkQ'));
  assert(nodes.some(x=>x['@type']==='BreadcrumbList'));
  assert.equal(await p.locator('.angle-worksheet input[type=checkbox]').count(),4);
  await p.locator('.angle-worksheet input').first().check();assert(await p.locator('.angle-worksheet input').first().isChecked());
  const download=await p.request.get(base+item.download);assert.equal(download.status(),200);assert((await download.text()).includes('Your notes'));
  assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await q.goto(base+item.path);await expect(q.locator('[data-comment-count]')).toHaveText('3 Comments');
  assert(await q.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  const frame=await q.locator('.watch-player iframe').boundingBox();assert(frame.width>=200&&frame.height>=200);
  for(const page of [p,q]){
   await page.addStyleTag({content:'html{scroll-behavior:auto!important}'});
   await page.evaluate(()=>document.querySelector('#video-context').scrollIntoView({block:'start'}));
   await page.screenshot({path:path.join(screenshots,item.slug+'-'+(page===p?'desktop':'mobile')+'.png')});
  }
 }
 assert.equal(titles.size,10);assert.equal(descriptions.size,10);assert.equal(frames.size,1);assert.equal(threads.size,10);
 // A real write to page one must not appear in page two's thread.
 const first=inventory.pages[0],second=inventory.pages[1];
 const receipt=await a.request.post(base+'/api/comments?'+new URLSearchParams({video:first.thread}),{data:{body:'Local QA thread isolation check',name:'Local QA',request_id:require('crypto').randomUUID()}});
 assert.equal(receipt.status(),200);const cid=(await receipt.json()).comment_id;created.push(cid);
 const one=await (await a.request.get(base+'/api/comments?'+new URLSearchParams({video:first.thread}))).json();
 const two=await (await b.request.get(base+'/api/comments?'+new URLSearchParams({video:second.thread}))).json();
 assert(one.comments.some(c=>c.id===cid));assert(!two.comments.some(c=>c.id===cid));assert.equal(two.total,3);
 const shared=await (await b.request.get(base+'/api/comments?'+new URLSearchParams({video:first.thread}))).json();assert(shared.comments.some(c=>c.id===cid));
 await p.goto(base+'/videos');assert.equal(await p.locator('.video-tile').count(),10);
 await p.screenshot({path:path.join(screenshots,'hub-desktop.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 const result={status:'pass',pages:10,uniqueTitles:10,uniqueDescriptions:10,uniqueBodies:10,actualVideoUrls:1,independentCommentThreads:10,sampleComments:30,realCrossVisitorThreadIsolation:true,editableChecklists:10,downloadableWorksheets:10,desktopAndMobile:true,jsErrors:errors,productionWrites:0};
 fs.writeFileSync(path.join(out,'browser-checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(async()=>{
 if(browser)await browser.close();
 if(created.length)execFileSync('python3',['-c','import sqlite3,json,sys; c=sqlite3.connect(sys.argv[1]); ids=json.loads(sys.argv[2]); [c.execute("DELETE FROM hc_comments WHERE id=?",(i,)) for i in ids]; c.commit()',path.join(out,'comments.sqlite3'),JSON.stringify(created)]);
});
