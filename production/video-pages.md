# Hoopcut video-page standard

Owner instruction, 2026-11-05: future `/videos/{slug}` pages follow the reviewed
pickup-jump-shot page. `/videos` itself remains the video catalogue. This standard
does not authorize automatic publishing.

## Shared layout

1. Breadcrumbs and the actual video player as the main content.
2. One factual H1, concise introduction, play details, original-source attribution,
   and App Store / YouTube links.
3. Anonymous comments: optional nickname, immediate posting without review,
   replies, reactions and sorting. Production requires shared persistent storage.
   Fictional sample comments remain labelled local fixtures.
4. Static, individually authored context below comments: observations from this
   clip, relevant Tracer/editing notes, useful questions and contextual links.
   Include a jump link from the short play notes and section-anchor navigation.
5. Related published videos and relevant existing guides, demos and tools.

## Player and visuals

- Record the actual `display_aspect_ratio` explicitly in the video manifest.
  Current layouts support `9:16` and `16:9`; validate other formats before use.
- Portrait video is centred on a transparent desktop stage, so its side space
  matches the page background. Small screens use the portrait layout.
- Preserve the complete picture, native YouTube controls and branding. Do not
  crop the iframe or cover controls to disguise its background.
- Reuse the reviewed dark theme, typography, comment and video-context components.

## Unique content and SEO

- Every video needs its own matching `content/videos/editorial/{slug}.json`.
  Complete missing context before building. Never reuse another clip's story or
  fill pages with generic paragraphs just to reach a word count.
- Describe only observed or verified details. Do not invent players, matches,
  scores, timestamps, measurements, quotations, feedback or product features.
- Cover related search terms naturally. The current example has about 660 words;
  this is a reference, not a mandatory count or keyword-density threshold.
- Use a clear title and description, one H1, logical headings, descriptive links,
  visible attribution and real section anchors. Link to full guides instead of
  duplicating them. Render the useful text into initial HTML.
- Preserve the preferred title URL/canonical, factual VideoObject and breadcrumbs.
  ID aliases canonicalize to the preferred URL and share one comment thread.
- Sitemap only the preferred URLs; update modification dates for actual material
  changes. Do not fabricate review markup, indexing or traffic results.

## Build and release

Use `python3 scripts/build_resources.py`. The shared builder requires verified
video metadata, an explicit supported aspect ratio and matching editorial context.
It must not silently publish a thin page when context is missing.

Check static SEO, internal links, player geometry, mobile layout, comments and
production storage as relevant. Show the concrete local version first; owner
approval is required before pushing, merging or deploying a new version.

Sources of truth: `content/videos/manifest.json`, `content/videos/editorial/`,
`scripts/build_videos.py`, `scripts/video_layout.py`, `scripts/video_editorial.py`,
the shared video styles and comments module.
