// Real Streamlit *runtime* browser regression coverage for the
// Bryggeskole lesson navigation buttons (issue #398 responsive
// follow-up, offline owner QA).
//
// The bug this catches: the lesson nav row is
// st.columns(_KNAPP_GRUPPE_KOLONNER) = (1, 1, 6), and Streamlit gives
// each column `width`/`flex: 1 1 calc(12.5% - 1rem)` -- one EIGHTH of
// the row. With the sidebar open at 641-1280px the row is narrow (440px
// at 900px), the button columns shrink to ~44px, and since the buttons
// have min-width 0 / white-space normal their labels wrap letter by
// letter: «← Forrige» 4 lines, «Neste →» 3, «▶️ Start spørsmål» 7. The
// fix sizes the button columns to their button (scoped
// `.st-key-bs_nav_actions` CSS in ui/bryggeskole_panel.py). Only a real
// browser layout can show this -- AppTest renders no CSS at all.
//
// Reproduced against the pre-fix source (stash-toggle) at 900/750px and
// confirmed fixed post-fix. Runs against
// tests/fixtures/streamlit_harness/bryggeskole_harness.py (the
// production render_bryggeskole_panel() call, with the same sidebar
// language picker as the app) via playwright.bryggeskole-grid.config.js.

const { test, expect } = require('@playwright/test');

const MODUL = 'rengjoring';
// Desktop/narrow widths from the QA report. At >= ~768px Streamlit keeps
// the sidebar open inline (the squeezed case); below it the sidebar
// auto-collapses.
const DESKTOP_BREDDER = [1280, 900, 750, 660];
const HOYDE = 900;
const BOLK = /Læringsbolk (\d+) av (\d+)/;

async function bolk(page) {
  const tekster = await page.locator('[data-testid="stCaptionContainer"]').allInnerTexts();
  const treff = tekster.map((t) => t.match(BOLK)).find(Boolean);
  return treff ? [Number(treff[1]), Number(treff[2])] : null;
}

async function ventPaBolk(page, n) {
  await expect.poll(async () => (await bolk(page) || [])[0], { timeout: 15_000 }).toBe(n);
}

// The block caption can update a moment before Streamlit swaps the nav
// row's stale button (e.g. «Neste →» -> «Start spørsmål» on the last
// block), so also wait until exactly the expected buttons are rendered
// and laid out.
async function ventPaNav(page, sisteBolk) {
  const forventet = sisteBolk ? `bs_start_sporsmal_${MODUL}_btn` : `bs_bolk_neste_${MODUL}_btn`;
  const annen = sisteBolk ? `bs_bolk_neste_${MODUL}_btn` : `bs_start_sporsmal_${MODUL}_btn`;
  await expect.poll(() => page.evaluate(([fv, an]) => {
    const knapper = [...document.querySelectorAll('.st-key-bs_nav_actions button')];
    const fvKnapp = document.querySelector(`.st-key-${fv} button`);
    return knapper.length === 2
      && !document.querySelector(`.st-key-${an}`)
      && !!fvKnapp && fvKnapp.getBoundingClientRect().width > 0
      && !document.querySelector('.st-key-bs_nav_actions [data-stale="true"]');
  }, [forventet, annen]), { timeout: 15_000 }).toBe(true);
}

async function apneLeksjon(page, viewport) {
  await page.setViewportSize(viewport);
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.locator('.st-key-bs_velg_hjemmebrygger_btn button').click();
  await page.locator(`.st-key-bs_apne_modul_${MODUL}_btn button`).click();
  await ventPaBolk(page, 1);
  const totalt = (await bolk(page))[1];
  await ventPaNav(page, totalt === 1);
  return totalt;
}

async function gaTilBolk(page, fra, til, totalt) {
  for (let n = fra; n < til; n += 1) {
    await page.locator(`.st-key-bs_bolk_neste_${MODUL}_btn button`).click();
    await ventPaBolk(page, n + 1);
    await ventPaNav(page, n + 1 === totalt);
  }
}

