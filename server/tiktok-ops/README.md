# TikTok Accounts API integration

2026-11-25: deployed and promoted as dpl_GSKrJYah331Kh7UjH9asRBCEnVxp (source c1583fc7). Database migration and runtime DML/RLS checks passed. Production account listing and single-use invitation/replay checks passed. Refresh service/timer installed and first execution succeeded. GolfCut invitation opened in Mac mini Safari; actual TikTok consent and token exchange still pending.

Private environment: `/var/lib/swi-codex/.local/state/tiktok-publisher/.env`, directory 0700 and file 0600. Never copy values to Git, frontend output, reports, or terminal logs. Contains TIKTOK_APP_ID, TIKTOK_APP_SECRET, TIKTOK_REDIRECT_URI, TIKTOK_TOKEN_KEY, TIKTOK_ADMIN_KEY and existing COMMENTS_DATABASE_URL/SSL. Production server functions need these environment variables; no NEXT_PUBLIC/VITE prefixes.

Official contract verified against https://business-api.tiktok.com/portal/docs/accounts-api-authentication/v1.3 . This is the Business Accounts API (`tt_user/oauth2/token/`), not the ordinary developer Content Posting token endpoint. Auth code is single use; original raw URL without server state cannot complete this new flow.

## Deployment and recovery procedure

1. Authorized Supabase administrator must execute `server/migrate-tiktok.sql` for cfskhucnihvnhcxoleaq. The existing `hoopcut_comments_runtime` role cannot create schemas. 109 helper `/Users/soda/Swi-app/hoopcut/cloud/scripts/gateway_admin.py` works after owner dashboard login. Use its existing project-scoped management request after owner login; never print session tokens. Migration completed through this authorized session.
2. Verify runtime DML on isolated tiktok_publisher schema, RLS enabled and no anon/authenticated access. Runtime cannot create schemas and must not receive database-wide privileges. Migration transaction grants only this schema's DML plus explicit RLS policies to runtime.
3. Set protected production Vercel environment from local .env using stdin and captured output; preserve existing environment. Build a production candidate without changing aliases, verify unauthenticated manage rejection, callback no-state rejection, connect page, and existing site. Promote only the tested candidate and reconcile latest main without overwriting SEO work.
4. Install tiktok-admin.py alongside protected .env, install supplied systemd service/timer. Run `list` then `refresh` (zero accounts should succeed). Enable timer only after deployed API and database work.
5. `python3 server/tiktok-admin.py invite --label GolfCut` yields a 30-minute single-use invitation. Open it in existing Mac Safari. User confirms correct TikTok account and consent. A stored encrypted account record and success callback are required before declaring connected. Repeat for HoopCut's browser. Do not log invitation URLs permanently.

Tokens are AES-256-GCM encrypted with account-specific authenticated data, never returned by management API. Keep the token encryption key securely backed up; changing it without migrating ciphertext makes stored tokens unusable. Browser-bound, hashed, one-use OAuth state expires in ten minutes. Refresh uses a transaction advisory lock and row locks, compatible with transaction pooling; transient network failures remain retryable, expired refresh tokens require renewed consent. This change does not publish videos or resume either paused collector.

Validation: 24 TikTok tests plus 11 attribution tests pass. Website build passes. Existing comments integration test requires a dedicated *_test PostgreSQL database; its guard rejected execution without that database, before any mutation. Database integration and production routing verified; real TikTok consent/token exchange still pending.
