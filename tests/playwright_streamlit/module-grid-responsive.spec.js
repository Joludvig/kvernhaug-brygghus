// Real Streamlit *runtime* browser regression coverage for the
// Bryggeskole module-card grid's responsive layout (issue #394).
//
// The bug this catches (owner-PC QA, issue #394): on a narrow/portrait
// screen the module cards in _render_skoleoversikt() were squeezed
// into a single row via `st.columns(len(stadier))`, whose per-column
// `flex-basis` was a PERCENTAGE of the container width -- the columns
// always summed to 100%, so the browser's own flex-wrap never
// actually triggers no matter how narrow the screen gets; the columns
// just shrink until the module name's text has no room left and the
// browser's overflow-wrap fallback breaks it mid-word ("Forbere/delse/
// metode", "Gjæring (bøtte/FermZill/a)"). A CSS-string presence check
// cannot catch this class of bug at all -- it requires measuring actual
// rendered layout in a real browser, which is what this spec does.
//
// Reproduced directly against the pre-fix source (stash-toggle) at
// viewport width 750px -- sidebar still shown inline (Streamlit's own
// auto-collapse breakpoint is narrower), main content squeezed to ~65-100px columns -- and confirmed fixed
// post-fix at the same width. The grid now has ten cards (issue #458;
// issue #473 adds Rengjøring og sikkerhet right after Råvarer; issue #472
// adds Smak og evaluering as the final card; Måling og bryggelogg
// (Foundation, measurement contract §21.5) is inserted as card nine,
// between Pakking and Smak og evaluering).
//
// Runs against tests/fixtures/streamlit_harness/bryggeskole_harness.py
// (already the production render_bryggeskole_panel() call; previously
// only exercised via AppTest, which never produces real browser
// layout/CSS at all) via playwright.bryggeskole-grid.config.js.

const { test, expect } = require('@playwright/test');

// The exact width the bug was reproduced at: narrow/portrait, but wide
// enough that Streamlit's own sidebar auto-collapse hasn't kicked in yet
// (so the module grid actually gets squeezed, not just handed the
// sidebar's freed-up width).
const NARROW_PORTRAIT_WIDTH = 750;
const NARROW_PORTRAIT_HEIGHT = 900;

const MODUL_TEKST = {
  no: ['Råvarer', 'Rengjøring og sikkerhet', 'Forberedelse/metode', 'Mesking (kjele/BIAB)', 'Koking', 'Kjøling', 'Gjæring (bøtte/FermZilla)', 'Pakking', 'Måling og bryggelogg', 'Smak og evaluering'],
  en: ['Raw materials', 'Cleaning and safety', 'Preparation/method', 'Mashing (kettle/BIAB)', 'Boil', 'Cooling', 'Fermentation (bucket/FermZilla)', 'Packaging', 'Measurement and brew log', 'Tasting and evaluation'],
};

const ENV_KNAPP = {
  no: /Velg dette miljøet/i,
  en: /Choose this environment/i,
};

// Wide enough that Streamlit's own sidebar auto-collapse never kicks in,
// used only as a transient starting size so the language radio (which
// lives in the sidebar) is reachable before narrowing down to the actual
// test viewport -- mirrors how a real user would pick a language on a
// desktop-width session before resizing/rotating, and avoids conflating
// "can the language switch be clicked at this width" (a sidebar-visibility
// concern, unrelated to this issue) with the module-grid layout behaviour
// this spec actually exists to test.
const WIDE_STARTING_VIEWPORT = { width: 1280, height: 900 };

async function gotoModuleGrid(page, lang, finalViewport) {
  const needsResize = finalViewport
    && (finalViewport.width !== WIDE_STARTING_VIEWPORT.width || finalViewport.height !== WIDE_STARTING_VIEWPORT.height);
  if (lang === 'en' || needsResize) {
    await page.setViewportSize(WIDE_STARTING_VIEWPORT);
  }
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  if (lang === 'en') {
    await page.getByText('English').first().click();
    await page.waitForTimeout(400);
  }
  await page.getByRole('button', { name: ENV_KNAPP[lang] }).first().click();
  await waitForModuleGridReady(page);
  if (needsResize) {
    await page.setViewportSize(finalViewport);
    await waitForModuleGridReady(page);
  }
}

