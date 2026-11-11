# Court tools: local review version

Two browser tools, separate from the iPhone app:

- `/tools/basketball-court-diagram`: NBA/FIBA, full/half court, markers, movement
  arrows, drag, erase, undo, local draft, SVG/PNG/print.
- `/tools/basketball-shot-chart`: manual make/miss locations, two/three-point
  estimates, FG and six planning-zone summaries, correction, undo, local draft,
  SVG/PNG/CSV/print. Up to 500 entries; recent 12 shown in the editable log.

Use `npm run build` for the actual Vercel static output, then:

```sh
python3 -B scripts/preview_court_tools.py --port 8772
```

Open `http://127.0.0.1:8772/tools/basketball-court-diagram` or
`http://127.0.0.1:8772/tools/basketball-shot-chart`.

The preview serves `dist` with clean URLs and HTTP `noindex, nofollow`. The
production HTML has its own canonical URL and no local-preview indexing rule.
The standard build generates both pages, graphics, homepage/Tools entries and
sitemap entries. Existing public pages and the owner's homepage reviews remain.

Sources: `scripts/build_court_tools.py`, `assets/court/geometry.js`,
`assets/court/studio.js`, `assets/court/studio.css`, and
`scripts/build_court_media.cjs`. The legacy resources builder also invokes the
court-tools builder. Browser acceptance: `node scripts/qa_court_tools.cjs`.

Court geometry is a simplified reference layout, not a construction drawing.
Shot locations are manual estimates, not computer-vision or calibrated tracking.
The selected reference controls two/three-point classification; changing it
rescales existing locations. Demo shots retain their example labels, including
in mixed-session CSV exports. These are not player results.

Current drafts use separate versioned localStorage keys. No shot cloud database
or video upload is involved. The existing optional `hoopcutTrack` hooks receive
code-owned tool/action identifiers only; titles and shot coordinates are never
event payloads. Analytics enablement and existing App Store attribution settings
are preserved. No claims of measured traffic or engagement improvement.

Only local review is authorized. Do not push, merge, deploy, or submit these
new URLs to GSC until the owner approves the concrete version.
