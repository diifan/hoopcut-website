import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
const source=fs.readFileSync('assets/shot-tracer-tool.js','utf8');
const helper=source.slice(source.indexOf('let previewController='),source.indexOf('async function upload()'));
function setup(fetcher,auto=true){
 const video=new EventTarget();video.removeAttribute=k=>{delete video[k]};video.load=()=>{if(auto)queueMicrotask(()=>video.dispatchEvent(new Event('loadeddata')));};
 const created=[],revoked=[];const c={epoch:1,exportBlob:null,exportURL:null,AbortController,DOMException,Blob,Number,Promise,Error,setTimeout,clearTimeout,fetch:fetcher,$:()=>video,URL:{createObjectURL:b=>{created.push(b);return 'blob:result'},revokeObjectURL:u=>revoked.push(u)}};
 vm.createContext(c);vm.runInContext(helper,c);return {c,video,created,revoked,abort:()=>vm.runInContext('previewController?.abort()',c)};
}
test('first frame readiness never waits for full fetch or Blob',async()=>{let calls=0;const x=setup(()=>{calls++;return new Promise(()=>{});});await x.c.loadResultPreview('remote',1,'mp4-faststart');assert.equal(calls,0);assert.equal(x.video.src,'remote');assert.equal(x.video.preload,'auto');assert.equal(x.c.exportBlob,null);assert.equal(x.c.exportURL,null);assert.equal(x.created.length,0);});
test('does not resolve until media loadeddata',async()=>{const x=setup(null,false);let done=false;const p=x.c.loadResultPreview('remote',1).then(()=>done=true);await new Promise(r=>setTimeout(r,10));assert.equal(done,false);x.video.dispatchEvent(new Event('loadeddata'));await p;assert.equal(done,true);});
test('stale run cannot replace preview',async()=>{const x=setup(null);x.c.epoch=2;await assert.rejects(x.c.loadResultPreview('remote',1),{name:'AbortError'});assert.equal(x.video.src,undefined);});
test('cancel releases media request and cannot report ready',async()=>{const x=setup(null,false);const p=x.c.loadResultPreview('remote',1);x.abort();await assert.rejects(p,{name:'AbortError'});assert.equal(x.video.src,undefined);assert.equal(x.c.exportBlob,null);});
test('media error rejects readiness and clears source',async()=>{const x=setup(null,false);const p=x.c.loadResultPreview('remote',1);x.video.dispatchEvent(new Event('error'));await assert.rejects(p,/Could not play/);assert.equal(x.video.src,undefined);});
test('newer epoch after loadeddata cannot publish ready',async()=>{const x=setup(null,false);const p=x.c.loadResultPreview('remote',1);x.c.epoch=2;x.video.dispatchEvent(new Event('loadeddata'));await assert.rejects(p,{name:'AbortError'});assert.equal(x.c.exportURL,null);});
