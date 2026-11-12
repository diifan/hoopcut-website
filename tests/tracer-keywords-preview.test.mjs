import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import {mkdtemp, mkdir, writeFile, symlink, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createTracerPreviewServer, parseRange, UPSTREAM_ENDPOINT} from '../server/tracer-keywords-preview.js';

async function fixture(t, fetchImpl = async () => { throw new Error('Unexpected upstream request'); }) {
  const root = await mkdtemp(join(tmpdir(), 'hoopcut-tracer-preview-'));
  for (const folder of ['assets', 'tools/nested', 'reports', 'server', 'content', '.git']) await mkdir(join(root, folder), {recursive: true});
  const files = {'index.html': '<h1>Home</h1>', 'shot-tracer.html': '<h1>Tracer</h1>', 'tools/shot-tracer.html': '<h1>Tool</h1>', 'tools/nested/index.html': '<h1>Nested</h1>', 'assets/clip.mp4': '0123456789abcdef', 'assets/tool.js': 'console.log("public")', 'assets/captions.vtt': 'WEBVTT', 'assets/tool.js.map': 'source map', 'reports/tracer-keywords-review.html': '<h1>Review</h1>', 'server/secret.js': 'secret', 'content/private.json': '{"private":true}', '.env': 'SECRET=value', '.git/config': 'private git config', 'package.json': '{"private":true}', 'comment-admin.html': 'private admin', 'robots.txt': 'User-agent: *\nAllow: /'};
  for (const [path, text] of Object.entries(files)) await writeFile(join(root, path), text);
  await symlink(join(root, 'server/secret.js'), join(root, 'assets/secret.js'));
  await symlink('/etc/passwd', join(root, 'assets/outside.json'));
  const server = createTracerPreviewServer({root, fetchImpl});
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  t.after(async () => { await new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }); await rm(root, {recursive: true, force: true}); });
  const port = server.address().port;
  const origin = `http://127.0.0.1:${port}`;
  const request = (path, {method = 'GET', headers = {}, body, chunked = false} = {}) => new Promise((resolve, reject) => {
    const req = http.request({host: '127.0.0.1', port, path, method, headers: {...headers, ...(body !== undefined && !chunked && !Object.hasOwn(headers, 'Content-Length') ? {'Content-Length': Buffer.byteLength(body)} : {})}}, res => {
      const chunks = [];
      res.on('data', chunk => chunks.push(chunk));
      res.on('end', () => resolve({status: res.statusCode, headers: res.headers, text: Buffer.concat(chunks).toString('utf8')}));
    });
    req.on('error', reject);
    if (body !== undefined) req.write(body);
    req.end();
  });
  const post = (body, options = {}) => request('/api/shot-tracer', {method: 'POST', body: JSON.stringify(body), ...options, headers: {'Content-Type': 'application/json', Origin: origin, ...options.headers}});
  return {request, post, origin, port};
}

test('serves clean URLs, local review, public MIME and noindex without directory listings', async t => {
  const f = await fixture(t);
  for (const [path, expected] of [['/', 'Home'], ['/shot-tracer?preview=1', 'Tracer'], ['/tools/shot-tracer', 'Tool'], ['/tools/nested/', 'Nested'], ['/__review/tracer-keywords', 'Review']]) {
    const res = await f.request(path);
    assert.equal(res.status, 200, path);
    assert.match(res.text, new RegExp(expected));
    assert.match(res.headers['content-type'], /^text\/html/);
    assert.equal(res.headers['x-robots-tag'], 'noindex, nofollow');
  }
  assert.match((await f.request('/assets/tool.js')).headers['content-type'], /^text\/javascript/);
  assert.match((await f.request('/assets/captions.vtt')).headers['content-type'], /^text\/vtt/);
  assert.equal((await f.request('/assets/')).status, 404);
  assert.equal((await f.request('/robots.txt')).text, 'User-agent: *\nDisallow: /\n');
  const head = await f.request('/shot-tracer', {method: 'HEAD'});
  assert.equal(head.status, 200); assert.equal(head.text, ''); assert.ok(Number(head.headers['content-length']) > 0);
});

