// Real Streamlit runtime coverage for the Bryggeskole learning-page layout
// (owner acceptance #508): the lesson text has a bounded reading measure on
// desktop, the Råvarer «Malt» page puts its text and the malt-roles visual
// side by side, and on a phone everything stacks with no horizontal scroll
// and a usable nav row. AppTest renders no CSS, so only a browser can show
// this. Measured geometry, not CSS strings, and no screenshot goldens.
//
// Runs against tests/fixtures/streamlit_harness/bryggeskole_wide_harness.py
// (the production panel call with app.py's layout="wide") on its own port,
// the second webServer of playwright.bryggeskole-grid.config.js.

const { test, expect } = require('@playwright/test');

const WIDE = 'http://127.0.0.1:8526/';
const SIDE = /Læringsside (\d+) av (\d+)/;

async function side(page) {
  const tekster = await page.locator('[data-testid="stCaptionContainer"]').allInnerTexts();
  const treff = tekster.map((t) => t.match(SIDE)).find(Boolean);
  return treff ? [Number(treff[1]), Number(treff[2])] : null;
}

async function ventPaSide(page, n, totalt) {
  await expect.poll(async () => JSON.stringify(await side(page)), { timeout: 15_000 }).toBe(JSON.stringify([n, totalt]));
  await page.waitForFunction(() => !document.querySelector('[data-stale="true"]'));
}

async function apneModul(page, modul) {
  await page.goto(WIDE);
  await page.waitForLoadState('networkidle');
  await page.locator('.st-key-bs_velg_hjemmebrygger_btn button').click();
  await page.locator(`.st-key-bs_apne_modul_${modul}_btn button`).click();
}

async function geometri(page) {
  return page.evaluate(() => {
    const rect = (el) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width };
    };
    const sideEl = document.querySelector('.st-key-bs_leksjon_side');
    const tekstP = sideEl && sideEl.querySelector('[class*="st-key-bs_leksjon_tekst_"] p');
    const tittel = sideEl && sideEl.querySelector('h3');
    const main = document.querySelector('[data-testid="stMainBlockContainer"]')
      || document.querySelector('section.main .block-container') || document.querySelector('.main');
    return {
      rem: parseFloat(getComputedStyle(document.documentElement).fontSize),
      side: rect(sideEl),
      main: rect(main),
      malt: rect(document.querySelector('.st-key-bs_leksjon_med_visual svg')),
      bred: rect(document.querySelector('.st-key-bs_leksjon_bred_visual svg')),
      // Smallest SVG font size as rendered: font-size in viewBox units
      // times the SVG's actual scale.
      bredMinFont: (() => {
        const svg = document.querySelector('.st-key-bs_leksjon_bred_visual svg');
        if (!svg) return null;
        const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
        return Math.min(...[...svg.querySelectorAll('text')].map((t) => parseFloat(t.getAttribute('font-size')))) * scale;
      })(),
      tekstFont: tekstP ? parseFloat(getComputedStyle(tekstP).fontSize) : null,
      tittelFont: tittel ? parseFloat(getComputedStyle(tittel).fontSize) : null,
      tittel: tittel ? tittel.innerText.trim() : null,
      hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
    };
  });
}

