# Web A2-06 — remaining handbook placement/state wording drift (analysis only)

*Astra Audit #2 finding A2-06 (MEDIUM), issue #194. Residual from
[web_b08_handbook_drift_triage.md](web_b08_handbook_drift_triage.md) after
B08-1 and B08-2 were fixed (issues #164/#165, PRs #168/#169, commits
`1836965`/`f5ee9d8`). GitHub-only, static-source audit — no `web/**`
handbook/product content, i18n string, or generated `web/en/**` page was
touched to produce this brief, per the owner's prep-lane instruction
("Do not edit handbook/product content in this prep. Stop at review.").*

## How to read this

- **Handbook source**: exact `web/hjelp/**` file/line + `data-i18n(-html)`
  key, quoted as it currently reads.
- **i18n touchpoint**: the same key's NO and EN entries in `web/js/i18n.js`
  (the single source both the NO handbook pages and the generated EN pages
  read from).
- **Generated-EN touchpoint**: the corresponding line in `web/en/hjelp/**`,
  produced byte-for-byte by `scripts/generate_web_i18n_pages.py` from the NO
  source + the EN half of `web/js/i18n.js` — never hand-edited
  (`.claude/rules/web.md`). Every finding below therefore applies
  **identically to both locales**; a fix only ever needs to change the NO
  source file and/or `web/js/i18n.js`, then regenerate.
- **Current Web evidence**: exact file/line proving what the Web product
  actually does today.
- **Status**: `already fixed` (B08-1/B08-2, done), `open — B08 carryover`
  (already triaged in the original B08 doc, still unaddressed), or
  `open — new (A2-06)` (not present in the original B08 triage; the product
  changed underneath the handbook after B08 was written, or the drift was
  simply missed the first time).

---

## Already-fixed B08 items (confirmed, not re-triaged here)

| # | Claim | Fixed by | Verified still holding |
|---|---|---|---|
| B08-1 | "💧 Vannkjemi"-module described as reachable in Web's Bryggmester | Issue #164, commit `1836965` | Yes — `web/hjelp/vannkjemi.html` and `web/hjelp/index.html:341,535` now consistently say "hovedappen" wherever the module is discussed (11 occurrences checked); `web/index.html:366` footer (`footer.builder`) matches this framing |
| B08-2 | Hochkurz/Dekoksjon/reiterated mash described as a "Prosessprofil-panelet i oppskriftsbyggeren" | Issue #165, commit `f5ee9d8` | Yes — `web/hjelp/index.html:341` (`hjelp.idx.defMesking.tekst`) now says "finnes som prosessprofiler i hovedappen", matching the App-only framing established by the B08-1 fix |

