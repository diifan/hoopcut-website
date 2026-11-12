// Local review only. Uses the public production bridge without reading secrets.
import http from 'node:http';
import {createReadStream} from 'node:fs';
import {realpath, stat} from 'node:fs/promises';
import {dirname, extname, relative, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {pipeline} from 'node:stream/promises';

export const UPSTREAM_ENDPOINT = 'https://hoopcut.ai/api/shot-tracer';
export const DEFAULT_PORT = 8795;
const DEFAULT_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const MAX_REQUEST_BYTES = 16 * 1024;
const MAX_RESPONSE_BYTES = 1024 * 1024;
const ACTIONS = new Set(['create', 'complete', 'status', 'process', 'download', 'cancel']);
const PUBLIC_DIRECTORIES = new Set(['assets', 'blog', 'demo', 'templates', 'tools', 'videos', 'homecourt', 'shot-tracer']);
const PUBLIC_ROOT_FILES = new Set([
  'index.html', 'privacy.html', 'terms.html', 'tools.html', 'homecourt.html', 'shot-tracer.html',
  'robots.txt', 'sitemap.xml', 'video-sitemap.xml', 'rss.xml', 'feed.xml', 'atom.xml',
  'favicon.ico', 'favicon.png', 'favicon.svg', 'apple-touch-icon.png',
  'manifest.json', 'manifest.webmanifest', 'site.webmanifest',
]);
const MIME = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.xml': 'application/xml; charset=utf-8', '.txt': 'text/plain; charset=utf-8',
  '.webmanifest': 'application/manifest+json', '.svg': 'image/svg+xml',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.webp': 'image/webp', '.avif': 'image/avif', '.gif': 'image/gif', '.ico': 'image/x-icon',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime',
  '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4', '.ogg': 'audio/ogg', '.wav': 'audio/wav',
  '.vtt': 'text/vtt; charset=utf-8', '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf',
};

function fail(res, status, error) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify({error}));
}

