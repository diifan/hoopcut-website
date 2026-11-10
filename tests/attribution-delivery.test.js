import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {webcrypto} from 'node:crypto';
const source=readFileSync(process.env.ATTRIBUTION_SCRIPT || new URL('../assets/attribution.js',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function harness(saved=new Map(),sdk=false) {
 const requests=[],timers=new Map(),docListeners={},winListeners={}; let seq=0;
 const storage={getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v)};
 const doc={visibilityState:'visible',hidden:false,referrer:'',querySelector:s=>s==='#attribution-settings'?{textContent:JSON.stringify({environment:'staging',oneLinkBaseURL:'https://hoopcut.onelink.me/SDN0',oneLinkHosts:['hoopcut.onelink.me']})}:null,querySelectorAll:()=>[],addEventListener:(n,f)=>{(docListeners[n]??=[]).push(f)}};
 const win={addEventListener:(n,f)=>{(winListeners[n]??=[]).push(f)}};
 if(sdk)win.AF_SMART_SCRIPT={generateOneLinkURL:()=>({clickURL:'https://hoopcut.onelink.me/SDN0?af_js_web=true&af_ss_ver=2_10_4'})};
 const context={window:win,document:doc,location:{href:'https://preview.invalid/',hostname:'preview.invalid',pathname:'/',search:''},history:{pushState(){},replaceState(){}},crypto:webcrypto,URL,TextEncoder,AbortSignal,Date,sessionStorage:storage,localStorage:storage,setTimeout:(f,ms)=>{timers.set(++seq,{f,ms});return seq},clearTimeout:id=>timers.delete(id),requestAnimationFrame:f=>f(),fetch:(_url,opts)=>new Promise(resolve=>requests.push({opts,events:JSON.parse(opts.body).events,resolve}))};
 vm.runInNewContext(source,context);
 const runTimer=()=>{const first=timers.entries().next().value;if(first){timers.delete(first[0]);void first[1].f();}};
 const click=(cta='hero_download')=>{const a={dataset:{attributionCta:cta},href:'https://apps.apple.com/app/id6824860341'}; const e={type:'click',button:0,defaultPrevented:false,target:{closest:s=>s==='a[data-attribution-cta]'?a:null},preventDefault(){this.defaultPrevented=true}};for(const f of docListeners.click||[])f(e);assert.equal(e.defaultPrevented,false);return a;};
 const respond=(r,status=200,body)=>r.resolve({ok:status===200,status,headers:{get:()=>null},json:async()=>body||{accepted_event_ids:r.events.map(x=>x.event_id),duplicate_event_ids:[],rejected:[]}});
 return {requests,saved,runTimer,click,respond,hide(){doc.hidden=true;doc.visibilityState='hidden';for(const f of docListeners.visibilitychange||[])f();for(const f of winListeners.pagehide||[])f();},queue:()=>JSON.parse(saved.get('hoopcut.attribution.v1.staging.queue')||'[]')};
}
test('download dispatches synchronously while page_view fetch is unresolved; navigation stays native',()=>{
 const h=harness();h.runTimer();assert.equal(h.requests.length,1);h.click();
 assert.equal(h.requests.length,2,'download must not wait for page_view response or timers');
 assert.equal(h.requests[1].events[0].event_name,'download_clicked');assert.equal(h.requests[1].opts.keepalive,true);h.hide();assert.equal(h.requests.length,2,'lifecycle must not duplicate in-flight events');
});
test('all CTA variants send immediately with fallback or OneLink and matching click_id',()=>{
 for(const sdk of [false,true])for(const cta of ['header_download','hero_download','video_detail_download','footer_download','mobile_sticky_download','article_download','resource_download']){
  const h=harness(new Map(),sdk);h.runTimer();const a=h.click(cta),r=h.requests.find(r=>r.events.some(e=>e.event_name==='download_clicked'));assert.ok(r);const e=r.events.find(e=>e.event_name==='download_clicked');assert.equal(e.cta_id,cta);assert.equal(e.destination_type,sdk?'onelink':'app_store_fallback');if(sdk)assert.equal(new URL(a.href).searchParams.get('af_sub1'),e.click_id);
 }
});
test('503 keeps exact IDs/payload for retry and reload; accepting click does not clear pending page view',async()=>{
 const h=harness();h.runTimer();h.click();const first=h.requests[1];assert.ok(first);h.respond(first,503);await tick();const queued=h.queue().find(e=>e.event_name==='download_clicked');assert.deepEqual(queued,first.events[0]);
 const reloaded=harness(h.saved);reloaded.runTimer();const retry=reloaded.requests[0];assert.deepEqual(retry.events.find(e=>e.event_id===queued.event_id),queued);
 const another=harness();another.runTimer();another.click();another.respond(another.requests[1]);await tick();assert.equal(another.queue().length,1);assert.equal(another.queue()[0].event_name,'page_view');
});
test('unrelated or malformed receipt cannot discard events; duplicate acknowledged by ID',async()=>{
 const h=harness();h.runTimer();h.click();const r=h.requests[1];assert.ok(r);const pageID=h.requests[0].events[0].event_id;
 h.respond(r,200,{accepted_event_ids:[pageID],duplicate_event_ids:[],rejected:[]});await tick();assert.equal(h.queue().length,2);
 const h2=harness();h2.runTimer();h2.click();const r2=h2.requests[1];h2.respond(r2,200,{accepted_event_ids:[],duplicate_event_ids:r2.events.map(e=>e.event_id),rejected:[]});await tick();assert.equal(h2.queue().length,1);
});
test('concurrency is bounded and further clicks remain queued with distinct IDs',()=>{
 const h=harness();h.runTimer();for(let i=0;i<5;i++)h.click();assert.equal(h.requests.length,2);const clicks=h.queue().filter(e=>e.event_name==='download_clicked');assert.equal(clicks.length,5);assert.equal(new Set(clicks.map(e=>e.click_id)).size,5);
});
