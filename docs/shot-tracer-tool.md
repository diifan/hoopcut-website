# Shot Tracer tool — implementation in progress

Requested: user-uploaded video, automatic tracing for <=30s, explicit <=30s trim for longer videos, free orange Firework, locked-effect previews, one contextual export/app action, real source export, download/share/app follow-up. Never use a sample export as a user's result.

## Source / run
- `shot-tracer.html`, `assets/shot-tracer-tool.{css,js}`: frontend draft. Standard `npm run build` copies this page to `dist/shot-tracer.html`.
- `server/shot-tracer/service.py`: FastAPI upload/job/status/media API on 112; one inference worker, bounded queue/upload/disk usage, capability job IDs, same-origin mutation guard, retention cleanup, retry after failure/restart.
- `server/shot-tracer/engine.py`: FFmpeg trims the submitted file, invokes the existing 112 detector and measured-arc fitter on fresh video, renders deterministic effects on the entire selected range, preserves audio. Browser previews the rendered MP4; export returns the same file. No Mac rendering or example video fallback.
- `/data/envs/torch-cu130/bin/python -m uvicorn service:app --app-dir server/shot-tracer --uds /tmp/hoopcut-web-tracer.sock`
- Private temporary media: `/var/lib/swi-codex/xcut-seo-agent/data/web-shot-tracer`. No user video enters Git or static build.

This GPU worker cannot run inside Vercel's static build. Production requires a reviewed 112 ingress or same-origin media gateway with request streaming, TLS, shared/persistent rate limits and worker supervision. It has not been published or wired into the public website. Locked previews are publicly decodable video to their capability holder; UI gating is not DRM. The explicit download endpoint only permits Firework.

## Supplied prototype (resolved 2026-11-11)
User supplied https://hoopcut-shot-tracer-preview.violettefairy0729.chatgpt.site/ . Its HTML and v6 stylesheet were successfully fetched. This supersedes the inaccessible localhost prototype.

The local implementation now follows its centered import surface, quiet dark palette, desktop player/effects columns, mobile stack, four circular preset swatches, and Import/Trace/Share steps. Firework is free; Cosmic, Ice Beam and Sunset are preview-only. Production code uses the existing real upload/tracking/rendering API, not the prototype's simulated canvas or sample export. Header/repeated app links were omitted according to the user's single-contextual-CTA requirement. Data retention disclosure and real error/progress controls remain. Drag/drop and replay are connected. New Cosmic/Sunset renderers use measured trajectories; this is not a claim of App effect pixel parity.

`reports/prototype-layout.json` covers 320/390/768/1440 import/editor layouts with no overflow or JS errors. `reports/prototype-interactions.json` records eight UI checks with an explicitly mocked API (not tracking validation). Existing eight backend tests and 71-page SEO validation pass. Screenshot files are `reports/prototype-{import,editor}-{width}.png`.

## Validation (honest scope)
- Full production build and existing 71-page SEO check pass; tool remains noindex and absent from sitemap until approved release.
- Eight isolated API contract tests pass: invalid upload, 30s bounds, effect allowlist, duplicate job dispatch, locked download denial, identical preview/export bytes, cross-origin rejection, internal paths not exposed. These contract tests mock job dispatch; they are not evidence of successful tracking.
- Browser import screen checked at 320/390/768/1440 without horizontal overflow (`reports/tool-browser.json`).
- Fresh real source `t2Pk-WvyQ20`: first 12s returns zero makes. Full24s detects a make but has only one reverse observation and no measured rise; fitter returns no usable arc. No fake fallback emitted. Logs live in `data/web-shot-tracer-validation[-full]/` in the agent workspace.
- Second fresh original `k6AbUcO4fys` passed: three measured arcs (8/6/14 observations), 770-frame / 25.666667s Firework render inspected. Browser then uploaded the original anew through the actual HTTP API (Unix transport), ran fresh inference, played the result and downloaded it. Preview/export SHA256 matched: `d3e1117bb3332b95f57a21a647ad6d265229a451519746c9fd06dbaca247320b`. Locked Ice preview rendered from the same evidence, with only the unlock CTA. Evidence: `reports/tool-e2e.json`, `tool-ready-390.png`, `firework-measured-review.jpg`. This is one positive clip, not general detector accuracy acceptance.
- A 51.333659s input requires trim in the browser; 31s is rejected, the selected 5–35s interval renders to exactly30s. Invalid media and retry were tested against the real API: `trim-boundaries.json`, `tool-ui-boundaries.json`.
- API/browser transport is real HTTP over the local Unix socket. Direct LAN port8791 could not be verified (timeout), so no publicly accessible tool URL is claimed.

## Remaining acceptance
Expand representative clip/negative-case and Safari tests; validate the effects with the owner; verify audio playback on target browsers; provide reachable review service; then obtain release approval. Inference model scope is fixed-camera half-court research pipeline with explicit upstream limitations, not arbitrary basketball-footage accuracy.

2026-11-11 new effect check: Cosmic and Sunset each rendered 770 frames / 25.666667 seconds from an existing actual uploaded clip and its measured arcs. Receipts: `reports/prototype-effects.json`. This checks rendering only, not fresh tracking.
