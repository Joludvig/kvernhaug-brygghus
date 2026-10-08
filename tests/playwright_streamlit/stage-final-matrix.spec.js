// Stage UI S5 final browser matrix (docs/development/v22_course_stage_ui_contract.md
// §3-§12, §15; offline, no GitHub issue yet). The real-runtime counterpart of
// tests/test_ui_bryggeskole_stage_final_qa.py: AppTest renders no CSS, so
// wrapping, clipping and overflow can only be measured here.
//
// Full Cartesian matrix per browser: {NO, EN} x {Hjemmebrygger, Bryggeri} x
// {Foundation, Kompetent} = 8 tests, each at 1280 / 900 / 750 / 390 px.
// At every width:
// - overview: selector visible and inside the viewport, the environment
//   switch above it, exactly 11 cards in canonical order, every card text,
//   status caption, stage count, guidance and «Anbefalt neste» line inside
//   its box and unclipped, no word broken across lines, no page overflow;
// - the stage's special card action (Kompetent-only «Se Trinn 2-innholdet»
//   under Foundation; Foundation-only «Repeter» under Kompetent), then back;
// - one short lesson walked to the summary: breadcrumb, lesson text, quiz
//   options, disabled «Sjekk svar» (contrast measured), feedback, «Prøv
//   igjen», summary -- all unclipped, no overflow.
// Plus one sidebar test per browser: overview with the sidebar expanded and
// collapsed at every width.
//
// Learner history goes to the web server's KVERNHAUG_BRYGGESKOLE_STATE_DIR,
// which must be an isolated directory:
//   KVERNHAUG_BRYGGESKOLE_STATE_DIR=<tmp> npx playwright test \
//     -c playwright.bryggeskole-grid.config.js stage-final-matrix \
//     --project=chromium-desktop --project=firefox-desktop

const { test, expect } = require('@playwright/test');

test.use({ actionTimeout: 20_000 });

const BREDDER = [1280, 900, 750, 390];
const HOYDE = 900;
const KORT = ['raavarer', 'rengjoring', 'metodevalg', 'mesking', 'koking', 'kjoling', 'gjaring', 'pakking',
  'maaling', 'oppskrift', 'smak'];
// The shortest lesson per stage (1 block; 1 and 3 questions).
const KORT_LEKSJON = { foundation: 'mesking', kompetent: 'koking' };

const TEKST = {
  no: {
    foundation: 'Trinn 1 · Foundation',
    kompetent: 'Trinn 2 · Kompetent hjemmebrygger',
    sti: { foundation: 'Trinn 1 · Foundation', kompetent: 'Trinn 2 · Kompetent' },
    miljo: { hjemmebrygger: '🏠 Hjemmebrygger', bryggeri: '🏭 Bryggeri' },
    telling: /^\d+ av 9 moduler gjennomgått$/,
    status: ['Ikke startet', 'Påbegynt', 'Gjennomgått'],
    spesial: { foundation: 'Hører til Trinn 2', kompetent: 'Bygger på Foundation – ingen egen Trinn 2-del' },
    tips: 'Tips: Du har fortsatt noen Foundation-deler du kan gå tilbake til.',
    oppsummering: '🌱 Slik ligger du an',
    legacy: 'Leksjon tilgjengelig',
  },
  en: {
    foundation: 'Stage 1 · Foundation',
    kompetent: 'Stage 2 · Competent homebrewer',
    sti: { foundation: 'Stage 1 · Foundation', kompetent: 'Stage 2 · Competent homebrewer' },
    miljo: { hjemmebrygger: '🏠 Homebrewer', bryggeri: '🏭 Brewery' },
    telling: /^\d+ of 9 modules worked through$/,
    status: ['Not started', 'In progress', 'Worked through'],
    spesial: { foundation: 'Belongs to Stage 2', kompetent: 'Builds on Foundation – no separate Stage 2 section' },
    tips: 'Tip: You still have some Foundation sections you can revisit.',
    oppsummering: '🌱 Where you stand',
    legacy: 'Lesson available',
  },
};

