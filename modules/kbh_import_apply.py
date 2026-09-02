# modules/kbh_import_apply.py
"""
PRI 2C3 -- én, delt hjelpefunksjon som hydrerer session_state fra et
PRI 2C1-parserresultat (modules/kbh_import.py::parse_kbhrecipe_json())
inn i den AKTIVE App-oppskriften, som en HELT NY, ulagret oppskrift
("import as new", KBHR-010) -- ALDRI en tidligere lagret oppskrifts
lokale identitet (kildefil).

Speilbildet av modules/recipe_importer.py::apply_import_to_session_state()
(tekstimport-flyten) -- samme mønster: én, testbar funksjon som muterer
st.session_state, kaller ALDRI st.rerun() selv (UI-lagets ansvar,
ui/sidebar.py), og trekkes derfor ut i en egen, liten modul i stedet for
å bygges direkte inn i UI-koden -- nettopp for at PRI 2C3 sin
state-hydrering skal kunne testes uten et fullt Streamlit-sidepanel-
oppsett (se tests/test_kbh_import_apply.py).

Setter/tømmer NØYAKTIG de samme session_state-nøklene som
ui/sidebar.py sin eksisterende last-fra-disk-flyt (render_sidebar()) --
se den filens kommentarer for begrunnelsen bak hver enkelt nøkkel --
PLUSS de "import as new"-spesifikke tømmingene nederst, som IKKE finnes
i last-fra-disk-flyten (den SKAL jo nettopp overta en lagret
oppskrifts identitet -- en import skal aldri gjøre det).
"""
import copy

from modules.process_profiles import normaliser_prosessprofil
from modules.recipe import resolve_recipe_efficiency


