(() => {
  const video = document.querySelector('#banner-video');
  const status = document.querySelector('#player-status');
  const choices = [...document.querySelectorAll('[data-player]')];
  if (!video || !status) return;
  const media = JSON.parse(document.querySelector('#hero-media-data')?.textContent || '{}');
  const smallScreen = window.matchMedia('(max-width: 700px)');
  const reels = {
    all: { label: 'All players', count: 10 },
    blue: { label: 'Blue #1', count: 5 },
    red: { label: 'Red shorts', count: 2 },
    black: { label: 'Black kit', count: 1 },
  };
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let selected = 'all';
  let userPaused = motion.matches;
  let inView = true;
  let failed = false;
  let switching = false;
  let loaded = false;
  let ready = false;
  const summary = () => {
    const reel = reels[selected];
    return `${reel.label} · ${reel.count} made shot${reel.count === 1 ? '' : 's'}`;
  };
  const load = () => {
    if (loaded) return;
    const item = media[selected];
    if (!item) return;
    video.src = smallScreen.matches ? item.mobile : item.desktop;
    loaded = true;
    video.load();
  };
  const play = () => {
    load();
    video.play().catch(() => {
      // Explicitly selecting an avatar can retry playback if autoplay is blocked.
    });
  };
  const sync = () => {
    if (!ready) return;
    if (document.hidden || !inView || userPaused) video.pause();
    else if (!failed) play();
  };
  video.muted = true;
  if (userPaused) { video.autoplay = false; video.pause(); }
  video.addEventListener('canplay', () => {
    switching = false;
    failed = false;
    video.removeAttribute('aria-busy');
    status.textContent = summary();
    sync();
  });
  video.addEventListener('error', () => {
    failed = true;
    switching = false;
    video.removeAttribute('aria-busy');
    status.textContent = 'Video unavailable. Select a player to retry.';
  });
  choices.forEach(button => button.addEventListener('click', () => {
    const key = button.dataset.player;
    if (!reels[key]) return;
    if (key === selected && !failed) {
      userPaused = false;
      if (!switching) play();
      return;
    }
    selected = key;
    failed = false;
    switching = true;
    userPaused = false;
    video.pause();
    choices.forEach(choice => choice.setAttribute('aria-pressed', String(choice === button)));
    status.textContent = `Loading ${reels[key].label}…`;
    video.setAttribute('aria-busy', 'true');
    video.setAttribute('aria-label', summary() + ' with original shot trajectories');
    video.poster = media[key]?.poster || `assets/video/players/${key}.jpg?v=5`;
    loaded = false;
    play();
  }));
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      inView = entry.isIntersecting;
      sync();
    }, { threshold: .15 }).observe(video);
  }
  document.addEventListener('visibilitychange', sync);
  motion.addEventListener('change', event => {
    userPaused = event.matches;
    sync();
  });
  // Let the hero poster and styles paint before starting background playback.
  const begin = () => { ready = true; requestAnimationFrame(sync); };
  if (document.readyState === 'complete') begin();
  else window.addEventListener('load', begin, {once:true});
})();
