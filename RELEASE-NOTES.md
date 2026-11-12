# Shot Tracer web tool — 2026-11-11

User authorized direct release after verification. PR25 preserves latest main 486237b (HomeCourt tools), comments and attribution. Adds /shot-tracer and mobile/desktop navigation.

Processing: Make/Miss native scan → independent ball detector → measured spline → render. No people tracking, pose, person ReID, ownership or adaptive people rounds. CUDA checked at model execution. 112 outbound worker, Vercel control API, private Supabase storage/leased queue. No public 112 port or new relay. One compute at a time; resource admission before claim, not GPU-pressure termination.

Validation: 18 BFF/attribution tests pass; 90 sitemap pages and standard build pass. 25.64s public HTTPS staging test ready: compute73.923s, peak process GPU392MiB, preview/download SHA identical 91ed75c6d79ee2c7fe610d9d0f3ab0fc062c71bd5a562cff351b62918e354775. 31s processing request rejected400. Fresh 25.67s source scan plus ball-only tracer produces3 arcs; screenshot visually checked. First benchmark reused native output only to isolate tracer cost, not claimed end-to-end.

Source limit512MiB/1h; process limit30s; longer videos require explicit trim. Four real effects; only Firework export unlocked. Videos private with24h access expiry; physical cleanup worker-scheduled. No synthetic production analytics.

Boundaries: Vercel preview deployment has authentication protection; current HTTPS staging test directly exercises Edge/storage/112, not authenticated Vercel UI. Live browser end-to-end verification follows release. Comments destructive integration tests intentionally cannot run without dedicated *_test DB; no comments code changes. Mobile Safari device acceptance and general basketball detection accuracy are not inferred from one portrait fixture.

Rollback: previous READY production dpl_BsrUWDbvJxt5BVgWUcpHRxPfiLmp, main486237bf079db67fb39e0163a3157d5cf8d5f2a6. Restore only this website if actual release fault occurs.

## Pending selection hotfix — NOT deployed
User production clip failed before Make/Miss: old initialize_segment_scene.py rejected all clusters with No stable hoop across samples. Not upload/GPU/person analysis failure. App ImportNativeSceneReference.prepare always presents candidate confirmation, then freezes actual frame/reference; website had omitted this flow.

New candidate-v3: explicit selection even with one hoop, normalized upright boxes, next sampled frame, submit opaque candidate ID (never client-supplied geometry), reference bound to exact analysis frame, existing OriginalHoopImageTracker carries selected hoop. Native scan/MakeMiss and ball tracer preserved. Web uses existing detector/decoder candidate extraction; this is NOT a binary-identical port of the full Swift native scene-candidate controller. No moving-camera/general-accuracy parity claim.

Verified: real fixture preflight8 candidates → selected frame0 native scan →4 measured arcs; browser UI-only fixture next frame→tap→confirm submits correct ID; confirm disabled until tapped;390px viewport no horizontal overflow.18 existing bridge/attribution tests pass. Python syntax and Deno type checks pass. UI-only mock is not end-to-end inference evidence.

BLOCKED: Supabase management login expired (new actual dashboard tab Sign in, no auth storage). SQL rollback test did NOT run; Edge/migration not deployed; production worker remains v2. Do not merge this UI before new backend is tested and deployed. Production retains prior behavior until then. Download signed-attachment/direct-download change also pending; production prior blob-fetch failure not declared fixed.

### 2026-11-12 deployment continuation
Supabase login restored. Transaction-isolated selection protocol test passed and rolled back (invalid selection rejected; confirmed candidate preserved; changed trim clears candidate). Edge v2 ACTIVE and additive SQL migration deployed. Production queue verified empty before worker change; v2 Python backup retained; v3 worker active. This supersedes the management-login blocker above. Existing18 tests and90-page build/SEO passed before release. Final public browser selection→compute→export verification remains required.

