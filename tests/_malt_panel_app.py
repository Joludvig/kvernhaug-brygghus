"""Minimal vertskap-app for AppTest-baserte tester av ui/malt_panel.py.
Rendrer KUN maltpanelet mot en liten stub-database -- ikke en del av
selve applikasjonen, og plukkes ikke opp av `unittest discover` (matcher
ikke test*.py). Speiler tests/_hop_panel_app.py sitt mønster."""
import streamlit as st
from ui.malt_panel import render_malt_panel

if "valgt_malt" not in st.session_state:
    st.session_state["valgt_malt"] = [
        {"id": "weyermann_pilsner", "mengde": 4.0},
        {"id": "weyermann_pilsner", "mengde": 1.0},
    ]

_MALT_DATABASE = {
    "weyermann_pilsner": {
        "display_name": "Pilsner Malt",
        "produsent": "Weyermann",
        "kategori": "Basemalt",
        "smakstags": ["brød", "korn"],
        "ebc": 3.5,
        "potensiale": 1.037,
    },
}

render_malt_panel(_MALT_DATABASE)
