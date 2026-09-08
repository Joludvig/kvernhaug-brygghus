# Web B08 — Handbook / current-Web drift triage (analysis only)

*Part of #101 Phase 1 NEXT preparation, audit finding B08. Supersedes the B08
portion of #123. GitHub-only, static-source audit comparing
`web/hjelp/**` (the handbook/help content, "Hjelp & bryggehåndbok") against
current `web/**` product source — no product code, handbook content, or i18n
touched, no fix implemented. Everything below is either quoted directly from
the current repository or explicitly flagged as needing a live browser
check.*

## How to read this

- **Handbook source**: exact `web/hjelp/**` file/line + `data-i18n(-html)`
  key, quoted as it currently reads.
- **Current Web evidence**: exact file/line proving what the Web product
  actually does today — either a matching feature, a moved/renamed one, or,
  where the claim is absent from Web entirely, the negative evidence (grep
  scope + zero matches) plus where the feature *does* live instead.
- **Classification**: `current` (statement matches Web today), `stale/moved/
  renamed` (statement described something real that has since relocated or
  been retitled), `App-only/non-Web` (statement describes a real feature,
  but only in the Streamlit App, not in Web at all), `ambiguous` (depends on
  a subjective/unverifiable word), `browser verification required` (static
  source can't settle it).
- NO and EN handbook pages are generated from the same DOM/JS/content
  contract (`web/en/**` is machine-generated from the NO source, see
  `.claude/rules/web.md`) — every finding below therefore applies
  **identically to both locales**, since the drift is in the underlying
  claim/source pairing, not in translation.

---

## Priority summary

| # | Handbook source | Claim | Classification | Severity |
|---|---|---|---|---|
| B08-1 | `hjelp/index.html` §F intro (`hjelp.idx.secF.intro`) + all of `hjelp/vannkjemi.html` | A "💧 Vannkjemi" module exists **in the Web builder** (Bryggmester) — register source water, set a target profile, get salt suggestions, register acid additions, convert alkalinity units | **App-only/non-Web** | HIGH — whole dedicated handbook page + a section of the main FAQ page describe a feature Web does not have at all |
| B08-2 | `hjelp/bryggemetoder.html` §"Bryggmester: avanserte meskemetoder" (`hjelp.metoder.bryggmesterIntro` + 3 method cards) | Hochkurz, Dekoksjon ("Enkel dekoksjon") and Dobbel mesking/reiterated mash exist as selectable "Prosessprofiler" in a "Prosessprofil-panelet i oppskriftsbyggeren", with specific example default values | **App-only/non-Web** | HIGH — whole section describes a feature Web does not have at all |
| B08-3 | `hjelp/bryggedag.html` closing paragraph (`hjelp.dag.avslutning`) | "Lag et konkret bryggedagsark ... fra oppskriftsbyggerens Skriv ut-panel", linking to `../index.html` | **stale/moved** (wrong page + dead claim) | MEDIUM — one sentence, but the link is actively misleading |
| B08-4 | `hjelp/index.html` §A "Lagre en oppskrift" (`hjelp.idx.lagreOppskrift.tekst`) | Saved recipe "dukker opp i 'Mine lagrede oppskrifter' lenger ned" (further down the *same* page) | **stale/moved** (correct feature/label, wrong location) | LOW-MEDIUM |
| B08-5 | *(not handbook — found incidentally while verifying B08-1)* `web/index.html:366` footer (`footer.builder`) | "Full versjon med pantry, vannkjemi og full sensorisk analyse: se hovedappen" | **stale** (the "pantry" half) / confirms B08-1 (the "vannkjemi" half) | LOW — one sentence, self-inconsistent with Web's own `pantry.html` |
| — | "full sensorisk analyse" phrase in the same footer sentence | Implies Web's sensory tooling is a cut-down subset of the App's | **ambiguous** | — (product judgement call, not asserted here) |

Everything not listed above that was checked (see "Verified current" section)
matches current Web exactly — this triage does not claim the whole handbook
is unreliable, only the five items above.

---

## B08-1 — "💧 Vannkjemi"-module: App-only, described as if it's in Web

### Handbook source

`web/hjelp/index.html:528-537` (`hjelp.idx.secF.intro`, section id `vannkjemi`):

> "Kvernhaug Brygghus har en egen «💧 Vannkjemi»-modul i
> oppskriftsbyggeren (Bryggmester) hvor du kan registrere kildevann, sette
> en målprofil og få saltforslag."

Reinforced across the **entire** dedicated page `web/hjelp/vannkjemi.html`
(294 lines, part of the "Bryggmester" nav group in `hjelp-side-nav`), e.g.:

- `vannkjemi.html:127-134` (`hjelp.vannkjemi.intro`): "...uten å bygge en
  full kjemilærebok eller nye beregningsmotorer i **appens «💧
  Vannkjemi»-modul**."
- `vannkjemi.html:160` (`hjelp.vannkjemi.meskePhUtvidet.hvorfor`): "KBH sine
  egne målprofiler i «💧 Vannkjemi»-modulen bruker forskjellige
  meske-pH-arbeidsområder for ulike ølstiler (typisk et sted mellom ca. 5,2
  og 5,6, avhengig av profil) ... Appens eget måleskjema registrerer om
  prøven ble avkjølt til romtemperatur før avlesning..."
- `vannkjemi.html:166` (`hjelp.vannkjemi.syretilsetning.tekst`): "KBH sin
  «💧 Vannkjemi»-modul støtter registrering av melkesyre og fosforsyre som
  egne syretilsetninger..."
- `vannkjemi.html:167` (`hjelp.vannkjemi.syretilsetning.hvorfor`):
  "...appen ber deg derfor alltid oppgi konsentrasjonen (%) for hver
  syretilsetning selv..."
- `vannkjemi.html:173` (`hjelp.vannkjemi.salterVsSyre.hvorfor`): "Natron
  (NaHCO3) er et godt eksempel ... det er et salt **appens saltdatabase**
  tilbyr for å HEVE HCO3/alkalitet..."

### Current Web evidence

No trace of this module in the Web product source:

- `grep -n -i "vannkjemi\|saltdosering\|kildevann\|malprofil\|mash-ph\|meske-ph" web/index.html web/js/*.js web/*.html` — the only two hits repo-wide are `web/js/i18n.js` (translation strings for the *handbook page's own* `meta.hjelpVannkjemiAvansert.*` title/description, not a feature) and `web/index.html:366` (the footer sentence discussed in B08-5, which itself says the opposite of the handbook: "vannkjemi ... se hovedappen").
- `web/index.html` has no water-chemistry section, panel, input field, or button of any kind — confirmed by reading the full builder markup (Grunndata → Malt → Humle → Gjær → Smaksprofil → Stilanalyse → Lagre/eksporter, no water section between any of these).
- The real implementation exists only in the Streamlit App: `ui/water_panel.py` and `modules/water_chemistry.py` (both matched by the same grep against `modules/` and `ui/`, zero matches under `web/`).

### Classification

**App-only/non-Web.** The handbook describes a concrete, named Web feature
("i oppskriftsbyggeren (Bryggmester)", "appens ... modul") with specific
claimed behavior (target profiles per style, pH 5.2–5.6 working ranges,
lactic/phosphoric acid registration with user-entered concentration,
NaHCO3 in a salt database) that has no Web implementation at all. A Web
user following this handbook page has no module to find.

### Likely future fix touchpoints

- `web/hjelp/index.html` §F intro paragraph (`hjelp.idx.secF.intro`).
- All of `web/hjelp/vannkjemi.html` (every "appens"/"KBH sin ... modul"
  sentence would need rewording to describe this as App-only content, or
  the page's framing would need to change if/when Web ever gets water
  chemistry).
- `web/js/i18n.js` — both NO and EN copies of every key above (same
  structural gap in both locales, since EN is generated from NO).

### Smallest bounded acceptance criteria (for a future fix issue, not this one)

1. `hjelp.idx.secF.intro` and every "appens"/"KBH sin"/"i Bryggmester"
   wording in `vannkjemi.html` either (a) is reworded to explicitly say this
   is an **App** feature, not a Web one, or (b) if a Web water-chemistry
   module ships first, the handbook then matches that Web implementation
   instead.
2. No remaining sentence implies a Web user can open a water-chemistry panel
   inside `web/index.html`.
3. NO/EN parity preserved (regenerate `web/en/**` per `.claude/rules/web.md`
   if source text changes).

### Regression risk

Low technical risk (docs/content-only change) but real user-trust risk if
left as-is: a Web user reading this page and trying to find "💧 Vannkjemi"
in Bryggmester will not find it and may conclude the app is broken.

### Proposed bounded future issue title

"WEB FIX — B08-1: reword handbook §F/vannkjemi.html to stop claiming an
in-Web water-chemistry module"

### Browser needs

None — this is fully provable from static source (absence of any water
chemistry markup/JS in `web/`).

### Dependencies / coupling

None to W5 (brew-completion state) or B06 (accessibility). Loosely related
to the ROADMAP V2.1 Phase 1 "NEXT" B08 item itself and to the general
App-vs-Web scope divergence the roadmap already acknowledges ("Do not
pursue UX parity between App and Web").

---

## B08-2 — "Prosessprofil-panelet": Hochkurz/Dekoksjon/reiterated mash are App-only

### Handbook source

`web/hjelp/bryggemetoder.html:171-178` (id `bryggmester-mesking`,
`hjelp.metoder.bryggmesterIntro`):

> "Disse tre metodene finnes som fullstendige prosessprofiler i Bryggmester
> (**Prosessprofil-panelet i oppskriftsbyggeren**) — her forklares HVA de
> er, HVORFOR de brukes..."

Each of the three method cards repeats the same claim with concrete example
values presented as live product defaults:

- `bryggemetoder.html:182` (Hochkurz): "Kvernhaug Brygghus sin egen
  Hochkurz-profil (**Bryggmester → Prosessprofil**) bruker som eksempel
  63 °C/40 min etterfulgt av 70 °C/30 min og mashout..."
- `bryggemetoder.html:188` (Dekoksjon): "Kvernhaug Brygghus sin egen
  dekoksjonsprofil (**Bryggmester → Prosessprofil**, «Enkel dekoksjon») er
  et eksempel med ett uttak... Uttaksvolumet beregnes som et forslag..."
- `bryggemetoder.html:194` (Reiterated mash): "Kvernhaug Brygghus sin egen
  reiterated mash-profil deler som eksempel maltmengden 50/50 mellom de to
  meskene..."

Also referenced from the main FAQ page: `hjelp/index.html:341`
(`hjelp.idx.defMesking.tekst`), linking to `bryggemetoder.html#bryggmester-mesking`
as "avanserte meskemetoder i Bryggmester".

### Current Web evidence

`grep -n -i "hochkurz\|dekoksjon\|reiterated\|prosessprofil" web/index.html
web/js/*.js` — **zero matches**. The only repo-wide hits for these terms
outside the handbook itself (`web/hjelp/index.html`,
`web/hjelp/bryggemetoder.html`, `web/hjelp/sterke-ol.html`, and their `en/`
mirrors) are in `web/js/i18n.js`, and every one of those is under a
`hjelp.*` key (the handbook's own translated text) — none under a
`builder.*` key, which is where an actual Web feature string would live.

`web/index.html`'s Grunndata section (`builder.grunndata.*`, lines 157-206)
has no mesh-schedule/process-profile selector of any kind — just ølnavn,
brygger, bryggeri, batchvolum, aktivt utstyr, effektivitet, notater.

The real implementation exists only in the Streamlit App:
`ui/process_panel.py` and `modules/process_profiles.py` (both matched by
the same grep against `modules/`/`ui/`, zero matches under `web/`).

### Classification

**App-only/non-Web.** Same pattern as B08-1 — a real App feature, described
with product-specific example values as if it is directly reachable in
Web's Bryggmester mode via a named panel ("Prosessprofil-panelet i
oppskriftsbyggeren") that does not exist.

### Likely future fix touchpoints

- `web/hjelp/bryggemetoder.html` §"Bryggmester: avanserte meskemetoder"
  (id `bryggmester-mesking`) — intro + all three method cards.
- `web/hjelp/index.html:341` cross-reference wording ("avanserte
  meskemetoder i Bryggmester").
- `web/js/i18n.js` — both NO and EN copies.

### Smallest bounded acceptance criteria (for a future fix issue, not this one)

1. Every "i Bryggmester (Prosessprofil-panelet i oppskriftsbyggeren)" /
   "Bryggmester → Prosessprofil" phrase is reworded to state this is an App
   feature, or the section is updated once/if Web ships an equivalent.
2. The cross-reference from `hjelp/index.html#def-mesking` no longer implies
   a Web user can reach these profiles from Bryggmester.
3. NO/EN parity preserved.

### Regression risk

Same class as B08-1 — content-only change, but real user-confusion risk
left as-is (three named "profiles" with concrete numbers that a Web user
cannot find anywhere).

### Proposed bounded future issue title

"WEB FIX — B08-2: reword bryggemetoder.html §Bryggmester-mesking to stop
claiming an in-Web Prosessprofil panel"

### Browser needs

None — fully provable from static source (absence of any process-profile
markup/JS/data in `web/`).

### Dependencies / coupling

None to W5/B06. Same App-vs-Web divergence category as B08-1; a future fix
issue for B08-1 and B08-2 could reasonably be combined since they're the
same defect pattern (App-only Bryggmester feature narrated as if in Web),
but that's a call for whoever scopes the fix issue(s), not asserted here.

---

## B08-3 — "oppskriftsbyggerens Skriv ut-panel" link points at the wrong page

### Handbook source

`web/hjelp/bryggedag.html:363-366` (`hjelp.dag.avslutning`, the page's
closing paragraph):

```html
<p class="hjelp-innledning" data-i18n-html="hjelp.dag.avslutning">
  Lag et konkret bryggedagsark for din egen oppskrift fra oppskriftsbyggerens
  <a href="../index.html">Skriv ut</a>-panel.
</p>
```

### Current Web evidence

- `web/index.html` has **no** "Skriv ut" panel, section, heading, or button
  anywhere — `grep -n "Skriv ut\|skriv-ut\|utskrift" web/index.html` matches
  only the unrelated side-menu link `<a href="utskrift.html" ...><span
  data-i18n="nav.utskrift">🖨️ Utskrift</span></a>` (`web/index.html:72`,
  label "Utskrift", not "Skriv ut"). The builder's own "Lagre og eksporter"
  section (`web/index.html:259-291`) has Ny oppskrift / Lagre / Lagre fil /
  Åpne fil / Avansert-JSON / Skaler — no print action of any kind.
- The real "Skriv ut" panel exists on the **separate** page
  `web/utskrift.html:103-110` — a distinct `<h2 data-i18n="utskrift.skrivUtTittel">Skriv
  ut</h2>` section containing exactly the four print buttons
  (`utskrift.knappOppskriftsark`/`knappHandleliste`/`knappBryggedagsark`/
  `knappBryggelogg`) that `hjelp/index.html`'s own §A "Skrive ut" article
  (`hjelp.idx.skriveUt.tekst`, lines 185-188) correctly describes. That
  article is **not** part of this finding — it's accurate; it just doesn't
  say where the panel lives, so nothing in it is wrong.
- `web/utskrift.html` is reached only via the side-menu "🖨️ Utskrift" link
  (`nav.utskrift`), never from inside `web/index.html`.

### Classification

**Stale/moved** (wrong page attribution + a dead-end claim, not merely an
outdated label). The link target (`../index.html`) and the claimed location
("oppskriftsbyggerens ... panel") are both wrong for the actual feature.

### Likely future fix touchpoints

- `web/hjelp/bryggedag.html:363-366` (`hjelp.dag.avslutning`) — change the
  link target to `../utskrift.html` and the wording to no longer attribute
  the panel to "oppskriftsbyggeren".
- `web/js/i18n.js` — both NO and EN copies of `hjelp.dag.avslutning`.

### Smallest bounded acceptance criteria (for a future fix issue, not this one)

1. The link in `hjelp.dag.avslutning` points to `../utskrift.html` (or an
   anchor within it), not `../index.html`.
2. The wording no longer implies the "Skriv ut" panel is inside the
   oppskriftsbygger itself.
3. NO/EN parity preserved.

### Regression risk

Very low technical risk (one sentence/one `href`). Practical risk: a reader
who clicks through lands on the builder with no obvious next step toward
printing, which is a small but real dead end for a first-time user trying
to prep for brew day.

### Proposed bounded future issue title

"WEB FIX — B08-3: fix bryggedag.html's closing link to point at
utskrift.html, not index.html"

### Browser needs

None — the absence of any "Skriv ut" markup in `index.html` and its
presence in `utskrift.html` are both directly readable from static source.

### Dependencies / coupling

None to W5/B06/#116/#98/#100.

---

## B08-4 — "Mine lagrede oppskrifter ... lenger ned" — moved to a separate page

### Handbook source

`web/hjelp/index.html:174-178` (id `lagre-oppskrift`,
`hjelp.idx.lagreOppskrift.tekst`):

> "'💾 Lagre oppskrift' lagrer oppskriften i denne nettleseren (localStorage)
> under navnet du har gitt den. Den dukker opp i **'Mine lagrede
> oppskrifter' lenger ned**, og du kan laste den inn igjen når som helst —
> også etter at du har lukket fanen."

"Lenger ned" ("further down") reads as further down the *same* page (the
builder), immediately after describing the "💾 Lagre oppskrift" button that
lives on that same page.

### Current Web evidence

- `web/index.html` has **no** inline saved-recipe list at all —
  `grep -n -i "mine.*oppskrift\|lagrede.*oppskrift\|mine-oppskrift"
  web/index.html` matches only the side-menu nav link (line 70) and the
  "Lagre og eksporter" helptext mentioning "her eller under «📥 Importer
  oppskrift»" (`web/index.html:270`) — no list markup, no `id`/class for a
  recipe list, confirmed by also grepping `web/js/app.js` for
  `lagret-liste|recipe-list|oppskrift-liste` (zero matches).
- The saved-recipe list lives entirely on the separate page
  `web/mine-oppskrifter.html:82` (`<h2
  data-i18n="mineOppskrifter.tittel">Mine lagrede oppskrifter</h2>` — note
  the heading text itself is byte-identical to the handbook's quoted
  phrase, so only the *location* claim is wrong, not the label), populated
  by `web/js/mine_oppskrifter_page.js`, reached only via the side menu
  ("📂 Mine oppskrifter", `nav.mineOppskrifter`).
- `web/CHANGELOG.md:761` documents this as a deliberate architecture
  change, not an oversight: "Fullbredde IA-redesign: Mine
  oppskrifter-/Importer-/Utskrift-sider ... " — i.e. these were pulled out
  into their own pages in a past round.

### Classification

**Stale/moved.** The feature and its exact label ("Mine lagrede
oppskrifter") are both still current; only the "lenger ned" (same-page)
placement claim is stale — it now requires a full page navigation via the
side menu, not scrolling.

### Likely future fix touchpoints

- `web/hjelp/index.html:174-178` (`hjelp.idx.lagreOppskrift.tekst`) — change
  "lenger ned" to something like "under «📂 Mine oppskrifter» i menyen".
- `web/js/i18n.js` — both NO and EN copies.

### Smallest bounded acceptance criteria (for a future fix issue, not this one)

1. `hjelp.idx.lagreOppskrift.tekst` no longer implies the saved-recipe list
   is on the same page as the "💾 Lagre oppskrift" button.
2. Wording correctly points to the side-menu "📂 Mine oppskrifter" page.
3. NO/EN parity preserved.

### Regression risk

Very low — one sentence, no functional risk. A first-time reader may
briefly scroll the builder page looking for a list that isn't there, but
the actual saved-recipe mechanism works exactly as described otherwise
("Åpne i byggeren" button confirmed at `web/js/i18n.js:554` = "Åpne i
byggeren", matching `hjelp/index.html:182`'s separate, correct claim about
that button).

### Proposed bounded future issue title

"WEB FIX — B08-4: fix hjelp/index.html's 'lenger ned' wording — saved
recipes live on a separate Mine oppskrifter page"

### Browser needs

None — provable from static source (no recipe-list markup in `index.html`
or `app.js`; full markup present in `mine-oppskrifter.html`).

### Dependencies / coupling

None to W5/B06/#116/#98/#100.

---

## B08-5 — Found incidentally: the builder's own footer is self-inconsistent

Not handbook content (`web/hjelp/**`) — this is `web/index.html`'s own
footer, surfaced only because it was the evidence that first confirmed
B08-1. Recorded here since it's directly relevant, structurally identical
"content describes wrong current-Web state" drift, and the issue asked to
record *current Web evidence* for B08-1 in full.

### Source

`web/index.html:366` (`footer.builder`, shown on every builder page load,
`no-print` footer):

> "Oppskriftene dine lagres lokalt i denne nettleseren (localStorage). Full
> versjon med **pantry**, **vannkjemi** og full sensorisk analyse: se
> hovedappen."

### Current Web evidence

- The **"vannkjemi"** half is accurate and *confirms* B08-1: no such module
  exists in Web (see B08-1's evidence above) — this footer line is Web's
  own, correct, source-of-truth admission that water chemistry is
  App-only. It directly contradicts `hjelp/index.html` §F and all of
  `hjelp/vannkjemi.html`, which is the core of B08-1.
- The **"pantry"** half is itself stale: Web has its own full pantry page,
  `web/pantry.html`, reached via the side-menu "📦 Lager" link
  (`nav.pantry`, present in every page's `sidemeny`, including this same
  `index.html`) — pantry is *not* App-only anymore, so this footer
  sentence is internally inconsistent with Web's own navigation one click
  away.
- The **"full sensorisk analyse"** half is **ambiguous**, not asserted
  stale here: Web does have real sensory tooling today — the 18-axis
  flavor-wheel radar chart in the builder (`web/index.html:318-319`,
  `web/js/radar.js`) and up to 18 per-category tasting sliders in the brew
  log (`web/js/brygg_page.js:90-113`, also documented in
  `docs/development/web_b06_accessibility_inventory.md` finding #8) — but
  whether that counts as less than the App's "full sensorisk analyse" is a
  product judgement call this triage does not make.

### Classification

**Stale** (the "pantry" clause) / confirms **App-only/non-Web** (the
"vannkjemi" clause, i.e. B08-1) / **ambiguous** (the "full sensorisk
analyse" clause).

### Proposed bounded future issue title

"WEB FIX — B08-5: update index.html footer — pantry is no longer App-only;
revisit the 'full sensorisk analyse' claim"

### Browser needs

None for the "pantry"/"vannkjemi" halves. The "sensorisk analyse" half
would need a product decision, not a browser check, before any wording
change.

### Dependencies / coupling

Directly coupled to B08-1 (shares the same underlying vannkjemi gap).
Not coupled to W5/B06/#116/#98/#100.

---

## Verified current (checked, not stale)

Recorded so a future fix pass doesn't re-audit these — all confirmed
byte/behavior-accurate against current Web source:

| Handbook claim | Web evidence |
|---|---|
| Grunndata → Malt → Humle → Gjær → live OG/FG/ABV/IBU/EBC + smakshjul, no "beregn"-knapp | `web/index.html:157,209,220,226,318-319` section order matches exactly |
| Bryggelærling/Bryggmester toggle "øverst" | `web/index.html:96-102` modal + `sidemeny-modus-knapp` |
| Måleenheter-bryter i menyen (☰) | `web/index.html` sidemeny `enhetsvelger-blokk`, identical structure to the handbook page's own chrome |
| "📐 Skaler oppskrift" / "Skaler til (L)" (Bryggmester) | `web/index.html:281-289`, `skalerOppskrift()` in `web/js/app.js:906` |
| Malt kg/% behavior + "Bruk prosentfordeling" | `web/index.html:212-216`, `brukMaltProsentfordeling()` in `web/js/app.js:521` |
| "Mål-IBU (denne tilsetningen)" / "Beregn gram", only shown for koketid > 0 | `web/index.html:407-410`, inverse-Tinseth block `web/js/app.js:759-779` |
| "💾 Lagre oppskrift" / "📄 Lagre oppskriftsfil (.kbhrecipe)" / "Avansert: rå JSON" | `web/index.html:263,265,273-278` |
| "Klikk 'Åpne i byggeren' ... under 'Mine oppskrifter'" | `web/js/i18n.js:554` = "Åpne i byggeren"; `web/js/mine_oppskrifter_page.js:73-74` |
| "📥 Importer oppskrift" — file + pasted-text import | `web/importer.html:87,103-113` (✏️ Lim inn tekst tab, textarea) |
| "+ Egendefinert" on malt/hop rows, "+ Egendefinert gjær" | `web/index.html:231,377,398` |
| Utstyrsvalg "under Grunndata" (`utstyr-brewzilla.html:197`) | `web/index.html:182` `#utstyr-velger-label`, inside the Grunndata section |
| Biblioteket dekker 26 stiler | `grep -c '"prio":' web/data/bjcp_styles.json` → 26 |
| klaring.html / humle.html self-disclaimers ("oppskriftsbyggeren regner ikke på klaringsmidler" / "endrer ikke selve IBU-beregningen") | Confirmed true — no fining or kettle-geometry calc exists in `web/js/app.js` |
| gjaervalg.html self-disclaimer ("oppskriftsbyggeren regner ikke ut celletall") | Confirmed true — no pitch-rate/cell-count calc exists in `web/js/app.js` |

---

## Suggested browser matrix (only if a future fix round needs it)

None of the five findings above need a browser to confirm — they are all
either "feature markup/JS exists" or "feature markup/JS does not exist"
questions, fully answerable from static source. A future *fix* round for
any of B08-1..5 is a text-only change and would fall under the existing
`web-full-regression` skill's normal content-change sweep, not a special
matrix of its own.

## Tests that could guard the contract

No automated test currently checks handbook prose against live product
markup — `tests/test_generate_web_i18n_pages.py` (per
`.claude/rules/testing.md`) verifies i18n **key symmetry** (every NO key
has an EN counterpart and vice versa) and generator output byte-parity, but
never checks whether a handbook sentence's *claim* about the product is
still true. That class of drift (this whole B08 finding) is inherently a
semantic check, not a structural one, and is a poor fit for the existing
static i18n-parity suite. No new test is proposed here — recorded only so
a future fix issue doesn't assume such a guard already exists.

---

## Explicitly out of scope for this issue (per its own hard-scope list)

No `web/**` product/content file, i18n string, CSS, or JS was edited to
produce this triage. B08 was not implemented. No deploy occurred. W5 was
not started. `#116`/`#98`/`#100`, App/Core/Bryggeskole, and
`raw_data/unmatched_malt.json` were not touched.
