# App Stabilization A2 — Calculation Presentation Consistency Preflight

*Part of Roadmap V2.1 #101 Phase 2 / CoS day queue #153, Q5. Source
audit only — no App/Core/Web behavior changed by this document.
Traced against master `b722811a7e04def9ae98baa95acaa78e6d0cbac4`.*

---

## 1. Current calculation ownership map

`modules/recipe_context.py::bygg_recipe_context()` is the App's single
authoritative calculation path. It is called exactly once per
Streamlit run, from `app.py:145`, after the malt/hop/yeast panels have
rendered, and calls straight into `modules/calculations.py` — the
Core-governed module (`docs/development/CORE_CALCULATION_CONTRACT.md`,
shared line-for-line with `web/js/calc.js`):

| Output | Authoritative function | Called from |
|---|---|---|
| OG | `beregn_og()` | `recipe_context.py:68` |
| EBC | `beregn_ebc()` | `recipe_context.py:70` |
| IBU | `beregn_total_ibu()` | `recipe_context.py:71` |
| FG, ABV (planned) | `beregn_fg_og_abv()` | `recipe_context.py:72` |
| ABV (measured OG+FG) | `beregn_abv_fra_og_fg()` → `{standard, high_gravity}` | `ui/abv_calculator_panel.py:39`, `modules/kbhbrew_history_ui.py:154` |
| BU:GU | `style_engine.py::analyser_stil_og_balanse()` (derives from `recipe["stats"]`, no new gravity/IBU math) | `recipe_context.py:95` |

The returned `ctx` dict (`ctx["og"]`, `ctx["fg"]`, `ctx["abv"]`,
`ctx["ibu"]`, `ctx["ebc"]`, `ctx["effektivitet"]`, `ctx["volum"]`) is
threaded, unmodified, into every downstream panel
(`recipe_card.py`, `style_panel.py`, `brewday_panel.py`,
`water_panel.py`, `pantry_panel.py`, `card_template.py`,
`kbhbrew_ui.py`). Confirmed by reading `app.py` in full: `ctx` is
built exactly once (`app.py:145-153`) and never rebuilt or shadowed
elsewhere in the tab-render sequence.

Formatting (not calculation) is centralized in
`modules/export_format.py`: `fmt_og`/`fmt_fg` → 3 decimals,
`fmt_abv` → 1 decimal, `fmt_ibu`/`fmt_ebc` → rounded to the nearest
whole number. This layer is consistent and out of scope for this
audit — the finding below is about *which number* reaches these
formatters, not how it is displayed once it does.

