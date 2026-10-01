"""Minimal vertskap-app for AppTest av Råvarer-broen i ui/water_panel.py.
Ikke en del av selve applikasjonen, og plukkes ikke opp av
`unittest discover` (matcher ikke test*.py)."""
import streamlit as st

from ui.water_panel import render_water_panel

ctx = {"volum": 20.0, "brygger_stil": "", "style_analysis": {}}
st.session_state.setdefault("valgt_malt", [{"id": "weyermann_pilsner", "mengde": 5.0}])
render_water_panel(ctx, {})
