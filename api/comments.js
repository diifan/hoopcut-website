import {comments,ApiError} from '../lib/comments.js';
export default async function handler(req,res){
 res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
 try{
  if(Number(req.headers['content-length']||0)>16000||Buffer.byteLength(JSON.stringify(req.body||{}))>16000)throw new ApiError(413,'Comment request is too large.');
  res.statusCode=200;res.end(JSON.stringify(await comments(req)));
 }catch(error){res.statusCode=error instanceof ApiError?error.status:503;if(res.statusCode===429)res.setHeader('Retry-After','60');res.end(JSON.stringify({error:error instanceof ApiError?error.message:'Comments are temporarily unavailable. Please try again later.'}));}
}
