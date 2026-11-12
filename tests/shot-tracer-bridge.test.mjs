import test from 'node:test';import assert from 'node:assert/strict';import {proxy} from '../lib/shot-tracer-bridge.js';
function res(){return {headers:{},setHeader(k,v){this.headers[k]=v},end(v){this.body=JSON.parse(v)}}}
function req(body,more={}){return {method:'POST',headers:{host:'example.vercel.app',origin:'https://example.vercel.app'},body,...more}}
test('public rejects worker action without contacting upstream',async()=>{process.env.HC_TRACER_WEB_SECRET='test-only-secret';let r=res();await proxy(req({action:'poll'}),r);assert.equal(r.statusCode,400)});
test('cross-origin rejected',async()=>{let r=res();await proxy(req({action:'status'},{headers:{host:'example.vercel.app',origin:'https://evil.test'}}),r);assert.equal(r.statusCode,403)});
test('GET rejected',async()=>{let r=res();await proxy(req({},{method:'GET'}),r);assert.equal(r.statusCode,405)});
test('worker requires bearer',async()=>{let r=res();await proxy(req({action:'poll'}),r,true);assert.equal(r.statusCode,401)});
test('worker cannot invoke browser create',async()=>{let r=res();await proxy(req({action:'create'},{headers:{authorization:'Bearer '+'x'.repeat(48)}}),r,true);assert.equal(r.statusCode,400)});
test('body limited',async()=>{let r=res();await proxy(req({action:'status',padding:'x'.repeat(20000)}),r);assert.equal(r.statusCode,400)});
test('server selects staging, does not trust client environment or rate key',async()=>{
 process.env.VERCEL_ENV='preview';process.env.VERCEL='1';const previous=globalThis.fetch;let sent;
 globalThis.fetch=async(url,options)=>{sent=JSON.parse(options.body);return {status:200,json:async()=>({id:'fixture'})}};
 try{let r=res();let q=req({action:'create',environment:'production',data:{rate_key:'forged',size_bytes:4}});q.headers['x-vercel-forwarded-for']='192.0.2.1';await proxy(q,r);assert.equal(r.statusCode,200);assert.equal(sent.environment,'staging');assert.match(sent.data.rate_key,/^[a-f0-9]{64}$/);assert.notEqual(sent.data.rate_key,'forged');assert.equal(r.headers['Cache-Control'],'no-store')}finally{globalThis.fetch=previous}
});
for(const [environment,enabled,suffix] of [['preview','1','shot-tracer-overlap-staging'],['preview','0','shot-tracer-bridge'],['production','1','shot-tracer-overlap-production'],['production','0','shot-tracer-overlap-production']]){
 test('endpoint isolation '+environment+' flag '+enabled,async()=>{
  const previous=globalThis.fetch,oldEnv=process.env.VERCEL_ENV,oldFlag=process.env.HC_TRACER_FAST_STAGING;let target,sent,sentHeaders;
  process.env.VERCEL_ENV=environment;process.env.HC_TRACER_FAST_STAGING=enabled;
  globalThis.fetch=async(url,options)=>{target=url;sentHeaders=options.headers;sent=JSON.parse(options.body);return {status:200,json:async()=>({state:'imported'})}};
  try{const r=res();await proxy(req({action:'status',id:'a'.repeat(48)}),r);assert.equal(r.statusCode,200);assert.equal(new URL(target).pathname.split('/').at(-1),suffix);assert.equal(sent.environment,environment==='production'?'production':'staging');const pinned=environment==='production'||enabled==='1';assert.equal(sentHeaders['x-region'],pinned?'ap-southeast-1':undefined);assert.equal(new URL(target).searchParams.get('forceFunctionRegion'),pinned?'ap-southeast-1':null);}
  finally{globalThis.fetch=previous;oldEnv===undefined?delete process.env.VERCEL_ENV:process.env.VERCEL_ENV=oldEnv;oldFlag===undefined?delete process.env.HC_TRACER_FAST_STAGING:process.env.HC_TRACER_FAST_STAGING=oldFlag;}
 });
}