test('video supports single byte ranges, suffixes, HEAD, and unsatisfiable ranges', async t => {
  const f = await fixture(t);
  const full = await f.request('/assets/clip.mp4');
  assert.equal(full.headers['content-type'], 'video/mp4'); assert.equal(full.text, '0123456789abcdef');
  for (const [range, text, contentRange] of [['bytes=2-5', '2345', 'bytes 2-5/16'], ['bytes=-3', 'def', 'bytes 13-15/16'], ['bytes=14-', 'ef', 'bytes 14-15/16'], ['bytes=14-999', 'ef', 'bytes 14-15/16']]) {
    const res = await f.request('/assets/clip.mp4', {headers: {Range: range}});
    assert.equal(res.status, 206); assert.equal(res.text, text); assert.equal(res.headers['content-range'], contentRange);
  }
  const head = await f.request('/assets/clip.mp4', {method: 'HEAD', headers: {Range: 'bytes=0-3'}});
  assert.equal(head.status, 206); assert.equal(head.text, ''); assert.equal(head.headers['content-length'], '4');
  assert.equal((await f.request('/assets/clip.mp4', {headers: {Range: 'bytes=0-3', 'If-Range': 'outdated'}})).status, 200);
  for (const range of ['bytes=16-', 'bytes=-0', 'bytes=7-2', 'bytes=0-1,3-4', 'bad']) {
    const res = await f.request('/assets/clip.mp4', {headers: {Range: range}});
    assert.equal(res.status, 416); assert.equal(res.headers['content-range'], 'bytes */16');
  }
  assert.equal(parseRange('bytes=0-', 0), false);
});

test('rejects traversal, hidden paths, sensitive files, source maps and unsafe symlinks', async t => {
  const f = await fixture(t);
  for (const path of ['/../.env', '/%2e%2e/.env', '/assets/%2e%2e/server/secret.js', '/assets%5c..%5c.env', '/%252e%252e/.env', '/bad%ZZ', '//evil.example/path']) assert.equal((await f.request(path)).status, 400, path);
  for (const path of ['/package.json', '/server/secret.js', '/content/private.json', '/reports/tracer-keywords-review.html', '/comment-admin', '/assets/tool.js.map', '/assets/secret.js', '/assets/outside.json', '/api/other']) assert.equal((await f.request(path)).status, 404, path);
  assert.equal((await f.request('/.git/config')).status, 400);
  assert.equal((await f.request('/assets/clip.mp4', {method: 'POST'})).status, 405);
});

