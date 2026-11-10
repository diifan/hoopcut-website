/* HoopCut attribution v1. No fingerprinting, form values or full URLs. */
(() => {
  'use strict';
  if (window.hoopcutAttribution) return;
  const cfg = JSON.parse(document.querySelector('#attribution-settings')?.textContent || '{}');
  const environment = cfg.environment === 'production' ? 'production' : 'staging';
  const key = 'hoopcut.attribution.v1.' + environment;
  const uuid = () => crypto.randomUUID();
  const now = () => Date.now();
  const clean = value => typeof value === 'string' && !/[\x00-\x1f@]/.test(value) ? value.trim().slice(0, 200) || null : null;
  const read = (storage, name) => { try { return JSON.parse(storage.getItem(name)); } catch { return null; } };
  const write = (storage, name, value) => { try { storage.setItem(name, JSON.stringify(value)); return true; } catch { return false; } };
  let storage; try { storage = sessionStorage; } catch {}
  let persistent; try { if (cfg.persistentStorageAllowed === true) persistent = localStorage; } catch {}
  let state = read(persistent || storage, key);
  if (!state || state.expires < now()) state = {visitor:uuid(), expires:now()+90*86400000};
  let scope = persistent && write(persistent, key, state) ? 'persistent' : 'session';
  const save = () => write(scope === 'persistent' ? persistent : storage, key, state);
  let queue = (read(storage, key+'.queue') || []).filter(x => now()-Date.parse(x.occurred_at)<86400000).slice(-100);
  let pageID, path, played = new Set(), timer, active = 0, retry = 1000;
  const inFlight = new Set();
  const source = () => {
    const q = new URL(location.href).searchParams;
    const fields = Object.fromEntries(['source','medium','campaign','content','term'].map(k => [k,clean(q.get('utm_'+k))]));
    let host = null; try { host = new URL(document.referrer).hostname; } catch {}
    const external = host && ![location.hostname,'hoopcut.ai','www.hoopcut.ai'].includes(host);
    return {source:fields.source?.toLowerCase() || (external ? host : 'direct'), medium:fields.source ? fields.medium?.toLowerCase() || 'unspecified' : external ? 'referral' : 'none', campaign:fields.campaign || 'website_default',content:fields.content,term:fields.term,referrer_host:host};
  };
  const touch = () => {
    if (!state.session || now()-state.last >= 1800000) state.session = {id:uuid(),...source()};
    if (!state.first) state.first = {...state.session,at:new Date().toISOString()};
    state.last = now(); save();
  };
  const persistQueue = () => { queue = queue.filter(x => now()-Date.parse(x.occurred_at)<86400000).slice(-100); write(storage,key+'.queue',queue); };
  const later = delay => { clearTimeout(timer); timer = setTimeout(flush,delay); };
  async function flush(urgent=false) {
    persistQueue();
    // Reserve a second keepalive request for a download. A pending page/video
    // request must not hold the click until after navigation suspends JS timers.
    if (active >= (urgent ? 2 : 1)) return;
    const pending=queue.filter(e=>!inFlight.has(e.event_id) && (!urgent || e.event_name==='download_clicked'));
    const batch=[]; for(const item of pending.slice(0,20)) { if(new TextEncoder().encode(JSON.stringify({schema_version:1,events:[...batch,item]})).length>32768) break; batch.push(item); }
    if (!batch.length) return;
    const ids=new Set(batch.map(e=>e.event_id));
    for (const id of ids) inFlight.add(id);
    active++;
    try {
      const response=await fetch('/api/analytics/events',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({schema_version:1,events:batch}),keepalive:true,...(typeof AbortSignal!=='undefined' && typeof AbortSignal.timeout==='function' ? {signal:AbortSignal.timeout(12000)} : {})});
      if (response.ok) {
        const result=await response.json();
        // HTTP 200 may contain per-event rejections. Never clear other requests'
        // events or lose queued data on a malformed/incomplete acknowledgement.
        if (!['accepted_event_ids','duplicate_event_ids','rejected'].every(k=>Array.isArray(result?.[k]))) throw Error('invalid_receipt');
        const acknowledged=[...result.accepted_event_ids,...result.duplicate_event_ids,...result.rejected.map(x=>x?.event_id)];
        if (acknowledged.some(id=>!ids.has(id)) || new Set(acknowledged).size!==acknowledged.length) throw Error('invalid_receipt');
        const done=new Set(acknowledged);
        queue=queue.filter(x=>!done.has(x.event_id)); retry=done.size ? 1000 : Math.min(retry*2,300000);
      } else if ([400,413].includes(response.status)) { queue=queue.filter(x=>!ids.has(x.event_id)); }
      else if (response.status===429) { const h=response.headers.get('Retry-After');retry=Math.max(1000, Number.isFinite(Number(h))&&h ? Number(h)*1000 : Date.parse(h)-now() || 60000); }
      else retry=Math.min(retry*2,300000);
    } catch { retry=Math.min(retry*2,300000); }
    finally { active--;for(const id of ids)inFlight.delete(id);persistQueue();if(queue.length) later(retry); }
  }

  function emit(name, detail={}) {
    touch(); const event={schema_version:1,product:'hoopcut',environment,event_id:uuid(),event_name:name,occurred_at:new Date().toISOString(),visitor_id:state.visitor,visitor_scope:scope,web_session_id:state.session.id,page_view_id:pageID,page_path:location.pathname,referrer_host:state.session.referrer_host,first_touch_at:state.first.at,...detail};
    for(const field of ['source','medium','campaign','content','term']) {event['session_'+field]=state.session[field];event['first_touch_'+field]=state.first[field];}
    queue.push(event);persistQueue();later(0);return event;
  }
  function page(force=false) { if(document.visibilityState==='hidden'||document.prerendering)return;if(!force && path===location.pathname)return;path=location.pathname;pageID=uuid();played=new Set();emit('page_view'); }
  function video(id, trigger) { if(!pageID)page();if(!pageID||played.has(id))return;played.add(id);emit('video_play',{video_id:id,playback_trigger:trigger}); }
  const storeURL='https://apps.apple.com/app/id6824860341';
  const ctas=new Set(['header_download','hero_download','video_detail_download','footer_download','mobile_sticky_download','article_download','resource_download']);
  function destination(click,cta) {
    try {
      const base=new URL(cfg.oneLinkBaseURL); if(base.protocol!=='https:'||base.username||base.password||base.host!=='hoopcut.onelink.me'||base.pathname!=='/SDN0'||!cfg.oneLinkHosts?.includes(base.hostname))throw Error();
      const fixed={mediaSource:'hoopcut_website',campaign:state.session.campaign,channel:state.session.source,afSub1:click,afSub2:cta,afSub3:state.session.medium,afSub4:state.session.content,afSub5:environment};
      const result=window.AF_SMART_SCRIPT?.generateOneLinkURL({oneLinkURL:base.origin+base.pathname,afParameters:Object.fromEntries(Object.entries(fixed).map(([k,v])=>[k,{keys:[],defaultValue:v||''}]))});
      const generated=new URL(result.clickURL);if(generated.origin!==base.origin||generated.pathname!==base.pathname||generated.username||generated.password||generated.searchParams.get('af_js_web')!=='true'||!/^\d+_\d+_\d+$/.test(generated.searchParams.get('af_ss_ver')||''))throw Error();
      // Rebuild from the allowlist: SDK automatic gclid/referrer/extra params are not v1 fields.
      const url=new URL(base.origin+base.pathname);
      const values={pid:fixed.mediaSource,c:fixed.campaign,af_channel:fixed.channel,af_sub1:click,af_sub2:cta,af_sub3:fixed.afSub3,af_sub4:fixed.afSub4,af_sub5:environment};
      for(const [k,v] of Object.entries(values))if(v!==null)url.searchParams.set(k,v);
      url.searchParams.set('af_js_web','true');url.searchParams.set('af_ss_ver',generated.searchParams.get('af_ss_ver'));
      return {url:url.href,type:'onelink'};
    } catch {return {url:storeURL,type:'app_store_fallback'};}
  }
  function activate(e) {
    if((e.type==='auxclick'&&e.button!==1)||e.defaultPrevented)return;
    const a=e.target.closest?.('a[data-attribution-cta]');if(!a||!ctas.has(a.dataset.attributionCta))return;
    if(!pageID)page();touch();const click=uuid(),dest=destination(click,a.dataset.attributionCta);
    a.href=dest.url;emit('download_clicked',{click_id:click,cta_id:a.dataset.attributionCta,destination_type:dest.type});
    // Native navigation (including keyboard/new tab) proceeds immediately. Never await collection.
    void flush(true);setTimeout(()=>{a.href=storeURL;},0);
  }
  document.addEventListener('click',activate);document.addEventListener('auxclick',activate);
  let lastActivity=0;for(const name of ['pointerdown','keydown','scroll'])document.addEventListener(name,()=>{if(now()-lastActivity>1000){lastActivity=now();touch();}},{passive:true});
  document.addEventListener('playing',e=>{const v=e.target;if(v.tagName==='VIDEO'){const id=v.dataset.analyticsVideo || new URL(v.currentSrc||v.src,location.href).pathname;video(id,v.dataset.analyticsTrigger|| (v.autoplay||v.id==='banner-video'?'autoplay':'user'));}},true);
  document.addEventListener('click',e=>{if(e.target.closest?.('[data-player]'))document.querySelector('#banner-video')?.setAttribute('data-analytics-trigger','user');},true);
  window.addEventListener('message',e=>{
    if(!['https://www.youtube.com','https://www.youtube-nocookie.com'].includes(e.origin))return;
    const f=[...document.querySelectorAll('iframe[data-analytics-video]')].find(x=>x.contentWindow===e.source);if(!f)return;
    let m;try{m=typeof e.data==='string'?JSON.parse(e.data):e.data;}catch{return;}
    if((m?.event==='onStateChange'&&m.info===1)||(m?.event==='infoDelivery'&&m.info?.playerState===1))video(f.dataset.analyticsVideo,'user');
  });
  // YouTube postMessage event subscription; a click/focus is never considered playback.
  const subscribe=f=>{f.contentWindow?.postMessage(JSON.stringify({event:'listening',id:f.id}),'https://www.youtube-nocookie.com');f.contentWindow?.postMessage(JSON.stringify({event:'command',func:'addEventListener',args:['onStateChange']}),'https://www.youtube-nocookie.com');};
  document.querySelectorAll('iframe[data-analytics-video]').forEach(f=>{f.addEventListener('load',()=>subscribe(f));subscribe(f);});
  for(const method of ['pushState','replaceState']){const original=history[method];history[method]=function(...args){const old=location.pathname+location.search;const result=original.apply(this,args);if(old!==location.pathname+location.search)page(true);return result;};}
  window.addEventListener('popstate',()=>page(true));window.addEventListener('pageshow',e=>{if(e.persisted)page(true);void flush(true);void flush();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){void flush(true);void flush();}else {page();void flush(true);void flush();}});
  window.addEventListener('online',()=>later(0));window.addEventListener('pagehide',()=>{void flush(true);void flush();});
  window.hoopcutAttribution=Object.freeze({version:1});
  requestAnimationFrame(()=>page());
})();
