import {createHmac} from 'node:crypto';
const endpoint='https://cfskhucnihvnhcxoleaq.supabase.co/functions/v1/shot-tracer-bridge';
export async function proxy(req,res,worker=false){
 res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');res.setHeader('X-Robots-Tag','noindex, nofollow');
 const fail=(status,error)=>{res.statusCode=status;res.end(JSON.stringify({error}));};
 if(req.method!=='POST')return fail(405,'method_not_allowed');
 if(Number(req.headers['content-length'])>16384)return fail(413,'body_too_large');
 let b=req.body;try{if(typeof b==='string')b=JSON.parse(b);if(!b||typeof b!=='object'||Array.isArray(b)||Buffer.byteLength(JSON.stringify(b))>16384)throw Error();}catch{return fail(400,'invalid_request');}
 const environment=process.env.VERCEL_ENV==='production'?'production':'staging';const secret=process.env.HC_TRACER_WEB_SECRET;
 const headers={'Content-Type':'application/json'};
 if(worker){
  if(!/^Bearer [A-Za-z0-9_-]{40,100}$/.test(req.headers.authorization||''))return fail(401,'unauthorized');
  if(!['poll','heartbeat','finish','artifact','cleanup'].includes(b.action))return fail(400,'invalid_action');
  headers['x-hc-worker']=req.headers.authorization.slice(7);
 }else{
  if(!secret)return fail(503,'not_configured');
  if(req.headers.origin!==`https://${req.headers.host}`)return fail(403,'origin_not_allowed');
  if(!['create','complete','status','process','download','cancel'].includes(b.action))return fail(400,'invalid_action');
  headers['x-hc-web']=secret;
  if(b.action==='create'){
   const ip=process.env.VERCEL==='1'?req.headers['x-vercel-forwarded-for']:req.socket?.remoteAddress;
   if(typeof ip!=='string'||ip.includes(','))return fail(503,'trusted_ingress_required');
   b.data={...(b.data||{}),rate_key:createHmac('sha256',secret).update(ip).digest('hex')};
  }
 }
 try{
  let target=environment==='staging'&&process.env.HC_TRACER_FAST_STAGING==='1'?endpoint.replace('/shot-tracer-bridge','/shot-tracer-overlap-staging'):endpoint;
  if(environment==='staging'&&process.env.HC_TRACER_FAST_STAGING==='1'){headers['x-region']='ap-southeast-1';target+='?forceFunctionRegion=ap-southeast-1';}
  const upstreamStarted=performance.now();
  const r=await fetch(target,{method:'POST',headers,body:JSON.stringify({environment,action:b.action,id:b.id,data:b.data||{}}),signal:AbortSignal.timeout(12000),redirect:'error'});
  const body=await r.json();if(environment==='staging'){res.setHeader('Server-Timing','upstream;dur='+(performance.now()-upstreamStarted).toFixed(1));res.setHeader('X-HoopCut-Region',process.env.VERCEL_REGION||'unknown');res.setHeader('X-HoopCut-Edge-Region',r.headers?.get?.('x-sb-edge-region')||'unknown');}res.statusCode=r.status;res.end(JSON.stringify(body));
 }catch{return fail(503,'bridge_unavailable');}
}
