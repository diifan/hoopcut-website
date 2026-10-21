# Hoopcut website

Static marketing site for Hoopcut: AI basketball highlights, player selection,
shot trajectories and scoring.

## Deploy

Publish this repository's root directory using any static web host.
No package installation, build command, environment variables or backend are required.
The entry point is `index.html`; legal pages are `terms.html` and `privacy.html`.
Keep the `assets/` directory and filenames intact, including the MP4 videos.

## Local preview

```sh
python3 -m http.server 8080
```

Open http://localhost:8080.

## Files

- `index.html`: landing page
- `terms.html`, `privacy.html`: legal pages
- `assets/banner.css`: responsive layout and video styling
- `assets/banner.js`: interactive player highlights
- `assets/navigation.js`: mobile navigation
- `assets/video/players/`: ready-to-serve reels and posters
- `assets/players/`: player portraits
- `production/`: video edit and attribution metadata
- `scripts/render_banner.py`: optional reel regeneration with Python 3 and FFmpeg

All assets needed to serve the website are included. Regenerating the reels
requires the original 52-second source footage separately:

```sh
python3 scripts/render_banner.py --source /path/to/all_makes.mp4
```

The local source URL recorded in production metadata is provenance only; the
website does not fetch it during playback. No video regeneration is needed for deployment.
