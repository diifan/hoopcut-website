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
