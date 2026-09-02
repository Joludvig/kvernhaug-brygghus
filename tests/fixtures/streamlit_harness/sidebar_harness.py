# PRI 2C3 -- minimal AppTest-harness for ui/sidebar.py::render_sidebar()
# alene, uten resten av app.py sine paneler/beregninger. Speiler KUN de
# session_state-init-nøklene render_sidebar() faktisk leser/skriver til
# FØR noen widget er instansiert (samme utvalg som app.py sin egen
# init-blokk, se app.py punkt "3. Initialiser globale session states") --
# ikke en generell App-harness, kun nok til å teste sidebarens
# .kbhrecipe-import-UI isolert (se tests/test_kbh_import_ui_apptest.py).
import streamlit as st
from ui.sidebar import render_sidebar

if "gjeldende_navn" not in st.session_state:
    st.session_state["gjeldende_navn"] = "Kvernhaug Spesial"
if "batch_volum_input" not in st.session_state:
    st.session_state["batch_volum_input"] = 20.0
if "brygger_stil" not in st.session_state:
    st.session_state["brygger_stil"] = ""
if "valgt_malt" not in st.session_state:
    st.session_state["valgt_malt"] = [{"id": "weyermann_pilsner", "mengde": 5.0}]
if "valgt_humle" not in st.session_state:
    st.session_state["valgt_humle"] = [{"id": "magnum_de", "gram": 20, "tid": 60}]
if "valgt_gjaer_id" not in st.session_state:
    st.session_state["valgt_gjaer_id"] = "safale_us_05"
if "_aktiv_recipe_efficiency" not in st.session_state:
    st.session_state["_aktiv_recipe_efficiency"] = None
if "_aktiv_kbh_passthrough" not in st.session_state:
    st.session_state["_aktiv_kbh_passthrough"] = None
if "import_versjon" not in st.session_state:
    st.session_state["import_versjon"] = 0

render_sidebar()
