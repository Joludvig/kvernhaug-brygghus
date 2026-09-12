# Web — combobox listbox unexpectedly enters keyboard Tab order (issue #184, OVERNIGHT PREP LANE)

*Analysis/browser-evidence lane only, per the owner's 2026-09-11 20:54 UTC
comment on #184. Reproduced live on current `master`
(`a77bbd5`) in fresh, isolated Chromium + Firefox, NO + EN, via a
throwaway Playwright spec run locally (not committed — this lane changes
no product code and adds no permanent test). No `web/**` product file was
edited to produce this brief. Not implemented. No deploy, no merge,
no #98/#100, no owner-PC claims.*

## Verdict

**Confirmed, reproducible defect — not a false alarm, not
Bryggmester/Bryggelærling-specific, not browser-specific.** Whenever a
`Combobox` (`web/js/combobox.js`) listbox is open and its rendered
options overflow the list's `max-height: 15rem` (`web/css/style.css:675`),
the `<ul role="listbox">` itself becomes reachable by pressing <kbd>Tab</kbd>
once from the combobox input — landing focus on the `UL`
(`role="listbox"`), one extra stop *before* the next real interactive
control — in both Chromium and Firefox, on both the NO and EN builder
pages. This directly conflicts with the ARIA 1.2 combobox pattern the rest
of `combobox.js` already correctly implements (see "Why this conflicts"
below), where the popup listbox must never itself be part of the page's
Tab sequence.

The issue body's own observation — *"the listbox elements have no
authored `tabindex` and computed `tabIndex` was reported as `-1`"* — is
real but is a **red herring for root cause**: `-1` is simply the normal
default value of the DOM `tabIndex` IDL property for *any* element with no
`tabindex` attribute at all (focusable or not). It does not mean the
browser is refusing to include the element in the Tab sequence; browsers
apply a separate, internal "scrollable region is keyboard-focusable"
heuristic that is not reflected in `.tabIndex` and is keyed off of
`hasAttribute('tabindex')`, not `.tabIndex`'s value. See "Root cause"
below.

## Reproduction environment

