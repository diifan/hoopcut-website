# Tracer keyword batches

Use one shared functional tool shell. The owner has requested one independent page
per distinct keyword, including synonyms. The current local batch is
`homecourt-20261112-one-per-keyword`: 370 ranking records, 199 distinct keywords,
184 additional pages and 15 retained pages. Exact duplicate ranking records do not
create extra URLs. The previous 15-page grouped batch remains reproducible as
`homecourt-20261112`; it is no longer the requested review scope.

The owner approved all 199 pages in review version `d019251331d0` on 2026-11-12.
Their source records now carry approval metadata; the normal production build
includes these pages and nine directory pages with indexable metadata and sitemap
entries. The three unrelated older draft scenarios remain excluded. Re-importing
unchanged approved profiles preserves approval; changed copy requires a new review.

## One keyword per page

Author one content profile for every keyword without an existing primary Tracer
page. Keep the shared uploader, preview and export unchanged. Distinguish different
queries in the introduction, practical example, guide, headings and FAQs; preserve
honest product boundaries for unrelated and ambiguous terms. Those pages still
exist in this local batch and are labeled in the review inventory.

```sh
python3 scripts/prepare_tracer_keyword_pages.py --csv /path/to/source.csv --profiles content/shot-tracer/keyword-profiles/homecourt-20261112-one-per-keyword.json --batch homecourt-20261112-one-per-keyword
python3 scripts/build_shot_tracer.py --preview-batch homecourt-20261112-one-per-keyword
python3 scripts/build_tracer_batch_review.py --batch homecourt-20261112-one-per-keyword
```

This command checks complete source coverage, unique routes and metadata, keeps all
original ranking records, and does not silently merge synonyms or omit low-fit
keywords. Authored profiles are required inputs; the importer does not invent copy.
The reviewed first 15 page configurations are retained without rewriting them.

## Sources

- `content/shot-tracer/pages.json`: existing hub and original draft pages.
- `content/shot-tracer/batches/<batch>/*.json`: authored page arrays, initially `draft`.
- `content/shot-tracer/keyword-maps/<batch>.json`: one decision per unique source keyword.
- `content/shot-tracer/batch-manifests/<batch>.json`: reconciled source evidence and explicit preview selection.

The following older command reproduces the original grouped-intent batch only;
do not use it as the default for the owner's one-keyword-per-page request.

```sh
python3 scripts/prepare_tracer_keyword_batch.py --csv /path/to/source.csv --mapping content/shot-tracer/keyword-maps/homecourt-20261112.json --batch homecourt-20261112
python3 scripts/build_shot_tracer.py --preview-batch homecourt-20261112
python3 scripts/build_tracer_batch_review.py --batch homecourt-20261112
node server/tracer-keywords-preview.js
```

Review `/__review/tracer-keywords` and the actual pages linked from it. The preview
server binds to localhost and connects the existing Tracer processing service.
It is not the production API or a replacement for the upload/render code.

## Validation and release

Run the generator tests, complete resource build, production build and browser
checks appropriate to changed content. `python3 scripts/build_resources.py` and
`npm run build` intentionally exclude draft routes; rebuild the preview afterward.
The review report is under `reports/` and is not shipped.

Reconcile source rows and dates, verify independent metadata and heading hierarchy,
check related links and media, and exercise the shared UI at desktop/mobile sizes.
Do not sum overlapping keyword volumes or describe an inventory as organic growth.

Publishing requires approval of the concrete review batch. Only after approval,
complete the existing evidence/reviewer fields and mark selected pages `approved`.
Rebuild, check indexation directives and sitemap membership, then follow the existing
GitHub/Vercel release process. No push, merge, deployment or GSC submission is part
of preparing a local batch.
