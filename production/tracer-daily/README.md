# HoopCut daily Tracer preparation

Entry: `python3 /data/swi-algo/Swi-App-Factory/Hoopcut/production/tracer-daily/prepare.py`

Required flags: `--day YYYY-MM-DD --pool CSV --source-manifest JSON --receipt PATH`; optional `--target 2000`.

Example:

```bash
python3 /data/swi-algo/Swi-App-Factory/Hoopcut/production/tracer-daily/prepare.py \
  --day 2026-11-20 \
  --pool /var/lib/swi-codex/xcut-seo-agent/data/tracer-keywords-199/keywords.csv \
  --source-manifest /var/lib/swi-codex/xcut-seo-agent/data/tracer-keywords-199/manifest.json \
  --receipt /data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily/2026-11-20-receipt.json \
  --target 2000
```

The date is an input, not a coded batch constant. `config.json` locates the registered repository, project, CLI and task-only proxy. Keep this entry directory persistent. The code is also copied into each prepared commit; the execution-machine config/cache/state remain here.

The latest pool must match `source-manifest.sha256`. Every `sources[].local_path` CSV must match its declared SHA. Existing cached source probes are reused; absence of evidence is counted as unresolved, not as an unrelated keyword. Explicit unrelated intent exclusions and full keyword identity alignment are inherited from the current main policy. No requirement for the literal word basketball in the source.

A global file lock serializes selection/reservation and deployment. Independent processes assemble three mutually exclusive shards; only the parent writes pages/manifest/receipt. Reserved keywords/URLs from other daily batches and local website worktrees are excluded. A durable reservation precedes generation. No partial batch is uploaded. Insufficient coverage returns exit 2 with eligible_count and shortfall.

Runs use a new worktree from origin/main and local preparation commit. Unrelated generated changes are preserved as an audit patch and excluded. Main is fetched again before upload; a changed base prevents readiness. Rerun then builds a fresh worktree from the new base, retaining old work and reservations. No push, merge or live-domain assignment occurs.

Upload uses only `vercel deploy --prod --skip-domain` for the registered project. A deployment is ready for promotion only after production/READY/project checks and proof that both live domain deployment IDs remain unchanged. Uncertain previous uploads are reconciled by swieBatch/swieCommit metadata before another upload. `published` stays false. The controller must enforce `promotion_not_before`, verify the prepared commit/base against current main (no stale rollback), and promote the deployment at 12:30 Asia/Shanghai. Preparation does not schedule or message anyone.

Rerunning a ready batch verifies its existing deployment and manifests and does not re-upload. The controller owns eventual main reconciliation and `published=true` after promotion/live verification. Future preparations must use a main baseline containing earlier promoted content; reserved words alone cannot preserve pages missing from main.

Receipt includes required deployment identifiers, pool SHA, all batch URLs, checks and three worker counts. `next_day_pool_warning.required` indicates that the remaining eligible pool cannot cover another full batch; the controller owns the SEO-Agent group mention to Cao Shiyu. Counts reflect current cached eligibility; unresolved rows are listed separately and must not be described as permanently unsuitable.

Tests: `python3 production/tracer-daily/test_prepare.py` from the HoopCut workspace. Logs, source snapshot and shard manifests are retained under `runs/<day>/`.

After the controller has promoted and verified the deployment, set its receipt `published=true`, then invoke:

```bash
python3 /data/swi-algo/Swi-App-Factory/Hoopcut/production/tracer-daily/finalize.py \
 --receipt /data/swi-algo/Swi-IP-Config/swie-app-mac/data/tracer-daily/2026-11-20-receipt.json \
 --confirm-promoted
```

This is not run during preparation. It checks both domain deployment IDs and swieBatch/swieCommit, verifies the pages hash, then fast-forwards main to the exact prepared commit without force. If main advanced it refuses to overwrite concurrent edits. This command does not promote or assign domains. Git auto-deployment may rebuild the same committed content after finalization. Do not start the next day's base from main until this reconciliation is complete.
