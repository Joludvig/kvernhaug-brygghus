'use strict';

// Astra A2-02 (issue #205) -- an invalid recipe with batch volume <= 0 must
// never be explicitly persisted as a saved recipe/variant or frozen into a
// new brew, while the autosaved active draft keeps working with an empty/0
// volume. See web/js/app.js (_blokkerUgyldigBatchVolum(), reused by
// lagreOppskrift()/lagreSomVariant()/startBrygging()) and web/js/i18n.js
// (oppskrift.volumPaakrevd).
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors, dismissModeDialog, openSideDrawer } = require('./helpers');

const OPPSKRIFT_NOKKEL = 'kvernhaug_web_oppskrifter';
const BREW_NOKKEL = 'kvernhaug_web_brygg';
const AKTIV_KLADD_NOKKEL = 'kvernhaug_web_aktiv_kladd';

async function lagredeOppskrifter(page) {
  return page.evaluate((key) => {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw).items;
  }, OPPSKRIFT_NOKKEL);
}

async function lagredeBrygg(page) {
  return page.evaluate((key) => {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw).items;
  }, BREW_NOKKEL);
}

test('empty and explicit-0 batch volume blocks Save, Save as variant and Start brewing [no]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  const naam = 'Volumsperre NO';
  await page.fill('#oppskrift-navn', naam);

  const forventetMelding = 'Batch-volum må være over 0 L før du kan lagre, lagre som variant eller starte brygging.';

  // Sak 1 -- tomt felt (tastet tomt/slettet), blokkerer "Lagre oppskrift".
  await page.fill('#batch-volum', '');
  await page.click('#lagre-knapp');
  await expect(page.locator('#lagre-status')).toHaveText(forventetMelding);
  expect(await lagredeOppskrifter(page)).toBeNull();

  // Sak 1 -- samme tomme felt blokkerer "Start brygging".
  await page.click('#start-brygging-knapp');
  await expect(page.locator('#brygg-start-status')).toHaveText(forventetMelding);
  expect(await lagredeBrygg(page)).toBeNull();

  // Sak 2 -- eksplisitt 0 blokkerer "Lagre oppskrift" på samme måte.
  await page.fill('#batch-volum', '0');
  await page.click('#lagre-knapp');
  await expect(page.locator('#lagre-status')).toHaveText(forventetMelding);
  expect(await lagredeOppskrifter(page)).toBeNull();

  // Sak 2 -- eksplisitt 0 blokkerer "Start brygging" på samme måte.
  await page.click('#start-brygging-knapp');
  await expect(page.locator('#brygg-start-status')).toHaveText(forventetMelding);
  expect(await lagredeBrygg(page)).toBeNull();

  expect(errors).toEqual([]);
});

test('0 batch volume blocks Save as variant on an already-saved recipe [no]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  await page.fill('#oppskrift-navn', 'Variantsperre NO');
  await page.fill('#batch-volum', '20');
  await page.click('#lagre-knapp');
  await expect(page.locator('#lagre-variant-knapp')).toBeVisible();
  expect(await lagredeOppskrifter(page)).toHaveLength(1);

  await page.fill('#batch-volum', '0');
  await page.click('#lagre-variant-knapp');
  await expect(page.locator('#lagre-status')).toHaveText(
    'Batch-volum må være over 0 L før du kan lagre, lagre som variant eller starte brygging.'
  );
  expect(await lagredeOppskrifter(page)).toHaveLength(1);

  expect(errors).toEqual([]);
});

test('a valid positive batch volume still saves, saves as variant and starts a brew [no]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  await page.fill('#oppskrift-navn', 'Gyldig volum NO');
  await page.fill('#batch-volum', '20');

  await page.click('#lagre-knapp');
  await expect(page.locator('#lagre-status')).toContainText('Lagret');
  expect(await lagredeOppskrifter(page)).toHaveLength(1);

  await page.click('#lagre-variant-knapp');
  await expect(page.locator('#lagre-status')).toContainText('variant');
  expect(await lagredeOppskrifter(page)).toHaveLength(2);

  await page.click('#start-brygging-knapp');
  await expect(page.locator('#brygg-start-status')).toContainText('Brygget er i gang');
  expect(await lagredeBrygg(page)).toHaveLength(1);

  expect(errors).toEqual([]);
});

test('empty batch volume blocks Save with the English message [en]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('en', '/index.html'));
  await dismissModeDialog(page);

  await page.fill('#oppskrift-navn', 'Volume guard EN');
  await page.fill('#batch-volum', '');
  await page.click('#lagre-knapp');
  await expect(page.locator('#lagre-status')).toHaveText(
    'Batch volume must be greater than 0 L before you can save, save as variant, or start brewing.'
  );
  expect(await lagredeOppskrifter(page)).toBeNull();

  expect(errors).toEqual([]);
});

test('empty batch volume blocks Save with the US customary unit wording [no]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  await openSideDrawer(page);
  await page.locator('.enhet-knapp[data-enhet="us"]').click();

  await page.fill('#oppskrift-navn', 'Volumsperre US NO');
  await page.fill('#batch-volum', '');
  await page.click('#lagre-knapp');
  await expect(page.locator('#lagre-status')).toHaveText(
    'Batch-volum må være over 0 US gal før du kan lagre, lagre som variant eller starte brygging.'
  );
  expect(await lagredeOppskrifter(page)).toBeNull();

  expect(errors).toEqual([]);
});

test('empty batch volume blocks Save with the US customary unit wording [en]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('en', '/index.html'));
  await dismissModeDialog(page);

  await openSideDrawer(page);
  await page.locator('.enhet-knapp[data-enhet="us"]').click();

  await page.fill('#oppskrift-navn', 'Volume guard US EN');
  await page.fill('#batch-volum', '');
  await page.click('#lagre-knapp');
  await expect(page.locator('#lagre-status')).toHaveText(
    'Batch volume must be greater than 0 US gal before you can save, save as variant, or start brewing.'
  );
  expect(await lagredeOppskrifter(page)).toBeNull();

  expect(errors).toEqual([]);
});

test('the active draft still autosaves with an empty/0 batch volume', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  await page.fill('#oppskrift-navn', 'Kladd med 0-volum');
  await page.fill('#batch-volum', '0');

  await expect
    .poll(() => page.evaluate((key) => {
      const raw = localStorage.getItem(key);
      if (!raw) return null;
      return JSON.parse(raw).volum;
    }, AKTIV_KLADD_NOKKEL))
    .toBe(0);

  // Ingen av de eksplisitte handlingene ble klikket -- kladden er ren
  // autolagring, ikke berørt av _blokkerUgyldigBatchVolum().
  expect(await lagredeOppskrifter(page)).toBeNull();
  expect(await lagredeBrygg(page)).toBeNull();

  expect(errors).toEqual([]);
});