// ---- waiting ---------------------------------------------------------------

async function vent(page) {
  await page.waitForFunction(() => !document.querySelector('[data-stale="true"]')
    && !document.querySelector('[data-testid="stStatusWidget"]'), null, { timeout: 20_000 });
  await page.waitForTimeout(250);
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

async function ventPaKey(page, key) {
  await page.waitForFunction((k) => {
    const el = document.querySelector(`.st-key-${k} button`);
    return !!el && el.getBoundingClientRect().width > 0 && !document.querySelector('[data-stale="true"]');
  }, key, { timeout: 20_000 });
  await vent(page);
}

async function klikkKey(page, key) {
  await page.locator(`.st-key-${key} button`).click();
}

// ---- measuring -------------------------------------------------------------

// Every visible text-bearing element in the main area: its box must lie in
// the viewport, its content must not be clipped (scrollWidth), and no word
// may be broken across lines (the letter-stacking failure mode).
async function malTekst(page) {
  return page.evaluate(() => {
    const main = document.querySelector('[data-testid="stMain"]') || document.querySelector('section.main') || document.body;
    const vw = document.documentElement.clientWidth;
    const sel = ['[data-testid="stCaptionContainer"]', '[data-testid="stMarkdownContainer"]', '[data-testid="stAlert"]',
      'button', '[data-testid="stRadio"] label', '[data-testid="stHeading"]'].join(',');
    const funn = [];
    const lineCount = (rects, tol) => {
      const tops = [...rects].filter((r) => r.width > 0).map((r) => r.top).sort((a, b) => a - b);
      let n = 0; let prev = -Infinity;
      for (const top of tops) { if (top - prev > tol) n += 1; prev = top; }
      return n;
    };
    for (const el of main.querySelectorAll(sel)) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0 || el.closest('svg')) continue;
      const tekst = (el.innerText || '').trim().slice(0, 60);
      if (!tekst) continue;
      if (r.left < -1 || r.right > vw + 1) funn.push(`outside viewport: «${tekst}» [${Math.round(r.left)}, ${Math.round(r.right)}] vw=${vw}`);
      const cs = getComputedStyle(el);
      if (cs.overflowX !== 'visible' && el.scrollWidth > el.clientWidth + 2 && !el.querySelector('svg, table')) {
        funn.push(`clipped: «${tekst}» scroll=${el.scrollWidth} client=${el.clientWidth}`);
      }
      if (el.matches('button, [data-testid="stRadio"] label, [data-testid="stCaptionContainer"]')) {
        const tol = (parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.5) / 2;
        const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          // Hyphens and slashes are legitimate break points («ikke-kokende»);
          // only a break INSIDE a run of letters is letter stacking.
          const re = /[^\s\-–/]{2,}/g; let m;
          while ((m = re.exec(node.textContent))) {
            const range = document.createRange();
            range.setStart(node, m.index); range.setEnd(node, m.index + m[0].length);
            if (lineCount(range.getClientRects(), tol) > 1) funn.push(`broken word: «${m[0]}» in «${tekst}»`);
          }
        }
      }
    }
    const d = document.documentElement;
    if (d.scrollWidth > d.clientWidth + 1) funn.push(`horizontal overflow: ${d.scrollWidth} > ${d.clientWidth}`);
    return funn;
  });
}

async function forventLesbar(page, kontekst) {
  expect(await malTekst(page), kontekst).toEqual([]);
}

