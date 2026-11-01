"""Minimal vertskap-app for AppTest av hele ui/water_panel.py (#548) med en
lagret vannbehandling (salter, syre) og ukjent kildevann, slik at
saltforklaringer, varsler og tabeller faktisk rendres. Ikke en del av
applikasjonen, og plukkes ikke opp av `unittest discover`."""
import streamlit as st

from ui.water_panel import render_water_panel

ctx = {"volum": 20.0, "brygger_stil": "", "style_analysis": {}}
st.session_state.setdefault("valgt_malt", [{"id": "weyermann_pilsner", "mengde": 5.0}])
st.session_state.setdefault("_last_loaded_recipe", "wf-i18n")
st.session_state.setdefault("_lastet_water_source_profile", None)
st.session_state.setdefault("_lastet_water_target_profile", None)
st.session_state.setdefault("_lastet_water_treatment", {
    "salter": [
        {"salt_id": "cacl2_vannfri", "gram": 40.0, "renhet": 1.0},
        {"salt_id": "kalsiumkarbonat", "gram": 0.04, "renhet": 1.0},
    ],
    "fordelingsmetode": "proporsjonal",
})
st.session_state.setdefault("_lastet_water_measurements", {
    "syrer": [{"syre_id": "melkesyre", "navn": "Melkesyre", "formel": "C3H6O3",
               "prosent": None, "mengde_ml": 2.0, "kommentar": ""}],
})
render_water_panel(ctx, {})
