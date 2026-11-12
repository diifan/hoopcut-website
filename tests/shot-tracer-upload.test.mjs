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


const hoopsSource=source.slice(source.indexOf('async function showHoops('),source.indexOf('async function upload()'));
async function selectionScenario(partial,overlapState=null){
 const elements={},calls=[];
 const make=()=>({hidden:false,disabled:false,style:{},children:[],classList:{add(){},remove(){}},setAttribute(){},replaceChildren(){this.children=[]},append(b){this.children.push(b)},querySelectorAll(){return this.children},getContext:()=>({drawImage(){},strokeRect(){}})});
 const c={cancelToUpload:async()=>{calls.push({action:'cancel',id:'fixture'});elements['hoop-panel'].hidden=true;},job:'fixture',rpc:async(action,id)=>calls.push({action,id}),choiceEpoch:0,hoopId:null,start:0,localURL:'blob:fixture',$:id=>elements[id]??=make(),document:{createElement:make},message(){},failure(e){throw e},process:()=>calls.push({hoopId:c.hoopId}),Math,Number,Array,JSON,Error,Promise,setTimeout,clearTimeout};
 Object.assign(c.$('preview'),{pause(){},src:'blob:fixture',readyState:4,currentTime:0,videoWidth:720,videoHeight:1280});
 vm.createContext(c);vm.runInContext(hoopsSource,c);
 await c.showHoops({partial,overlap_state:overlapState,candidates:[{id:'detected-one',frame:0,box:[.1,.2,.1,.1]}]});
 return {c,calls,elements};
}
test('partial selection offers full sampling without automatic confirmation',async()=>{
 const x=await selectionScenario(true);assert.equal(x.calls.length,0);assert.equal(x.elements['hoop-confirm'].disabled,true);
 assert.equal(x.elements['hoop-next'].hidden,false);assert.equal(x.elements['hoop-next'].textContent,'More frames');
 x.elements['hoop-next'].onclick();assert.deepEqual(x.calls,[{hoopId:null}]);
});
test('hoop requires click and explicit confirm',async()=>{
 const x=await selectionScenario(true);x.elements['hoop-confirm'].onclick();assert.equal(x.calls.length,0);
 x.elements['hoop-boxes'].children[0].onclick();assert.equal(x.elements['hoop-confirm'].disabled,false);
 assert.equal(x.calls.length,0);x.elements['hoop-confirm'].onclick();assert.deepEqual(x.calls,[{hoopId:'detected-one'}]);
});
test('complete single-frame selection hides next-frame action',async()=>{
 const x=await selectionScenario(false);assert.equal(x.elements['hoop-next'].hidden,true);assert.equal(x.calls.length,0);
});


test('processing task with early choice displays hoops without requeueing',async()=>{
 const x=await scenario({state:'processing',stage:'choosing_hoop',video:{duration:25},trim:[0,25],selection:{overlap_state:'waiting',candidates:[]}});
 assert.equal(x.failure,undefined);assert.deepEqual(x.calls,['create','complete','status','showHoops']);
});

test('cancel live choice requests cancellation of processing task',async()=>{
 const x=await selectionScenario(true,'waiting');await x.elements['hoop-cancel'].onclick();
 assert.deepEqual(x.calls,[{action:'cancel',id:'fixture'}]);assert.equal(x.elements['hoop-panel'].hidden,true);
});
test('cancel completed preflight also returns to upload',async()=>{
 const x=await selectionScenario(true);await x.elements['hoop-cancel'].onclick();
 assert.deepEqual(x.calls,[{action:'cancel',id:'fixture'}]);assert.equal(x.elements['hoop-panel'].hidden,true);
});

const resetSource=source.slice(source.indexOf('function resetToUpload()'),source.indexOf('async function showHoops('));
for(const reject of [false,true])test('cancel resets upload immediately, server rejection '+reject,async()=>{
 const elements={};let aborts=0,revoked=[],resolve;
 const c={epoch:4,choiceEpoch:1,activeUpload:{abort(){aborts++}},previewController:{abort(){aborts++}},busy:true,ready:true,localURL:'blob:input',file:{},job:'fixture',uploadRequest:{},hoopId:'old',hoopRange:'old',duration:30,start:0,end:30,lastAction:'process',phase:'selection',
 $:id=>elements[id]??={hidden:false,value:'old',classList:{add(){},remove(){}},pause(){},removeAttribute(){},load(){},scrollIntoView(){}},cleanExport(){},actions(){},message(){},URL:{revokeObjectURL:v=>revoked.push(v)},rpc:()=>new Promise((yes,no)=>{resolve=()=>reject?no(Error('offline')):yes({});})};
 vm.createContext(c);vm.runInContext(resetSource,c);const pending=c.cancelToUpload();
 assert.equal(elements.editor.hidden,true);assert.equal(elements['import-panel'].hidden,false);assert.equal(elements['video-file'].value,'');assert.equal(c.job,null);assert.equal(c.uploadRequest,null);assert.equal(c.busy,false);assert.equal(aborts,2);assert.deepEqual(revoked,['blob:input']);
 resolve();await pending;assert.equal(elements.editor.hidden,true);
});

test('hoop control follows actual rectangle without visible numbering',async()=>{
 const x=await selectionScenario(true);const b=x.elements['hoop-boxes'].children[0];
 assert.ok(!b.textContent);assert.equal(b.style.left,'10%');assert.equal(b.style.top,'20%');assert.equal(b.style.width,'10%');assert.equal(b.style.height,'10%');
 b.onclick();x.elements['hoop-confirm'].onclick();assert.deepEqual(x.calls,[{hoopId:'detected-one'}]);
});