## 2026-11-12 Shot Tracer: NVENC and measured progress
- Final render uses A6000 NVENC p4/cq26; unchanged analysis input and exact existing arcs. Range-identical trim shared between hoop preflight and confirmation, never between different uploaded jobs or analysis selections.
- 25.67s fixture: preflight17.66s; confirmed full-chain46.31s at cq20 versus prior70.00s. Final cq26 sandbox render4.67s,770frames,15,883,048bytes; full decode passed. Exact arcs match baseline. cq26 versus previous x264 output SSIM0.992309 (similarity, not perceptual sign-off). Synthetic landscape audio decoded hash preserved. No all-format claim.
- Upload preview retained; real upload percent, stage-local render progress, indeterminate analysis, elapsed time, accessible retry/cancel, compact hoop selection and responsive status card. No invented ETA or fake progress.
- Browser local UI mocks: upload, tracking, explicit hoop selection, ready;320/390/768/1440px no overflow or console errors. These are not GPU E2E tests. GPU isolated sandbox above is real inference.
- Bridge7 tests, trim reuse1 regression, production build and90-page SEO passed. Preserve comments, attribution and navigation. Production browser test and iOS Safari visual acceptance still separate.
- Runtime rollback: restore prior engine.py/compute.py from runtime/pull-app-v3-backup; website rollback target dpl_3GKqN8ytgJfR8c9L278yRWqUjy6h. Do not terminate an active job.

## 2026-11-12 — fused short-video probe, preview-only activation
- Accept a validated needs_hoop response directly after upload; preserve explicit user hoop selection and the existing long-video trim workflow.
- Keep old imported responses compatible. Reject a fused range that differs from the reported full short video.
- HC_TRACER_FAST_STAGING=1 selects the isolated fast-staging endpoint only outside production; production routing is unchanged.
- 14 bridge/upload-flow tests and the standard website build passed. Tests mock browser DOM/requests; this is not mobile/browser acceptance.
- Actual 112 HTTPS staging job ee37fbad67960a007d2a03fd6ab62421c384a8ad98db0750: upload-to-ready 52.249s, download complete 55.568s, exact baseline artifact SHA. Does not include Vercel BFF or human selection delay.
- Approximately 30s end-to-end target remains unmet. No claim of production performance or browser validation.
- Browser preview now actually completed the upload/explicit-selection/ready flow. Resource Timing upload start to result-video request: 63.9615s; a late DOM observer's 89.232s was corrected, not treated as processing latency.
- Next preview pins only Shot Tracer BFF functions to sin1, near the Supabase region, and adds staging-only upstream Server-Timing / region evidence. No comments/attribution function region changes. Performance benefit still to be measured; not a 30s claim.

### Early hoop choice staging UI
- Partial first-frame choices offer More frames through the existing full preflight request; no automatic hoop confirmation. Existing complete selections retain Next frame.
- 7 upload/selection and 10 bridge tests passed; build passed. Worker candidate remains isolated pending fallback/retry and browser validation; no production release claimed.

- Active upload/processing status polling waits 750 ms after each completed request (no overlapping polls); idle page does not poll. Cuts unnecessary ready/selection detection delay; still needs browser end-to-end timing.

## 2026-11-12 staging Edge region alignment
- Pin only fast staging BFF requests to ap-southeast-1, matching HoopCut database. Production route unchanged.
- Expose non-secret staging edge region for verification; 28 tracer tests passed including production isolation.
- Worker region benchmark: default us-west-1 warm 0.788/1.281s; pinned ap-southeast-1 warm 0.562/0.469s. Not an end-to-end result.

## 2026-11-12 indexed staging output
- Only server-marked mp4-faststart results load directly; legacy results retain bounded Blob loading.
- Wait for loadeddata before ready; cancellation stops pending direct media. Export still refreshes signed download URL.
- 31 tracer tests passed; worker isolated full computation produced verified indexed output with identical video/audio decoding to baseline. Full browser pipeline timing pending.

## Approved ~65-second Shot Tracer rollout
Production routes to the production-only overlap endpoint; preview stays staging-isolated. Deploy alongside the verified progressive-download worker. Real staging browser measurement: 64.853s, not an SLA. Prior production deployment retained for rollback.

## Multi-hoop selection and cancel fix
Retain detector candidates above the App candidate threshold (0.1), instead of discarding secondary hoops at 0.5. Three-hoop user fixture validated separately on GPU. Both cancel controls immediately return to upload and cancel the server job; stale callbacks cannot restore the old editor. 34 tracer tests passed.
