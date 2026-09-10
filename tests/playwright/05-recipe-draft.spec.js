'use strict';

// Issue #200 V1 scope item 5: representative recipe draft/save/reload
// state that is already valid on current master. web/js/app.js autosaves
// the "aktiv kladd" (active draft) to localStorage["kvernhaug_web_aktiv_kladd"]
// on every relevant input (beregnOgVisResultat()) and restores it on load
// (hentAktivKladd()/_gjenopprettOppskrift()). Uses the recipe name + brewer
// fields (both plain "Grunndata" fields, always visible in either mode,
// samleOppskrift() always includes them, web/js/app.js:1474/1475) --
// deliberately not a malt/hop row, since lesMaltRader()/lesHumleRader()
// (app.js:851-871) drop any row with no ingredient actually selected from
// the combobox, which a plain .fill() on the amount field never does, and
// not #oppskrift-notater, which is .mester-only (hidden in Laerling mode).
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors, dismissModeDialog } = require('./helpers');

test('active draft autosaves on input and restores after a reload', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  await page.fill('#oppskrift-navn', 'Kladdetest Saison');
  await page.fill('#brygger-navn', 'Ola Brygger');

  await expect
    .poll(() => page.evaluate(() => {
      const kladd = localStorage.getItem('kvernhaug_web_aktiv_kladd');
      if (!kladd) return null;
      const parsed = JSON.parse(kladd);
      return { navn: parsed.navn, brygger: parsed.brygger };
    }))
    .toEqual({ navn: 'Kladdetest Saison', brygger: 'Ola Brygger' });

  await page.reload();

  await expect(page.locator('#oppskrift-navn')).toHaveValue('Kladdetest Saison');
  await expect(page.locator('#brygger-navn')).toHaveValue('Ola Brygger');

  expect(errors).toEqual([]);
});
