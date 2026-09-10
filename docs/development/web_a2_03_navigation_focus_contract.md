# Web A2-03 — Navigation hidden-focus + open-drawer containment: implementation-ready contract (issue #191)

*Part of KBDP. Reconciles two related current-production keyboard gaps found
across two audit passes — the B06 accessibility inventory / #186 measurement
(open-drawer half) and Astra Audit #2 finding A2-03 (both halves) — into one
smallest coherent implementation contract for a future implementation issue.
See [../../CLAUDE.md](../../CLAUDE.md) for the wider document system.*

**Status: docs-only implementation-ready brief. No `web/**` file is touched
by this issue.** Every file/line/selector reference below was re-verified
directly against current `master` (`web/index.html`, `web/css/style.css`,
`web/js/chrome.js`, `web/js/app.js`) at the time of writing, not carried over
unverified from either source document.

---

## 1. The problem, reconciled into one paragraph

Kvernhaug's web chrome — identical `.kompaktnav`/`.sidemeny` markup repeated
verbatim across every NO page (no shared partial/include, see §2), driven by
one shared behavior file, `web/js/chrome.js` — has three navigation surfaces
that change visibility at runtime —
`.kompaktnav` (sticky nav, hidden until scrolled past `.hero`), `.sidemeny`
(the side drawer, hidden until opened), and `.sidemeny-bakteppe` (its
backdrop) — plus one unrelated, already-correct dialog, `#modus-forstegang`
(the first-visit mode dialog, hidden via the `hidden` attribute, which
already removes it from both the tab order and the accessibility tree in
every browsable engine). The two navigation surfaces are **not** hidden via
`hidden` — they are hidden purely visually, via CSS `transform`/`opacity`/
`pointer-events`, which affects nothing about keyboard focusability or
accessibility-tree exposure. That single root cause produces both audit
findings:

- **A2-03 half 1 (hidden/off-screen controls in Tab order):** `.kompaktnav`'s
  hamburger button (`#meny-knapp-kompakt`) stays keyboard-focusable and
  keyboard-activatable while `.kompaktnav` sits off-screen above the
  viewport (`transform: translateY(-100%)`) before the user scrolls past the
  hero — `pointer-events: none` blocks *mouse* clicks in that state but does
  nothing to Tab order or Enter/Space activation. The same gap applies to
  every one of `.sidemeny`'s 15 focusable controls while the drawer sits
  off-screen to the left (`transform: translateX(-100%)`) — i.e. **the
  closed drawer's entire content stays in sequential Tab order and can
  receive off-screen focus**, not just the open drawer.
