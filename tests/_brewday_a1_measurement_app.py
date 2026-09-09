# App A1 (issue #170) -- minimal vertskap-app for AppTest-baserte tester
# av ui/brewday_panel.py::render_brewday_panel() sin Steg 4/5-
# målingsbinding til DET AKTIVE `.kbhbrew`-brygget
# (ui/kbhbrew_panel.py::aktiv_brew_id()/_sinkroniser_aktiv_brew_mot_
# oppskrift()) -- speiler tests/_brewday_panel_app.py sitt "minimal
# vertskap"-prinsipp, men inkluderer i tillegg "Start nytt brygg"/
# Brygghistorikk-panelene (render_kbhbrew_create_panel() krever en
# GYLDIG, bekreftet utstyrsprofil -- se
# tests/test_kbhbrew_create_panel_apptest.py) og lar testen styre
# gjeldende oppskrifts-identitet (`_last_loaded_recipe_file`) direkte
# via miljøvariabelen KVERNHAUG_TEST_RECIPE_ID -- UTEN den ekte
# sidebaren -- for å kunne simulere et oppskriftsbytte mellom to
# `at.run()`-kall (se tests/test_brewday_a1_measurement_apptest.py).
import os

import streamlit as st

from modules.recipe import bygg_recipe_object

st.session_state.setdefault("valgt_malt", [{"id": "weyermann_pilsner", "mengde": 5.0}])
st.session_state.setdefault("valgt_humle", [])
st.session_state.setdefault("valgt_gjaer_id", "safale_us_05")
st.session_state.setdefault("bd_tilsetninger", [])

# Speiler ui/sidebar.py sin egen "ingen oppskrift valgt" -> pop()-
# oppførsel når miljøvariabelen ikke er satt, i stedet for å la en
# tidligere kjørings identitet bli hengende.
_recipe_id = os.environ.get("KVERNHAUG_TEST_RECIPE_ID")
if _recipe_id:
    st.session_state["_last_loaded_recipe_file"] = _recipe_id
else:
    st.session_state.pop("_last_loaded_recipe_file", None)

_navn = os.environ.get("KVERNHAUG_TEST_RECIPE_NAVN", "A1 Harness Pilsner")

ctx = {
    "name": _navn, "volum": 20.0, "og": 1.050, "fg": 1.012, "abv": 5.0,
    "ibu": 20, "ebc": 8, "effektivitet": 0.75,
    "style_analysis": {"stil_liste": []},
    "recipe": bygg_recipe_object(
        _navn, 20.0, 0.75, st.session_state["valgt_malt"], [],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
    ),
}
malt_db = {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037}}
gjaer_db = {"safale_us_05": {"display_name": "US-05", "gjaertype": "Ale", "attenuation": 0.75}}

from ui.brewday_panel import render_brewday_panel  # noqa: E402 -- etter session_state-seed over

render_brewday_panel(ctx, {}, gjaer_db, malt_db)
