# HomeCourt organic content family

Local review batch: **HC-HOMECOURT-2026-11-11-01**. No push, remote PR, merge, deployment or GSC submission is authorized by implementation approval.

## Source of truth and expansion

- `content/homecourt/pages.json`: independent intent records, candidate query aliases, authored answers, sections, checklists, choices, official references and related URLs. Public research is not measured search volume; volume/KD stay null.
- `content/homecourt/existing-pages.json`: twelve contextual additions. Primary titles, primary content and original homepage reviews remain intact.
- `content/homecourt/growth-plan.json`: query/page cohorts, missing baseline, post-release observation and decisions. No scheduler is changed by this batch.
- `scripts/build_homecourt.py`: static English HTML, Article/CollectionPage/Breadcrumb/ItemList schema, unique metadata, sitemap entries, idempotent contextual injection and private review output.
- `assets/homecourt/homecourt.js`: native disclosure routing, hub search/filter, per-page checklist storage/download and a user-input cost calculator. No upload, account access or real diagnosis.
- `scripts/build_homecourt_media.cjs`: original SVG diagrams and social PNGs. They are illustrations, never HomeCourt screenshots or real player results.

Add a record only for an independently useful question. Near-synonyms belong in its `keywords` list. Prefer a relevant existing canonical page if it already answers the question. Update `related` edges together; the generator checks references. Publish no fabricated comparisons, customer ratings, discontinued-product claims or API integrations. Cite the primary source and keep source review dates distinct from app testing.

## Build and review

```sh
python3 scripts/build_resources.py
npm run build
python3 scripts/check_site_seo.py
python3 scripts/preview_homecourt.py --port 8773
node scripts/qa_homecourt.cjs
```

The Python complete build regenerates the legacy resources, court tools and HomeCourt family. The production Node build runs the court, video and HomeCourt builders and copies public files to `dist`. Reports, sources, credentials and server code are excluded from the static output. Local preview serves `dist` with `X-Robots-Tag: noindex, nofollow`; `/__review/homecourt` is a local-only report route, not a production page.

The preview also includes the previous pending court-tool version, copied into this isolated worktree. It does not alter that worktree or approve its release separately. The final batch inventory must state that dependency before approval.

## Checks and limitations

Use the recorded browser report for tests actually executed. The checklist is stored only on the current device when localStorage is available. Private mode/storage denial falls back to page-only state. The downloaded worksheet contains user-ticked checklist statuses, not verified workout outcomes. Cost inputs are never sent to telemetry. Existing analytics remain disabled; hooks being prepared is not proof of collected engagement data. App Store attribution remains the existing build's responsibility.

Public HomeCourt help articles include 2022 instructions. Existing menus and permissions were not tested in a logged-in account. The US App Store public listing reviewed November 11, 2026 shows Monthly $7.99 and Yearly $69.99; checkout/region-specific terms still need confirmation by the purchaser. The Android page does not claim Hoopcut provides an Android app. The video guide describes a file handoff, not HomeCourt account synchronization.

## Growth measurement

Do not infer current traffic from this build. The first-party indexing snapshot available from November 11 covered the previous 71 production URLs: 12 indexed / 59 not indexed, with individual inspection times retained outside this repo. This is not the status of the new local pages and is not a GSC Performance baseline.

After approval and production verification, record the real release time; inspect matched, completed US Web Search windows and report query/page cohorts separately. Store unresolved or anonymized query attribution explicitly. Preserve the current scheduled workflow; do not invent a new timer or send messages to a group from this build.
