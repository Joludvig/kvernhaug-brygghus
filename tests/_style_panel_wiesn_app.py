"""Minimal vertskap-app for AppTest av ui/style_panel.py sitt
BJCP-offisiell-merke (krav 2, Kvernhaug-gjennomgang 2026-07-27). Bruker en
oppskrift som lander headline på «Historisk Wiesn-Märzen» — den eneste
ikke-offisielle stilen i biblioteket — for å bekrefte at UI-et faktisk merker
den som Kvernhaug/historisk. Ikke en del av selve applikasjonen, og plukkes
ikke opp av `unittest discover` (matcher ikke test*.py)."""
import streamlit as st
from modules.flavor_engine import generer_smakshjul
from modules.style_engine import analyser_stil_og_balanse
from ui.style_panel import render_style_panel

if "valgt_humle" not in st.session_state:
    st.session_state["valgt_humle"] = []

recipe = {
    "stats": {"og": 1.064, "fg": 1.013, "ibu": 23.5, "ebc": 17.5, "abv": 6.7},
    "flavor_profile": {"Brød": 6.0, "Toast": 4.0, "Maltfylde": 6.0, "Bitterhet": 3.0},
    "malts": [], "hops": [], "yeast": "saflager_w3470",
}
style_analysis = analyser_stil_og_balanse(recipe)
fig_smak, _ = generer_smakshjul([], {}, [], {}, recipe["stats"]["ibu"], "SafLager W-34/70", {})

ctx = {
    "fig_smak": fig_smak,
    "style_analysis": style_analysis,
    "recipe": recipe,
    "volum": 20.0,
    "conflicts": [],
}

render_style_panel(ctx, {})
