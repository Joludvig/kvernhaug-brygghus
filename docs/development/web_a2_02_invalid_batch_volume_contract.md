# Web A2-02 — Invalid/zero batch-volume gate before save/start brewing: implementation-ready contract (issue #190)

*Part of KBDP. Astra Audit #2 finding A2-02 (MEDIUM), confirmed on production
`6841d047...`: empty or zero batch volume yields OG/FG 1.000, ABV/IBU/EBC 0; a
variant can be reported saved and "Start brewing" can freeze a 0 L plan in the
brew log. See [../../CLAUDE.md](../../CLAUDE.md) for the wider document
system.*

**Status: docs-only implementation-ready brief. No `web/**` file is touched by
this issue** (per the issue's own "WORKDAY PREP LANE" scope and its retry
comment). Every file/line reference below was re-verified directly against
current `master` (`0c2bfb1`) at the time of writing — not carried over from
the audit report unverified.

---

## 1. The problem, restated precisely

`#batch-volum` (`web/index.html:179`) is a plain
`<input type="number" id="batch-volum" min="0" step="0.1" value="20">`, with
no `required` attribute, and — critically — **not inside a `<form>`**: every
recipe-builder control lives in a bare `<main class="byggerlayout">`
(`web/index.html:154`), and "Lagre"/"Lagre som variant"/"Start brygging" are
all `<button type="button">` wired via `addEventListener("click", ...)`
(`web/js/app.js:1939-1951`). There is no form submission event anywhere on
this page and nothing ever calls `.checkValidity()`/`.reportValidity()`, so
`min="0"` is decorative today — it constrains the spinner arrows only, not
typed input, and does nothing about an emptied field. **Any fix has to be
enforced in JS; the HTML attribute is not a control surface here.**

Emptying the field or typing `0` both converge, before any calculation code
runs, on the exact same numeric state:

- `web/js/units.js:43-47`, `parseVolume()`: `parseFloat("")` is `NaN`, so an
  emptied field parses to `NaN`.
- `web/js/app.js:63-70`, `_lesEnhetsfelt()`: `return isFinite(tolket) ? tolket
  : 0;` — silently coerces that `NaN` to `0`.
- `web/js/app.js:1478`, `samleOppskrift()`: `volum:
  _lesVolumFelt(document.getElementById("batch-volum"))` — so
  `oppskrift.volum` is **always** a finite JS number by the time any
  downstream code sees it; "empty" and "explicit 0" are the *same* state
  (`0`), never `null`/`undefined`/`NaN`. This simplifies the fix: one
  predicate (`volum > 0`) closes both cases at once, with no separate
  "was it empty vs. zero" branch needed anywhere.

That `volum: 0` then flows, unguarded, through calculation, save, and
start-brewing:

```js
// web/js/calc.js:11-22
function beregnOG(valgtMaltListe, maltData, volum, effektivitet) {
  let totalePoeng = 0;
  for (const m of valgtMaltListe) { /* ... */ }
  if (volum === 0) return 1.0;
  return 1 + ((totalePoeng * effektivitet * 8.3454) / volum) / 1000;
}
```
```js
// web/js/calc.js:24-38 — EBC
if (volum <= 0) return 0;
```
```js
// web/js/calc.js:56-61 — FG/ABV, driven by OG
function beregnFgOgAbv(og, attenuation) {
  if (og <= 1.0) return { fg: 1.0, abv: 0.0 };
  ...
}
```
```js
// web/js/calc.js:96-97 — IBU
function beregnTotalIBU(valgtHumleListe, humleData, volum, beregnetOG) {
  if (volum === 0 || beregnetOG <= 1.0) return 0;
  ...
```

This is the literal source of "OG/FG 1.000, ABV/IBU/EBC 0" — each guard exists
only to avoid a division by zero, not to signal "this input is invalid," and
none of the three product touchpoints downstream ever check `volum` before
acting on the result.

## 2. Exact current-source evidence

### 2.1 Save / Save-as-variant — no volume check exists

`web/js/app.js:1592-1604` (`lagreOppskrift`) and `web/js/app.js:1636-1653`
(`lagreSomVariant`) both go straight from `samleOppskrift()` to
`lagreOppskriftIStore(oppskrift, ...)` with no precondition. The only gate
inside that store function is a pure **shape** check, never a value check:

```js
// web/js/recipe_storage.js:61-64
function _erOppskriftForm(o) {
  if (!o || typeof o !== "object" || Array.isArray(o)) return false;
  return ["navn", "malt", "humle", "gjaerId", "gjaerCustom", "volum", "brygger", "bryggeri"].some((f) => f in o);
}
```
```js
// web/js/recipe_storage.js:248-260
function lagreOppskriftIStore(recipe, recipeId) {
  if (!_erOppskriftForm(recipe)) return { ok: false, melding: t("oppskrift.lagreFeil") };
  const state = lesOppskriftState();
  const normalisert = _normalisertRecipe(recipe);
  const id = recipeId || _genererRecipeId();
  state.items = state.items.filter((i) => i.recipeId !== id && i.recipe.navn !== normalisert.navn);
  state.items.push({ recipeId: id, recipe: normalisert });
  if (!_skrivOppskriftState(state)) return { ok: false, melding: t("oppskrift.lagreFeil") };
  return { ok: true, recipeId: id };
}
```
A recipe/variant with `volum: 0` (or any other degenerate value) saves
unconditionally — confirming the audit's "a variant can be reported saved"
observation exactly.

### 2.2 Start brewing / frozen `.kbhbrew` plan — the same gap, plus a footgun

```js
// web/js/app.js:1740-1757
function startBrygging() {
  const status = document.getElementById("brygg-start-status");
  const oppskrift = samleOppskrift();
  if (!oppskriftHarInnhold(oppskrift)) {
    status.textContent = t("builder.brygg.tomOppskrift");
    return;
  }
  const beregning = beregnOppskrift(oppskrift, maltData, humleData, gjaerData, bjcpStyles);
  const snapshot = byggBrewSnapshot(oppskrift, beregning, maltData, humleData, gjaerData, hentAktivUtstyrsprofil());
  const res = opprettBrygg({ snapshot, recipeId: _aktivRecipeId });
  if (!res.ok) {
    status.textContent = res.melding;
    return;
  }
  status.textContent = t("builder.brygg.startetStatus", { navn: visningsnavn(oppskrift.navn) || t("identitet.utenNavn") });
}
```
The only existing gate, `oppskriftHarInnhold()`, checks for *any* content, not
volume validity:

```js
// web/js/kbhrecipe.js:108-121
function oppskriftHarInnhold(o) {
  if (!o || typeof o !== "object") return false;
  return !!(
    (o.navn && o.navn !== "Uten navn") ||
    o.notater ||
    (Array.isArray(o.malt) && o.malt.length > 0) ||
    (Array.isArray(o.humle) && o.humle.length > 0) ||
    o.gjaerId || o.gjaerCustom || o.valgtStil ||
    (typeof o.volum === "number" && o.volum !== 20) ||
    (typeof o.effektivitet === "number" && o.effektivitet !== 75)
  );
}
```
Line 118's `o.volum !== 20` means a zeroed-out volume **by itself** — with no
malt, no hops, no name — already satisfies "has content" (it differs from the
`20` default), so a recipe with only an emptied batch-volume field sails
straight past this guard. `byggBrewSnapshot()` and `opprettBrygg()` then only
validate object *shape*, never numeric sanity:

```js
// web/js/brew_storage.js:215-220
function _gyldigSnapshot(s) {
  if (!_erObjekt(s)) return false;
  if (!_erObjekt(s.recipe)) return false;
  if (!_erObjekt(s.predicted)) return false;
  return true;
}
```
```js
// web/js/brew_storage.js:466-484
function opprettBrygg({ snapshot, recipeId, parentBrewId }) {
  if (!_gyldigSnapshot(snapshot)) return { ok: false, melding: t("brygg.feilUgyldigSnapshot") };
  ... // no volume/stat check anywhere in this path
}
```
So a `0 L` plan with `OG=1.000/FG=1.000/ABV=0/IBU=0/EBC=0` passes both checks
and is written into the brew log (`BREW_FIL_FORMAT = "kbhbrew"`,
`web/js/brew_storage.js:30`). Per that module's own header comment
(`web/js/brew_storage.js:168-171`): *"Skrives ÉN gang, ved opprettelse, og
endres deretter aldri — Uforanderligheten ER poenget"* ("written once, at
creation, and never changed afterward — immutability IS the point"). That
frozen `0`/degenerate state is then rendered permanently in Bryggeloggen
(`web/js/brygg_page.js:35-43`, `_planTekst()`: `"Planlagt: OG {og} · FG {fg} ·
{abv} % · {volum}"` → literally "Planlagt: OG 1.000 · FG 1.000 · 0,0 % ·
0 L") — this is the audit's "freeze a 0 L plan in the brew log" finding,
confirmed line-for-line.

### 2.3 The architectural constraint that shapes the entire fix: `calc.js`/Python parity

`web/js/calc.js:1-2` states its own contract: *"Beregningsformler portert fra
modules/calculations.py ... hold i sync manuelt hvis formlene endres i
Python-siden"* ("ported from the Python side; keep in sync manually if the
formulas change there"). `modules/calculations.py:28-40` (`beregn_og`) has the
**identical** zero-volume guard, value-for-value:

```python
def beregn_og(valgt_malt_liste, malt_data, volum, effektivitet):
    ...
    if volum == 0:
        return 1.000
    return 1 + ((totale_poeng * effektivitet * 8.3454) / volum) / 1000
```

This manual JS/Python duplication is **not just documentation** — it is
actively, deterministically enforced by
[`tests/test_web_calc_js_parity.py`](../../tests/test_web_calc_js_parity.py),
which reads both live source files and asserts, with real value/sequence
equality (not a pattern match), that every shared numeric constant and the
ordered sequence of numeric literals/comparison operators/arithmetic
operators in each ported function body are identical between the two
languages. **Any change to `beregnOG`/`beregnEBC`/`beregnFgOgAbv`/
`beregnTotalIBU`'s zero/negative-volume return values in `calc.js` — e.g.
throwing, returning `NaN`, or changing the guard's comparator — would
desynchronize from `modules/calculations.py` and fail this test**, which
would in turn require a matching Python/`modules/calculations.py` edit. The
issue's own retry contract is explicit: *"No App/Core/schema changes unless
a proven shared contract defect requires a separate issue."* Nothing here is
a shared-contract *defect* — both sides already agree byte-for-byte on
returning `1.0`/`0` for a zero-volume input, by design, to avoid a division
by zero during live, incremental typing. **This decisively shapes §3 below:
the gate cannot live in `calc.js` or `recipe_engine.js` — it must live at the
UI/action layer** (`app.js`'s save/start-brewing functions), leaving the
shared calculation engine's zero-volume return values completely untouched
on both sides of the port.

The same reasoning applies to `web/js/recipe_engine.js:57-58`
(`beregnOppskrift`'s own `const volum = parseFloat(oppskrift.volum) || 0;`,
a second, independent zero-defaulting used by both the builder and the
Utskrift/print page) — this defensive fallback exists for *any* caller,
including recipes reconstructed from `.kbhrecipe` files/older schema
versions with a missing `volum` field, and is out of scope for the same
reason: it is shared, DOM-free, print-page-facing code, not a place a
save/start-brewing-specific gate belongs.

### 2.4 Existing reusable validation pattern in this exact codebase

`web/js/equipment.js:120-132` already implements precisely the shape this fix
needs — a synchronous "translate invalid fields to a message, or `null`"
validator, for the conceptually adjacent "kettle capacity"/"max recommended
batch" fields:

```js
// web/js/equipment.js:120-132
function _validerUtstyrsfelt({ name, kettleCapacityL, maxRecommendedBatchL }) {
  if (!name || !String(name).trim()) return t("utstyr.feilNavnPakrevd");
  const kap = parseFloat(kettleCapacityL);
  if (!isFinite(kap) || kap <= 0) return t("utstyr.feilKapasitetPositiv");
  if (maxRecommendedBatchL !== undefined && maxRecommendedBatchL !== null && String(maxRecommendedBatchL).trim() !== "") {
    const maks = parseFloat(maxRecommendedBatchL);
    if (!isFinite(maks) || maks <= 0) return t("utstyr.feilMaksPositiv");
    if (maks > kap) return t("utstyr.feilMaksOverstigerKapasitet");
  }
  return null;
}
```
used as `{ ok, melding }` gate (`web/js/equipment.js:150-158`,
`opprettCustomUtstyrsprofil`), consumed exactly like
`lagreOppskriftIStore`/`opprettBrygg` already are today
(`web/js/app.js:1225-1231`: `if (!resultat.ok) { _visUtstyrSkjemaMelding(resultat.melding); return; }`).

Even closer precedent — **on the very same page, for the very same field** —
`skalerOppskrift()` already treats `volum <= 0` as the definition of
"invalid volume" and blocks on it:

```js
// web/js/app.js:969-979
function skalerOppskrift() {
  const volumInput = document.getElementById("batch-volum");
  const naavaerende = _lesVolumFelt(volumInput);
  const maalInput = document.getElementById("skaler-maal-volum");
  const maal = _lesVolumFelt(maalInput);
  const statusEl = document.getElementById("skaler-status");
  if (naavaerende <= 0 || maal <= 0) {
    statusEl.textContent = t("builder.skaler.statusUgyldig"); // NO: "Ugyldig volum -- skalering avbrutt."
    return;
  }
  ...
```
This is direct proof that "`#batch-volum` invalid ⇒ block the action and show
a status message" is already an established, shipped convention for this
exact input — Save/Save-as-variant/Start-brewing are simply the three places
it was never applied. The equipment inputs even carry the HTML-level parity
already recommended below: `web/index.html:136,140`,
`<input id="utstyr-felt-kapasitet" min="0.01" step="0.01" required>` /
`<input id="utstyr-felt-maks" min="0.01" step="0.01">` (vs. `#batch-volum`'s
`min="0"`).

Both `lagreOppskrift()`/`lagreSomVariant()` and `startBrygging()` already
speak the same `if (!res.ok) { status.textContent = res.melding; return; }`
idiom against the **existing** `aria-live="polite"` status paragraphs —
`#lagre-status` (`web/index.html:269`) and `#brygg-start-status`
(`web/index.html:255`) — so a volume gate needs **zero new markup**, exactly
as the A2-03 contract found for its own fix.

### 2.5 `web/js/i18n.js` naming convention for validation messages

Flat `TEKSTER = { no: {...}, en: {...} }` dictionary (`web/js/i18n.js:213-214`
NO, `:1967` EN), 1:1 key-symmetric, verified by
`tests/test_generate_web_i18n_pages.py`. Convention:
`<namespace>.feil<Beskrivelse>` / `<namespace>.ugyldig<Beskrivelse>`:

| Key | NO | EN |
|---|---|---|
| `utstyr.feilKapasitetPositiv` (`:339`/`:2092`) | "Kjelekapasitet må være et tall større enn 0." | "Kettle capacity must be a number greater than 0." |
| `builder.skaler.statusUgyldig` (`:416`/`:2169`) | "Ugyldig volum -- skalering avbrutt." | "Invalid volume -- scaling cancelled." |
| `oppskrift.lagreFeil` (`:455`/`:2208`) | "Kunne ikke lagre oppskriften i nettleseren. ..." | "Couldn't save the recipe in this browser. ..." |
| `builder.brygg.tomOppskrift` (`:476`/`:2229`) | "Legg inn litt malt eller humle først — da har brygget noe å huske." | "Add some malt or hops first — then the brew has something to remember." |

A new key fits directly into this convention, reusing `utstyr.feilKapasitetPositiv`'s
exact phrasing shape (see §3.3).

### 2.6 Scope confirmation — one page, no i18n-generator run needed

`#batch-volum`/`#start-brygging-knapp`/`#lagre-knapp`/`#lagre-variant-knapp`
exist only in `web/index.html` (confirmed: no other NO page contains them).
`web/en/index.html` is 1:1 generated from it by
`scripts/generate_web_i18n_pages.py` (registered in the generator's `PAGES`
list) — same markup, same `web/js/*.js` files loaded via relative paths, only
label text differs. Because every proposed message here is a **dynamic
status string** (`t("...")` called from JS, never a new `data-i18n="..."`
attribute on static HTML), adding the new `TEKSTER` key pair does not change
any generated page's byte content — `python3 scripts/generate_web_i18n_pages.py`
would produce a no-op diff for this specific change (still worth a
confirmation run at implementation time, per `.claude/rules/web.md`, but not
a source of new `web/en/**` content).

## 3. Recommended smallest coherent contract

### 3.1 Answers to the issue's four product-contract questions

1. **May an incomplete/invalid recipe remain autosaved as a draft?**
   **Yes, unchanged.** The autosave path (`web/js/app.js:1017-1053`,
   `beregnOgVisResultat()` → `localStorage.setItem(AKTIV_KLADD_NOKKEL, ...)`,
   fired on every keystroke including `#batch-volum`'s `input` listener at
   `:1909-1912`) must stay ungated. It is private, continuously-overwritten
   scratch space for a recipe still being typed — not a named, shareable
   artifact — and blocking it would break normal typing (the field is
   legitimately empty for a moment on every edit) and contradicts this
   project's own stated philosophy for brew/recipe drafts
   (`web/js/brygg_page.js:10-14`: *"Ingen felt er påkrevd, alt kan fylles ut
   senere"* — "no field is required, everything can be filled in later").
   The live result panel already shows the honest (if unflagged) numbers for
   whatever is currently typed; §3.4 below adds an optional, non-blocking
   improvement there.
2. **May it be explicitly saved as a recipe/variant?** **No.** Block both
   "Lagre oppskrift" and "Lagre som variant" identically — same predicate,
   same message — when `volum <= 0`.
3. **Exact validity gate for Start brewing / frozen `.kbhbrew` creation:**
   `volum > 0` (a finite number strictly greater than zero), checked
   **before** `beregnOppskrift()`/`byggBrewSnapshot()`/`opprettBrygg()` run —
   identical predicate to (2), so a recipe that could not be saved could
   also never be brewed, and vice versa.
4. **User-facing NO/EN validation message/state:** reuse the existing
   `aria-live="polite"` status paragraphs already wired to every one of these
   three actions (`#lagre-status`, `#brygg-start-status`) — no new markup —
   with one new, shared `TEKSTER` key pair (§3.3).

### 3.2 Where the gate lives — confined to `web/js/app.js`

Per §2.3, the fix must **not** touch `web/js/calc.js`, `web/js/recipe_engine.js`,
or `modules/calculations.py` — those stay byte-for-byte as they are today,
zero-volume guards included, so live typing never throws or shows `NaN` mid-edit
and the parity test (`tests/test_web_calc_js_parity.py`) never needs a
matching Python change. The entire fix is three small, additive call sites in
`web/js/app.js`, following the `_validerUtstyrsfelt` pattern from §2.4.

### 3.3 Exact recommended change

One new helper, mirroring `_validerUtstyrsfelt`'s "value or `null`" contract:

```js
// New, in web/js/app.js (near samleOppskrift()/lagreOppskrift(), no DOM dependency beyond the recipe object already collected)
function _validerOppskriftVolum(oppskrift) {
  if (!(oppskrift.volum > 0)) return t("oppskrift.feilVolumPositiv");
  return null;
}
```
`!(oppskrift.volum > 0)` (rather than `oppskrift.volum <= 0`) is deliberate:
`oppskrift.volum` is always a finite number by construction (§1,
`_lesEnhetsfelt`'s `isFinite(...) ? ... : 0` fallback), but writing the check
this way fails closed even if that guarantee is ever weakened later, exactly
mirroring `_validerUtstyrsfelt`'s own `!isFinite(kap) || kap <= 0` defensive
style.

Three call sites, each gated **before** doing anything with side effects:

```js
// web/js/app.js:1592, lagreOppskrift() — insert as the first statement
function lagreOppskrift() {
  const oppskrift = samleOppskrift();
  const status = document.getElementById("lagre-status");
  const feil = _validerOppskriftVolum(oppskrift);
  if (feil) { status.textContent = feil; return; }
  const res = lagreOppskriftIStore(oppskrift, _aktivRecipeId);
  ...
```
```js
// web/js/app.js:1636, lagreSomVariant() — same check, same message, before any lagreOppskriftIStore() call
function lagreSomVariant() {
  const navnFelt = document.getElementById("oppskrift-navn");
  let oppskrift = samleOppskrift();
  const status = document.getElementById("lagre-status");
  const feil = _validerOppskriftVolum(oppskrift);
  if (feil) { status.textContent = feil; return; }
  ...
```
```js
// web/js/app.js:1740, startBrygging() — inserted as a second guard, after the existing empty-recipe check
function startBrygging() {
  const status = document.getElementById("brygg-start-status");
  const oppskrift = samleOppskrift();
  if (!oppskriftHarInnhold(oppskrift)) {
    status.textContent = t("builder.brygg.tomOppskrift");
    return;
  }
  const feil = _validerOppskriftVolum(oppskrift);
  if (feil) { status.textContent = feil; return; }
  const beregning = beregnOppskrift(oppskrift, maltData, humleData, gjaerData, bjcpStyles);
  ...
```
**Why after, not instead of, `oppskriftHarInnhold()`:** preserves the
existing, more specific "nothing to brew at all" message
(`builder.brygg.tomOppskrift`) for a genuinely empty recipe, and only surfaces
the new volume-specific message once the recipe is judged non-empty by
today's rule — §2.2's footgun (volume alone satisfying "has content") stops
mattering either way, since a `volum <= 0` recipe now always fails at this
second check regardless of which branch of `oppskriftHarInnhold()` let it
through.

**One shared key, both languages**, following `utstyr.feilKapasitetPositiv`'s
established phrasing and grammatical shape exactly, added to both `TEKSTER.no`
(near `web/js/i18n.js:455`, `oppskrift.*` namespace) and `TEKSTER.en` (near
`:2208`):

```js
"oppskrift.feilVolumPositiv": "Batchvolum må være et tall større enn 0 liter.",
```
```js
"oppskrift.feilVolumPositiv": "Batch volume must be a number greater than 0 liters.",
```
Namespaced under `oppskrift.*` (not `builder.brygg.*`) because it is reused
verbatim from `startBrygging()` too — already precedented by
`brygg.feilUgyldigSnapshot` (a `brygg.*`-namespaced key) being called from
inside this same `builder.brygg`-labeled button handler today
(`web/js/app.js:1751`); cross-namespace reuse from `startBrygging()` is
already how this file is organized, not a new convention.

### 3.4 Optional, non-blocking complement (not required for this contract)

`web/js/app.js:1139-1150`, `_oppdaterUtstyrBatchAdvarsel()`, already shows a
precedent for a **live, non-blocking** inline warning next to
`#batch-volum` (`#utstyr-batch-advarsel`, `web/index.html:188`), updated on
every `beregnOgVisResultat()` call. A future implementation round could
reuse this exact pattern to show a passive "Batchvolum må være større enn 0"
hint while the field is `<= 0`, **without** blocking the live OG/FG/ABV/IBU/EBC
numbers or the autosaved draft (§3.1.1) — this is a nice-to-have UX
improvement, not required to close the audit finding, and is called out here
only so a future implementer doesn't have to rediscover the pattern. See §6,
open question 3.

### 3.5 Optional HTML parity note (not required, low-risk if taken)

`#batch-volum`'s `min="0"` (`web/index.html:179`) could be tightened to
`min="0.1"` (matching its own `step="0.1"`) for parity with the equipment
fields' `min="0.01"` (`web/index.html:136,140`). As established in §1, this
has **no functional effect** on its own (no form validation ever runs) — it
only affects the native spinner-arrow floor and would need the identical
1-line edit mirrored into `web/en/index.html` via the generator. Purely
cosmetic/consistency; the real fix is §3.3's JS gate regardless of whether
this is taken.

## 4. Save-vs-start-brew distinction, stated explicitly

| Touchpoint | Trigger | Gate today | Gate after this contract | Rationale |
|---|---|---|---|---|
| Autosaved draft (`AKTIV_KLADD_NOKKEL`) | Every keystroke (`beregnOgVisResultat()`) | None | **Unchanged — none** | Private scratch space; §3.1.1 |
| "Lagre oppskrift" (`lagreOppskrift`) | Explicit click | Shape-only (`_erOppskriftForm`) | Shape-only **+ `volum > 0`** | A named, persisted, later-reloadable recipe |
| "Lagre som variant" (`lagreSomVariant`) | Explicit click | Shape-only (`_erOppskriftForm`) | Shape-only **+ `volum > 0`** | Same artifact class as above, same predicate |
| "Start brygging" (`startBrygging`) | Explicit click | `oppskriftHarInnhold()` (content, not validity) | `oppskriftHarInnhold()` **+ `volum > 0`** | Freezes an *immutable* `.kbhbrew` snapshot — never editable after creation (§2.2), so this is the highest-stakes of the three and must never admit a degenerate plan |

All three explicit-action gates share **one** predicate and **one** message
(§3.3) — there is no product reason for Save and Start-brewing to disagree on
what counts as a valid batch volume, and a shared predicate is what keeps this
"smallest coherent," per this project's own recurring phrase for this class of
brief.

## 5. Explicit non-goals

- **No change to `web/js/calc.js`, `web/js/recipe_engine.js`, or
  `modules/calculations.py`** — their zero/negative-volume return values stay
  exactly as they are (§2.3); live typing continues to show `OG 1.000` etc.
  while volume is `0`, same as today, so the parity test
  (`tests/test_web_calc_js_parity.py`) needs no change and no App/Core PR is
  required.
- **No change to negative-volume handling inside `calc.js` itself.** A
  manually typed negative number (e.g. `-5`, not blockable by `min="0"` since
  no form validation runs, §1) is inconsistently guarded today —
  `beregnEBC` uses `volum <= 0` but `beregnOG`/`beregnTotalIBU` use
  `volum === 0` only, so a negative volume could drive a nonsensical OG/IBU
  during live preview. This contract's §3.3 gate incidentally closes negative
  volume for the three **persisted/frozen** touchpoints (Save/Save-as-variant/
  Start-brewing all use `volum > 0`, rejecting negative too), but the
  live-preview-only inconsistency inside `calc.js` remains unfixed by design
  (§2.3) — flagged as an open question in §6, not silently expanded into this
  issue's scope.
- **No change to `oppskriftHarInnhold()`'s existing default-value semantics**
  (§2.2, `volum !== 20`) — it stays exactly as-is; §3.3 adds a second,
  independent check after it rather than altering its logic, so every other
  caller of `oppskriftHarInnhold()` (the "New recipe"/"Open file"
  discard-confirmation prompts) is completely unaffected.
- **No i18n-generator-visible change** — the new key is dynamic-JS-only
  (§2.6); `web/en/index.html` needs no new text, only the generator
  confirmation run noted there.
- **No new UI markup** — reuses `#lagre-status`/`#brygg-start-status`
  (§2.4); §3.4's inline-warning idea is explicitly optional/deferred, not
  part of this contract's required scope.
- **No `.kbhrecipe`/schema/localStorage-key change** — this is a
  precondition on existing save/start actions, not a data-format change; no
  migration is needed or implied.
- **Does not implement anything** — like its predecessors, this document
  changes no file under `web/**`.

## 6. Automated tests — what exists, what's blocked, what a future round should add

**Existing JS-level test infrastructure is currently non-functional for this
area, for reasons unrelated to this contract.**
[`tests/web_js_runtime.py`](../../tests/web_js_runtime.py)'s `run_web_js()` —
the harness that would execute real `web/js/*.js` source via Node for
`tests/test_web_js_calc.py`, `tests/test_web_js_kbhrecipe.py`, and
`tests/test_web_js_brew_storage.py` — is **deliberately blocked** (Chief
review, PR #53): shelling out to `node` from an allowed
`python3 -m unittest ...` process was found to be a Bridge `--allowedTools`
circumvention, so `run_web_js()` refuses to run and every test in those three
files is `@unittest.skip`-ped, including the ones most relevant here:
`TestBeregnOG.test_zero_volume_returns_1`, `TestBeregnEBC.test_non_positive_volume_returns_0`
(`tests/test_web_js_calc.py`), and `TestOpprettOgLesBrygg.test_ugyldig_snapshot_avvises`
(`tests/test_web_js_brew_storage.py`, shape-only — no existing golden vector
covers a *valid-shape-but-zero-volume* snapshot). `node` is not, and per the
PR #53 review should not casually become, part of this Bridge's
`--allowedTools`; re-enabling `run_web_js()` needs its own separate,
explicitly reviewed permission-model change, not something a Web-content PR
should smuggle in.

**Active, non-blocked coverage today** is
[`tests/test_web_calc_js_parity.py`](../../tests/test_web_calc_js_parity.py)
— source-level literal/operator-sequence comparison between `calc.js` and
`modules/calculations.py`, requiring zero Node execution. §3.2/§5 already
establish that this contract's fix must leave both files untouched, so this
test needs **no** new assertions from this work and — precisely because
`_validerOppskriftVolum()`/its three call sites live only in `app.js`, a file
this parity test does not inspect — **can't** exercise the new gate at all.

**What a future implementation round should add**, ready to run the moment
issue #53's permission gap is resolved (mirroring the existing
`@unittest.skip`-but-not-deleted convention in the three blocked files):

1. `tests/test_web_js_kbhrecipe.py` or a new
   `tests/test_web_js_app_volume_gate.py`: golden-vector calls to
   `_validerOppskriftVolum({volum: 0, ...})` → expect the
   `oppskrift.feilVolumPositiv` message string;
   `_validerOppskriftVolum({volum: -5, ...})` → same; `_validerOppskriftVolum({volum: 20, ...})`
   → expect `null`.
2. `tests/test_web_js_brew_storage.py`: one new case in
   `TestOpprettOgLesBrygg` confirming `opprettBrygg()` itself is **unchanged**
   by this contract — it still accepts a shape-valid, `volum: 0` snapshot,
   since (per §3.2) the block is enforced one layer up in `app.js`'s
   `startBrygging()`, never inside `brew_storage.js` — this is a deliberate
   "prove the layering held" regression test, not a gap this contract leaves
   open.
3. No new `tests/test_web_calc_js_parity.py` assertions (§ above — out of
   scope by construction).

**Testability boundary, stated plainly, exactly as prior briefs in this
series:** whether the three `app.js` call sites actually behave as specified
above — the field accepts focus, typing `0`/clearing it, clicking each of
the three buttons, seeing the right status text in the right paragraph, in
both languages — can only be confirmed by manual browser verification (§7)
today; the JS-level golden vectors above are prepared-but-blocked, identical
in spirit to every `@unittest.skip`-ped test already in this codebase for
this exact reason.

## 7. Manual browser verification matrix (for a future implementation round)

Per `.claude/rules/testing.md` ("no browser/E2E coverage in `tests/`" for
`web/**` runtime behavior), verification is a manual sweep — the
`web-full-regression` skill's dimensions (Chromium + Firefox × desktop +
mobile × NO + EN), scoped to `web/index.html` only (§2.6 — the only page
with this UI).

| # | Scenario | Expected outcome |
|---|---|---|
| B1 | Load the builder fresh (default `volum: 20`); click "Lagre oppskrift" | Saves normally — unchanged from today (regression check) |
| B2 | Clear `#batch-volum` entirely (delete all digits); click "Lagre oppskrift" | Blocked: `#lagre-status` shows `oppskrift.feilVolumPositiv`; nothing new appears in `mine-oppskrifter.html`'s stored list |
| B3 | Type `0` explicitly into `#batch-volum`; click "Lagre oppskrift" | Same as B2 — identical blocking behavior for explicit zero and emptied field |
| B4 | Type `-5` into `#batch-volum`; click "Lagre oppskrift" | Blocked with the same message (§5 — negative volume closed for this touchpoint) |
| B5 | Repeat B2/B3/B4 with "Lagre som variant" | Identical blocking behavior and message |
| B6 | With `volum` invalid (per B2-B4) and no malt/hops entered at all, click "Start brygging" | Shows `builder.brygg.tomOppskrift` (the pre-existing empty-recipe message), **not** the volume message — confirms ordering in §3.3 |
| B7 | With `volum` invalid (per B2-B4) but at least one malt or hop row filled in, click "Start brygging" | Blocked: `#brygg-start-status` shows `oppskrift.feilVolumPositiv`; confirm via `bryggelogg.html` that **no** new brew entry was created |
| B8 | Fix `#batch-volum` back to a positive number (e.g. `20`) after a B2/B4 block, without reloading; click "Lagre oppskrift"/"Start brygging" again | Proceeds normally — confirms the gate re-evaluates live `samleOppskrift()` state on every click, not a cached invalid flag |
| B9 | Repeat B1-B8 with the unit toggle set to US customary | Identical outcomes — `_lesVolumFelt`/`_validerOppskriftVolum` operate on the canonical liter value regardless of display unit (§1) |
| B10 | Repeat B2-B8 in both NO and EN (`web/en/index.html`) | Identical outcomes; correct language's message text in each |
| B11 | While typing (no click), verify draft autosave still updates `AKTIV_KLADD_NOKKEL` for an in-progress, momentarily-invalid volume | Unblocked — confirms §3.1.1 (autosave stays ungated) |
| B12 | Full B1-B11 sweep | 0 console/page errors, both Chromium and Firefox |

## 8. Unresolved questions for whoever opens the implementation issue

1. **Exact wording of `oppskrift.feilVolumPositiv`** (§3.3) — this brief
   recommends mirroring `utstyr.feilKapasitetPositiv`'s phrasing exactly
   ("X må være et tall større enn 0[.]"), with the unit spelled out
   ("... enn 0 liter") since batch volume, unlike kettle capacity, already
   has an explicit unit in its own label (`builder.grunndata.batchvolum`,
   "Batchvolum (liter)"). Confirm this exact string at implementation time.
2. **§3.4's optional live inline warning** — recommended as a nice-to-have,
   not required to close the audit finding. Decide whether to include it in
   the same implementation PR (low risk, reuses an existing pattern
   1:1) or defer it.
3. **§5's negative-volume `calc.js` inconsistency** (`beregnEBC` uses
   `<= 0`, `beregnOG`/`beregnTotalIBU` use `=== 0` only) — a real,
   independently-discovered gap in the *live-preview* path, but out of scope
   here per §2.3/§5's parity-test reasoning. Worth its own future issue if
   the owner judges the live-preview cosmetic impact (a nonsensical OG shown
   while typing a negative number, never persisted anywhere) worth a
   coordinated JS+Python change.
4. **§3.5's HTML `min="0"` → `min="0.1"` tightening** — purely cosmetic
   parity with the equipment inputs; take it or leave it independently of
   the required JS gate.
5. **Batching**: should the implementation ship as one issue covering all of
   §3.3 (both save functions + start-brewing, one shared key), or should
   Save and Start-brewing be split into two issues? This brief recommends one
   combined issue, exactly as A2-03's own precedent
   ([web_a2_03_navigation_focus_contract.md](web_a2_03_navigation_focus_contract.md)
   §6.3) reasoned for its two additive fixes — shared root cause (§1), shared
   predicate/message (§3.3-§4), shared verification sweep (§7) — but does not
   decide it.
