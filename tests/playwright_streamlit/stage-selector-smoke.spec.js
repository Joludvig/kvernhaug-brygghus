// Stage UI S3 browser smoke (docs/development/v22_course_stage_ui_contract.md
// §3, §4, §10; offline, no GitHub issue yet). A SMALL real-runtime check of
// the first visible stage UI -- not the S5 matrix (Firefox, 900/750 px,
// sidebar states and the full i18n pass stay in S5).
//
// Per combination (NO Foundation, NO Kompetent, EN Kompetent) at the
// project's viewport (chromium-desktop 1280, chromium-mobile 390):
// - the `bs_trinn` selector is visible and fits the viewport;
// - exactly 11 cards render, in canonical order;
// - no horizontal page overflow (overview and lesson);
// - the Mesking card opens the selected stage (block counter) with both
//   axes in the breadcrumb;
// - the special card action works: Kompetent-only «Se Trinn 2-innholdet»
//   under Foundation switches the lens; Foundation-only «Repeter» under
//   Kompetent opens Foundation and keeps the lens.
//
// Runs against the production render_bryggeskole_panel() harness through
// playwright.bryggeskole-grid.config.js:
//   npx playwright test -c playwright.bryggeskole-grid.config.js \
//     stage-selector-smoke --project=chromium-desktop --project=chromium-mobile

const { test, expect } = require('@playwright/test');

const WIDE = { width: 1280, height: 900 };
const KORT = ['raavarer', 'rengjoring', 'metodevalg', 'mesking', 'koking', 'kjoling', 'gjaring', 'pakking',
  'maaling', 'oppskrift', 'smak'];

const TEKST = {
  no: {
    miljo: /Velg dette miljøet/i,
    foundation: 'Trinn 1 · Foundation',
    kompetent: 'Trinn 2 · Kompetent hjemmebrygger',
    sti: {
      foundation: '🎓 Bryggeskole ▸ 🏠 Hjemmebrygger ▸ Trinn 1 · Foundation ▸ Mesking',
      kompetent: '🎓 Bryggeskole ▸ 🏠 Hjemmebrygger ▸ Trinn 2 · Kompetent ▸ Mesking',
    },
    bolk: { foundation: 'Læringsbolk 1 av 1', kompetent: 'Læringsbolk 1 av 5' },
    stiTrinn1: 'Trinn 1 · Foundation',
    stiTrinn2: 'Trinn 2 · Kompetent',
    seTrinn2: 'Se Trinn 2-innholdet',
    repeter: 'Repeter',
  },
  en: {
    miljo: /Choose this environment/i,
    foundation: 'Stage 1 · Foundation',
    kompetent: 'Stage 2 · Competent homebrewer',
    sti: {
      foundation: '🎓 Brew School ▸ 🏠 Homebrewer ▸ Stage 1 · Foundation ▸ Mashing',
      kompetent: '🎓 Brew School ▸ 🏠 Homebrewer ▸ Stage 2 · Competent homebrewer ▸ Mashing',
    },
    bolk: { foundation: 'Learning block 1 of 1', kompetent: 'Learning block 1 of 5' },
    stiTrinn1: 'Stage 1 · Foundation',
    stiTrinn2: 'Stage 2 · Competent homebrewer',
    seTrinn2: 'View Stage 2 content',
    repeter: 'Review',
  },
};

async function vent(page) {
  await page.waitForFunction(() => !document.querySelector('[data-stale="true"]')
    && !document.querySelector('[data-testid="stStatusWidget"]'), null, { timeout: 20_000 });
  await page.waitForTimeout(300);
}

async function ventGrid(page) {
  await page.waitForFunction((antall) => {
    const grid = document.querySelector('.st-key-bs_skoleoversikt_grid');
    if (!grid || document.querySelector('[data-stale="true"]')) return false;
    const knapper = [...grid.querySelectorAll('[class*="st-key-bs_apne_modul_"] button')];
    return knapper.length === antall && knapper.every((k) => k.getBoundingClientRect().width > 0);
  }, KORT.length, { timeout: 20_000 });
  await vent(page);
}

async function ingenOverflyt(page, hvor) {
  const m = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
  }));
  expect(m.scroll, `horizontal overflow (${hvor})`).toBeLessThanOrEqual(m.client + 1);
}