// Deterministic readiness gate before any measurement. A bare
// waitForSelector('[data-testid="stHorizontalBlock"]') + fixed sleep was
// racy: it resolved within ms on the environment chooser's OWN
// st.columns block (still mounted while the rerun runs), and the grid
// then streams in 1-2.5s later column by column (e.g. 3 -> 6 -> 9 -> 10 cards, with
// transient mixed blocks such as [224,224,224,344,344]) -- so the
// measurement sometimes saw a half-rendered or stale block. Ready means:
// the block the assertions measure (the FIRST stHorizontalBlock) is the
// grid itself, it has exactly the expected card count (MODUL_TEKST,
// currently 10), every card has rendered down to
// its own "open module" button (the last element of each card), no
// stale elements remain from the rerun, and the card rects are identical
// on two consecutive animation frames (layout settled).
async function waitForModuleGridReady(page) {
  await page.evaluate(() => { window.__gridSignatur = null; });
  await page.waitForFunction((antallKort) => {
    const blokk = document.querySelector('[data-testid="stHorizontalBlock"]');
    if (!blokk || !blokk.closest('.st-key-bs_skoleoversikt_grid')) return false;
    if (document.querySelector('[data-stale="true"]')) return false;
    const cols = [...blokk.querySelectorAll(':scope > [data-testid="stColumn"]')];
    if (cols.length !== antallKort) return false;
    const ferdige = cols.every((c) => {
      const knapp = c.querySelector('[class*="st-key-bs_apne_modul_"] button');
      return knapp && knapp.getBoundingClientRect().width > 0;
    });
    if (!ferdige) return false;
    const signatur = cols.map((c) => {
      const r = c.getBoundingClientRect();
      return `${Math.round(r.top)},${Math.round(r.left)},${Math.round(r.width)},${Math.round(r.height)}`;
    }).join('|');
    const stabil = signatur === window.__gridSignatur;
    window.__gridSignatur = signatur;
    return stabil;
  }, MODUL_TEKST.no.length, { polling: 'raf', timeout: 20_000 });
}

// Genuine layout measurement: bounding rect of each stColumn card, to
// derive actual row grouping (distinct top offsets) and column count --
// not a CSS-property/string check.
async function getCardLayout(page) {
  return page.locator('[data-testid="stHorizontalBlock"]').first().locator('[data-testid="stColumn"]').evaluateAll(
    (cols) => cols.map((c) => {
      const r = c.getBoundingClientRect();
      return { top: Math.round(r.top), left: Math.round(r.left), width: Math.round(r.width) };
    }),
  );
}

// Range-based mid-word-break detector: for every "fragment" inside each
// card's title <p> -- split on whitespace AND on '/'/'-' (both legitimate
// UAX#14 line-break opportunities that real browsers may use, e.g.
// wrapping "Gjæring (bøtte/FermZilla)" as "(bøtte/" + "FermZilla)", which
// is a completely normal, expected break, NOT the reported bug) -- build
// a DOM Range over exactly that fragment's own characters and check
// getClientRects().length. A fragment that wraps cleanly onto the next
// line at one of those legitimate boundaries still has all of ITS OWN
// characters on one line, so this is 1 rect. A fragment broken *inside
// itself*, with NO natural boundary at all (the actual reported bug --
// e.g. "Forbere" + "delse" on two different lines, mid-syllable) produces
// >1 rects, because the fragment's own characters now span two lines.
async function findMidWordBreaks(page) {
  return page.locator('[data-testid="stHorizontalBlock"]').first().locator('[data-testid="stColumn"] p').evaluateAll(
    (paragraphs) => {
      const broken = [];
      for (const p of paragraphs) {
        const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          const text = node.textContent;
          const tokenRe = /[^\s/-]+/g;
          let m;
          while ((m = tokenRe.exec(text))) {
            const range = document.createRange();
            range.setStart(node, m.index);
            range.setEnd(node, m.index + m[0].length);
            const rectCount = range.getClientRects().length;
            if (rectCount > 1) {
              broken.push({ token: m[0], rectCount });
            }
          }
        }
      }
      return broken;
    },
  );
}

