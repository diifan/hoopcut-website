import http from 'node:http';import path from 'node:path';import {fileURLToPath} from 'node:url';import {readFile,stat,unlink} from 'node:fs/promises';import handler from '../api/comments.js';
const root=fileURLToPath(new URL('../',import.meta.url));const prefix=process.env.PREVIEW_PREFIX||'';
const mime={'.html':'text/html; charset=utf-8','.js':'application/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.jpg':'image/jpeg','.png':'image/png','.svg':'image/svg+xml','.webp':'image/webp','.mp4':'video/mp4','.xml':'application/xml','.woff2':'font/woff2'};
export const server=http.createServer(async(req,res)=>{
 try{
  const u=new URL(req.url,'http://localhost');let name=decodeURIComponent(u.pathname);
  if(name==='/api/comments'){
   let data='',size=0;for await(const chunk of req){size+=chunk.length;if(size>16000){res.writeHead(413,{'Content-Type':'application/json'});res.end('{"error":"Comment request is too large."}');return;}data+=chunk;}
   if(data){try{req.body=JSON.parse(data);}catch{res.writeHead(400,{'Content-Type':'application/json'});res.end('{"error":"Invalid JSON."}');return;}}
   return await handler(req,res);
  }
  if(name==='/' )name='/index.html';if(!path.extname(name)){try{await stat(path.join(root,name+'.html'));name+='.html';}catch{name+='/index.html';}}
  const file=path.resolve(root,'.'+name);const relative=path.relative(root,file);
  if(relative.startsWith('..')||path.isAbsolute(relative)||relative.split('/').some(x=>x.startsWith('.'))||!mime[path.extname(file)]||['server','lib','api','tests','node_modules','scripts','docs'].includes(relative.split('/')[0])){res.writeHead(404);res.end('Not found');return;}
  let data=await readFile(file);
  if(file.endsWith('.html')){
   let html=data.toString();if(prefix)html=html.replaceAll('href="/','href="'+prefix+'/').replaceAll('src="/','src="'+prefix+'/').replace('data-video-comments',`data-comments-api="${prefix}/api/comments" data-video-comments`).replace('data-comments-video=',`data-comments-api="${prefix}/api/comments" data-comments-video=`);
   data=Buffer.from(html.replace('</head>','<meta name="robots" content="noindex,nofollow"></head>'));
  }
  res.writeHead(200,{'Content-Type':mime[path.extname(file)],'Cache-Control':'no-store','X-Robots-Tag':'noindex, nofollow'});res.end(data);
 }catch{res.writeHead(404);res.end('Not found');}
});
if(process.env.COMMENTS_SOCKET){await unlink(process.env.COMMENTS_SOCKET).catch(()=>{});server.listen(process.env.COMMENTS_SOCKET,()=>console.log('Comments preview listening on Unix socket'));}
else server.listen(Number(process.env.PORT||8767),'127.0.0.1',()=>console.log('Comments preview listening'));
