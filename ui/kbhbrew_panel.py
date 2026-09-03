# ui/kbhbrew_panel.py
"""
PRI 3B2 -- minimal Streamlit-UI for den nye Core `.kbhbrew` V1-arbeids-
flyten (docs/development/CORE_KBHBREW_V1.md), koblet til den allerede
merged/testede PRI 3B1-motoren (modules/kbhbrew.py) og lagringen
(modules/kbhbrew_storage.py). Tre smale, eksplisitte handlinger:

  1. render_kbhbrew_create_panel() -- kalles fra ui/brewday_panel.py.
     Fryser gjeldende oppskrift/utstyr/spådde verdier som et NYTT,
     historisk brygg -- KUN på eksplisitt knappeklikk, aldri bare fordi
     Bryggdag-fanen rendres/rerendres.
  2. render_kbhbrew_import_panel() -- kalles fra app.py under
     "🔧 Verktøy". Opplasting -> forhåndsvisning (parse_kbhbrew_json,
     skriver ingenting) -> eksplisitt "Importer brygg" (kbhbrew_storage.
     importer_kbhbrew(), som selv håndhever duplikat-/DEMO_MODE-policy).
  3. render_kbhbrew_export_panel() -- kalles fra app.py under
     "🔧 Verktøy". Kilde er UTELUKKENDE hent_alle_brews() (den NYE Core
     V1-butikken) -- rører aldri recipes/_logs/ (legacy).

Ingen ny snapshot-/valideringslogikk bygges her -- alt kaller inn i den
eksisterende, testede motoren/lagringslaget. Rene formaterings-/
utvalgshjelpere (predicted-bygging, eksport-label/-filnavn) er flyttet
til modules/kbhbrew_ui.py, slik at de kan enhetstestes uten en
Streamlit-kontekst (se tests/test_kbhbrew_ui_helpers.py).
"""
import json

import streamlit as st

from config import DEMO_MODE
from modules.equipment import last_equipment
from modules.kbh_contract import UgyldigOppskriftForEksport
from modules.kbhbrew import UgyldigKbhbrewForImport, parse_kbhbrew_json
from modules.kbhbrew_storage import (
    eksporter_kbhbrew,
    hent_alle_brews,
    hent_brew,
    importer_kbhbrew,
    opprett_og_lagre_ny_brew,
)
from modules.kbhbrew_ui import (
    bygg_brew_eksport_filnavn,
    bygg_predicted_fra_ctx,
    sorter_brews_for_eksport,
)

_AKTIV_BREW_ID_NOKKEL = "_aktiv_kbhbrew_brew_id"
_IMPORT_FIL_ID_NOKKEL = "kbhbrew_import_preview_file_id"


