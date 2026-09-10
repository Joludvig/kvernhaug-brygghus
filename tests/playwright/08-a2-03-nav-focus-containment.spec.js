'use strict';

// Issue #209 (Astra A2-03, docs/development/web_a2_03_navigation_focus_contract.md)
// -- the two related keyboard-focus fixes in web/js/chrome.js:
//   Half 1 (initHero()'s oppdater() / initSidemeny()'s apne()/lukk()): the
//     closed .kompaktnav and closed .sidemeny/.sidemeny-bakteppe toggle the
//     native `inert` property in lock-step with their existing
//     .synlig/.apen visibility classes, so hidden/off-screen nav content is
//     out of the Tab order (and unfocusable via .focus()) while closed.
//   Half 2 (#186 OPTION A, the always-attached Tab/Shift+Tab keydown
//     listener added right after the existing Escape listener): while the
//     drawer is open, Tab/Shift+Tab wraps within its focusable controls
//     instead of leaking into header/background content behind the
//     pointer-blocking backdrop.
// Also covers the Chief-review-requested safe-fallback case (contract
// acceptance matrix M15/M16, issue #209 acceptance 6): a control inside
// .kompaktnav that holds focus when it becomes inert (scrolling back above
// .hero's threshold) must go through BOTH contract-mandated steps in order
// -- (1) the browser's native inert focus-fixup-to-<body> rule (automatic,
// no chrome.js code needed), then (2) the *next forward Tab press* lands on
// #meny-knapp-hero (the page's skip-link, were one to precede it -- none
// exists yet in this codebase), not wherever the browser's retained
// sequential focus-navigation position would otherwise resume. An earlier
// round of this PR skipped step (1) by focusing #meny-knapp-hero
// immediately when .kompaktnav became inert, which Chief review flagged as
// not implementing the ratified sequence: `oppdater()` (web/js/chrome.js)
// now leaves the native fixup-to-<body> alone and instead arms a one-shot
// keydown listener that intercepts exactly the next forward Tab press while
// focus is still on <body>, redirecting only that keypress to the safe
// target. This spec asserts both steps, in order.
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors, dismissModeDialog } = require('./helpers');

// The drawer's 15 focusable controls in DOM order (contract §2.2); first
// and last are enough to assert the wrap-around trap boundaries without
// hardcoding the full list (chrome.js itself doesn't either -- it reuses
// meny.querySelectorAll("a, button")).
const EERSTE_FOKUSERBARE = '#sidemeny .sidemeny-lukk';
const SISTE_FOKUSERBARE = '#sidemeny .sidemeny-lenke[href*="hjelp"]';

async function scrollPastHero(page) {
  const kompaktnav = page.locator('.kompaktnav');
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await expect(kompaktnav).toHaveClass(/synlig/);
}

async function scrollBackToTop(page) {
  const kompaktnav = page.locator('.kompaktnav');
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(kompaktnav).not.toHaveClass(/synlig/);
}

/** True if `selector` currently matches document.activeElement. */
function isFocused(page, selector) {
  return page.evaluate((sel) => document.activeElement === document.querySelector(sel), selector);
}

