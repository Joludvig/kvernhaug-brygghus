'use strict';

// Issue #188 -- .hjelp-metode-kort anchors (e.g. #dry-hop in
// web/hjelp/humle.html) had no scroll-margin-top, so a direct/bookmarked
// hash load or an in-page TOC click landed the card's heading underneath
// the fixed .kompaktnav. web/css/style.css now extends the same
// `scroll-margin-top: calc(var(--kompaktnav-h, 0px) + 1rem)` rule already
// used by .hjelp-seksjon/.hjelp-artikkel/.hjelp-steg to .hjelp-metode-kort
// -- see docs/development/web_b11_metode_kort_anchor_preflight.md §4/§7
// for the measured before/after evidence and this spec's acceptance matrix
// (T1-T6). Chromium/Firefox x desktop/mobile coverage comes from
// playwright.config.js's project matrix, not from this file.
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors } = require('./helpers');

// Bounding-box overlap of a fixed nav against a scrolled-to heading: a
// positive value means the heading's top sits above the nav's bottom edge
// (hidden underneath it) -- the exact symptom the issue reports. Asserting
// <= 0 (with a small tolerance for subpixel rounding) instead of pinning
// the brief's measured ~-33px keeps the test robust to font/layout drift
// while still catching the regression it exists to catch.
async function assertClearOfNav(page, headingLocator) {
  const nav = page.locator('.kompaktnav');
  await expect(nav).toHaveClass(/synlig/);
  const navBox = await nav.boundingBox();
  const headingBox = await headingLocator.boundingBox();
  const overlap = navBox.y + navBox.height - headingBox.y;
  expect(overlap).toBeLessThan(2);
}

for (const locale of ['no', 'en']) {
  test(`a direct hash load lands a .hjelp-metode-kort heading clear of .kompaktnav (T1-T3) [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/hjelp/humle.html#dry-hop'));
    await assertClearOfNav(page, page.locator('#dry-hop h3'));
    expect(errors).toEqual([]);
  });

  test(`an in-page TOC click to a .hjelp-metode-kort anchor lands clear of .kompaktnav (T4) [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/hjelp/humle.html'));
    await page.locator('a[href="#dry-hop"]').first().click();
    await assertClearOfNav(page, page.locator('#dry-hop h3'));
    expect(errors).toEqual([]);
  });

  test(`a second .hjelp-metode-kort anchor on a different page is also clear of .kompaktnav (T5) [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/hjelp/vannkjemi.html#alkalitet'));
    await assertClearOfNav(page, page.locator('#alkalitet h3'));
    expect(errors).toEqual([]);
  });

  test(`an already-covered .hjelp-steg anchor is unaffected by the .hjelp-metode-kort fix (T6) [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/hjelp/bryggedag.html#steg-10'));
    await assertClearOfNav(page, page.locator('#steg-10 h3'));
    expect(errors).toEqual([]);
  });
}
