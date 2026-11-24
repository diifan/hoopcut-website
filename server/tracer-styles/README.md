# Shared tracer gallery, 2026-11-24

25 styles pinned from HoopCut production/tracer-styles/catalog.json (gallery-longtail-v3-20261118). Vendor renderers retained with provenance. gallery.py adapts measured observations to the original trail renderers. Website previews do not infer an impact from a track ending; no fabricated landing, made basket or distance. Swatches use an explicitly illustrative arc; MP4 examples use accepted measured basketball footage. sample-receipt.json binds each style to output SHA and source SHA.

SEO video entry remains app/render_reserve_app.py → render_gallery_styles.render. tracer_style_assignment.py uses SQLite BEGIN IMMEDIATE and a shuffle bag: 25 unique styles per cycle, no immediate repeat at cycle boundaries. Same source SHA reuses its assignment across output directories. Existing style-choice.json and published exports are preserved. The original per-output source/catalog validation remains.

scripts/build_shot_tracer.py stores page default styles in content/shot-tracer/style-assignments.json, and chooses the matching real-footage sample. Rebuilds do not redraw. Commit that JSON with a new daily batch. Daily quantity, release time and keyword pool remain unchanged. Video pages must retain the video's actual style; do not assign a different one to an already-rendered video.

app/tracer_style_report.py exports task/style/platform/page correspondence whenever daily materials are exported. Legacy unknown styles stay unknown; views/likes/comments are null until platform measurements are joined. Raw views alone do not establish a preferred effect: compare matched exposure windows/platform and engagement rates; footage differences confound interpretation.

Validation: 100 concurrent assignments, four complete non-repeating cycles, retry stability; all 25 styles rasterized with actual AceCut and GolfCut observations, 25 distinct frame hashes per app. Illustrative contact sheet in /tmp/tracer-styles-20261124/catalog.jpg. This does not claim native app modifications or universal detection accuracy.
