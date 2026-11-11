# Shot Tracer web tool — 2026-11-11

User authorized direct release after verification. PR25 preserves latest main 486237b (HomeCourt tools), comments and attribution. Adds /shot-tracer and mobile/desktop navigation.

Processing: Make/Miss native scan → independent ball detector → measured spline → render. No people tracking, pose, person ReID, ownership or adaptive people rounds. CUDA checked at model execution. 112 outbound worker, Vercel control API, private Supabase storage/leased queue. No public 112 port or new relay. One compute at a time; resource admission before claim, not GPU-pressure termination.

Validation: 18 BFF/attribution tests pass; 90 sitemap pages and standard build pass. 25.64s public HTTPS staging test ready: compute73.923s, peak process GPU392MiB, preview/download SHA identical 91ed75c6d79ee2c7fe610d9d0f3ab0fc062c71bd5a562cff351b62918e354775. 31s processing request rejected400. Fresh 25.67s source scan plus ball-only tracer produces3 arcs; screenshot visually checked. First benchmark reused native output only to isolate tracer cost, not claimed end-to-end.

Source limit512MiB/1h; process limit30s; longer videos require explicit trim. Four real effects; only Firework export unlocked. Videos private with24h access expiry; physical cleanup worker-scheduled. No synthetic production analytics.

Boundaries: Vercel preview deployment has authentication protection; current HTTPS staging test directly exercises Edge/storage/112, not authenticated Vercel UI. Live browser end-to-end verification follows release. Comments destructive integration tests intentionally cannot run without dedicated *_test DB; no comments code changes. Mobile Safari device acceptance and general basketball detection accuracy are not inferred from one portrait fixture.

Rollback: previous READY production dpl_BsrUWDbvJxt5BVgWUcpHRxPfiLmp, main486237bf079db67fb39e0163a3157d5cf8d5f2a6. Restore only this website if actual release fault occurs.
