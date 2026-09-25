"""Minimal vertskap-app for AppTest-baserte tester av ui/hop_panel.py.
Rendrer KUN humlepanelet mot en liten stub-database — ikke en del av
selve applikasjonen, og plukkes ikke opp av `unittest discover` (matcher
ikke test*.py). Speiler tests/_yeast_panel_app.py sitt mønster."""
import streamlit as st
from ui.hop_panel import render_hop_panel

if "valgt_humle" not in st.session_state:
    st.session_state["valgt_humle"] = [{"id": "citra", "gram": 20, "tid": 60}]

_HUMLE_DATABASE = {
    "citra": {
        "display_name": "Citra",
        "opprinnelse": "Amerikansk",
        "alfa_typisk": 12.0,
        "smakstags": ["sitrus", "tropisk"],
        "pris_olbrygging": 99.0,
        "pris_vestbrygg": 99.0,
    },
    "east_kent_goldings": {
        "display_name": "East Kent Goldings",
        "opprinnelse": "Britisk",
        "alfa_typisk": 5.0,
        "smakstags": ["blomster", "jordaktig"],
        "pris_olbrygging": 89.0,
        "pris_vestbrygg": 89.0,
    },
}

render_hop_panel(_HUMLE_DATABASE)
