import {createHmac} from 'node:crypto';
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const ctas=new Set(['header_download','hero_download','video_detail_download','footer_download','mobile_sticky_download','article_download','resource_download']);
const common=['schema_version','product','environment','event_id','event_name','occurred_at','visitor_id','visitor_scope','web_session_id','page_view_id','page_path','referrer_host','first_touch_at',...['session','first_touch'].flatMap(p=>['source','medium','campaign','content','term'].map(k=>p+'_'+k))];
const extras={page_view:[],video_play:['video_id','playback_trigger'],download_clicked:['click_id','cta_id','destination_type']};
export function validEvent(e,environment){
 if(!e||typeof e!=='object'||Array.isArray(e)||typeof e.event_name!=='string'||!Object.hasOwn(extras,e.event_name))return false;
 const keys=[...common,...extras[e.event_name]];
 if(keys.some(k=>!Object.hasOwn(e,k))||Object.keys(e).some(k=>!keys.includes(k)))return false;
 if(e.schema_version!==1||e.product!=='hoopcut'||e.environment!==environment)return false;
 if(['event_id','visitor_id','web_session_id','page_view_id',...(e.event_name==='download_clicked'?['click_id']:[])].some(k=>!uuid.test(e[k])))return false;
 if(!['persistent','session'].includes(e.visitor_scope))return false;
 if(typeof e.page_path!=='string'||!/^\/[^?#\s]*$/.test(e.page_path)||e.page_path.length>2048||e.page_path.startsWith('//'))return false;
 if(e.referrer_host!==null&&(typeof e.referrer_host!=='string'||! /^[a-z0-9.-]{1,253}$/i.test(e.referrer_host)))return false;
 if(['occurred_at','first_touch_at'].some(k=>typeof e[k]!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z$/.test(e[k])||!Number.isFinite(Date.parse(e[k]))))return false;
 for(const p of ['session','first_touch'])for(const k of ['source','medium','campaign','content','term']){const v=e[p+'_'+k];if(v!==null&&(typeof v!=='string'||!v.trim()||v!==v.trim()||v.length>200||(/[\x00-\x1f@]/.test(v))))return false;if(v!==null&&['source','medium'].includes(k)&&v!==v.toLowerCase())return false;}
 if(e.event_name==='download_clicked'&&(!ctas.has(e.cta_id)||!['onelink','app_store_fallback'].includes(e.destination_type)))return false;
 if(e.event_name==='video_play'&&(typeof e.video_id!=='string'||!e.video_id||e.video_id.length>512||/[?#\s]/.test(e.video_id)||!['user','autoplay'].includes(e.playback_trigger)))return false;
 return true;
}
const buckets=new Map();
export async function collect(req,env=process.env,send=fetch){
 const fail=(status,code)=>({status,body:{error:code}});
 if(req.method!=='POST')return fail(405,'method_not_allowed');
 const environment=env.VERCEL_ENV==='production'?'production':'staging';
 const allowed=(env.HOOPCUT_ANALYTICS_ORIGINS||'').split(',').filter(Boolean);
 if(!allowed.length||!allowed.includes(req.headers.origin)||!allowed.some(x=>{try{return new URL(x).host===req.headers.host;}catch{return false;}}))return fail(403,'origin_not_allowed');
 if(!/^application\/json(?:;|$)/i.test(req.headers['content-type']||''))return fail(400,'invalid_content_type');
 if(Number(req.headers['content-length'])>32768)return fail(413,'payload_too_large');
 let body=req.body;try{if(typeof body==='string'){if(Buffer.byteLength(body)>32768)return fail(413,'payload_too_large');body=JSON.parse(body);}if(Buffer.byteLength(JSON.stringify(body))>32768)return fail(413,'payload_too_large');}catch{return fail(400,'invalid_body');}
 if(!body||Object.keys(body).some(k=>!['schema_version','events'].includes(k))||body.schema_version!==1||!Array.isArray(body.events)||!body.events.length||body.events.length>20)return fail(400,'invalid_batch');
 if(!env.HOOPCUT_ANALYTICS_SECRET||!env.HOOPCUT_ANALYTICS_RATE_SECRET)return fail(503,'analytics_not_configured');
 // Only Vercel's overwritten forwarding header is trusted. Raw addresses are never persisted or sent upstream.
 const ip=env.VERCEL==='1'?req.headers['x-vercel-forwarded-for']:req.socket?.remoteAddress;
 if(typeof ip!=='string'||ip.includes(','))return fail(503,'trusted_ingress_required');
 const time=Date.now(),key=createHmac('sha256',env.HOOPCUT_ANALYTICS_RATE_SECRET).update(ip).digest('hex');
 for(const [k,b] of buckets)if(b.expires<=time)buckets.delete(k);
 if(buckets.size>10000)return {status:429,retry:60,body:{error:'rate_limited'}};
 const bucket=buckets.get(key)||{count:0,expires:time+60000};bucket.count+=body.events.length;buckets.set(key,bucket);
 if(bucket.count>120)return {status:429,retry:60,body:{error:'rate_limited'}};
 const rejected=[],events=[];
 for(const e of body.events){if(validEvent(e,environment))events.push(e);else rejected.push({event_id:uuid.test(e?.event_id)?e.event_id:null,code:'invalid_event'});}
 if(!events.length)return {status:200,body:{accepted_event_ids:[],duplicate_event_ids:[],rejected}};
 // Fixed product endpoint; independent server credential, never anon/Auth login or App analytics RPC.
 const endpoint='https://cfskhucnihvnhcxoleaq.supabase.co/functions/v1/web-attribution-events';
 const header=env.HOOPCUT_ANALYTICS_SECRET_HEADER;
 if(!header||!/^x-[a-z0-9-]+$/.test(header))return fail(503,'receiver_header_not_configured');
 let response;try{response=await send(endpoint,{method:'POST',redirect:'error',headers:{'Content-Type':'application/json',[header]:env.HOOPCUT_ANALYTICS_SECRET},body:JSON.stringify({schema_version:1,events}),signal:AbortSignal.timeout(8000)});}catch{return fail(503,'receiver_unavailable');}
 if(!response.ok)return {status:response.status===429?429:503,retry:response.status===429?60:undefined,body:{error:'receiver_unavailable'}};
 let receipt;try{receipt=await response.json();}catch{return fail(503,'invalid_receiver_receipt');}
 const ids=new Set(events.map(e=>e.event_id));
 if(!['accepted_event_ids','duplicate_event_ids','rejected'].every(k=>Array.isArray(receipt[k]))||[...receipt.accepted_event_ids,...receipt.duplicate_event_ids].some(id=>!ids.has(id))||receipt.rejected.some(x=>!ids.has(x.event_id)))return fail(503,'invalid_receiver_receipt');
 return {status:200,body:{accepted_event_ids:receipt.accepted_event_ids,duplicate_event_ids:receipt.duplicate_event_ids,rejected:[...rejected,...receipt.rejected.map(x=>({event_id:x.event_id,code:'invalid_event'}))]}};
}
