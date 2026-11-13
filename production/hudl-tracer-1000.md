# Hudl keyword release — 2026-11-13

The owner requested publication of 1,000 new keyword pages using the reviewed
original `/shot-tracer/{slug}` interface. This batch is `hudl-20261113-1000`.
Its manifest lists the exact 1,000 routes and preserved source estimates. The
four reviewed examples are copied into the same original renderer.

## Sources and regeneration

- `content/shot-tracer/keyword-profiles/hudl-20261113-1000-selection.json`
  preserves the selected rows, export URL, date, volume and KD; these are
  third-party estimates, not measured HoopCut traffic.
- `content/shot-tracer/keyword-profiles/hudl-20261113-1000-reviewed-samples.json`
  contains the four reviewed examples.
- `scripts/hudl_editorial.py` supplies query-modifier and source-context copy.
- `scripts/prepare_hudl_tracer_batch.py --csv /path/to/hudl-keywords-deduplicated.csv`
  regenerates exactly this first batch without treating it as pre-existing pages
  or overwriting earlier batches.
- `python3 scripts/build_shot_tracer.py` renders approved pages, directory pages
  and sitemap entries. `npm run build` includes this step for production.

The 14,863 remaining source keywords stay in the original keyword inventory.
The selection order prioritizes reviewed examples, basketball and video tasks;
it adds no minimum-volume or KD threshold. Ambiguous unrelated searches remain
queued rather than displacing clearer first-batch tasks.

## Product and editorial scope

Pages reuse the original uploader, processing script, sample player and export.
Copy distinguishes the user's own basketball footage from a searched team,
player or event. Source URL labels are navigation hints, not verified identities.
No team broadcasts, player evaluations, live scores, affiliation or support for
tracking other sports is asserted. No fictional user reviews are introduced.

## Discovery and checks

Main and topical directories are paginated at 24 cards. The main directory links
directly to every topic page so the new routes stay within three homepage clicks.
Related links stay within topic and, where available, source organization groups.
Each route has a unique title/description, one H1, H2/H3, a self canonical,
breadcrumbs, existing WebApplication schema and the central App Store URL.

Release verification covers the complete sitemap, HTML metadata, crawl graph,
shared assets, representative mobile rendering and existing uploader controls.
It does not demonstrate Google indexing, rankings, traffic growth, field Core
Web Vitals, or a new cloud processing job. Individual GSC indexing requests remain
deferred until November 14 under the owner's existing schedule.
