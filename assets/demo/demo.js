(() => {
  'use strict';
  const video = document.querySelector('#demo-video');
  if (!video) return;
  // Exact boundaries of the ten existing clips, from production/render_banner.py.
  const frames = [128,182,157,162,146,148,159,134,148,196];
  let totalFrames = 0;
  const shots = frames.map((n, i) => { const start = totalFrames / 30; totalFrames += n; return {id:i+1,start,end:totalFrames/30}; });
  const tracer = document.body.dataset.demo === 'tracer';
  const selected = new Set([1,4,10]);
  let current = tracer ? 4 : 1;
  let sequence = false, transitioning = false;
  const $ = s => document.querySelector(s);
  const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2,'0')}`;
  const shot = () => shots[current-1];
  const status = text => { if ($('#selection-status')) $('#selection-status').textContent = text; };
  const setCurrent = id => {
    current = id;
    $('#shot-caption').textContent = `Shot ${String(id).padStart(2,'0')} / 10`;
    document.querySelectorAll('[data-preview]').forEach(e => e.closest('.clip-row').classList.toggle('is-current',Number(e.dataset.preview)===id));
    document.querySelectorAll('[data-jump]').forEach(e => e.classList.toggle('is-current',Number(e.dataset.jump)===id));
    document.querySelectorAll('[data-shot]').forEach(e => e.setAttribute('aria-pressed',String(Number(e.dataset.shot)===id)));
  };
  const play = async () => {
    try { await video.play(); }
    catch { status('Playback paused. Press play to continue.'); }
  };
  const seek = async (seconds, shouldPlay = true) => {
    if (video.readyState === 0) await new Promise(resolve => video.addEventListener('loadedmetadata',resolve,{once:true}));
    video.currentTime = Math.min(seconds,video.duration || 52);
    if (shouldPlay) await play();
  };
  const preview = (id, shouldPlay=true) => {
    sequence = false;
    setCurrent(id);
    status(`Previewing shot ${String(id).padStart(2,'0')}.`);
    seek(shot().start,shouldPlay);
  };
  const updateSelection = () => {
    if (tracer) return;
    $('#selection-count').textContent = `${selected.size} / 10`;
    $('#selected-duration').textContent = fmt(shots.filter(s=>selected.has(s.id)).reduce((n,s)=>n+s.end-s.start,0));
    $('#play-selection').disabled = selected.size===0;
    document.querySelectorAll('[data-select]').forEach(e=>e.checked=selected.has(Number(e.dataset.select)));
    document.querySelectorAll('[data-jump]').forEach(e=>e.setAttribute('aria-pressed',String(selected.has(Number(e.dataset.jump)))));
    if (sequence) { sequence=false;video.pause();status('Selection changed. Press Play selected clips to restart.'); }
    else status(selected.size ? `${selected.size} clips selected. Ready when you are.` : 'Select at least one clip to build your shortlist.');
  };
  if (!tracer) {
    $('#clip-list').innerHTML = shots.map(s=>`<div class="clip-row"><input class="clip-check" type="checkbox" data-select="${s.id}" aria-label="Select shot ${s.id}" ${selected.has(s.id)?'checked':''}><button class="clip-preview" data-preview="${s.id}" aria-label="Preview shot ${s.id}"><img src="/assets/demo/shot-${String(s.id).padStart(2,'0')}.jpg" alt="" width="124" height="72" loading="lazy"><span><strong>Shot ${String(s.id).padStart(2,'0')}</strong><small>${fmt(s.start)} – ${fmt(s.end)}</small></span><b>▶</b></button></div>`).join('');
    $('#shot-timeline').innerHTML = shots.map(s=>`<button class="shot-marker" data-jump="${s.id}" aria-label="Jump to shot ${s.id}" aria-pressed="${selected.has(s.id)}" style="flex:${s.end-s.start}">${String(s.id).padStart(2,'0')}</button>`).join('');
    document.querySelectorAll('[data-select]').forEach(e=>e.addEventListener('change',()=>{const id=Number(e.dataset.select);e.checked?selected.add(id):selected.delete(id);updateSelection();}));
    document.querySelectorAll('[data-preview]').forEach(e=>e.addEventListener('click',()=>preview(Number(e.dataset.preview))));
    document.querySelectorAll('[data-jump]').forEach(e=>e.addEventListener('click',()=>preview(Number(e.dataset.jump))));
    $('#select-all').addEventListener('click',()=>{shots.forEach(s=>selected.add(s.id));updateSelection();});
    $('#clear-all').addEventListener('click',()=>{selected.clear();updateSelection();});
    $('#play-selection').addEventListener('click',()=>{
      if (!selected.size) return;
      sequence = true;
      setCurrent(shots.find(s=>selected.has(s.id)).id);
      status(`Playing your ${selected.size}-clip selection.`);
      seek(shot().start);
    });
    updateSelection();
  } else {
    document.querySelectorAll('[data-shot]').forEach(e=>e.addEventListener('click',()=>preview(Number(e.dataset.shot))));
    document.querySelectorAll('[data-moment]').forEach(e=>e.addEventListener('click',()=>{
      video.pause();seek(shot().start+(shot().end-shot().start)*Number(e.dataset.moment),false);
      document.querySelectorAll('[data-moment]').forEach(b=>b.setAttribute('aria-pressed',String(b===e)));
    }));
    $('#slow-replay').addEventListener('click',()=>{setSpeed(.5);preview(current);});
  }
  const setSpeed = rate => { video.playbackRate = rate;$('#speed').textContent=`${rate}×`;$('#speed').setAttribute('aria-pressed',String(rate===.5)); };
  $('#speed').addEventListener('click',()=>setSpeed(video.playbackRate===1?.5:1));
  const togglePlay = () => { if (video.paused) { if (video.currentTime>=shot().end-.06 || video.currentTime<shot().start) seek(shot().start);else play(); } else video.pause(); };
  $('#play').addEventListener('click',togglePlay);
  $('#center-play').addEventListener('click',togglePlay);
  $('#restart').addEventListener('click',()=>seek(shot().start));
  $('#sound').addEventListener('click',()=>{ video.muted=!video.muted;$('#sound').textContent=video.muted?'Sound off':'Sound on';$('#sound').setAttribute('aria-pressed',String(!video.muted));$('#sound').setAttribute('aria-label',video.muted?'Unmute video':'Mute video'); });
  // Existing sample reels contain no audio track; make that explicit rather than a fake toggle.
  $('#sound').hidden=true;
  $('#seek').addEventListener('input',e=>{
    sequence=false;video.pause();const t=Number(e.target.value);
    const found=shots.find(s=>t>=s.start&&t<s.end)||shots[9];setCurrent(found.id);seek(t,false);status('Choose Play to preview from this position.');
  });
  video.addEventListener('loadedmetadata',()=>{
    $('#seek').max=video.duration;$('#clock').textContent=`${fmt(video.currentTime)} / ${fmt(video.duration)}`;
    if(tracer && video.currentTime===0) video.currentTime=shot().start;
  });
  video.addEventListener('play',()=>{ $('#center-play').hidden=true;$('#play').textContent='Ⅱ';$('#play').setAttribute('aria-label','Pause video'); });
  video.addEventListener('pause',()=>{ $('#center-play').hidden=false;$('#play').textContent='▶';$('#play').setAttribute('aria-label','Play video'); });
  const tick = () => {
    $('#clock').textContent=`${fmt(video.currentTime)} / ${fmt(video.duration || 52)}`;$('#seek').value=video.currentTime;
    if (video.paused || transitioning) return;
    if (video.currentTime>=shot().end-.04) {
      if (sequence) {
        const next=shots.find(s=>s.id>current&&selected.has(s.id));
        if(next) { transitioning=true;setCurrent(next.id);video.currentTime=next.start;transitioning=false; }
        else {video.pause();sequence=false;status('Selection complete. Replay it or choose different clips.');}
      } else video.pause();
    }
  };
  video.addEventListener('timeupdate',tick);
  video.addEventListener('ended',()=>{if(sequence){sequence=false;status('Selection complete. Replay it or choose different clips.');}});
  // requestVideoFrameCallback keeps clip boundaries accurate during playback.
  if ('requestVideoFrameCallback' in video) { const frame=()=>{tick();video.requestVideoFrameCallback(frame);};video.requestVideoFrameCallback(frame); }
  video.addEventListener('error',()=>{$('#media-error').hidden=false;});
  $('#retry').addEventListener('click',()=>{$('#media-error').hidden=true;video.load();preview(current);});
  document.addEventListener('visibilitychange',()=>{if(document.hidden) video.pause();});
  setCurrent(current);
})();
