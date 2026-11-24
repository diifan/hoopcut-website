import test from 'node:test';
import assert from 'node:assert/strict';
import {callbackHandler} from '../lib/tiktok-callback.js';
function call(kind,url,method='GET'){const r={headers:{},setHeader(k,v){this.headers[k]=v},end(body=''){this.body=body}};callbackHandler(kind)({url,method},r);return r;}
for(const kind of ['advertiser','account']) {
 test(`${kind} callback is available, unindexed and uncached`,()=>{const r=call(kind,'/callback');assert.equal(r.statusCode,200);assert.match(r.headers['X-Robots-Tag'],/noindex/);assert.match(r.headers['Cache-Control'],/no-store/);assert.match(r.body,/Authorization callback ready/);assert.match(r.body,/history.replaceState/);assert.doesNotMatch(r.body,/<script[^>]+src=/);});
 test(`${kind} does not leak code or claim connection`,()=>{for(const param of ['code','auth_code']){const r=call(kind,`/callback?${param}=SECRET_CANARY&state=STATE_CANARY`);assert.equal(r.statusCode,503);assert.doesNotMatch(r.body,/SECRET_CANARY|STATE_CANARY/);assert.match(r.body,/No account was connected/);}});
 test(`${kind} cancellation is not successful authorization`,()=>{const r=call(kind,'/callback?error=access_denied&error_description=SECRET_CANARY');assert.equal(r.statusCode,400);assert.doesNotMatch(r.body,/SECRET_CANARY/);});
}
test('POST cannot bind accounts',()=>assert.equal(call('account','/callback','POST').statusCode,405));
test('HEAD has no body',()=>assert.equal(call('account','/callback','HEAD').body,''));
