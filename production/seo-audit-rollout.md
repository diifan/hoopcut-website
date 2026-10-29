# SEO audit follow-up — local review, 2026-10-28

The user approved publishing the reviewed local version on 2026-10-28. The
checklist below separates website changes from hosting/account activation and
post-deployment Google verification; those require their own observed results.

## Prepared locally

- Readable homepage text on mobile; original review copy and cards preserved.
- Responsive WebP images and smaller complete background/player video reels.
- App Store download buttons use the verified Hoopcut detail page (App ID
  `6824860341`). The existing hello@goswie.com address remains for support.
- Contextual guide-to-tool links, a revised Instagram video workflow, and links
  to the real prepared sample in the primary/iPhone/Tracer guides.
- Shared Organization identity; clearer Tools and Blog headings; editorial
  attribution without invented credentials, measurements or app recordings.
- Anonymous event hooks, disabled pending provider activation.
- Fingerprinted asset caching and a www-to-apex redirect rule.
- Full sitemap retained: 39 existing canonical URLs. Local preview is noindex.

## Hosting: www certificate (still requires live verification)

1. In the existing Vercel project, check that both `hoopcut.ai` and
   `www.hoopcut.ai` are attached to the correct project/account.
2. Use the DNS value actually prescribed by that project's domain setup. Do not
   copy a guessed generic CNAME or IP, and do not change email-related records.
3. Provision a certificate valid for `www.hoopcut.ai`. The HTTP redirect cannot
   bypass a TLS hostname error because TLS is established before HTTP.
4. After the approved release, confirm www redirects to the apex with path and
   query preserved. Keep the apex as the established canonical domain.

```sh
curl -I https://www.hoopcut.ai/
curl -IL 'https://www.hoopcut.ai/tools?source=domain-check'
curl -I https://hoopcut.ai/tools
```

Do not use `curl -k` as proof that the certificate is fixed.

## Analytics: activation and validation

1. Enable Web Analytics in the correct Vercel project's Analytics dashboard.
2. Confirm the plan supports the requested features. Basic page views and custom
   events have different entitlements; custom events require Pro/Enterprise in
   the documentation checked on 2026-10-28. No plan upgrade is authorized here.
3. In `content/site-config.json`, set `analytics.enabled` to true only after the
   provider is ready. Set `customEvents` to true only if entitled. Rebuild and
   include those changes in the approved release.
4. Verify one live page-view request and one successful export event in the
   dashboard. Preview events are local-only and do not prove live delivery.
5. Events include only the canonical page path, code-owned tool identifier,
   format or demo identifier. They must not contain names, worksheet entries,
   captions, email addresses, query strings or uploaded media.

`export_success` means the browser created a downloadable file; it does not prove
that the user saved it to disk. `print_click` records intent, not a printed page.

References: [Vercel quickstart](https://vercel.com/docs/analytics/quickstart),
[custom events](https://vercel.com/docs/analytics/custom-events).

## GSC: after the approved release

1. Verify production has all 39 canonical URLs and the updated sitemap.
2. Resubmit the existing `https://hoopcut.ai/sitemap.xml`, rather than creating
   duplicate sitemap locations.
3. Inspect `/tools` and a few representative new tools. For the Instagram guide,
   inspect canonical selection and request indexing after the updated copy is live.
4. Record the new sitemap last-read date, discovered pages and URL-level crawl
   status. Report discovery separately from indexing; neither a submission nor
   an HTTP 200 guarantees inclusion.
5. Compare organic query/page data only once the report covers this release.

## Evidence still needed for later improvements

- Store availability and download-link changes should be maintained in
  `content/site-config.json` rather than generated HTML alone.
- Genuine app screen recordings, source/output comparisons and the conditions
  under which they were made. Existing prepared footage is not an app tutorial
  or a benchmark and is labeled accordingly.
- Tool use and export data before choosing further photo/layout features or
  scaling the page count. No speculative feature expansion is bundled here.
- Real community adoption and editorial references. No outreach, paid links or
  third-party posts were performed by this change.