def apply_kbhrecipe_import_to_session_state(import_resultat):
    """
    `import_resultat` er EKSAKT det parse_kbhrecipe_json() returnerer:
    `{"recipe": {...App-native felt...}, "passthrough": {...}}` -- se
    modules/kbh_import.py sin egen docstring for feltlisten.

    Ren mutasjon av st.session_state -- ingen filsystem-tilgang, ingen
    st.rerun(), ingen UI. Kalleren (ui/sidebar.py) er ansvarlig for å
    faktisk kalle parse_kbhrecipe_json() FØRST (denne funksjonen
    validerer ingenting selv -- den stoler fullt ut på at
    `import_resultat` allerede er en gyldig, godkjent import), vise en
    bekreftelse FØR denne kalles, og kalle st.rerun() ETTERPÅ.
    """
    import streamlit as st

    r = import_resultat["recipe"]
    passthrough = import_resultat.get("passthrough")

    st.session_state.valgt_malt = r["malts"]
    st.session_state.valgt_humle = r["hops"]
    st.session_state.valgt_gjaer_id = r["yeast"]
    st.session_state.gjeldende_navn = r["name"]
    st.session_state["_gjeldende_navn_preserved"] = r["name"]
    st.session_state.brygger_stil = r["brygger_stil"]
    st.session_state.batch_volum_input = r["batch_size"]
    # PRI 2C0 (KBHR-019) -- en importert fils effektivitet er, akkurat
    # som en lagret oppskrifts, recipe-scoped og skal vinne over
    # utstyrsprofilen resten av denne oppskriftens aktive økt (se
    # modules/recipe_context.py). Parseren garanterer allerede et
    # gyldig, positivt tall her, så resolve_recipe_efficiency() er i
    # praksis en no-op-bekreftelse -- men brukes likevel, for å gå
    # gjennom den ENE, felles policy-funksjonen i stedet for å anta
    # gyldigheten selv (samme forsvar-i-dybden-prinsipp som resten av
    # denne kodebasen).
    st.session_state["_aktiv_recipe_efficiency"] = resolve_recipe_efficiency(r.get("efficiency"))
    # PRI 2C2 (KBHR-011/KBHR-014) -- bevart, ikke-beregningspåvirkende
    # metadata fra selve importen. Deep-copiert (kilden er parserens
    # EGEN returverdi, men vi skal aldri stole på at ingen andre
    # steder senere kan finne på å mutere den samme dicten).
    st.session_state["_aktiv_kbh_passthrough"] = (
        copy.deepcopy(passthrough) if isinstance(passthrough, dict) and passthrough else None
    )
    # Samme forsvar som ui/sidebar.py sin last-fra-disk-flyt: en
    # normalisering her (selv om parseren allerede har normalisert en
    # kjent standardprofil, eller aldri endrer en "egendefinert") er
    # billig og fjerner enhver tvil om at en korrupt/hybrid meskeplan
    # noensinne kan bli aktiv.
    _prosess = r.get("process_profile")
    st.session_state["aktiv_prosessprofil"] = normaliser_prosessprofil(_prosess) if _prosess else None
    st.session_state["_lastet_water_source_profile"] = r.get("water_source_profile")
    st.session_state["_lastet_water_target_profile"] = r.get("water_target_profile")
    st.session_state["_lastet_water_treatment"] = r.get("water_treatment")
    st.session_state["_lastet_water_measurements"] = r.get("water_measurements")
    st.session_state["_original_batch_size"] = r["batch_size"]
    # Tvinger malt-/humleradenes widget-nøkler til å bli friske (se
    # ui/malt_panel.py/ui/hop_panel.py sin `_v = import_versjon`-bruk)
    # slik at de faktisk viser de NYE, importerte radene i stedet for
    # gammel, stedfortredende widget-state fra FØR importen.
    st.session_state.import_versjon = st.session_state.get("import_versjon", 0) + 1
    st.session_state["_malt_pct_pending_sync"] = False
    st.session_state.pop("skaler_maal_volum", None)

    # "Import as new" (KBHR-010) -- ALDRI arv en tidligere lastet/lagret
    # oppskrifts lokale identitet. En importert fil skal aldri kunne
    # overskrive en annen, eksisterende lagret oppskrift bare fordi den
    # ble importert -- lagring skjer KUN via en påfølgende, eksplisitt
    # "Lagre"-handling i ui/recipe_card.py, og den handlingen ser da
    # ALLTID `_last_loaded_recipe` som tom og tilbyr derfor kun "Lagre
    # som ny kopi" (som selv nekter å overskrive en annen eksisterende
    # fil stille, se modules/recipe_storage.py::lagre_oppskrift()) --
    # aldri "Lagre endringer" på en fremmed fil.
    st.session_state.pop("_last_loaded_recipe", None)
    st.session_state.pop("_last_loaded_recipe_file", None)

    # Chief review-fiks (PR #5): ui/process_panel.py og ui/water_panel.py
    # bruker HVER SIN egen "synced_for"-markør
    # (_prosess_synced_for/_vann_synced_for) som de sammenligner mot
    # _last_loaded_recipe for å avgjøre om de skal resynke sin EGEN,
    # panel-lokale widget-state fra aktiv_prosessprofil/_lastet_water_*.
    # Siden importen over BEVISST tømmer _last_loaded_recipe (den skal jo
    # forbli None for en "ny, ulagret" oppskrift), ville et bytte fra "en
    # ANNEN allerede ulagret oppskrift" (der _last_loaded_recipe også
    # allerede var None) til "nettopp importert oppskrift" sett ut som
    # None -> None for begge panelene -- ingen synlig endring, og de ville
    # IKKE resynket, slik at forrige, nå stale panel-lokale prosess-/
    # vann-widget-state kunne overleve og overskrive akkurat de feltene vi
    # nettopp satte over. Ved eksplisitt å FJERNE begge markørene tvinges
    # BEGGE panelene til å resynke ubetinget på neste rendering, uansett
    # hva _last_loaded_recipe måtte være før/etter -- uten å måtte
    # gjeninnføre/late som en lagret identitet (som ville brutt "import
    # as new"). Ren, minimal fiks: INGEN endring i selve panelfilene.
    st.session_state.pop("_prosess_synced_for", None)
    st.session_state.pop("_vann_synced_for", None)