- **A2-03 half 2 / #186's already-decided half (open-drawer focus
  containment):** already measured in #186 (OPTION A, "add a bounded focus
  trap") and independently listed as B06 finding #14 / Batch 8 in
  [web_b06_accessibility_inventory.md](web_b06_accessibility_inventory.md) /
  [web_b06_implementation_batches.md](web_b06_implementation_batches.md).
  With the drawer open behind its 55%-opacity, pointer-blocking backdrop,
  Tab from the drawer's last focusable control (`.sidemeny-lenke` "Hjelp /
  Bryggehåndbok") leaks forward into background page content
  (`#oppskrift-navn` per #186's measurement), and Shift+Tab from the first
  focusable control (`.sidemeny-lukk`) leaks backward into header/background
  controls — with no trap keeping Tab/Shift+Tab inside the drawer while it
  is visibly (and, for pointer users, functionally) modal.

Both halves are gaps in **focus/interaction containment for a
visibility-toggled navigation surface** — one for the *closed* state, one
for the *open* state of the same two-part component family
(`.kompaktnav`/`.sidemeny`). That shared shape is what makes one coherent
contract possible instead of two unrelated patches.

## 2. Exact current-source evidence

**Source layout, relevant to every fix below:** there is no shared
partial/include/templating system for this chrome — `web/index.html`,
`web/pantry.html`, `web/verktoy.html`, `web/bryggelogg.html`,
`web/mine-oppskrifter.html`, `web/importer.html`, `web/utskrift.html`,
`web/personvern.html`, and `web/hjelp/*.html` each repeat the identical
`.kompaktnav`/`.sidemeny`/`.sidemeny-bakteppe` markup verbatim (confirmed
identical shape across all of them), with `web/en/**` generated 1:1 from
each. **`web/js/chrome.js` is the one genuinely shared file** — it is
loaded on every page and is the only place `.kompaktnav`/`.sidemeny`
*behavior* lives. This materially shapes §3 below: a fix confined to
`chrome.js` touches one file; a fix that also required a static-HTML
attribute change would need to touch every NO page listed above (then a
full `generate_web_i18n_pages.py` regeneration for `web/en/**`). §3.1 is
written to avoid that multiplication deliberately.

### 2.1 `.kompaktnav` (sticky nav) — closed/hidden state

`web/css/style.css:216-236`:

```css
.kompaktnav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 40;
  ...
  transform: translateY(-100%);
  opacity: 0;
  transition: transform 0.2s ease, opacity 0.2s ease;
  pointer-events: none;
}

.kompaktnav.synlig {
  transform: translateY(0);
  opacity: 1;
  pointer-events: auto;
}
```

Visibility toggled purely by class, in `web/js/chrome.js:16-24`
(`initHero`'s `oppdater()`), driven by scroll position vs. `.hero`'s own
height. No `hidden`, `aria-hidden`, `inert`, or `tabindex` management exists
anywhere in this path. `web/index.html:37-46` shows `.kompaktnav`'s single
focusable descendant relevant here: `#meny-knapp-kompakt` (the hamburger
button; the language-selector links inside `.kompaktnav-inner` are a second,
duplicate pair of `.sprak-knapp` anchors with the same off-screen-focus gap).

### 2.2 `.sidemeny` (drawer) — closed/hidden state

`web/css/style.css:330-352`:

```css
.sidemeny {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 280px;
  max-width: 82vw;
  ...
  transform: translateX(-100%);
  transition: transform 0.22s ease;
  z-index: 46;
  ...
}

.sidemeny.apen {
  transform: translateX(0);
}
```

Same pattern: `.apen` is a pure visual toggle (`web/js/chrome.js:82-98`,
`apne()`/`lukk()`), with no `hidden`/`aria-hidden`/`inert`/`tabindex`
anywhere. `.sidemeny-bakteppe` (`web/css/style.css:315-328`) already sets
`pointer-events: none` while closed and has no focusable descendants itself,
so it needs no focus-order fix — only the *containment* treatment below, for
defense-in-depth consistency with `.sidemeny`.

**The drawer's 15 focusable controls, in DOM order** (`web/index.html:51-86`,
matching #186's measured count exactly):

1. `.sidemeny-lukk` (close button)
2. `.sprak-knapp[data-sprak="no"]` (NO, current-page link)
3. `.sprak-knapp[data-sprak="en"]` (EN link)
4. `.enhet-knapp[data-enhet="metric"]`
5. `.enhet-knapp[data-enhet="us"]`
6. `.sidemeny-lenke` → Oppskriftsbygger
7. `.sidemeny-lenke` → Mine oppskrifter
8. `.sidemeny-lenke` → Importer oppskrift
9. `.sidemeny-lenke` → Utskrift
10. `.sidemeny-lenke` → Pantry/Lager
11. `.sidemeny-lenke` → Bryggelogg
12. `.sidemeny-lenke` → Verktøy
13. `.sidemeny-modus-knapp[data-modus="laerling"]`
14. `.sidemeny-modus-knapp[data-modus="mester"]`
15. `.sidemeny-lenke` → Hjelp / Bryggehåndbok

### 2.3 `initSidemeny()` — current open/close/focus logic

`web/js/chrome.js:63-111`, in full:

```js
function initSidemeny() {
  var knapper = document.querySelectorAll(".meny-knapp");
  var meny = document.querySelector(".sidemeny");
  var bakteppe = document.querySelector(".sidemeny-bakteppe");
  var lukkKnapp = document.querySelector(".sidemeny-lukk");
  if (!knapper.length || !meny || !bakteppe) return;

  var sisteApnetFra = null;

  function apen() {
    return meny.classList.contains("apen");
  }

  function settAriaExpanded(verdi) {
    knapper.forEach(function (k) {
      k.setAttribute("aria-expanded", verdi);
    });
  }

  function apne(fraKnapp) {
    sisteApnetFra = fraKnapp || knapper[0];
    meny.classList.add("apen");
    bakteppe.classList.add("apen");
    settAriaExpanded("true");
    document.body.classList.add("sidemeny-aktiv");
    var forsteLenke = meny.querySelector("a, button");
    if (forsteLenke) forsteLenke.focus();
  }

  function lukk() {
    meny.classList.remove("apen");
    bakteppe.classList.remove("apen");
    settAriaExpanded("false");
    document.body.classList.remove("sidemeny-aktiv");
    if (sisteApnetFra) sisteApnetFra.focus();
  }

  knapper.forEach(function (knapp) {
    knapp.addEventListener("click", function () {
      if (apen()) lukk();
      else apne(knapp);
    });
  });
  bakteppe.addEventListener("click", lukk);
  if (lukkKnapp) lukkKnapp.addEventListener("click", lukk);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && apen()) lukk();
  });
}
```

Focus-on-open (`:88-89`), focus-restore-on-close (`:97`), backdrop-click
(`:106`), and a permanently-attached, self-guarding Escape handler (`:108-
110`, attached once, no-ops via `apen()` when not open) are all already
correct and are explicitly preserved unchanged by this contract (§4).
**No Tab/Shift+Tab handling of any kind exists** — the confirmed root cause
of A2-03 half 2 / #186.

### 2.4 Existing ARIA — already correct, not to be changed

`web/index.html:23,39,52`: both `.meny-knapp` buttons already carry
`aria-expanded` (kept live by `settAriaExpanded()`) and `aria-controls=
"sidemeny"`; `.sidemeny` and `.kompaktnav` are both `<nav aria-label="…">`
landmarks already. **No `role="dialog"`/`aria-modal` exists on either
surface today, and this contract does not add either** — per the issue's
own hard guard, and because neither surface is being redesigned as a modal
dialog: `.kompaktnav` is a persistent nav bar (never modal), and the
drawer's own #186 rationale explicitly frames the fix as "completing the
existing focus-on-open/restore/Escape/backdrop pattern," not converting a
`<nav>` landmark into a `dialog` role. (Contrast with `#modus-forstegang`,
which legitimately *is* `role="dialog" aria-modal="true"` because it is a
true one-time modal choice screen, not a navigation landmark — that
distinction is exactly why this contract does not import its ARIA, only its
keyboard-trap *pattern*, see §3.2.)

### 2.5 Existing reusable trap pattern in this codebase

`web/js/app.js:348-390` (B06 batch 7, PR merged as `a96ebac`) already
implements a bounded, wrap-around Tab/Shift+Tab trap plus Escape for
`#modus-forstegang`:

```js
function _modusForstegangFokuserbare() {
  return Array.from(document.querySelectorAll("#modus-forstegang .modus-knapp"));
}

function _modusForstegangKeydownHandler(e) {
  if (e.key === "Escape") {
    _lukkModusForstegang();
    return;
  }
  if (e.key !== "Tab") return;
  const fokuserbare = _modusForstegangFokuserbare();
  if (fokuserbare.length === 0) return;
  const forste = fokuserbare[0];
  const siste = fokuserbare[fokuserbare.length - 1];
  const aktivIndeks = fokuserbare.indexOf(document.activeElement);
  if (e.shiftKey) {
    if (aktivIndeks <= 0) {
      e.preventDefault();
      siste.focus();
    }
  } else if (aktivIndeks === -1 || aktivIndeks === fokuserbare.length - 1) {
    e.preventDefault();
    forste.focus();
  }
}
```

attached/detached on open/close (`initModus()` / `_lukkModusForstegang()`).
This is the proof, cited by the issue's own "smallest coherent" framing,
that a wrap-around trap is a known, minimal-diff, already-shipped pattern in
this exact file tree — §3.2 below reuses its *shape*, adapted to
`chrome.js`'s own always-attached/self-guarding style (§2.3) rather than
copying its attach/detach-on-toggle style verbatim, to keep the diff to that
one file's existing idiom.

**Not directly reusable/importable:** these four functions are private
(`_`-prefixed, unexported) and live in `web/js/app.js`, which — unlike
`chrome.js` — is loaded only on `index.html`, not on every page (confirmed:
`pantry.html`/`verktoy.html`/etc. do not include `app.js`). §3.2 therefore
treats this as a **pattern to replicate inside `chrome.js`** (dynamic
focusable-query, cyclic wrap, one guard per direction), not code to call or
import — `chrome.js` already runs on every page, so the drawer fix has no
equivalent single-page limitation to design around.

## 3. Recommended smallest coherent contract

Two independent, additive fixes, both confined to `web/js/chrome.js` (plus
the two CSS rules noted), reusing existing project mechanisms — no new
dependency, no build step, no new ARIA role, no change to `.kbhrecipe`/
localStorage/i18n surfaces.

### 3.1 Fix A2-03 half 1 — `inert` on the closed navigation surfaces

Add the native `inert` boolean attribute/IDL property, toggled in lock-step
with the existing `.synlig`/`.apen` class toggles, to `.kompaktnav` and
`.sidemeny` (+ `.sidemeny-bakteppe`, for consistency even though it has no
focusable descendants today):

- `initHero()`'s `oppdater()` (`web/js/chrome.js:16-24`): alongside
  `kompaktnav.classList.toggle("synlig", synlig)`, add
  `kompaktnav.inert = !synlig;`.
- `initSidemeny()`'s `apne()`/`lukk()` (`web/js/chrome.js:82-98`): alongside
  the existing `classList.add/remove("apen")` calls, add
  `meny.inert = false; bakteppe.inert = false;` in `apne()` and
  `meny.inert = true; bakteppe.inert = true;` in `lukk()`.
- Initial-load state: **do not** add the `inert` attribute to the static
  HTML source. `.kompaktnav`/`.sidemeny` already ship with no `synlig`/
  `apen` class in the markup — both start visually hidden purely because
  the CSS default (§2.1/§2.2) is off-screen, with the JS-added class being
  the opt-*in* for "visible," never an opt-out for "hidden." `inert`
  should follow the exact same convention: set only by `initHero()`/
  `initSidemeny()` at `DOMContentLoaded` (both already run there today), not
  baked into the HTML. This keeps the entire fix confined to
  `web/js/chrome.js` — given §2's "no shared partial" constraint, a static-
  HTML-attribute requirement would instead mean editing every NO page listed
  in §2 plus a full i18n-generator regeneration, for a benefit (closing a
  sub-millisecond pre-`DOMContentLoaded` window no real Tab press can reach)
  that does not justify that multiplied diff. `.sidemeny-bakteppe` gets its
  `inert` toggle the same way, inside `apne()`/`lukk()`.

**Why `inert` and not `aria-hidden`/manual `tabindex="-1"`:** `inert` is a
single attribute per container that atomically removes every descendant
from the tab order *and* the accessibility tree *and* blocks pointer
interaction, with no per-control bookkeeping across the drawer's 15 (or the
kompaktnav's 3) focusable children, and with no interaction with the
existing `aria-expanded`/`aria-controls` pair (§2.4) — those stay exactly as
they are. `aria-hidden="true"` alone would not stop Tab from reaching the
element (it only affects the accessibility tree, a common pitfall this
contract deliberately avoids), and manual `tabindex="-1"` would require
individually managing and later restoring the original tab-reachability of
15 different elements including live `aria-current="page"` anchors — a
larger, more error-prone diff for the same outcome. `inert` also **subsumes
and does not conflict with** the existing `pointer-events: none` on
`.kompaktnav`/`.sidemeny-bakteppe` — both are safe to leave in place.

**Browser-support note (explicit decision point for whoever implements
this):** the `inert` attribute/property has been supported in all evergreen
engines since 2022 (Chromium 102, Firefox 112, Safari 15.5) — consistent
with this codebase's existing use of equally modern, unprefixed CSS
(`aspect-ratio`, `clamp()`) with no polyfill/fallback layer anywhere in
`web/**`. No regression risk exists for any engine that lacks `inert`
support: such an engine simply keeps today's exact (already-shipped)
behavior for that user, it does not newly break anything. This contract
treats that as sufficient justification to add `inert` with no fallback,
but flags it explicitly as a call for whoever opens the implementation
issue to confirm, not a silent assumption.

### 3.2 Fix A2-03 half 2 / #186 OPTION A — bounded Tab/Shift+Tab trap for the open drawer

Add one new keydown listener inside `initSidemeny()`, attached once
(matching the existing always-attached, self-guarding Escape handler style
at `web/js/chrome.js:108-110`, not the attach/detach-on-toggle style used by
`#modus-forstegang` — see §2.5), immediately after the existing Escape
listener:

```js
document.addEventListener("keydown", function (e) {
  if (e.key !== "Tab" || !apen()) return;
  var fokuserbare = Array.from(meny.querySelectorAll("a, button"));
  if (!fokuserbare.length) return;
  var forste = fokuserbare[0];
  var siste = fokuserbare[fokuserbare.length - 1];
  var aktivIndeks = fokuserbare.indexOf(document.activeElement);
  if (e.shiftKey) {
    if (aktivIndeks <= 0) {
      e.preventDefault();
      siste.focus();
    }
  } else if (aktivIndeks === -1 || aktivIndeks === fokuserbare.length - 1) {
    e.preventDefault();
    forste.focus();
  }
});
```

(`meny.querySelectorAll("a, button")` is the same selector `apne()` already
uses for its first-focusable lookup, §2.3 — reused here rather than
hardcoding the 15-item list from §2.2, so the trap never drifts from
whatever `apne()` itself considers "the drawer's focusable content" if a
future round adds/removes a drawer link.)

**Explicitly unchanged by this fix:** focus-on-open (`apne()` line `:88-89`),
focus-restore-on-close (`lukk()` line `:97`), Escape-to-close (already
correct, untouched), backdrop-click-to-close (already correct, untouched).
This is additive-only — the exact "preserving existing focus-on-open, exact
focus restore, Escape and backdrop behavior" instruction from both #186 and
this issue's own body.

**Interaction between §3.1 and §3.2 while the drawer is open:** none — while
`.sidemeny.apen`, `meny.inert` is `false` (§3.1), so every one of the 15
controls is normally focusable and the trap above governs where Tab/Shift+
Tab can go; `inert` only ever applies while the drawer is closed, at which
point the trap's own `!apen()` guard already makes it a no-op regardless.
The two fixes are independent and do not need to be sequenced relative to
each other in an implementation PR — either could ship alone, though
shipping both together is recommended since they resolve the same
audit finding and touch the same function.

## 4. Explicit non-goals

- **No `role="dialog"`/`aria-modal` added to `.kompaktnav` or `.sidemeny`** —
  per the issue's hard guard and §2.4's reasoning; both remain `<nav>`
  landmarks.
- **No change to `#modus-forstegang`** — its focus trap/Escape handling
  (B06 batch 7) already shipped and is only *referenced* here as a pattern
  (§2.5), not touched.
- **No change to focus-on-open, focus-restore-on-close, Escape, or
  backdrop-click behavior** for either `.kompaktnav` or `.sidemeny` — all
  already correct per #186's own measurement and preserved verbatim.
- **No new i18n keys, no visible text change, no NO/EN divergence risk** —
  every change is behavioral (JS) or a boolean attribute/CSS-adjacent
  property, so `python3 scripts/generate_web_i18n_pages.py` does not need to
  be re-run for this work and `tests/test_generate_web_i18n_pages.py` needs
  no new assertions.
- **No change to `.hero-topprad`'s own `.meny-knapp` (`#meny-knapp-hero`)** —
  it lives in `.hero`, which is never visibility-toggled (it scrolls away
  like ordinary page content, `web/css/style.css:98-100`), so it never had
  the off-screen-focus gap in the first place and needs no `inert` handling.
- **No Batch 9 (radar chart) or any other B06/#191-unrelated finding** — out
  of scope, unaffected by this contract.
- **Does not implement anything** — this document, like its predecessors,
  changes no file under `web/**`.

## 5. Acceptance matrix (for a future implementation round)

All cases below are keyboard/focus behavior, none are automatable in
`tests/` today (`.claude/rules/testing.md`: "There is no browser/E2E
coverage in `tests/`" for `web/**` runtime/focus behavior) — verification is
a manual Playwright sweep, per the `web-full-regression` skill, across
Chromium + Firefox × desktop + mobile viewport × NO + EN, exactly the
dimensions #186 already used for its half of this measurement.

| # | Scenario | Expected outcome |
|---|---|---|
| M1 | Load any page at the top (before scrolling past `.hero`); Tab forward from the page's first focusable control | `#meny-knapp-kompakt` and `.kompaktnav`'s two `.sprak-knapp` links are **never** reached — Tab moves directly from `#meny-knapp-hero`/hero content to whatever follows `.kompaktnav` in DOM order |
| M2 | Scroll past `.hero` so `.kompaktnav.synlig` is active; Tab forward | `#meny-knapp-kompakt` and its `.sprak-knapp` links **are** reachable and activatable exactly as today — confirms `inert` is correctly released, not just added |
| M3 | With the drawer closed, Tab through the whole page | None of the 15 controls in §2.2 are reached at any point, on any page that includes the shared drawer markup |
| M4 | Open the drawer via keyboard (Enter/Space on a `.meny-knapp`) | Focus moves to `.sidemeny-lukk` exactly as today (regression check — unchanged behavior) |
| M5 | From `.sidemeny-lukk` (drawer open), Shift+Tab | Focus wraps to the **last** focusable control (Hjelp / Bryggehåndbok link), not out to header/background content |
| M6 | From the Hjelp / Bryggehåndbok link (drawer open, last control), Tab | Focus wraps to `.sidemeny-lukk` (the **first** control), not out to `#oppskrift-navn`/background content |
| M7 | With the drawer open, attempt to Tab into any control behind the backdrop (e.g. `#oppskrift-navn`) | Unreachable via keyboard for the entire duration the drawer is open |
| M8 | Press Escape while the drawer is open | Drawer closes; focus restored to the exact opener button — unchanged from today |
| M9 | Click the backdrop while the drawer is open | Drawer closes; focus restored to the exact opener button — unchanged from today |
| M10 | Close the drawer (any method in M8/M9, or the close button), then Tab through the page again | Behaves exactly as M3 again — `inert` correctly re-applied on close, no leftover focusability from the just-closed state |
| M11 | Repeat M1-M10 on mobile viewport | Identical outcomes — `inert`/trap logic is viewport-independent; drawer's own responsive sizing (`max-width: 82vw`) is unaffected by either fix |
| M12 | Repeat M1-M10 in both NO and EN | Identical outcomes both languages; 0 raw i18n keys (none introduced) |
| M13 | Inspect `.kompaktnav`/`.sidemeny`/`.sidemeny-bakteppe` in DevTools across all states above | No `role="dialog"`/`aria-modal` present at any point (confirms §4's non-goal held) |
| M14 | Full scenario set M1-M13 | 0 console/page errors, both Chromium and Firefox |

## 6. Unresolved questions for whoever opens the implementation issue

1. **`inert` browser-support baseline** (§3.1) — this brief recommends
   adding it with no fallback, on the grounds that no regression is possible
   for any engine lacking support; confirm that reasoning still holds at
   implementation time (e.g. no newly-discovered support requirement for an
   older engine).
2. **Whether `.hero-topprad`'s language-selector duplicate
   (`.sprakvelger-kompakt` inside `.kompaktnav`, `web/index.html:41-44`) is
   intentionally redundant with the hero's own language selector** — both
   exist today and neither is touched by this contract, but it is a
   pre-existing duplication this brief noticed while enumerating
   `.kompaktnav`'s focusable content (§2.1) and did not investigate further,
   since it is unrelated to A2-03's containment gap.
3. **Batching**: should this ship as a single implementation issue covering
   both §3.1 and §3.2 (recommended, since both are additive, low-risk, and
   confined to the same function/file), or split into two, mirroring how
   the B06 plan originally separated the drawer trap (Batch 8) from the
   (never-filed) hidden-controls half? This brief recommends one combined
   issue given the shared root cause (§1) and shared verification sweep
   (§5), but does not decide it.
