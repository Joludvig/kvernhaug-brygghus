'use strict';

// Issue #275 (Roadmap V2.1 #101 Phase 3C follow-up) -- browser coverage for
// the .kbhbrew import/export UI wired onto the existing engine in
// web/js/brew_storage.js (byggKbhBrewInnhold()/parseKbhBrewInnhold()/
// importerBrygg()). This does not re-test the engine's own parsing/
// validation rules (that is the engine's own job) -- it proves the
// USER-VISIBLE path: export downloads a real file, an invalid/duplicate
// import writes nothing and shows feedback, and a valid import only
// persists after the explicit preview + confirm step (never on upload/
// preview alone), without touching an unrelated stored brew.
//
// Every brew's `originBrewId` defaults to its OWN local `brewId` at
// creation (brew_storage.js opprettBrygg()), so re-importing a brew's own
// export back into the SAME storage it came from always collides with
// itself by design -- that is exactly the duplicate-rejection contract,
// not a bug. To exercise a genuine cross-device import, this spec deletes
// the original stored brew (a normal, user-initiated action) before
// importing its exported file back in, while a second, unrelated brew
// stays present throughout to prove the import never touches it.

const { test, expect } = require('@playwright/test');
const {
  localePath, collectErrors, dismissModeDialog,
} = require('./helpers');

const RECIPE_NAVN = 'KBH Brew Export Test';
const UBERORT_NAVN = 'KBH Untouched Brew';

async function velgFraCombobox(page, radSelector, sokeTekst, valgTekst) {
  const rad = page.locator(radSelector).first();
  const input = rad.locator('.combobox-input');
  await input.click();
  await input.fill(sokeTekst);
  await rad.locator('.combobox-option', { hasText: valgTekst }).first().click();
}

async function opprettOgStartBrygg(page, locale) {
  await page.goto(localePath(locale, '/index.html'));
  await dismissModeDialog(page, 'laerling');
  await page.fill('#oppskrift-navn', RECIPE_NAVN);
  await page.fill('#batch-volum', '20');
  await velgFraCombobox(page, '#malt-rader .ingrediens-rad', 'Weyermann', 'Pilsner Malt');
  await page.fill('#malt-rader .malt-mengde', '5');
  await velgFraCombobox(page, '#humle-rader .ingrediens-rad', 'Cascade', 'Cascade');
  await velgFraCombobox(page, '#gjaer-panel', 'Fermentis', 'SafAle US-05');
  await page.locator('#start-brygging-knapp').click();
  await expect(page.locator('#brygg-start-status')).toContainText(RECIPE_NAVN);
}

// A second, unrelated brew, injected directly via the already-loaded
// brew_storage.js engine (not the full recipe-builder flow) -- it only
// needs to be a genuinely separate, valid, stored brew whose survival the
// import must never disturb.
async function leggTilUberortBrygg(page) {
  await page.evaluate((navn) => {
    window.opprettBrygg({ snapshot: { recipe: { navn }, predicted: {} } });
    window.visLogg(null, null);
  }, UBERORT_NAVN);
}

async function bryggState(page) {
  const raw = await page.evaluate(() => localStorage.getItem('kvernhaug_web_brygg'));
  return raw ? JSON.parse(raw) : { items: [] };
}

async function lesNedlastning(download) {
  const stream = await download.createReadStream();
  const chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  return Buffer.concat(chunks).toString('utf-8');
}

async function slettBryggMedNavn(page, navn) {
  page.once('dialog', (d) => d.accept());
  const kort = page.locator('.brygg-kort', { hasText: navn });
  await kort.locator('.brygg-slett').click();
}

