import test from 'node:test';import assert from 'node:assert/strict';import {randomUUID} from 'node:crypto';import {readFileSync} from 'node:fs';
import {comments,database,closeDatabase} from '../lib/comments.js';
if(!new URL(process.env.COMMENTS_DATABASE_URL||'postgresql://invalid/').pathname.endsWith('_test'))throw new Error('Refusing destructive tests outside a dedicated *_test database');
const video='MLcda_7VYkQ';const origin='http://127.0.0.1:8767';const a=randomUUID(),b=randomUUID();
function request(method='GET',body=null,visitor=a,query='',headers={}){return {method,url:'/api/comments?videoId='+video+query,body,headers:{origin,'content-type':'application/json','x-comment-client':visitor,...headers},socket:{remoteAddress:'127.0.0.1'}};}
const post=(body,parentId=null)=>({body,parentId,requestId:randomUUID()});
await test('real PostgreSQL anonymous comments workflow',async t=>{
 await database().query(readFileSync(new URL('../lib/comments-schema.sql',import.meta.url),'utf8'));
 await database().query('TRUNCATE hc_comment_reports,hc_comment_actions,hc_comments,hc_comment_rates CASCADE');
 let root;
 await t.test('publish is immediately visible to another visitor and retry is idempotent',async()=>{
  const data=post('A real database comment');root=(await comments(request('POST',data))).comment;
  const retry=(await comments(request('POST',data))).comment;assert.equal(retry.id,root.id);
  const found=await comments(request('GET',null,b));assert.equal(found.total,1);assert.equal(found.comments[0].body,data.body);assert.equal(found.comments[0].isMine,false);assert.equal(root.isMine,true);
 });
 await t.test('reply survives a fresh connection pool',async()=>{
  await comments(request('POST',post('Reply from another browser',root.id),b));await closeDatabase();
  const result=await comments(request('GET',null,a,'&parentId='+root.id));assert.equal(result.comments[0].body,'Reply from another browser');
 });
 await t.test('invalid input, unknown parents/video and cross-origin mutation fail',async()=>{
  await assert.rejects(comments(request('POST',post('  '))),e=>e.status===400);
  await assert.rejects(comments(request('POST',post('hello',randomUUID()))),e=>e.status===404);
  await assert.rejects(comments({...request(),url:'/api/comments?videoId=bad'}),e=>e.status===404);
  await assert.rejects(comments(request('POST',post('foreign origin'),a,'',{origin:'https://evil.example'})),e=>e.status===403);
 });
 await t.test('report is deduplicated and does not hide comments before a decision',async()=>{
  await comments(request('POST',{action:'report',id:root.id,reason:'spam'},b));await comments(request('POST',{action:'report',id:root.id,reason:'spam'},b));
  assert.equal((await database().query('SELECT count(*) FROM hc_comment_reports')).rows[0].count,'1');assert.equal((await comments(request())).comments[0].deleted,false);
 });
 await t.test('only author or administrator can delete; replies survive deletion',async()=>{
  await assert.rejects(comments(request('DELETE',{id:root.id},b)),e=>e.status===403);
  await comments(request('DELETE',{id:root.id},a));const deleted=(await comments(request())).comments[0];assert.equal(deleted.deleted,true);assert.equal(deleted.body,'[Comment deleted]');
  assert.equal((await comments(request('GET',null,b,'&parentId='+root.id))).comments.length,1);
 });
 await t.test('reports require admin authorization and admin removal is audited',async()=>{
  await assert.rejects(comments(request('GET',null,b,'&action=reports')),e=>e.status===401);
  const headers={authorization:'Bearer '+process.env.COMMENTS_ADMIN_TOKEN};
  const reports=await comments(request('GET',null,b,'&action=reports',headers));assert.equal(reports.reports.length,1);
  const item=(await comments(request('POST',post('Admin removal test'),b))).comment;
  await comments(request('DELETE',{id:item.id},a,'',headers));
  assert.ok((await database().query("SELECT 1 FROM hc_comment_actions WHERE comment_id=$1 AND action='admin-delete'",[item.id])).rowCount);
 });
 await t.test('server-side throttling survives reconnection',async()=>{
  await database().query('TRUNCATE hc_comment_rates');const visitor=randomUUID();
  for(let i=0;i<8;i++)await comments(request('POST',post('Rate test '+i),visitor));await closeDatabase();
  await assert.rejects(comments(request('POST',post('Too many'),visitor)),e=>e.status===429);
 });
 await t.test('pagination has no duplicate rows and validates cursors',async()=>{
  await database().query('TRUNCATE hc_comment_rates');
  for(let i=0;i<22;i++)await comments(request('POST',post('Page test '+i),randomUUID()));
  const first=await comments(request());assert.equal(first.comments.length,20);assert.ok(first.nextCursor);
  const second=await comments(request('GET',null,a,'&cursor='+first.nextCursor));assert.ok(second.comments.length);assert.equal(new Set([...first.comments,...second.comments].map(x=>x.id)).size,first.comments.length+second.comments.length);
  await assert.rejects(comments(request('GET',null,a,'&cursor=invalid')),e=>e.status===400);
 });
 await t.test('optional names and reactions persist; top ordering and cursor paging remain valid',async()=>{
  await database().query('TRUNCATE hc_comment_rates');
  const item=(await comments(request('POST',{...post('Named comment'),name:'Court guest'},a))).comment;assert.equal(item.author,'Court guest');
  let voted=await comments(request('POST',{action:'vote',id:item.id,value:1},b));assert.equal(voted.likes,1);
  await closeDatabase();let top=await comments(request('GET',null,b,'&sort=top'));assert.equal(top.comments[0].id,item.id);assert.equal(top.comments[0].myVote,1);
  const page2=await comments(request('GET',null,b,'&sort=top&cursor='+top.nextCursor));assert.equal(new Set([...top.comments,...page2.comments].map(x=>x.id)).size,top.comments.length+page2.comments.length);
  voted=await comments(request('POST',{action:'vote',id:item.id,value:-1},b));assert.equal(voted.likes,0);assert.equal(voted.my_vote,-1);
  voted=await comments(request('POST',{action:'vote',id:item.id,value:0},b));assert.equal(voted.my_vote,0);
  await assert.rejects(comments(request('POST',{action:'vote',id:item.id,value:3},b)),e=>e.status===400);
  await assert.rejects(comments(request('POST',{...post('Bad name'),name:'x'.repeat(41)},a)),e=>e.status===400);
 });
 await database().query('TRUNCATE hc_comment_reports,hc_comment_actions,hc_comments,hc_comment_rates CASCADE');await closeDatabase();
});
