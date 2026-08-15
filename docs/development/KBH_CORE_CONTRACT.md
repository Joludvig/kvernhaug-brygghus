# KBH Core Contract

Version: 1.0
Status: Active

This is not a locked text. It is a versioned document. Changes to this
contract require explicit review and a version increment.

---

## Background

Kvernhaug Brygghus consists of two independent workspaces sharing one
language: the exchange files.

**Streamlit (desktop)**
- owns planning
- owns advanced recipe design
- owns master data
- owns water chemistry
- owns process profiles
- owns calculation and optimization

**Web (mobile)**
- owns brew day
- owns execution
- owns the brew log
- owns experience and the learning loop

**File formats**
- own the data interchange
- are independent of either implementation
- are meant to outlive both systems' current code

> One brewhouse. Two work surfaces. One language — and the language is
> the files, not the code.

---

## Section 1 — Core philosophy

**1. Store what cannot be regenerated.**

Examples: actual measurements, the brewer's reflections, frozen
calculation inputs, historical snapshots.

**2. Never store what can be recalculated.**

Examples: live ABV, deviations, converted units, flavor derived from
today's engine.

**3. Ownership.**

- Streamlit: owns the plan and the design.
- Web: owns the execution and the experience.
- Files: own the language.

---

## Section 2 — KBH data ownership

No single application owns the file format.

Applications may read, write, display, and interpret a KBH file. The
file contract stands above the code that happens to implement it today.

**KBH files must be movable between systems without their identity or
meaning changing.**

---

## Section 3 — `.kbhrecipe` V1 contract

**Wrapper**

```
{
  format,
  version,
  exportedAt,
  generator,
  recipe
}
```

**Payload — required fields**

```
recipeSchemaVersion: 1

navn
volum
effektivitet
malt[]
humle[]
```

**Payload — optional fields**

```
brygger
bryggeri
notater

gjaerId
gjaerCustom
attenuationOverride

valgtStil
bryggerStil

prosess

vann:
  kilde
  maal
  behandling
  maalinger
```

Streamlit's internal snake_case fields are translated into this shape
at export time. The web format is canonical for interchange — it is
the shape both systems agree to speak, regardless of which system
produced the file.

---

## Section 4 — The whitelist rule

Export is always built field by field.

**Never:**
- copy the whole source object
- delete known fields off a copy
- forward unknown internal data by accident

**The following must never appear in a `.kbhrecipe`:**
- `stats`
- `flavor_profile`
- any value computed by the engine

A recipe describes the plan. A brew snapshot describes the history.
Only the snapshot format is allowed to carry computed results.

---

## Section 5 — Units and normalization

All KBH files always use:

```
Liter
Kilogram
Gram
Minutter
Celsius
Metric standard values
```

Display units — US units, locale preference, UI formatting — must
never be stored in a file.

**Effektivitet**

```
Streamlit internal:  0.75
KBH file format:     75
```

The factor-100 conversion happens only in the adapter layer, never in
storage and never in the UI layer directly.

---

## Section 6 — Identity policy

Two distinct identifiers exist and must not be conflated:

- **Local identity** — `recipeId`
- **Historical link** — `originRecipeId`

**Rule:** a shareable `.kbhrecipe` must never contain the receiving
system's local `recipeId`.

**At export:**

Streamlit may hold an internal `recipe_id`. If it is missing:

- a `uuid4` is generated
- it is written atomically back to that one recipe file only
- this happens only on an explicit, user-triggered export
- it never happens as a background migration

**Goal:** the same recipe exports with the same identity every time.

---

## Section 7 — `originRecipeId`

`originRecipeId` is a historical hint, carried in the exported file.

**Used for:**
- linking a recipe to a later brew
- tracing experience back to the correct recipe
- preserving identity across file movement between systems

**Never used as:**
- a local database ID
- a forced import ID
- a substitute for explicit user confirmation

---

## Section 8 — The passthrough law

An application must preserve data it does not understand through the
full cycle:

```
read → change → save
```

Web does not need to understand water chemistry. But web must never
delete water chemistry.

Streamlit does not need to understand future web-only fields. But
Streamlit must preserve them.

Unknown data must be:
- kept
- left uninterpreted
- never silently overwritten

---

## Section 9 — No smart guessing

KBH files are structured data. The system must never:

- fuzzy-match ingredients automatically
- guess a style
- substitute an unknown ID with a similar one
- fall back to default data while presenting the result as correct

**If data cannot be understood:**
- show a clear error
- mark it as unresolved
- require an explicit user decision

---

## Section 10 — Relationship to `.kbhbrew`

- `.kbhrecipe` — the plan.
- `.kbhbrew` — the history.

The recipe holds what we intend to make. The brew holds what actually
happened: measurements, sensory notes, experience.

Computed historical values are frozen into the `.kbhbrew` snapshot at
brew time. They are never frozen into the recipe.

---

## Section 11 — Future extensions

New areas of the contract must be additive.

Examples: fermentation profile, temperature history, advanced water
analysis, a combined backup format.

New features must never break existing files.
