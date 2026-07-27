"""Minimal vertskap-app for AppTest-baserte tester av ui/style_panel.py.
Rendrer KUN stilpanelet mot en stubbet ctx (samme mønster som
_process_panel_app.py) — ikke en del av selve applikasjonen, og plukkes ikke
opp av `unittest discover` (matcher ikke test*.py)."""
import streamlit as st
from modules.flavor_engine import generer_smakshjul
from modules.style_engine import analyser_stil_og_balanse
from ui.style_panel import render_style_panel

if "valgt_humle" not in st.session_state:
    st.session_state["valgt_humle"] = []

# Reproduserbart avviks-scenario (se
# tests/test_style_engine.py::TestNumeriskNaermesteVsSamletTopp): belgisk
# gjærsignatur straffer English Bitter (raw_score-vinner) uten å påvirke
# English Dark Mild (score-vinner), slik at headline og listetopp peker på
# ulike stiler.
flavor_profile = {
    "Brød": 6.0, "Sitrus": 1.3, "Bitterhet": 2.0, "Fruktighet": 3.6,
    "Krydder": 6.4, "Maltfylde": 3.4, "Toast": 6.3, "Karamell": 0.4,
    "Nøtter": 1.7, "Sjokolade": 2.1, "Kaffe": 3.1, "Røyk": 3.0,
    "Honning": 0.3, "Jordlig": 5.2, "Tropisk": 5.3, "Steinfrukt": 3.2,
}
recipe = {
    "stats": {"og": 1.031, "fg": 1.0082, "ibu": 32.2, "ebc": 17.7, "abv": 2.99},
    "flavor_profile": flavor_profile,
    "malts": [], "hops": [], "yeast": "wlp500",
}
style_analysis = analyser_stil_og_balanse(recipe)
fig_smak, _ = generer_smakshjul([], {}, [], {}, recipe["stats"]["ibu"], "Belgisk Trippel-gjær", {})

ctx = {
    "fig_smak": fig_smak,
    "style_analysis": style_analysis,
    "recipe": recipe,
    "volum": 20.0,
    "conflicts": [],
}

render_style_panel(ctx, {})
