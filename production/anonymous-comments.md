# Anonymous watch-page comments · local review

The existing static video page now mounts a YouTube-style comment section: anonymous
composer, optional public name, top/newest ordering, replies, expand/collapse, likes,
dislikes and pagination. No account, CAPTCHA, moderation queue, approval state,
keyword filter or AI review is implemented. A successful submission is immediately
visible to other visitors of the same service.

## Run the real local service

```sh
python3 -B scripts/preview_comments.py --port 8769 --examples
```

Open `http://127.0.0.1:8769/videos/two-pickup-jump-shots-shot-tracer#comments-title`.
Comments persist in `reports/comments-preview.sqlite3` on disk, shared between local
browser sessions. This is not a browser-only localStorage comment list. A random
HttpOnly cookie identifies an anonymous visitor for reactions. localStorage stores
only the optional nickname preference. No email address or real name is required.

`--examples` loads five **explicitly fictional** layout samples, marked Example in
each row and in the local banner. They are restricted to local SQLite and never
seeded by the production API. Omit `--examples` with a fresh `--database /path/file`
to review the honest empty state. Example JSON and local databases are excluded from
Vercel deployment. The preview blocks source and database downloads.

## Production storage is not yet configured

The current live website has no comments database. This batch adds a real API at
`/api/comments` and a Postgres adapter, but it has **not** created a hosted database,
configured production credentials, uploaded examples or deployed any changes.

Vercel needs an actual shared Postgres connection in the server-only environment
variable `COMMENTS_DATABASE_URL` before public comments can work. Never put this
value in site config, HTML, browser code or chat. An existing database can be reused;
no paid service or new account has been enabled here. The adapter uses psycopg 3
from `requirements.txt`. Runtime DDL creates `hc_visitors`, `hc_comments`, `hc_votes`
and their indexes using the configured database role; alternatively run the statements
in `api/comments.py` beforehand using the project's normal migration process.

SQLite is supported for a persistent self-hosted service. It is explicitly rejected
on Vercel because serverless temporary disk cannot provide durable shared comments.
Without configured persistent storage the API returns 503, and the UI shows an
error/retry state. It never reports a fake successful submission or falls back to
private browser-only comments. Real Postgres integration remains unverified until
an approved database is configured.

## Data and technical behavior

- Public data: optional name, comment text, date, thread and reaction counts.
- Private data: random visitor token hash and reaction association. Raw tokens are
  HttpOnly, SameSite cookies and never exposed in API lists. No IP/user-agent fields
  are recorded in these tables.
- POST bodies use JSON with same-origin checks. Length/type validation and HTML
  escaping are technical protections, not content moderation.
- Text is inserted using textContent/DOM nodes, never as user-supplied HTML. URLs
  use `rel="ugc nofollow noopener"`. API responses are no-store/noindex.
- Idempotency keys prevent duplicate submissions when retrying the same post.
- Anonymous reactions are one active vote per cookie identity. Anonymous cookies
  do not establish a verified person's identity or prevent a person from clearing
  cookies and obtaining another pseudonym.
- No user comment is fabricated as SEO review markup. Existing video canonical,
  VideoObject, title, description and sitemap URLs remain unchanged.

## Build and verify

```sh
python3 scripts/build_resources.py
python3 -B scripts/test_comments.py
node scripts/qa_comments.cjs
python3 scripts/check_site_seo.py
```

The complete build regenerates the preferred watch URL and existing YouTube-ID
alias with the same video ID/comment thread. New CSS/JS are fingerprinted under
`assets/static/`. The backend allowlist `api/video-ids.json` is generated from the
verified video manifest. No editorial upload receipts are needed in the deployed
API. `vercel.json` includes that allowlist in the Python function bundle.

Browser QA uses two isolated anonymous contexts, a temporary SQLite service on an
OS-assigned loopback port, and no live-site writes. Screenshots show only the marked
local samples. Verify the actual production database and upload/deploy the reviewed
batch only after user approval; a local SQLite test is not a production acceptance test.
