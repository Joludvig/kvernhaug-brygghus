"""Minimal vertskap-app for AppTest av ui/brewday_panel.py (gjæringstemperatur,
#546). Ikke en del av applikasjonen, og plukkes ikke opp av `unittest discover`
(matcher ikke test*.py). Språk, gjær og planlagt mål seedes via session_state
fra testen."""
import json
import os
import streamlit as st

from ui.brewday_panel import render_brewday_panel
from modules.recipe import bygg_recipe_object

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "data", "master_gjaer_v2.json"), encoding="utf-8") as _f:
    gjaer_db = json.load(_f)

st.session_state.setdefault("aktiv_prosessprofil", None)
st.session_state.setdefault("valgt_malt", [{"id": "weyermann_pilsner", "mengde": 5.0}])
st.session_state.setdefault("valgt_humle", [])
st.session_state.setdefault("valgt_gjaer_id", "saflager_w3470")
st.session_state.setdefault("bd_tilsetninger", [])

ctx = {
    "name": "Test", "volum": 20.0, "og": 1.050, "fg": 1.012, "abv": 5.0,
    "ibu": 20, "ebc": 8, "effektivitet": 0.75, "brygger_stil": "",
    "recipe": bygg_recipe_object(
        "Test", 20.0, 0.75, st.session_state["valgt_malt"], [],
        st.session_state["valgt_gjaer_id"], 1.050, 1.012, 5.0, 20, 8, {},
        fermentation_temp_target_c=st.session_state.get("gjaering_temp_maal_c"),
    ),
}
render_brewday_panel(ctx, {}, gjaer_db, {})