function requestPath(rawURL) {
  // Check before WHATWG URL parsing: it normalizes away traversal segments.
  if (typeof rawURL !== 'string' || !rawURL.startsWith('/') || rawURL.startsWith('//')) return null;
  let path;
  try { path = decodeURIComponent(rawURL.split('?')[0]); } catch { return null; }
  if (/[\\\x00-\x1f\x7f%#]/.test(path) || path.includes('//')) return null;
  if (path.split('/').some(part => part.startsWith('.'))) return null;
  return path;
}

function allowedPublicFile(path) {
  const parts = path.split(sep);
  if (parts.some(part => !part || part.startsWith('.'))) return false;
  if (parts.length === 1) return PUBLIC_ROOT_FILES.has(path);
  return PUBLIC_DIRECTORIES.has(parts[0]) && Object.hasOwn(MIME, extname(path).toLowerCase());
}

async function publicFile(root, path) {
  const review = path === '/__review/tracer-keywords';
  const requested = review ? 'reports/tracer-keywords-review.html' : path === '/' ? 'index.html' : path.slice(1).replace(/\/$/, '');
  const candidates = review || extname(requested) ? [requested] : [requested, `${requested}.html`, `${requested}/index.html`];
  for (const candidate of candidates) {
    if (!review && !allowedPublicFile(candidate)) continue;
    try {
      const file = await realpath(resolve(root, candidate));
      const withinRoot = relative(root, file);
      if (withinRoot.startsWith(`..${sep}`) || withinRoot === '..' || withinRoot.startsWith(sep)) continue;
      if (review ? withinRoot !== requested : !allowedPublicFile(withinRoot)) continue;
      const metadata = await stat(file);
      if (metadata.isFile()) return {file, metadata};
    } catch (error) {
      if (!['ENOENT', 'ENOTDIR', 'EACCES', 'ELOOP'].includes(error.code)) throw error;
    }
  }
  return null;
}

export function parseRange(header, size) {
  if (!header) return null;
  const match = /^bytes=(\d*)-(\d*)$/.exec(header);
  if (!match || (!match[1] && !match[2]) || size === 0) return false;
  let start, end;
  if (!match[1]) {
    const suffix = Number(match[2]);
    if (!Number.isSafeInteger(suffix) || suffix <= 0) return false;
    start = Math.max(0, size - suffix); end = size - 1;
  } else {
    start = Number(match[1]); end = match[2] ? Number(match[2]) : size - 1;
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start >= size || end < start) return false;
    end = Math.min(end, size - 1);
  }
  return {start, end};
}

async function serveFile(req, res, found) {
  const {file, metadata} = found;
  res.setHeader('Content-Type', MIME[extname(file).toLowerCase()] || 'application/octet-stream');
  res.setHeader('Accept-Ranges', 'bytes');
  res.setHeader('Last-Modified', metadata.mtime.toUTCString());
  const range = parseRange(!req.headers['if-range'] || req.headers['if-range'] === metadata.mtime.toUTCString() ? req.headers.range : undefined, metadata.size);
  if (range === false) {
    res.setHeader('Content-Range', `bytes */${metadata.size}`);
    return fail(res, 416, 'range_not_satisfiable');
  }
  if (range) {
    res.statusCode = 206;
    res.setHeader('Content-Range', `bytes ${range.start}-${range.end}/${metadata.size}`);
  }
  res.setHeader('Content-Length', range ? range.end - range.start + 1 : metadata.size);
  if (req.method === 'HEAD') return res.end();
  await pipeline(createReadStream(file, range || {}), res);
}

function readJSON(req) {
  return new Promise((accept, reject) => {
    let size = 0;
    const chunks = [];
    const error = (status, code) => Object.assign(new Error(code), {status});
    const finish = (err, body) => {
      clearTimeout(timer);
      req.off('data', onData); req.off('end', onEnd); req.off('error', onError); req.off('aborted', onAborted);
      if (err) { req.resume(); reject(err); } else accept(body);
    };
    const onData = chunk => {
      size += chunk.length;
      if (size > MAX_REQUEST_BYTES) return finish(error(413, 'body_too_large'));
      chunks.push(chunk);
    };
    const onEnd = () => {
      try { finish(null, JSON.parse(Buffer.concat(chunks).toString('utf8'))); }
      catch { finish(error(400, 'invalid_json')); }
    };
    const onError = () => finish(error(400, 'request_interrupted'));
    const onAborted = () => finish(error(400, 'request_interrupted'));
    const timer = setTimeout(() => finish(error(408, 'request_timeout')), 10000);
    timer.unref();
    req.on('data', onData); req.on('end', onEnd); req.on('error', onError); req.on('aborted', onAborted);
  });
}

async function readUpstreamJSON(upstream) {
  if (!/\bapplication\/(?:[\w.+-]+\+)?json\b/i.test(upstream.headers.get('content-type') || '')) throw new Error('upstream_invalid_response');
  if (Number(upstream.headers.get('content-length')) > MAX_RESPONSE_BYTES) throw new Error('upstream_response_too_large');
  const reader = upstream.body?.getReader();
  if (!reader) throw new Error('upstream_invalid_response');
  const chunks = [];
  let size = 0;
  try {
    for (;;) {
      const {done, value} = await reader.read();
      if (done) break;
      size += value.length;
      if (size > MAX_RESPONSE_BYTES) throw new Error('upstream_response_too_large');
      chunks.push(Buffer.from(value));
    }
    try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); }
    catch { throw new Error('upstream_invalid_response'); }
  } finally { await reader.cancel().catch(() => {}); }
}

async function proxyBridge(req, res, fetchImpl) {
  if (req.method !== 'POST') { res.setHeader('Allow', 'POST'); return fail(res, 405, 'method_not_allowed'); }
  if (req.headers.origin !== `http://${req.headers.host}`) return fail(res, 403, 'origin_not_allowed');
  if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(req.headers['content-type'] || '')) return fail(res, 415, 'json_required');
  if (req.headers['content-encoding'] && req.headers['content-encoding'] !== 'identity') return fail(res, 415, 'content_encoding_not_supported');
  if (Number(req.headers['content-length']) > MAX_REQUEST_BYTES) return fail(res, 413, 'body_too_large');
  let body;
  try { body = await readJSON(req); } catch (error) { return fail(res, error.status || 400, error.message); }
  if (!body || typeof body !== 'object' || Array.isArray(body)) return fail(res, 400, 'invalid_request');
  if (!ACTIONS.has(body.action)) return fail(res, 400, 'invalid_action');
  if ((body.id !== undefined && (typeof body.id !== 'string' || body.id.length > 128)) ||
      (body.data !== undefined && (!body.data || typeof body.data !== 'object' || Array.isArray(body.data)))) return fail(res, 400, 'invalid_request');
  try {
    const upstream = await fetchImpl(UPSTREAM_ENDPOINT, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'Origin': 'https://hoopcut.ai'},
      body: JSON.stringify({action: body.action, id: body.id || '', data: body.data || {}}),
      redirect: 'error', signal: AbortSignal.timeout(20000),
    });
    if (upstream.status >= 300 && upstream.status < 400) return fail(res, 502, 'upstream_redirect_refused');
    const result = await readUpstreamJSON(upstream);
    res.statusCode = upstream.status;
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.end(JSON.stringify(result));
  } catch (error) {
    const timeout = error.name === 'TimeoutError' || error.name === 'AbortError';
    const code = timeout ? 'upstream_timeout' : ['upstream_invalid_response', 'upstream_response_too_large'].includes(error.message) ? error.message : 'upstream_unavailable';
    fail(res, timeout ? 504 : 502, code);
  }
}

