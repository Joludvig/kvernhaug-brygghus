# app.py
import streamlit as st
import json
import os

from config import DEMO_MODE

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
from ui.import_panel import render_import_panel
from ui.shopping_list_panel import render_shopping_list_panel
from ui.humle_lager_panel import render_humle_lager_panel
from ui.pantry_panel import render_pantry_panel
from ui.smart_shopping_list_panel import render_smart_shopping_list_panel
from ui.brewday_panel import render_brewday_panel
from ui.equipment_panel import render_equipment_panel
from ui.process_panel import render_process_panel
from ui.water_panel import render_water_panel

# 1. Grunnleggende Streamlit-konfigurering
st.set_page_config(page_title="Kvernhaug Brygghus", page_icon="🍺", layout="wide")

render_header()

# Helper-funksjon for å laste råvare-JSON
# Helper-funksjon for å laste råvare-JSON med krasjsikring
def last_json_data(filnavn):
    filsti = os.path.join("data", filnavn)

    # Hvis filen ikke finnes, eller er helt tom (0 bytes): i DEMO_MODE
    # returneres bare en tom struktur i minnet -- masterdatabasene skal
    # ALDRI endres eller opprettes på disk i demo-modus, selv ikke som et
    # ufarlig "opprett tom fil"-skjelett.
    if not os.path.exists(filsti) or os.path.getsize(filsti) == 0:
        if DEMO_MODE:
            return {}
        # Sørg for at data-mappen eksisterer (kun utenfor DEMO_MODE)
        os.makedirs("data", exist_ok=True)
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
malt_database = last_json_data("master_malt.json")
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
    st.session_state.gjeldende_navn = st.session_state.get("_gjeldende_navn_preserved", "Kvernhaug Spesial")
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
if "_aktiv_recipe_efficiency" not in st.session_state:
    # PRI 2C0 (KBHR-019) -- None = "ingen recipe-scoped override ennå",
    # ikke en verdi. En helt ny/blank oppskrift skal fortsatt følge
    # utstyrsprofilen live (samme oppførsel som før denne rettelsen) --
    # se modules/recipe_context.py. Ikke widget-bundet (ingen UI-widget
    # skriver direkte til denne nøkkelen), så den kan settes direkte her
    # og i ui/recipe_card.py sin arkiver-/blank-flyt uten "pending"-mønsteret
    # gjeldende_navn/brygger_stil trenger.
    st.session_state["_aktiv_recipe_efficiency"] = None
if "_aktiv_kbh_passthrough" not in st.session_state:
    # PRI 2C2 (KBHR-011/KBHR-014) -- None = "ingen bevart import-
    # metadata ennå" for en helt ny/blank økt. Ikke widget-bundet, kan
    # settes direkte her og i ui/recipe_card.py sin arkiver-/blank-flyt,
    # samme mønster som _aktiv_recipe_efficiency over.
    st.session_state["_aktiv_kbh_passthrough"] = None

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

# Keep shadow keys in sync before any panel can call st.rerun().
# These keys are not widget-bound so Streamlit never clears them.
st.session_state["_batch_volum_preserved"] = st.session_state.batch_volum_input
st.session_state["_gjeldende_navn_preserved"] = st.session_state.gjeldende_navn

# 4. SIDEBAR
render_sidebar()

# 5. TABS
tab_oppskrift, tab_innkjop, tab_bryggdag, tab_verktoy = st.tabs([
    "🍺 Oppskrift", "🛒 Innkjøp & Lager", "🧪 Bryggdag", "🔧 Verktøy"
])

# ==================================================
# === TAB 1: OPPSKRIFT ============================
# ==================================================
# NB: col1 (input-paneler) MÅ rendres før bygg_recipe_context() kalles.
# Streamlit rendrer alle tab-innhold på hver kjøring, uavhengig av aktiv tab.
with tab_oppskrift:
    col1, col2 = st.columns([2.0, 1.2])

    with col1:
        render_malt_panel(malt_database)
        st.write("---")
        render_hop_panel(humle_database)
        st.write("---")
        render_yeast_panel(gjaer_database)

    # 6. SENTRAL BEREGNINGS-MOTOR — kjøres etter at input-panelene har rendret
    ctx = bygg_recipe_context(
        oppskrift_navn=st.session_state.gjeldende_navn,
        malt_valg=st.session_state.valgt_malt,
        humle_valg=st.session_state.valgt_humle,
        gjaer_id=st.session_state.valgt_gjaer_id,
        malt_db=malt_database,
        humle_db=humle_database,
        gjaer_db=gjaer_database
    )

    with col2:
        render_recipe_card(ctx, malt_database, humle_database, gjaer_database)

    render_style_panel(ctx, humle_database)

# ==================================================
# === TAB 2: INNKJØP & LAGER =====================
# ==================================================
with tab_innkjop:
    render_pantry_panel(ctx, malt_database, humle_database, gjaer_database)
    render_smart_shopping_list_panel(ctx, malt_database, humle_database, gjaer_database)
    st.write("---")
    with st.expander("Eldre handleliste og humlelager", expanded=False):
        render_shopping_list_panel(ctx, malt_database, humle_database, gjaer_database)
        st.write("---")
        render_humle_lager_panel(humle_database)

# ==================================================
# === TAB 3: BRYGGDAG ============================
# ==================================================
with tab_bryggdag:
    render_process_panel(ctx, malt_database, humle_database)
    st.write("---")
    render_water_panel(ctx, malt_database)
    st.write("---")
    render_brewday_panel(ctx, humle_database, gjaer_database, malt_database)

# ==================================================
# === TAB 4: VERKTØY =============================
# ==================================================
with tab_verktoy:
    render_import_panel()
    # Utstyrsprofil er ren konfigurasjon (aldri brukt under aktiv brygging)
    # -- flyttet hit fra Bryggdag-fanen i Brewday Tab UX Cleanup V1 for å
    # redusere planleggings-/konfigstøy i selve bryggedagsverktøyet. Ren
    # visuell flytting: samme funksjon, samme render_equipment_panel()-kall,
    # samme egen "st.write('---')" innledningsvis i funksjonen selv.
    render_equipment_panel()
