'use strict';

// Issue #230 (Astra A2-04, docs/development/web_combobox_tabindex_triage_184.md)
// -- fix for the shared combobox listbox (web/js/combobox.js) becoming an
// unintended sequential Tab stop whenever its rendered options overflow the
// list's `max-height: 15rem` (web/css/style.css). Chromium/Firefox both make
// an overflowing `overflow-y: auto` container sequentially focusable via Tab
// unless it carries an explicit `tabindex` attribute -- the fix authors
// `tabindex="-1"` on `.combobox-list[role="listbox"]` at construction time.
// Covers all three suggested acceptance tests from the triage doc: (1) Tab
// skips the listbox entirely, (2) the listbox stays scrollable by keyboard,
// (3) arrow-key roving-focus navigation and Enter-to-select are unchanged.
const { test, expect } = require('@playwright/test');
const { localePath, collectErrors, dismissModeDialog } = require('./helpers');

// The style/"Ølstil" combobox (#stilvalg-panel) always renders all 26 BJCP
// styles on focus of an empty input (triage doc: "focusing an empty input
// already opens the full, unfiltered list") -- reliably overflows the
// 15rem/238px content-box max-height regardless of viewport, so it's a
// stable reproduction surface without depending on the mobile/desktop
// project's viewport height.
const STIL_INPUT = '#stilvalg-panel .combobox-input';
const STIL_LIST = '#stilvalg-panel .combobox-list';

// The next real control after the style input in DOM/tab order: the
// combobox input of the first (default, always-present) malt row. Verified
// directly (not assumed) across chromium-desktop/firefox-desktop x NO/EN
// before writing this assertion.
const MALT_INPUT = '#malt-rader .combobox-input';

for (const locale of ['no', 'en']) {
  test(`overflowing combobox listbox is skipped by Tab, stays keyboard-scrollable, and keeps arrow-key navigation [${locale}]`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localePath(locale, '/index.html'));
    await dismissModeDialog(page);

    const input = page.locator(STIL_INPUT);
    const list = page.locator(STIL_LIST);

    // Focusing the empty style input opens the full, unfiltered list.
    await input.click();
    await expect(list).toBeVisible();

    // Confirm this reproduction surface genuinely overflows its max-height
    // box -- otherwise browsers would never apply the scrollable-region
    // focusability heuristic this fix addresses, and the Tab assertion
    // below would pass vacuously.
    const overflows = await list.evaluate((el) => el.scrollHeight > el.clientHeight);
    expect(overflows).toBe(true);

    // The fix: an explicit tabindex="-1" attribute is authored on the
    // listbox (not merely the default -1 .tabIndex property every
    // non-tabindex element already has).
    expect(await list.evaluate((el) => el.getAttribute('tabindex'))).toBe('-1');

    // Acceptance test 1 (triage doc): a single Tab from the combobox input
    // moves focus to the next real interactive control -- never to the
    // listbox itself or one of its options. Asserts the exact expected
    // control (the first malt row's combobox input, #malt-panel being the
    // next panel in DOM order) is focused, not merely that focus landed
    // somewhere outside the listbox -- a generic "not in listbox" check
    // would pass vacuously even if focus fell through to <body> or some
    // other unintended element.
    const maltInput = page.locator(MALT_INPUT);
    await page.keyboard.press('Tab');
    await expect(maltInput).toBeFocused();

    // Acceptance test 2: the listbox remains keyboard-scrollable via arrow
    // keys past the visible region -- a future fix must not achieve (1) by
    // breaking scroll (e.g. overflow: hidden). Re-open the list and arrow
    // all the way down to the last of the 26 BJCP styles.
    //
    // The blur that just moved focus away from `input` (via Tab, above)
    // scheduled combobox.js's own unconditional `setTimeout(() =>
    // this._close(), 150)`. That is pre-existing behavior this fix does not
    // touch, but re-clicking `input` inside that same 150ms window can race
    // it: the click's own focus reopens the list, then the stale timeout
    // fires anyway and closes it again. Wait past that window first so the
    // stale close has already resolved before this test reopens the list.
    await page.waitForTimeout(200);
    await input.click();
    await expect(list).toBeVisible();
    const optionCount = await page.locator(`${STIL_LIST} .combobox-option`).count();
    expect(optionCount).toBeGreaterThan(1);
    for (let i = 0; i < optionCount; i++) {
      await page.keyboard.press('ArrowDown');
    }
    const scrollTop = await list.evaluate((el) => el.scrollTop);
    expect(scrollTop).toBeGreaterThan(0);

    // Acceptance test 3: arrow-key roving focus and Enter-to-select are
    // unchanged by the fix. aria-activedescendant tracks the last
    // highlighted (wrapped-around-to-first, since ArrowDown wraps) option,
    // real DOM focus stays on the input throughout, and Enter selects it.
    const activeDescendantId = await input.getAttribute('aria-activedescendant');
    expect(activeDescendantId).toBeTruthy();
    await expect(page.locator(`#${activeDescendantId}`)).toHaveClass(/is-active/);
    await expect(input).toBeFocused();

    const highlightedLabel = await page.locator(`#${activeDescendantId}`).textContent();
    await page.keyboard.press('Enter');
    await expect(list).toBeHidden();
    await expect(input).toHaveValue(highlightedLabel);

    expect(errors).toEqual([]);
  });
}
