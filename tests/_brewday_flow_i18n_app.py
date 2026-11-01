"""Minimal vertskap-app for AppTest av hele ui/brewday_panel.py (#548): et
rikt scenario med humletidsavvik, tilsetninger, lagergjær og en valgfri
prosessprofil, slik at dynamiske varsler/anbefalinger faktisk rendres.
Ikke en del av applikasjonen, og plukkes ikke opp av `unittest discover`
(matcher ikke test*.py). Alt seedes via session_state fra testen."""
import json
import os
import streamlit as st

from ui.brewday_panel import render_brewday_panel
from modules.recipe import bygg_recipe_object

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "data", "master_gjaer_v2.json"), encoding="utf-8") as _f:
    gjaer_db = json.load(_f)

humle_db = {"magnum": {"display_name": "Magnum", "alfa": 12.0}}
malt_db = {"vienna": {"display_name": "Vienna Malt", "potensiale": 1.036}}

st.session_state.setdefault("aktiv_prosessprofil", None)
st.session_state.setdefault("valgt_malt", [{"id": "vienna", "mengde": 25.0}])
st.session_state.setdefault("valgt_humle", [{"id": "magnum", "gram": 20, "tid": 90}])
st.session_state.setdefault("valgt_gjaer_id", "saflager_w3470")
st.session_state.setdefault("bd_tilsetninger", ["whirlfloc", "fermaid_o"])

ctx = {
    "name": "Sommerglød", "volum": 30.0, "og": 1.050, "fg": 1.012, "abv": 5.0,
    "ibu": 20, "ebc": 8, "effektivitet": 0.75, "brygger_stil": "Sommerstil",
    "recipe": bygg_recipe_object(
        "Sommerglød", 30.0, 0.75, st.session_state["valgt_malt"], [],
        st.session_state["valgt_gjaer_id"], 1.050, 1.012, 5.0, 20, 8, {},
        fermentation_temp_target_c=st.session_state.get("gjaering_temp_maal_c"),
    ),
}
render_brewday_panel(ctx, humle_db, gjaer_db, malt_db)
