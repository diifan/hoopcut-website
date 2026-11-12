/* Section links remain usable without JavaScript; this adds the current location. */
(() => {
  const nav = document.querySelector('.keyword-jumps');
  if (!nav) return;
  const entries = [...nav.querySelectorAll('a[href^="#"]')]
    .map(link => ({link, section: document.getElementById(link.hash.slice(1))}))
    .filter(entry => entry.section);
  if (!entries.length) return;
  let queued = false;
  function update() {
    queued = false;
    const offset = nav.offsetHeight + parseFloat(getComputedStyle(nav).top) + 16;
    document.documentElement.style.setProperty('--keyword-nav-offset', `${offset}px`);
    const toolHeading = document.querySelector('.keyword-tool-heading');
    if (toolHeading) {
      const space = toolHeading.offsetHeight + parseFloat(getComputedStyle(toolHeading).marginBottom);
      document.documentElement.style.setProperty('--keyword-tool-heading-space', `${space}px`);
    }
    let current = entries[0];
    for (const entry of entries) {
      if (entry.section.getBoundingClientRect().top <= offset + 2) current = entry;
    }
    for (const entry of entries) {
      if (entry === current) entry.link.setAttribute('aria-current', 'location');
      else entry.link.removeAttribute('aria-current');
    }
  }
  function schedule() {
    if (!queued) { queued = true; requestAnimationFrame(update); }
  }
  window.addEventListener('scroll', schedule, {passive: true});
  window.addEventListener('resize', schedule);
  window.addEventListener('hashchange', schedule);
  window.addEventListener('load', schedule);
  if ('ResizeObserver' in window) new ResizeObserver(schedule).observe(nav);
  update();
})();
