import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../assets/shot-tracer-tool.js',import.meta.url),'utf8');
const uploadSource=source.slice(source.indexOf('async function upload()'),source.indexOf('async function process()'));
async function scenario(state){
 const elements={};const calls=[];let failure;
 const c={epoch:0,busy:false,ready:false,lastAction:'',uploadRequest:null,file:{size:20},job:null,duration:0,start:0,end:0,hoopId:null,hoopRange:'',Date,Math,Number,Array,JSON,Error,crypto:{randomUUID:()=> 'fixture'},$:id=>elements[id]??=( {hidden:false,value:0}),message(){},actions(){},putVideo:async()=>{},rpc:async(action)=>{calls.push(action);return action==='create'?{id:'fixture',upload_url:'https://fixture.invalid'}:action==='status'?state:{}},process:async()=>calls.push('process'),showHoops:async()=>calls.push('showHoops'),updateTrim:()=>calls.push('updateTrim'),failure:e=>failure=e.message};
 vm.createContext(c);vm.runInContext(uploadSource,c);await c.upload();return {c,calls,failure,elements};
}
test('fused response shows selection without redundant process request',async()=>{
 const x=await scenario({state:'needs_hoop',video:{duration:25.666667},trim:[0,25.666667],selection:{candidates:[]}});
 assert.equal(x.failure,undefined);assert.deepEqual(x.calls,['create','complete','status','showHoops']);assert.equal(x.c.hoopId,null);assert.equal(x.c.lastAction,'process');assert.equal(x.c.hoopRange,JSON.stringify([0,25.666667]));assert.equal(x.c.busy,false);
});
test('old imported short-video response still starts preflight',async()=>{const x=await scenario({state:'imported',video:{duration:25}});assert.equal(x.failure,undefined);assert.equal(x.calls.at(-1),'process');});
test('long video still needs explicit trimming',async()=>{const x=await scenario({state:'imported',video:{duration:31}});assert.equal(x.calls.at(-1),'updateTrim');assert.equal(x.elements['trim-panel'].hidden,false);assert.ok(!x.calls.includes('process'));});
test('invalid fused range fails without selection or processing',async()=>{const x=await scenario({state:'needs_hoop',video:{duration:25},trim:[0,24],selection:{candidates:[]}});assert.match(x.failure,/range is invalid/);assert.ok(!x.calls.includes('process')&&!x.calls.includes('showHoops'));});

