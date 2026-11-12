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
test('single bounded fetch supplies identical preview/export blob',async()=>{let calls=0;const x=setup(async()=>{calls++;return new Response(new Uint8Array([1,2,3]));});await x.c.loadResultPreview('https://fixture.invalid',1);assert.equal(calls,1);assert.equal(x.video.src,'blob:result');assert.equal(x.c.exportURL,'blob:result');assert.deepEqual([...new Uint8Array(await x.c.exportBlob.arrayBuffer())],[1,2,3]);});
test('does not resolve until media loadeddata',async()=>{const x=setup(async()=>new Response('video'),false);let done=false;const p=x.c.loadResultPreview('remote',1).then(()=>done=true);await new Promise(r=>setTimeout(r,10));assert.equal(done,false);x.video.dispatchEvent(new Event('loadeddata'));await p;assert.equal(done,true);});
test('oversize known length avoids buffering and uses remote playback',async()=>{const x=setup(async()=>new Response('video',{headers:{'Content-Length':String(33*1024**2)}}));await x.c.loadResultPreview('remote',1);assert.equal(x.video.src,'remote');assert.equal(x.c.exportBlob,null);assert.equal(x.created.length,0);});
test('oversize unknown length cancels stream and uses remote playback',async()=>{let cancelled=false;const x=setup(async()=>new Response(new ReadableStream({start(c){c.enqueue(new Uint8Array(33*1024**2));},cancel(){cancelled=true;}})));await x.c.loadResultPreview('remote',1);assert.equal(cancelled,true);assert.equal(x.video.src,'remote');assert.equal(x.c.exportBlob,null);});
test('stale run cannot replace preview',async()=>{const x=setup(async()=>new Response('video'));x.c.epoch=2;await assert.rejects(x.c.loadResultPreview('remote',1),{name:'AbortError'});assert.equal(x.video.src,undefined);});
test('cancel while media loads revokes object URL',async()=>{const x=setup(async()=>new Response('video'),false);const p=x.c.loadResultPreview('remote',1);await new Promise(r=>setTimeout(r,10));x.abort();await assert.rejects(p,{name:'AbortError'});assert.deepEqual(x.revoked,['blob:result']);assert.equal(x.c.exportBlob,null);});
test('media error revokes object URL and rejects ready',async()=>{const x=setup(async()=>new Response('video'),false);const p=x.c.loadResultPreview('remote',1);await new Promise(r=>setTimeout(r,10));x.video.dispatchEvent(new Event('error'));await assert.rejects(p,/Could not play/);assert.deepEqual(x.revoked,['blob:result']);});
test('HTTP error and empty output fail before assigning preview',async()=>{for(const response of [new Response('bad',{status:500}),new Response('')]){const x=setup(async()=>response);await assert.rejects(x.c.loadResultPreview('remote',1));assert.equal(x.video.src,undefined);}});

test('indexed output buffers once for smooth local preview and export',async()=>{let calls=0;const x=setup(async()=>{calls++;return new Response('video')});await x.c.loadResultPreview('indexed-url',1,'mp4-faststart');assert.equal(calls,1);assert.equal(x.video.src,'blob:result');assert.equal(x.c.exportURL,'blob:result');assert.equal(await x.c.exportBlob.text(),'video')});
test('unknown container retains bounded blob compatibility',async()=>{let calls=0;const x=setup(async()=>{calls++;return new Response('video')});await x.c.loadResultPreview('remote',1,'unknown');assert.equal(calls,1);assert.equal(x.video.src,'blob:result')});
test('indexed cancellation cannot report ready',async()=>{const x=setup(async()=>new Response('video'),false);const p=x.c.loadResultPreview('remote',1,'mp4-faststart');x.abort();await assert.rejects(p,{name:'AbortError'});assert.equal(x.c.exportBlob,null);assert.equal(x.video.src,undefined)});