async function tilOversikt(page, lang, viewport) {
  await page.setViewportSize(WIDE);
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  if (lang === 'en') {
    await page.getByText('English').first().click();
    await vent(page);
  }
  await page.getByRole('button', { name: TEKST[lang].miljo }).first().click();
  await ventGrid(page);
  await page.setViewportSize(viewport);
  await ventGrid(page);
}

async function velgTrinn(page, lang, trinn) {
  await page.locator('.st-key-bs_trinn').getByText(TEKST[lang][trinn], { exact: true }).click();
  await ventGrid(page);
}

async function valgtTrinn(page) {
  return page.locator('.st-key-bs_trinn input[type="radio"]:checked').evaluate(
    (input) => input.closest('label').innerText.trim(),
  );
}

async function sti(page) {
  return (await page.locator('[data-testid="stCaptionContainer"]').filter({ hasText: '▸' }).first().innerText()).trim();
}

async function klikkKort(page, modul) {
  await page.locator(`.st-key-bs_apne_modul_${modul}_btn button`).click();
  await page.waitForFunction(() => !document.querySelector('.st-key-bs_skoleoversikt_grid'), null, { timeout: 20_000 });
  await vent(page);
}

async function tilbake(page) {
  await page.locator('[class*="st-key-bs_tilbake_"] button').first().click();
  await ventGrid(page);
}

for (const [lang, trinn] of [['no', 'foundation'], ['no', 'kompetent'], ['en', 'kompetent']]) {
  test(`stage selector smoke: ${lang} ${trinn}`, async ({ page }, testInfo) => {
    const viewport = testInfo.project.use.viewport;
    const t = TEKST[lang];
    await tilOversikt(page, lang, viewport);

    // Selector visible, both options, fits the viewport.
    const velger = page.locator('.st-key-bs_trinn');
    await expect(velger).toBeVisible();
    await expect(velger.getByText(t.foundation, { exact: true })).toBeVisible();
    await expect(velger.getByText(t.kompetent, { exact: true })).toBeVisible();
    const boks = await velger.boundingBox();
    expect(boks.x + boks.width).toBeLessThanOrEqual(viewport.width + 1);
    expect(await valgtTrinn(page)).toBe(t.foundation);
    if (trinn === 'kompetent') {
      await velgTrinn(page, lang, 'kompetent');
      expect(await valgtTrinn(page)).toBe(t.kompetent);
    }

    // 11 cards, canonical order, nothing disabled, no overflow.
    const nokler = await page.locator('.st-key-bs_skoleoversikt_grid [class*="st-key-bs_apne_modul_"]').evaluateAll(
      (els) => els.map((e) => [...e.classList].find((c) => c.startsWith('st-key-bs_apne_modul_'))),
    );
    expect(nokler).toEqual(KORT.map((m) => `st-key-bs_apne_modul_${m}_btn`));
    expect(await page.locator('.st-key-bs_skoleoversikt_grid button:disabled').count()).toBe(0);
    await ingenOverflyt(page, 'overview');

    // Mesking opens at the selected stage, both axes in the breadcrumb.
    await klikkKort(page, 'mesking');
    expect(await sti(page)).toBe(t.sti[trinn]);
    await expect(page.getByText(t.bolk[trinn], { exact: true })).toBeVisible();
    await ingenOverflyt(page, 'Mesking lesson');
    await tilbake(page);
    expect(await valgtTrinn(page)).toBe(t[trinn]);

    // Special card action.
    if (trinn === 'foundation') {
      await expect(page.locator('.st-key-bs_apne_modul_oppskrift_btn button')).toHaveText(t.seTrinn2);
      await klikkKort(page, 'oppskrift');
      expect(await sti(page)).toContain(t.stiTrinn2);
      await tilbake(page);
      expect(await valgtTrinn(page)).toBe(t.kompetent);
    } else {
      await expect(page.locator('.st-key-bs_apne_modul_rengjoring_btn button')).toHaveText(t.repeter);
      await klikkKort(page, 'rengjoring');
      expect(await sti(page)).toContain(t.stiTrinn1);
      await ingenOverflyt(page, 'Rengjøring Foundation lesson');
      await tilbake(page);
      expect(await valgtTrinn(page)).toBe(t.kompetent);
    }
    await ingenOverflyt(page, 'overview after special card');
  });
}
