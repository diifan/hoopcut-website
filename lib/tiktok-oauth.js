import {createHash,randomBytes,timingSafeEqual,createCipheriv,createDecipheriv} from 'node:crypto';
import {readFileSync} from 'node:fs';
import pg from 'pg';
export const SCOPES='user.info.basic,user.info.username,user.info.stats,user.info.profile,user.account.type,user.insights,video.publish,video.upload,comment.list,comment.list.manage,video.list,video.insights';
export const ORIGIN='https://hoopcut.ai';
const COOKIE='__Host-tt_oauth';
export const hash=s=>createHash('sha256').update(String(s)).digest('hex');
export const secret=()=>randomBytes(32).toString('base64url');
const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export class OAuthError extends Error{constructor(status,message){super(message);this.status=status;}}
export function config(env=process.env){
 for(const k of ['TIKTOK_APP_ID','TIKTOK_APP_SECRET','TIKTOK_REDIRECT_URI','TIKTOK_TOKEN_KEY','TIKTOK_ADMIN_KEY'])if(!env[k])throw new OAuthError(503,'Account connection is not configured.');
 if(!/^[a-f0-9]{64}$/.test(env.TIKTOK_TOKEN_KEY)||env.TIKTOK_ADMIN_KEY.length<32||env.TIKTOK_REDIRECT_URI!==ORIGIN+'/auth/tiktok/account/callback')throw new OAuthError(503,'Invalid server configuration.');
 return env;
}
export function encrypt(data,aad,env=process.env){const iv=randomBytes(12),c=createCipheriv('aes-256-gcm',Buffer.from(env.TIKTOK_TOKEN_KEY,'hex'),iv);c.setAAD(Buffer.from(aad));const bytes=Buffer.concat([c.update(JSON.stringify(data),'utf8'),c.final()]);return [iv,c.getAuthTag(),bytes].map(x=>x.toString('base64url')).join('.');}
export function decrypt(value,aad,env=process.env){const [iv,tag,bytes]=value.split('.').map(x=>Buffer.from(x,'base64url'));const c=createDecipheriv('aes-256-gcm',Buffer.from(env.TIKTOK_TOKEN_KEY,'hex'),iv);c.setAAD(Buffer.from(aad));c.setAuthTag(tag);return JSON.parse(Buffer.concat([c.update(bytes),c.final()]).toString('utf8'));}
export function admin(req,env=process.env){const expected=env.TIKTOK_ADMIN_KEY||'',got=(req.headers.authorization||'').replace(/^Bearer /,'');return expected.length>=32&&Buffer.byteLength(got)===Buffer.byteLength(expected)&&timingSafeEqual(Buffer.from(got),Buffer.from(expected));}
export function headers(res){res.setHeader('Cache-Control','private, no-store, max-age=0');res.setHeader('X-Robots-Tag','noindex, nofollow, noarchive');res.setHeader('Referrer-Policy','no-referrer');res.setHeader('X-Content-Type-Options','nosniff');}
export function page(res,status,title,message,extra=''){
 headers(res);const nonce=randomBytes(18).toString('base64');res.setHeader('Content-Type','text/html; charset=utf-8');res.setHeader('Content-Security-Policy',`default-src 'none'; script-src 'nonce-${nonce}'; style-src 'nonce-${nonce}'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`);res.statusCode=status;
 res.end(`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(title)} | HoopCut</title><style nonce="${nonce}">body{background:#f7f6ee;color:#173c30;font:18px/1.6 system-ui}main{max-width:680px;margin:12vh auto;padding:32px}button{font:inherit;padding:12px 24px;cursor:pointer}p{overflow-wrap:anywhere}</style><main><b>SWIE Content Publisher</b><h1>${escape(title)}</h1><p id="message">${escape(message)}</p>${extra.replaceAll('NONCE',nonce)}</main><script nonce="${nonce}">history.replaceState(null,'',location.pathname)</script></html>`);
}
export async function payload(req){if(req.body&&typeof req.body==='object')return req.body;let text=typeof req.body==='string'?req.body:'';if(!text)for await(const chunk of req){text+=chunk;if(text.length>8192)throw new OAuthError(413,'Request too large.');}try{return JSON.parse(text||'{}');}catch{throw new OAuthError(400,'Invalid request.');}}
let pool;
export function database(env=process.env){if(!env.COMMENTS_DATABASE_URL)throw new OAuthError(503,'Account storage is unavailable.');return pool??=new pg.Pool({connectionString:env.COMMENTS_DATABASE_URL,ssl:env.COMMENTS_DATABASE_SSL==='true'?{ca:readFileSync(new URL('./supabase-ca.crt',import.meta.url),'utf8'),rejectUnauthorized:true}:undefined,max:3,connectionTimeoutMillis:5000,statement_timeout:10000,idleTimeoutMillis:10000});}
export async function tokenRequest(kind,credential,env=process.env,send=fetch){
 const body={client_id:env.TIKTOK_APP_ID,client_secret:env.TIKTOK_APP_SECRET,grant_type:kind==='token'?'authorization_code':'refresh_token',redirect_uri:env.TIKTOK_REDIRECT_URI,[kind==='token'?'auth_code':'refresh_token']:credential};
 let response,data;try{response=await send(`https://business-api.tiktok.com/open_api/v1.3/tt_user/oauth2/${kind}/`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:AbortSignal.timeout(18000),redirect:'error'});data=await response.json();}catch{throw new OAuthError(502,'TikTok token request could not be confirmed. Start a new authorization.');}
 if(!response.ok||data.code!==0)throw new OAuthError(502,`TikTok rejected the token request (code ${Number.isInteger(data.code)?data.code:'unknown'}). Start a new authorization.`);
 const t=data.data;if(!t||typeof t.access_token!=='string'||typeof t.refresh_token!=='string'||typeof t.open_id!=='string'||!(t.expires_in>0)||!(t.refresh_token_expires_in>0))throw new OAuthError(502,'TikTok returned incomplete account credentials.');return t;
}
export function authorizationURL(state,env=process.env){const u=new URL('https://www.tiktok.com/v2/auth/authorize');u.search=new URLSearchParams({client_key:env.TIKTOK_APP_ID,scope:SCOPES,response_type:'code',redirect_uri:env.TIKTOK_REDIRECT_URI,state});return u.href;}
export function cookieValue(req){const part=(req.headers.cookie||'').split(';').map(x=>x.trim()).find(x=>x.startsWith(COOKIE+'='));return part?.slice(COOKIE.length+1)||'';}
export async function start(req,res,env=process.env){
 config(env);if(req.method!=='POST')throw new OAuthError(405,'Use POST.');if(req.headers.origin!==ORIGIN)throw new OAuthError(403,'Invalid origin.');
 const {ticket}=await payload(req);if(typeof ticket!=='string'||!/^[\w-]{43}$/.test(ticket))throw new OAuthError(400,'Invalid or expired connection link.');
 const db=database(env),state=secret(),browser=secret();const c=await db.connect();
 try{await c.query('BEGIN');const r=await c.query('DELETE FROM tiktok_publisher.invites WHERE hash=$1 AND expires_at>now() RETURNING label',[hash(ticket)]);if(!r.rowCount)throw new OAuthError(400,'Connection link expired or already used. Request a new one.');await c.query('INSERT INTO tiktok_publisher.states(hash,browser_hash,label,expires_at) VALUES($1,$2,$3,now()+interval \'10 minutes\')',[hash(state),hash(browser),r.rows[0].label]);await c.query('COMMIT');}catch(e){await c.query('ROLLBACK');throw e;}finally{c.release();}
 res.setHeader('Set-Cookie',`${COOKIE}=${browser}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600`);res.setHeader('Content-Type','application/json');res.end(JSON.stringify({url:authorizationURL(state,env)}));
}
export async function callback(req,res,env=process.env){
 config(env);if(req.method!=='GET')throw new OAuthError(405,'Use GET.');const u=new URL(req.url,ORIGIN),state=u.searchParams.get('state'),browser=cookieValue(req);
 if(!state||!browser)throw new OAuthError(400,'授权入口已失效。请使用新生成的账号连接链接重新授权。');
 const db=database(env);const r=await db.query('DELETE FROM tiktok_publisher.states WHERE hash=$1 AND browser_hash=$2 AND expires_at>now() RETURNING label',[hash(state),hash(browser)]);
 if(!r.rowCount)throw new OAuthError(400,'授权已过期、已处理或浏览器不匹配，请重新开始。');
 res.setHeader('Set-Cookie',`${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`);
 if(u.searchParams.has('error')||(u.searchParams.get('error_code')&&!['0',''].includes(u.searchParams.get('error_code'))))throw new OAuthError(400,'你未完成 TikTok 授权，未连接账号。');
 const code=u.searchParams.get('code')||u.searchParams.get('auth_code');if(!code||code.length>4096)throw new OAuthError(400,'Missing authorization code.');
 const t=await tokenRequest('token',code,env),aad=env.TIKTOK_APP_ID+':'+t.open_id;
 await db.query(`INSERT INTO tiktok_publisher.accounts(app_id,open_id,label,credentials,scopes,expires_at,refresh_expires_at,status) VALUES($1,$2,$3,$4,$5,now()+$6*interval '1 second',now()+$7*interval '1 second','connected') ON CONFLICT(app_id,open_id) DO UPDATE SET label=excluded.label,credentials=excluded.credentials,scopes=excluded.scopes,expires_at=excluded.expires_at,refresh_expires_at=excluded.refresh_expires_at,status='connected',refresh_failures=0,updated_at=now()`,[env.TIKTOK_APP_ID,t.open_id,r.rows[0].label,encrypt(t,aad,env),t.scope||'',t.expires_in,t.refresh_token_expires_in]);
 page(res,200,'账号已连接',`${r.rows[0].label} 的 TikTok 授权已保存。后端将自动维护令牌；本次操作未发布视频。`);
}
export async function refreshAccounts(env=process.env){
 const db=database(env),c=await db.connect(),results=[];
 try{
 await c.query("BEGIN");
 const lock=await c.query("SELECT pg_try_advisory_xact_lock(hashtext('swie-tiktok-refresh')) AS locked");if(!lock.rows[0].locked){await c.query('ROLLBACK');return {state:'already_running'};}
 try{const rows=await c.query("SELECT * FROM tiktok_publisher.accounts WHERE app_id=$1 AND status='connected' AND expires_at<now()+interval '2 hours' ORDER BY expires_at LIMIT 2 FOR UPDATE",[env.TIKTOK_APP_ID]);
 for(const a of rows.rows){try{if(new Date(a.refresh_expires_at)<=new Date())throw new Error('Expired');const old=decrypt(a.credentials,a.app_id+':'+a.open_id,env),t=await tokenRequest('refresh_token',old.refresh_token,env);if(t.open_id!==a.open_id)throw new Error('Identity mismatch');await c.query("UPDATE tiktok_publisher.accounts SET credentials=$3,scopes=$4,expires_at=now()+$5*interval '1 second',refresh_expires_at=now()+$6*interval '1 second',refresh_failures=0,updated_at=now() WHERE app_id=$1 AND open_id=$2",[a.app_id,a.open_id,encrypt(t,a.app_id+':'+a.open_id,env),t.scope||a.scopes,t.expires_in,t.refresh_token_expires_in]);results.push({label:a.label,status:'refreshed'});}catch{await c.query("UPDATE tiktok_publisher.accounts SET refresh_failures=refresh_failures+1,status=CASE WHEN refresh_expires_at<=now() THEN 'reauthorization_required' ELSE 'connected' END,updated_at=now() WHERE app_id=$1 AND open_id=$2",[a.app_id,a.open_id]);results.push({label:a.label,status:'refresh_failed'});}}
 }catch(e){await c.query("ROLLBACK");throw e;}
 await c.query("COMMIT");
 }finally{c.release();}return {state:'complete',results};
}
export async function manage(req,res,env=process.env){
 config(env);if(!admin(req,env))throw new OAuthError(401,'Unauthorized.');let result;
 if(req.method==='GET'){const r=await database(env).query('SELECT open_id,label,scopes,expires_at,refresh_expires_at,status,updated_at FROM tiktok_publisher.accounts WHERE app_id=$1 ORDER BY label',[env.TIKTOK_APP_ID]);result={accounts:r.rows};}
 else if(req.method==='POST'){const body=await payload(req);if(body.operation==='invite'){if(!/^[A-Za-z][A-Za-z0-9_-]{1,30}$/.test(body.label||''))throw new OAuthError(400,'Invalid account label.');const ticket=secret();await database(env).query("INSERT INTO tiktok_publisher.invites(hash,label,expires_at) VALUES($1,$2,now()+interval '30 minutes')",[hash(ticket),body.label]);result={url:ORIGIN+'/auth/tiktok/connect#ticket='+ticket,expires_in:1800};}else if(body.operation==='refresh')result=await refreshAccounts(env);else throw new OAuthError(400,'Unknown operation.');}
 else throw new OAuthError(405,'Unsupported method.');res.setHeader('Content-Type','application/json');res.end(JSON.stringify(result));
}
export function route(fn){return async(req,res)=>{headers(res);try{await fn(req,res);}catch(e){page(res,e instanceof OAuthError?e.status:503,'账号连接未完成',e instanceof OAuthError?e.message:'服务暂时不可用，请重新获取连接链接。');}};}
export function connect(req,res){if(req.method!=='GET')throw new OAuthError(405,'Use GET.');page(res,200,'连接 TikTok 账号','请先确认浏览器登录的是你要连接的 TikTok 账号。',`<button id="connect">前往 TikTok 授权</button><script nonce="NONCE">const ticket=new URLSearchParams(location.hash.slice(1)).get('ticket');history.replaceState(null,'',location.pathname);const button=document.getElementById('connect');button.disabled=!ticket;if(!ticket)document.getElementById('message').textContent='请使用新生成的账号连接链接打开此页面。';button.onclick=async()=>{button.disabled=true;try{const r=await fetch('/api/tiktok/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticket})});if(!r.ok)throw new Error();const data=await r.json();const u=new URL(data.url);if(u.origin!=='https://www.tiktok.com'||u.pathname!=='/v2/auth/authorize')throw new Error();location.assign(u.href);}catch{document.getElementById('message').textContent='链接已失效或请求失败，请重新获取连接链接。';}};</script>`);}
