// Real Streamlit *runtime* browser regression coverage for the contrast
// of LOCKED quiz answer options after «Sjekk svar» (issues #401, #482).
//
// The bug this catches: after answering, st.radio(..., disabled=True)
// locks the options and Streamlit's own disabled styling dims the answer
// text to rgba(<text colour>, 0.4) -- about 2.2-2.6:1 on the light theme.
// Where the dimmed colour sits differs between Streamlit versions (#482:
// 1.65 dims a new wrapper div between stRadioGroup and the option
// labels), so the CSS-string/AppTest tests in
// tests/test_ui_bryggeskole_panel.py can pass while a real browser still
// shows the dimmed text. Only the browser's own computed style can tell,
// which is what this spec measures.
//
// Deliberately DOM-version-agnostic: it finds options via the ARIA
// `[role="radiogroup"] label` structure and the native `<input
// type="radio">`, never Streamlit's testids or emotion hash classes.
//
// Runs via playwright.bryggeskole-quiz-contrast.config.js (isolated
// mastery-state temp dir, light + dark colour scheme).

const { test, expect } = require('@playwright/test');

// WCAG 2.x AA for normal-size text (answer text is ~17.6px regular, not
// "large text"). Disabled controls are formally exempt from 1.4.3, but
// the owner requirement for #401 is that locked answers stay readable --
// the answer status itself is shown separately as text (#338), so the
// locked radio has no reason to be dimmed below normal-text contrast.
const MIN_KONTRAST = 4.5;

const SVARALTERNATIV = '.st-key-bs_svaralternativ [role="radiogroup"]';

async function klikk(page, key) {
  await page.locator(`.st-key-${key} button`).first().click();
  await page.waitForTimeout(700);
}

async function gaaTilForsteMeskingSporsmal(page) {
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await klikk(page, 'bs_velg_hjemmebrygger_btn');
  await klikk(page, 'bs_apne_modul_mesking_btn');
  while (await page.locator('.st-key-bs_bolk_neste_mesking_btn button').count()) {
    await klikk(page, 'bs_bolk_neste_mesking_btn');
  }
  await klikk(page, 'bs_start_sporsmal_mesking_btn');
  await expect(page.locator(`${SVARALTERNATIV} label`).first()).toBeVisible();
}

// For each answer option: the computed colour of the answer text itself,
// the effective background behind it (first opaque ancestor background,
// with any translucent layers above it composited in), and the WCAG
// contrast ratio after compositing the text's own alpha over that
// background -- i.e. what the user actually sees, not what a CSS rule says.
async function malKontrast(page) {
  return page.locator(`${SVARALTERNATIV} label`).evaluateAll((labels) => {
    const parse = (c) => {
      const m = c.match(/rgba?\(([^)]+)\)/);
      if (!m) return null;
      const [r, g, b, a] = m[1].split(/[ ,/]+/).filter(Boolean).map(Number);
      return { r, g, b, a: a === undefined ? 1 : a };
    };
    const over = (top, bottom) => ({
      r: top.r * top.a + bottom.r * (1 - top.a),
      g: top.g * top.a + bottom.g * (1 - top.a),
      b: top.b * top.a + bottom.b * (1 - top.a),
      a: 1,
    });
    const effektivBakgrunn = (el) => {
      const lag = [];
      for (let n = el; n; n = n.parentElement) {
        const bg = parse(getComputedStyle(n).backgroundColor);
        if (bg && bg.a > 0) {
          lag.push(bg);
          if (bg.a >= 1) break;
        }
      }
      let resultat = { r: 255, g: 255, b: 255, a: 1 }; // canvas default
      for (const l of lag.reverse()) resultat = over(l, resultat);
      return resultat;
    };
    const luminans = ({ r, g, b }) => {
      const lin = (v) => {
        const s = v / 255;
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
    };
    return labels.map((label) => {
      const p = label.querySelector('p');
      const tekstFarge = getComputedStyle(p).color;
      const bakgrunn = effektivBakgrunn(p);
      const tekst = over(parse(tekstFarge), bakgrunn);
      const [l1, l2] = [luminans(tekst), luminans(bakgrunn)].sort((x, y) => y - x);
      return {
        tekst: p.textContent.slice(0, 40),
        tekstFarge,
        // Product of opacity along the whole ancestor chain: any of them
        // would dim the text without changing its computed `color`.
        opacity: (() => {
          let o = 1;
          for (let n = p; n; n = n.parentElement) o *= Number(getComputedStyle(n).opacity);
          return o;
        })(),
        bakgrunn: `rgb(${bakgrunn.r}, ${bakgrunn.g}, ${bakgrunn.b})`,
        kontrast: Math.round(((l1 + 0.05) / (l2 + 0.05)) * 100) / 100,
        inputDisabled: label.querySelector('input[type="radio"]').disabled,
      };
    });
  });
}

test('locked quiz answers keep >= 4.5:1 text contrast after «Sjekk svar»', async ({ page }) => {
  await gaaTilForsteMeskingSporsmal(page);

  const for_ = await malKontrast(page);
  expect(for_.length).toBeGreaterThanOrEqual(2);
  for (const o of for_) {
    expect(o.inputDisabled, `before answering, option "${o.tekst}" must be enabled`).toBe(false);
  }

  await page.locator(`${SVARALTERNATIV} label`).nth(1).click();
  await page.locator('.st-key-bs_svar_btn_mesking_r1_q0 button').click();
  // Answer state is rendered once the «Fortsett» button replaces «Sjekk svar».
  await expect(page.locator('.st-key-bs_fortsett_btn_mesking_r1_q0 button')).toBeVisible();

  const etter = await malKontrast(page);
  expect(etter).toHaveLength(for_.length);
  for (const o of etter) {
    // The lock itself must survive the contrast fix.
    expect(o.inputDisabled, `after answering, option "${o.tekst}" must stay disabled`).toBe(true);
    expect(o.opacity, `option "${o.tekst}" cumulative opacity`).toBe(1);
    expect(
      o.kontrast,
      `option "${o.tekst}": text ${o.tekstFarge} on ${o.bakgrunn} = ${o.kontrast}:1`,
    ).toBeGreaterThanOrEqual(MIN_KONTRAST);
  }
});
