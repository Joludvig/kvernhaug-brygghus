# App A3 (issue #237) -- kombinert AppTest-harness som verter BÅDE
# ui/sidebar.py::render_sidebar() (den EKTE "Importer oppskrift fra
# tekst"-UI-en) OG ui/brewday_panel.py::render_brewday_panel() (Steg
# 4/5-målefeltene + det delte aktiv-brew-målet), for å teste den EKTE
# tekstimport-stien -- i motsetning til tests/_brewday_a1_measurement_app.py,
# som setter `_last_loaded_recipe_file` direkte via en miljøvariabel og
# derfor ALDRI kjører gjennom modules/recipe_importer.py::
# apply_import_to_session_state() (se docs/development/
# app_a3_state_orientation_preflight.md Section 14, punkt 1, og
# tests/test_app_a3_state_orientation_apptest.py).
#
# KVERNHAUG_EQUIPMENT_FILE / KVERNHAUG_RECIPES_DIR styres av testens
# egen setUp(), akkurat som tests/_brewday_a1_measurement_app.py.
import json
import os

import streamlit as st

from modules.recipe_context import bygg_recipe_context
from ui.brewday_panel import render_brewday_panel
from ui.sidebar import render_sidebar

for _nokkel, _default in (
    ("gjeldende_navn", "A3 Harness Ale"),
    ("batch_volum_input", 20.0),
    ("brygger_stil", ""),
    ("valgt_malt", [{"id": "weyermann_pilsner", "mengde": 5.0}]),
    ("valgt_humle", []),
    ("valgt_gjaer_id", "safale_us_05"),
    ("_aktiv_recipe_efficiency", None),
    ("_aktiv_kbh_passthrough", None),
    ("import_versjon", 0),
    ("bd_tilsetninger", []),
):
    if _nokkel not in st.session_state:
        st.session_state[_nokkel] = _default


def _last_json(filnavn):
    try:
        with open(os.path.join("data", filnavn), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


malt_db = _last_json("master_malt.json")
humle_db = _last_json("master_humle_v2.json")
gjaer_db = _last_json("master_gjaer_v2.json")
# Sikrer at harnessets egne default-valg alltid finnes i databasen som
# faktisk sendes videre til bygg_recipe_context()/render_brewday_panel(),
# uavhengig av hva den ekte data/master_*.json for øyeblikket inneholder.
malt_db.setdefault("weyermann_pilsner", {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037})
gjaer_db.setdefault("safale_us_05", {"display_name": "US-05", "gjaertype": "Ale", "attenuation": 0.75})

render_sidebar()

ctx = bygg_recipe_context(
    oppskrift_navn=st.session_state.gjeldende_navn,
    malt_valg=st.session_state.valgt_malt,
    humle_valg=st.session_state.valgt_humle,
    gjaer_id=st.session_state.valgt_gjaer_id,
    malt_db=malt_db,
    humle_db=humle_db,
    gjaer_db=gjaer_db,
)

render_brewday_panel(ctx, humle_db, gjaer_db, malt_db)
