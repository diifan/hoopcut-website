import pg from 'pg';
import {createHmac, randomUUID, timingSafeEqual} from 'node:crypto';
import {readFileSync} from 'node:fs';
const videos=new Set(JSON.parse(readFileSync(new URL('./comment-videos.json',import.meta.url),'utf8')));
const schema=process.env.COMMENTS_DATABASE_SCHEMA||'public';
if(!/^[a-z_][a-z0-9_]*$/.test(schema))throw new Error('Invalid comments schema');
export const commentsSchema=schema;
let pool;
export function database(){
 if(!process.env.COMMENTS_DATABASE_URL || !process.env.COMMENTS_HASH_SECRET || process.env.COMMENTS_HASH_SECRET.length<32) throw new ApiError(503,'Comments are temporarily unavailable. Please try again later.');
 return pool??=new pg.Pool({connectionString:process.env.COMMENTS_DATABASE_URL,ssl:process.env.COMMENTS_DATABASE_SSL==='true'?{ca:readFileSync(new URL('./supabase-ca.crt',import.meta.url),'utf8'),rejectUnauthorized:true}:undefined,max:3,idleTimeoutMillis:15000,connectionTimeoutMillis:5000,statement_timeout:8000});
}
export async function closeDatabase(){if(pool){await pool.end();pool=undefined;}}
export class ApiError extends Error {constructor(status,message){super(message);this.status=status;}}
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function validId(value){if(!uuid.test(value||''))throw new ApiError(400,'Invalid comment identifier.');return value;}
function hash(value){return createHmac('sha256',process.env.COMMENTS_HASH_SECRET).update(value).digest('hex');}
function publicComment(row,visitor){return {id:row.id,videoId:row.video_id,parentId:row.parent_id,author:'Guest '+row.author_hash.slice(0,6),body:row.deleted_at?'[Comment deleted]':row.body,createdAt:row.created_at,deleted:!!row.deleted_at,isMine:!row.deleted_at&&row.author_hash===visitor,replyCount:Number(row.reply_count||0)};}
async function rate(client,bucket,limit,seconds){
 const window=Math.floor(Date.now()/1000/seconds);
 const result=await client.query(`INSERT INTO ${schema}.hc_comment_rates(bucket,window_start,count) VALUES($1,$2,1) ON CONFLICT(bucket,window_start) DO UPDATE SET count=${schema}.hc_comment_rates.count+1 RETURNING count`,[bucket,window]);
 if(result.rows[0].count>limit)throw new ApiError(429,'Too many requests. Please wait a minute and try again.');
 // Keep rate counters bounded; no raw client IPs are persisted.
 await client.query(`DELETE FROM ${schema}.hc_comment_rates WHERE window_start<$1`,[window-1440]);
}
function admin(req){const expected=process.env.COMMENTS_ADMIN_TOKEN;const actual=(req.headers.authorization||'').replace(/^Bearer /,'');return !!expected&&expected.length>=32&&Buffer.byteLength(actual)===Buffer.byteLength(expected)&&timingSafeEqual(Buffer.from(actual),Buffer.from(expected));}
export async function comments(req){
 const db=database();const url=new URL(req.url,'https://hoopcut.ai');const method=req.method;
 const video=url.searchParams.get('videoId');if(!videos.has(video))throw new ApiError(404,'Video not found.');
 const token=req.headers['x-comment-client']||'';const visitor=uuid.test(token)?hash('visitor:'+token):'';
 if(method==='GET'&&url.searchParams.get('action')==='reports'){
  if(!admin(req))throw new ApiError(401,'Administrator authorization required.');
  const rows=await db.query(`SELECT c.id,c.video_id,c.body,c.deleted_at,count(r.comment_id)::int reports,max(r.created_at) last_report,array_agg(DISTINCT r.reason) reasons FROM ${schema}.hc_comment_reports r JOIN ${schema}.hc_comments c ON c.id=r.comment_id WHERE c.video_id=$1 GROUP BY c.id ORDER BY max(r.created_at) DESC LIMIT 100`,[video]);
  return {reports:rows.rows};
 }
 if(method==='GET'){
  const parent=url.searchParams.get('parentId');if(parent)validId(parent);
  const order=url.searchParams.get('sort')==='oldest'?'ASC':'DESC';
  const cursor=url.searchParams.get('cursor');let cursorTime=null,cursorId=null;
  if(cursor){try {const item=JSON.parse(Buffer.from(cursor,'base64url').toString());cursorTime=new Date(item[0]).toISOString();cursorId=validId(item[1]);}catch{throw new ApiError(400,'Invalid page cursor.');}}
  const op=order==='ASC'?'>':'<';
  const rows=await db.query(`SELECT c.*,(SELECT count(*) FROM ${schema}.hc_comments r WHERE r.parent_id=c.id) reply_count FROM ${schema}.hc_comments c WHERE video_id=$1 AND parent_id IS NOT DISTINCT FROM $2::uuid AND ($3::timestamptz IS NULL OR (created_at,id) ${op} ($3::timestamptz,$4::uuid)) ORDER BY created_at ${order},id ${order} LIMIT 21`,[video,parent,cursorTime,cursorId]);
  const list=rows.rows.slice(0,20);const last=list.at(-1);
  const count=await db.query(`SELECT count(*) FROM ${schema}.hc_comments WHERE video_id=$1 AND deleted_at IS NULL`,[video]);
  return {comments:list.map(x=>publicComment(x,visitor)),total:Number(count.rows[0].count),nextCursor:rows.rows.length>20?Buffer.from(JSON.stringify([last.created_at,last.id])).toString('base64url'):null};
 }
 if(method!=='POST'&&method!=='DELETE')throw new ApiError(405,'Method not allowed.');
 const origins=(process.env.COMMENTS_ALLOWED_ORIGINS||'https://hoopcut.ai,https://www.hoopcut.ai').split(',');
 if(!origins.includes(req.headers.origin))throw new ApiError(403,'Request origin is not allowed.');
 if(!String(req.headers['content-type']||'').startsWith('application/json'))throw new ApiError(415,'JSON is required.');
 if(!visitor)throw new ApiError(400,'Allow browser storage to post an anonymous comment.');
 const body=req.body;if(!body||typeof body!=='object'||Array.isArray(body))throw new ApiError(400,'Invalid request.');
 const ip=process.env.VERCEL?(req.headers['x-forwarded-for']||'unknown').split(',')[0].trim():req.socket?.remoteAddress||'local';
 const client=await db.connect();
 try{
  await client.query(`BEGIN`);await rate(client,hash('ip:'+ip),30,60);await rate(client,'v:'+visitor,8,60);
  if(method==='DELETE'){
   const id=validId(body.id);const row=(await client.query(`SELECT * FROM ${schema}.hc_comments WHERE id=$1 AND video_id=$2 FOR UPDATE`,[id,video])).rows[0];
   if(!row)throw new ApiError(404,'Comment not found.');
   const isAdmin=admin(req);if(row.author_hash!==visitor&&!isAdmin)throw new ApiError(403,'You can only delete your own comments.');
   await client.query(`UPDATE ${schema}.hc_comments SET body='',deleted_at=COALESCE(deleted_at,now()) WHERE id=$1`,[id]);
   await client.query(`INSERT INTO ${schema}.hc_comment_actions(comment_id,action) VALUES($1,$2)`,[id,isAdmin?'admin-delete':'author-delete']);
   await client.query(`COMMIT`);return {deleted:true};
  }
  if(body.action==='report'){
   const id=validId(body.id);if(!['spam','abuse','other'].includes(body.reason))throw new ApiError(400,'Choose a report reason.');
   const exists=(await client.query(`SELECT id FROM ${schema}.hc_comments WHERE id=$1 AND video_id=$2 AND deleted_at IS NULL`,[id,video])).rows[0];if(!exists)throw new ApiError(404,'Comment not found.');
   await client.query(`INSERT INTO ${schema}.hc_comment_reports(comment_id,reporter_hash,reason) VALUES($1,$2,$3) ON CONFLICT DO NOTHING`,[id,visitor,body.reason]);
   await client.query(`COMMIT`);return {reported:true};
  }
  const text=typeof body.body==='string'?body.body.trim():'';
  if(text.length<1||text.length>2000||/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(text))throw new ApiError(400,'Write a comment between 1 and 2,000 characters.');
  if(body.website)throw new ApiError(400,'Could not submit this comment.');
  const requestId=validId(body.requestId);const prior=(await client.query(`SELECT * FROM ${schema}.hc_comments WHERE author_hash=$1 AND request_id=$2`,[visitor,requestId])).rows[0];
  if(prior){if(prior.video_id!==video||prior.body!==text||prior.parent_id!==(body.parentId||null))throw new ApiError(409,'This request was already used.');await client.query(`COMMIT`);return {comment:publicComment(prior,visitor)};}
  let parent=body.parentId||null;
  if(parent){validId(parent);const row=(await client.query(`SELECT * FROM ${schema}.hc_comments WHERE id=$1 AND video_id=$2 FOR SHARE`,[parent,video])).rows[0];if(!row||row.deleted_at)throw new ApiError(404,'This comment can no longer receive replies.');if(row.parent_id)throw new ApiError(400,'Reply to the original comment.');}
  const row=(await client.query(`INSERT INTO ${schema}.hc_comments(id,video_id,parent_id,author_hash,body,request_id) VALUES($1,$2,$3,$4,$5,$6) RETURNING *`,[randomUUID(),video,parent,visitor,text,requestId])).rows[0];
  await client.query(`COMMIT`);return {comment:publicComment(row,visitor)};
 }catch(e){await client.query(`ROLLBACK`);throw e;}finally{client.release();}
}
