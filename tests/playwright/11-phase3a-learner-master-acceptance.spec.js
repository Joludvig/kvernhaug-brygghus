'use strict';

// Issue #250 (Roadmap #101 Phase 3A) -- automated acceptance proof for the
// Learner/Master ("Bryggelaerling"/"Bryggmester") contract on the current
// Web recipe builder. This is ACCEPTANCE evidence, not new coverage of a
// freshly built feature: web/js/app.js::settModus() (see 04-mode-
// preservation.spec.js) and the first-visit dialog (02-mode-dialog.spec.js)
// are already covered -- this spec proves the FULLER Phase 3A contract on
// top of that: a full L->M->L->M cycle (not just one L->M->L round trip),
// an explicit Master-only advanced-control witness whose produced value
// must survive the cycle, the Learner guidance surface actually rendering
// real, non-stale, non-raw-key text tied to the live recipe (not merely a
// toggle), save/draft-state orientation, and a bounded step into the brew
// loop (start-brygging) without mutating the brew lifecycle any further.
//
// Deliberately scoped OUT (see docs/development/
// phase3a_learner_master_acceptance.md "Contract results" for the
// reasoning): forcing the per-field "tydelig avvik" deviation-tips branch
// in web/js/veiledning.js (the one branch whose *wording* differs between
// modes, e.g. "eller hoyere brygghuseffektivitet") is not attempted here --
// it would require a contrived recipe engineered against a specific BJCP
// style's numeric range purely to make automation possible, which the
// issue explicitly disallows ("do not invent controls or data simply to
// make automation easier"). That branch was instead verified by source
// read (quoted in the acceptance doc) and is flagged there as a residual,
// honestly-scoped gap for the human novice gate / a future issue to widen.

const { test, expect } = require('@playwright/test');
const {
  localePath, collectErrors, dismissModeDialog, openSideDrawer, closeSideDrawer,
} = require('./helpers');

const RECIPE_NAVN = 'KBH 3A Acceptance';
const BATCH_VOLUM = '20';
const RAW_I18N_KEY_RE = /^[a-z][a-z0-9]*(\.[a-zA-Z0-9]+)+$/;

async function velgFraCombobox(page, radSelector, sokeTekst, valgTekst) {
  const rad = page.locator(radSelector).first();
  const input = rad.locator('.combobox-input');
  await input.click();
  await input.fill(sokeTekst);
  await rad.locator('.combobox-option', { hasText: valgTekst }).first().click();
}

async function byttModusViaSidemeny(page, modus) {
  await openSideDrawer(page);
  await page.locator(`.sidemeny-modus-knapp[data-modus="${modus}"]`).click();
  await expect(page.locator('body')).toHaveClass(new RegExp(`modus-${modus}`));
  await closeSideDrawer(page);
}

async function byggOppskrift(page) {
  await page.fill('#oppskrift-navn', RECIPE_NAVN);
  await expect(page.locator('#batch-volum')).toHaveValue(BATCH_VOLUM);
  await page.fill('#batch-volum', BATCH_VOLUM);
  await velgFraCombobox(page, '#malt-rader .ingrediens-rad', 'Weyermann', 'Pilsner Malt');
  await page.fill('#malt-rader .malt-mengde', '5');
  await velgFraCombobox(page, '#humle-rader .ingrediens-rad', 'Cascade', 'Cascade');
  await velgFraCombobox(page, '#gjaer-panel', 'Fermentis', 'SafAle US-05');
}

