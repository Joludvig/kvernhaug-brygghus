"""Minimal vertskap-app for AppTest-baserte tester av
ui/brewday_panel.py sin normalisering av prosessprofilen rett før
lag_brewday_plan(). Ikke en del av selve applikasjonen, og plukkes ikke
opp av `unittest discover` (matcher ikke test*.py).

Den innledende, potensielt korrupte session_state["aktiv_prosessprofil"]
seedes via miljøvariabelen KVERNHAUG_TEST_AKTIV_PROSESSPROFIL (JSON),
slik at testen kan gjenskape EKSAKT den rapporterte kombinasjonen: en
korrupt profil i session_state samtidig som ctx allerede har den
korrekte, kanoniske profilen."""
import json
import os
import streamlit as st

from ui.brewday_panel import render_brewday_panel
from modules.recipe import bygg_recipe_object
from modules.process_profiles import hent_standardprofil

if "aktiv_prosessprofil" not in st.session_state:
    _seed = os.environ.get("KVERNHAUG_TEST_AKTIV_PROSESSPROFIL")
    st.session_state["aktiv_prosessprofil"] = json.loads(_seed) if _seed else None

st.session_state.setdefault("valgt_malt", [{"id": "weyermann_pilsner", "mengde": 5.0}])
st.session_state.setdefault("valgt_humle", [])
st.session_state.setdefault("valgt_gjaer_id", "safale_us_05")
st.session_state.setdefault("bd_tilsetninger", [])

ctx = {
    "name": "Test", "volum": 20.0, "og": 1.050, "fg": 1.012, "abv": 5.0,
    "ibu": 20, "ebc": 8, "effektivitet": 0.75,
    "recipe": bygg_recipe_object(
        "Test", 20.0, 0.75, st.session_state["valgt_malt"], [],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        # Speiler den rapporterte 3b-verdien: ctx har FRA FØR den
        # korrekte, kanoniske Hochkurz-profilen.
        process_profile=hent_standardprofil("hochkurz"),
    ),
}
gjaer_db = {"safale_us_05": {"display_name": "US-05", "gjaertype": "Ale", "attenuation": 0.75}}

render_brewday_panel(ctx, {}, gjaer_db, {})

# Test-fixturens EGEN snapshot (ikke produksjonskode) av hele ctx etter at
# ui/brewday_panel.py sin normalisering har skrevet tilbake til den.
st.session_state["_test_ctx_snapshot"] = ctx
st.session_state["_test_ctx_process_profile_etter_panel"] = ctx["recipe"]["process_profile"]
