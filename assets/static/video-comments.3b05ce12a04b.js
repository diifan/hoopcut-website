/* Shared anonymous comments: every published item comes from the persistent API. */
(() => {
  'use strict';
  const root = document.querySelector('[data-video-comments]');
  if (!root) return;
  const video = root.dataset.videoId;
  const list = root.querySelector('[data-comment-list]');
  const status = root.querySelector('[data-comment-status]');
  const count = root.querySelector('[data-comment-count]');
  const more = root.querySelector('[data-comment-more]');
  const sortMenu = root.querySelector('.comments-sort');
  const sortButtons = [...root.querySelectorAll('[data-comment-sort]')];
  let sort = 'top', next = null, ready = false, listRequest = 0;
  let viewerName = 'Anonymous', savedName = '';
  try { savedName = localStorage.getItem('hoopcut.commentName') || ''; } catch (_) { /* Optional preference. */ }
  const icons = {
    like: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10v10H3V10h4Zm2 10V9l5-6 1 1c.5.5.6 1.2.4 1.8L14 9h5c1.3 0 2.2 1.2 1.9 2.4l-1.6 7A2 2 0 0 1 17.4 20H9Zm2-2h6.4L19 11h-8v7Z"/></svg>',
    dislike: '<svg viewBox="0 0 24 24" aria-hidden="true"><g transform="rotate(180 12 12)"><path d="M7 10v10H3V10h4Zm2 10V9l5-6 1 1c.5.5.6 1.2.4 1.8L14 9h5c1.3 0 2.2 1.2 1.9 2.4l-1.6 7A2 2 0 0 1 17.4 20H9Zm2-2h6.4L19 11h-8v7Z"/></g></svg>',
    empty: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M8 8h32v24H20L8 42V8Z"/><path d="M16 17h16M16 24h10"/></svg>'
  };
  function el(tag, cls, text) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function button(cls, text) { const b = el('button', cls, text); b.type = 'button'; return b; }
  function avatar(name, small = false) {
    const a = el('span', 'comment-avatar', Array.from(name.trim() || 'G')[0].toUpperCase());
    a.setAttribute('aria-hidden','true');
    const hash = Array.from(name).reduce((v,c) => v + c.codePointAt(0), 0);
    a.style.setProperty('--avatar', `hsl(${hash % 360} 26% 32%)`);
    return a;
  }
  function announce(message) { status.textContent = message; }
  function updateCount(total) { count.textContent = total.toLocaleString() + (total === 1 ? ' Comment' : ' Comments'); }
  async function api(params = {}, payload) {
    const query = new URLSearchParams({video, ...params});
    let response;
    try {
      response = await fetch('/api/comments?' + query, {
        method: payload ? 'POST' : 'GET', credentials: 'same-origin', cache:'no-store',
        headers: payload ? {'Content-Type':'application/json'} : {},
        body: payload ? JSON.stringify(payload) : undefined
      });
    } catch (_) { throw new Error('Could not connect. Please try again. Your draft is still here.'); }
    let data;
    try { data = await response.json(); }
    catch (_) { throw new Error('Comments are unavailable right now. Please try again.'); }
    if (!response.ok) throw new Error(data.error || 'Comments could not load. Please try again.');
    return data;
  }
  function textWithLinks(node, text) {
    const pattern = /https?:\/\/[^\s<>"']+/g;
    let previous = 0;
    for (const match of text.matchAll(pattern)) {
      node.append(document.createTextNode(text.slice(previous, match.index)));
      const a = el('a', '', match[0]);
      a.href = match[0]; a.rel = 'ugc nofollow noopener'; a.target = '_blank';
      node.append(a); previous = match.index + match[0].length;
    }
    node.append(document.createTextNode(text.slice(previous)));
  }
  function relativeTime(ms) {
    const seconds = Math.max(0, (Date.now() - ms) / 1000);
    if (seconds < 60) return 'just now';
    const units = [['year',31536000],['month',2592000],['week',604800],['day',86400],['hour',3600],['minute',60]];
    for (const [unit,size] of units) if (seconds >= size) {
      const n = Math.floor(seconds/size); return `${n} ${unit}${n === 1 ? '' : 's'} ago`;
    }
  }
  function makeForm(parent, onPosted, initialText = '') {
    const form = el('form', 'comments-form' + (parent ? ' is-expanded' : ''));
    form.append(avatar(viewerName));
    const compose = el('div', 'comments-compose');
    const label = el('label', 'comments-label', 'Comment anonymously · no sign-in');
    const textarea = el('textarea', 'comments-input');
    const id = 'comment-input-' + crypto.randomUUID();
    textarea.id = id; textarea.rows = 1; textarea.maxLength = 3000;
    textarea.placeholder = parent ? 'Add a reply…' : 'Add a comment…';
    textarea.setAttribute('aria-label', parent ? 'Add a reply' : 'Add a comment');
    label.htmlFor = id; textarea.value = initialText;
    const expanded = el('div', 'comments-expanded');
    const nameRow = el('div', 'comments-name-row');
    const nameId = 'comment-name-' + crypto.randomUUID();
    const nameLabel = el('label','', 'Name (optional)'); nameLabel.htmlFor = nameId;
    const name = el('input'); name.id = nameId; name.maxLength = 40;
    name.autocomplete = 'nickname'; name.placeholder = viewerName; name.value = savedName;
    name.setAttribute('aria-label', 'Name (optional)');
    nameRow.append(nameLabel,name);
    const hint = el('p','comments-hint','Posted publicly as soon as you submit. You can leave the name blank.');
    const row = el('div','comments-submit-row');
    const chars = el('span','comments-count','0 / 3,000');
    const cancel = button('comments-button','Cancel');
    const submit = button('comments-button primary',parent ? 'Reply' : 'Comment'); submit.type = 'submit'; submit.disabled = true;
    row.append(chars,cancel,submit); expanded.append(nameRow,hint,row);
    compose.append(label,textarea,expanded); form.append(compose);
    let sending = false, requestId = null, requestBody = null;
    function resize() {
      textarea.style.height = 'auto'; textarea.style.height = textarea.scrollHeight + 'px';
      chars.textContent = textarea.value.length.toLocaleString() + ' / 3,000';
      submit.disabled = !ready || sending || !textarea.value.trim();
    }
    textarea.addEventListener('focus', () => { form.classList.add('is-expanded'); resize(); });
    textarea.addEventListener('input', resize);
    function cancelForm() {
      if (sending) return;
      textarea.value = ''; requestId = null;
      if (parent) form.remove(); else { form.classList.remove('is-expanded'); textarea.blur(); resize(); }
    }
    cancel.addEventListener('click',cancelForm);
    textarea.addEventListener('keydown',e => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); if (!submit.disabled) form.requestSubmit(); }
      if (e.key === 'Escape') cancelForm();
    });
    form.addEventListener('submit', async e => {
      e.preventDefault();
      if (!ready || sending || !textarea.value.trim()) return;
      const draft = JSON.stringify([textarea.value.trim(),name.value.trim()]);
      if (!requestId || draft !== requestBody) { requestId = crypto.randomUUID(); requestBody = draft; }
      sending = true; form.setAttribute('aria-busy','true');
      textarea.disabled = true; name.disabled = true; cancel.disabled = true; resize();
      const originalLabel = submit.textContent; submit.textContent = 'Posting…';
      try {
        const result = await api({}, {action:'comment',body:textarea.value.trim(),name:name.value.trim(),parent_id:parent,request_id:requestId});
        savedName = name.value.trim();
        try { localStorage.setItem('hoopcut.commentName',savedName); } catch (_) { /* Not required. */ }
        textarea.value = ''; requestId = null; updateCount(result.total);
        announce(parent ? 'Reply posted.' : 'Comment posted.');
        await onPosted(result);
        if (parent) form.remove(); else form.classList.remove('is-expanded');
      } catch (error) { announce(error.message); }
      finally {
        sending = false; form.removeAttribute('aria-busy'); textarea.disabled = false; name.disabled = false;
        cancel.disabled = false; submit.textContent = originalLabel; resize();
      }
    });
    return {form,textarea,resize,name};
  }
  function rowFor(comment, parent = null) {
    const row = el('article','comment-row'); row.id = 'comment-' + comment.id;
    row.append(avatar(comment.name));
    const content = el('div','comment-content');
    const meta = el('div','comment-meta');
    const name = el('span','comment-name',comment.name);
    const when = el('time','comment-time',relativeTime(comment.created_at));
    when.dateTime = new Date(comment.created_at).toISOString(); when.title = new Date(comment.created_at).toLocaleString();
    meta.append(name,when);
    if (comment.is_example) meta.append(el('span','comment-example','Example'));
    const body = el('p','comment-body'); textWithLinks(body,comment.body);
    content.append(meta,body);
    if (comment.body.length > 350 || comment.body.split('\n').length > 4) {
      body.classList.add('is-collapsed');
      const expand = button('comment-expand','Read more'); expand.setAttribute('aria-expanded','false');
      expand.addEventListener('click',()=>{
        const expanded = body.classList.toggle('is-collapsed') === false;
        expand.textContent = expanded ? 'Show less' : 'Read more'; expand.setAttribute('aria-expanded',String(expanded));
      }); content.append(expand);
    }
    const actions = el('div','comment-actions');
    const up = button('comment-vote'), down = button('comment-vote');
    const likes = el('span','',comment.likes ? String(comment.likes) : '');
    up.innerHTML = icons.like; down.innerHTML = icons.dislike; up.append(likes);
    function reactionState() {
      up.setAttribute('aria-pressed',String(comment.my_vote === 1));
      down.setAttribute('aria-pressed',String(comment.my_vote === -1));
      up.setAttribute('aria-label',`${comment.my_vote === 1 ? 'Remove like from' : 'Like'} comment by ${comment.name}`);
      down.setAttribute('aria-label',`${comment.my_vote === -1 ? 'Remove dislike from' : 'Dislike'} comment by ${comment.name}`);
      likes.textContent = comment.likes ? String(comment.likes) : '';
    }
    reactionState();
    for (const [b,value] of [[up,1],[down,-1]]) b.addEventListener('click',async()=>{
      up.disabled = down.disabled = true;
      try {
        const result = await api({}, {action:'vote',comment_id:comment.id,value:comment.my_vote === value ? 0 : value});
        Object.assign(comment,result); reactionState();
      } catch(error) { announce(error.message); }
      finally { up.disabled = down.disabled = false; }
    });
    const reply = button('comment-reply','Reply');
    actions.append(up,down,reply); content.append(actions);
    const replyHost = el('div'); content.append(replyHost);
    let replyForm = null;
    const replies = el('div','comment-replies'); replies.hidden = true;
    const toggle = button('comment-replies-toggle');
    let replyNext = null, replyLoad = 0;
    function toggleText() { toggle.textContent = `${replies.hidden ? '▾' : '▴'} ${comment.reply_count} ${comment.reply_count === 1 ? 'reply' : 'replies'}`; toggle.setAttribute('aria-expanded',String(!replies.hidden)); toggle.hidden = !comment.reply_count; }
    const replyMore = button('comments-button comments-load','Show more replies'); replyMore.hidden = true;
    async function loadReplies(append = false) {
      const ticket = ++replyLoad; toggle.disabled = true;
      try {
        const data = await api({parent:comment.id,sort:'newest',offset:append ? replyNext : 0});
        if (ticket !== replyLoad) return;
        if (!append) replies.replaceChildren();
        for (const item of data.comments) replies.append(rowFor(item,comment.id));
        replyNext = data.next_offset; replyMore.hidden = replyNext === null;
        replies.append(replyMore); replies.hidden = false; toggleText();
      } catch(error) { announce(error.message); }
      finally { toggle.disabled = false; }
    }
    replyMore.addEventListener('click',()=>loadReplies(true));
    if (!parent) {
      toggleText(); content.append(toggle,replies);
      toggle.addEventListener('click',()=>{
        if (replies.hidden) loadReplies(); else { replies.hidden = true; toggleText(); }
      });
    }
    reply.addEventListener('click',()=>{
      if (replyForm?.form.isConnected) { replyForm.textarea.focus(); return; }
      replyForm = makeForm(parent || comment.id, async()=>{
        if (!parent) { comment.reply_count++; toggleText(); await loadReplies(); }
        else await load(false);
      },parent ? '@'+comment.name+' ' : '');
      replyHost.replaceChildren(replyForm.form); replyForm.textarea.focus(); replyForm.resize();
    });
    row.append(content); return row;
  }
  const composer = makeForm(null, async()=>{
    sort = 'newest'; updateSort(); await load(false);
  });
  root.querySelector('[data-comment-composer]').append(composer.form);
  function updateSort() {
    for (const b of sortButtons) b.setAttribute('aria-pressed',String(b.dataset.commentSort === sort));
  }
  async function load(append = false) {
    const ticket = ++listRequest; more.disabled = true; list.setAttribute('aria-busy','true');
    try {
      const data = await api({sort,offset:append ? next : 0});
      if (ticket !== listRequest) return;
      ready = true; viewerName = data.viewer.name; composer.name.placeholder = viewerName; composer.resize();
      updateCount(data.total); next = data.next_offset; more.hidden = next === null;
      root.querySelector('[data-comment-preview]').hidden = !data.preview;
      if (!append) list.replaceChildren();
      if (!data.comments.length && !append) {
        const empty = el('div','comments-empty'); empty.innerHTML = icons.empty;
        empty.append(el('h3','','Start the conversation'),el('p','','What stood out about this play?'));
        list.append(empty);
      }
      for (const item of data.comments) list.append(rowFor(item));
      root.querySelector('[data-comment-retry]').hidden = true;
      if (status.textContent === 'Loading comments…' || status.dataset.failed) { announce(''); delete status.dataset.failed; }
    } catch(error) {
      if (ticket !== listRequest) return;
      announce(error.message); status.dataset.failed = 'true';
      root.querySelector('[data-comment-retry]').hidden = false;
      list.querySelectorAll('.comments-skeleton').forEach(n=>n.remove());
    } finally {
      if (ticket === listRequest) { more.disabled = false; list.removeAttribute('aria-busy'); }
    }
  }
  for (const b of sortButtons) b.addEventListener('click',()=>{
    sort = b.dataset.commentSort; sortMenu.open = false; updateSort(); load(false);
  });
  root.querySelector('[data-comment-retry]').addEventListener('click',()=>load(false));
  more.addEventListener('click',()=>load(true));
  document.addEventListener('click',e=>{ if (!sortMenu.contains(e.target)) sortMenu.open = false; });
  sortMenu.addEventListener('keydown',e=>{ if(e.key === 'Escape') sortMenu.open = false; });
  updateSort(); load();
})();