test.describe('.kbhbrew import/export UI (#275)', () => {
  test('export a stored brew, then re-import it via explicit preview/confirm (NO)', async ({ page }) => {
    const errors = collectErrors(page);

    await opprettOgStartBrygg(page, 'no');
    await page.goto(localePath('no', '/bryggelogg.html'));

    const kort = page.locator('.brygg-kort', { hasText: RECIPE_NAVN });
    await expect(kort).toBeVisible();

    // 1. Export the existing brew -- a real .kbhbrew download, no local
    // brewId leaked into the file (Core identity policy), but a portable
    // originBrewId present.
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      kort.locator('.brygg-eksporter').click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.kbhbrew$/);
    const eksportertTekst = await lesNedlastning(download);
    const eksportert = JSON.parse(eksportertTekst);
    expect(eksportert.format).toBe('kbhbrew');
    expect(eksportert.brew.snapshot.recipe.navn).toBe(RECIPE_NAVN);
    expect(eksportert.brew.brewId).toBeUndefined();
    expect(typeof eksportert.brew.originBrewId).toBe('string');

    // A second, unrelated brew must survive every step below untouched.
    await leggTilUberortBrygg(page);
    await expect(page.locator('.brygg-kort', { hasText: UBERORT_NAVN })).toBeVisible();

    // Remove the original brew (simulating "on a fresh device/browser this
    // brew doesn't exist yet") so the re-import below is a genuine new
    // arrival, not a self-collision with the still-present original.
    await slettBryggMedNavn(page, RECIPE_NAVN);
    await expect(page.locator('.brygg-kort', { hasText: RECIPE_NAVN })).toHaveCount(0);
    expect((await bryggState(page)).items.length).toBe(1); // only the untouched brew left

    // 2. Invalid file -- no preview, nothing persisted, clear feedback.
    await page.setInputFiles('#brygg-importer-input', {
      name: 'ugyldig.kbhbrew',
      mimeType: 'application/json',
      buffer: Buffer.from('dette er ikke json'),
    });
    await expect(page.locator('#brygg-import-status')).toContainText('ikke gyldig JSON');
    await expect(page.locator('#brygg-import-forhandsvisning-blokk')).toBeHidden();
    expect((await bryggState(page)).items.length).toBe(1);

    // 3. Valid file -- preview renders, but upload/preview alone persists
    // nothing (acceptance #3).
    await page.setInputFiles('#brygg-importer-input', {
      name: 'gyldig.kbhbrew',
      mimeType: 'application/json',
      buffer: Buffer.from(eksportertTekst),
    });
    await expect(page.locator('#brygg-import-forhandsvisning-blokk')).toBeVisible();
    await expect(page.locator('#brygg-import-forhandsvisning-navn')).toContainText(RECIPE_NAVN);
    expect((await bryggState(page)).items.length).toBe(1);

    // Cancel discards the preview -- still nothing written.
    await page.locator('#brygg-import-avbryt').click();
    await expect(page.locator('#brygg-import-forhandsvisning-blokk')).toBeHidden();
    expect((await bryggState(page)).items.length).toBe(1);

    // 4. Re-select the same file and actually confirm the import.
    await page.setInputFiles('#brygg-importer-input', {
      name: 'gyldig.kbhbrew',
      mimeType: 'application/json',
      buffer: Buffer.from(eksportertTekst),
    });
    await expect(page.locator('#brygg-import-forhandsvisning-blokk')).toBeVisible();
    await page.locator('#brygg-import-bekreft').click();
    await expect(page.locator('#brygg-import-forhandsvisning-blokk')).toBeHidden();
    await expect(page.locator('#brygg-import-status')).toContainText('importert');
    let state = await bryggState(page);
    expect(state.items.length).toBe(2);
    // Acceptance #5: the imported brew appears, and the unrelated brew is
    // untouched (still present, unchanged).
    expect(state.items.some((b) => b.snapshot.recipe.navn === RECIPE_NAVN)).toBe(true);
    expect(state.items.some((b) => b.snapshot.recipe.navn === UBERORT_NAVN)).toBe(true);
    await expect(page.locator('.brygg-kort', { hasText: RECIPE_NAVN })).toBeVisible();
    await expect(page.locator('.brygg-kort', { hasText: UBERORT_NAVN })).toBeVisible();

    // 5. Importing the exact same file again is rejected as a duplicate
    // (same originBrewId) -- no overwrite/merge, no third item persisted.
    await page.setInputFiles('#brygg-importer-input', {
      name: 'gyldig.kbhbrew',
      mimeType: 'application/json',
      buffer: Buffer.from(eksportertTekst),
    });
    await expect(page.locator('#brygg-import-forhandsvisning-blokk')).toBeVisible();
    await page.locator('#brygg-import-bekreft').click();
    await expect(page.locator('#brygg-import-status')).toContainText('finnes allerede');
    state = await bryggState(page);
    expect(state.items.length).toBe(2);

    expect(errors).toEqual([]);
  });

  test('import preview and feedback render real EN copy, no raw i18n key', async ({ page }) => {
    const errors = collectErrors(page);

    await opprettOgStartBrygg(page, 'en');
    await page.goto(localePath('en', '/bryggelogg.html'));

    const kort = page.locator('.brygg-kort', { hasText: RECIPE_NAVN });
    await expect(kort).toBeVisible();
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      kort.locator('.brygg-eksporter').click(),
    ]);
    const eksportertTekst = await lesNedlastning(download);

    await slettBryggMedNavn(page, RECIPE_NAVN);
    await expect(page.locator('.brygg-kort', { hasText: RECIPE_NAVN })).toHaveCount(0);

    // Invalid file: EN feedback, no persistence.
    await page.setInputFiles('#brygg-importer-input', {
      name: 'invalid.kbhbrew',
      mimeType: 'application/json',
      buffer: Buffer.from('not json'),
    });
    await expect(page.locator('#brygg-import-status')).toContainText('not valid JSON');
    expect((await bryggState(page)).items.length).toBe(0);

    // Valid file: EN preview, explicit confirm persists exactly once.
    await page.setInputFiles('#brygg-importer-input', {
      name: 'valid.kbhbrew',
      mimeType: 'application/json',
      buffer: Buffer.from(eksportertTekst),
    });
    await expect(page.locator('#brygg-import-forhandsvisning-blokk')).toBeVisible();
    await expect(page.locator('#brygg-import-forhandsvisning-navn')).toContainText(RECIPE_NAVN);
    await page.locator('#brygg-import-bekreft').click();
    await expect(page.locator('#brygg-import-status')).toContainText('imported');
    expect((await bryggState(page)).items.length).toBe(1);

    expect(errors).toEqual([]);
  });
});
