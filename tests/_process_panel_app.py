"""Minimal vertskap-app for AppTest-baserte tester av ui/process_panel.py.
Rendrer KUN prosesspanelet mot en stubbet ctx — ikke en del av selve
applikasjonen, og plukkes ikke opp av `unittest discover` (matcher ikke
test*.py)."""
import streamlit as st
from ui.process_panel import render_process_panel

if "valgt_malt" not in st.session_state:
    st.session_state["valgt_malt"] = [
        {"id": "weyermann_munich_1", "mengde": 0.65},
        {"id": "munich_ii", "mengde": 4.28},
        {"id": "vienna", "mengde": 1.60},
    ]

ctx = {
    "brygger_stil": "",
    "style_analysis": {"stil": ""},
    "recipe": {"stats": {"og": 1.064}},
    "volum": 23.0,
}

render_process_panel(ctx, {})
