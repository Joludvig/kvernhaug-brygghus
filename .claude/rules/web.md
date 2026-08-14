---
paths:
  - "web/**"
---

# Web version — resident rules

- Static HTML/CSS/vanilla JS. No backend, no build step, no npm dependency — don't introduce one without explicit approval.
- Preserve existing `localStorage` keys and the `.kbhrecipe` import/export format — never a breaking change without an explicit, versioned migration.
- `recipe_engine.js` stays DOM-independent shared logic (used by both the builder and Utskrift) — don't couple it back to `document`.
- Responsive behavior (no horizontal overflow, 0 console/page errors) must be preserved across viewports/browsers on any change.
- Norwegian/English localization work must use real shared data/logic and explicit, reviewed translations — never machine translation.
- `web/en/**` and `web/sitemap.xml` are 100% generated output (by `scripts/generate_web_i18n_pages.py`) — never hand-edit them. To change English content, SEO metadata, or add a page: edit the Norwegian source HTML (title/description/canonical/hreflang `<link>` tags in `<head>`) and/or `TEKSTER` in `web/js/i18n.js`, register any new page in the generator's `PAGES` list, then re-run the generator and commit source + regenerated `web/en/**`/`sitemap.xml` together in the same change. Production domain (`https://kvernhaugbrygghus.no`, canonical/hreflang/sitemap base) is hardcoded once as `PROD_BASE` in the generator — never duplicate it elsewhere. `web/robots.txt` is a small hand-written static file, not generated.
- Full architecture, file structure, and design rationale: [web/README.md](../../web/README.md) — read when the task needs deeper context. Historical round-by-round narrative: [web/CHANGELOG.md](../../web/CHANGELOG.md).
