// Stage UI S4 browser smoke (docs/development/v22_course_stage_ui_contract.md
// §7.2, §7.3, §10; offline, no GitHub issue yet). A SMALL real-runtime check
// of the per-stage status lines and the stage module count -- not the S5
// matrix (Firefox, 900/750 px, sidebar states stay in S5).
//
// Needs a seeded learner history in KVERNHAUG_BRYGGESKOLE_STATE_DIR (the
// web server inherits it): Råvarer Foundation worked through and one of
// Gjæring Foundation's questions answered -- so the Foundation lens shows
// all three statuses and "1 av 9 moduler gjennomgått".
//
//   npx playwright test -c playwright.bryggeskole-grid.config.js \
//     stage-progress-smoke --project=chromium-desktop --project=chromium-mobile

const { test, expect } = require('@playwright/test');

const WIDE = { width: 1280, height: 900 };

const TEKST = {
  no: {
    miljo: /Velg dette miljøet/i,
    kompetent: 'Trinn 2 · Kompetent hjemmebrygger',
    status: ['Ikke startet', 'Påbegynt', 'Gjennomgått'],
    telling: { foundation: '1 av 9 moduler gjennomgått', kompetent: '0 av 9 moduler gjennomgått' },
    tips: 'Tips: Du har fortsatt noen Foundation-deler du kan gå tilbake til.',
  },
  en: {
    miljo: /Choose this environment/i,
    kompetent: 'Stage 2 · Competent homebrewer',
    status: ['Not started', 'In progress', 'Worked through'],
    telling: { foundation: '1 of 9 modules worked through', kompetent: '0 of 9 modules worked through' },
    tips: 'Tip: You still have some Foundation sections you can revisit.',
  },
};

async function ventGrid(page) {
  await page.waitForFunction(() => {
    const grid = document.querySelector('.st-key-bs_skoleoversikt_grid');
    if (!grid || document.querySelector('[data-stale="true"]')) return false;
    const knapper = [...grid.querySelectorAll('[class*="st-key-bs_apne_modul_"] button')];
    return knapper.length === 11 && knapper.every((k) => k.getBoundingClientRect().width > 0);
  }, null, { timeout: 20_000 });
  await page.waitForTimeout(400);
}

async function statusLinjer(page, lang) {
  const tekster = await page.locator('.st-key-bs_skoleoversikt_grid [data-testid="stCaptionContainer"]').allInnerTexts();
  return tekster.map((s) => s.trim()).filter((s) => TEKST[lang].status.includes(s));
}

async function ingenOverflyt(page) {
  const m = await page.evaluate(() => ({ s: document.documentElement.scrollWidth, c: document.documentElement.clientWidth }));
  expect(m.s).toBeLessThanOrEqual(m.c + 1);
}

for (const [lang, trinn] of [['no', 'foundation'], ['no', 'kompetent'], ['en', 'kompetent']]) {
  test(`stage progress smoke: ${lang} ${trinn}`, async ({ page }, testInfo) => {
    const viewport = testInfo.project.use.viewport;
    const t = TEKST[lang];
    await page.setViewportSize(WIDE);
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    if (lang === 'en') {
      await page.getByText('English').first().click();
      await page.waitForTimeout(600);
    }
    await page.getByRole('button', { name: t.miljo }).first().click();
    await ventGrid(page);
    await page.setViewportSize(viewport);
    await ventGrid(page);
    if (trinn === 'kompetent') {
      await page.locator('.st-key-bs_trinn').getByText(t.kompetent, { exact: true }).click();
      await ventGrid(page);
    }

    // Stage count line, visible and inside the viewport.
    const telling = page.getByText(t.telling[trinn], { exact: true });
    await expect(telling).toBeVisible();
    const boks = await telling.boundingBox();
    expect(boks.x + boks.width).toBeLessThanOrEqual(viewport.width + 1);

    // 9 status lines (one per module with content at this stage), 11 cards.
    const linjer = await statusLinjer(page, lang);
    expect(linjer.length).toBe(9);
    if (trinn === 'foundation') {
      expect(linjer[0]).toBe(t.status[2]); // Råvarer worked through
      expect(linjer[6]).toBe(t.status[1]); // Gjæring in progress
      expect(linjer[3]).toBe(t.status[0]); // Mesking not started
    } else {
      expect(new Set(linjer)).toEqual(new Set([t.status[0]]));
      await expect(page.getByText(t.tips, { exact: true })).toBeVisible();
    }
    expect(await page.locator('.st-key-bs_skoleoversikt_grid [class*="st-key-bs_apne_modul_"] button').count()).toBe(11);

    // Status captions stay inside their card; no page overflow.
    const utenfor = await page.locator('.st-key-bs_skoleoversikt_grid [data-testid="stColumn"]').evaluateAll((cols) => cols
      .flatMap((col) => {
        const r = col.getBoundingClientRect();
        return [...col.querySelectorAll('[data-testid="stCaptionContainer"]')]
          .filter((c) => c.getBoundingClientRect().right > r.right + 1).map((c) => c.innerText);
      }));
    expect(utenfor).toEqual([]);
    await ingenOverflyt(page);
    expect(await page.evaluate(() => document.body.innerText.includes('%'))).toBe(false);
  });
}