for (const locale of ['no', 'en']) {
  test(`kompaktnav and the drawer are inert while closed, and only the active surface is focusable [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/index.html'));
    await dismissModeDialog(page);

    // Closed on load: both the sticky nav and the drawer/backdrop start inert.
    expect(await page.locator('.kompaktnav').evaluate((el) => el.inert)).toBe(true);
    expect(await page.locator('#sidemeny').evaluate((el) => el.inert)).toBe(true);
    expect(await page.locator('.sidemeny-bakteppe').evaluate((el) => el.inert)).toBe(true);
    // .hero itself is never visibility-toggled -- its own .meny-knapp is
    // never inert (contract §4 non-goal).
    expect(await page.locator('#meny-knapp-hero').evaluate((el) => el.inert)).toBe(false);

    // Closed .kompaktnav content is unfocusable, not just visually hidden --
    // inert blocks programmatic .focus(), the same mechanism that removes
    // it from Tab order.
    await page.locator('#meny-knapp-kompakt').evaluate((el) => el.focus());
    expect(await page.evaluate(() => document.activeElement.id)).not.toBe('meny-knapp-kompakt');

    // Scroll past .hero's threshold: .kompaktnav becomes visible AND
    // released from inert -- confirms the toggle runs both ways, not just
    // "add inert once."
    await scrollPastHero(page);
    expect(await page.locator('.kompaktnav').evaluate((el) => el.inert)).toBe(false);
    await page.locator('#meny-knapp-kompakt').evaluate((el) => el.focus());
    expect(await page.evaluate(() => document.activeElement.id)).toBe('meny-knapp-kompakt');

    // Scroll back above the threshold: inert is re-applied.
    await scrollBackToTop(page);
    expect(await page.locator('.kompaktnav').evaluate((el) => el.inert)).toBe(true);

    expect(errors).toEqual([]);
  });
}

test('the closed drawer is unfocusable, opening releases inert and focuses the close button, closing re-applies inert [no]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  // Closed drawer's first and last controls are both unfocusable.
  await page.locator(EERSTE_FOKUSERBARE).evaluate((el) => el.focus());
  expect(await isFocused(page, EERSTE_FOKUSERBARE)).toBe(false);
  await page.locator(SISTE_FOKUSERBARE).evaluate((el) => el.focus());
  expect(await isFocused(page, SISTE_FOKUSERBARE)).toBe(false);

  await page.locator('#meny-knapp-hero').click();
  await expect(page.locator('#sidemeny')).toHaveClass(/apen/);
  expect(await page.locator('#sidemeny').evaluate((el) => el.inert)).toBe(false);
  expect(await page.locator('.sidemeny-bakteppe').evaluate((el) => el.inert)).toBe(false);
  await expect(page.locator(EERSTE_FOKUSERBARE)).toBeFocused();

  await page.locator(EERSTE_FOKUSERBARE).click();
  await expect(page.locator('#sidemeny')).not.toHaveClass(/apen/);
  expect(await page.locator('#sidemeny').evaluate((el) => el.inert)).toBe(true);
  expect(await page.locator('.sidemeny-bakteppe').evaluate((el) => el.inert)).toBe(true);

  // Re-closed: unfocusable again, same as before the open/close cycle.
  await page.locator(EERSTE_FOKUSERBARE).evaluate((el) => el.focus());
  expect(await isFocused(page, EERSTE_FOKUSERBARE)).toBe(false);

  expect(errors).toEqual([]);
});

for (const locale of ['no', 'en']) {
  test(`open-drawer Tab/Shift+Tab wraps within its focusable controls, never leaking to background content [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/index.html'));
    await dismissModeDialog(page);

    await page.locator('#meny-knapp-hero').click();
    await expect(page.locator(EERSTE_FOKUSERBARE)).toBeFocused();

    // Shift+Tab from the first control wraps to the last (M5), staying
    // inside the drawer -- not leaking backward into header/background.
    await page.keyboard.press('Shift+Tab');
    await expect(page.locator(SISTE_FOKUSERBARE)).toBeFocused();
    expect(await page.evaluate(() => document.activeElement.closest('#sidemeny') !== null)).toBe(true);

    // Tab from the last control wraps back to the first (M6).
    await page.keyboard.press('Tab');
    await expect(page.locator(EERSTE_FOKUSERBARE)).toBeFocused();

    // Tab forward through every one of the drawer's focusable controls
    // (more presses than controls exist) -- focus must stay contained the
    // entire time (M7), never landing on e.g. #oppskrift-navn behind the
    // backdrop.
    const fokuserbareAntall = await page.locator('#sidemeny a, #sidemeny button').count();
    for (let i = 0; i < fokuserbareAntall + 3; i++) {
      await page.keyboard.press('Tab');
      expect(await page.evaluate(() => document.activeElement.closest('#sidemeny') !== null)).toBe(true);
    }

    expect(errors).toEqual([]);
  });
}

