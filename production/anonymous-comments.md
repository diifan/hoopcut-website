# Video comments deployment

The video-page frontend uses the existing Node `/api/comments` and isolated Supabase schema. No Python API or SQLite service is deployed. See `docs/anonymous-comments.md` for server configuration and administration.

This integration preserves anonymous ownership, reports, deletion and existing comments, and adds optional names, persistent reactions and top-comment sorting. Production fixtures are never seeded.
