'use strict';

// Issue #200 V1 scope item 6: representative help hash/anchor navigation
// that is already known-good. Deliberately does NOT assert the
// .hjelp-metode-kort scroll-margin behavior fixed by issue #188 -- see
// 09-b11-metode-kort-scroll-margin.spec.js -- only that a "Les mer ->"
// popover link actually lands on its target article in
// web/hjelp/index.html.
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors, dismissModeDialog } = require('./helpers');

for (const locale of ['no', 'en']) {
  test(`a help "Les mer" link opens the matching help article anchor [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/index.html'));
    await dismissModeDialog(page);

    await page.locator('.hjelp-knapp[data-hjelp="alfasyre"]').first().click();
    const popover = page.locator('.hjelp-popover');
    await expect(popover).toBeVisible();

    const lesMer = popover.locator('.hjelp-les-mer');
    await expect(lesMer).toHaveAttribute('href', 'hjelp/index.html#alfasyre');
    await expect(lesMer).toHaveAttribute('target', '_blank');

    // Opens in a new tab (target="_blank") -- assert on that popup, not
    // the original builder page.
    const [helpPage] = await Promise.all([page.waitForEvent('popup'), lesMer.click()]);
    await helpPage.waitForLoadState();

    await expect(helpPage).toHaveURL(/hjelp\/index\.html#alfasyre$/);
    await expect(helpPage.locator('#alfasyre')).toBeVisible();

    await helpPage.close();
    expect(errors).toEqual([]);
  });
}
