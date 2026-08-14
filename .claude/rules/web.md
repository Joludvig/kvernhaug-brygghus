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
- `web/en/**` is 100% generated output (by `scripts/generate_web_i18n_pages.py`) — never hand-edit it. To change English content or add a page: edit the Norwegian source HTML and/or `TEKSTER` in `web/js/i18n.js`, register any new page in the generator's `PAGES` list, then re-run the generator and commit source + regenerated `web/en/**` together in the same change.
- Full architecture, file structure, and design rationale: [web/README.md](../../web/README.md) — read when the task needs deeper context. Historical round-by-round narrative: [web/CHANGELOG.md](../../web/CHANGELOG.md).
