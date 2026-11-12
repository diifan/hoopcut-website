# Shot Tracer runtime

Browser POST /api/shot-tracer → authenticated Supabase shot-tracer-bridge control plane. Signed uploads go directly to private storage; no video bytes through Vercel. Worker polls /api/shot-tracer/worker using independent bearer (Edge enforces), environment chosen by deployment, never browser. 112 GPU worker downloads source, runs networkless job sandbox, uploads rendered artifact, finishes lease. Production and staging have separate keys, queue and paths.

Required Vercel variable: HC_TRACER_WEB_SECRET, distinct production/preview values. Credentials are not in this repo. Runtime config private on112. Source≤512MiB, duration≤1h; processing interval≤30s, longer source requires trim. Rate/quota limits and queue handled in DB. One GPU task, pre-admission availability gate. No per-pressure preemption. Bounded1200s execution remains enforced.

Only Make/Miss and ball Tracer run. server/shot-tracer/engine.py stops native analysis before people pipeline. tracer_only.py uses actual CoreMLBallDetector ONNX CUDA with detector-confirmed observations; native polygons only seed ROIs. Confidence/trajectory/gap gates followed by no-extrapolation spline. No person/pose/ReID models, identities or ownership. Runtime cache version makemiss-tracer-v2 invalidates old people-dependent results. Rendering preserves source audio if present. Preview/export use same artifact.

Effect choices Firework, Cosmic, Ice Beam, Sunset. Locked effects have real previews but download endpoint only permits Firework. No example-video fallback. No confident measured trajectory yields no_shots.

24h signed-access TTL; periodic worker cleanup removes expired objects. If worker offline, access still expires but physical cleanup is delayed. No billing or success-rate claims. Fixed-camera portrait fixture tested; moving-camera/general accuracy not certified.

Tests: node --test tests/shot-tracer-bridge.test.mjs tests/attribution.test.js tests/attribution-delivery.test.js; npm run build; python3 scripts/check_site_seo.py. Comments integration suite requires dedicated *_test DB, never production. Production rollback target recorded in release notes.

## SEO landing pages (2026-11-12)

The shared HTML source is now `content/shot-tracer/tool.html`, including the real
upload/editor DOM and existing runtime script. Edit that source rather than the
generated `shot-tracer.html`. Page-specific metadata, copy and FAQs live in
`content/shot-tracer/pages.json`; `scripts/build_shot_tracer.py` generates them.
It runs after the other page builders in both the Vercel build and the complete
resource build. The existing browser JS, API bridge and processing worker are
unchanged. Attribution is still injected by the existing distribution builder.

The root tool page is approved. Three scene entries are drafts, not deployed
routes. Approving a scene requires a distinct intent, demand evidence, a named
reviewer and an example evidence URL displayed in its `examples` list. This is an
editorial gate, not automated proof of search demand or content quality. Do not
approve synonym pages solely to increase the URL count. Real case studies should
continue to use the existing `/videos` editorial workflow.

Approved scene URLs use `/shot-tracer/{slug}`. The `scenarios` slug is reserved:
it provides a crawlable directory, 24 entries per page, with self-canonical
pagination and previous/next links. Each tool page links to this directory when
scenes exist, and to at most three other scenes. Directory pages do not load the
upload runtime. Only approved pages and their directory pages are added to the
existing sitemap; unrelated URLs and their lastmod values are preserved. This
generator owns HTML beneath `/shot-tracer/` and removes obsolete generated routes
when an entry returns to draft. Do not place hand-maintained pages there.

Tools, the original demo and the existing tutorial gain contextual links to the
upload tool. The standalone Tools/blog builders preserve those additions; the
tracer build also applies them idempotently. Original demo/tutorial URLs retain
their own canonicals and purpose. No client-only SEO content, invented ratings or
FAQ rich-result promises are introduced. Copy distinguishes a visual trail from
calibrated shooting analysis and accurately describes access expiry versus cleanup.

Validation commands:

```sh
python3 -m unittest discover -s tests -p 'test_shot_tracer_seo.py'
node --test tests/shot-tracer-*.test.mjs tests/attribution.test.js tests/attribution-delivery.test.js
npm run build
python3 scripts/check_site_seo.py
python3 scripts/preview_site.py --port 8794
node scripts/qa_shot_tracer_seo.cjs
```

The synthetic scale test builds 1,000 approved fixture scenes, checks every route
is reachable via the paginated directory and verifies withdrawal removes stale
HTML/sitemap entries. It does not publish them or validate real keyword demand.
Browser QA checks the actual runtime initialization, file picker, FAQ, schemas,
mobile/desktop layout, inbound links and invalid-slug 404. Local static preview has
no processing API; these checks do not claim a production GPU end-to-end run,
Core Web Vitals improvement or ranking gains. Monitor successful uploads, previews,
exports and repeat use separately from queue/render wait time after deployment.
