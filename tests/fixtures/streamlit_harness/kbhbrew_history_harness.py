# V2-1A (issue #83) -- minimal AppTest-harness for
# ui/kbhbrew_history_panel.py::render_kbhbrew_history_panel() alene, uten
# resten av Bryggdag-fanen (samme prinsipp som
# tests/fixtures/streamlit_harness/kbhbrew_create_harness.py).
#
# KVERNHAUG_TEST_KBHBREW_SEED_COUNT (default "1") styrer hvor mange
# forhåndslagrede Core V1-brygg som seedes FØR panelet rendres, via
# modules/kbhbrew_storage.py::opprett_og_lagre_ny_brew() direkte (IKKE
# via UI-klikk -- render_kbhbrew_create_panel() er ikke del av dette
# harnesset). Seedingen sjekker først hent_brew() for å unngå å
# opprette et NYTT duplikat-brygg ved hver AppTest-rerun (knappeklikk
# kjører HELE dette skriptet på nytt) -- samme "aldri dobbel-seed"-
# forsiktighet som andre AppTest-harnesser i dette prosjektet.
import os

import streamlit as st

from modules.kbhbrew_storage import hent_brew, opprett_og_lagre_ny_brew
from modules.recipe import bygg_recipe_object
from ui.kbhbrew_history_panel import render_kbhbrew_history_panel

_MALT_DB = {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037}}
_HUMLE_DB = {}
_GJAER_DB = {"safale_us_05": {"display_name": "SafAle US-05", "attenuation": 0.75}}
_EQUIPMENT = {
    "efficiency": 0.75, "boil_off_l_per_hour": 4.0, "grain_absorption_l_per_kg": 1.0,
    "dead_space_l": 2.0, "mash_ratio_l_per_kg": 3.2, "kettle_capacity_l": 35.0,
    "default_boil_time_min": 60,
}

_SEED_DEFS = [
    ("brew-seed-0001", "Harness Pilsner", {"og": 1.052, "fg": 1.012, "abv": 5.2}),
    ("brew-seed-0002", "Harness IPA", {"og": 1.060, "fg": 1.014, "abv": 6.0}),
]


def _recipe(navn):
    return bygg_recipe_object(
        navn, 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
        "safale_us_05", 1.052, 1.012, 5.2, 20, 8, {},
    )


_seed_count = int(os.environ.get("KVERNHAUG_TEST_KBHBREW_SEED_COUNT", "1"))
for brew_id, navn, predicted in _SEED_DEFS[:_seed_count]:
    if hent_brew(brew_id) is None:
        opprett_og_lagre_ny_brew(
            _recipe(navn), _MALT_DB, _HUMLE_DB, _GJAER_DB, _EQUIPMENT, predicted, brew_id=brew_id,
        )

render_kbhbrew_history_panel()
