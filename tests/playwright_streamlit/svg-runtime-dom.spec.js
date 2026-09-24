// Real Streamlit *runtime* browser regression coverage for the three
// Bryggeskole static SVG visuals (issue #378 Chief review, PR #379).
//
// The bug this catches (owner-PC QA, issue #378): the Pakking SVG
// diagram rendered as plain linear label text with no visible geometry
// and a large blank vertical gap, despite every source/viewBox unit
// test and the (web/-only) Playwright Critical Browser Gate being
// green -- because neither of those exercises the real Streamlit
// `st.markdown(svg, unsafe_allow_html=True)` rendering path at all.
// `tests/test_bryggeskole_svg_streamlit_rendering.py` closed part of
// that gap by parsing the markup through a real CommonMark parser, but
// that is still a simulation, not the actual browser DOM. This spec is
// the real-browser half: it starts the actual Streamlit app (via the
// minimal harness in harness_app.py, over playwright.streamlit.config.js)
// and inspects genuine computed layout/DOM properties.
//
// Deliberately bounded, not a general Streamlit E2E framework: one
// harness page, three visuals, two languages, the existing four-project
// device matrix already used by the web Browser Gate.

const { test, expect } = require('@playwright/test');

// (aria-label per language, expected labels that must be attached
// inside that same <svg>, expected shape tags proving real geometry --
// mirrors tests/test_bryggeskole_svg_streamlit_rendering.py's _CASES).
const VISUALS = [
  {
    name: 'boil_timeline',
    ariaLabel: { no: 'Koking og humletidspunkt', en: 'Boil and hop timing' },
    labels: {
      no: ['Kokestart', 'Tidlig humletilsetning', 'Hot break / skum'],
      en: ['Boil start', 'Early hop addition', 'Hot break / foam'],
    },
    shapeSelector: 'rect, circle',
  },
  {
    name: 'cool_transfer_flow',
    ariaLabel: { no: 'Kjøling og overføring', en: 'Cooling and transfer' },
    labels: {
      no: ['Kjøling', 'Overføring', 'Gjæringskar'],
      en: ['Cooling', 'Transfer', 'Fermenter'],
    },
    shapeSelector: 'rect, line',
  },
  {
    name: 'package_flow',
    ariaLabel: { no: 'Pakking', en: 'Packaging' },
    labels: {
      no: ['Gjæringskar (ferdig gjæret)', 'Flaske-sti', 'Fat-sti'],
      en: ['Fermenter (done fermenting)', 'Bottle path', 'Keg path'],
    },
    shapeSelector: 'rect, line',
  },
];

const LANGUAGES = ['no', 'en'];

// Proves `label` never appears as a leaf text node outside any <svg> --
// the reported bug rendered labels as loose page text below a blank
// gap once the diagram markup fragmented. Cross-visual duplicate
// wording (e.g. "Transfer" is used by both cool_transfer_flow and
// package_flow, each inside its own <svg>) is expected and not a
// failure -- only text with no `<svg>` ancestor at all counts as stray.
async function assertLabelNeverStrayOutsideSvg(page, label) {
  const strayCount = await page.evaluate((text) => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    let count = 0;
    let node = walker.currentNode;
    while (node) {
      if (node.children.length === 0 && node.textContent && node.textContent.trim() === text && !node.closest('svg')) {
        count += 1;
      }
      node = walker.nextNode();
    }
    return count;
  }, label);
  expect(strayCount).toBe(0);
}

for (const lang of LANGUAGES) {
  test.describe(`Bryggeskole SVG runtime rendering (lang=${lang})`, () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(`/?lang=${lang}`);
      // Streamlit's own root mount point; waiting for it confirms the
      // app actually booted before any per-visual assertion runs.
      await page.locator('[data-testid="stAppViewContainer"]').waitFor({ state: 'visible' });
    });

    for (const visual of VISUALS) {
      test(`${visual.name}: SVG root renders as real, visible geometry (not text fallback)`, async ({ page }) => {
        const svg = page.locator(`svg[aria-label="${visual.ariaLabel[lang]}"]`);

        // 1. The visual root is present and visible -- the exact thing
        // the reported bug broke (no diagram rendered at all).
        await expect(svg).toBeVisible();
        const svgBox = await svg.boundingBox();
        expect(svgBox).not.toBeNull();
        expect(svgBox.width).toBeGreaterThan(50);
        expect(svgBox.height).toBeGreaterThan(20);

        // 2. Representative geometry elements are real rendered shapes
        // with non-zero dimensions, not orphaned siblings the browser
        // never gives a layout box (the pre-fix fragmentation failure).
        const shapes = svg.locator(visual.shapeSelector);
        const shapeCount = await shapes.count();
        expect(shapeCount).toBeGreaterThan(0);
        let sawNonZeroShape = false;
        for (let i = 0; i < shapeCount; i += 1) {
          const box = await shapes.nth(i).boundingBox();
          if (box && box.width > 0 && box.height > 0) {
            sawNonZeroShape = true;
            break;
          }
        }
        expect(sawNonZeroShape).toBe(true);

        // 3. Expected labels are attached as descendants of this same
        // <svg> element -- not merely present somewhere on the page as
        // loose fallback text outside any diagram (the reported "just
        // text near the bottom" symptom). Exact match (not substring):
        // several of these visuals also carry a <title>/heading <text>
        // whose own wording contains a shorter label as a substring
        // (e.g. "Cooling" inside the "Cooling and transfer" title), so
        // exact equality is what actually isolates the dedicated label
        // node instead of also matching the title.
        for (const label of visual.labels[lang]) {
          await expect(svg.getByText(label, { exact: true })).toHaveCount(1);
          await assertLabelNeverStrayOutsideSvg(page, label);
        }
      });
    }

    test('the three visuals are stacked without an oversized blank gap between them', async ({ page }) => {
      const boxes = [];
      for (const visual of VISUALS) {
        const svg = page.locator(`svg[aria-label="${visual.ariaLabel[lang]}"]`);
        await expect(svg).toBeVisible();
        const box = await svg.boundingBox();
        expect(box).not.toBeNull();
        boxes.push(box);
      }
      // Reported bug: "a very large blank vertical region" between
      // lesson content and the broken text fallback. With three correctly
      // rendered SVGs back to back, normal Streamlit block spacing is a
      // handful of pixels of margin -- a generous but still bounded cap
      // (well under an order of magnitude smaller than a "very large"
      // gap) catches a regression back to stray empty fragments without
      // being flaky across viewports/browsers.
      const MAX_GAP_PX = 250;
      for (let i = 1; i < boxes.length; i += 1) {
        const gap = boxes[i].y - (boxes[i - 1].y + boxes[i - 1].height);
        expect(gap).toBeLessThan(MAX_GAP_PX);
      }
    });
  });
}
