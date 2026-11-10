import {readdir,readFile,writeFile} from 'node:fs/promises';
const store='https://apps.apple.com/app/id6824860341';
export async function buildAttribution(out,env=process.env){
 env={HOOPCUT_ONELINK_BASE_URL:'https://hoopcut.onelink.me/SDN0',HOOPCUT_ONELINK_ALLOWED_HOSTS:'hoopcut.onelink.me',HOOPCUT_SMART_SCRIPT_SRC:'https://onelinksmartscript.appsflyer.com/onelink-smart-script-latest.js',...env};
 const environment=env.VERCEL_ENV==='production'?'production':'staging';
 let base=null,hosts=[];
 if(env.HOOPCUT_ONELINK_BASE_URL){const u=new URL(env.HOOPCUT_ONELINK_BASE_URL);hosts=(env.HOOPCUT_ONELINK_ALLOWED_HOSTS||'').split(',');if(u.host!=='hoopcut.onelink.me'||u.pathname!=='/SDN0'||u.protocol!=='https:'||u.username||u.password||u.search||u.hash||!hosts.includes(u.hostname))throw Error('OneLink requires verified HTTPS host allowlist and template path');base=u.href;}
 const config={environment,persistentStorageAllowed:env.HOOPCUT_ANALYTICS_PERSISTENT_STORAGE==='allowed',oneLinkBaseURL:base,oneLinkHosts:hosts};
 let sdk='';if(base&&env.HOOPCUT_SMART_SCRIPT_SRC){const u=new URL(env.HOOPCUT_SMART_SCRIPT_SRC);if(u.origin!=='https://onelinksmartscript.appsflyer.com')throw Error('Unapproved Smart Script origin');sdk=`<script defer src="${u.href.replaceAll('&','&amp;').replaceAll('"','&quot;')}"></script>`;}
 const tag=`<script id="attribution-settings" type="application/json">${JSON.stringify(config).replaceAll('<','\\u003c')}</script>${sdk}<script defer src="/assets/attribution.js"></script>`;
 async function walk(dir){for(const entry of await readdir(dir,{withFileTypes:true})){const file=new URL(entry.name,dir);if(entry.isDirectory())await walk(new URL(entry.name+'/',dir));else if(entry.name.endsWith('.html')){
 let html=await readFile(file,'utf8');if(entry.name==='comment-admin.html')continue;
 html=html.replace(/<a\b[^>]*href="https:\/\/apps\.apple\.com[^" ]*"[^>]*>/g,(tag,offset)=>{
 let id=tag.includes('nav-download')?'header_download':tag.includes('video-detail')?'video_detail_download':tag.includes('article-product')?'article_download':null;
 if(!id){const pos=offset;const prefix=html.slice(0,pos);id=prefix.lastIndexOf('class="hero')>prefix.lastIndexOf('</section>')?'hero_download':prefix.includes('class="end"')||prefix.includes('class="site-footer"')?'footer_download':'resource_download';}
 return tag.replace(/href="[^"]*"/,`href="${store}"`).replace(/>$/,` data-attribution-cta="${id}">`);
 });
 html=html.replace(/<iframe\b[^>]*src="https:\/\/www\.youtube-nocookie\.com\/embed\/([A-Za-z0-9_-]+)[^"]*"[^>]*>/g,(tag,id)=>tag.replace(/src="[^"]*"/,`src="https://www.youtube-nocookie.com/embed/${id}?rel=0&amp;enablejsapi=1"`));
 html=html.replace(/<iframe\b[^>]*src="https:\/\/www\.youtube-nocookie\.com\/embed\/([A-Za-z0-9_-]+)[^"]*"[^>]*>/g,(tag,id)=>tag.replace(/>$/,` data-analytics-video="${id}" id="analytics-youtube-${id}">`));
 html=html.replace('</head>',tag+'</head>');await writeFile(file,html);
 }}}
 await walk(out);
}
