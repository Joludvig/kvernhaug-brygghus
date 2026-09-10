'use strict';

// Issue #200 V1 scope item 1: builder loads in all 8 browser/viewport/
// locale combinations (the 4 projects x these 2 locales cover the matrix).
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors, dismissModeDialog } = require('./helpers');

for (const locale of ['no', 'en']) {
  test(`builder (index.html) loads with 0 console/page errors [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/index.html'));
    await dismissModeDialog(page);

    await expect(page.locator('#oppskrift-navn')).toBeVisible();
    await expect(page.locator('#malt-rader .ingrediens-rad[data-type="malt"]').first()).toBeVisible();
    await expect(page.locator('#humle-rader .ingrediens-rad[data-type="humle"]').first()).toBeVisible();
    await expect(page).toHaveTitle(/.+/);

    expect(errors).toEqual([]);
  });
}