// WCAG contrast of a button's text against the nearest opaque background.
async function kontrast(page, selector) {
  return page.locator(selector).first().evaluate((el) => {
    const rgb = (s) => (s.match(/[\d.]+/g) || []).map(Number);
    const lum = ([r, g, b]) => {
      const f = (c) => { const v = c / 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const tekstEl = el.querySelector('p') || el;
    let farge = rgb(getComputedStyle(tekstEl).color);
    let bg = null;
    for (let n = el; n; n = n.parentElement) {
      const c = rgb(getComputedStyle(n).backgroundColor);
      if (c.length >= 3 && (c.length < 4 || c[3] > 0.5)) { bg = c; break; }
    }
    bg = bg || [255, 255, 255];
    const opasitet = parseFloat(getComputedStyle(el).opacity) || 1;
    if (farge.length === 4) farge = farge.slice(0, 3).map((c, i) => c * farge[3] + bg[i] * (1 - farge[3]));
    farge = farge.slice(0, 3).map((c, i) => c * opasitet + bg[i] * (1 - opasitet));
    const [a, b] = [lum(farge), lum(bg.slice(0, 3))].sort((x, y) => y - x);
    return Math.round(((a + 0.05) / (b + 0.05)) * 100) / 100;
  });
}

// ---- navigation ------------------------------------------------------------

async function start(page, lang, miljo) {
  await page.setViewportSize({ width: 1280, height: HOYDE });
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  if (lang === 'en') {
    await page.getByText('English').first().click();
    await vent(page);
  }
  await klikkKey(page, `bs_velg_${miljo}_btn`);
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

async function tilbake(page) {
  await page.locator('[class*="st-key-bs_tilbake_"] button').first().click();
  await ventGrid(page);
}

// ---- checks ----------------------------------------------------------------

async function sjekkOversikt(page, lang, trinn, kontekst) {
  const t = TEKST[lang];
  const velger = page.locator('.st-key-bs_trinn');
  await expect(velger, kontekst).toBeVisible();
  await expect(velger.getByText(t.foundation, { exact: true })).toBeVisible();
  await expect(velger.getByText(t.kompetent, { exact: true })).toBeVisible();
  expect(await valgtTrinn(page), kontekst).toBe(t[trinn]);
  // The environment switch stays its own control, above the stage selector.
  const bytt = await page.locator('.st-key-bs_bytt_miljo_btn button').boundingBox();
  expect(bytt.y + bytt.height, kontekst).toBeLessThanOrEqual((await velger.boundingBox()).y);

  const nokler = await page.locator('.st-key-bs_skoleoversikt_grid [class*="st-key-bs_apne_modul_"]').evaluateAll(
    (els) => els.map((e) => [...e.classList].find((c) => c.startsWith('st-key-bs_apne_modul_'))),
  );
  expect(nokler, kontekst).toEqual(KORT.map((m) => `st-key-bs_apne_modul_${m}_btn`));
  expect(await page.locator('.st-key-bs_skoleoversikt_grid button:disabled').count(), kontekst).toBe(0);

  const captions = (await page.locator('[data-testid="stCaptionContainer"]').allInnerTexts()).map((s) => s.trim());
  expect(captions.filter((c) => t.telling.test(c)).length, `${kontekst}: stage count`).toBe(1);
  expect(captions.filter((c) => t.status.includes(c)).length, `${kontekst}: status lines`).toBe(9);
  expect(captions.filter((c) => c === t.spesial[trinn]).length, `${kontekst}: special lines`).toBe(2);
  expect(captions.some((c) => c.includes(t.legacy)), `${kontekst}: legacy badge`).toBe(false);
  if (trinn === 'kompetent') expect(captions, `${kontekst}: tip`).toContain(t.tips);
  await expect(page.locator('[data-testid="stAlert"]').first(), `${kontekst}: recommended next`).toBeVisible();

  // Card captions and buttons stay inside their own card.
  const utenfor = await page.locator('.st-key-bs_skoleoversikt_grid [data-testid="stColumn"]').evaluateAll((cols) => cols
    .flatMap((col) => {
      const r = col.getBoundingClientRect();
      return [...col.querySelectorAll('[data-testid="stCaptionContainer"], button, [data-testid="stMarkdownContainer"]')]
        .filter((c) => c.getBoundingClientRect().right > r.right + 1 || c.getBoundingClientRect().left < r.left - 1)
        .map((c) => c.innerText);
    }));
  expect(utenfor, kontekst).toEqual([]);
  // Card buttons: usable, not giant (one or two text lines).
  const hoyder = await page.locator('.st-key-bs_skoleoversikt_grid button').evaluateAll(
    (bs) => bs.map((b) => Math.round(b.getBoundingClientRect().height)),
  );
  expect(Math.max(...hoyder), `${kontekst}: card button height ${hoyder}`).toBeLessThanOrEqual(80);
  await forventLesbar(page, `${kontekst}: overview`);
}

async function sjekkSpesialkort(page, lang, trinn, kontekst) {
  const t = TEKST[lang];
  if (trinn === 'foundation') {
    await klikkKey(page, 'bs_apne_modul_oppskrift_btn');
    await ventPaKey(page, 'bs_tilbake_oppskrift_k_btn');
    expect(await sti(page), kontekst).toContain(t.sti.kompetent);
    await forventLesbar(page, `${kontekst}: Kompetent-only lesson`);
    await tilbake(page);
    expect(await valgtTrinn(page), kontekst).toBe(t.kompetent);
    await velgTrinn(page, lang, 'foundation'); // back to the combination under test
  } else {
    await klikkKey(page, 'bs_apne_modul_rengjoring_btn');
    await ventPaKey(page, 'bs_tilbake_rengjoring_btn');
    expect(await sti(page), kontekst).toContain(t.sti.foundation);
    await forventLesbar(page, `${kontekst}: Foundation review lesson`);
    await tilbake(page);
    expect(await valgtTrinn(page), kontekst).toBe(t.kompetent);
  }
}

async function gaGjennomLeksjon(page, lang, miljo, trinn, kontekst) {
  const t = TEKST[lang];
  const modul = KORT_LEKSJON[trinn];
  const base = modul + (trinn === 'kompetent' ? '_k' : '');
  await klikkKey(page, `bs_apne_modul_${modul}_btn`);
  await ventPaKey(page, `bs_tilbake_${base}_btn`);
  const brodsmule = await sti(page);
  expect(brodsmule, kontekst).toContain(t.miljo[miljo]);
  expect(brodsmule, kontekst).toContain(t.sti[trinn]);
  await forventLesbar(page, `${kontekst}: lesson`);

  // The card may reopen a finished session at its summary (state is shared
  // by the server); retry from there, otherwise start the questions.
  if (await page.locator(`.st-key-bs_prov_igjen_${base}_btn`).count()) {
    await klikkKey(page, `bs_prov_igjen_${base}_btn`);
  } else {
    if (!(await page.locator(`.st-key-bs_start_sporsmal_${base}_btn`).count())) {
      await klikkKey(page, `bs_bolk_neste_${base}_btn`); // never reached with 1-block lessons
    }
    await ventPaKey(page, `bs_start_sporsmal_${base}_btn`);
    await klikkKey(page, `bs_start_sporsmal_${base}_btn`);
  }

  for (let q = 0; q < 10; q += 1) {
    const svar = page.locator(`[class*="st-key-bs_svar_btn_${base}_r"] button`);
    await expect(svar, `${kontekst}: question ${q}`).toBeVisible({ timeout: 20_000 });
    await vent(page);
    await expect(svar).toBeDisabled();
    if (q === 0) {
      // Streamlit's own disabled-button styling (unchanged since PR #328; an
      // inactive control, exempt under WCAG 1.4.3). Baseline only: ~2.2:1.
      const k = await kontrast(page, `[class*="st-key-bs_svar_btn_${base}_r"] button`);
      expect(k, `${kontekst}: disabled «Sjekk svar» contrast`).toBeGreaterThanOrEqual(2);
    }
    const valg = page.locator('.st-key-bs_svaralternativ label:has(input[type="radio"])');
    expect(await valg.count(), kontekst).toBeGreaterThanOrEqual(2);
    await forventLesbar(page, `${kontekst}: question ${q}`);
    await valg.first().click();
    await expect(svar).toBeEnabled();
    await svar.click();
    const fortsett = page.locator(`[class*="st-key-bs_fortsett_btn_${base}_r"] button`);
    await expect(fortsett).toBeVisible({ timeout: 20_000 });
    await vent(page);
    await expect(page.locator('[data-testid="stAlert"]').last()).toBeVisible();
    // The answered (disabled) options are text the learner reads: issue #401
    // keeps them at full contrast.
    const besvart = await kontrast(page, '.st-key-bs_svaralternativ label:has(input[type="radio"]) p');
    expect(besvart, `${kontekst}: answered option contrast`).toBeGreaterThanOrEqual(4.5);
    await forventLesbar(page, `${kontekst}: feedback ${q}`);
    await fortsett.click();
    await vent(page);
    if (await page.locator(`.st-key-bs_prov_igjen_${base}_btn`).count()) break;
  }
  await ventPaKey(page, `bs_prov_igjen_${base}_btn`);
  await expect(page.getByText(t.oppsummering, { exact: true })).toBeVisible();
  await forventLesbar(page, `${kontekst}: summary`);
  await klikkKey(page, `bs_oppsummering_tilbake_${base}_btn`);
  await ventGrid(page);
  expect(await valgtTrinn(page), kontekst).toBe(t[trinn]);
}

// ---- the matrix ------------------------------------------------------------

for (const lang of ['no', 'en']) {
  for (const miljo of ['hjemmebrygger', 'bryggeri']) {
    for (const trinn of ['foundation', 'kompetent']) {
      test(`stage final matrix: ${lang} ${miljo} ${trinn}`, async ({ page }, testInfo) => {
        test.setTimeout(420_000);
        await start(page, lang, miljo);
        if (trinn === 'kompetent') await velgTrinn(page, lang, 'kompetent');
        for (const bredde of BREDDER) {
          const kontekst = `${testInfo.project.name} ${lang} ${miljo} ${trinn} ${bredde}px`;
          await page.setViewportSize({ width: bredde, height: HOYDE });
          await ventGrid(page);
          await sjekkOversikt(page, lang, trinn, kontekst);
          await sjekkSpesialkort(page, lang, trinn, kontekst);
          await gaGjennomLeksjon(page, lang, miljo, trinn, kontekst);
          await sjekkOversikt(page, lang, trinn, `${kontekst} (after lesson)`);
        }
      });
    }
  }
}

// ---- sidebar expanded / collapsed -----------------------------------------

async function sidebarApen(page) {
  return page.evaluate(() => {
    const sb = document.querySelector('[data-testid="stSidebar"]');
    if (!sb) return false;
    const r = sb.getBoundingClientRect();
    return sb.getAttribute('aria-expanded') !== 'false' && r.right > 10 && r.width > 50;
  });
}

async function settSidebar(page, apen) {
  if ((await sidebarApen(page)) === apen) return;
  if (apen) {
    await page.locator('[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button').first().click();
  } else {
    await page.locator('[data-testid="stSidebar"]').hover();
    await page.locator('[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapseButton"]').first().click();
  }
  await expect.poll(() => sidebarApen(page), { timeout: 10_000 }).toBe(apen);
  await page.waitForTimeout(500);
}

test('stage final matrix: sidebar expanded and collapsed', async ({ page }, testInfo) => {
  test.setTimeout(240_000);
  await start(page, 'en', 'hjemmebrygger');
  await velgTrinn(page, 'en', 'kompetent');
  for (const bredde of BREDDER) {
    await page.setViewportSize({ width: bredde, height: HOYDE });
    await ventGrid(page);
    for (const apen of [true, false]) {
      const kontekst = `${testInfo.project.name} sidebar ${apen ? 'expanded' : 'collapsed'} ${bredde}px`;
      await settSidebar(page, apen);
      await ventGrid(page);
      await sjekkOversikt(page, 'en', 'kompetent', kontekst);
      if (apen && bredde <= 750) {
        // Overlay sidebar: the language picker stays reachable.
        await expect(page.locator('[data-testid="stSidebar"]').getByText('English').first()).toBeVisible();
      }
    }
  }
});