def render_kbhbrew_create_panel(ctx, malt_database, humle_database, gjaer_database):
    """Ett eksplisitt "Start nytt brygg"-knappeklikk fryser `ctx["recipe"]`
    (allerede bygget av modules/recipe_context.py::bygg_recipe_context()
    for DENNE renderingen -- samme gjeldende oppskrift Bryggdag-fanen
    allerede viser) + gjeldende utstyrsprofil + predicted-verdier som et
    NYTT Core V1-brygg, via den eksisterende 3B1-lagringen. Skjules helt
    i DEMO_MODE (persistent skriving), samme mønster som "Lagre
    endringer"-seksjonen i ui/recipe_card.py.

    `brewId`-en til sist opprettede brygg beholdes i session_state
    (`_AKTIV_BREW_ID_NOKKEL`) KUN for å vise en vedvarende bekreftelse på
    tvers av senere reruns -- IKKE for å hindre et NYTT, eksplisitt klikk
    fra å opprette et NYTT batch (flere reelle brygg fra samme oppskrift
    er gyldig historikk, se issue). Selve dedupliseringen mot en
    utilsiktet Streamlit-rerun følger av at opprettelsen kun kan nås
    inne i `if st.button(...)`-blokken -- `st.button()` returnerer kun
    True i akkurat den kjøringen knappen faktisk ble trykket i."""
    if DEMO_MODE:
        return

    st.markdown("**🍺 Start nytt brygg (lagre historisk snapshot)**")
    st.caption(
        "Fryser gjeldende oppskrift, utstyrsprofil og spådde verdier som ET NYTT, "
        "historisk Core V1-brygg (.kbhbrew). Senere endringer i oppskrift/utstyr/"
        "masterdata påvirker ALDRI dette snapshotet igjen. Hvert klikk oppretter et "
        "NYTT batch — flere reelle brygg fra samme oppskrift er normalt."
    )
    if st.button("▶️ Start nytt brygg", key="kbhbrew_start_ny_brew_btn"):
        try:
            brew = opprett_og_lagre_ny_brew(
                ctx.get("recipe"), malt_database, humle_database, gjaer_database,
                last_equipment(), bygg_predicted_fra_ctx(ctx),
                recipe_id=st.session_state.get("_last_loaded_recipe_file"),
            )
        except UgyldigOppskriftForEksport as e:
            st.error(f"❌ Kunne ikke starte nytt brygg — oppskriften er ikke gyldig for eksport: {e}")
        else:
            st.session_state[_AKTIV_BREW_ID_NOKKEL] = brew["brewId"]
            st.toast(f"Nytt brygg startet: {brew['brewId']}", icon="🍺")

    aktiv_brew_id = st.session_state.get(_AKTIV_BREW_ID_NOKKEL)
    if aktiv_brew_id:
        aktiv_brew = hent_brew(aktiv_brew_id)
        if aktiv_brew is None:
            st.session_state.pop(_AKTIV_BREW_ID_NOKKEL, None)
        else:
            st.success(
                f"✅ Aktivt brygg denne økten: `{aktiv_brew_id}` · "
                f"opprettet {aktiv_brew.get('createdAt', '-')} · status **{aktiv_brew.get('status')}**"
            )


def render_kbhbrew_import_panel():
    """Trygg opplasting -> forhåndsvisning -> eksplisitt import, speiler
    det allerede etablerte .kbhrecipe-mønsteret i ui/sidebar.py.
    `kbhbrew_import_preview_tekst` bevarer den RÅ, allerede analyserte
    filteksten kun for å sende akkurat den samme teksten videre til
    `importer_kbhbrew()` ved bekreftelse -- forhåndsvisningen alene
    skriver aldri noe."""
    if DEMO_MODE:
        st.info("Import av .kbhbrew-filer er deaktivert i demo-modus.")
        return

    st.write("---")
    st.subheader("📦 Importer .kbhbrew-fil")
    st.caption(
        "Åpne en .kbhbrew-fil (Core V1 — et historisk brygg, IKKE en oppskrift). "
        "Importeres alltid som et HELT NYTT, lokalt brygg med sin egen, ferskt "
        "mintede identitet — ingenting skrives før du selv trykker «Importer brygg»."
    )

    kbhbrew_fil = st.file_uploader(
        "Velg .kbhbrew-fil", type=["kbhbrew"], key="kbhbrew_import_uploader",
        label_visibility="collapsed",
    )

    # Samme forsvar som ui/sidebar.py sin .kbhrecipe-import (Chief review-fiks
    # PR #5): enhver endring i opplasterens tilstand (ny/fjernet fil)
    # ugyldiggjør en gammel forhåndsvisning/feil FØR den i det hele tatt vurderes
    # vist under.
    _fil_id = getattr(kbhbrew_fil, "file_id", None) if kbhbrew_fil is not None else None
    if st.session_state.get(_IMPORT_FIL_ID_NOKKEL) != _fil_id:
        st.session_state.pop("kbhbrew_import_preview", None)
        st.session_state.pop("kbhbrew_import_preview_tekst", None)
        st.session_state.pop("kbhbrew_import_feil", None)
        st.session_state[_IMPORT_FIL_ID_NOKKEL] = _fil_id

    if st.button("🔍 Analyser .kbhbrew-fil", key="kbhbrew_analyser_btn"):
        if kbhbrew_fil is None:
            st.warning("Velg en fil først.")
        else:
            try:
                kbhbrew_tekst = kbhbrew_fil.getvalue().decode("utf-8")
            except UnicodeDecodeError:
                st.session_state["kbhbrew_import_preview"] = None
                st.session_state["kbhbrew_import_feil"] = "Filen er ikke gyldig UTF-8-tekst."
            else:
                try:
                    preview = parse_kbhbrew_json(kbhbrew_tekst)
                except UgyldigKbhbrewForImport as e:
                    st.session_state["kbhbrew_import_preview"] = None
                    st.session_state["kbhbrew_import_feil"] = e.melding
                else:
                    st.session_state["kbhbrew_import_preview"] = preview
                    st.session_state["kbhbrew_import_preview_tekst"] = kbhbrew_tekst
                    st.session_state["kbhbrew_import_feil"] = None

    kbhbrew_feil = st.session_state.get("kbhbrew_import_feil")
    if kbhbrew_feil:
        st.error(f"❌ {kbhbrew_feil}")

    preview = st.session_state.get("kbhbrew_import_preview")
    if preview:
        snapshot_recipe = (preview.get("snapshot") or {}).get("recipe") or {}
        st.markdown("**Forhåndsvisning:**")
        st.caption(f"📛 Oppskrift: **{snapshot_recipe.get('navn', '(ukjent)')}**")
        st.caption(f"📅 Opprettet: **{preview.get('createdAt', '-')}**")
        if preview.get("brewedAt"):
            st.caption(f"🍺 Brygget: **{preview['brewedAt']}**")
        st.caption(f"🏷️ Status: **{preview.get('status')}**")
        st.caption(f"🆔 Origin-ID: `{preview.get('originBrewId')}`")

        if st.button("✅ Importer brygg", key="kbhbrew_bekreft_btn"):
            resultat = importer_kbhbrew(st.session_state.get("kbhbrew_import_preview_tekst"))
            if resultat.get("duplicate"):
                st.warning(
                    f"⚠️ Dette brygget (origin-ID `{resultat['originBrewId']}`) "
                    "er allerede importert lokalt — ingenting ble skrevet."
                )
            elif resultat.get("ok"):
                st.success(f"✅ Importert som nytt lokalt brygg: `{resultat['brewId']}`")
                st.session_state.pop("kbhbrew_import_preview", None)
                st.session_state.pop("kbhbrew_import_preview_tekst", None)
                st.session_state.pop("kbhbrew_import_feil", None)
                st.session_state.pop(_IMPORT_FIL_ID_NOKKEL, None)