**Deliberately separate, correctly-labeled derived calculations**
(not part of the duplication problem — verified by reading each call
site's UI label):

- `modules/brewday_calc.py::beregn_effektivitete()` — mash/brewhouse
  efficiency computed *backwards* from a measured pre-boil/OG reading,
  not a re-derivation of `beregn_og()`. Deliberately reuses the same
  `8.3454` unit factor (own docstring: "Uses the same 8.3454 unit
  factor as beregn_og() so the numbers are consistent") — this is the
  correct, intentional relationship between a forward and an inverse
  calculation, not a duplicate. Displayed under "Maskeeffektivitet" /
  "Brygghuseffektivitet", next to (not instead of) `ctx["effektivitet"]`
  labeled "Planlagt effektivitet" (`ui/brewday_panel.py:368-375`).
- `modules/brewday_calc.py::beregn_post_boil_og()` — estimates OG from
  a measured pre-boil gravity/volume reading concentrated to a
  post-boil volume. Displayed as "Forventet OG (etter kok)" directly
  beside "Planlagt OG" (`ctx["og"]`) with an explicit `+/-` "Avvik"
  delta metric (`ui/brewday_panel.py:259-267`) — the UI treats the two
  as deliberately different numbers being compared, not the same
  number computed two ways.
- `modules/kbhbrew_history_ui.py::bygg_planlagt_vs_faktisk()` — the
  `.kbhbrew` "planned vs actual" comparison (issue #83). For ABV this
  is the **model** the rest of the app should follow: it derives the
  "faktisk" (actual) ABV *only* for display, via
  `beregn_abv_fra_og_fg()` (own docstring, lines 118-126, explicitly:
  *"ingen ny ABV-formel bygges her"* — "no new ABV formula is built
  here"), wrapped in a `try/except ValueError` so an invalid
  actual-FG-over-actual-OG entry degrades to "no actual value shown"
  instead of a garbage number. `modules/kbhbrew.py`'s
  `FORBUDTE_ACTUALS_EKSPORTFELT` (line 87) additionally guarantees a
  locally-computed `actual_abv` can never leak onto the `.kbhbrew`
  wire — actuals ABV is always *derived*, never stored/exported as its
  own field.

## 2. Source-proven duplicate/shortcut inventory

### Finding 1 — `ui/recipe_card.py:80`: inline measured-ABV formula in the brew log form

```python
"actual_abv": round((actual_og - actual_fg) * 131.25, 1),
```

- **Formula/path**: hand-inlines the same arithmetic as
  `beregn_abv_standard()` (`modules/calculations.py:110-124`,
  `ABV = (OG - FG) * 131.25`), directly in the "Nytt brygg" bryggelogg
  form's submit handler, instead of calling it.
- **Authoritative comparison path**: `beregn_abv_standard()` /
  `beregn_abv_fra_og_fg()` — the exact Core contract (#77) built for
  this precise scenario (a *measured* OG+FG, no recipe/attenuation
  context), and already correctly used for the analogous "actual ABV"
  presentation in `.kbhbrew` history (`kbhbrew_history_ui.py:154`).
- **Inputs/units/rounding**: identical inputs (measured OG, measured
  FG, both plain SG floats) and identical arithmetic — the *value*
  this code computes for valid input is numerically identical to
  `beregn_abv_standard()`'s. The divergence is in **validation**, not
  arithmetic.
- **Disagreement currently possible?** Yes, in the sense of silent
  wrong output, not cross-path numeric disagreement: `actual_og` and
  `actual_fg` are two independent `st.number_input` widgets
  (`min_value=1.000, max_value=1.200` each, no cross-field
  constraint) — a user can enter `actual_fg > actual_og` (e.g. a
  transposed/typo'd reading) and this code silently stores and later
  displays a **negative ABV** (`ui/recipe_card.py:95`,
  `f" · ABV {entry['actual_abv']:.1f}%"`). `beregn_abv_standard()`
  would instead raise `ValueError("FG kan ikke være høyere enn OG")`
  for the exact same input (`_valider_malt_og_fg()`,
  `modules/calculations.py:88-107`), which is the behavior
  `kbhbrew_history_ui.py:154-156` already relies on (catches
  `ValueError`, shows no actual value instead of a bad one).
- **Severity/trust impact**: Low-to-medium. Only reachable via an
  operator data-entry mistake in a rarely-audited free-text brew log,
  not a live per-keystroke recipe value — but it is a genuine,
  demonstrable silent-bad-data path (a negative-percent ABV visibly
  printed in the brew log) with zero user-facing error, in an app
  whose stated priority order starts with correctness.
- **Justified or should delegate?** Should delegate. There is no
  reason for this call site to reimplement arithmetic Core already
  owns and validates; the local formula strictly loses functionality
  (no validation) for no benefit.

### Finding 2 — `ui/brewday_panel.py:344`: inline measured-ABV formula in the brewday sheet

```python
if og_f > 1.001 and fg_f > 1.000:
    st.metric("Beregnet ABV", f"{(og_f - fg_f) * 131.25:.1f}%")
```

- **Formula/path**: same inline duplicate of the standard-ABV
  arithmetic, in Step 5 ("Gjæring") of the live brewday sheet, fed
  from two free-text (`st.text_input`) fields `bd_og`/`bd_fg` parsed
  with `float(... or 0)`.
- **Authoritative comparison path**: same as Finding 1 —
  `beregn_abv_standard()` / `beregn_abv_fra_og_fg()`.
- **Inputs/units/rounding**: identical arithmetic; identical
  numeric result to Core's function for valid input.
- **Disagreement currently possible?** Yes, same class as Finding 1:
  the guard `og_f > 1.001 and fg_f > 1.000` checks only that both
  values are plausible SG numbers individually — not that
  `fg_f <= og_f`. A mistyped `bd_fg` greater than `bd_og` silently
  renders a negative-percent `st.metric`, with no error shown, right
  next to the correctly-computed "Planlagt" OG/ABV metrics on the same
  screen — a direct side-by-side presentation-consistency problem: one
  number on the same expander is Core-validated, the other is not.
- **Severity/trust impact**: Low-to-medium, same reasoning as Finding
  1 — a manual brew-day data-entry field, but this one is on the
  primary live brewday worksheet the audit's own scope explicitly
  names.
- **Justified or should delegate?** Should delegate, same reasoning
  as Finding 1.

### Finding 3 — `modules/brewday_calc.py`: local Tinseth re-derivation for `ibu_planlagt`/`ibu_faktisk_prosess`

`_bygg_humle_entry()` (lines 109-146) and its `_ibu_for_tid()` closure
(lines 115-119) reimplement Tinseth's bigness/utilization formula
locally instead of calling `beregn_total_ibu()`:

```python
alfa = h_info.get("alfa") or h_info.get("alfa_typisk") or 5.0     # line 112
...
def _ibu_for_tid(effektiv_tid):
    if effektiv_tid > 0 and bigness > 0 and volum > 0:
        times = (1 - math.exp(-0.04 * effektiv_tid)) / 4.15
        return round((gram * 1000 * (alfa / 100.0) / volum) * bigness * times, 1)
    return 0.0
```
`bigness` itself is computed identically to `beregn_total_ibu()`'s
`bigness_faktor`, inline at `lag_brewday_plan()` line 271. The
per-addition results feed `ibu_planlagt = round(sum(h["ibu_bidrag"] ...), 1)`
and `ibu_faktisk_prosess` (lines 284-285), both displayed to 1 decimal
in the brewday sheet (`ui/brewday_panel.py:185-188`) beside `ctx["ibu"]`
elsewhere in the app (`fmt_ibu`, rounded to a whole number, in
`recipe_card.py`/`card_template.py`/`style_panel.py`).

**Two independent, source-proven divergences from the authoritative
path, of different character:**

**3a. Alpha-acid fallback regresses an already-fixed bug.**
`_bygg_humle_entry`'s `h_info.get("alfa") or h_info.get("alfa_typisk") or 5.0`
(line 112) is, character-for-character, the exact buggy pattern that
`modules/calculations.py::_hent_alfa()` was written to replace. Per
`tests/test_calculations_ibu_alfa.py`'s own header comment (Steg
F11G/F11I, 2026-08-07): *"den gamle koden brukte `alfa =
entry.get("alfa") or entry.get("alfa_typisk") or 5.0` som feilaktig
behandlet en eksplisitt alfa=0.0 som 'mangler'"* — this was a real,
already-diagnosed-and-fixed defect class in this exact codebase, fixed
in `beregn_total_ibu()`'s call path but never propagated to
`brewday_calc.py`'s independent copy of the same arithmetic.
**Currently reachable?** No — confirmed by grepping
`data/master_humle_v2.json` for `"alfa": 0`/`"alfa_typisk": 0`: no hop
in the live master database has an explicit `0.0` alpha acid today.
The defect is real and proven by direct code comparison, but latent
under current data.

**3b. Round-then-sum vs. sum-then-round is a provable, generally-reachable numeric divergence.**
`beregn_total_ibu()` accumulates the **unrounded** per-hop IBU
contribution and returns one raw float; `ctx["ibu"]` is that raw value
(only rounded at display time, once, by `fmt_ibu`/`fmt_ibu_bid`).
`ibu_planlagt`/`ibu_faktisk_prosess` instead round **each hop
addition** to 1 decimal first (`_ibu_for_tid`'s `round(..., 1)`) and
*then* sum and round the total again. These are not algebraically
equivalent operations. Minimal, self-contained proof (plain decimal
arithmetic, no code execution needed): three hop additions with raw
contributions `0.26 + 0.26 + 0.26`. Summed first: `round(0.78, 1) =
0.8`. Rounded individually first: `round(0.26, 1) = 0.3` for each,
summed: `0.9`. A 0.1 IBU (at this precision) or, after `fmt_ibu`'s
whole-number rounding, up to a full integer-point disagreement is
therefore mathematically possible for realistic multi-addition
recipes (3-6 hop additions is a normal recipe shape in this app's own
demo/fixture data), and grows with hop-addition count. This directly
contradicts the module's own inline comment at
`brewday_calc.py:128-129`, which asserts `ibu_bidrag` is *"samme tall
som modules/calculations.py::beregn_total_ibu() uten
koketid-grense"* ("the same number as `beregn_total_ibu()` without the
boil-time cap") — that comment overclaims exact equivalence; it is
only true modulo this rounding-order gap.
- **Severity/trust impact**: Medium. This is precisely the kind of
  "same recipe, two different IBU numbers on two different screens"
  scenario this audit exists to find — reachable with ordinary input
  (no edge case, no bad data entry required), and both numbers are
  shown to the brewer as if they were the same "IBU" concept applied
  to planned vs. process-constrained hop timing, not flagged as
  independently-computed.
- **Justified or should delegate?** `ibu_faktisk_prosess`'s *concept*
  (capping a hop's effective utilization time at the process's actual
  boil length) is legitimate domain logic with no Core equivalent —
  that part is justified, process-specific, and already well
  documented (lines 121-139). The *arithmetic engine underneath it*
  (bigness/utilization/mg-per-liter Tinseth math and alpha resolution)
  should delegate to `modules/calculations.py`'s primitives instead of
  re-deriving them, and the summation should use a single
  round-once-at-the-end policy consistent with `ctx["ibu"]`.

## 3. Contradiction/risk classification

| # | Location | Class | Currently reachable? | Severity |
|---|---|---|---|---|
| 1 | `ui/recipe_card.py:80` | Duplicate formula, missing Core validation | Yes (bad manual input) | Low-medium |
| 2 | `ui/brewday_panel.py:344` | Duplicate formula, missing Core validation | Yes (bad manual input) | Low-medium |
| 3a | `modules/brewday_calc.py:112` | Duplicate formula, regressed fixed bug | No (no `alfa=0.0` in live data) | Low (latent) |
| 3b | `modules/brewday_calc.py` `ibu_planlagt`/`ibu_faktisk_prosess` | Duplicate formula, rounding-order divergence | Yes (ordinary multi-hop recipes) | Medium |

No contradiction was found for OG, EBC, planned FG/ABV, or BU:GU — all
confirmed to flow exclusively through `ctx` with no parallel
implementation anywhere in `app.py`, `ui/**`, or `modules/**` (verified
by grepping every constant unique to `beregn_og`/`beregn_ebc`/
`beregn_fg_og_abv` — `131.25`, `8.3454`, `1.4922`, `0.6859`, `2.2046`,
`0.2641` — across `app.py`, `ui/`, `modules/`, and confirming every hit
outside `modules/calculations.py` is one of the four findings above,
the intentionally-separate efficiency/post-boil-OG calculations in
section 1, or the already-correct `kbhbrew_history_ui.py`).

## 4. Authoritative-path recommendation

| Calculation | Recommended authoritative call |
|---|---|
| Measured-OG+FG ABV (brew log "actual_abv") | `modules.calculations.beregn_abv_standard(actual_og, actual_fg)` (or `beregn_abv_fra_og_fg` if the high-gravity estimate should also be stored/shown), inside a `try/except ValueError` mirroring `kbhbrew_history_ui.py:150-158` |
| Measured-OG+FG ABV (brewday sheet "Beregnet ABV") | Same as above, same `try/except` pattern in place of the current `if og_f > 1.001 and fg_f > 1.000:` guard |
| Planned per-hop/total IBU inside `lag_brewday_plan()` | `modules.calculations.beregn_total_ibu()` / its `_hent_alfa()` alpha resolution for the raw per-addition contribution; keep the existing `tid_over_koketid`/`ibu_bidrag_faktisk` boil-time-cap logic as the only local addition, summed once at the end rather than per-addition-rounded-then-summed |

## 5. Exact implementation touchpoints

- `ui/recipe_card.py` — the `"actual_abv": round(...)` line inside
  `_render_brewday_result_panel`'s form-submit handler (~line 80), plus
  its `import` block (add `from modules.calculations import
  beregn_abv_standard` or `beregn_abv_fra_og_fg`).
- `ui/brewday_panel.py` — the `st.metric("Beregnet ABV", ...)` block in
  Step 5 (~lines 339-346), plus its `import` block.
- `modules/brewday_calc.py` — `_bygg_humle_entry()`'s `alfa` resolution
  (line 112) and `_ibu_for_tid()` (lines 115-119); the module-level
  `bigness` computation (line 271); the `ibu_planlagt`/
  `ibu_faktisk_prosess` aggregation (lines 284-285). Needs either an
  import of `modules.calculations` primitives or an equivalent
  refactor that keeps `_hent_alfa()`'s None-aware fallback and
  `beregn_total_ibu()`'s raw-sum-then-round-once semantics while
  preserving the boil-time-cap feature this module legitimately owns.
- No changes needed in `app.py`, `modules/recipe_context.py`,
  `modules/style_engine.py`, `modules/kbhbrew_history_ui.py`,
  `modules/kbhbrew.py`, or any EBC/OG/planned-FG/ABV path — all
  already confirmed authoritative-only.

## 6. Bounded acceptance matrix

| Scenario | Expected post-fix behavior |
|---|---|
| Brew log form: `actual_fg <= actual_og`, both valid SG | `actual_abv` numerically unchanged from today (same formula, now via `beregn_abv_standard`) |
| Brew log form: `actual_fg > actual_og` | No `actual_abv` stored / a visible error, instead of a silent negative percentage |
| Brewday sheet: valid `bd_og`/`bd_fg` with `fg <= og` | "Beregnet ABV" metric numerically unchanged from today |
| Brewday sheet: `bd_fg > bd_og` | No "Beregnet ABV" metric shown / a visible error, instead of a silent negative percentage |
| Recipe with hop `alfa` explicitly `0.0` (if ever added to master data) | `ibu_planlagt`/`ibu_faktisk_prosess` treat that hop as contributing `0` IBU, matching `beregn_total_ibu()`, not silently falling back to `alfa_typisk`/`5.0` |
| Any recipe, `ctx["ibu"]` vs. `ibu_planlagt` for the *unconstrained* (no boil-time cap triggered) case | The two must agree to `fmt_ibu`'s whole-number rounding for every recipe in `demo_recipes/` and every existing brewday-plan test fixture — this is the acceptance bar for closing Finding 3b, not exact float equality (display-precision equality is what users actually compare) |
| Existing `humle_over_koketid`/`ibu_bidrag_faktisk` boil-time-cap behavior (`tests/test_brewday_export_hop_mismatch.py`) | Unchanged — this feature is confirmed legitimate and out of scope for removal |

## 7. Focused unit/AppTest plan

- `tests/test_calculations_gravity.py` / `test_ebc_calculation.py` /
  `test_calculation_golden_vectors.py` / `test_calculations_ibu_alfa.py`
  — already exist, already pass today (not run in this docs-only
  round per the issue's own instruction to keep this analysis-only),
  and should be re-run unmodified as regression proof once an
  implementation round touches `modules/calculations.py` callers.
- New: a `brewday_calc` test asserting `ibu_planlagt` (no boil-time
  cap triggered) matches `beregn_total_ibu()`'s output for the same
  malt/hop/og/volum input, to the same rounding precision — this is
  the regression guard for Finding 3b and would have caught it.
- New: a `brewday_calc` test mirroring
  `test_calculations_ibu_alfa.py`'s Case A (`alfa=0.0` explicit) but
  driven through `lag_brewday_plan()`, to close Finding 3a and prevent
  the fixed-bug pattern from being reintroduced a third time.
- New: `ui/recipe_card.py` and `ui/brewday_panel.py` AppTest cases
  (pattern: `tests/test_kbhbrew_history_panel_apptest.py`,
  `tests/_brewday_panel_app.py` fixture) for the `fg > og` input case,
  asserting no ABV value / a visible error is shown, not a negative
  percentage.
- `tests/test_brewday_export_hop_mismatch.py` — re-run unmodified as
  proof the boil-time-cap feature (the legitimate part of Finding 3)
  is untouched by any fix to the arithmetic engine underneath it.

## 8. Recommended implementation split/order

Suggested as two independently mergeable, small PRs — not a
recommendation to implement either in this round:

1. **ABV delegation** (Findings 1+2): mechanical, low-risk — replace
   two inline formulas with the existing, already-proven
   `beregn_abv_standard()`/`beregn_abv_fra_og_fg()` call plus
   `try/except ValueError`, following the exact pattern already live
   in `kbhbrew_history_ui.py`. No new Core function needed. Smallest
   safe unit: `ui/recipe_card.py` and `ui/brewday_panel.py` can each
   be its own commit/PR if preferred, since they're independent call
   sites with no shared state.
2. **IBU engine consolidation** (Finding 3): needs more care —
   `_bygg_humle_entry()`'s boil-time-cap logic is real, tested,
   exported-HTML-dependent domain logic
   (`tests/test_brewday_export_hop_mismatch.py`) that must be
   preserved exactly; only the underlying per-hop IBU arithmetic and
   alpha-resolution should be swapped for Core's primitives, and the
   final aggregation should move from
   round-per-addition-then-sum-then-round to sum-raw-then-round-once
   to match `ctx["ibu"]`'s semantics. Recommended to land after (1),
   since it touches more call sites and interacts with existing
   process-profile tests.

## 9. Explicit non-goals

- No App/Core/Web product behavior is changed by this document itself
  (analysis/preflight only, per the issue's scope guard).
- Does not implement A1 or A2 — recommendations only.
- Does not touch `app.py`, `ui/**`, `modules/**`, Core
  contracts/schemas, Web, Bryggeskole/Sóti, deploy state, B06/B07/
  B08/B10/B11, #98/#100, or owner data.
- Does not re-litigate `CORE_CALCULATION_CONTRACT.md`'s existing,
  owner-approved decisions (CALC-001 alpha-fallback-is-out-of-scope,
  CALC-002 half-up rounding) — those govern the Python/JS parity
  contract for the seven Core calculations themselves, not the
  App-internal duplication this document addresses. Finding 3a is
  about `brewday_calc.py` diverging from `_hent_alfa()`'s *already
  App-internal* fallback policy, not about reopening CALC-001.
- Does not propose changing `fmt_ibu`'s whole-number display rounding
  or any other `export_format.py` presentation choice — those are
  unaffected; the finding is about which raw number reaches them.
- Does not assert whether `beregn_effektivitet()`/
  `beregn_post_boil_og()` are the "right" formulas in a brewing-science
  sense (out of scope) — only that they are correctly, distinctly
  labeled and not silently presented as the same value as their
  forward-calculation counterparts.