test.describe('Bryggeskole learning pages: width and composition (lang=no)', () => {
  test('desktop: bounded reading width, Malt text and visual side by side', async ({ page, viewport }) => {
    test.skip(viewport.width <= 480, 'desktop scenario');
    await apneModul(page, 'raavarer');
    await ventPaSide(page, 1, 4);

    let g = await geometri(page);
    expect(g.tittel).toBe('Malt');
    expect(g.side.width).toBeLessThanOrEqual(42 * g.rem + 1);
    expect(g.tekstFont).toBeCloseTo(1.2 * g.rem, 1);
    expect(g.tittelFont).toBeGreaterThan(g.tekstFont);
    // Side by side: the visual starts right of the text and shares its rows.
    expect(g.malt, 'the Malt visual is inside the text|visual row').not.toBeNull();
    expect(g.malt.left).toBeGreaterThanOrEqual(g.side.right - 1);
    expect(g.malt.top).toBeLessThan(g.side.bottom);
    expect(g.hscroll).toBe(false);
    // #508: the visual must be readable, not a thin side strip. Two equal
    // columns: at 1280px with the sidebar open it got 320px under the old
    // 3:2 split; now it takes about half of the row.
    expect(g.malt.width).toBeGreaterThanOrEqual(380);
    expect(g.malt.width).toBeGreaterThanOrEqual(0.9 * g.side.width);

    // On a wide desktop the visual scales up past the old 560px SVG cap
    // (it was 440px here before), while the text keeps its 42rem measure.
    await page.setViewportSize({ width: 1920, height: 1080 });
    await expect.poll(async () => (await geometri(page)).malt.width, { timeout: 10_000 }).toBeGreaterThanOrEqual(560);
    g = await geometri(page);
    expect(g.side.width).toBeLessThanOrEqual(42 * g.rem + 1);
    expect(g.malt.width).toBeLessThanOrEqual(42 * g.rem + 1);
    expect(g.malt.left).toBeGreaterThanOrEqual(g.side.right - 1);
    expect(g.malt.top).toBeLessThan(g.side.bottom);
    expect(g.hscroll).toBe(false);
    await page.setViewportSize(viewport);

    // A text-only page: the same measure, clearly narrower than the page.
    await page.locator('.st-key-bs_bolk_neste_raavarer_btn button').click();
    await ventPaSide(page, 2, 4);
    g = await geometri(page);
    expect(g.tittel).toBe('Humle');
    expect(g.side.width).toBeLessThanOrEqual(42 * g.rem + 1);
    expect(g.main.width).toBeGreaterThan(g.side.width + 100);
    expect(g.malt).toBeNull();
    expect(g.hscroll).toBe(false);
  });

  test('desktop: a wide process diagram stays full width below the text', async ({ page, viewport }) => {
    test.skip(viewport.width <= 480, 'desktop scenario');
    await apneModul(page, 'koking');
    await ventPaSide(page, 1, 2);
    const g = await geometri(page);
    expect(g.bred.top).toBeGreaterThanOrEqual(g.side.bottom - 1);
    expect(g.bred.width).toBeGreaterThan(g.side.width);
    expect(g.hscroll).toBe(false);
  });

  // #508: on a screen wider than a diagram's own max-width, the SVG used to
  // centre itself (inline margin:0 auto) and start 80-200px right of the
  // text. It must share the text's left edge, at its unchanged size.
  const BREDE = [['metodevalg', 3], ['koking', 2], ['kjoling', 4], ['pakking', 4]];
  for (const [modul, sider] of BREDE) {
    test(`wide desktop: the ${modul} diagram starts at the text's left edge`, async ({ page, viewport }) => {
      test.skip(viewport.width <= 480, 'desktop scenario');
      await page.setViewportSize({ width: 1920, height: 1080 });
      await apneModul(page, modul);
      await ventPaSide(page, 1, sider);
      const g = await geometri(page);
      expect(g.bred, 'the wide diagram is in its own aligned wrapper').not.toBeNull();
      expect(Math.abs(g.bred.left - g.side.left)).toBeLessThanOrEqual(4);
      expect(g.bred.top).toBeGreaterThanOrEqual(g.side.bottom - 1);
      expect(g.bred.width).toBeGreaterThan(g.side.width);
      expect(g.bred.right).toBeLessThanOrEqual(1920);
      expect(g.hscroll).toBe(false);
    });
  }

  // #508 refined: the wide figures read as thin panoramic strips (Koking
  // 3.7:1, Kjøling 3.2:1, Pakking 2.9:1) with tiny text at 1280-1440px.
  // Koking/Kjøling/Pakking were reflowed to <= 2.5:1 teaching figures;
  // Metode (2.3:1) kept its geometry. Bounded ratio, not one exact shape.
  for (const [modul, sider] of BREDE) {
    test(`desktop: the ${modul} figure is a proportionate teaching figure`, async ({ page, viewport }) => {
      test.skip(viewport.width <= 480, 'desktop scenario');
      await apneModul(page, modul);
      await ventPaSide(page, 1, sider);
      const g = await geometri(page);
      const ratio = g.bred.width / (g.bred.bottom - g.bred.top);
      expect(ratio, `${modul} aspect ratio`).toBeLessThanOrEqual(2.5);
      expect(ratio, `${modul} aspect ratio`).toBeGreaterThanOrEqual(1.5);
      expect(g.bred.top).toBeGreaterThanOrEqual(g.side.bottom - 1);
      expect(Math.abs(g.bred.left - g.side.left)).toBeLessThanOrEqual(4);
      expect(g.bred.right).toBeLessThanOrEqual(viewport.width);
      if (modul !== 'metodevalg') {
        // Before the reflow these rendered their smallest text at 9-10px here.
        expect(g.bredMinFont, `${modul} smallest figure text (px)`).toBeGreaterThanOrEqual(11);
      }
      expect(g.hscroll).toBe(false);
    });
  }

  test('mobile: a wide diagram fits the viewport below the text', async ({ page, viewport }) => {
    test.skip(viewport.width > 480, 'mobile scenario');
    await apneModul(page, 'metodevalg');
    await ventPaSide(page, 1, 3);
    const g = await geometri(page);
    expect(g.bred.top).toBeGreaterThanOrEqual(g.side.bottom - 1);
    expect(Math.abs(g.bred.left - g.side.left)).toBeLessThanOrEqual(4);
    expect(g.bred.right).toBeLessThanOrEqual(viewport.width + 1);
    expect(g.hscroll).toBe(false);
  });

  test('mobile: Malt stacks text then visual, no horizontal scroll, nav usable', async ({ page, viewport }) => {
    test.skip(viewport.width > 480, 'mobile scenario');
    await apneModul(page, 'raavarer');
    await ventPaSide(page, 1, 4);
    const g = await geometri(page);
    expect(g.hscroll).toBe(false);
    expect(g.side.right).toBeLessThanOrEqual(viewport.width + 1);
    expect(g.malt.top).toBeGreaterThanOrEqual(g.side.bottom - 1);
    expect(g.malt.right).toBeLessThanOrEqual(viewport.width + 1);
    const neste = page.locator('.st-key-bs_bolk_neste_raavarer_btn button');
    await neste.scrollIntoViewIfNeeded();
    const boks = await neste.boundingBox();
    expect(boks.height).toBeGreaterThanOrEqual(36);
    expect(boks.x + boks.width).toBeLessThanOrEqual(viewport.width + 1);
    await neste.click();
    await ventPaSide(page, 2, 4);
    expect((await geometri(page)).hscroll).toBe(false);
  });
});
