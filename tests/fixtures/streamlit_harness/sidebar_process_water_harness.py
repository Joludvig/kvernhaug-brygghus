# PRI 2C3 -- Chief review-fiks (PR #5): AppTest-harness som i tillegg
# til ui/sidebar.py::render_sidebar() (se sidebar_harness.py) ALSO
# rendrer ui/process_panel.py og ui/water_panel.py, siden det er
# NØYAKTIG disse to panelenes egne "synced_for"-resync-markører
# (_prosess_synced_for/_vann_synced_for) reviewet fant en reell,
# ubevist regresjon i -- sidebar_harness.py alene kan derfor ikke bevise
# fiksen (se tests/test_kbh_import_process_water_resync_apptest.py).
import streamlit as st
from modules.recipe_context import bygg_recipe_context
from ui.sidebar import render_sidebar
from ui.process_panel import render_process_panel
from ui.water_panel import render_water_panel

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

ctx = bygg_recipe_context(
    st.session_state["gjeldende_navn"],
    st.session_state["valgt_malt"],
    st.session_state["valgt_humle"],
    st.session_state["valgt_gjaer_id"],
    malt_db={}, humle_db={}, gjaer_db={},
)
render_process_panel(ctx)
render_water_panel(ctx)
