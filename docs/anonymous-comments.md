# Anonymous video comments

Same-origin `/api/comments` persists comments in PostgreSQL. Video ID is the thread key, so the title URL and preserved ID URL share comments. Visitors need no login. Posts appear immediately; reports do not hide content. Browser-held random IDs support deletion of one's own comments. Database-backed per-client and hashed-IP limits, length checks, parameterized SQL, same-origin mutation checks and text-only rendering are enforced. Changing browsers creates a different anonymous identity.

## Deployment

Install the locked dependencies with `npm ci` first. The image build dependency `sharp` is declared explicitly; no private machine cache is required. Vercel installCommand is explicitly set because the existing static deployment may have an empty install-command override.

The existing full resources build remains the authoring pipeline. Run `python3 scripts/build_resources.py` and its resource/SEO checks first. `npm run build` then copies only public assets into `dist`; Vercel bundles `/api/comments` separately.

Production reuses the existing HoopCut Supabase project in the isolated `hoopcut_website` schema. The `hoopcut_comments_runtime` role has only comment-table access; the App administrator password stays on the native host and is never deployed. Configure these **server-side** environment variables in the HoopCut Vercel project:

- `COMMENTS_DATABASE_URL`: TLS session-pooler URL for the restricted comment role (never exposed in HTML).
- `COMMENTS_DATABASE_SCHEMA`: `hoopcut_website` in production; defaults to `public` for isolated local test databases.
- `COMMENTS_DATABASE_SSL`: `true` in production, enables certificate and hostname verification using the bundled Supabase CA. Do not append conflicting `sslmode` parameters to the URL.
- `COMMENTS_HASH_SECRET`: at least 32 random characters; keep stable to preserve anonymous identity ownership.
- `COMMENTS_ADMIN_TOKEN`: at least 32 random characters for post-publication report handling.
- `COMMENTS_ALLOWED_ORIGINS`: defaults to `https://hoopcut.ai,https://www.hoopcut.ai`. Add an exact preview origin for preview deployments if needed.

Provision the isolated schema using the database administrator, then run `npm run migrate:comments` using that migration role; give the runtime role SELECT/INSERT/UPDATE/DELETE on the five hc_comment tables and sequence usage for hc_comment_actions. The migration is idempotent and does not modify other tables. Keep credentials out of Git. Vercel functions must use external durable PostgreSQL, not temporary filesystem storage.

`/comment-admin` is an unindexed management shell. Loading reports or deleting others' comments requires the secret administrator token, held only in memory until the tab closes. This is post-publication handling, not pre-publication approval. No fabricated comments or counters are seeded in production.

## Review and verification

Run `npm run test:comments` only against a **dedicated test database**: the suite clears the hc_comment test tables. Never point tests at production. Browser tests cover anonymous posting, another visitor's view, replies, reporting, unsafe text rendering, mobile overflow, and input retention on errors. Store test evidence outside the public site.

The local review service uses the same API handler, schema and PostgreSQL adapter as production. It sets noindex and keeps test data separate. Its database and secret configuration live outside the repository.

## Rollback

Roll back the frontend/API deployment through the existing Git release process. Keep the database intact; rolling back must not delete real comments. Deletion removes body text and preserves a tombstone for replies. Reports and deletion audit metadata remain for operator handling. Apply a retention policy before prolonged public operation.

## Verified review state (2026-11-05)

- Continued in the original HoopCut website conversation; no other app is modified.
- Current production base: `ac63d6dcb0180cf58fde5d3564695b802212e522`.
- PostgreSQL tests: 9 passed against the dedicated test database.
- Browser tests: 12 checks passed against the real HTTP API backed by a separate test database, including the collapsed-thread reply regression. Browser network requests were bridged through a Unix socket; the external YouTube iframe was excluded from these comment tests.
- Full resources build, blog/resources/SEO checks, static build and whitespace checks passed.
- Review page and its comments API return HTTP 200; review database was empty at verification. Test fixture content was removed only from the separate test database.
- Initial production release: PR #17, commit `c4a08315f79fd30ff150f2fe1d48269ca48475a4`, verified live. The video-page integration extends that API without replacing existing comment records.
- Production database migration verified: five isolated tables with RLS, no runtime read/write access to the ten existing App tables, verified TLS and restricted-role login. The production comment database is initially empty.
- Vercel CLI refreshed its expired authentication successfully. Management access and the GitHub main deployment link were verified; all five server-only comments environment variables are configured for production.
- Public certificate source: the Supabase Studio official `ssl:certificate_url` configuration points to https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt .
- Release authorization: the owner explicitly requested continuation through the existing Git release workflow on 2026-11-05. Deployment status is recorded separately after live verification.
- Local review: http://192.168.0.112:8190/reviews/hoopcut-comments/videos/two-pickup-jump-shots-shot-tracer

## Video-page integration

Optional display names (40 characters), persistent reactions and top sorting use the same visitor identity. The additive migration adds `display_name` and `hc_comment_votes`; grant the runtime role table access and add the same runtime-only RLS policy. No existing comment is deleted.

Run `python3 scripts/qa_comments.py` with a dedicated `_test` COMMENTS_DATABASE_URL plus the hash/admin test configuration and Playwright installed. `PLAYWRIGHT_CHROMIUM_EXECUTABLE` optionally selects a browser; `COMMENTS_TEST_OUTPUT` selects the evidence directory. This test clears only the explicitly selected test database.