test.describe('Phase 3A (#250) -- Learner/Master representative task', () => {
  test('open, build recipe, Learner guidance, Master control, L-M-L-M persistence, save, start brewing (NO)', async ({ page }) => {
    const errors = collectErrors(page);

    // 1. open/start recipe work, in Learner (Bryggelaerling) mode
    await page.goto(localePath('no', '/index.html'));
    await dismissModeDialog(page, 'laerling');
    await expect(page.locator('body')).toHaveClass(/modus-laerling/);

    // Master-only witnesses that must be invisible/unreachable in Learner.
    const maltPct = page.locator('#malt-rader .malt-pct').first();
    const humleIbuRad = page.locator('#humle-rader .humle-maal-ibu-rad').first();
    const skalerRad = page.locator('#skaler-rad');
    const naerliggendeStiler = page.locator('.stil-alternativer');
    const manuellResultat = page.locator('#stil-manuell-resultat');
    await expect(maltPct).toBeHidden();
    await expect(humleIbuRad).toBeHidden();
    await expect(skalerRad).toBeHidden();
    await expect(naerliggendeStiler).toBeHidden();
    await expect(manuellResultat).toBeHidden();

    // 2-6. establish name, batch volume, at least one malt/hop/yeast
    await byggOppskrift(page);

    // 7. observe the main calculated outputs already exposed by the product
    await expect(page.locator('#res-og')).not.toHaveText('1.000');
    await expect(page.locator('#res-fg')).not.toHaveText('1.000');
    await expect(page.locator('#res-ibu')).not.toHaveText('0');
    await expect(page.locator('#res-ebc')).not.toHaveText('0');
    await expect(page.locator('#res-abv')).not.toHaveText('0,0 %');

    // Learner acceptance: the auto style-match guidance is genuine
    // progressive disclosure (a collapsed <details>/<summary>, not hidden
    // by mode) -- open it explicitly before asserting its content.
    await page.locator('#stilanalyse-panel > summary').click();
    await expect(page.locator('#stilanalyse-panel')).toHaveJSProperty('open', true);

    // The auto style-match guidance panel is REAL instruction tied to this
    // exact recipe, not merely a mode toggle -- non-empty, not a raw/
    // missing i18n key, and not referencing Master-only vocabulary while
    // the Master-only controls above are hidden.
    await expect(page.locator('#stil-tom-tilstand')).toBeHidden();
    await expect(page.locator('#stil-auto-innhold')).toBeVisible();
    const stilNavnLearner = (await page.locator('#stil-headline-navn').textContent()).trim();
    expect(stilNavnLearner).not.toBe('');
    expect(stilNavnLearner).not.toBe('—'); // "—" placeholder, no match computed yet
    const veiledningLearner = (
      (await page.locator('#stil-veiledning-auto').textContent()) || ''
    ).trim();
    expect(veiledningLearner.length).toBeGreaterThan(0);
    expect(veiledningLearner).not.toMatch(RAW_I18N_KEY_RE);
    expect(veiledningLearner.toLowerCase()).not.toContain('brygghuseffektivitet');
    expect(veiledningLearner.toLowerCase()).not.toContain('mester');

    // 8. save/preserve behaviour: draft -> explicit save -> "Lagret"
    await expect(page.locator('#identitet-lagretilstand')).toHaveText(/Kladd/);
    await page.locator('#lagre-knapp').click();
    await expect(page.locator('#lagre-status')).toContainText(RECIPE_NAVN);
    await expect(page.locator('#identitet-lagretilstand')).toHaveText('Lagret');

    async function snapshot() {
      return {
        navn: await page.locator('#oppskrift-navn').inputValue(),
        volum: await page.locator('#batch-volum').inputValue(),
        maltMengde: await page.locator('#malt-rader .malt-mengde').first().inputValue(),
        maltId: await page.locator('#malt-rader .combobox-input').first().inputValue(),
        humleGram: await page.locator('#humle-rader .humle-gram').first().inputValue(),
        gjaer: await page.locator('#gjaer-panel .combobox-input').inputValue(),
        og: await page.locator('#res-og').textContent(),
        lagretilstand: await page.locator('#identitet-lagretilstand').textContent(),
      };
    }
    const forsteLaerling = await snapshot();

    // 9/10. Learner -> Master (hop #1): verify Master-only controls now
    // reachable, and every recipe/save-state field is byte-identical.
    await byttModusViaSidemeny(page, 'mester');
    await expect(maltPct).toBeVisible();
    await expect(humleIbuRad).toBeVisible();
    await expect(skalerRad).toBeVisible();
    expect(await snapshot()).toEqual(forsteLaerling);

    // 11. use a genuine advanced Master-only control: recompute hop grams
    // from a target IBU for this addition (web/js/app.js
    // beregnHumleGramFraMaalIbu()) -- not cosmetic, an actual calculation
    // control absent from Learner mode.
    const hopRad = page.locator('#humle-rader .ingrediens-rad').first();
    const humleGramForBeregning = await hopRad.locator('.humle-gram').inputValue();
    await hopRad.locator('.humle-maal-ibu').fill('25');
    await hopRad.locator('.humle-beregn-knapp').click();
    const humleGramEtterBeregning = await hopRad.locator('.humle-gram').inputValue();
    expect(Number(humleGramEtterBeregning)).toBeGreaterThan(0);
    expect(humleGramEtterBeregning).not.toBe(humleGramForBeregning);

    // The advanced control genuinely changed recipe content after the
    // explicit save above -- correctly reflected as "changed since saved",
    // not silently reverted to "saved" or reset to an unsaved draft. This
    // is real save/draft-orientation evidence, not incidental.
    await expect(page.locator('#identitet-lagretilstand')).toHaveText('Endret siden lagring');

    // 12. Master -> Learner (hop #2): the produced advanced value is a
    // regular recipe field (hop grams) and must survive like any other --
    // only the Master-only calculator UI around it disappears.
    await byttModusViaSidemeny(page, 'laerling');
    await expect(maltPct).toBeHidden();
    await expect(humleIbuRad).toBeHidden();
    await expect(hopRad.locator('.humle-gram')).toHaveValue(humleGramEtterBeregning);
    await expect(page.locator('#oppskrift-navn')).toHaveValue(RECIPE_NAVN);
    await expect(page.locator('#identitet-lagretilstand')).toHaveText('Endret siden lagring');

    // second Learner -> Master (hop #3), completing L->M->L->M
    await byttModusViaSidemeny(page, 'mester');
    await expect(hopRad.locator('.humle-gram')).toHaveValue(humleGramEtterBeregning);
    await expect(maltPct).toBeVisible();
    await expect(page.locator('#oppskrift-navn')).toHaveValue(RECIPE_NAVN);
    await expect(page.locator('#identitet-lagretilstand')).toHaveText('Endret siden lagring');

    // Guidance panel re-rendered, not stale/blank, after four mode hops.
    await expect(page.locator('#stil-headline-navn')).not.toHaveText('—');
    await expect(page.locator('#stil-auto-innhold')).toBeVisible();

    // 13. continue into the existing brew flow far enough to meaningfully
    // proceed toward brewing -- and no further (14: no destructive/deeper
    // brew-lifecycle mutation attempted here).
    await page.locator('#start-brygging-knapp').click();
    await expect(page.locator('#brygg-start-status')).toContainText(RECIPE_NAVN);
    const bryggState = await page.evaluate(() => localStorage.getItem('kvernhaug_web_brygg'));
    expect(bryggState).toBeTruthy();
    const bryggItems = JSON.parse(bryggState).items || [];
    expect(bryggItems.length).toBe(1);
    expect(bryggItems[0].snapshot.recipe.navn).toBe(RECIPE_NAVN);

    // Mobile: no major horizontal overflow at the end of the flow.
    const viewport = page.viewportSize();
    if (viewport && viewport.width <= 420) {
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
    }

    // Accessibility spot-check: trust-critical controls expose real
    // accessible names (label/aria-label), not just visual text/position.
    await expect(page.getByRole('textbox', { name: /.lnavn/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Start brygging/i })).toBeVisible();
    await expect(page.getByRole('button', { name: '💾 Lagre oppskrift' })).toBeVisible();
    await expect(page.locator('#gjaer-panel .combobox-input')).toHaveAttribute('aria-label', /.+/);

    expect(errors).toEqual([]);
  });
});

