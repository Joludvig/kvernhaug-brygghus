"""Realistisk testvert som gjenskaper HELE den faktiske appflyten fra
app.py — i nøyaktig samme rekkefølge som app.py selv:

    render_sidebar() (kan laste en lagret oppskrift og sette
    aktiv_prosessprofil direkte)
        -> bygg_recipe_context()   (bygges FØR prosesspanelet, som i
                                     tab_oppskrift i app.py, linje 119)
        -> render_process_panel()  (som i tab_bryggdag i app.py, linje 145)
        -> lag_brewday_plan()      (som ui/brewday_panel.py sin egen,
                                     direkte session_state-lesing)
        -> render_brewday_html()   (selve bryggedagsark-eksporten)

Resten av UI-en (malt/humle/gjær-redigering, innkjøp, verktøy) er utelatt
siden den ikke er relevant for denne regresjonen — men ALLE fem stegene
over bruker den ekte, uendrede applikasjonskoden.

Mellomresultatene stashes i st.session_state["_debug_*"] slik at testene
i tests/test_full_process_flow.py kan inspisere nøyaktig hvilket ledd som
først inneholder en feil meskeplan.

Ikke en del av selve applikasjonen, og plukkes ikke opp av
`unittest discover` (matcher ikke test*.py)."""
import json
import os
import streamlit as st

from ui.sidebar import render_sidebar
from ui.process_panel import render_process_panel
from modules.recipe_context import bygg_recipe_context
from modules.brewday_calc import lag_brewday_plan
from modules.brewday_template import render_brewday_html


def _last_json_data(filnavn):
    filsti = os.path.join("data", filnavn)
    with open(filsti, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


malt_database  = _last_json_data("master_malt.json")
humle_database = _last_json_data("master_humle_v2.json")
gjaer_database = _last_json_data("master_gjaer_v2.json")

if "valgt_malt" not in st.session_state:
    st.session_state.valgt_malt = [{"id": next(iter(malt_database)), "mengde": 5.0}]
if "valgt_humle" not in st.session_state:
    st.session_state.valgt_humle = [{"id": next(iter(humle_database)), "gram": 20, "tid": 60}]
if "valgt_gjaer_id" not in st.session_state:
    st.session_state.valgt_gjaer_id = next(iter(gjaer_database))
if "gjeldende_navn" not in st.session_state:
    st.session_state.gjeldende_navn = "Kvernhaug Spesial"
if "batch_volum_input" not in st.session_state:
    st.session_state.batch_volum_input = 20.0
if "brygger_stil" not in st.session_state:
    st.session_state.brygger_stil = ""
if "global_butikk" not in st.session_state:
    st.session_state.global_butikk = "Ølbrygging.no"

# 1) SIDEBAR — kan laste en lagret oppskrift, som setter
#    aktiv_prosessprofil DIREKTE (uten å gå via prosesspanelets selectbox)
#    og deretter kaller st.rerun().
render_sidebar()

# 2) SENTRAL BEREGNINGSMOTOR — bygges FØR prosesspanelet, akkurat som i
#    app.py (ctx bygges i tab_oppskrift, FØR tab_bryggdag sin
#    render_process_panel).
ctx = bygg_recipe_context(
    oppskrift_navn=st.session_state.gjeldende_navn,
    malt_valg=st.session_state.valgt_malt,
    humle_valg=st.session_state.valgt_humle,
    gjaer_id=st.session_state.valgt_gjaer_id,
    malt_db=malt_database,
    humle_db=humle_database,
    gjaer_db=gjaer_database,
)
st.session_state["_debug_ctx_process_profile"] = ctx["recipe"]["process_profile"]

# 3) PROSESSPANEL — akkurat som tab_bryggdag i app.py.
render_process_panel(ctx, malt_database)
st.session_state["_debug_aktiv_prosessprofil_etter_panel"] = st.session_state.get("aktiv_prosessprofil")

# 4) BRYGGEDAGSPLAN — leser aktiv_prosessprofil DIREKTE fra session_state,
#    akkurat som ui/brewday_panel.py gjør (se dens egen kommentar om
#    hvorfor den ikke bruker ctx her).
prosess_profil_til_plan = st.session_state.get("aktiv_prosessprofil")
st.session_state["_debug_process_profile_til_plan"] = prosess_profil_til_plan
plan = lag_brewday_plan(
    malt_valg=st.session_state.valgt_malt,
    humle_valg=st.session_state.valgt_humle,
    gjaer_id=st.session_state.valgt_gjaer_id,
    gjaer_info=gjaer_database.get(st.session_state.valgt_gjaer_id, {}),
    og=ctx["og"],
    batch_volum_l=ctx["volum"],
    humle_database=humle_database,
    malt_database=malt_database,
    process_profile=prosess_profil_til_plan,
)
st.session_state["_debug_plan"] = plan

# 5) EKSPORT — selve bryggedagsarket (HTML).
html = render_brewday_html(ctx, plan, {})
st.session_state["_debug_export_html"] = html
