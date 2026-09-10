'use strict';

// Shared helpers for the Playwright Critical Browser Gate (issue #200).
// Kept dependency-free (plain @playwright/test API only), mirroring the
// same minimal-infrastructure principle web/ itself follows.

/**
 * The NO source pages live at the web/ root; the generated EN mirror
 * lives one directory deeper under /en/ (scripts/generate_web_i18n_pages.py).
 */
function localePath(locale, path) {
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return locale === 'en' ? `/en${suffix}` : suffix;
}

/** Attach console/page error collectors. Call before page.goto(). */
function collectErrors(page) {
  const errors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`console: ${msg.text()}`);
  });
  page.on('pageerror', (err) => {
    errors.push(`pageerror: ${err.message}`);
  });
  return errors;
}

/**
 * Dismiss the first-visit mode dialog (#modus-forstegang) if it is showing
 * -- every fresh Playwright test gets an isolated context (empty
 * localStorage), so it always shows on the very first goto() of a test.
 * Picks the given mode ("laerling" default -- Bryggelaerling) via its
 * .modus-knapp button. A no-op if a mode preference is already stored
 * (dialog stays hidden, see web/js/app.js::initModus()).
 */
async function dismissModeDialog(page, mode = 'laerling') {
  const dialog = page.locator('#modus-forstegang');
  if (await dialog.isVisible().catch(() => false)) {
    await page.locator(`#modus-forstegang .modus-knapp[data-modus="${mode}"]`).click();
    await dialog.waitFor({ state: 'hidden' });
  }
}

/**
 * Open the side drawer (.sidemeny) via its hamburger toggle -- the unit
 * switcher, mode switcher (drawer copy) and nav links all live inside it,
 * off-screen/closed by default (see .claude/skills/web-full-regression).
 * Idempotent: the toggle button opens/closes (web/js/chrome.js
 * initSidemeny()), so this only clicks it when the drawer isn't already open.
 */
async function openSideDrawer(page) {
  const meny = page.locator('#sidemeny');
  const isOpen = await meny.evaluate((el) => el.classList.contains('apen'));
  if (!isOpen) {
    await page.locator('#meny-knapp-hero').click();
    await meny.waitFor({ state: 'visible' });
  }
}

module.exports = { localePath, collectErrors, dismissModeDialog, openSideDrawer };