def render_kbhbrew_export_panel():
    """Kilde er UTELUKKENDE hent_alle_brews() (den NYE Core V1-butikken)
    -- rører ALDRI recipes/_logs/ (legacy, uendret via
    modules/recipe_storage.py). Selve nedlastingsknappen genererer kun
    innhold i minnet ved rendring (samme mønster som .kbhrecipe-eksporten
    i ui/recipe_card.py) -- ingen fil skrives til disk av at panelet
    rendres."""
    if DEMO_MODE:
        st.info("Eksport av .kbhbrew-filer er deaktivert i demo-modus.")
        return

    st.write("---")
    st.subheader("📥 Eksporter lagret .kbhbrew-brygg")
    brews = hent_alle_brews()
    if not brews:
        st.caption(
            "Ingen Core V1-brygg lagret lokalt ennå. Bruk «▶️ Start nytt brygg» i "
            "Bryggdag-fanen, eller importer en .kbhbrew-fil over."
        )
        return

    valg = sorter_brews_for_eksport(brews)
    etiketter = dict(valg)
    brew_id = st.selectbox(
        "Velg brygg", options=[bid for bid, _ in valg],
        format_func=lambda bid: etiketter[bid],
        key="kbhbrew_eksport_valgt_id",
    )
    if st.button("📦 Eksporter valgt brygg (.kbhbrew)", key="kbhbrew_eksport_btn"):
        try:
            konvolutt = eksporter_kbhbrew(brew_id)
        except ValueError as e:
            st.error(f"❌ Kunne ikke eksportere brygg: {e}")
        else:
            fil_navn = bygg_brew_eksport_filnavn(brews.get(brew_id), brew_id)
            st.download_button(
                label="📥 Last ned .kbhbrew",
                data=json.dumps(konvolutt, ensure_ascii=False, indent=2),
                file_name=fil_navn,
                mime="application/json",
                key="kbhbrew_eksport_last_ned_btn",
            )
