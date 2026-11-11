# Shot Tracer isolated preview — 2026-11-11

Preview only. Do not merge/promote this branch: public processing backend is not connected.
Preserves comments, attribution and current Videos navigation; adds Shot Tracer page/navigation.
12 local API contract tests, 72-page SEO and standard build passed. One real 25.67s portrait sample freshly processed with four effects on 112 isolated Unix HTTP; not public/Safari acceptance.
CPU v1 failed because GPU-only configuration rejected CPU fallback; v2 adaptation script failed before inference. CPU v3 runs in a separate non-production copy; no final performance verdict yet.
`/api/shot-tracer/cpu-probe` runs a bounded Python smoke check only when VERCEL_ENV=preview; production returns404. It does not run inference, access storage/database, or measure full pipeline performance.
Preview must use staging attribution only; missing branch collector config remains fail-closed. No production synthetic analytics or videos are submitted for testing. No production variable changes.
Models/native dependencies are NOT bundled in this preview. Full Vercel feasibility remains unverified.

## Outbound bridge integration
Added separate Supabase-backed leased jobs/private storage and 112 outbound worker; no SSH relay. Browser uploads directly to signed storage. Preview still not approved for production: real public compute verification in progress. Seven BFF security/contract tests passed. Runtime GPU pressure no longer preempts admitted jobs.
