"""Minimal vertskap-app for AppTest av ui/water_panel.py sin returkontrakt
(Brewday Tab UX Cleanup V1, Steg F13 -- MUST 2). Ikke en del av selve
applikasjonen, og plukkes ikke opp av `unittest discover` (matcher ikke
test*.py).

Kaller render_water_panel() ÉN gang per skriptkjøring (som i den ekte
appen) og lagrer returverdien i session_state under en NY nøkkel per
kjøring (telleren økes for hver .run()), slik at testen kan sammenligne
kontrakten (de fire nøklene) på tvers av flere ekte reruns -- uavhengig
av at hele forberedelsesdelen nå ligger inne i en lukket expander."""
import streamlit as st

from ui.water_panel import render_water_panel

ctx = {"volum": 20.0, "brygger_stil": "", "style_analysis": {}}

st.session_state.setdefault("valgt_malt", [{"id": "weyermann_pilsner", "mengde": 5.0}])

resultat = render_water_panel(ctx, {})

_teller = st.session_state.get("_test_water_return_teller", 0) + 1
st.session_state["_test_water_return_teller"] = _teller
st.session_state[f"_test_water_return_{_teller}"] = resultat
