import {COURTS,courtSVG,layout,clamp,shotValue,shotZone,summarize,escapeXML} from './geometry.js';

const config=JSON.parse(document.querySelector('#court-tool-data').textContent);
const chart=config.mode==='shots',slug=config.slug,key='hoopcut:'+slug+':v1';
const $=s=>document.querySelector(s),svg=$('#court-svg'),history=[];
let tool='player',result=true,pendingArrow=null,drag=null,started=false,storageAvailable=true;
const uid=()=>crypto.randomUUID();
function fresh(){return {version:1,standard:'nba',view:chart?'half':'full',units:'ft',theme:'wood',dimensions:!chart,title:chart?'My shooting session':'Evening run',items:[],example:false};}
let state=fresh();
function sample(){
  const c=COURTS[state.standard];
  if(chart){const points=[[.5,.14,true],[.48,.2,true],[.52,.24,false],[.2,.4,true],[.74,.5,false],[.08,.13,true],[.92,.14,false],[.51,.7,true],[.37,.74,false],[.63,.71,true],[.3,.46,true],[.65,.4,false],[.48,.12,true],[.13,.35,false],[.87,.34,true]];
    return points.map(([x,y,made],i)=>({id:uid(),type:'shot',number:i+1,x:x*c.width,y:y*c.length/2,made,isExample:true,at:new Date().toISOString()}));}
  return [{id:uid(),type:'player',label:'1',x:c.width*.42,y:c.length*.18},{id:uid(),type:'player',label:'2',x:c.width*.73,y:c.length*.34},{id:uid(),type:'ball',x:c.width*.48,y:c.length*.16},{id:uid(),type:'camera',x:c.width*.94,y:c.length*.48},{id:uid(),type:'arrow',x:c.width*.46,y:c.length*.2,x2:c.width*.64,y2:c.length*.31}];
}
function validStored(v){
  if(!v||v.version!==1||!COURTS[v.standard]||!['half','full'].includes(v.view)||!['ft','m'].includes(v.units)||!['wood','ink'].includes(v.theme)||typeof v.title!=='string'||v.title.length>60||!Array.isArray(v.items)||v.items.length>500)throw Error('Unsupported draft');
  const c=COURTS[v.standard],types=chart?['shot']:['player','camera','ball','arrow'];
  for(const m of v.items){if(!types.includes(m.type)||typeof m.id!=='string'||!/^[A-Za-z0-9-]{1,60}$/.test(m.id)||!Number.isFinite(m.x)||!Number.isFinite(m.y)||m.x<0||m.x>c.width||m.y<0||m.y>c.length)throw Error('Invalid point');
    if(m.type==='arrow'&&(!Number.isFinite(m.x2)||!Number.isFinite(m.y2)||m.x2<0||m.x2>c.width||m.y2<0||m.y2>c.length))throw Error('Invalid arrow');
    if(m.type==='shot'&&(typeof m.made!=='boolean'||!Number.isInteger(m.number)||m.number<1))throw Error('Invalid shot');
    if(m.type==='player'&&(typeof m.label!=='string'||m.label.length>3))throw Error('Invalid player');
  }
  if(new Set(v.items.map(m=>m.id)).size!==v.items.length)throw Error('Duplicate point');
  delete v.cursor;v.dimensions=Boolean(v.dimensions);if(chart)v.view='half';return v;
}
try{const raw=localStorage.getItem(key);if(raw&&raw.length<180000)state=validStored(JSON.parse(raw));else if(!chart){state.items=sample();state.example=true;}}catch{storageAvailable=false;}
function track(name,format){if(typeof window.hoopcutTrack==='function')window.hoopcutTrack(name,{tool:slug,...(format?{format}:{})});}
function begin(){if(!started){track('tool_start');started=true;}}
function announce(message){$('#studio-status').textContent=message;}
function save(){try{localStorage.setItem(key,JSON.stringify(state));storageAvailable=true;}catch{storageAvailable=false;}$('#local-save').textContent=storageAvailable?'Saved on this device':'Download to keep your work';}
function checkpoint(){history.push(JSON.stringify(state));if(history.length>50)history.shift();}
function change(fn,message){begin();checkpoint();fn();state.example=false;pendingArrow=null;render();save();if(message)announce(message);}
function displayStats(){
  if(!chart)return;
  const stats=summarize(state.standard,state.items),pct=stats.percentage;
  $('#shot-fg').innerHTML=pct===null?'—':pct+'<small>%</small>';
  $('#shot-made').textContent=stats.made;$('#shot-attempts').textContent=stats.attempts;
  for(const [selector,v] of [['#shot-two',stats.two],['#shot-three',stats.three]])$(selector).textContent=`${v.made}/${v.attempts}`;
  const zones=['At the rim','Paint','Mid-range','Left three','Above-break three','Right three'];
  $('#shot-zones').innerHTML=zones.map(z=>{const a=stats.zones[z]||{made:0,attempts:0};return `<div class="zone-line"><span>${z}</span><b>${a.made}/${a.attempts}${a.attempts?' · '+Math.round(a.made/a.attempts*100)+'%':''}</b></div>`;}).join('');
  $('#shot-empty').hidden=state.items.length>0;$('#shot-log-table').hidden=state.items.length===0;
  $('#shot-table-body').innerHTML=state.items.slice(-12).reverse().map(m=>`<tr><td>#${m.number}</td><td><button data-toggle-shot="${m.id}" aria-label="Change result of shot ${m.number}">${m.made?'● Made':'× Missed'}</button></td><td>${shotValue(state.standard,m)} PT</td><td class="log-zone">${shotZone(state.standard,m)}</td><td><button data-remove-shot="${m.id}" aria-label="Remove shot ${m.number}">Remove</button></td></tr>`).join('');
  $('#log-count').textContent=`${state.items.length} ${state.items.length===1?'shot':'shots'}`;
  $('#print-summary').textContent=`${state.example?'DEMO DATA · ':''}${stats.made}/${stats.attempts} made · FG ${pct===null?'—':pct+'%'} · 2PT ${stats.two.made}/${stats.two.attempts} · 3PT ${stats.three.made}/${stats.three.attempts}`;
}
function render(){
  if(chart)state.example=state.items.some(m=>m.isExample===true);
  const output=courtSVG(state);svg.setAttribute('viewBox',output.viewBox);svg.innerHTML=output.content;
  $('#court-frame').className='court-frame '+state.view+(state.theme==='ink'?' ink':'');
  $('#court-standard').value=state.standard;$('#court-units').value=state.units;$('#show-dimensions').checked=state.dimensions;
  $('#session-title').value=state.title;$('#drawing-title').textContent=state.title|| (chart?'Shooting session':'Court plan');
  $('#session-badge').textContent=state.example?(chart?'Includes demo shots':'Example plan'):(chart?'Your session':'Your plan');
  $('#court-reference').textContent=COURTS[state.standard].name+' / '+(state.view==='full'?'FULL COURT':'HALF COURT');
  document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===state.view)));
  document.querySelectorAll('[data-theme]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.theme===state.theme)));
  $('#undo-court').disabled=history.length===0;$('#clear-court').disabled=state.items.length===0;
  $('#print-heading').textContent=(state.title||'Basketball '+(chart?'shot chart':'court diagram'))+' · '+COURTS[state.standard].name+' · Hoopcut';
  displayStats();
}
function point(event){
  const matrix=$('#court-coordinate')?.getScreenCTM();if(!matrix)return null;
  const p=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse()),c=COURTS[state.standard],height=state.view==='full'?c.length:c.length/2;
  if(p.x<0||p.x>c.width||p.y<0||p.y>height)return null;
  return {x:p.x,y:p.y};
}
function add(p){
  if(state.items.length>=500){announce('This session has 500 entries. Download it and start a new session.');return;}
  if(chart){change(()=>state.items.push({id:uid(),type:'shot',number:Math.max(0,...state.items.map(s=>s.number))+1,...p,made:result,at:new Date().toISOString()}),`${result?'Made':'Missed'} shot recorded.`);return;}
  if(tool==='erase'){announce('Select an existing marker or arrow to remove it.');return;}
  if(tool==='arrow'&&!pendingArrow){pendingArrow=p;announce('Arrow start placed. Tap where the arrow should end.');return;}
  const start=pendingArrow;
  change(()=>state.items.push(tool==='arrow'?{id:uid(),type:tool,x:start.x,y:start.y,x2:p.x,y2:p.y}:{id:uid(),type:tool,...p,...(tool==='player'?{label:String(state.items.filter(m=>m.type==='player').length+1)}:{})}),tool==='arrow'?'Movement arrow added.':`${tool[0].toUpperCase()+tool.slice(1)} added. Drag it to adjust.`);
}
svg.addEventListener('pointerdown',event=>{
  if(event.button!==0)return;const p=point(event);if(!p)return;begin();
  const id=event.target.closest('[data-point]')?.dataset.point;
  if(id&&!chart&&tool==='erase'){change(()=>state.items=state.items.filter(m=>m.id!==id),'Marker removed.');return;}
  const item=state.items.find(m=>m.id===id);
  drag={id:item?.type==='arrow'?null:id,origin:p,start:{x:event.clientX,y:event.clientY},moved:false,original:item?{...item}:null};
  svg.setPointerCapture(event.pointerId);
});
svg.addEventListener('pointermove',event=>{
  if(!drag?.id)return;const p=point(event);if(!p)return;
  if(!drag.moved&&Math.hypot(event.clientX-drag.start.x,event.clientY-drag.start.y)<5)return;
  if(!drag.moved)checkpoint();drag.moved=true;
  const item=state.items.find(m=>m.id===drag.id);if(!item)return;
  item.x=p.x;item.y=p.y;state.example=false;render();
});
svg.addEventListener('pointerup',event=>{
  if(!drag)return;const d=drag;drag=null;const p=point(event);
  if(d.moved){save();announce('Location updated.');}
  else if(p&&!d.id)add(p);
  else if(d.id)announce(chart?'Use the shot log to change a result, or drag the mark to correct its location.':'Drag this marker to move it, or choose Eraser to remove it.');
  if(svg.hasPointerCapture(event.pointerId))svg.releasePointerCapture(event.pointerId);
});
svg.addEventListener('pointercancel',()=>{if(drag?.moved){save();announce('Location saved.');}drag=null;});
svg.addEventListener('keydown',event=>{
  const c=COURTS[state.standard],height=state.view==='full'?c.length:c.length/2,id=event.target.closest('[data-point]')?.dataset.point,item=state.items.find(m=>m.id===id);
  if(item&&(event.key==='Delete'||event.key==='Backspace')){event.preventDefault();change(()=>state.items=state.items.filter(m=>m.id!==id),'Entry removed.');svg.focus();return;}
  if(chart&&item&&['Enter',' '].includes(event.key)){event.preventDefault();change(()=>item.made=!item.made,'Shot result changed.');svg.focus();return;}
  if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){
    event.preventDefault();const p=item||state.cursor||{x:c.width/2,y:height*.5},step=event.shiftKey?.8:.25;
    if(item)checkpoint();const next={x:clamp(p.x+(event.key==='ArrowRight'?step:event.key==='ArrowLeft'?-step:0),0,c.width),y:clamp(p.y+(event.key==='ArrowUp'?step:event.key==='ArrowDown'?-step:0),0,height)};
    if(item){Object.assign(item,next);state.example=false;}else state.cursor=next;
    render();save();svg.focus();announce('Court position adjusted. Press Enter to place an entry.');return;
  }
  if(event.target===svg&&['Enter',' '].includes(event.key)){event.preventDefault();const p=state.cursor||{x:c.width/2,y:height*.5};add(p);svg.focus();}
});
document.querySelectorAll('[data-mode]').forEach(b=>b.addEventListener('click',()=>{tool=b.dataset.mode;pendingArrow=null;document.querySelectorAll('[data-mode]').forEach(a=>a.setAttribute('aria-pressed',String(a===b)));announce(tool==='arrow'?'Tap two court locations to draw an arrow.':tool==='erase'?'Tap a marker or an arrow to remove it.':`Tap the court to place a ${tool}.`);}));
document.querySelectorAll('[data-result]').forEach(b=>b.addEventListener('click',()=>{result=b.dataset.result==='made';document.querySelectorAll('[data-result]').forEach(a=>a.setAttribute('aria-pressed',String(a===b)));announce(`Tap the court to record a ${result?'made':'missed'} shot.`);}));
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{state.view=b.dataset.view;pendingArrow=null;render();save();announce('View changed. Markers outside the half-court view are kept in the full-court plan.');}));
document.querySelectorAll('[data-theme]').forEach(b=>b.addEventListener('click',()=>{state.theme=b.dataset.theme;render();save();}));
$('#court-units').addEventListener('change',event=>{state.units=event.target.value;render();save();});
$('#show-dimensions').addEventListener('change',event=>{state.dimensions=event.target.checked;render();save();});
$('#court-standard').addEventListener('change',event=>{const previous=COURTS[state.standard],next=COURTS[event.target.value];change(()=>{state.standard=event.target.value;for(const m of state.items){m.x=m.x/previous.width*next.width;m.y=m.y/previous.length*next.length;if(m.type==='arrow'){m.x2=m.x2/previous.width*next.width;m.y2=m.y2/previous.length*next.length;}}delete state.cursor;},'Court changed. Existing locations were scaled to the new layout'+(chart?' and scoring recalculated.':'.'));});
$('#session-title').addEventListener('input',event=>{state.title=event.target.value.slice(0,60);$('#drawing-title').textContent=state.title||'Untitled';$('#print-heading').textContent=(state.title||'Basketball plan')+' · '+COURTS[state.standard].name+' · Hoopcut';save();});
$('#undo-court').addEventListener('click',()=>{if(!history.length)return;state=JSON.parse(history.pop());pendingArrow=null;render();save();announce('Last edit undone.');});
$('#sample-court').addEventListener('click',()=>{begin();checkpoint();state.items=sample();state.example=true;pendingArrow=null;render();save();announce(chart?'Demo session loaded. These are fictional shots. Clear them before recording your own session.':'Example plan loaded. Move the markers to make it yours.');});
$('#clear-court').addEventListener('click',()=>$('#clear-dialog').showModal());
$('#confirm-clear').addEventListener('click',()=>{change(()=>state.items=[],chart?'Session cleared. Ready for your shots.':'Court cleared. Ready for your plan.');$('#clear-dialog').close();});
if(chart){
  $('#shot-table-body').addEventListener('click',event=>{const toggle=event.target.closest('[data-toggle-shot]'),remove=event.target.closest('[data-remove-shot]');if(toggle){const item=state.items.find(m=>m.id===toggle.dataset.toggleShot);if(item)change(()=>item.made=!item.made,'Shot result changed.');}if(remove)change(()=>state.items=state.items.filter(m=>m.id!==remove.dataset.removeShot),'Shot removed.');});
  $('#add-position-shot').addEventListener('click',()=>{const c=COURTS[state.standard],positions={rim:[.5,.13],paint:[.55,.28],midrange:[.28,.4],left:[.07,.13],top:[.5,.72],right:[.93,.13]},p=positions[$('#shot-position').value];add({x:p[0]*c.width,y:p[1]*c.length/2});});
}
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
function exported(){const out=courtSVG(state,{exporting:true}),vb=out.viewBox.split(' ').map(Number),w=vb[2],h=vb[3],stats=chart?summarize(state.standard,state.items):null;const note=chart?`${state.example?'DEMO DATA | ':''}${stats.made}/${stats.attempts} made | FG ${stats.percentage===null?'—':stats.percentage+'%'} | 2PT ${stats.two.made}/${stats.two.attempts} | 3PT ${stats.three.made}/${stats.three.attempts}`:'Court plan | '+COURTS[state.standard].name+' reference layout';
  return {width:w,height:h+110,source:`<svg xmlns="http://www.w3.org/2000/svg" width="${w*2}" height="${(h+110)*2}" viewBox="0 0 ${w} ${h+110}"><rect width="100%" height="100%" fill="#eee8d8"/><text x="24" y="30" font-family="Arial,sans-serif" font-size="18" fill="#313d2d">${escapeXML(state.title||'Basketball '+(chart?'shot chart':'court diagram'))}</text><text x="24" y="51" font-family="Arial,sans-serif" font-size="10" fill="#65715a">HOOPCUT / ${COURTS[state.standard].name}${state.example?' / EXAMPLE DATA':''}</text><g transform="translate(0 65)">${out.content}</g><text x="24" y="${h+91}" font-family="Arial,sans-serif" font-size="11" fill="#4b5840">${escapeXML(note)}</text></svg>`};}
