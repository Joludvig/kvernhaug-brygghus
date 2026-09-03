# PRI 3B2 -- minimal AppTest-harness for ui/kbhbrew_panel.py::
# render_kbhbrew_create_panel() alene, uten resten av Bryggdag-fanen
# (ui/brewday_panel.py sine egne meske-/koke-/gjæringswidgets/plan-
# bygging er IKKE del av dette) -- kun nok ctx/malt/humle/gjaer-input
# til å teste selve "Start nytt brygg"-handlingen isolert (se
# tests/test_kbhbrew_create_panel_apptest.py).
#
# KVERNHAUG_TEST_KBHBREW_INVALID (satt til hva som helst ikke-tomt)
# bygger en recipe med efficiency=0 -- ugyldig for
# modules/kbh_contract.py::recipe_to_kbhrecipe_payload() -- for å teste
# feilstien uten å måtte konstruere en full ugyldig malt-/humle-liste.
#
# KVERNHAUG_TEST_KBHBREW_MISSING_MALT (satt til hva som helst ikke-tomt)
# fjerner "weyermann_pilsner" fra den oppgitte malt-databasen -- for å
# teste opprettelses-preflighten (Chief review, PR #30 blocker 3) uten
# en egen full oppskrift.
#
# KVERNHAUG_EQUIPMENT_FILE styrer selve testisolasjonen for
# modules/equipment.py (se _equipment_file() der) -- satt av
# tests/test_kbhbrew_create_panel_apptest.py sin setUp() til enten en
# gyldig midlertidig fil (happy path) eller en ikke-eksisterende/korrupt
# sti (equipment-preflight-testene), ALDRI den ekte data/equipment.json.
import os

import streamlit as st

from modules.recipe import bygg_recipe_object
from ui.kbhbrew_panel import render_kbhbrew_create_panel

_MALT_DB = {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037}}
if os.environ.get("KVERNHAUG_TEST_KBHBREW_MISSING_MALT"):
    _MALT_DB = {}
_HUMLE_DB = {}
_GJAER_DB = {"safale_us_05": {"display_name": "SafAle US-05", "attenuation": 0.75}}

_efficiency = 0.0 if os.environ.get("KVERNHAUG_TEST_KBHBREW_INVALID") else 0.75

recipe = bygg_recipe_object(
    "Harness Pilsner", 20.0, _efficiency,
    [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
    "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {"Bitterhet": 4},
)

ctx = {
    "name": "Harness Pilsner", "volum": 20.0, "og": 1.050, "fg": 1.012, "abv": 5.0,
    "ibu": 20, "ebc": 8, "effektivitet": 0.75,
    "style_analysis": {
        "stil": "Tysk Pilsner",
        "stil_liste": [{"stil": "Tysk Pilsner", "score": 80}],
        "bu_gu": 0.5,
    },
    "recipe": recipe,
}

render_kbhbrew_create_panel(ctx, _MALT_DB, _HUMLE_DB, _GJAER_DB)
