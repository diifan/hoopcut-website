import { randomBytes } from 'node:crypto';

// Registration endpoints only: no token exchange or account binding until app
// credentials and an authenticated, state-bound authorization flow are installed.
export function callbackHandler(kind) {
  if (!['advertiser', 'account'].includes(kind)) throw new Error('Invalid callback type');
  return function handler(req, res) {
    const nonce = randomBytes(18).toString('base64');
    res.setHeader('Cache-Control', 'private, no-store, max-age=0');
    res.setHeader('X-Robots-Tag', 'noindex, nofollow, noarchive');
    res.setHeader('Referrer-Policy', 'no-referrer');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Content-Security-Policy', `default-src 'none'; script-src 'nonce-${nonce}'; style-src 'nonce-${nonce}'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`);
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    if (!['GET', 'HEAD'].includes(req.method)) {
      res.setHeader('Allow', 'GET, HEAD'); res.statusCode = 405; return res.end('Method not allowed');
    }
    const url = new URL(req.url, 'https://hoopcut.ai');
    const errorCode = url.searchParams.get('error_code');
    const denied = Boolean(url.searchParams.get('error')) || (errorCode !== null && errorCode !== '' && errorCode !== '0');
    const received = url.searchParams.has('auth_code') || url.searchParams.has('code');
    const label = kind === 'advertiser' ? 'Advertiser authorization' : 'TikTok account authorization';
    const title = denied ? 'Authorization was not completed' : received ? 'Application setup required' : 'Authorization callback ready';
    const message = denied ? 'TikTok returned an authorization error or cancellation. No account was connected. Return to the publisher to try again.' : received ? 'An authorization response arrived, but account connection is not configured yet. No account was connected. Finish the application setup, then begin a new authorization from the publisher.' : 'This is the HoopCut callback address for SWI Content Publisher. After the application is configured, begin authorization from the publisher to connect your account.';
    res.statusCode = denied ? 400 : received ? 503 : 200;
    if (req.method === 'HEAD') return res.end();
    // Never echo, log, persist, or send authorization parameters to analytics.
    // Remove the query before any user navigation; no third-party resources.
    res.end(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><meta name="referrer" content="no-referrer"><title>${label} | HoopCut</title><script nonce="${nonce}">history.replaceState(null,'',location.pathname);</script><style nonce="${nonce}">*{box-sizing:border-box}body{margin:0;background:#f5f4ee;color:#173c30;font:18px/1.6 system-ui,sans-serif}main{max-width:680px;margin:10vh auto;padding:32px}header{font-size:25px;font-weight:800;letter-spacing:-1px}small{display:block;margin-top:36px;font-size:14px}h1{font-size:clamp(28px,5vw,40px);line-height:1.2}p{color:#40584d}a{color:inherit;text-underline-offset:4px}footer{margin-top:42px;font-size:14px}</style></head><body><main><header>HOOPCUT</header><small>SWI Content Publisher · ${label}</small><h1>${title}</h1><p role="status">${message}</p><footer><a href="https://hoopcut.ai/">Return to HoopCut</a></footer></main></body></html>`);
  };
}
