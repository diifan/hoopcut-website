/* Check the actual timestamp-log workflow, exported drafts and shared editor regressions. */
const fs=require('fs'),path=require('path'),os=require('os');
const {chromium}=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const base='http://127.0.0.1:8767',out=path.resolve(__dirname,'../../seo/agent/runs/2026-11-02');
fs.mkdirSync(out,{recursive:true});
const assert=(ok,message)=>{if(!ok)throw Error(message);};
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 try{
  const context=await browser.newContext({acceptDownloads:true});const page=await context.newPage();
  const errors=[],broken=[],checks=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=400)broken.push(r.url());});
  for(const width of [320,390,768,1440]){
   await page.setViewportSize({width,height:950});
   const response=await page.goto(base+'/templates/basketball-clip-log');
   assert(response.status()===200&&response.headers()['x-robots-tag'].includes('noindex'),'Protected local preview');
   await page.locator('#clip-log-summary').waitFor({state:'visible'});
   assert(await page.locator('#clip-log-total').textContent()==='0:18','Initial 18-second total');
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No document overflow '+width);
   assert(await page.locator('h1').count()===1,'One H1');
   assert(await page.getByRole('region',{name:'Clip log fields, horizontally scrollable'}).getAttribute('tabindex')==='0','Keyboard-accessible horizontal table');
   assert(await page.locator('link[rel=canonical]').getAttribute('href')==='https://hoopcut.ai/templates/basketball-clip-log','Canonical');
   const graph=await page.locator('script[type="application/ld+json"]').evaluateAll(nodes=>nodes.flatMap(n=>JSON.parse(n.textContent)['@graph']||[]));
   assert(graph.some(n=>n['@type']==='WebPage'&&n.dateModified==='2026-11-02'),'Correct rendered modification date');
   assert(graph.some(n=>n['@type']==='BreadcrumbList'),'Breadcrumb schema');
   for(const image of await page.locator('main img').all()){
    await image.scrollIntoViewIfNeeded();await image.evaluate(img=>img.decode());
   }
   if(width===390||width===1440){
    await page.screenshot({path:path.join(out,'clip-log-page-'+width+'.png'),fullPage:true});
    await page.locator('#workspace').screenshot({path:path.join(out,'clip-log-workspace-'+width+'.png')});
   }
   checks.push('Initial result, metadata/schema, decoded images and layout '+width);
  }
  const input=(row,col)=>page.locator('#resource-table tbody tr').nth(row).locator('textarea').nth(col);
  await input(0,1).fill('02:10.500');await input(0,2).fill('02:18.250');
  assert(await page.locator('#clip-log-total').textContent()==='0:17.75','Decimal duration');
  await input(0,1).fill('1:02:10');await input(0,2).fill('1:02:18');
  assert(await page.locator('#clip-log-total').textContent()==='0:18','Hour format');
  await input(0,1).fill('90:00');await input(0,2).fill('90:10');
  assert(await page.locator('#clip-log-total').textContent()==='0:20','Long minutes');
  for(const invalid of ['1:60:00','02:61','130','-1:00','1:2','999999999999999999999:00']){
   await input(0,1).fill(invalid);
   assert(await input(0,1).getAttribute('aria-invalid')==='true','Reject '+invalid);
   assert(await page.locator('#clip-log-total').textContent()==='0:10','Exclude invalid row '+invalid);
  }
  await input(0,1).fill('02:10');
  for(const end of ['02:09','02:10']){
   await input(0,2).fill(end);
   assert(await page.locator('[data-clip-result]').first().textContent().then(t=>t.includes('later than start')),'Reject reversed/equal boundary');
  }
  await page.locator('#add-row').click();
  assert(await page.locator('#resource-table tbody tr').count()===3,'Add blank row');
  assert(await page.locator('#clip-log-count').textContent()==='1 valid clip · 1 row needs attention','Ignore blank row');
  await input(0,1).fill('01:70');await input(0,2).fill('02:18');await input(0,0).fill('=SUM(1,2)');
  const wait=page.waitForEvent('download');await page.locator('[data-export=csv]').click();
  const download=await wait;const csvPath=path.join(out,'clip-log-draft.csv');await download.saveAs(csvPath);
  const csv=fs.readFileSync(csvPath,'utf8');
  assert(csv.includes('"Duration (seconds)","Timing check"'),'Derived export columns');
  assert(csv.includes('Enter a valid start time.')&&csv.includes('"10","Ready"'),'Draft preserves errors and valid duration');
  assert(csv.includes("'=SUM(1,2)"),'CSV formula neutralized');
  assert(await page.locator('#editor-status').textContent().then(t=>t.includes('Draft downloaded')),'Draft feedback');
  await page.evaluate(()=>window.dispatchEvent(new Event('beforeprint')));
  const print=await page.locator('.print-output').textContent();
  assert(print.includes('Timing check')&&print.includes('Valid clips total: 0:10')&&print.includes('Enter a valid start time.'),'Print retains timing notes and subtotal');
  await page.locator('#reset-resource').click();
  assert(await page.locator('#resource-table tbody tr').count()===2&&await page.locator('#clip-log-total').textContent()==='0:18','Reset restores example');
  await input(0,1).fill('1:00');await input(0,2).fill('1:10');await input(1,1).fill('1:05');await input(1,2).fill('1:15');
  assert(await page.locator('#clip-log-total').textContent()==='0:20','Overlap counts independently');
  await page.locator('[data-remove]').last().click();
  assert(await page.locator('#clip-log-total').textContent()==='0:10','Remove updates total');
  await page.locator('[data-remove]').first().click();
  assert(await page.locator('#resource-table tbody tr').count()===1,'Retain one editable row');
  await input(0,0).fill('');
  assert(await input(0,0).getAttribute('aria-invalid')==='true'&&await page.locator('#clip-log-total').textContent()==='0:00','Missing filename excluded');
  checks.push('Decimal/hour/minute times, invalid inputs, reversed/equal boundaries, blank rows, missing file, overlap semantics, add/remove/reset, CSV and print');
  await page.goto(base+'/templates/basketball-senior-gift-budget');
  const original=await page.locator('#budget-total').textContent();
  await input(0,2).fill('-1');await page.locator('[data-export=csv]').click();
  assert(await page.locator('#editor-status').textContent().then(t=>t.includes('Correct the budget')),'Budget validation preserved');
  await page.locator('#reset-resource').click();assert(await page.locator('#budget-total').textContent()===original,'Budget reset preserved');
  await page.goto(base+'/templates/basketball-senior-night-poster');
  await page.locator('[data-field="0"]').fill('QA PLAYER');
  const svgWait=page.waitForEvent('download');await page.locator('[data-export=svg]').click();
  await (await svgWait).saveAs(path.join(out,'poster-regression.svg'));
  assert(fs.readFileSync(path.join(out,'poster-regression.svg'),'utf8').includes('QA PLAYER'),'Graphic editor/export preserved');
  checks.push('Shared budget validation/reset and poster SVG export preserved');
  const nojs=await browser.newContext({javaScriptEnabled:false});const fallback=await nojs.newPage();
  await fallback.goto(base+'/templates/basketball-clip-log');
  assert(await fallback.locator('#clip-log-summary').isHidden(),'No misleading no-JS result');
  const link=await fallback.locator('.fallback-download a').getAttribute('href');
  assert((await fallback.request.get(base+link)).status()===200,'Original CSV without JS');
  checks.push('No-JavaScript readable guide and original CSV available');
  assert(!errors.length&&!broken.length,JSON.stringify({errors,broken}));
  fs.writeFileSync(path.join(out,'browser-qa.json'),JSON.stringify({passed:true,checks,errors,broken},null,2)+'\n');
  console.log('PASS: clip-log calculations, draft exports/print, four viewport sizes, no-JS fallback and shared editor regressions.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