test.describe('Phase 3A (#250) -- trust-critical Learner/Master proof in EN', () => {
  test('EN guidance/mode labels are coherent and non-raw, and one L-M-L cycle preserves recipe + Master-only value', async ({ page }) => {
    const errors = collectErrors(page);

    await page.goto(localePath('en', '/index.html'));
    await dismissModeDialog(page, 'laerling');
    await expect(page.locator('body')).toHaveClass(/modus-laerling/);

    await byggOppskrift(page);

    // Mode status text is real English copy, not the NO string / a raw key.
    await openSideDrawer(page);
    await expect(page.locator('#sidemeny-modus-status')).toContainText(/Apprentice/i);
    await closeSideDrawer(page);

    // Guidance panel: real EN text, no raw i18n key, no stray NO leakage.
    await page.locator('#stilanalyse-panel > summary').click();
    await expect(page.locator('#stil-auto-innhold')).toBeVisible();
    const veiledningEn = (
      (await page.locator('#stil-veiledning-auto').textContent()) || ''
    ).trim();
    expect(veiledningEn.length).toBeGreaterThan(0);
    expect(veiledningEn).not.toMatch(RAW_I18N_KEY_RE);
    expect(veiledningEn.toLowerCase()).not.toContain('brygghuseffektivitet');

    const hopRad = page.locator('#humle-rader .ingrediens-rad').first();
    const forsteGram = await hopRad.locator('.humle-gram').inputValue();

    // L -> M: EN mode status text + the same Master-only witness control.
    await byttModusViaSidemeny(page, 'mester');
    await expect(page.locator('#malt-rader .malt-pct').first()).toBeVisible();
    await openSideDrawer(page);
    await expect(page.locator('#sidemeny-modus-status')).toContainText(/Master/i);
    await closeSideDrawer(page);

    await hopRad.locator('.humle-maal-ibu').fill('25');
    await hopRad.locator('.humle-beregn-knapp').click();
    const gramEtterBeregning = await hopRad.locator('.humle-gram').inputValue();
    expect(gramEtterBeregning).not.toBe(forsteGram);

    // M -> L: recipe + the advanced value survive, EN status text correct.
    await byttModusViaSidemeny(page, 'laerling');
    await expect(page.locator('#malt-rader .malt-pct').first()).toBeHidden();
    await expect(hopRad.locator('.humle-gram')).toHaveValue(gramEtterBeregning);
    await expect(page.locator('#oppskrift-navn')).toHaveValue(RECIPE_NAVN);
    await openSideDrawer(page);
    await expect(page.locator('#sidemeny-modus-status')).toContainText(/Apprentice/i);
    await closeSideDrawer(page);

    expect(errors).toEqual([]);
  });
});
