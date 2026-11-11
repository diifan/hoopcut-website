(()=>{'use strict';
const $=id=>document.getElementById(id),api='/api/shot-tracer/jobs';
let job=null,file=null,effect='firework',duration=0,start=0,end=0,localURL=null,epoch=0,busy=false,ready=false,exportBlob=null,exportURL=null,lastAction='upload';
const stages={downloading:'Preparing your uploaded video…',returning:'Saving your result…',probing:'Checking your video…',queued:'Waiting to process…',trimming:'Preparing your clip…',tracking:'Tracking the ball…',rendering:'Rendering your effect…',ready:'Ready to preview.'};
let phase='idle',phaseSince=Date.now();
const phaseNames={upload:'Uploading video',prepare:'Preparing your clip',tracking:'Tracing your shot',rendering:'Finishing your video',selection:'Choose your hoop',ready:'Your shot is ready',error:'Let’s try that again',idle:'Your clip'};
function message(text,progress=null){
 const next=phase==='error'&&!busy?'error':/hoop|Selection/.test(text)?'selection':/upload/i.test(text)&&!/uploaded/.test(text)?'upload':/tracking|processing|Starting|Waiting/.test(text)?'tracking':/Rendering|Saving/.test(text)?'rendering':/hoop|Selection/.test(text)?'selection':/Ready|complete/i.test(text)?'ready':/Checking|Preparing your (clip|uploaded)/.test(text)?'prepare':phase;
 if(next!==phase){phase=next;phaseSince=Date.now();}
 const panel=$('status-panel');panel.hidden=false;panel.dataset.phase=phase;
 $('status-title').textContent=phaseNames[phase]||'Your clip';$('status').textContent=text;
 // Upload bytes and rendered frames are real measurements. Never fake an ETA.
 const measured=Number.isFinite(progress)&&(phase==='upload'||phase==='rendering');
 const value=phase==='rendering'?Math.max(0,Math.min(100,Math.round((progress-70)/29*100))):progress;
 $('progress').hidden=!busy;measured?$('progress').value=value:$('progress').removeAttribute('value');
 $('progress').setAttribute('aria-label',phaseNames[phase]);$('progress-value').textContent=measured?`${value}%`:'';
 panel.classList.toggle('is-busy',busy);$('status-note').textContent=busy?'Keep this tab open. Your preview will appear here.':'';
}
function actions(){
 $('editor').classList.toggle('is-busy',busy);$('editor').setAttribute('aria-busy',String(busy));
 $('cancel-job').hidden=!busy;$('replace').disabled=busy;
 $('status-panel').classList.toggle('is-busy',busy);if(!busy)$('progress').hidden=true;
 $('actions').hidden=!job||!$('trim-panel').hidden||busy;$('export').hidden=effect!=='firework';$('export').disabled=!ready;$('unlock').hidden=effect==='firework';
 document.querySelectorAll('[data-effect]').forEach(b=>{b.disabled=busy;b.setAttribute('aria-pressed',String(b.dataset.effect===effect));});
}
const statusPanel=$('status-panel');
statusPanel.insertAdjacentHTML('afterbegin','<div class="status-heading"><span class="status-orbit" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><circle cx="16" cy="16" r="12"/><path d="M4 16h24M16 4v24M8 7c12 4 12 14 0 18M24 7c-12 4-12 14 0 18"/></svg></span><div><span class="status-kicker">HOOPCUT STUDIO</span><h3 id="status-title">Your clip</h3></div><span id="progress-value"></span></div>');
statusPanel.insertAdjacentHTML('beforeend','<div class="status-footer"><span id="status-note"></span><span id="status-elapsed" aria-hidden="true"></span></div>');
$('editor').append(statusPanel);
setInterval(()=>{$('status-elapsed').textContent=busy?`${Math.floor((Date.now()-phaseSince)/1000)}s elapsed`:'';},1000);
async function rpc(action,id='',data={}){const r=await fetch('/api/shot-tracer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,id,data})});let d;try{d=await r.json()}catch{}if(!r.ok){const messages={queue_busy:'Busy right now. Please retry shortly.',storage_busy:'Storage is busy. Please try later.',rate_limited:'Upload limit reached. Please try later.',expired:'Video expired. Import it again.',job_busy:'This video is still processing.',upload_incomplete:'Upload is incomplete. Please retry.',bridge_unavailable:'Connection failed. Please retry.',not_configured:'The preview service is not connected yet.'};throw Error(messages[d?.error]||'Could not complete this request. Please retry.')}return d;}
async function request(url,options={}){const parts=url.slice(api.length).split('/').filter(Boolean);return rpc(parts[1]==='process'?'process':'status',parts[0],options.body?JSON.parse(options.body):{});}
function putVideo(url,file){return new Promise((resolve,reject)=>{const x=new XMLHttpRequest();activeUpload=x;x.onabort=()=>reject(Error('Upload cancelled.'));x.open('PUT',url);x.timeout=600000;x.setRequestHeader('Content-Type','application/octet-stream');x.upload.onprogress=e=>{if(e.lengthComputable)message('Uploading your video…',Math.round(100*e.loaded/e.total));};x.onload=()=>x.status>=200&&x.status<300?resolve():reject(Error('Upload failed. Please retry.'));x.onerror=()=>reject(Error('Upload connection failed. Please retry.'));x.ontimeout=()=>reject(Error('Upload timed out. Please retry.'));x.send(file);});}
function failure(e){busy=false;ready=false;$('edit-trim').hidden=!job||duration<=30;phase='error';message(e.message);$('status-title').textContent=phaseNames.error;$('retry').hidden=false;actions();}
function cleanExport(){if(exportURL?.startsWith('blob:'))URL.revokeObjectURL(exportURL);exportURL=null;exportBlob=null;$('complete').hidden=true;$('after-download').hidden=true;}
let uploadRequest=null;let activeUpload=null;let hoopId=null,hoopRange='',choiceEpoch=0;
const hoopPanel=document.createElement('section');hoopPanel.id='hoop-panel';hoopPanel.hidden=true;
hoopPanel.innerHTML='<h2>Choose your hoop</h2><p>Tap your hoop, then confirm. Try another frame if needed.</p><div class="hoop-frame"><canvas id="hoop-canvas"></canvas><div id="hoop-boxes"></div></div><p id="hoop-frame-label"></p><button id="hoop-next" class="text-button">Next frame</button> <button id="hoop-confirm" class="primary" disabled>Confirm hoop</button> <button id="hoop-cancel" class="text-button">Cancel</button>';
$('editor').append(hoopPanel);
async function showHoops(selection){
 const run=++choiceEpoch,choices=selection?.candidates||[],frames=[...new Set(choices.map(c=>c.frame))];let index=0,picked=null;
 $('effects').hidden=true;$('hoop-panel').hidden=false;$('editor').classList.add('choosing-hoop');$('retry').hidden=true;$('hoop-confirm').disabled=true;
 if(!frames.length){message('No hoop found. Choose another range or video.');$('hoop-next').hidden=true;$('edit-trim').hidden=false;return;}
 $('hoop-next').hidden=frames.length<2&&!selection.partial;
 $('hoop-next').textContent=selection.partial?'More frames':'Next frame';
 async function draw(){
  $('hoop-next').disabled=true;picked=null;$('hoop-confirm').disabled=true;$('hoop-boxes').replaceChildren();const frame=frames[index],video=$('preview');
  video.pause();if(video.src!==localURL)video.src=localURL;
  const waitEvent=name=>new Promise((resolve,reject)=>{const timer=setTimeout(()=>{video.removeEventListener(name,done);reject(Error('Cannot display this frame. Please retry.'));},10000);function done(){clearTimeout(timer);resolve();}video.addEventListener(name,done,{once:true});});
  if(video.readyState<2)await waitEvent('loadeddata');
  const t=start+frame/25;if(Math.abs(video.currentTime-t)>.001){const sought=waitEvent('seeked');video.currentTime=t;await sought;}
  if(run!==choiceEpoch)return;
  const canvas=$('hoop-canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;const ctx=canvas.getContext('2d');ctx.drawImage(video,0,0,canvas.width,canvas.height);
  for(const [i,c] of choices.filter(c=>c.frame===frame).entries()){
   const [x,y,w,h]=c.box;ctx.strokeStyle='#ff861b';ctx.lineWidth=Math.max(2,canvas.width/350);ctx.strokeRect(x*canvas.width,y*canvas.height,w*canvas.width,h*canvas.height);
   const b=document.createElement('button');b.type='button';b.textContent=String(i+1);b.setAttribute('aria-label',`Select hoop ${i+1}`);b.style.left=`${(x+w/2)*100}%`;b.style.top=`${(y+h/2)*100}%`;
   b.onclick=()=>{picked=c;$('hoop-confirm').disabled=false;$('hoop-boxes').querySelectorAll('button').forEach(e=>e.setAttribute('aria-pressed',String(e===b)));};$('hoop-boxes').append(b);
  }
  $('hoop-frame-label').textContent=`Frame ${index+1} of ${frames.length} · ${t.toFixed(2)}s`;$('hoop-next').disabled=false;message('Choose and confirm your hoop before processing.');
 }
 $('hoop-next').onclick=()=>{if(selection.partial){hoopId=null;++choiceEpoch;process();return;}index=(index+1)%frames.length;draw().catch(failure);};
 $('hoop-confirm').onclick=()=>{if(!picked)return;hoopId=picked.id;choiceEpoch++;process();};
 $('hoop-cancel').onclick=()=>{choiceEpoch++;$('hoop-panel').hidden=true;$('editor').classList.remove('choosing-hoop');message('Selection cancelled. Retry to choose again, or change video.');$('retry').hidden=false;};
 await draw();
}

async function upload(){const run=++epoch;busy=true;ready=false;lastAction='upload';$('retry').hidden=true;message('Preparing upload…');actions();try{if(!uploadRequest)uploadRequest=await rpc('create','',{request_id:crypto.randomUUID(),size_bytes:file.size});job=uploadRequest.id;if(!uploadRequest.uploaded){await putVideo(uploadRequest.upload_url,file);uploadRequest.uploaded=true;}await rpc('complete',job);let d;const deadline=Date.now()+20*60*1000;while(run===epoch){d=await rpc('status',job);if(d.state==='imported'||d.state==='needs_hoop')break;if(['failed','expired','cancelled'].includes(d.state))throw Error(d.error||'Cannot read this video. Import another file.');if(Date.now()>deadline)throw Error('Processing is taking longer than expected. Please retry.');message(d.stage==='downloading'?'Preparing your uploaded video…':'Checking your video…');await new Promise(r=>setTimeout(r,750));}if(run!==epoch)return;duration=d.video.duration;start=0;end=Math.min(30,duration);$('trim-start').value=0;$('trim-end').value=end.toFixed(2);$('trim-slider').max=Math.max(0,duration-1);$('trim-slider').value=0;busy=false;if(d.state==='needs_hoop'){if(!Array.isArray(d.trim)||d.trim.length!==2||d.trim[0]!==0||d.trim[1]!==duration)throw Error('Prepared clip range is invalid. Please retry.');start=d.trim[0];end=d.trim[1];hoopId=null;hoopRange=JSON.stringify([start,end]);lastAction='process';$('effects').hidden=false;actions();await showHoops(d.selection);return;}if(duration>30){$('trim-panel').hidden=false;message('Choose the part you want to trace.');updateTrim();actions()}else await process();}catch(e){if(run===epoch)failure(e);}}
async function process(){$('editor').classList.remove('choosing-hoop');if(hoopRange!==JSON.stringify([start,end])){hoopId=null;hoopRange=JSON.stringify([start,end]);}$('hoop-panel').hidden=true;$('edit-trim').hidden=true;const run=++epoch;busy=true;ready=false;lastAction='process';cleanExport();$('retry').hidden=true;$('trim-panel').hidden=true;$('effects').hidden=false;actions();message(hoopId?'Tracking the ball…':'Preparing your clip…');try{await request(`${api}/${job}/process`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({start,end,effect,...(hoopId?{hoop_id:hoopId}:{})})});while(run===epoch){const s=await request(`${api}/${job}`);if(s.stage==='needs_hoop'){busy=false;ready=false;actions();await showHoops(s.selection);return;}if(s.stage==='ready'){busy=false;ready=true;$('preview').src=s.preview_url;message('Ready to preview.');actions();return;}if(['failed','no_shots','cancelled','expired'].includes(s.stage))throw Error(s.error);message(stages[s.stage]||'Processing…',s.progress);await new Promise(r=>setTimeout(r,750));}}catch(e){if(run===epoch)failure(e);}}
function updateTrim(){start=Number($('trim-start').value);end=Number($('trim-end').value);const valid=Number.isFinite(start)&&Number.isFinite(end)&&start>=0&&end>start&&end<=duration+.01&&end-start<=30;$('apply-trim').disabled=!valid;$('trim-length').textContent=valid?`${(end-start).toFixed(1)} seconds`:'Choose a valid range of up to 30 seconds.';if(valid)$('preview').currentTime=start;}
function chooseFile(chosen){$('editor').classList.remove('choosing-hoop');if(!chosen||busy)return;if(chosen.size>512*1024**2){message('Choose a video smaller than 512 MB.');return;}$('edit-trim').hidden=true;uploadRequest=null;hoopId=null;hoopRange='';$('hoop-panel').hidden=true;epoch++;file=chosen;job=null;effect='firework';cleanExport();if(localURL)URL.revokeObjectURL(localURL);localURL=URL.createObjectURL(file);$('preview').src=localURL;$('clip-name').textContent=file.name;$('editor').querySelector('h2').textContent='Your shot. Your spotlight.';$('editor').hidden=false;$('import-panel').hidden=true;$('effects').hidden=true;$('trim-panel').hidden=true;upload();$('step1').classList.remove('active');$('step2').classList.add('active');$('step3').classList.remove('active');}
$('video-file').addEventListener('change',()=>chooseFile($('video-file').files[0]));
$('choose').onclick=()=>$('video-file').click();
$('drop').ondragover=e=>{e.preventDefault();$('drop').classList.add('dragging');};$('drop').ondragleave=()=>$('drop').classList.remove('dragging');$('drop').ondrop=e=>{e.preventDefault();$('drop').classList.remove('dragging');if(!busy)chooseFile(e.dataTransfer.files[0]);};
$('replay').onclick=()=>{if(ready){$('preview').currentTime=0;$('preview').play().catch(()=>message('Tap play to preview.'));}};
$('replace').onclick=()=>{if(busy){message('Wait for this clip to finish before changing videos.');return;}$('video-file').click();};
$('trim-start').oninput=updateTrim;$('trim-end').oninput=updateTrim;
$('trim-slider').oninput=()=>{$('trim-start').value=$('trim-slider').value;$('trim-end').value=Math.min(duration,Number($('trim-slider').value)+30).toFixed(2);updateTrim();};
$('preview').ontimeupdate=()=>{if(!$('trim-panel').hidden&&$('preview').currentTime>=end)$('preview').pause();};
$('apply-trim').onclick=process;document.querySelectorAll('[data-effect]').forEach(b=>b.onclick=()=>{if(!busy&&effect!==b.dataset.effect){effect=b.dataset.effect;process();}});
$('edit-trim').onclick=()=>{if(busy||!job)return;$('preview').src=localURL;$('trim-panel').hidden=false;$('edit-trim').hidden=true;$('retry').hidden=true;updateTrim();actions();};
$('cancel-job').onclick=async()=>{const id=job;epoch++;activeUpload?.abort();busy=false;ready=false;try{if(id)await rpc('cancel',id);message('Cancelled. You can import another video.');}catch{message('Cancellation could not be confirmed. Please retry.');}$('retry').hidden=true;actions();};
$('retry').onclick=()=>lastAction==='upload'?upload():process();
$('export').onclick=async()=>{if(!ready||effect!=='firework')return;$('export').disabled=true;message('Preparing your download…');try{const signed=await rpc('download',job);exportURL=signed.url;exportBlob=null;$('complete').hidden=false;$('actions').hidden=true;message('Export complete.');$('step2').classList.remove('active');$('step3').classList.add('active');}catch(e){message(e.message);$('export').disabled=false;}};
$('download').onclick=()=>{const a=document.createElement('a');a.href=exportURL;a.download='HoopCut-Firework.mp4';a.target='_blank';a.rel='noopener';a.click();$('after-download').hidden=false;};
$('share').onclick=async()=>{if(!exportBlob){message('Use your downloaded video to share in your favorite app.');return;}const f=new File([exportBlob],'HoopCut-Firework.mp4',{type:'video/mp4'});try{if(navigator.canShare?.({files:[f]}))await navigator.share({files:[f],title:'My shot with HoopCut'});else message('Attach your downloaded video in your favorite social app.');}catch(e){if(e.name!=='AbortError')message('Share your downloaded video from your photos or files.');}};
})();