test('requires exact local host and matching origin before any upstream request', async t => {
  let calls = 0;
  const f = await fixture(t, async () => { calls++; return Response.json({}); });
  for (const host of ['evil.example', '127.0.0.1:999', `127.0.0.1:${f.port}.evil`, `localhost:${f.port}@evil.example`]) assert.equal((await f.request('/', {headers: {Host: host}})).status, 403);
  for (const origin of ['https://hoopcut.ai', 'null', 'http://evil.example', `http://localhost:${f.port}`]) assert.equal((await f.post({action: 'status'}, {headers: {Origin: origin}})).status, 403);
  assert.equal((await f.request('/api/shot-tracer', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{"action":"status"}'})).status, 403);
  assert.equal(calls, 0);
  const local = await f.post({action: 'status'}, {headers: {Host: `localhost:${f.port}`, Origin: `http://localhost:${f.port}`}});
  assert.equal(local.status, 200); assert.equal(calls, 1);
});

test('proxies only six browser actions to fixed endpoint and strips credentials and arbitrary fields', async t => {
  const calls = [];
  const f = await fixture(t, async (url, options) => { calls.push({url, options}); return Response.json({state: 'fixture-only'}, {headers: {'Set-Cookie': 'must-not-forward=1'}}); });
  for (const action of ['create', 'complete', 'status', 'process', 'download', 'cancel']) {
    const res = await f.post({action, id: 'test-job', data: {start: 0, end: 5}, url: 'https://evil.example'}, {headers: {Authorization: 'Bearer not-forwarded', Cookie: 'secret=not-forwarded', 'X-Hc-Worker': 'not-forwarded'}});
    assert.equal(res.status, 200); assert.equal(JSON.parse(res.text).state, 'fixture-only'); assert.equal(res.headers['set-cookie'], undefined);
  }
  assert.equal(calls.length, 6);
  for (const {url, options} of calls) {
    assert.equal(url, UPSTREAM_ENDPOINT);
    assert.deepEqual(options.headers, {'Content-Type': 'application/json', Origin: 'https://hoopcut.ai'});
    assert.equal(options.redirect, 'error'); assert.ok(options.signal instanceof AbortSignal);
    assert.deepEqual(Object.keys(JSON.parse(options.body)).sort(), ['action', 'data', 'id']);
  }
});

test('validates JSON, action, field types, encoding and 16KB request limits without upstream calls', async t => {
  let calls = 0;
  const f = await fixture(t, async () => { calls++; return Response.json({}); });
  for (const body of [null, [], {action: 'poll'}, {action: 'worker'}, {action: 'status', id: {}}, {action: 'status', data: []}, {action: 'status', data: null}]) assert.equal((await f.post(body)).status, 400);
  assert.equal((await f.post({action: 'status'}, {body: '{broken'})).status, 400);
  assert.equal((await f.post({action: 'status'}, {headers: {'Content-Type': 'text/plain'}})).status, 415);
  assert.equal((await f.post({action: 'status'}, {headers: {'Content-Encoding': 'gzip'}})).status, 415);
  for (const chunked of [false, true]) assert.equal((await f.post({action: 'status', data: {value: 'a'.repeat(16384)}}, {chunked})).status, 413);
  assert.equal((await f.request('/api/shot-tracer')).status, 405);
  assert.equal(calls, 0);
});

test('preserves real upstream error status and reports unavailable, malformed or redirected responses', async t => {
  const responses = [
    () => Response.json({error: 'rate_limited'}, {status: 429}),
    () => { throw new Error('private connection detail must not leak'); },
    () => new Response('<h1>Login</h1>', {headers: {'Content-Type': 'text/html'}}),
    () => new Response('bad json', {headers: {'Content-Type': 'application/json'}}),
    () => Response.json({redirect: true}, {status: 302}),
    () => { throw new DOMException('Timeout', 'TimeoutError'); },
  ];
  const f = await fixture(t, async () => responses.shift()());
  for (const [status, error] of [[429, 'rate_limited'], [502, 'upstream_unavailable'], [502, 'upstream_invalid_response'], [502, 'upstream_invalid_response'], [502, 'upstream_redirect_refused'], [504, 'upstream_timeout']]) {
    const res = await f.post({action: 'status'});
    assert.equal(res.status, status); assert.deepEqual(JSON.parse(res.text), {error});
    assert.equal(res.headers['x-robots-tag'], 'noindex, nofollow');
  }
});

test('enforces inclusive 16KB JSON limit and rejects oversized upstream JSON', async t => {
  let calls = 0;
  const f = await fixture(t, async () => { calls++; return calls === 1 ? Response.json({ok: true}) : Response.json({value: 'x'.repeat(1024 * 1024)}); });
  const body = {action: 'status', data: {value: ''}};
  body.data.value = 'a'.repeat(16384 - Buffer.byteLength(JSON.stringify(body)));
  assert.equal(Buffer.byteLength(JSON.stringify(body)), 16384);
  assert.equal((await f.post(body)).status, 200);
  body.data.value += 'a';
  assert.equal((await f.post(body)).status, 413);
  assert.equal(calls, 1);
  const res = await f.post({action: 'status'});
  assert.equal(res.status, 502); assert.equal(JSON.parse(res.text).error, 'upstream_response_too_large');
});
