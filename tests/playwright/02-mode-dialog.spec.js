'use strict';

// Issue #200 V1 scope item 2: first-visit mode dialog contract (initial
// focus, Tab/Shift+Tab containment, Escape, storage/focus return) per the
// already-shipped Batch 7 contract -- see web/js/app.js
// (initModus/_modusForstegangKeydownHandler/_lukkModusForstegang).
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors } = require('./helpers');

test('shows on first visit with focus on the first mode button', async ({ page }) => {
  const errors = collectErrors(page);
  await page.goto(localePath('no', '/index.html'));

  const dialog = page.locator('#modus-forstegang');
  await expect(dialog).toBeVisible();
  await expect(page.locator('#modus-forstegang .modus-knapp').first()).toBeFocused();

  expect(errors).toEqual([]);
});

test('Tab/Shift+Tab stay contained to the two mode buttons', async ({ page }) => {
  await page.goto(localePath('no', '/index.html'));
  const knapper = page.locator('#modus-forstegang .modus-knapp');
  await expect(knapper.first()).toBeFocused();

  await page.keyboard.press('Tab');
  await expect(knapper.nth(1)).toBeFocused();

  // Tab from the last button wraps back to the first (trap, not a leak
  // into background page content).
  await page.keyboard.press('Tab');
  await expect(knapper.first()).toBeFocused();

  // Shift+Tab from the first button wraps to the last.
  await page.keyboard.press('Shift+Tab');
  await expect(knapper.nth(1)).toBeFocused();
});

test('Escape closes the dialog without persisting a mode and returns focus to the recipe name field', async ({ page }) => {
  await page.goto(localePath('no', '/index.html'));
  const dialog = page.locator('#modus-forstegang');
  await expect(dialog).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();

  const stored = await page.evaluate(() => localStorage.getItem('kvernhaug_web_modus'));
  expect(stored).toBeNull();
  await expect(page.locator('#oppskrift-navn')).toBeFocused();
});

test('choosing a mode persists it, closes the dialog, and returns focus to the recipe name field', async ({ page }) => {
  await page.goto(localePath('no', '/index.html'));
  await page.locator('#modus-forstegang .modus-knapp[data-modus="mester"]').click();

  await expect(page.locator('#modus-forstegang')).toBeHidden();
  const stored = await page.evaluate(() => localStorage.getItem('kvernhaug_web_modus'));
  expect(stored).toBe('mester');
  await expect(page.locator('#oppskrift-navn')).toBeFocused();
  await expect(page.locator('body')).toHaveClass(/modus-mester/);
});

test('does not reappear on a later visit once a mode is stored', async ({ page }) => {
  await page.goto(localePath('no', '/index.html'));
  await page.locator('#modus-forstegang .modus-knapp[data-modus="laerling"]').click();

  await page.reload();
  await expect(page.locator('#modus-forstegang')).toBeHidden();
});
