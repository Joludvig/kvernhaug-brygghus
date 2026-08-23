# Testing policy

- Run focused/relevant tests first; suppress successful-test noise where possible (`py -3 -m unittest discover -s tests -b`).
- Full Python suite (`tests/`) is required at final checkpoints and commit-ready validation.
- `tests/` DOES cover `web/**` — `tests/test_generate_web_i18n_pages.py` (49 tests) covers the i18n generator, NO/EN key symmetry, the `PAGES` guard, canonical/hreflang, `sitemap.xml`, `robots.txt`, noindex and favicon, and asserts that committed `web/en/**` + `sitemap.xml` byte-match a fresh generator run. A `web/**` diff can therefore break the suite: always run at least that file on a web round (`py -3 -m unittest tests.test_generate_web_i18n_pages -b`). An intermediate round whose diff is demonstrably confined to `web/**` may skip the *rest* of the suite, but still run the full suite at the final checkpoint before commit.
- There is no browser/E2E coverage in `tests/` — functional/responsive/console-error verification in a real browser is a separate, manual Playwright sweep (see the `web-full-regression` skill).
- Failures always get full, detailed output. Successful runs get a compact summary (counts, not per-test noise).
- Deeper guidance (isolation principles, `AppTest` pattern): [TESTING.md](../../docs/development/TESTING.md).
