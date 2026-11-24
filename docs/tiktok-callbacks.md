# TikTok developer registration callbacks

- Advertiser redirect URL: https://hoopcut.ai/auth/tiktok/advertiser/callback
- TikTok account holder redirect URL: https://hoopcut.ai/auth/tiktok/account/callback

Both are unlinked, noindex, no-store server-rendered endpoints, without analytics or external resources. No parameters are reflected or persisted. The response immediately removes the query/fragment from browser history. Normal registration checks return 200; provider cancellation returns 400; a code returns 503 until integration is configured, never a false connection success.

These URLs are ready for developer application registration. Token exchange, authenticated authorization initiation, CSRF state verification, encrypted token storage and account binding still require the approved TikTok App ID/Secret and the appropriate Accounts API authorization configuration. Do not put credentials in Git or browser JavaScript. Start a fresh authorization after integration is configured; registration-stage codes are not stored or reused.

Deploy from current main; preserve all existing SEO content. Future prepared SEO deployments must incorporate this commit before promotion.
