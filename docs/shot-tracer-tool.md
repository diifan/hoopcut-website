# Shot Tracer runtime

Browser POST /api/shot-tracer → authenticated Supabase shot-tracer-bridge control plane. Signed uploads go directly to private storage; no video bytes through Vercel. Worker polls /api/shot-tracer/worker using independent bearer (Edge enforces), environment chosen by deployment, never browser. 112 GPU worker downloads source, runs networkless job sandbox, uploads rendered artifact, finishes lease. Production and staging have separate keys, queue and paths.

Required Vercel variable: HC_TRACER_WEB_SECRET, distinct production/preview values. Credentials are not in this repo. Runtime config private on112. Source≤512MiB, duration≤1h; processing interval≤30s, longer source requires trim. Rate/quota limits and queue handled in DB. One GPU task, pre-admission availability gate. No per-pressure preemption. Bounded1200s execution remains enforced.

Only Make/Miss and ball Tracer run. server/shot-tracer/engine.py stops native analysis before people pipeline. tracer_only.py uses actual CoreMLBallDetector ONNX CUDA with detector-confirmed observations; native polygons only seed ROIs. Confidence/trajectory/gap gates followed by no-extrapolation spline. No person/pose/ReID models, identities or ownership. Runtime cache version makemiss-tracer-v2 invalidates old people-dependent results. Rendering preserves source audio if present. Preview/export use same artifact.

Effect choices Firework, Cosmic, Ice Beam, Sunset. Locked effects have real previews but download endpoint only permits Firework. No example-video fallback. No confident measured trajectory yields no_shots.

24h signed-access TTL; periodic worker cleanup removes expired objects. If worker offline, access still expires but physical cleanup is delayed. No billing or success-rate claims. Fixed-camera portrait fixture tested; moving-camera/general accuracy not certified.

Tests: node --test tests/shot-tracer-bridge.test.mjs tests/attribution.test.js tests/attribution-delivery.test.js; npm run build; python3 scripts/check_site_seo.py. Comments integration suite requires dedicated *_test DB, never production. Production rollback target recorded in release notes.