async function hasHorizontalOverflow(page) {
  return page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2);
}

for (const lang of ['no', 'en']) {
  test.describe(`Bryggeskole module grid (lang=${lang})`, () => {
    test(`project default viewport: multi-column, no mid-word breaks, no h-scroll`, async ({ page, viewport }) => {
      await gotoModuleGrid(page, lang, viewport);

      const cards = await getCardLayout(page);
      expect(cards).toHaveLength(MODUL_TEKST.no.length);

      const broken = await findMidWordBreaks(page);
      expect(broken, `mid-word breaks found: ${JSON.stringify(broken)}`).toEqual([]);

      expect(await hasHorizontalOverflow(page)).toBe(false);

      // Every rendered title text must still be exactly one of the nine
      // expected module names (rules out any content/navigation
      // regression from the layout change).
      const titles = await page.locator('[data-testid="stHorizontalBlock"]').first().locator('[data-testid="stColumn"] p').allTextContents();
      for (const expected of MODUL_TEKST[lang]) {
        expect(titles).toContain(expected);
      }
    });

    test(`narrow/portrait ${NARROW_PORTRAIT_WIDTH}px: cards wrap to fewer columns, no pathological word-breaking`, async ({ page }) => {
      await gotoModuleGrid(page, lang, { width: NARROW_PORTRAIT_WIDTH, height: NARROW_PORTRAIT_HEIGHT });

      const cards = await getCardLayout(page);
      expect(cards).toHaveLength(MODUL_TEKST.no.length);

      const rows = new Set(cards.map((c) => c.top));
      // The reported bug is precisely "all cards squeezed into one
      // row" at this width -- the fix must wrap to at least two rows.
      expect(rows.size, `expected wrapping into multiple rows, got layout: ${JSON.stringify(cards)}`).toBeGreaterThan(1);

      // No card should be squeezed thinner than a comfortably readable
      // width (this is what forced the mid-word breaking in the first
      // place -- the columns fit in ~65-100px each pre-fix).
      for (const c of cards) {
        expect(c.width, `card too narrow: ${JSON.stringify(c)}`).toBeGreaterThanOrEqual(150);
      }

      const broken = await findMidWordBreaks(page);
      expect(broken, `mid-word breaks found at ${NARROW_PORTRAIT_WIDTH}px: ${JSON.stringify(broken)}`).toEqual([]);

      expect(await hasHorizontalOverflow(page)).toBe(false);
    });

    test('very narrow (project mobile viewport): single column allowed, no h-scroll, no word-breaking', async ({ page, viewport }) => {
      test.skip(viewport.width > 480, 'this scenario only applies to the mobile-width projects');
      await gotoModuleGrid(page, lang, viewport);

      const cards = await getCardLayout(page);
      expect(cards).toHaveLength(MODUL_TEKST.no.length);

      const rows = new Set(cards.map((c) => c.top));
      // At genuinely mobile widths, one column per row is an acceptable
      // (and expected) outcome -- every card gets the full row.
      expect(rows.size).toBeGreaterThanOrEqual(1);
      const distinctLefts = new Set(cards.map((c) => c.left));
      expect(distinctLefts.size, 'expected a single-column stack at mobile width').toBe(1);

      const broken = await findMidWordBreaks(page);
      expect(broken, `mid-word breaks found at mobile width: ${JSON.stringify(broken)}`).toEqual([]);

      expect(await hasHorizontalOverflow(page)).toBe(false);
    });
  });
}