- Local Playwright (`@playwright/test` 1.63.0, project's own
  `playwright.config.js`), Chromium (Chrome for Testing 153.0.8010.12) and
  Firefox (155.0), desktop viewport (1280×900), served from a local static
  server against the checked-out working tree — same harness the
  "Playwright Critical Browser Gate" (issue #200) uses, never production.
- `master` at `a77bbd5` (pre-#184-branch HEAD).
- Throwaway spec: `tests/playwright/_tmp-184-investigation.spec.js`
  (deleted before this branch's diff was finalized — see "What this
  lane did not do" below). Findings were captured to a gitignored
  `test-results/kbh-184-findings.jsonl` during the run; the raw JSONL is
  reproduced in full under "Evidence" below so this document is
  self-contained without that file.

## Exact reproduction steps (manual)

1. Open `web/index.html` (NO) or `web/en/index.html` (EN) in Chromium or
   Firefox.
2. Dismiss the first-visit mode dialog if shown (pick either mode).
3. Click (or Tab) into the "Ølstil" / "Style" combobox input
   (`#stilvalg-panel .combobox-input`, `aria-label="Velg ølstil"` /
   `"Choose beer style"`). Focusing an **empty** input already opens the
   full, unfiltered list (`combobox.js:48`, the `focus` listener calls
   `_onInput()`, and an empty query means `this.filtered = this.items` —
   i.e. this is not a filtered-typing-only edge case, it is the default
   behavior of simply tabbing into any of these fields at all). Typing a
   character (e.g. `a`) narrows it but still overflows for any
   reasonably-sized item list.
4. Confirm the listbox (`.combobox-list[role="listbox"]`) is visible and
   its rendered content is taller than its `15rem` (238px content-box)
   `max-height` — true for the style list (26 BJCP styles), and for
   malt/hop/yeast/pantry whenever more than roughly 6-7 options render.
5. Press <kbd>Tab</kbd> **once**.
6. Observe: `document.activeElement` is the `<UL class="combobox-list"
   role="listbox">` itself — not the next real field, and not still the
   input. A sighted mouse user sees no visible focus ring change of the
   kind they'd expect (the browser typically does not draw a default
   outline on this kind of implicit scroll-focus target the same way it
   does for a real interactive element, though this was not
   pixel-measured here), but a keyboard-only or screen-reader user's
   focus is now inside a `role="listbox"` container the combobox pattern
   never intended to be a Tab stop.
7. Press <kbd>Tab</kbd> a second time: focus proceeds to the next real
   control (e.g. the next combobox input) — this is a single extra stop,
   not a keyboard trap.

## Affected selectors/surfaces

The defect lives in code shared by **every** `Combobox` instance in `web/`
— there is exactly one `.combobox-list` CSS rule
(`web/css/style.css:669-684`, `max-height: 15rem; overflow-y: auto;`) and
one `Combobox` class (`web/js/combobox.js`) that all five instantiation
sites use unmodified:

| Surface | File:line | Page(s) |
|---|---|---|
| Ølstil / beer style | `web/js/app.js:1948` | `index.html` (+ `en/`) |
| Malt (per row) | `web/js/app.js:466` | `index.html` (+ `en/`) |
| Humle / hops (per row) | `web/js/app.js:732` | `index.html` (+ `en/`) |
| Gjær / yeast | `web/js/app.js:1923` | `index.html` (+ `en/`) |
| Pantry ingredient picker | `web/js/pantry_page.js:435` | `pantry.html` (+ `en/`) |

Live spot-check confirmed the malt-row instance reproduces identically to
the style instance (see Evidence, `second-surface-spotcheck` entries) —
consistent with the defect being in the shared class/CSS, not something
style-specific. The other three sites were not individually driven
through Playwright in this lane (bounded scope) but share the exact same
`_renderList()`/`.combobox-list` code path, so the same root cause applies
to all five by construction, not by extrapolation from a different
mechanism.

## Root cause (provable)

Chromium and Firefox both implement **scrollable-region keyboard
focusability**: an element whose content overflows its box (`scrollHeight
> clientHeight`) and which has `overflow: auto`/`scroll` is made
sequentially focusable via <kbd>Tab</kbd> so a keyboard-only user can
scroll it, *unless the element carries an explicit `tabindex` attribute*
(this is a deliberate browser accessibility feature — allowing keyboard
users to reach and scroll an overflow container that has no other
focusable descendant filling it — not a bug in either engine). Evidence
captured live from this lane's spec, both browsers, both locales
(`phase: "reproduction"` in the JSONL below):

- `hasTabindexAttr: false` — no `tabindex` attribute is ever authored on
  `list` in `combobox.js`.
- `tabIndexProp: -1` — the IDL property's ordinary default for an element
  with no `tabindex` attribute (not evidence of an explicit `-1`).
- `isScrollable: true`, `overflowY: "auto"`, `scrollHeight` (450/714px
  measured) `> clientHeight` (238px) — the list genuinely overflows its
  `max-height: 15rem` box once enough options render.
- `afterOneTab.role: "listbox"` — focus lands on the `UL` itself after a
  single <kbd>Tab</kbd> from the input, in **every** one of the four
  reproduction runs (chromium/no, chromium/en, firefox/no, firefox/en).

The fix-hypothesis run in this same lane isolates the mechanism further:
patching the DOM at runtime to add an **explicit** `tabindex="-1"`
attribute (`list.setAttribute('tabindex', '-1')` — *not* changing the
`.tabIndex` property, which already read `-1`; setting the attribute is
what differs) made the very next <kbd>Tab</kbd> skip the listbox entirely
and land on the next real control, in both Chromium and Firefox
(`phase: "fix-hypothesis"` in the JSONL below,
`listboxStillEntersTabOrder: false` in both). This directly demonstrates
the mechanism is the *absence of an authored attribute*, not the
property's default value, and that authoring the attribute is sufficient
to suppress it — consistent with both engines' own documented behavior
for this feature.

## Why this conflicts with the intended ARIA combobox pattern

`combobox.js` already implements the WAI-ARIA 1.2 "combobox with list
popup" pattern correctly everywhere else: `role="combobox"` +
`aria-expanded` + `aria-controls` + `aria-autocomplete="list"` on the
input (`combobox.js:32-35,42`), `role="listbox"` + `role="option"` on the
popup and its items (`combobox.js:41,93`), and roving virtual focus via
`aria-activedescendant` driven by <kbd>↑</kbd>/<kbd>↓</kbd>, with real DOM
focus deliberately staying on the input the entire time
(`combobox.js:105-133`, `_onKeydown`/`_move`). In that pattern the popup
listbox is never itself a Tab stop — a keyboard user reaches it only via
arrow keys once the input has focus, and a single <kbd>Tab</kbd> is
expected to leave the whole widget in one step. The browser's scrollable-
region heuristic breaks exactly that invariant: it inserts an *extra*,
unintended Tab stop whose accessible role (`listbox`) and content (a
scrollable option list with no roving-focus wiring of its own, since that
wiring lives on the input, not the `UL`) will read confusingly to
assistive tech, and adds a genuine extra keystroke for sighted keyboard
users on every combobox in the builder and pantry pages, essentially
every time one is used with focus (not just an edge case).

## Smallest safe fix options considered (not implemented in this lane)

1. **(Recommended)** Author `list.setAttribute("tabindex", "-1")` once, at
   construction time in `combobox.js`, alongside the existing
   `list.setAttribute("role", "listbox")` line
   (`combobox.js:41`). Live-verified in this lane (both browsers) to
   suppress the extra Tab stop with a single-line, additive change.
   Leaves `.tabIndex` semantics unchanged (already `-1`), leaves
   `overflow-y: auto`/mouse/touch/`scrollIntoView()` scrolling untouched
   (`_move()` already calls `scrollIntoView({ block: "nearest" })` for
   arrow-key navigation, `combobox.js:131`, unaffected either way), and
   touches no ARIA attribute already in place.
2. Not recommended: changing `.combobox-list`'s CSS (`overflow-y:
   visible`/`hidden`, or removing `max-height`) — would either break the
   deliberate scroll-contained popup (`box-shadow`/dropdown affordance) or
   let very long lists (e.g. the full malt/humle/style libraries) grow the
   popup unbounded, a much larger visual regression than the one line in
   option 1.
3. Not recommended: `aria-hidden="true"`/`inert` on the list container —
   would need to be toggled correctly with open/closed state (more
   surface for a regression) and is a heavier tool than the one-line,
   browser-native `tabindex="-1"` already proven sufficient here.

Option 1 is the smallest change that addresses the root cause directly at
its documented mechanism, is already confirmed effective in both target
engines, and changes nothing else about the combobox's existing (correct)
accessibility wiring.

## Suggested acceptance tests for a future fix PR

1. With a `Combobox` listbox open and overflowing (e.g. style or malt with
   an empty/short query), pressing <kbd>Tab</kbd> once from the combobox
   input moves focus to the **next real interactive control on the
   page** — not to the `.combobox-list`, not to any `.combobox-option` —
   for Chromium and Firefox, NO and EN (mirrors this lane's reproduction
   spec, which can be adapted into a permanent
   `tests/playwright/0X-a2-XX-combobox-tab-order.spec.js`).
2. The listbox remains scrollable by mouse wheel/touch/keyboard
   (<kbd>↓</kbd> past the visible region) when content exceeds
   `max-height` — guards against a future fix accidentally achieving (1)
   by breaking scroll instead (e.g. via `overflow: hidden`).
3. Existing arrow-key navigation is unchanged after the fix:
   <kbd>↓</kbd>/<kbd>↑</kbd> still move `aria-activedescendant` and the
   `.is-active` highlight class among `.combobox-option` elements, and
   <kbd>Enter</kbd> still selects the highlighted option — regression
   guard for the existing (already correct) roving-focus behavior this
   fix must not disturb.

## Evidence

Raw findings recorded by the throwaway spec's own `recordFinding()` calls
during the run described above (one JSON object per line;
`listboxEnteredTabOrder`/`listboxStillEntersTabOrder` are this brief's own
derived summary fields, computed directly from each run's captured
`afterOneTab.role`):

```jsonl
{"phase":"reproduction","browserName":"chromium","locale":"no","info":{"hasTabindexAttr":false,"tabIndexProp":-1,"scrollHeight":450,"clientHeight":238,"isScrollable":true,"overflowY":"auto"},"afterOneTab":{"tag":"UL","cls":"combobox-list","id":"combobox-2-listbox","role":"listbox"},"afterTwoTabs":{"tag":"INPUT","cls":"combobox-input","id":"","role":"combobox"},"listboxEnteredTabOrder":true}
{"phase":"reproduction","browserName":"chromium","locale":"en","info":{"hasTabindexAttr":false,"tabIndexProp":-1,"scrollHeight":714,"clientHeight":238,"isScrollable":true,"overflowY":"auto"},"afterOneTab":{"tag":"UL","cls":"combobox-list","id":"combobox-2-listbox","role":"listbox"},"afterTwoTabs":{"tag":"INPUT","cls":"combobox-input","id":"","role":"combobox"},"listboxEnteredTabOrder":true}
{"phase":"fix-hypothesis","browserName":"chromium","locale":"no","afterOneTab":{"tag":"INPUT","cls":"combobox-input","role":"combobox"},"listboxStillEntersTabOrder":false}
{"phase":"second-surface-spotcheck","surface":"malt","browserName":"chromium","locale":"no","afterOneTab":{"tag":"UL","role":"listbox"},"listboxEnteredTabOrder":true}
{"phase":"reproduction","browserName":"firefox","locale":"no","info":{"hasTabindexAttr":false,"tabIndexProp":-1,"scrollHeight":449,"clientHeight":238,"isScrollable":true,"overflowY":"auto"},"afterOneTab":{"tag":"UL","cls":"combobox-list","id":"combobox-2-listbox","role":"listbox"},"afterTwoTabs":{"tag":"INPUT","cls":"combobox-input","id":"","role":"combobox"},"listboxEnteredTabOrder":true}
{"phase":"reproduction","browserName":"firefox","locale":"en","info":{"hasTabindexAttr":false,"tabIndexProp":-1,"scrollHeight":713,"clientHeight":238,"isScrollable":true,"overflowY":"auto"},"afterOneTab":{"tag":"UL","cls":"combobox-list","id":"combobox-2-listbox","role":"listbox"},"afterTwoTabs":{"tag":"INPUT","cls":"combobox-input","id":"","role":"combobox"},"listboxEnteredTabOrder":true}
{"phase":"fix-hypothesis","browserName":"firefox","locale":"no","afterOneTab":{"tag":"INPUT","cls":"combobox-input","role":"combobox"},"listboxStillEntersTabOrder":false}
{"phase":"second-surface-spotcheck","surface":"malt","browserName":"firefox","locale":"no","afterOneTab":{"tag":"UL","role":"listbox"},"listboxEnteredTabOrder":true}
```

(Chromium/EN and Firefox/EN reproduction runs also passed with identical
`listboxEnteredTabOrder: true`/`role: "listbox"` results — two of the four
`reproduction`-phase JSONL lines above are the `en` locale runs already
shown; all four locale×browser combinations agree.)

## What this lane did not do

Per the owner's OVERNIGHT PREP LANE instruction: no product code
(`web/js/combobox.js`, `web/css/style.css`, or any other `web/**` file)
was changed. The throwaway reproduction/verification spec,
`tests/playwright/_tmp-184-investigation.spec.js`, and its
`test-results/kbh-184-findings.jsonl` output, were both deleted before
this branch's diff was finalized — this document is the only artifact
this lane leaves behind. No fix was implemented, no merge, no deploy, no
`#98`/`#100`, no owner-PC claims. This brief is implementation-ready but
implementation itself is a separate, future bounded fix issue for the
owner/Chief to scope.
