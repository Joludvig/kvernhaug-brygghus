# app.py
import streamlit as st
import json
import os

# Importer den nye sentrale hjernen (Prioritet: Central Engine)
from modules.recipe_context import bygg_recipe_context

# Importer de nye, rene UI-komponentene (Prioritet: UI-Splitting)
from ui.sidebar import render_sidebar
from ui.branding import render_header
from ui.malt_panel import render_malt_panel
from ui.hop_panel import render_hop_panel
from ui.yeast_panel import render_yeast_panel
from ui.recipe_card import render_recipe_card
from ui.style_panel import render_style_panel
from ui.supplier_panel import render_supplier_panel
from ui.import_panel import render_import_panel
from ui.shopping_list_panel import render_shopping_list_panel
from ui.brewday_panel import render_brewday_panel
from ui.equipment_panel import render_equipment_panel

# 1. Grunnleggende Streamlit-konfigurering
st.set_page_config(page_title="Kvernhaug Brygghus", page_icon="🍺", layout="wide")

render_header()

# Helper-funksjon for å laste råvare-JSON
# Helper-funksjon for å laste råvare-JSON med krasjsikring
def last_json_data(filnavn):
    filsti = os.path.join("data", filnavn)
    
    # Sørg for at data-mappen eksisterer
    os.makedirs("data", exist_ok=True)
    
    # Hvis filen ikke finnes, eller er helt tom (0 bytes), opprett en tom database-struktur
    if not os.path.exists(filsti) or os.path.getsize(filsti) == 0:
        with open(filsti, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}
        
    try:
        with open(filsti, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except json.JSONDecodeError:
        return {}

# 2. Sentral lasting av de tre råvaredatabasene
malt_database = last_json_data("malt.json")
humle_database = last_json_data("master_humle_v2.json")
gjaer_database = last_json_data("master_gjaer_v2.json")

# 3. Initialiser globale session states hvis appen startes for første gang
if "valgt_malt" not in st.session_state:
    første_malt = next(iter(malt_database), "weyermann_pilsner")
    st.session_state.valgt_malt = [{"id": første_malt, "mengde": 5.0}]
if "valgt_humle" not in st.session_state:
    første_humle = next(iter(humle_database), "magnum")
    st.session_state.valgt_humle = [{"id": første_humle, "gram": 20, "tid": 60}]
if "valgt_gjaer_id" not in st.session_state:
    st.session_state.valgt_gjaer_id = next(iter(gjaer_database), "safale_us_05")
if "gjeldende_navn" not in st.session_state:
    st.session_state.gjeldende_navn = "Kvernhaug Spesial"
if "global_butikk" not in st.session_state:
    st.session_state.global_butikk = "Ølbrygging.no"
if "import_versjon" not in st.session_state:
    st.session_state.import_versjon = 0
if "batch_volum_input" not in st.session_state:
    # Restore from shadow key if Streamlit cleared the widget-bound key
    # during a mid-render st.rerun() (e.g. from malt_panel before col2 ran)
    st.session_state.batch_volum_input = st.session_state.get("_batch_volum_preserved", 20.0)
if "brygger_stil" not in st.session_state:
    st.session_state.brygger_stil = ""

# Løs opp pending batch-volum fra skalering (må skje før widgeten instansieres)
if "_pending_batch_volum" in st.session_state:
    st.session_state.batch_volum_input = st.session_state.pop("_pending_batch_volum")
if "_pending_gjeldende_navn" in st.session_state:
    st.session_state.gjeldende_navn = st.session_state.pop("_pending_gjeldende_navn")
if "_pending_import_versjon_bump" in st.session_state:
    st.session_state.pop("_pending_import_versjon_bump")
    st.session_state.import_versjon = st.session_state.get("import_versjon", 0) + 1
if "_pending_brygger_stil_reset" in st.session_state:
    st.session_state.pop("_pending_brygger_stil_reset")
    st.session_state.brygger_stil = ""

# Keep shadow key in sync before any panel can call st.rerun().
# _batch_volum_preserved is not widget-bound so Streamlit never clears it.
st.session_state["_batch_volum_preserved"] = st.session_state.batch_volum_input

# 4. RJØR SIDEBAR RECIPE BROWSER (Prioritet 4 & UI-splitting)
render_sidebar()

# 5. OPPRETT HOVEDLAYOUTEN (To asymmetriske spalter)
col1, col2 = st.columns([2.0, 1.2])

# ==================================================
# === SPALTE 1: INTERAKTIV OPPSKRIFTSBYGGER =======
# ==================================================
# NB: Panelene settes FØRST slik at valgt_malt / valgt_humle / valgt_gjaer_id
# i session_state reflekterer gjeldende widget-verdier FØR beregningsmotor kjøres.
# Uten denne rekkefølgen vil IBU/OG alltid ligge én kjøring bak brukerens input.
with col1:
    render_malt_panel(malt_database)
    st.write("---")
    render_hop_panel(humle_database)
    st.write("---")
    render_yeast_panel(gjaer_database)

# 6. KJØR SENTRAL BEREGNINGS-MOTOR etter at inputpanelene har oppdatert session_state
ctx = bygg_recipe_context(
    oppskrift_navn=st.session_state.gjeldende_navn,
    malt_valg=st.session_state.valgt_malt,
    humle_valg=st.session_state.valgt_humle,
    gjaer_id=st.session_state.valgt_gjaer_id,
    malt_db=malt_database,
    humle_db=humle_database,
    gjaer_db=gjaer_database
)

# ==================================================
# === SPALTE 2: SENTRAL ANALYSE & SENSORISK KORT ====
# ==================================================
with col2:
    render_recipe_card(ctx, malt_database, humle_database, gjaer_database)
    render_style_panel(ctx, humle_database)
    render_supplier_panel(malt_database, humle_database, gjaer_database)

render_shopping_list_panel(ctx, malt_database, humle_database, gjaer_database)
render_brewday_panel(ctx, humle_database, gjaer_database)
render_equipment_panel()

render_import_panel()
