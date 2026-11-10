// Explicit opt-in staging integration only. Never loads production credentials.
import http from 'node:http';
import {readFile} from 'node:fs/promises';
import {resolve,extname} from 'node:path';
import {randomBytes} from 'node:crypto';
import handler from '../api/analytics/events.js';
// Local lab egress requires its existing proxy; production Vercel handler is unaffected.
if(process.env.HTTPS_PROXY){const {EnvHttpProxyAgent,setGlobalDispatcher}=await import('undici');setGlobalDispatcher(new EnvHttpProxyAgent());}
if(process.env.HOOPCUT_STAGING_SECRET_FILE){
 const privateConfig=JSON.parse(await readFile(process.env.HOOPCUT_STAGING_SECRET_FILE,'utf8'));
 process.env.HOOPCUT_ANALYTICS_SECRET=privateConfig.HOOPCUT_WEB_STAGING_SECRET;
}
process.env.VERCEL_ENV='preview';delete process.env.VERCEL;
process.env.HOOPCUT_ANALYTICS_SECRET_HEADER='x-hoopcut-web-secret';
process.env.HOOPCUT_ANALYTICS_RATE_SECRET=randomBytes(32).toString('hex');
const port=Number(process.env.PORT||8261),root=resolve('dist');
process.env.HOOPCUT_ANALYTICS_ORIGINS=`http://127.0.0.1:${port},http://192.168.0.112:${port},http://localhost:${port}`;
http.createServer(async(req,res)=>{
 res.setHeader('X-Robots-Tag','noindex, nofollow');
 const path=new URL(req.url,'http://preview').pathname;
 if(path==='/api/analytics/events'){
  const chunks=[];let size=0;
  for await(const part of req){size+=part.length;if(size>32768){res.writeHead(413);res.end();return;}chunks.push(part);}
  req.body=Buffer.concat(chunks).toString('utf8');await handler({method:req.method,headers:req.headers,body:req.body,socket:{remoteAddress:req.socket.remoteAddress || '127.0.0.1'}},res);return;
 }
 const target=resolve(root,'.'+decodeURIComponent(path==='/'?'/index.html':path));
 if(!target.startsWith(root+'/')){res.writeHead(404);res.end();return;}
 try{let data;let file=target;try{data=await readFile(file);}catch{file=target+'.html';data=await readFile(file);}
 const type={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.mp4':'video/mp4','.webp':'image/webp','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml'}[extname(file)]||'application/octet-stream';
 res.writeHead(200,{'Content-Type':type});res.end(data);
 }catch{res.writeHead(404);res.end();}
}).listen(process.env.HOOPCUT_PREVIEW_SOCKET || port,()=>console.log('Staging attribution preview ready'));
