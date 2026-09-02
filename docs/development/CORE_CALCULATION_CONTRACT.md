# Core Calculation Contract

Version: 1.0
Status: Active
Governed by: [KBH_CORE_CONTRACT.md](KBH_CORE_CONTRACT.md) (v2.0) — this
document names six calculations as Core-owned shared semantic
contracts, under the existing "shared semantic contracts" grant in
Section 1. It does not redefine domain ownership.

This is not a locked text. It is a versioned document. Changes require
explicit review and a version increment.

---

## Purpose

Documents which calculations are now proven, Core-owned shared
semantics between the Python (`modules/calculations.py`) and
JavaScript (`web/js/calc.js`) implementations, and where the
normative compatibility baseline for that proof lives. Does not
document the underlying brewing math itself — see the docstrings in
`modules/calculations.py` (source-of-truth comments, constants,
citations) for that; this document is intentionally short.

## The six calculations

1. **OG** (Original Gravity) — `beregn_og()` / `beregnOG()`
2. **FG** (Final Gravity) and **ABV** — `beregn_fg_og_abv()` /
   `beregnFgOgAbv()` (one shared function, two outputs — see
   `core/calculation_golden_vectors.json`'s `fg_abv` calculation type)
3. **EBC / Morey** (beer color) — `beregn_ebc()` / `beregnEBC()`
4. **Tinseth IBU** — `beregn_total_ibu()` / `beregnTotalIBU()`
5. **Inverse Tinseth IBU** — `beregn_gram_fra_ibu()` /
   `beregnGramFraIBU()`

`web/js/calc.js` is a direct, deliberate line-for-line port of
`modules/calculations.py` (see that file's own header comment). This
document does not change that relationship — it adds proof that the
port is still faithful today, and a fixed baseline to catch future
drift.

## Canonical inputs/units

See `canonical_units` in
[`core/calculation_golden_vectors.json`](../../core/calculation_golden_vectors.json)
for the authoritative, machine-readable field/unit list (grain
kilograms, hop grams, specific gravity, EBC, liters, 0-1 fractions for
efficiency/attenuation, percent for alpha acid, minutes for boil time).
Not duplicated here to avoid two sources of truth.

## Tolerance principle

Absolute tolerance, sized per calculation type to the smallest value
robust across Python and JavaScript double-precision floating point —
not a large tolerance chosen to hide a real deviation. Full reasoning
and the exact values used are documented in the golden vectors file's
own `tolerance_principle` field (`og`/`fg_abv`: 1e-9, no transcendental
functions involved; `ebc_morey`/`tinseth_ibu`: 1e-6, involves a
fractional-exponent power and/or `exp`; `inverse_tinseth`: 1e-9,
compared against the production functions' own contractual 1-decimal
rounded output — now that both implementations round that output with
the same decimal half-up rule, CALC-002 below — a wider tolerance such
as `0.05` is deliberately **not** used here, since it would be wide
enough to let two adjacent, equally-plausible 1-decimal contractual
results both pass the same vector, silently hiding exactly the kind of
rounding-rule divergence CALC-002 exists to catch).

## Golden vectors as the compatibility baseline

`core/calculation_golden_vectors.json` is the single, technology-
independent fixture both runtimes are tested against:

- `tests/test_calculation_golden_vectors.py` runs every vector through
  today's actual `modules/calculations.py` functions.
- `tests/js/test_calculation_golden_vectors.js` runs the *same*
  vectors through today's actual `web/js/calc.js` functions (loaded
  via Node's `vm` module — `web/js/calc.js` itself is unmodified, no
  `module.exports` added to it).

Neither test copies a formula into itself — both reshape canonical
vector inputs/outputs into each runtime's own function signature, then
call the real production function.

A future change to either implementation that is not a deliberate,
reviewed formula change should be caught by these tests failing. A
genuine, authorized formula change should update the golden vectors
(regenerated from the new production code, never hand-typed — see the
golden vectors file's own values, all generated programmatically) as
part of that change, not as a separate, silent edit.

## Core-Chief decisions (PRI 1 QA correction)

### CALC-001 — alpha acid resolution is outside this contract

The Tinseth golden contract (`tinseth_ibu` and `inverse_tinseth` cases
in `core/calculation_golden_vectors.json`) receives an explicit,
already-resolved canonical `alpha_acid_percent` input directly.

**Resolving that value from legacy/masterdata fields — an explicit
`alfa`, a fallback `alfa_typisk`, or a final hardcoded default — is
adapter/input-resolution, not part of the shared Tinseth arithmetic
this PRI 1 contract covers.**

This is why the two implementations resolve it differently today, and
why that difference is a decided, out-of-scope boundary rather than a
bug:

- Python's `beregn_total_ibu()` resolves a missing `alfa` via an
  internal, 3-level fallback (`_hent_alfa()`: explicit `alfa` →
  `alfa_typisk` → `5.0`).
- JS's `beregnTotalIBU()` only does a 2-level fallback
  (`entry.alfa ?? 5.0`) — the `alfa`/`alfa_typisk` resolution is
  instead performed once, at build time, by
  `scripts/generate_web_data.py`, before the JS function ever sees the
  data.

When both functions are given the same, already-resolved explicit
alpha value — the actual shared calculation input under this contract
— they compute identical results. No golden vector exercises the
`alfa_typisk`/default fallback path, and the alpha-fallback code in
either runtime is **not** harmonized by this document or by PRI 1 —
per explicit Core-Chief instruction, that code is left exactly as it
is.

### CALC-002 — inverse Tinseth rounding: escalated production semantic change, decimal half-up (owner GO obtained)

**This is a production semantic change, not test plumbing.** PRI 1's
locked instruction was that existing formulas/semantics must not be
changed unless an existing discrepancy is documented and escalated to
the owner. This entry is that escalation. It was reviewed and
**explicitly approved by the owner (Joludvig) on 2026-09-02**, in
response to Chief review feedback on this PR (PR #1) requesting one of:
(A) document as an escalated deliberate decision and wait for explicit
owner GO, or (B) revert the production change and record the
divergence as an unresolved finding outside PRI 1. The owner chose (A)
and gave explicit GO to keep the change described below.

**Concrete before/after production behavior change:**
`beregn_gram_fra_ibu()`'s contractual final-rounding step previously
used Python's built-in `round(x, 1)`, which rounds ties to even
(banker's rounding). `beregnGramFraIBU()`'s JS
`Math.round(x * 10) / 10` rounds ties up. The two could disagree
whenever a raw (pre-rounding) gram value landed exactly on a `.x5`
boundary at the first decimal.

**Decision: JavaScript's existing `Math.round(x * 10) / 10` — decimal
half-up for non-negative values — is the Core semantics for this
contract.** `modules/calculations.py::beregn_gram_fra_ibu()` was
corrected to match it, via a small, local, dependency-free helper
(`_avrund_gram_half_up()`, `math.floor(x * 10 + 0.5) / 10`) that
operates on the same intermediate `x * 10` float `Math.round` does, so
it agrees with JS bit-for-bit rather than reinterpreting the value
through a decimal string. `web/js/calc.js` was **not** changed — its
existing `Math.round` behavior already was and remains the wanted
semantics. No other function, formula, or file was touched.

`core/calculation_golden_vectors.json`'s
`inverse_tinseth_tie_case_half_up` case is deliberately constructed so
its raw gram value is exactly `10.25` (an exact IEEE754 double
1-decimal tie) — old Python gave `10.2`, JS gave `10.3`; the corrected
Python now also gives `10.3`. Every other `inverse_tinseth` case
remains deliberately verified to sit away from a tie boundary, and all
`inverse_tinseth` cases now use a near-exact tolerance (`1e-9`, not the
previous `0.05`) so a vector can no longer pass against two different,
equally-plausible 1-decimal contractual results.