**Water-chemistry Web/App boundary (owner's prep note) — confirmed intact.**
The B08-1 wording pattern ("hovedappen") is used consistently across all
11 current `hovedappen` references in `web/hjelp/vannkjemi.html` +
`web/hjelp/index.html` + `web/index.html:366` — no regression found. Any
future round touching this area should re-grep
`grep -rn hovedappen web/hjelp/vannkjemi.html web/hjelp/index.html
web/index.html` before editing, to keep this boundary intact.

---

## Remaining drift mapped to the five A2-06 claims

### A2-06-1 — Mode selection: "two buttons at the top" is stale (open — new)

**Handbook source**: `web/hjelp/index.html:140`
(`hjelp.idx.laerlingMester.tekst`, article "Bryggelærling og Bryggmester"):

> "De to knappene **øverst** bytter mellom to visninger av *samme*
> oppskrift. ..."

**i18n touchpoint**: `web/js/i18n.js:793` (NO) / `web/js/i18n.js:2544` (EN
— "**The two buttons at the top** switch between two views...").
Companion paragraph `hjelp.idx.laerlingMester.hvorfor`
(`i18n.js:794`/`2545`) is unaffected — it only discusses switching back and
forth, not location.

**Generated-EN touchpoint**: `web/en/hjelp/index.html:134`.

**Current Web evidence**: this was true when the original B08 triage
verified it ("Bryggelærling/Bryggmester toggle 'øverst'" — listed in that
doc's "Verified current" table), but the mode control was redesigned since
then. `web/js/app.js:322-328` (comment, "Runde 11"):

> "modusvalget er ikke lenger en stor, permanent kontroll i arbeidsflaten —
> kun et førstegangsvalg (modal) + et lite bytte i hamburger-menyen."

Concretely: `web/index.html:77-81` — the ongoing control is a small toggle
inside the hamburger side menu (`sidemeny-modus-knapp`, two icon buttons
"🎓 Lærling" / "⚙️ Mester"), not two buttons at the top of the builder's main
content. `web/index.html:91-102` — a **first-visit modal dialog**
(`#modus-forstegang`) is shown once (only when no preference is yet stored,
`app.js:400-413`) and never appears again afterward. Neither location is
"at the top" of the builder's visible content the way the handbook implies.

**Classification**: stale/moved (a real past UI, since redesigned; not
present in the original B08 triage because the redesign predates or
postdates that triage's snapshot — either way, the current wording no
longer matches).

**Acceptance checks for a future fix**:
1. `hjelp.idx.laerlingMester.tekst` no longer says "de to knappene øverst";
   it instead describes the current mechanism (small toggle in the
   hamburger menu, plus a one-time first-visit choice).
2. NO/EN parity preserved (regenerate `web/en/**`).
3. No other paragraph on the page assumes the old "two buttons at the top"
   layout (checked: none — `laerlingMester.hvorfor` and every other
   reference to switching modes elsewhere in the handbook describe
   *behavior*, not *location*).

---

### A2-06-2 — Learner efficiency copy: 75% estimate vs. preserved Master value (open — new)

**Handbook source**: `web/hjelp/index.html:245`
(`hjelp.idx.effektivitet.hvorfor`, article "Brygghuseffektivitet"):

> "...Bryggelærling skjuler feltet og bruker 75 % som estimat, slik at du
> kan komme i gang uten å måtte vite dette først. I Bryggmester kan du
> justere det etter egne, målte brygg..."

**i18n touchpoint**: `web/js/i18n.js:861` (NO) / `web/js/i18n.js:2612`
(EN). Sibling key `hjelp.idx.effektivitet.tekst` (`i18n.js:860`/`2611`,
"75 % er et vanlig utgangspunkt") is the general-knowledge paragraph and is
not itself wrong — only the `.hvorfor` paragraph's implication is
incomplete.

**Generated-EN touchpoint**: `web/en/hjelp/index.html:221`.

**Current Web evidence**: the phrasing "Bryggelærling ... bruker 75 % som
estimat" reads as if Lærling mode always computes with 75%. It does not:
- `web/index.html:189-191` — the `#effektivitet` input is `mester-only` and
  only carries the `value="75"` **default**; it is one ordinary form field,
  not a mode-dependent calculated constant.
- `web/css/style.css:1655` — `body.modus-laerling .mester-only { display:
  none; ... }`: switching to Lærling only **hides** the field via CSS. It
  does not reset, clear, or disable it.
- `web/js/app.js:1460` — `effektivitet: parseFloat(document.getElementById
  ("effektivitet").value) || 0` reads the field's live DOM value for every
  OG calculation, in **both** modes, unconditionally.
- `web/js/app.js:1783-1790` (`_blankOppskrift()`) — `effektivitet: 75` is
  only the reset value for an explicit **new/blank recipe** action, not
  something mode-switching itself re-applies.

Net effect: if a user sets efficiency to, say, 82% while in Bryggmester,
then switches to Bryggelærling, the field is hidden but its value stays 82
— Lærling's "hidden estimate" silently becomes whatever was last set in
Mester, not always 75%. The handbook's `.hvorfor` paragraph never states
this, so a Lærling-mode user has no way to learn that an earlier
Mester-mode adjustment is still being used behind the hidden field.

**Classification**: incomplete/misleading-by-omission — not factually
false (75% *is* the field's out-of-the-box default), but omits a
behaviorally important case Astra flagged.

**Acceptance checks for a future fix**:
1. `hjelp.idx.effektivitet.hvorfor` explicitly states that a
   previously-set (Bryggmester) efficiency value is preserved and still
   used even while the field is hidden in Bryggelærling — 75% is only the
   value for a fresh/never-touched recipe.
2. Wording stays consistent with `hjelp.idx.effektivitet.tekst`'s "75 % er
   et vanlig utgangspunkt" framing (a starting point, not a hard rule) —
   avoid overstating precision in the other direction.
3. NO/EN parity preserved.

---

### A2-06-3 — Target-IBU action label drifted from the handbook's literal quote (open — new; regressed since B08)

**Handbook source**: `web/hjelp/index.html:170-171`
(`hjelp.idx.malIbu.tekst` / `hjelp.idx.malIbu.hvorfor`, article "Mål-IBU:
baklengs bitterhetsberegning") — both paragraphs quote the button's label
literally, twice each direction:

> "...og trykker **'Beregn gram'** — da regner byggeren ut hvor mange gram
> som trengs..." / "...fyller **'Beregn gram'** inn den gramvekten..."

**i18n touchpoint**: `web/js/i18n.js:813-814` (NO) /
`web/js/i18n.js:2564-2565` (EN — quotes **"Calculate grams"** twice).

**Generated-EN touchpoint**: `web/en/hjelp/index.html:159-160`.

**Current Web evidence** — two independent drifts, both post-dating the
original B08 triage (which listed this pairing under "Verified current"
before the unit-system feature, issue #102, landed — commits `a027a66`,
`5232a77`, `5e6ed9c`):

1. The i18n **label itself already changed** away from "gram"-specific
   wording: `web/js/i18n.js:385` — `"builder.humle.beregnGramKnapp":
   "Beregn mengde"` (NO), `web/js/i18n.js:2136` — `"Calculate amount"`
   (EN). The key name (`beregnGramKnapp`) still says "Gram" but the
   *string value* it resolves to no longer does.
2. The rendered button additionally appends the **active unit** at
   runtime: `web/js/app.js:127-128` —
   `` knapp.textContent = `${t("builder.humle.beregnGramKnapp")} (${enhet.humle})` `` —
   where `enhet.humle` is `"g"` under Metric or `"oz"` under US units
   (`ENHET_FORKORTELSE`, `web/js/app.js:95-96`). A US-unit user therefore
   currently sees **"Beregn mengde (oz)"** / **"Calculate amount (oz)"** —
   neither the word the handbook quotes ("gram"/"grams") nor a fixed
   label at all.
3. `web/index.html:410`'s own static markup —
   `<button ... data-i18n="builder.humle.beregnGramKnapp">Beregn
   gram</button>` — still carries the **old, pre-#102 fallback text**
   ("Beregn gram") as its no-JS/pre-render placeholder. This never
   displays once `app.js` runs (it is immediately overwritten per point 2
   above), but it is a second, independent stale touchpoint in the same
   feature area, worth fixing in the same batch for consistency even
   though it carries no live-render risk.

**Classification**: stale (literal quoted button text no longer matches
either the base i18n string or the unit-aware rendered text) — the
strongest "regressed since B08" case in this brief, since the original
triage's "Verified current" call was correct *at the time* and has since
been invalidated by an unrelated feature (unit selection, #102), not by
any handbook edit.

**Acceptance checks for a future fix**:
1. `hjelp.idx.malIbu.tekst` and `.hvorfor` no longer literally quote
   "Beregn gram"/"Calculate grams"; wording instead describes the action
   generically (e.g. "trykker knappen for å beregne mengden" / "fyller
   knappen inn mengden") or names the current base label ("Beregn
   mengde"/"Calculate amount") without hardcoding a unit that can change.
2. Wording does not imply a Metric-only (gram) experience — must read
   correctly under both Metric and US units, given the button's own label
   already varies by unit.
3. `web/index.html:410`'s static fallback text is updated to match the
   current base label ("Beregn mengde"), even though it is functionally
   inert post-render, so the source no longer contradicts
   `web/js/i18n.js`.
4. NO/EN parity preserved.

---

### A2-06-4 — Saved recipes "further down the builder" (open — B08 carryover, = B08-4)

Unchanged from the original triage — see
[web_b08_handbook_drift_triage.md § B08-4](web_b08_handbook_drift_triage.md#b08-4--mine-lagrede-oppskrifter--lenger-ned--moved-to-a-separate-page)
for the full writeup. Restated here only to map it into this issue's five
claims and confirm it is still current:

- **Handbook source**: `web/hjelp/index.html:176`
  (`hjelp.idx.lagreOppskrift.tekst`) — "Den dukker opp i 'Mine lagrede
  oppskrifter' **lenger ned**".
- **i18n touchpoint**: `web/js/i18n.js:817` (NO) / `web/js/i18n.js:2568`
  (EN — "further down").
- **Generated-EN touchpoint**: `web/en/hjelp/index.html:164`.
- **Current Web evidence**: `web/mine-oppskrifter.html` is a fully
  separate page (heading text itself unchanged — "Mine lagrede
  oppskrifter" — only the *location* claim is wrong), reached solely via
  the side-menu "📂 Mine oppskrifter" link (`nav.mineOppskrifter`).
  `web/index.html` has no inline saved-recipe list at all (confirmed
  unchanged from the original triage — no recipe-list markup or
  `lagret-liste`/`recipe-list` selectors in `web/js/app.js`).

**Acceptance checks**: identical to the original triage's — change
"lenger ned" to point at the side-menu "📂 Mine oppskrifter" page; NO/EN
parity preserved.

---

### A2-06-5 — Brewday guide's Print-panel link (open — B08 carryover, = B08-3)

Unchanged from the original triage — see
[web_b08_handbook_drift_triage.md § B08-3](web_b08_handbook_drift_triage.md#b08-3--oppskriftsbyggerens-skriv-ut-panel-link-points-at-the-wrong-page)
for the full writeup. Restated here only to map it into this issue's five
claims and confirm it is still current:

- **Handbook source**: `web/hjelp/bryggedag.html:363-366`
  (`hjelp.dag.avslutning`) — links `../index.html` and calls it
  "oppskriftsbyggerens **Skriv ut**-panel".
- **i18n touchpoint**: `web/js/i18n.js:1165` (NO) / `web/js/i18n.js:2916`
  (EN — links `../index.html`, labeled "**Print**").
- **Generated-EN touchpoint**: `web/en/hjelp/bryggedag.html:334`.
- **Current Web evidence**: `web/index.html` has no "Skriv ut"/"Print"
  panel of any kind (confirmed unchanged — the builder's "Lagre og
  eksporter" section has no print action). The real panel is the separate
  page `web/utskrift.html:103-110`, reached only via the side-menu
  "🖨️ Utskrift" link (`nav.utskrift`).

**Acceptance checks**: identical to the original triage's — change the
link target to `../utskrift.html` (or an anchor within it) and stop
attributing the panel to "oppskriftsbyggeren"; NO/EN parity preserved.

---

## Smallest coherent content batches for a future fix pass

Following this project's established B08-1/B08-2 precedent (two
independently small, single-purpose fix issues/PRs rather than one large
combined change), the five items above split into **four** batches by
root cause and touched area, not five, because two pairs share both a root
cause and adjacent source lines:

| Batch | Items | Why grouped | Files touched |
|---|---|---|---|
| **1** | A2-06-5 (B08-3, print link) | Standalone — already independently scoped in the original B08 triage, zero shared lines with anything else | `hjelp/bryggedag.html`, `i18n.js` (2 keys) |
| **2** | A2-06-4 (B08-4, saved-recipe location) | Standalone — already independently scoped in the original B08 triage, zero shared lines with anything else | `hjelp/index.html` (1 paragraph), `i18n.js` (2 keys) |
| **3** | A2-06-1 (mode-selection wording) + A2-06-2 (Learner efficiency copy) | Both are direct consequences of the same "Runde 11" mode-UI redesign (`app.js:322-424`), both live in the same handbook article group (`hjelp/index.html`'s Bryggelærling/Bryggmester + Brygghuseffektivitet articles, lines 140/245 — a few dozen lines apart), and a reviewer checking one naturally re-reads the other | `hjelp/index.html` (2 paragraphs), `i18n.js` (2 keys, ~4 locale entries) |
| **4** | A2-06-3 (target-IBU button label) | Standalone — root cause is the unrelated unit-system feature (#102), and it uniquely also touches the builder's own static markup (`web/index.html:410`), not just handbook prose | `hjelp/index.html` (2 paragraphs), `web/index.html` (1 fallback string), `i18n.js` (2 keys) |

Batches 1+2 could be combined into one PR if the owner prefers fewer
review cycles (both are one-sentence "wrong page" corrections with
effectively zero technical risk, same as B08-1/B08-2's own combinability
note) — flagged as an option, not a recommendation, per "split only if
materially safer": keeping them separate costs little and mirrors how
B08-3/B08-4 were already scoped as distinct findings in the original
triage.

**Common acceptance check across every batch**: run
`python3 -m unittest tests.test_generate_web_i18n_pages -b` after
regenerating `web/en/**` via
`python3 scripts/generate_web_i18n_pages.py` — this is the only automated
guard that exists for this class of change (it checks NO/EN key symmetry
and generator byte-parity, not prose-vs-product accuracy; a human read of
the affected paragraph against current Web behavior remains the only check
for the semantic claim itself, exactly as the original B08 triage already
noted).

---

## Tests that could guard this contract

Unchanged from the original B08 triage's own conclusion: no automated test
checks handbook prose against live product markup or behavior —
`tests/test_generate_web_i18n_pages.py` verifies i18n key symmetry and
generator output byte-parity only. This class of drift (both this issue
and B08) is a semantic check, not a structural one, and remains a poor fit
for that suite. No new test is proposed here.

## Explicitly out of scope for this prep

No `web/**` product/content file, i18n string, or generated `web/en/**`
page was edited to produce this brief. None of A2-06-1..5 was implemented.
No deploy occurred. No other Astra Audit #2 finding was investigated.
