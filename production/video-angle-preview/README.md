# Ten video-page local review candidates

This branch contains ten editorial pages around **one** verified basketball video,
not ten recordings. It builds on `codex/video-page-v1-2026-11-05`.

## Reproduce the reviewed preview

From the repository root:

```sh
python3 -B scripts/build_video_angles.py --serve --port 8771
```

Open `http://127.0.0.1:8771/videos`. The preview generator creates its isolated
site and local comments database under ignored `reports/video-angles/`.
It leaves the main video manifest, production sitemap and production database alone.
Use a different free port if 8771 is occupied. The included browser QA script
uses port 8771 and the original developer's local Chrome/Playwright installation.

## Contents

- `scripts/video_angle_content.py`: individually authored copy, questions, worksheets
  and explicitly fictional example comments for all ten pages.
- `scripts/build_video_angles.py`: isolated builder and loopback-only preview server.
- `scripts/qa_video_angles.cjs`: desktop/mobile and comment-thread integration checks.
- `production/video-angle-preview/site/`: exact HTML and CSV snapshots from the
  reviewed local build. These HTML snapshots use root-relative shared assets;
  run the preview command above to view the complete working site.
- The three JSON reports record the prior local static/browser checks and inventory.
  They are local evidence, not a GitHub CI run or a production acceptance result.

## Publishing boundary

This is a review branch only. No merge or production release is authorized.
`production/` and `reports/` are excluded by `.vercelignore`.
The candidate pages are not added to the production builder or production sitemap.
The local server disallows indexing. The standard build continues to produce the
existing site; publishing these candidates requires a separate reviewed integration.

Each page has a distinct title, description, text, FAQ, worksheet and comment thread.
VideoObject facts retain the same underlying video identity. Thirty fictional
comments are labelled **Example**, seeded only in the local preview. No comment
database, visitor records, cookies or credentials are included in this branch.
Production anonymous comments still require separately configured persistent storage.
