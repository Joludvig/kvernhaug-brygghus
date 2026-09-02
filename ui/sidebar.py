import copy
import json
import streamlit as st
from config import DEMO_MODE
from modules.recipe_storage import (
    hent_alle_oppskrifter,
    hent_oppskrift_filnavn_kart,
    finn_duplikate_oppskrift_navn,
)
from modules.process_profiles import normaliser_prosessprofil
from modules.recipe import resolve_recipe_efficiency
from modules.recipe_importer import (
    parse_recipe_text,
    match_imported_ingredients,
    apply_import_to_session_state,
)

def _last_master_db(filnavn):
    try:
        with open(f"data/{filnavn}", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def render_sidebar():
    if DEMO_MODE:
        st.sidebar.warning("🍺 Demo-modus — oppskrifter lagres ikke")

    st.sidebar.header("📁 Lagrede oppskrifter")
    _oppskrift_mappe_kwargs = {"mappe": "demo_recipes"} if DEMO_MODE else {}
    lagrede_brygg = hent_alle_oppskrifter(**_oppskrift_mappe_kwargs)
    filnavn_kart = hent_oppskrift_filnavn_kart(**_oppskrift_mappe_kwargs)

    if not DEMO_MODE:
        duplikater = finn_duplikate_oppskrift_navn()
        if duplikater:
            for dup in duplikater:
                st.sidebar.warning(
                    f"⚠️ Flere filer deler navnet «{dup['navn']}» "
                    f"({', '.join(dup['filer'])}) — kun én av dem vises under."
                )

    if lagrede_brygg:
        oppskrift_valg = ["-- Velg oppskrift --"] + list(lagrede_brygg.keys())
        valgt_lagret_navn = st.sidebar.selectbox(
            "Velg et brygg fra harddisken:",
            oppskrift_valg,
            key="sidebar_recipe_selector",
        )
        if (valgt_lagret_navn != "-- Velg oppskrift --"
                and valgt_lagret_navn != st.session_state.get("_last_loaded_recipe")):
            r_data = lagrede_brygg[valgt_lagret_navn]
            st.session_state.valgt_malt = r_data["malts"]
            st.session_state.valgt_humle = r_data["hops"]
            st.session_state.valgt_gjaer_id = r_data["yeast"] if isinstance(r_data["yeast"], str) else r_data["yeast"].get("id", "fermentis_us05")
            st.session_state.gjeldende_navn = r_data["name"]
            st.session_state["_gjeldende_navn_preserved"] = r_data["name"]
            st.session_state.brygger_stil = r_data.get("brygger_stil", "")
            st.session_state.batch_volum_input = r_data.get("batch_size", 20.0)
            # PRI 2C0 (KBHR-019) -- en gyldig, lagret recipe-efficiency er
            # recipe-scoped og skal vinne over utstyrsprofilen resten av
            # denne oppskriftens aktive økt (se modules/recipe_context.py).
            # Mangler feltet, eller er det ugyldig (eldre oppskrift), er
            # resultatet None -- da faller recipe_context.py tilbake til
            # gjeldende utstyrsprofil, akkurat som OPPGAVE D krever. Selve
            # utstyrsprofilen leses/endres ALDRI her.
            st.session_state["_aktiv_recipe_efficiency"] = resolve_recipe_efficiency(r_data.get("efficiency"))
            # PRI 2C2 (KBHR-011/KBHR-014) -- ikke-beregningspåvirkende
            # metadata bevart opakt fra en tidligere .kbhrecipe-import
            # (se modules/kbh_import.py sin "passthrough",
            # modules/recipe.py sin `_kbh_passthrough`-nøkkel) må følge
            # oppskriften videre gjennom load, akkurat som
            # _aktiv_recipe_efficiency over. Nøkkelen settes UBETINGET på
            # HVERT load -- enten til den nylastede oppskriftens egen
            # (deep-copierte) passthrough, eller til None -- slik at en
            # tidligere lastet oppskrifts passthrough ALDRI kan henge
            # igjen etter et bytte til en oppskrift som mangler feltet
            # (vanlig, ikke-importert oppskrift, eller en eldre lagring).
            _lagret_passthrough = r_data.get("_kbh_passthrough")
            st.session_state["_aktiv_kbh_passthrough"] = (
                copy.deepcopy(_lagret_passthrough)
                if isinstance(_lagret_passthrough, dict) and _lagret_passthrough
                else None
            )
            # Normaliser en EVENTUELT lagret prosessprofil FØR den blir
            # aktiv — en kjent standardprofil (Hochkurz osv.) kan da
            # ALDRI hydreres inn med en korrupt/hybrid meskeplan fra en
            # eldre, buggy lagring. Mangler oppskriften en prosessprofil
            # helt (f.eks. lagret før feltet eksisterte), holdes den
            # bevisst None — det lar ui/process_panel.py sin egen,
            # anbefaling-baserte førstegangsvisning slå inn i stedet for
            # å tvinge fram "Enkel infusjon".
            _lagret_profil = r_data.get("process_profile")
            st.session_state["aktiv_prosessprofil"] = (
                normaliser_prosessprofil(_lagret_profil) if _lagret_profil else None
            )
            # Vannbehandling (se modules/water_chemistry.py) lagres KUN som
            # en snapshot her — selve resynkroniseringen inn i panelets
            # egne, redigerbare session_state-nøkler skjer i
            # ui/water_panel.py (samme split som prosessprofilen: sidebaren
            # eier LASTING, panelet eier egen widget-hydrering). Mangler
            # oppskriften vannfelter (eldre lagring), forblir de bevisst
            # None — Jordalsvatnet (eller noen annen kilde) settes ALDRI
            # inn automatisk uten at brukeren selv velger det.
            st.session_state["_lastet_water_source_profile"] = r_data.get("water_source_profile")
            st.session_state["_lastet_water_target_profile"] = r_data.get("water_target_profile")
            st.session_state["_lastet_water_treatment"] = r_data.get("water_treatment")
            st.session_state["_lastet_water_measurements"] = r_data.get("water_measurements")
            st.session_state.import_versjon = st.session_state.get("import_versjon", 0) + 1
            st.session_state["_last_loaded_recipe"] = valgt_lagret_navn
            # Den FAKTISKE kildefilen (ikke bare navnet) -- se
            # modules/recipe_storage.py::lagre_oppskrift() sin
            # kilde_filnavn-parameter. Nødvendig for at en påfølgende
            # omdøping arkiverer riktig gammel fil i stedet for å gjette
            # filnavnet på nytt fra teksten i "name".
            st.session_state["_last_loaded_recipe_file"] = filnavn_kart.get(valgt_lagret_navn)
            st.session_state["_original_batch_size"] = r_data.get("batch_size", 20.0)
            st.session_state["_malt_pct_pending_sync"] = False
            st.session_state.pop("skaler_maal_volum", None)
            st.sidebar.success(f"Laddet: {valgt_lagret_navn}")
            st.rerun()
        elif valgt_lagret_navn == "-- Velg oppskrift --":
            st.session_state.pop("_last_loaded_recipe", None)
            st.session_state.pop("_last_loaded_recipe_file", None)
    else:
        st.sidebar.info("Ingen oppskrifter lagret i mappen ennå.")

    st.sidebar.write("---")
    with st.sidebar.expander("📥 Importer oppskrift fra tekst"):
        st.caption(
            "**Kg-format:**\n\n"
            "`5 kg Maris Otter`\n\n"
            "`300 g CaraMunich`\n\n"
            "**Prosentformat** (krever total maltmengde):\n\n"
            "`Total malt: 6 kg`\n\n"
            "`90% Maris Otter`\n\n"
            "`10% Crystal Malt`\n\n"
            "**Humle og gjær:**\n\n"
            "`20 g Magnum 60 min`\n\n"
            "`Wyeast 1318 London Ale III`\n\n"
            "⚠️ Humle må ha koketid, f.eks. `50 g Magnum 60 min`."
        )
        import_tekst = st.text_area("Oppskrift:", height=160, key="import_tekst_input", label_visibility="collapsed")

        if st.button("🔍 Analyser", key="import_analyser_btn", width="stretch"):
            if import_tekst.strip():
                parsed = parse_recipe_text(import_tekst)
                master_malt  = _last_master_db("master_malt.json")
                master_humle = _last_master_db("master_humle_v2.json")
                master_gjaer = _last_master_db("master_gjaer_v2.json")
                resultat = match_imported_ingredients(parsed, master_malt, master_humle, master_gjaer)
                resultat["metadata"] = {"navn": parsed.get("navn"), "batch_liter": parsed.get("batch_liter")}
                st.session_state["import_preview"] = resultat
                st.session_state["import_parsed"] = parsed
            else:
                st.warning("Lim inn ingredienser først.")

        preview = st.session_state.get("import_preview")
        if preview:
            parsed_debug = st.session_state.get("import_parsed", {})
            n_malt  = len(parsed_debug.get("malt", []))
            n_humle = len(parsed_debug.get("humle", []))
            n_gjaer = len(parsed_debug.get("gjaer", []))
            st.caption(f"Tolket: {n_malt} malt · {n_humle} humle · {n_gjaer} gjær-linje(r)")
            meta = preview.get("metadata", {})
            if meta.get("navn"):
                st.caption(f"📛 Navn: **{meta['navn']}**")
            if meta.get("batch_liter"):
                st.caption(f"🪣 Batch: **{meta['batch_liter']:.0f} L**")
            for w in parsed_debug.get("warnings", []):
                st.warning(w)

            matched = preview["matched"]
            unmatched = preview["unmatched"]

            st.markdown("**Matchet:**")
            noe_matchet = False
            for m in matched["malt"]:
                st.success(f"Malt: {m['navn']} → `{m['id']}` ({m['mengde']} kg)")
                noe_matchet = True
            for h in matched["humle"]:
                st.success(f"Humle: {h['navn']} → `{h['id']}` ({h['gram']}g, {h['tid']} min)")
                noe_matchet = True
            if matched["gjaer"]:
                g = matched["gjaer"]
                st.success(f"Gjær: {g['navn']} → `{g['id']}`")
                noe_matchet = True
            if not noe_matchet:
                st.info("Ingen ingredienser ble gjenkjent.")

            if unmatched:
                st.markdown("**Ikke gjenkjent:**")
                for u in unmatched:
                    st.error(f"{u['kategori'].capitalize()}: {u['navn']}")

            if noe_matchet:
                if st.button("✅ Importer oppskrift", key="import_bekreft_btn", width="stretch"):
                    apply_import_to_session_state(preview)
                    del st.session_state["import_preview"]
                    del st.session_state["import_parsed"]
                    st.rerun()
