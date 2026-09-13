# Issue #256 -- minimal AppTest-harness for ui/recipe_card.py::
# _render_brewday_result_panel() alene (samme "ett funksjon, syntetisk
# ctx"-prinsipp som tests/fixtures/streamlit_harness/
# kbhbrew_create_harness.py), for å teste dual-truth-vakten mot den
# gamle, per-oppskrift Bryggeloggen når den lastede oppskriften allerede
# har >=1 lagret .kbhbrew-brygg (Phase 3B durable decision #253).
#
# KVERNHAUG_TEST_RECIPE_CARD_HAS_KBHBREW (satt til hva som helst
# ikke-tomt) seeder ETT lokalt .kbhbrew-brygg med `recipeId` satt til
# NØYAKTIG samme identitet som `_last_loaded_recipe_file` under -- FØR
# panelet rendres -- for å dekke "finnes >=1 .kbhbrew"-grenen. Usatt
# (default) dekker den uendrede "ingen .kbhbrew"-grenen.
import os

import streamlit as st

from modules.kbhbrew_storage import hent_brew, opprett_og_lagre_ny_brew
from modules.recipe import bygg_recipe_object
from ui.recipe_card import _render_brewday_result_panel

_RECIPE_NAVN = "Harness Pilsner"
_RECIPE_FIL = "harness_pilsner.json"

_MALT_DB = {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037}}
_HUMLE_DB = {}
_GJAER_DB = {"safale_us_05": {"display_name": "SafAle US-05", "attenuation": 0.75}}
_EQUIPMENT = {
    "efficiency": 0.75, "boil_off_l_per_hour": 4.0, "grain_absorption_l_per_kg": 1.0,
    "dead_space_l": 2.0, "mash_ratio_l_per_kg": 3.2, "kettle_capacity_l": 35.0,
    "default_boil_time_min": 60,
}

_recipe = bygg_recipe_object(
    _RECIPE_NAVN, 20.0, 0.75,
    [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
    "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
)

if os.environ.get("KVERNHAUG_TEST_RECIPE_CARD_HAS_KBHBREW") and hent_brew("brew-256-seed") is None:
    opprett_og_lagre_ny_brew(
        _recipe, _MALT_DB, _HUMLE_DB, _GJAER_DB, _EQUIPMENT,
        {"og": 1.050, "fg": 1.012, "abv": 5.0},
        recipe_id=_RECIPE_FIL, brew_id="brew-256-seed",
    )

st.session_state["_last_loaded_recipe"] = _RECIPE_NAVN
st.session_state["_last_loaded_recipe_file"] = _RECIPE_FIL

ctx = {"name": _RECIPE_NAVN, "volum": 20.0, "og": 1.050, "fg": 1.012}

_render_brewday_result_panel(ctx)
