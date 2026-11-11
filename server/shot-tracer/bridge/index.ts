import {createClient} from 'npm:@supabase/supabase-js@2';
const db=createClient(Deno.env.get('SUPABASE_URL')!,Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,{auth:{persistSession:false}});
const store=db.storage.from('hoopcut-web-tracer');
const effects=new Set(['firework','cosmic','ice','sunset']);
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const hex=/^[0-9a-f]{48}$/;
const reply=(status:number,data:unknown)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow'}});
async function eq(a:string,b:string){const h=async(s:string)=>new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)));const [x,y]=await Promise.all([h(a),h(b)]);let d=0;for(let i=0;i<x.length;i++)d|=x[i]^y[i];return d===0;}
function need(ok:unknown,msg='invalid_request'){if(!ok)throw Error(msg);}
async function sign(path:string,download?:string){const {data,error}=await store.createSignedUrl(path,600,download?{download}:undefined);if(error)throw Error('storage_unavailable');return data.signedUrl;}
async function command(env:string,action:string,id:string,data:unknown){const r=await db.rpc('hc_tracer_command',{p_env:env,p_action:action,p_id:id,p_data:data});if(r.error){const known=['not_found','expired','lease_expired','rate_limited','storage_busy','queue_busy','job_busy','request_conflict','invalid_range','video_not_ready'];throw Error(known.find(x=>r.error!.message.includes(x))||'database_unavailable');}return r.data;}
Deno.serve(async(req)=>{
 try{
  if(req.method!=='POST')return reply(405,{error:'method_not_allowed'});
  const reader=req.body?.getReader();let raw='';if(reader){let size=0;const decoder=new TextDecoder();while(true){const r=await reader.read();if(r.done)break;size+=r.value.length;if(size>65536){await reader.cancel();return reply(413,{error:'body_too_large'});}raw+=decoder.decode(r.value,{stream:true});}}
  let b;try{b=JSON.parse(raw);}catch{return reply(400,{error:'invalid_json'});}
  need(b&&typeof b==='object'&&!Array.isArray(b));const env=b.environment;need(['staging','production'].includes(env));
  const worker=req.headers.has('x-hc-worker');const name=`HC_TRACER_${worker?'WORKER':'WEB'}_${env.toUpperCase()}`;
  const secret=Deno.env.get(name)||'';if(secret.length<32||!await eq(req.headers.get(worker?'x-hc-worker':'x-hc-web')||'',secret))return reply(401,{error:'unauthorized'});
  const action=b.action;const id=b.id||'';const data=b.data||{};
  if(worker){
   need(['poll','heartbeat','finish','artifact','cleanup'].includes(action));
   if(action==='cleanup'){
    const rows=await db.from('hc_tracer_jobs').select('id').eq('environment',env).lt('expires_at',new Date().toISOString()).neq('state','expired').limit(5);
    if(rows.error)throw Error('database_unavailable');let count=0;
    for(const j of rows.data){const prefix=`${env}/${j.id}`;const list=await store.list(prefix,{limit:100});if(list.error)continue;const names=list.data.map(x=>`${prefix}/${x.name}`);if(names.length&&(await store.remove(names)).error)continue;await db.from('hc_tracer_jobs').update({state:'expired',stage:'expired',lease:null,renders:{}}).eq('id',j.id);count++;}
    return reply(200,{cleaned:count});
   }
   if(action==='poll'){
    const j=await command(env,action,'',{});if(!j)return reply(200,{task:null});
    return reply(200,{task:{id:j.id,lease:j.lease,operation:j.operation,source_url:await sign(`${env}/${j.id}/source`),size_bytes:j.size_bytes,trim:j.trim,effect:j.effect,hoop:j.hoop,expires_at:j.expires_at}});
   }
   need(hex.test(id)&&uuid.test(data.lease));
   if(action==='artifact'){
    const j=await command(env,'status',id,{});need(j.state==='processing'&&j.lease===data.lease&&Date.parse(j.lease_until)>Date.now(),'lease_expired');need(j.operation==='render');
    const path=`${env}/${id}/${j.effect}-${j.lease}.mp4`;const r=await store.createSignedUploadUrl(path);if(r.error)throw Error('storage_unavailable');return reply(200,{upload_url:r.data.signedUrl,path});
   }
   if(action==='heartbeat'){need(['downloading','trimming','tracking','rendering','returning','probing'].includes(data.stage));need(Number.isInteger(data.progress)&&data.progress>=0&&data.progress<=99);}
   if(action==='finish'){
    need(['imported','ready','no_shots','failed','needs_hoop'].includes(data.state));
    if(data.state==='imported'){const v=data.video;need(v&&Number.isFinite(v.duration)&&v.duration>0&&v.duration<=3600&&Number.isInteger(v.width)&&Number.isInteger(v.height)&&v.width>0&&v.height>0&&Math.max(v.width,v.height)<=7680);}
    if(data.state==='needs_hoop'){
     const s=data.selection;need(s&&Number.isInteger(s.frames)&&s.frames>0&&s.frames<=751&&s.fps===25&&[720,1280].includes(s.width)&&[720,1280].includes(s.height)&&Array.isArray(s.candidates)&&s.candidates.length<=64);
     for(const c of s.candidates)need(/^[a-f0-9]{24}$/.test(c.id)&&Number.isInteger(c.frame)&&c.frame>=0&&c.frame<s.frames&&Number.isFinite(c.score)&&c.score>=0&&c.score<=1&&Array.isArray(c.rim)&&c.rim.length===4&&c.rim.every(Number.isFinite)&&c.rim[2]>0&&c.rim[3]>0&&Array.isArray(c.box)&&c.box.length===4&&c.box.every(Number.isFinite));
    }
    if(data.state==='ready'){
     const j=await command(env,'status',id,{});need(j.lease===data.lease,'lease_expired');const r=data.render;need(r&&r.path===`${env}/${id}/${j.effect}-${data.lease}.mp4`&&/^[a-f0-9]{64}$/.test(r.sha256)&&Number.isFinite(r.duration)&&r.duration>0&&r.duration<=30.1&&Number.isInteger(r.size_bytes)&&r.size_bytes>0&&r.size_bytes<=536870912);
     const obj=await store.info(r.path);need(!obj.error&&Number(obj.data?.size)===r.size_bytes,'artifact_missing');
    }
    const messages:Record<string,string>={invalid_video:'Cannot read this video. Try a supported MP4 or MOV.',no_shots:'No clear shot found. Try a clip where the ball and hoop stay visible.',resource_limit:'Processing paused to protect server resources. Please retry later.',processing_failed:'Processing failed. Please retry or choose another clip.'};
    data.error=data.state==='no_shots'?messages.no_shots:data.state==='failed'?(messages[data.error_code]||messages.processing_failed):null;
   }
   const j=await command(env,action,id,data);return reply(200,{ok:true,state:j.state});
  }
  need(['create','complete','status','process','download','cancel'].includes(action));
  if(action==='create'){
   need(uuid.test(data.request_id)&&Number.isInteger(data.size_bytes)&&data.size_bytes>0&&data.size_bytes<=536870912&&/^[a-f0-9]{64}$/.test(data.rate_key));
   const key=Array.from(crypto.getRandomValues(new Uint8Array(24)),x=>x.toString(16).padStart(2,'0')).join('');
   const j=await command(env,action,key,data);need(j.state==='uploading','request_conflict');const r=await store.createSignedUploadUrl(`${env}/${j.id}/source`);if(r.error)throw Error('storage_unavailable');
   return reply(200,{id:j.id,upload_url:r.data.signedUrl,max_bytes:536870912});
  }
  need(hex.test(id));
  if(action==='complete'){
   const j=await command(env,'status',id,{});const obj=await store.info(`${env}/${id}/source`);need(!obj.error&&Number(obj.data?.size)===j.size_bytes,'upload_incomplete');
  }
  if(action==='process')need(Number.isFinite(data.start)&&Number.isFinite(data.end)&&data.start>=0&&data.start<data.end&&data.end-data.start<=30.001&&effects.has(data.effect));
  if(action==='download'){
   const j=await command(env,'status',id,{});need(j.state==='ready'&&j.effect==='firework'&&j.renders.firework,'download_locked');return reply(200,{url:await sign(j.renders.firework.path,"HoopCut-Firework.mp4"),sha256:j.renders.firework.sha256});
  }
  const j=await command(env,action,id,data);
  const out:Record<string,unknown>={id:j.id,stage:j.stage,state:j.state,progress:j.progress,video:j.video,trim:j.trim,effect:j.effect,selection:j.selection?{...j.selection,candidates:j.selection.candidates.map((c:any)=>({id:c.id,frame:c.frame,time:c.time,box:c.box}))}:null,selected_hoop:j.hoop?.id||null,error:j.error,expires_at:j.expires_at,renders:{}};
  if(j.state==='ready'&&j.renders[j.effect]){const r=j.renders[j.effect];out.preview_url=await sign(r.path);out.renders={[j.effect]:{sha256:r.sha256,duration:r.duration}};}
  return reply(200,out);
 }catch(e){const code=e instanceof Error?e.message:'internal_error';const known=['invalid_request','invalid_selection','invalid_range','invalid_json','not_found','expired','lease_expired','rate_limited','storage_busy','queue_busy','job_busy','request_conflict','video_not_ready','upload_incomplete','download_locked','artifact_missing','database_unavailable','storage_unavailable'];const safe=known.includes(code)?code:'internal_error';const status=safe==='not_found'?404:safe==='expired'?410:safe==='download_locked'?403:['rate_limited','storage_busy','queue_busy'].includes(safe)?429:['lease_expired','job_busy','request_conflict'].includes(safe)?409:safe.endsWith('unavailable')||safe==='internal_error'?503:400;return reply(status,{error:safe});}
});
