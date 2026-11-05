(() => {
 const root=document.querySelector('[data-comments-video]');if(!root)return;
 const video=root.dataset.commentsVideo, endpoint=root.dataset.commentsApi||'/api/comments';
 const list=root.querySelector('[data-comment-list]'),status=root.querySelector('[data-comment-status]'),sort=root.querySelector('[data-comment-sort]'),more=root.querySelector('[data-comment-more]');
 const uuid=()=>{if(globalThis.crypto?.randomUUID)return crypto.randomUUID();const b=crypto.getRandomValues(new Uint8Array(16));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;const h=Array.from(b,x=>x.toString(16).padStart(2,'0')).join('');return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;};
 let client='',cursor=null,generation=0;
 try{client=localStorage.getItem('hoopcut-comment-client')||uuid();localStorage.setItem('hoopcut-comment-client',client);}catch{}
 const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
 function announce(text,error=false){status.textContent=text;status.classList.toggle('error',error);}
 async function api(method='GET',body=null,query={}){
  const u=new URL(endpoint,location.origin);u.searchParams.set('videoId',video);Object.entries(query).forEach(([k,v])=>{if(v)u.searchParams.set(k,v);});
  const response=await fetch(u,{method,headers:{'Content-Type':'application/json','X-Comment-Client':client,'X-SEO-Request':'1'},body:body?JSON.stringify(body):undefined,cache:'no-store'});
  let data;try{data=await response.json();}catch{throw Error('Comments could not be loaded. Please try again.');}
  if(!response.ok)throw Error(data.error||'Comments are temporarily unavailable.');return data;
 }
 function updateCount(total){root.querySelector('[data-comment-count]').textContent=`${total} ${total===1?'comment':'comments'}`;}
 function composer(parent=null,onDone=null){
  const form=el('form','comment-composer');const avatar=el('span','comment-avatar','G');avatar.setAttribute('aria-hidden','true');form.append(avatar);
  const area=el('div','comment-compose-body');const label=el('label',null,parent?'Add a reply':'Add a comment');const input=el('textarea');input.id='comment-input-'+uuid();input.name='comment';input.placeholder=parent?'Add a reply…':'Add a comment…';input.maxLength=2000;input.rows=2;input.required=true;label.htmlFor=input.id;label.className='sr-only';area.append(label,input);
  const honey=el('input','comment-honey');honey.name='website';honey.tabIndex=-1;honey.autocomplete='off';honey.setAttribute('aria-hidden','true');area.append(honey);
  const note=el('p','comment-hint','Anonymous and public · Comments appear immediately');area.append(note);
  const actions=el('div','comment-compose-actions');const counter=el('span','comment-counter','0 / 2000');const cancel=el('button','comment-button','Cancel');cancel.type='button';const submit=el('button','comment-button comment-submit',parent?'Reply':'Comment');submit.type='submit';submit.disabled=true;actions.append(counter,cancel,submit);area.append(actions);form.append(area);
  const error=el('p','comment-form-error');error.setAttribute('role','alert');area.append(error);let requestId=uuid(),busy=false;
  input.addEventListener('input',()=>{counter.textContent=`${input.value.length} / 2000`;submit.disabled=busy||!input.value.trim();requestId=uuid();error.textContent='';});
  cancel.addEventListener('click',()=>{if(busy)return;if(parent)form.remove();else{input.value='';input.dispatchEvent(new Event('input'));input.blur();}});
  form.addEventListener('submit',async event=>{
   event.preventDefault();if(busy)return;if(!client){error.textContent='Enable browser storage to post anonymously.';return;}
   busy=true;submit.disabled=true;submit.textContent='Posting…';error.textContent='';
   try{await api('POST',{body:input.value,requestId,parentId:parent,website:honey.value});input.value='';requestId=uuid();announce(parent?'Reply posted.':'Comment posted.');if(onDone)await onDone();else await load(false);if(parent)form.remove();}
   catch(e){error.textContent=e.message;}finally{busy=false;submit.textContent=parent?'Reply':'Comment';submit.disabled=!input.value.trim();counter.textContent=`${input.value.length} / 2000`;}
  });return form;
 }
 function renderComment(c,isReply=false){
  const article=el('article',isReply?'comment-row comment-reply':'comment-row');article.dataset.commentId=c.id;
  const avatar=el('span','comment-avatar',c.author.slice(-2).toUpperCase());avatar.setAttribute('aria-hidden','true');const body=el('div','comment-main');
  const meta=el('div','comment-meta');meta.append(el('strong',null,c.author));const time=el('time',null,new Date(c.createdAt).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'}));time.dateTime=c.createdAt;meta.append(time);if(c.isMine)meta.append(el('span','comment-you','You'));body.append(meta,el('p','comment-text',c.body));article.append(avatar,body);
  const actions=el('div','comment-actions');body.append(actions);
  const replies=el('div','comment-replies');body.append(replies);let replyCursor=null,repliesLoaded=false;
  async function loadReplies(append=false){const result=await api('GET',null,{parentId:c.id,sort:'oldest',cursor:append?replyCursor:null});if(!append)replies.replaceChildren();result.comments.forEach(item=>replies.append(renderComment(item,true)));replyCursor=result.nextCursor;repliesLoaded=true;replies.hidden=false;show.hidden=false;show.textContent=replyCursor?'Load more replies':'Hide replies';updateCount(result.total);}
  if(!c.deleted&&!isReply){const reply=el('button','comment-button','Reply');reply.type='button';reply.addEventListener('click',()=>{if(body.querySelector('form')){body.querySelector('textarea').focus();return;}const f=composer(c.id,()=>loadReplies(false));body.insertBefore(f,replies);f.querySelector('textarea').focus();});actions.append(reply);}
  if(!c.deleted){const report=el('button','comment-button','Report');report.type='button';report.addEventListener('click',()=>{
   if(body.querySelector('.comment-report'))return;const form=el('form','comment-report');const label=el('label',null,'Report reason '),select=el('select');select.setAttribute('aria-label','Report reason');[['spam','Spam'],['abuse','Abusive content'],['other','Other']].forEach(([v,t])=>{const o=el('option',null,t);o.value=v;select.append(o);});label.append(select);const send=el('button','comment-button','Send report');send.type='submit';const cancel=el('button','comment-button','Cancel');cancel.type='button';cancel.onclick=()=>form.remove();form.append(label,send,cancel);actions.after(form);
   form.onsubmit=async e=>{e.preventDefault();send.disabled=true;try{await api('POST',{action:'report',id:c.id,reason:select.value});form.remove();announce('Report received. Thank you.');}catch(err){announce(err.message,true);send.disabled=false;}};
  });actions.append(report);}
  if(c.isMine){const del=el('button','comment-button','Delete');del.type='button';del.onclick=async()=>{if(!confirm('Delete your comment?'))return;del.disabled=true;try{await api('DELETE',{id:c.id});await load(false);announce('Comment deleted.');}catch(e){announce(e.message,true);del.disabled=false;}};actions.append(del);}
  const show=el('button','comment-button comment-reply-toggle',`${c.replyCount} ${c.replyCount===1?'reply':'replies'}`);show.type='button';
  if(!isReply){show.hidden=!c.replyCount;body.append(show);show.onclick=async()=>{show.disabled=true;try{if(repliesLoaded&&!replyCursor){replies.hidden=!replies.hidden;show.textContent=replies.hidden?'Show replies':'Hide replies';}else{replies.hidden=false;await loadReplies(repliesLoaded);}}catch(e){announce(e.message,true);}finally{show.disabled=false;}};}
  return article;
 }
 async function load(append=false){
  const version=++generation;more.disabled=true;sort.disabled=true;root.setAttribute('aria-busy','true');
  try{const data=await api('GET',null,{sort:sort.value,cursor:append?cursor:null});if(version!==generation)return;root.querySelector('[data-comment-retry]').hidden=true;if(!append)list.replaceChildren();data.comments.forEach(c=>list.append(renderComment(c)));cursor=data.nextCursor;more.hidden=!cursor;updateCount(data.total);if(!data.comments.length&&!append)list.append(el('p','comment-empty','Be the first to share your thoughts.'));announce('');}
  catch(e){announce(e.message,true);root.querySelector('[data-comment-retry]').hidden=false;}
  finally{if(version===generation){more.disabled=false;sort.disabled=false;root.setAttribute('aria-busy','false');}}
 }
 root.querySelector('[data-comment-compose]').append(composer());sort.addEventListener('change',()=>load(false));more.onclick=()=>load(true);
 root.querySelector('[data-comment-retry]').onclick=e=>{e.target.hidden=true;load(false);};load(false);
})();