// Genuine rendered geometry per nav button: rendered line count (line
// tops of the label's own text rects), letter stacking (any word whose
// own characters span >1 line -- the reported bug), size and position.
// Not a CSS-string check. Tops are clustered with half a line-height of
// tolerance: an emoji glyph («▶️», «🔁») can sit a few px off the text
// baseline on the SAME line, which a plain distinct-top count would
// misread as a second line.
async function navKnapper(page) {
  return page.locator('.st-key-bs_nav_actions button').evaluateAll((knapper) => knapper.map((b) => {
    const p = b.querySelector('p') || b;
    const cs = getComputedStyle(p);
    const toleranse = (parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.5) / 2;
    const antallLinjer = (rects) => {
      const topper = [...rects].filter((r) => r.width > 0).map((r) => r.top).sort((a, c) => a - c);
      let linjer = 0;
      let forrige = -Infinity;
      for (const top of topper) {
        if (top - forrige > toleranse) linjer += 1;
        forrige = top;
      }
      return linjer;
    };
    const alleRects = [];
    const brutteOrd = [];
    const walker = document.createTreeWalker(b, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      const hele = document.createRange();
      hele.selectNodeContents(node);
      alleRects.push(...hele.getClientRects());
      const ordRe = /\S+/g;
      let m;
      while ((m = ordRe.exec(node.textContent))) {
        const range = document.createRange();
        range.setStart(node, m.index);
        range.setEnd(node, m.index + m[0].length);
        if (antallLinjer(range.getClientRects()) > 1) brutteOrd.push(m[0]);
      }
    }
    const r = b.getBoundingClientRect();
    return {
      tekst: b.innerText.trim(),
      linjer: antallLinjer(alleRects),
      brutteOrd,
      disabled: b.disabled,
      synlig: r.width > 0 && r.height > 0,
      w: Math.round(r.width),
      h: Math.round(r.height),
      top: Math.round(r.top),
      left: Math.round(r.left),
    };
  }));
}

async function harHorisontalScroll(page) {
  return page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2);
}

function forventLesbar(knapper, kontekst) {
  expect(knapper.length, `${kontekst}: expected two nav buttons`).toBe(2);
  for (const k of knapper) {
    const hvor = `${kontekst} «${k.tekst}» ${JSON.stringify(k)}`;
    expect(k.synlig, hvor).toBe(true);
    expect(k.brutteOrd, `${hvor}: letter-stacked words`).toEqual([]);
    expect(k.linjer, `${hvor}: label should render on one line`).toBe(1);
  }
}

async function sjekkLeksjon(page, viewport, kontekst) {
  const totalt = await apneLeksjon(page, viewport);
  expect(totalt).toBeGreaterThanOrEqual(3);
  const midt = Math.ceil(totalt / 2);

  // Block 1: Prev disabled but readable, Next usable.
  let knapper = await navKnapper(page);
  forventLesbar(knapper, `${kontekst} block 1`);
  expect(knapper[0].disabled).toBe(true);
  expect(knapper[1].disabled).toBe(false);
  expect(await harHorisontalScroll(page)).toBe(false);

  // Middle block: Prev + Next both enabled and clickable.
  await gaTilBolk(page, 1, midt, totalt);
  knapper = await navKnapper(page);
  forventLesbar(knapper, `${kontekst} block ${midt}`);
  expect(knapper.map((k) => k.disabled)).toEqual([false, false]);
  expect(await harHorisontalScroll(page)).toBe(false);
  await page.locator(`.st-key-bs_bolk_forrige_${MODUL}_btn button`).click();
  await ventPaBolk(page, midt - 1);
  await ventPaNav(page, false);
  await gaTilBolk(page, midt - 1, midt, totalt);

  // Last block: Prev + Start spørsmål.
  await gaTilBolk(page, midt, totalt, totalt);
  knapper = await navKnapper(page);
  forventLesbar(knapper, `${kontekst} block ${totalt}`);
  expect(knapper[1].tekst).toContain('Start spørsmål');
  expect(knapper.map((k) => k.disabled)).toEqual([false, false]);
  expect(await harHorisontalScroll(page)).toBe(false);
  return knapper;
}

test.describe('Bryggeskole lesson nav buttons (lang=no)', () => {
  for (const bredde of DESKTOP_BREDDER) {
    test(`${bredde}px: Forrige/Neste/Start spørsmål on one line, no letter stacking, no h-scroll`, async ({ page, viewport }) => {
      test.skip(viewport.width <= 480, 'desktop/narrow widths only run in the desktop projects');
      const knapper = await sjekkLeksjon(page, { width: bredde, height: HOYDE }, `${bredde}px`);
      // Side by side and compact, not stretched across the row.
      expect(knapper[0].top).toBe(knapper[1].top);
      for (const k of knapper) expect(k.w, JSON.stringify(k)).toBeLessThan(bredde / 2);
    });
  }

  test('mobile: buttons keep the stacked layout, sensible touch targets, no h-scroll', async ({ page, viewport }) => {
    test.skip(viewport.width > 480, 'this scenario only applies to the mobile-width projects');
    const knapper = await sjekkLeksjon(page, viewport, `mobile ${viewport.width}px`);
    expect(knapper[1].top, JSON.stringify(knapper)).toBeGreaterThan(knapper[0].top);
    expect(knapper[0].left).toBe(knapper[1].left);
    for (const k of knapper) {
      expect(k.h, JSON.stringify(k)).toBeGreaterThanOrEqual(36);
      expect(k.w, JSON.stringify(k)).toBeGreaterThanOrEqual(44);
    }
  });
});
