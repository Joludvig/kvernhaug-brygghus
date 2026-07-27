"""Realistisk testvert for Pantry V1-integrasjonstestene, samme mønster som
tests/_full_flow_app.py: gjenskaper den relevante delen av den ekte app.py-
flyten (oppskrift -> ctx -> recipe_card sin "Skaler oppskrift" -> Pantry-
panelet), i nøyaktig samme rekkefølge som app.py selv.

Oppskriften seedes fra den committede Wiesn-Märzen-fixturen
(tests/fixtures/recipes/wiesn_marzen_1872.json) — samme fixture som
tests/test_style_engine_recipes.py bruker — i stedet for en vilkårlig
standardoppskrift, slik testene kan sjekke reell nok/mangler-status mot en
kjent, karakteristisk oppskrift.

Session_state med prefiks "_debug_" eksponerer mellomresultater (ctx,
innlest pantry) slik at tests/test_pantry_integration.py kan verifisere
strukturelt (f.eks. at oppskriften/prosessprofilen/vannkjemien er byte-for-
byte uendret) i stedet for å skrape rendret UI-tekst for alt.

Ikke en del av selve applikasjonen, og plukkes ikke opp av
`unittest discover` (matcher ikke test*.py)."""
import json
import os
import streamlit as st

from modules.recipe_context import bygg_recipe_context
from modules import pantry
from modules.smart_shopping_list import beregn_handleliste
from ui.recipe_card import render_recipe_card
from ui.pantry_panel import render_pantry_panel
from ui.smart_shopping_list_panel import render_smart_shopping_list_panel

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _last_json(*deler):
    with open(os.path.join(_REPO_ROOT, *deler), encoding="utf-8") as f:
        return json.load(f)


malt_database = {k: v for k, v in _last_json("data", "master_malt.json").items() if not k.startswith("_")}
humle_database = {k: v for k, v in _last_json("data", "master_humle_v2.json").items() if not k.startswith("_")}
gjaer_database = {k: v for k, v in _last_json("data", "master_gjaer_v2.json").items() if not k.startswith("_")}

_fixture = _last_json("tests", "fixtures", "recipes", "wiesn_marzen_1872.json")

if "valgt_malt" not in st.session_state:
    st.session_state.valgt_malt = list(_fixture["malts"])
if "valgt_humle" not in st.session_state:
    st.session_state.valgt_humle = list(_fixture["hops"])
if "valgt_gjaer_id" not in st.session_state:
    st.session_state.valgt_gjaer_id = _fixture["yeast"]
if "gjeldende_navn" not in st.session_state:
    st.session_state.gjeldende_navn = _fixture["name"]
if "batch_volum_input" not in st.session_state:
    st.session_state.batch_volum_input = 20.0
if "brygger_stil" not in st.session_state:
    st.session_state.brygger_stil = ""
if "global_butikk" not in st.session_state:
    st.session_state.global_butikk = "Ølbrygging.no"
if "_original_batch_size" not in st.session_state:
    st.session_state["_original_batch_size"] = 20.0

# Løs opp pending-nøkler fra "Skaler oppskrift" FØR widgetene under
# instansieres, akkurat som app.py gjør det (linje 79-85).
if "_pending_batch_volum" in st.session_state:
    st.session_state.batch_volum_input = st.session_state.pop("_pending_batch_volum")
if "_pending_gjeldende_navn" in st.session_state:
    st.session_state.gjeldende_navn = st.session_state.pop("_pending_gjeldende_navn")
if "_pending_import_versjon_bump" in st.session_state:
    st.session_state.pop("_pending_import_versjon_bump")
    st.session_state.import_versjon = st.session_state.get("import_versjon", 0) + 1

# Satt FØR noen Pantry-handling kjøres, slik testene kan bekrefte at Pantry
# aldri rører prosessprofilen eller vannkjemien (krav 16/17) -- disse to
# session_state-nøklene settes normalt av ui/process_panel.py og
# ui/water_panel.py, som ikke er en del av denne minimale testverten.
if "aktiv_prosessprofil" not in st.session_state:
    st.session_state["aktiv_prosessprofil"] = {"navn": "Test Prosessprofil", "uendret": True}
if "aktiv_vannmaal_snapshot" not in st.session_state:
    st.session_state["aktiv_vannmaal_snapshot"] = {"target_id": "test_profil", "uendret": True}

ctx = bygg_recipe_context(
    oppskrift_navn=st.session_state.gjeldende_navn,
    malt_valg=st.session_state.valgt_malt,
    humle_valg=st.session_state.valgt_humle,
    gjaer_id=st.session_state.valgt_gjaer_id,
    malt_db=malt_database,
    humle_db=humle_database,
    gjaer_db=gjaer_database,
)
st.session_state["_debug_ctx_recipe"] = ctx["recipe"]

render_recipe_card(ctx, malt_database, humle_database, gjaer_database)
render_pantry_panel(ctx, malt_database, humle_database, gjaer_database)
render_smart_shopping_list_panel(ctx, malt_database, humle_database, gjaer_database)

st.session_state["_debug_pantry"] = pantry.last_pantry()
st.session_state["_debug_mangler_rader"] = pantry.beregn_mangler(
    ctx["recipe"], st.session_state["_debug_pantry"], malt_database, humle_database, gjaer_database,
)
st.session_state["_debug_handleliste"] = beregn_handleliste(
    ctx["recipe"], st.session_state["_debug_pantry"], malt_database, humle_database, gjaer_database,
    butikk=st.session_state.get("global_butikk", "Ølbrygging.no"),
)
