# Website attribution v1 — implementation receipt

Latest 2026-11-10: real OneLink Smart Script and staging BFF→Supabase persistence verified. The standard build includes the verified public template by default. See WEB-INTEGRATION-RECEIPT.md for current evidence and remaining public deployment checks.

Source contract: attachment om_x100b6023ab64d890cfbe01eb9ba442a/README.md, 2026-11-09.
Website implementation only; no App, AF account, database or production changes.

## Deploy configuration (server-owned)
- VERCEL_ENV selects production only when exactly production; otherwise staging. URL parameters cannot select it.
- HOOPCUT_ANALYTICS_ORIGINS: exact allowed origins for this deployment. Production: https://hoopcut.ai,https://www.hoopcut.ai. Preview origin must be listed explicitly in staging.
- HOOPCUT_ANALYTICS_SECRET and HOOPCUT_ANALYTICS_SECRET_HEADER: receiver team's independent environment-specific credential and x-* header. Both are server-only. No defaults, no anon token or App RPC reuse.
- HOOPCUT_ANALYTICS_RATE_SECRET: server-only HMAC key for short-lived in-memory throttling. This is not an identity or JOIN key. Vercel trusted forwarding header only; no raw IP forwarded or logged by this code.
- HOOPCUT_ONELINK_BASE_URL and HOOPCUT_ONELINK_ALLOWED_HOSTS: verified template URL and hostname allowlist, supplied by AF owner, never guessed.
- HOOPCUT_SMART_SCRIPT_SRC: verified AppsFlyer hosted SDK URL. No SDK/invalid SDK result => App Store fallback. No navigation delay.
- HOOPCUT_ANALYTICS_PERSISTENT_STORAGE defaults off. Only set to allowed where storage permission is established; otherwise session-only; disabled storage uses memory. No consent UI is invented here.

Build injects the script, safe public configuration, stable CTA IDs and YouTube API flags into all built public HTML. Source generators remain compatible because this is the final standard build step. No-script href remains the exact Apple ID fallback.

## Contract additions for existing positions
- article_download: existing editorial article product CTA.
- resource_download: existing tool/demo/resource-body CTA.
Other positions retain header_download / hero_download / video_detail_download / footer_download / mobile_sticky_download. Current layout has no mobile sticky download control; do not invent one.

## Transport boundary
Only receiver-confirmed persisted IDs are returned accepted. A 503 when receiver config is absent is intentional, not an accepted event. Client retries reuse event IDs, bounded to 24h/100 events, max20/32KiB per batch. 400/413 drop that batch, 429 respects Retry-After, network/5xx use backoff. Multiple tabs may resend the same IDs: upstream durable uniqueness is required.
Rate limiting here is per server instance (120 events/minute/address HMAC); cross-instance abuse protection and durable dedup must also be verified at ingress/receiver before production. Receiver owns received_at, clock_skew, environment-specific secret enforcement, RLS and durable uniqueness. Website does not fabricate these guarantees.

## Outstanding integration
Receiver is ACTIVE. Real SDK 2.10.4, four staging events and fallback verified. Vercel management access currently returns 403, preventing server environment configuration and public BFF acceptance tests. Real YouTube playback and one video_play event verified with the local built page and live YouTube network. Production release and AF installation verification are not claimed.

### 109 原项目实查更正（2026-11-09）
已直接 SSH 检查 /Users/soda/Swi-app/hoopcut。确认可复用项目 cfskhucnihvnhcxoleaq，现有 record_analytics RPC 强制 authenticated/auth.uid；不是官网匿名接收端。cloud/supabase/functions 现有 apple-attribution、people-gateway；web-attribution-events 仅出现在双方协议，没有源码。对约定接收地址发送空事件列表实测 HTTP404 NOT_FOUND（未产生事件）。找到既有 cloud/scripts/gateway_admin.py 管理工具，但实调未取得当前 HoopCut dashboard 登录 token，不能据此声称具备部署权限。未修改 App/数据库/认证配置。阻塞精确为：新官网接收函数未部署，现有管理入口当前无可用登录态；不是缺少 Supabase 项目地址。证据：website-attribution/docs/evidence/supabase-109-check.json。
