'use strict';

// Issue #200 V1 scope item 4: representative Learner<->Master state
// preservation. web/js/app.js::settModus() is documented as a pure
// display toggle ("rorer aldri oppskriftsdata, kun CSS-klasse pa body") --
// this asserts recipe field values survive a mode round-trip, and that
// only .mester-only visibility (driven by body.modus-laerling in
// web/css/style.css) changes.
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors, dismissModeDialog, openSideDrawer } = require('./helpers');

test('switching Laerling <-> Mester preserves recipe data and only toggles mester-only visibility', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page, 'laerling');

  await page.fill('#oppskrift-navn', 'Regresjonstest IPA');
  await page.fill('#malt-rader .malt-mengde', '5.5');

  const maltPct = page.locator('#malt-rader .malt-pct').first();
  await expect(page.locator('body')).toHaveClass(/modus-laerling/);
  await expect(maltPct).toBeHidden();

  await openSideDrawer(page);
  await page.locator('.sidemeny-modus-knapp[data-modus="mester"]').click();

  await expect(page.locator('body')).toHaveClass(/modus-mester/);
  await expect(maltPct).toBeVisible();
  await expect(page.locator('#oppskrift-navn')).toHaveValue('Regresjonstest IPA');
  await expect(page.locator('#malt-rader .malt-mengde').first()).toHaveValue('5.5');

  await openSideDrawer(page);
  await page.locator('.sidemeny-modus-knapp[data-modus="laerling"]').click();

  await expect(page.locator('body')).toHaveClass(/modus-laerling/);
  await expect(maltPct).toBeHidden();
  await expect(page.locator('#oppskrift-navn')).toHaveValue('Regresjonstest IPA');
  await expect(page.locator('#malt-rader .malt-mengde').first()).toHaveValue('5.5');

  expect(errors).toEqual([]);
});