// Dependency injection is for isolated tests; the CLI has no alternate endpoint option.
export function createTracerPreviewServer({root = DEFAULT_ROOT, fetchImpl = globalThis.fetch} = {}) {
  const rootPromise = realpath(root);
  const server = http.createServer(async (req, res) => {
    res.setHeader('X-Robots-Tag', 'noindex, nofollow');
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    const localHosts = new Set([`127.0.0.1:${req.socket.localPort}`, `localhost:${req.socket.localPort}`]);
    if (!localHosts.has(req.headers.host)) return fail(res, 403, 'host_not_allowed');
    const path = requestPath(req.url);
    if (!path) return fail(res, 400, 'invalid_path');
    try {
      if (path === '/api/shot-tracer') return await proxyBridge(req, res, fetchImpl);
      if (!['GET', 'HEAD'].includes(req.method)) { res.setHeader('Allow', 'GET, HEAD'); return fail(res, 405, 'method_not_allowed'); }
      // Local robots overrides the production file; preview URLs must never be indexed.
      if (path === '/robots.txt') {
        const text = 'User-agent: *\nDisallow: /\n';
        res.setHeader('Content-Type', 'text/plain; charset=utf-8');
        res.setHeader('Content-Length', Buffer.byteLength(text));
        return res.end(req.method === 'HEAD' ? undefined : text);
      }
      const found = await publicFile(await rootPromise, path);
      if (!found) return fail(res, 404, 'not_found');
      await serveFile(req, res, found);
    } catch (error) {
      if (!res.headersSent && !res.destroyed) fail(res, 500, 'preview_unavailable');
      else if (!res.destroyed) res.destroy(error);
    }
  });
  server.requestTimeout = 15000;
  server.headersTimeout = 10000;
  return server;
}

export async function proxyAwareFetch(env = process.env) {
  if (![env.HTTP_PROXY, env.HTTPS_PROXY, env.http_proxy, env.https_proxy].some(Boolean)) return globalThis.fetch;
  // No global dispatcher changes, credential loading or client-header forwarding.
  const {fetch, EnvHttpProxyAgent} = await import('undici');
  const dispatcher = new EnvHttpProxyAgent({httpProxy: env.http_proxy || env.HTTP_PROXY, httpsProxy: env.https_proxy || env.HTTPS_PROXY, noProxy: env.no_proxy || env.NO_PROXY});
  const fetchImpl = (url, options) => fetch(url, {...options, dispatcher});
  fetchImpl.close = () => dispatcher.close();
  return fetchImpl;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const port = Number(process.env.PORT || DEFAULT_PORT);
    if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('PORT must be between 1 and 65535.');
    const fetchImpl = await proxyAwareFetch();
    const server = createTracerPreviewServer({fetchImpl});
    server.on('error', error => { console.error(`Preview could not start: ${error.code || error.message}`); process.exitCode = 1; fetchImpl.close?.(); });
    server.listen(port, '127.0.0.1', () => console.log(`Local review: http://127.0.0.1:${port}/__review/tracer-keywords`));
    for (const signal of ['SIGTERM', 'SIGINT']) process.once(signal, () => server.close(async () => { await fetchImpl.close?.(); }));
  } catch (error) {
    console.error(`Preview could not start: ${error.code === 'ERR_MODULE_NOT_FOUND' ? 'Install dependencies (npm ci) for HTTP(S)_PROXY support.' : error.message}`);
    process.exitCode = 1;
  }
}
