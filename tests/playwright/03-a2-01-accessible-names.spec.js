'use strict';

// Issue #200 V1 scope item 3: A2-01/W1 regression -- malt/hop accessible
// names follow Metric<->US and NO<->EN, including a language switch while
// US is active. See web/js/app.js
// (_oppdaterMaltRadEnhet/_oppdaterHumleRadEnhet, ENHET_FORKORTELSE) and
// web/js/i18n.js (builder.malt.mengdeAriaLabelEnhet / builder.humle.gramAriaLabelEnhet).
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors, dismissModeDialog, openSideDrawer } = require('./helpers');

test('malt/hop amount aria-label reflects the active unit system [no]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  const maltMengde = page.locator('#malt-rader .malt-mengde').first();
  const humleGram = page.locator('#humle-rader .humle-gram').first();
  await expect(maltMengde).toHaveAttribute('aria-label', 'Maltmengde (kg)');
  await expect(humleGram).toHaveAttribute('aria-label', 'Humlemengde (g)');

  await openSideDrawer(page);
  await page.locator('.enhet-knapp[data-enhet="us"]').click();

  await expect(maltMengde).toHaveAttribute('aria-label', 'Maltmengde (lb)');
  await expect(humleGram).toHaveAttribute('aria-label', 'Humlemengde (oz)');

  expect(errors).toEqual([]);
});

test('malt/hop amount aria-label follows a language switch while US is active [no -> en]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  await openSideDrawer(page);
  await page.locator('.enhet-knapp[data-enhet="us"]').click();
  await expect(page.locator('#malt-rader .malt-mengde').first()).toHaveAttribute('aria-label', 'Maltmengde (lb)');

  await Promise.all([
    page.waitForURL(/\/en\/index\.html$/),
    page.locator('.sprakvelger-drawer .sprak-knapp[data-sprak="en"]').click(),
  ]);
  await dismissModeDialog(page);

  // Unit preference is a separate localStorage key from language (see
  // web/js/preferences.js) and survives the plain page navigation above.
  await expect(page.locator('#malt-rader .malt-mengde').first()).toHaveAttribute('aria-label', 'Malt amount (lb)');
  await expect(page.locator('#humle-rader .humle-gram').first()).toHaveAttribute('aria-label', 'Hop amount (oz)');

  expect(errors).toEqual([]);
});

test('malt/hop combobox accessible name is language-only, unaffected by unit system [en]', async ({ page }) => {
  await page.goto(localePath('en', '/index.html'));
  await dismissModeDialog(page);

  // Note: the template's .malt-velger-mount/.humle-velger-mount div is
  // entirely replaced by the Combobox's own element at construction time
  // (mount.replaceWith(cb.el), see web/js/app.js::leggTilMaltRad()) -- it
  // never wraps .combobox-input, so the selector below scopes to the row
  // container instead.
  const maltCombobox = page.locator('#malt-rader .ingrediens-rad[data-type="malt"] .combobox-input').first();
  const humleCombobox = page.locator('#humle-rader .ingrediens-rad[data-type="humle"] .combobox-input').first();
  await expect(maltCombobox).toHaveAttribute('aria-label', 'Choose malt');
  await expect(humleCombobox).toHaveAttribute('aria-label', 'Choose hops');

  await openSideDrawer(page);
  await page.locator('.enhet-knapp[data-enhet="us"]').click();

  await expect(maltCombobox).toHaveAttribute('aria-label', 'Choose malt');
  await expect(humleCombobox).toHaveAttribute('aria-label', 'Choose hops');
});
