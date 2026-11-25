#!/usr/bin/env python3
"""Private operator client; never emits application secrets or account tokens."""
import argparse
import json
import pathlib
import sys
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument('operation', choices=['list', 'refresh', 'invite'])
parser.add_argument('--label', choices=['GolfCut', 'HoopCut'])
args = parser.parse_args()
path = pathlib.Path('/var/lib/swi-codex/.local/state/tiktok-publisher/.env')
if path.stat().st_mode & 0o077:
    sys.exit('Refusing environment file accessible by other users.')
env = dict(line.split('=', 1) for line in path.read_text().splitlines() if line and not line.startswith('#'))
body = None if args.operation == 'list' else {'operation': args.operation}
if args.operation == 'invite':
    if not args.label:
        parser.error('--label is required for invite')
    body['label'] = args.label
request = urllib.request.Request(
    'https://hoopcut.ai/api/tiktok/manage',
    data=json.dumps(body).encode() if body else None,
    headers={'Authorization': 'Bearer ' + env['TIKTOK_ADMIN_KEY'], 'Content-Type': 'application/json'})
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
try:
    with urllib.request.build_opener(NoRedirect).open(request, timeout=65) as response:
        result = json.load(response)
    print(json.dumps(result, ensure_ascii=False))
    if any(row.get('status') == 'refresh_failed' for row in result.get('results', [])):
        sys.exit(1)
except Exception:
    sys.exit('TikTok management request failed; credentials and provider response omitted.')