$('#export-svg').addEventListener('click',()=>{try{const out=exported();download(new Blob([out.source],{type:'image/svg+xml'}),slug+'.svg');track('export_success','svg');announce('SVG downloaded.');}catch{announce('Export could not finish. Your local draft is still available.');}});
$('#export-png').addEventListener('click',async()=>{const button=$('#export-png');button.disabled=true;let url;try{const out=exported(),img=new Image();url=URL.createObjectURL(new Blob([out.source],{type:'image/svg+xml'}));img.src=url;await img.decode();const canvas=document.createElement('canvas');canvas.width=Math.round(out.width*2);canvas.height=Math.round(out.height*2);canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));if(!blob)throw Error('PNG failed');download(blob,slug+'.png');track('export_success','png');announce('PNG downloaded.');}catch{announce('PNG export could not finish. Try SVG, or print your plan.');}finally{button.disabled=false;if(url)URL.revokeObjectURL(url);}});
if(chart)$('#export-csv').addEventListener('click',()=>{const cell=v=>'"'+String(v).replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"',rows=[['Session','Data type','Court','Shot','Result','Points','Zone','X metres from left sideline','Y metres from near baseline','Recorded at UTC'],...state.items.map(m=>[state.title,m.isExample?'FICTIONAL DEMO':'User entered',COURTS[state.standard].name,m.number,m.made?'Made':'Missed',shotValue(state.standard,m),shotZone(state.standard,m),m.x.toFixed(3),m.y.toFixed(3),m.at||''])];download(new Blob(['\ufeff'+rows.map(r=>r.map(cell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),slug+'.csv');track('export_success','csv');announce('Shot log CSV downloaded'+(state.example?' with a demo-data label.':'.'));});
$('#print-court').addEventListener('click',()=>{track('print_click');window.print();});
render();save();
announce(storageAvailable?(state.example?(chart?'A session containing demo shots was restored. Clear it to start your own record.':'Example plan loaded. Edit the markers or clear the court.'):chart?'Choose Made or Missed, then tap where the shot was taken.':'Your court plan is ready.'): 'Local storage is unavailable. You can use the tool and download a copy.');
