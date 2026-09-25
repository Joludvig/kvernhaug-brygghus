"""Minimal vertskap-app for AppTest-baserte tester av ui/yeast_panel.py.
Rendrer KUN gjærpanelet mot en liten stub-database — ikke en del av
selve applikasjonen, og plukkes ikke opp av `unittest discover` (matcher
ikke test*.py). Speiler tests/_process_panel_app.py sitt mønster."""
import streamlit as st
from ui.yeast_panel import render_yeast_panel

if "valgt_gjaer_id" not in st.session_state:
    st.session_state["valgt_gjaer_id"] = "safale_us_05"
if "gjaering_temp_maal_c" not in st.session_state:
    st.session_state["gjaering_temp_maal_c"] = None

_GJAER_DATABASE = {
    "safale_us_05": {
        "display_name": "SafAle US-05",
        "produsent": "Fermentis",
        "smakstags": ["nøytral", "ren"],
        "attenuation": 0.78,
    },
    "saflager_w3470": {
        "display_name": "SafLager W-34/70",
        "produsent": "Fermentis",
        "smakstags": ["ren", "lager"],
        "attenuation": 0.80,
    },
}

render_yeast_panel(_GJAER_DATABASE)
