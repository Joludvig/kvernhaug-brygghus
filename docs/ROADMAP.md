# Kvernhaug Brygghus — Roadmap

## Current status

The app is a functional single-user recipe platform for home brewing.

**What works today:**
- Recipe builder with live OG / IBU / EBC / ABV calculations
- Editable malt percentages (redistributes proportionally)
- Editable batch volume and brew name
- Fritekst recipe importer (kg, g, %, with name and batch detection)
- Style engine — 22 BJCP styles, 6 recipe signatures (hazy, belgian, stout, west coast, english ale, dark malt)
- Sensory flavor wheel and balance analysis
- Save / load recipes (sidebar)
- Shopping list V1 — prices and product links per store
- Brewday Plan V1.1 — water volumes, mash schedule, hop schedule, yeast recommendations
- Printable recipe sheet (compact A4, white background)
- Printable brewday sheet (two-column A4 with checkboxes and write-in fields)
- Supplier panel (price sync / product link check)
- AI scraper + normalizer pipeline (Vestbrygg + Ølbrygging.no)

---

## V1.1.x — Polish and real brewday testing

**Goal:** Validate the app through real-world brewing before adding new features.

- End-to-end test of Sommerglød (or similar) brew workflow
- Fix any UI / print / import bugs discovered during real use
- Polish shopping list (price accuracy, missing links)
- Polish brewday sheet (layout, readability during actual brewing)
- Avoid large architecture changes
- Stabilize before V1.2 work begins

---

## V1.2 — Inventory / Pantry System

**Goal:** Track what ingredients the user already has at home.

**Features:**
- Malt inventory in kg (per entry)
- Hop inventory in grams (per entry)
- Yeast inventory in packs (per entry)
- Compare current recipe against inventory
- Show what is already available ("you have 80% of this recipe")
- Show what must be purchased ("missing: Rauchmalz")
- Shopping list aware of inventory (only lists what is missing)

---

## V1.3 — Store Comparison

**Goal:** Side-by-side price comparison across supported stores.

**Features:**
- Vestbrygg total cost for current recipe
- Ølbrygging.no total cost for current recipe
- Highlight cheapest option
- Flag missing product links per store
- Future: stock warning if a product is unavailable at selected store

---

## V1.4 — Equipment Profile

**Goal:** Replace hardcoded BrewZilla 35L defaults with user-editable equipment settings.

**Fields:**
- Kettle volume (L)
- Boiloff rate (L/hour)
- Mash ratio (L/kg)
- Dead volume / trub loss (L)
- Grain absorption (L/kg)
- Preferred boil time (min)
- Default mash temperature (°C)

**Scope:** Single profile to start. Profile persists between sessions.

---

## V1.5 — Brew Log

**Goal:** Record actual brew results against the planned recipe.

**Fields:**
- Brew date
- Measured OG
- Measured FG (calculated ABV)
- Fermentation temperature (actual)
- Fermentation notes
- Tasting notes
- Improvements for next batch

**Scope:** Linked to saved recipe. Log entries stored alongside recipe JSON.

---

## V2.0 — Multi-User / First-Run Setup

**Goal:** Prepare the app for sharing with other brewers.

**Features:**
- First-run store selection (choose Vestbrygg / Ølbrygging / future stores)
- App catalog filtered to products available at selected stores
- Separation of product catalog from store inventory (see data architecture notes)
- Optional: producer-data enrichment layer for EBC / potensiale / flavor data
- Optional: shared recipe library

---

## Data Architecture Direction

Current state: store prices and URLs are embedded inside master product databases.

Long-term direction (when a third store is added or multi-user is needed):

```
LAYER 1 — Product Catalog     catalog/malt.json etc.
          Sensory, style, canonical IDs, aliases
          Source: manual curation + producer data

LAYER 2 — Store Inventory     stores/vestbrygg.json etc.
          Price, URL, pakke_gram, in_stock
          Source: scraper, per store

LAYER 3 — App View            data/malt.json etc.
          Join of catalog + store data for selected stores
          Only includes products with at least one active store match
```

Trigger for this refactor: adding a third store.

---

## Guiding Principles

- **Do not overbuild.** Each feature should come from a real brewing need.
- **Keep the app stable.** New features are additive, not replacements.
- **Small commits.** One logical change per commit.
- **Real use drives priorities.** V1.1.x polish comes from actual brewday testing, not assumptions.
- **Master DB = product knowledge.** EBC, flavor, style. Stable.
- **Store data = commercial availability.** Price, URL, stock. Volatile.
- **Producer data = enrichment.** Authoritative for technical specs. Does not replace curation.