test('Escape and backdrop click both close the drawer and restore focus to the exact opener [no]', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));
  await dismissModeDialog(page);

  await page.locator('#meny-knapp-hero').click();
  await expect(page.locator(EERSTE_FOKUSERBARE)).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.locator('#sidemeny')).not.toHaveClass(/apen/);
  await expect(page.locator('#meny-knapp-hero')).toBeFocused();

  await page.locator('#meny-knapp-hero').click();
  await expect(page.locator(EERSTE_FOKUSERBARE)).toBeFocused();
  const viewport = page.viewportSize();
  // Click far enough right to land on the backdrop, not the (<=82vw wide)
  // drawer, on both desktop and mobile viewports.
  await page.mouse.click(viewport.width - 5, 100);
  await expect(page.locator('#sidemeny')).not.toHaveClass(/apen/);
  await expect(page.locator('#meny-knapp-hero')).toBeFocused();

  expect(errors).toEqual([]);
});

for (const locale of ['no', 'en']) {
  test(`a focused kompaktnav control that becomes inert on scroll-back is explicitly refocused to #meny-knapp-hero (M15/M16) [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/index.html'));
    await dismissModeDialog(page);

    await scrollPastHero(page);
    await page.locator('#meny-knapp-kompakt').evaluate((el) => el.focus());
    await expect(page.locator('#meny-knapp-kompakt')).toBeFocused();

    // Scroll back above the threshold WITHOUT moving focus away first --
    // .kompaktnav becomes inert while it still contains the focused
    // element (contract §3.1 "Where focus lands..." / acceptance matrix
    // M15). Step 1: the browser's native inert-focus-fixup moves focus to
    // <body> -- chrome.js does not (and per the contract, must not)
    // override this step.
    await scrollBackToTop(page);
    const erPaaBody = await page.evaluate(() => document.activeElement === document.body);
    expect(erPaaBody).toBe(true);

    // Focus must never remain inside now-inert nav content either.
    const erInertOmraade = await page.evaluate(
      () => document.activeElement.closest('.kompaktnav, #sidemeny, .sidemeny-bakteppe') !== null
    );
    expect(erInertOmraade).toBe(false);

    // Step 2: the *next forward Tab press* lands on #meny-knapp-hero (the
    // page's first focusable control) -- not wherever the browser's
    // retained sequential focus-navigation position would otherwise resume.
    await page.keyboard.press('Tab');
    await expect(page.locator('#meny-knapp-hero')).toBeFocused();

    expect(errors).toEqual([]);
  });
}

for (const locale of ['no', 'en']) {
  test(`the armed M15 fallback disarms once .kompaktnav becomes active again, so a later Tab stays in the active surface instead of jumping to the scrolled-away #meny-knapp-hero [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/index.html'));
    await dismissModeDialog(page);

    // Arm the M15 fallback exactly as in the test above: a focused
    // .kompaktnav control goes inert on scroll-back, native inert-fixup
    // moves focus to <body>.
    await scrollPastHero(page);
    await page.locator('#meny-knapp-kompakt').evaluate((el) => el.focus());
    await scrollBackToTop(page);
    expect(await page.evaluate(() => document.activeElement === document.body)).toBe(true);

    // Chief review (issue #209, round 5): WITHOUT pressing Tab yet, the
    // user scrolls back down -- .kompaktnav becomes active/visible (and
    // released from inert) again, so the M15 fallback context has ended.
    await scrollPastHero(page);

    // The next Tab press must NOT be forced to the now off-screen
    // #meny-knapp-hero -- that would reintroduce off-screen focus and
    // break the requirement to preserve responsive active-surface
    // semantics. It must follow normal sequential navigation, which stays
    // within the currently active .kompaktnav surface (verified empirically
    // in Chromium and Firefox, desktop and mobile: browsers resume
    // sequential navigation from the just-reactivated control's own
    // position, landing on a .kompaktnav control, not <body>'s absolute
    // start).
    await page.keyboard.press('Tab');
    const erMenyKnappHero = await isFocused(page, '#meny-knapp-hero');
    expect(erMenyKnappHero).toBe(false);
    const erIKompaktnav = await page.evaluate(
      () => document.activeElement.closest('.kompaktnav') !== null
    );
    expect(erIKompaktnav).toBe(true);

    expect(errors).toEqual([]);
  });
}
