# modules/recipe_context.py
from modules.calculations import beregn_og, beregn_ebc, beregn_total_ibu, beregn_fg_og_abv
from modules.flavor_engine import generer_smakshjul
from modules.flavor_summary import generer_smakssammendrag
from modules.style_engine import analyser_stil_og_balanse
from modules.flavor_conflicts import sjekk_smakskonflikter
from modules.recipe import bygg_recipe_object
from modules.equipment import last_equipment
import streamlit as st

def bygg_recipe_context(oppskrift_navn, malt_valg, humle_valg, gjaer_id, malt_db, humle_db, gjaer_db):
    volum = st.session_state.get("batch_volum_input", 20.0) if "batch_volum_input" in st.session_state else 20.0
    effektivitet = last_equipment().get("efficiency", 0.75)
    brygger_stil = st.session_state.get("brygger_stil", "")
    # Bryggemåte (prosessprofil) er helt separat fra ingrediensvalget over —
    # samme mønster som brygger_stil: lest fra session_state, satt av
    # ui/process_panel.py, og påvirker ALDRI malt/humle/gjær-beregningene.
    prosess_profil = st.session_state.get("aktiv_prosessprofil")

    # Flater ut biblioteker for beregninger
    flatt_malt = {info.get("display_name", k): info for k, info in malt_db.items() if info}
    flatt_humle = {info.get("display_name", k): info for k, info in humle_db.items() if info}
    flatt_gjaer = {info.get("display_name", k): info for k, info in gjaer_db.items() if info}

    # Hent navn og data med trygge fallbacks hvis databasen er slettet/tom
    malt_calc = []
    for m in malt_valg:
        m_id = m["id"]
        m_info = malt_db.get(m_id, {"display_name": "Ukjent Malt", "ebc": 4.0, "pris_olbrygging": 35.0, "pris_vestbrygg": 35.0})
        malt_calc.append({"navn": m_info.get("display_name", "Ukjent Malt"), "mengde": m["mengde"]})

    humle_calc = []
    for h in humle_valg:
        h_id = h["id"]
        h_info = humle_db.get(h_id, {"display_name": "Ukjent Humle", "alfa": 5.0, "pris_olbrygging": 99.0, "pris_vestbrygg": 99.0})
        humle_calc.append({"navn": h_info.get("display_name", "Ukjent Humle"), "gram": h["gram"], "tid": h["tid"]})

    gjaer_info = gjaer_db.get(gjaer_id, {
        "display_name": "Standard Gjær (US-05)", 
        "attenuation": 0.75, 
        "pris_olbrygging": 59.0, 
        "pris_vestbrygg": 59.0
    })
    gjaer_navn = gjaer_info.get("display_name", "Standard Gjær (US-05)")
    attenuation = gjaer_info.get("attenuation", 0.75)

    # Beregninger (Linjen under er nå helt renset)
    og = beregn_og(malt_calc, flatt_malt, volum, effektivitet)
    st.session_state["_last_og"] = og
    ebc = beregn_ebc(malt_calc, flatt_malt, volum)
    ibu = beregn_total_ibu(humle_calc, flatt_humle, volum, og)
    fg, abv = beregn_fg_og_abv(og, attenuation)

    # Priskalkulering med sjekk på om prisnøkkelen faktisk eksisterer
    pris_nokkel = "pris_olbrygging" if st.session_state.get("global_butikk") == "Ølbrygging.no" else "pris_vestbrygg"
    total_pris = gjaer_info.get(pris_nokkel, 59.0)
    
    for m in malt_valg:
        m_info = malt_db.get(m["id"], {})
        total_pris += m["mengde"] * (m_info.get(pris_nokkel) or 35.0)
    for h in humle_valg:
        h_info = humle_db.get(h["id"], {})
        total_pris += (h["gram"] * h_info.get(pris_nokkel, 99.0) / 100)

    # Sensorikk og AI
    fig_smak, poeng = generer_smakshjul(malt_calc, flatt_malt, humle_calc, flatt_humle, ibu, gjaer_navn, flatt_gjaer)
    summary = generer_smakssammendrag(poeng)

    recipe_obj = bygg_recipe_object(oppskrift_navn, volum, effektivitet, malt_valg, humle_valg, gjaer_id, og, fg, abv, ibu, ebc, poeng, brygger_stil=brygger_stil, process_profile=prosess_profil)
    style_analysis = analyser_stil_og_balanse(recipe_obj)
    conflicts = sjekk_smakskonflikter(recipe_obj)

    return {
        "name": oppskrift_navn, "volum": volum, "effektivitet": effektivitet,
        "brygger_stil": brygger_stil,
        "og": og, "fg": fg, "abv": abv, "ibu": ibu, "ebc": ebc, "total_pris": total_pris,
        "fig_smak": fig_smak, "summary": summary, "style_analysis": style_analysis, "conflicts": conflicts,
        "recipe": recipe_obj
    }
