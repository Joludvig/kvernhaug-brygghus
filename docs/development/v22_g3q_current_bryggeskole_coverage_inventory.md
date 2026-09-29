# V2.2 G3Q-A — Current Bryggeskole coverage inventory (current-product side of #419)

*Docs-only READ/PREP inventory for issue [#420](https://github.com/Joludvig/kvernhaug-brygghus/issues/420), the repo-side half of
[#419](https://github.com/Joludvig/kvernhaug-brygghus/issues/419) (parent: #343 Roadmap V2.2 Goal 3; #65 locked Bryggeskole direction).
It records **current repo truth only**. It does not decide the future curriculum, create or modify any fact, use Kunze chapter
structure, or touch product code.*

| Item | Value |
|---|---|
| Audited base | `0dad9b0d8f0273aa478f29cc20cfd3ceefee39aa` (master at run start, matches the base recorded in #420) |
| Method | Direct reading of `bryggeskole/**`, `bryggeskole/data/**`, `ui/bryggeskole_panel.py`, `ui/process_panel.py`, `ui/yeast_panel.py`, `ui/hop_panel.py`, `ui/kbhbrew_history_panel.py`, `web/hjelp/**` (file inventory and headings), `docs/development/v22_*` contracts, test/CI file inventory |
| Not done | No tests were executed for this document. Test counts below are counts of `def test_` in files, not pass results. Static help prose (`web/hjelp/**`, App panel captions) was inventoried by file and title, **not** content-audited claim by claim. |

Coverage vocabulary follows #420: **substantial / partial / incidental / absent**. "Verified" means `status: verified` in
`bryggeskole/data/course_fact_registry.json` and nothing else.

---

## 1. Executive summary

- Bryggeskole today is **six topic-scoped modules**, one per process stage: Forberedelse/metode, Mesking, Koking/humle,
  Kjøling/overføring, Gjæring, Pakking (`ui/bryggeskole_panel.py` `_MODULER`, `_MODUL_REKKEFOLGE`). Together they hold
  **27 chunks and 29 questions** (15 `concept_check`, 14 `scenario`), all bilingual NO/EN, backed by hidden per-concept mastery.
- The Course Fact Registry holds **30 records: 29 `verified`, 1 `draft`** (`FACT-MASH-0003`, iodine test, needs a second source and is
  referenced by no shipped content). Every question/chunk `source_claims` entry points to a verified record.
- The spine is **process-oriented and qualitative**. It teaches direction and mechanism ("warmer mash → less fermentable wort in one study",
  "late hops keep more aroma, lower utilisation"), deliberately without numeric schedules, targets or dosages.
- **Learn→Plan bridges exist for three modules only** (Mesking → `ui/process_panel.py`, Gjæring → `ui/yeast_panel.py`, Koking/humle →
  `ui/hop_panel.py`). Kjøling/overføring, Pakking and Forberedelse/metode have no bridge into an App surface. One Learn→Reflect
  bridge exists in `ui/kbhbrew_history_panel.py`; it is static i18n text, not registry-backed.
- **Raw materials are not taught as subjects.** Malt, hops, yeast and water appear only inside process contexts (enzymes in the mash,
  hop timing in the boil, yeast temperature in fermentation). Water and malt as ingredients have no Bryggeskole content at all
  (this is the gap tracked as [#418](https://github.com/Joludvig/kvernhaug-brygghus/issues/418) / G3P).
- **App tools are broad, teaching is narrow.** Live OG/IBU/EBC/ABV, BJCP matching, water/salt dosing, brew-day plan and Brew History
  exist as calculators/forms; none of them is verified teaching, and their existence must not be read as course coverage.
- **Static Web help is a second, unlinked knowledge surface**: 12 hjelp pages × NO/EN, no reference to Course Fact Registry ids,
  no quiz, no mastery. The Web has no Bryggeskole module (no match for "bryggeskole" in `web/js` or the root `web/*.html` pages).
- **Acceptance is mostly automated.** Owner-PC evidence is visible only for a subset (see §7). No recorded human result was found in the
  inspected files for the §9 acceptance scenarios of the Koking, Kjøling, Pakking, Metode or Gjæring contracts.

---

## 2. Coverage matrix

Legend — **Type**: SM structured module · QM question/mastery · L→P Learn→Plan bridge · CT contextual teaching · SH static help only ·
AT App tool without teaching. **NO/EN**: B both / P partial / N none. **Visual**: what actually ships. **Accept.**: A automated only · O owner-PC
evidence seen · U not proven (see §7). "Registry facts" lists ids from the registry's own `modules`/`concepts` fields.

| # | Domain | Coverage | Location (exact) | Type | Verified facts | NO/EN | Visual/interactive | Accept. | Duplication / drift risk |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Malt** (as raw material) | incidental | Enzyme role only inside `pilot_mashing_fundamentals.json`; malt data in `ui/malt_panel.py`, `web/data/malt.json` | AT (+ CT via mash chunks) | None about malt itself (base/specialty, EBC, kilning). Only MASH-0001/0004 mention malt enzymes/enzyme content | Module B; tool B | none | A | Malt claims in App/Web masterdata are not registry-backed |
| 2 | **Hops** (as raw material) | partial | Alpha-acid isomerisation/aroma volatility inside `pilot_boil_hop_fundamentals.json`; `ui/hop_panel.py`; `web/hjelp/humle.html` | SM+QM+L→P (+SH) | HOP-0001, 0002, 0003 | B | `boil_timeline.py` SVG (static) | A | `humle.html` overlaps HOP-* topics with no registry link |
| 3 | **Yeast** (as raw material) | partial | Temperature/strain dependence in `pilot_fermentation_temperature.json`; `ui/yeast_panel.py`; `web/hjelp/gjaervalg.html`, `gjaerhosting.html` | SM+QM+L→P (+SH) | BREW-0001, 0002, 0003 (temperature only). OXY-0001 mentions sterols/UFA | B | none | A | `gjaervalg.html` covers flavour/strain claims that BREW-0002 also makes |
| 4 | **Water** | absent (Bryggeskole) | `ui/water_panel.py` (salts/profiles), `web/hjelp/vannkjemi.html` (advanced) | AT + SH | None | tool B; help B | none | U | Most of the water claims in App/Web are unsourced against the registry |
| 5 | Adjuncts / other fermentables | absent | Not found in Bryggeskole or registry | — | None | — | — | — | — |
| 6 | Recipe/planning theory | incidental | App recipe engine (live OG/IBU/EBC/ABV, BJCP match) in `modules/**` + `ui/**`; METHOD-0004 (planning differs by method) | AT (+ one CT fact) | METHOD-0004 only | tool B | none | A (calc contract tests) | Calculator behaviour is contract-tested, not taught |
| 7 | Preparation / method / equipment | partial→substantial for method choice | `pilot_method_context_fundamentals.json`, `method_context_flow.py`; `ui/equipment_panel.py`; `web/hjelp/bryggemetoder.html`, `utstyr-brewzilla.html` | SM+QM (+AT, SH) | METHOD-0001…0005, reuses MASH-0001, BOIL-0001 | B | `method_context_flow.py` SVG (static) | A | Equipment panel/help are device-specific and outside the registry |
| 8 | Milling | absent | Former "Maling av malt/Mølle" grid cell was orientation-only and was replaced by Forberedelse/metode (`ui/bryggeskole_panel.py` header comment, #380) | — | None | — | — | — | — |
| 9 | Mashing | partial | `pilot_mashing_fundamentals.json` (3 chunks, 3 questions); `ui/process_panel.py` (mash-step editor, profiles, decoction/reiterated mash) | SM+QM+L→P (+AT) | MASH-0001, 0002, 0004. **MASH-0003 (iodine) draft-only, unused** | B | none (text + quiz) | A | Process profiles carry unsourced numeric defaults; not registry-backed |
| 10 | Lautering / sparging | incidental | METHOD-0002 describes sparge as layout; sparge method is a field in `ui/process_panel.py` | CT + AT | METHOD-0002 (layout only; batch vs fly explicitly out of scope) | B | none | A | Sparge choice exposed in App without teaching |
| 11 | Wort collection | absent | Not found | — | None | — | — | — | — |
| 12 | Boiling | partial→substantial | `pilot_boil_hop_fundamentals.json` (6 chunks, 8 questions); `boil_timeline.py` | SM+QM | BOIL-0001, 0002, 0003, 0004 | B | static SVG timeline | A | Kunze is cited second-hand in BOIL-0001/0003 (see §9) |
| 13 | Hop timing / use | substantial (qualitative) | Same module; `ui/hop_panel.py` bridge (CHUNK-BOILHOP-C…F) | SM+QM+L→P | HOP-0001…0003 | B | static SVG timeline | A | Bridge hard-codes chunk ids |
| 14 | Whirlpool / hopstand | partial | Inside HOP-0002/0003 and the boil module; G3L contract deliberately keeps whirlpool outside App boil-time semantics | SM+QM (+L→P) | HOP-0002, 0003 | B | timeline | A | App timing semantics vs. whirlpool teaching kept apart by contract, not by code enforcement seen here |
| 15 | Cooling | partial | `pilot_cool_transfer_fundamentals.json` (5 chunks, 6 questions); `cool_transfer_flow.py` | SM+QM | COOL-0001, 0002 | B | static SVG flow | A | None to Plan |
| 16 | Transfer | partial | Same module | SM+QM | TRANSFER-0001, OXY-0002 | B | static SVG flow | A | No bridge |
| 17 | Oxygenation / aeration | partial | Same module | SM+QM | OXY-0001, 0002, 0003 | B | SVG (oxygen labels) | A | OXY-0001 conditional wording must stay conditional |
| 18 | Fermentation | partial (temperature only) | `pilot_fermentation_temperature.json` (3 chunks, 2 questions); `ui/yeast_panel.py` bridge | SM+QM+L→P | BREW-0001, 0002, 0003 | B | none | A | Smallest module (2 questions); no fermentation phases, pitch rate, attenuation, monitoring |
| 19 | Conditioning / maturation | incidental | PACK-0004 only mentions time; `web/hjelp/klaring.html` | SH | None dedicated | help B | none | U | — |
| 20 | Clarification | static help only | `web/hjelp/klaring.html` (break, trub, finings, cold crash, chill haze) | SH | None dedicated (BOIL-0003/COOL-0002 cover hot/cold break mechanism only) | B | none | U | Web page describes topics the registry covers partially — unlinked |
| 21 | Carbonation | partial | `pilot_package_fundamentals.json`; `web/hjelp/trykkgjaering.html` | SM+QM (+SH) | PACK-0001, 0002 (mechanism only, no numbers by design) | B | `package_flow.py` SVG | A + O (diagram layout, see §7) | No dosing/volumes teaching; calculators in App are untaught |
| 22 | Packaging | partial | Same module (5 chunks, 5 questions) | SM+QM | PACK-0001…0004, COOL-0003, OXY-0002 | B | static SVG flow | A + O (layout) | No bridge |
| 23 | Cleaning / sanitation | incidental | The sanitation *boundary* only (COOL-0003) | SM+QM (partial) | COOL-0003 | B | — | A | No cleaning procedure/chemistry content |
| 24 | Safety | partial | Package pressure safety (PACK-0003); `web/hjelp/humle.html` also holds general brewing safety | SM+QM (+SH) | PACK-0003 | B | — | A | Web safety prose is not registry-backed |
| 25 | Measurement — temperature | incidental | Mash/fermentation temperature as concepts; measured values in `ui/kbhbrew_history_panel.py` | CT + AT | Concept only (MASH-0002, BREW-0001) | B | — | A | — |
| 26 | Measurement — gravity, ABV | AT only | `ui/abv_calculator_panel.py`; OG/FG/volume entry in `ui/kbhbrew_history_panel.py` (strict numeric validation) | AT | None | tool B | — | A + O (history flow, see §7) | Hydrometer/refractometer use is untaught |
| 27 | Measurement — volume, pH, pressure, calibration | absent (teaching) | Volume appears in App calculators; pH/calibration: no Bryggeskole content found; pressure as safety concept only (PACK-0003) | AT / — | PACK-0003 (pressure safety only) | — | — | U | — |
| 28 | Sensory / quality | static help + capture UI | `web/hjelp/sensorikk.html`; sensing form in `ui/kbhbrew_history_panel.py` | SH + AT | None | help B; tool B | none | U | Off-flavour prose unsourced against the registry |
| 29 | Evaluate / reflect / improve next brew | partial (product-methodology) | `ui/kbhbrew_history_panel.py`: actuals form, planned-vs-actual, sensing/learning fields incl. `hypothesis`, next-variant seed, collapsed `_render_laer_bro` | L→R (static i18n) + AT | Intentionally none (G3N: methodology, not a brewing-science claim) | B | expander only | A + O (next-variant, per G3N §1.6) | Reflect text lives in i18n, outside the registry by design |
| 30 | Brewing-science foundations already present | partial | Enzymes/dextrins (MASH-0001), isomerisation (HOP-0001), hot/cold break (BOIL-0003, COOL-0002), DMS (BOIL-0002), enzyme inactivation (BOIL-0001), yeast temperature (BREW-*) | SM+QM | as listed | B | — | A | — |
| 31 | Advanced / professional material anywhere | static help + presentation only | `web/hjelp/sterke-ol.html`, `gjaerhosting.html`, `trykkgjaering.html`, `vannkjemi.html`; "Bryggeri" environment in `ui/bryggeskole_panel.py` | SH; environment = labels only | None registry-backed | help B | Bryggeri env swaps `_PROSESS_STADIER` labels only; same six modules | U | Bryggeri env could be mistaken for professional content — it is navigation labels (no separate facts) |

Additional domains clearly present in repo truth (not in the required list):

| Domain | Coverage | Location | Type |
|---|---|---|---|
| Style / BJCP matching | AT | `ui/style_panel.py`, `web/data/bjcp_styles.json` | AT, no teaching |
| Brew-day planning / process profiles | AT + one bridge | `ui/brewday_panel.py`, `ui/process_panel.py`, `modules/process_profiles.py` | AT (+ Mesking L→P) |
| Pantry / shopping / stock | AT | `ui/pantry_panel.py`, `ui/shopping_list_panel.py`, `ui/humle_lager_panel.py` | AT, not learning |
| Course mechanics (mastery, answer order) | implemented | `bryggeskole/mastery.py`, `mastery_store.py`, `answer_order.py` | infrastructure |

---

## 3. Verified-fact coverage matrix

Registry: `bryggeskole/data/course_fact_registry.json`, `schema_version: 1`. 30 records, 29 verified, 1 draft. Consumed via the
verified-only API (`read_verified_records` / `get_verified_record` / `find_verified_records`) in `bryggeskole/course_fact_registry.py`.

| Registry `modules` id | Fact ids | Status | Shipped pilot file | Chunks / questions |
|---|---|---|---|---|
| `fermentation.fundamentals` | FACT-BREW-0001, 0002, 0003 | verified ×3 | `pilot_fermentation_temperature.json` | 3 / 2 |
| `mashing.fundamentals` | FACT-MASH-0001, 0002, 0004 | verified ×3 | `pilot_mashing_fundamentals.json` | 3 / 3 |
| `mashing.fundamentals` | FACT-MASH-0003 | **draft** (one source only; #337 requires a second) | not used | — |
| `boil_hop.fundamentals` | FACT-BOIL-0001…0004, FACT-HOP-0001…0003 | verified ×7 | `pilot_boil_hop_fundamentals.json` | 6 / 8 |
| `cool_transfer.fundamentals` | FACT-COOL-0001…0003, FACT-OXY-0001…0003, FACT-TRANSFER-0001 | verified ×7 | `pilot_cool_transfer_fundamentals.json` | 5 / 6 |
| `package.fundamentals` | FACT-PACK-0001…0004 (+ reuses COOL-0003, OXY-0002) | verified ×4 | `pilot_package_fundamentals.json` | 5 / 5 |
| `method_context.fundamentals` | FACT-METHOD-0001…0005 (+ reuses MASH-0001, BOIL-0001) | verified ×5 | `pilot_method_context_fundamentals.json` | 5 / 5 |

Observations about the registry as evidence (facts about the registry, not new claims):

- **Source tiers are mostly B.** Tier A appears for the fermentation, HOP-0001/0002, MASH-0001/0002/0004, OXY-0001, PACK-0001/0002 (partly) records. Most process
  facts rest on Palmer *How to Brew*, Brew Your Own, AHA, Brewers Association and manufacturer pages.
- **Kunze is already cited, but second-hand.** FACT-BOIL-0001 and FACT-BOIL-0003 cite "Kunze, *Technology Brewing and Malting*" as reported in a Brewers Association-hosted
  VLB presentation. No record cites the Kunze book directly.
- **FACT-MASH-0002** was verified from abstract/metadata only (publisher full text returned HTTP 403); its notes restrict it to the exact 65–80 °C study range.
- **Classification mix**: `documented_fact`, `practical_experience` (BOIL-0004, TRANSFER-0001) and `professional_interpretation` (BREW-0003, MASH-0004, HOP-0003, OXY-0003, PACK-0004, METHOD-0004/0005).
- **No records exist** for: malt (as a raw material), water, hops as a raw material beyond HOP-0001…0003, yeast beyond temperature/oxygen, milling, lautering technique,
  wort collection, conditioning, clarification, cleaning/sanitation procedure, measurement/calibration, pH, sensory, adjuncts.
- Any App/Web statement in those areas is **not** verified course truth.

---

## 4. Structured learning vs static help vs App tool

| Class | What it is | Surfaces (current) | May be cited as verified Course Fact Registry truth? |
|---|---|---|---|
| **Structured learning** | Lesson chunks (paged), scenario/concept questions, answer-order shuffle, feedback, hidden per-concept mastery, per-module in-session resume, summary | `ui/bryggeskole_panel.py` (top-level tab "Bryggeskole", `app.py`) over `bryggeskole/pilot_*.py` + JSON | Yes — `source_claims` validated against the verified-only registry API |
| **Learn→Plan bridge** | Collapsed expander reusing existing chunks read-only; no questions, no mastery call | Mesking: `ui/process_panel.py` (CHUNK-MASH-B, -C); Gjæring: `ui/yeast_panel.py` (CHUNK-FERM-A, -B, -C); Koking/humle: `ui/hop_panel.py` (CHUNK-BOILHOP-C…F, plus a guardrail warning) | Yes (same chunks) — but only for those chunk ids |
| **Learn→Reflect bridge** | Collapsed expander of static i18n text before actuals form | `ui/kbhbrew_history_panel.py::_render_laer_bro` | No — deliberately reads no pilot and cites no registry fact |
| **Contextual teaching (captions/hints)** | Captions/help strings inside App panels | e.g. `ui/water_panel.py`, `ui/process_panel.py` header captions, tooltips | No — not audited claim-by-claim here; not registry-backed |
| **Static help** | 12 hjelp pages (`web/hjelp/*.html`, NO; mirrored in `web/en/hjelp/*.html`), plus "?" popovers (`web/js/help.js`) | Web only; pages: bryggedag, bryggemetoder, gjaervalg, trykkgjaering, sterke-ol, gjaerhosting, vannkjemi, humle, klaring, sensorikk, utstyr-brewzilla + hub `index.html` | **No** — unlinked to registry ids; static prose is not verified truth |
| **App tool without teaching** | Calculators/planners/forms | recipe engine (OG/IBU/EBC/ABV), BJCP match, water/salts, process profiles, brew-day plan, Brew History, ABV calculator, pantry/shopping | **No** |

Rule visible in code: the Bryggeskole tab reuses six **topic-scoped copies** of the pilot engine (each `pilot_*.py` defines its own `PilotContentError`; `_PILOT_CONTENT_ERRORS` is a tuple
of six classes) and shares only mastery, answer-order and the process grid.

---

## 5. NO/EN status

| Surface | NO | EN | Notes |
|---|---|---|---|
| Pilot chunks + questions + feedback (all six JSON files) | yes | yes | Every `text`, `prompt`, `option`, `feedback_*` object is `{"no","en"}` in the files read (mashing shown in full; others share the schema) |
| Panel UI strings | yes | yes | Keys under `bryggeskole.*` in `modules/i18n.py`; `_PROSESS_STADIER` and `_KONSEPT_LABELS` are local bilingual dicts in `ui/bryggeskole_panel.py` |
| Learn→Plan bridge headers/footers | yes | yes | `prosess.laer_bro.*`, `gjaering.laer_bro.*`, `koking.laer_bro.*` via `t()` |
| Learn→Reflect bridge | yes | yes | `brew_history.laer_bro.*` |
| SVG diagrams | yes | yes | Each `render_*_svg(language)` takes a language and fails on unsupported ones (`_require_language`) |
| Web hjelp pages | yes (12) | yes (12) | `web/README.md`: NO/EN symmetric; EN generated by `scripts/generate_web_i18n_pages.py`; guarded by `tests/test_generate_web_i18n_pages.py` |
| Surrounding App text not in a bridge | mixed | mixed | e.g. `ui/process_panel.py` renders a hard-coded Norwegian `st.subheader("🧭 Bryggemåte")` and caption (outside the bridge); not audited further |

**Partial/none:** no known surface is EN-only or NO-only inside Bryggeskole. Coverage of *all* App panels in EN was not audited here.

---

## 6. Visual / interactivity status (actual, not aspirational)

| Module | Diagram | Interactivity |
|---|---|---|
| Forberedelse/metode | `method_context_flow.py` — static SVG | Quiz only |
| Mesking | none | Quiz only |
| Koking/humle | `boil_timeline.py` — static, qualitative horizontal timeline (no numeric scale) | Quiz only |
| Kjøling/overføring | `cool_transfer_flow.py` — static SVG flow | Quiz only |
| Gjæring | none | Quiz only |
| Pakking | `package_flow.py` — static SVG (fermenter → split path → serve/store) | Quiz only |

- All four SVG modules state "deliberately not interactive: no clickable markers, no JavaScript".
- Interactivity that exists: paged lessons (Forrige/Neste), question rounds, shuffled answer options (`answer_order.py`), immediate feedback, locked answer state, per-module in-session resume, module cards with status badges and a
  "recommended next" signal (`_anbefalt_modul`), and two environment views (Hjemmebrygger/Bryggeri) that only change labels.
- No simulators, sliders, drag-and-drop, calculators-as-exercises, or interactive graphs exist in Bryggeskole.
- "Gjennomført denne økten" (completed this session) lives only in `st.session_state`; no persistent completion contract. Mastery persists locally (`bryggeskole/mastery_store.py`, DEMO_MODE panel guard `_les_tilstand`/`_skriv_tilstand` keeps demo state out of disk).

---

## 7. Known acceptance evidence

**Automated (counts of `def test_`, not results of a run here):**

| Area | File(s) | Count |
|---|---|---|
| Panel | `tests/test_ui_bryggeskole_panel.py` | 113 |
| Registry | `tests/test_course_fact_registry.py` | 78 |
| Pilot engines | `test_pilot_fermentation` 42, `_boil_hop` 34, `_cool_transfer` 35, `_mashing` 30, `_package` 38, `_method_context` 39 | 218 |
| Flow/timeline SVG | boil 12, cool_transfer 17, package 21, method_context 16 | 66 |
| Mastery + store + answer order | 48 + 10 + 16 | 74 |
| Streamlit SVG rendering | `tests/test_bryggeskole_svg_streamlit_rendering.py` | 3 |
| Browser/runtime (CI) | `tests/playwright_streamlit/svg-runtime-dom.spec.js`, `module-grid-responsive.spec.js`, run in `.github/workflows/playwright-browser-gate.yml` as `test:bryggeskole-svg-runtime` and `test:bryggeskole-grid-runtime` | 2 specs |

**Owner-PC / human evidence visible in the repo:**

- Pakking diagram composition and nav-button grouping: commit `b61c9ec` ("owner-QA correction", #397/#398) and follow-ups `31985ba`, `f896a5e`, `aee6ad9`, `1edd97c` (UX legibility, contrast, responsive grid). This is evidence that the owner looked at these on a real screen and requested corrections; it is not a recorded pass statement.
- Brew History next-variant flow: `docs/development/v22_g3n_evaluate_inspect_closure_contract.md` §1.6 records owner-PC QA of #363 on the real product path.

**Not proven (no recorded human result found in the inspected files):** the §9 "transfer/application acceptance scenarios" defined in the Mesking, Gjæring (`v22_g3j`), Koking/humle (`v22_g3l`),
Evaluate/reflect (`v22_g3n`) contracts, and module-level owner acceptance for Kjøling/overføring, Forberedelse/metode and Gjæring. Absence of a record here is not proof that it did not happen.

**Adjacent, but not Bryggeskole:** `docs/development/phase3a_learner_master_acceptance.md` covers the Web Bryggelærling/Bryggmester modes (automated 3A PASS, human novice gate pending) — it says nothing about the Streamlit Bryggeskole tab.

---

## 8. Confirmed gaps visible from the repo alone (not exhaustive)

1. **Raw-material learning (#418 / G3P).** No module or registry record teaches malt, hops as an ingredient, yeast as an organism (beyond temperature) or water. The process spine assumes the learner already knows what these are.
2. **Water has no Bryggeskole presence at all**, although `ui/water_panel.py` and `web/hjelp/vannkjemi.html` (advanced) exist. Chlorine/chloramine, pH concept, ions: no registry facts.
3. **Malt facts absent**: base vs specialty, colour/EBC, extract, kilning, storage — App computes EBC/OG from malt data but nothing teaches it.
4. **Fermentation is a single-topic module** (temperature only; 2 questions): no phases, pitching/viability, attenuation, monitoring, end-of-fermentation.
5. **Milling, wort collection, lautering technique, conditioning/maturation, cleaning/sanitation procedure** are absent or only boundary-level.
6. **Measurement and control**: hydrometer/refractometer use, calibration, pH, volume measurement — App inputs exist, no teaching, no facts.
7. **Clarification and sensory** exist only as unlinked Web help; no registry facts, no quiz.
8. **Bridges missing** for Kjøling/overføring, Pakking, Forberedelse/metode into the App surfaces they concern (e.g. equipment panel, brew-day plan).
9. **`FACT-MASH-0003` (iodine test)** is draft-only and unused; the mashing module cannot teach conversion checks.
10. **Numeric/quantitative teaching is intentionally absent** (priming amounts, hop utilisation numbers, mash rests, pH targets). The registry notes forbid presenting such numbers as universal; the course therefore cannot yet support quantitative recipe decisions.
11. **No visual for Mesking or Gjæring**; all diagrams are static.
12. **No persistent completion/progress contract** across sessions beyond hidden mastery.
13. **Registry sourcing depth**: mostly tier B; Kunze only second-hand; MASH-0002 abstract-only.
14. **Drift risk between Web help (12 pages × 2 languages), App captions and the registry**: overlapping topics (hops, yeast choice, clarification, method, pressure fermentation) with no shared ids.
15. **Doc-history drift**: `docs/development/v22_g3f_package_module_contract.md` says the four Package records "still remain `draft`" at contract time, while the registry now has PACK-0001…0004 as `verified`. Historical contract text is not current truth.

---

## 9. Handoff to #419 — what the later Kunze audit must add

This inventory gives the **current-product side**. The Kunze pass must not restate it; it should map the subject domain and compare against §2/§3.

The Kunze audit must supply (all from the validated local OCR, not from memory):

1. **The subject-domain map**: the book's own chapter/section structure and terminology, mapped to the domain rows in §2 (including domains rows 5, 8, 11, 19, 20, 23, 27 that are `absent`/`incidental` here).
2. **Per domain**: what the book treats as core vs specialist/industrial vs out of homebrew scope, with exact chapter/page references, so #419 can separate "missing for a homebrewer" from "professional/LATER".
3. **Evidence quality per domain**: which claims Kunze supports directly, and which existing registry facts it could upgrade — in particular re-sourcing **FACT-BOIL-0001** and **FACT-BOIL-0003** (currently second-hand Kunze) and checking **FACT-MASH-0003** (draft) for a second source. Any promotion is a separate, source-reviewed change.
4. **Contradictions or scope conflicts** between Kunze and existing verified facts (direction, wording traps recorded in registry `notes`), reported, not resolved here.
5. **Homebrew-relevance mapping**: which Kunze topics are already covered by App tools or Web help (§4) and only lack verified teaching, versus topics with no product surface at all.
6. **Prioritisation input** that connects to #418 (raw materials): which Kunze raw-material material is needed for the smallest finishable journey, without importing a professional brewing textbook wholesale.
7. **Numeric-content policy**: where Kunze gives numbers the registry currently refuses to assert, mark them as candidate facts with unit/scope caveats, never as teaching content.

What #419 can rely on from this document: module list and boundaries (§1, §4), the exact fact ids per module (§3), which surfaces are bridges vs tools vs help (§4), NO/EN and visual status (§5–§6), acceptance state (§7), and the gap list (§8).

What this document does **not** establish: which curriculum is right, whether static help claims are correct, whether any App calculator output is pedagogically sound, or the completeness of any subject.

---

## 10. Boundary statement

Docs-only. No product code, Course Fact Registry, tests, Web, deploy or Sóti file was changed. No new fact was created or promoted. No general brewing knowledge or Kunze structure was used to infer missing curriculum; gaps in §8 are stated only where the repo shows the absence.
