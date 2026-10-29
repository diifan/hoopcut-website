/* Optional analytics. Editor field values never enter an event payload. */
(() => {
  'use strict';
  const config = JSON.parse(document.querySelector('#site-settings')?.textContent || '{}').analytics || {};
  const local = ['localhost','127.0.0.1',''].includes(location.hostname);
  const production = location.hostname === 'hoopcut.ai';
  const debug = local && window.__HOOPCUT_ANALYTICS_DEBUG__ === true;
  const active = production && config.enabled === true;
  if (active) {
    window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
    window.va('beforeSend', event => {
      // Keep query strings and hashes (including user-entered data) out of URLs.
      try { const url = new URL(event.url); event.url = url.origin + url.pathname; } catch {}
      return event;
    });
    const script = document.createElement('script');
    script.defer = true; script.src = config.scriptSrc || '/_vercel/insights/script.js';
    document.head.append(script);
  }
  const names = new Set(['tool_start','export_success','print_click','demo_click','app_outbound']);
  window.hoopcutTrack = (name, detail = {}) => {
    if (!names.has(name)) return;
    // Only code-owned identifiers, never form values, URLs or search queries.
    const data = {page: location.pathname};
    if (typeof detail.tool === 'string' && /^basketball-[a-z-]+$/.test(detail.tool)) data.tool = detail.tool;
    if (['svg','png','csv','original'].includes(detail.format)) data.format = detail.format;
    if (['auto-clipping','shot-tracer'].includes(detail.demo)) data.demo = detail.demo;
    if (debug) window.dispatchEvent(new CustomEvent('hoopcut:analytics-debug', {detail:{name,data}}));
    if (active && config.customEvents === true) window.va('event', {name,data});
  };
  document.addEventListener('click', event => {
    const a = event.target.closest('a');
    if (!a) return;
    if (a.dataset.appAccess === 'app-store') window.hoopcutTrack('app_outbound');
    const match = a.getAttribute('href')?.match(/^\/demo\/(auto-clipping|shot-tracer)(?:#.*)?$/);
    if (match) window.hoopcutTrack('demo_click', {demo:match[1]});
  });
})();
