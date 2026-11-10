import {collect} from '../../lib/web-attribution.js';
export default async function handler(req,res){
 res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
 try{const result=await collect(req);res.statusCode=result.status;if(result.retry)res.setHeader('Retry-After',String(result.retry));res.end(JSON.stringify(result.body));}
 catch{res.statusCode=503;res.end(JSON.stringify({error:'analytics_unavailable'}));}
}
