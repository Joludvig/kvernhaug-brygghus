import streamlit as st
from modules.equipment import last_equipment
from modules.brewday_calc import beregn_vann
from modules.process_profiles import (
    tilgjengelige_profiler, hent_standardprofil, normaliser_prosessprofil,
    anbefal_prosess, sjekk_utstyrsbegrensninger,
    beregn_dekoksjon_uttak, beregn_reiterated_mash,
    INFUSJON, MASHOUT, DEKOKSJON_UTTAK, DEKOKSJON_RETUR,
    BATCH_SPARGE, NO_SPARGE, FLY_SPARGE, _SPARGE_NAVN,
)

_STEGTYPE_LABELS = {
    INFUSJON: "Infusjon", MASHOUT: "Mashout",
    DEKOKSJON_UTTAK: "Dekoksjon-uttak", DEKOKSJON_RETUR: "Dekoksjon-retur",
}
_STEGTYPE_KEYS = list(_STEGTYPE_LABELS.keys())
_SPARGE_KEYS = [BATCH_SPARGE, NO_SPARGE, FLY_SPARGE]


_ANDRE_PROFIL_WIDGET_NOKLER = [
    "prosess_boil_minutes_input", "prosess_sparge_method_input",
    "prosess_brukernotater_input", "prosess_dek_fra_input",
    "prosess_dek_til_input", "prosess_dek_koketid_input",
    "prosess_dek_auto", "prosess_dek_uttak_input", "prosess_mesk1_andel_input",
]

# Meskesteg-widgetnøklene bærer et REVISJONSNUMMER
# (_process_widget_revision). Dette gjør at et profilbytte/en reparasjon
# fysisk BYTTER UT widget-instansene (ny nøkkel = ny widget for
# Streamlit) i stedet for å stole utelukkende på at en eksplisitt
# slette-rutine har fjernet akkurat de gamle nøklene i tide — mer robust
# mot fremtidige hull i den logikken.
_MESKESTEG_WIDGET_PREFIKSER = ("mash_temp_", "mash_time_", "mash_type_", "mash_comment_", "mash_delete_")


def _fjern_meskesteg_widget_state():
    """Fjerner ALLE meskesteg-widgetnøkler, uansett revisjonsnummer — trygt
    siden de bygges opp igjen fra prosess_mash_steps rett etterpå."""
    for k in [k for k in st.session_state if k.startswith(_MESKESTEG_WIDGET_PREFIKSER)]:
        del st.session_state[k]


def _ny_widget_revisjon():
    """Bumper revisjonstelleren som inngår i meskesteg-widgetnøklene, og
    rydder samtidig bort de gamle nøklene. Kalles ved ETHVERT
    profilbytte/reparasjon/steg-tillegg/steg-sletting."""
    st.session_state["_process_widget_revision"] = st.session_state.get("_process_widget_revision", 0) + 1
    _fjern_meskesteg_widget_state()
    return st.session_state["_process_widget_revision"]


def _fjern_alle_profil_widget_state():
    """Fjerner widget-nøklene for koketid/skyllemetode/dekoksjon/
    dobbeltmesk/notater (samme Streamlit-gotcha som for meskestegene: en
    widgets egen lagrede verdi vinner over et nytt `value=` så lenge
    nøkkelen ikke slettes først). Meskesteg-widgetene håndteres separat
    via _ny_widget_revisjon()."""
    for k in _ANDRE_PROFIL_WIDGET_NOKLER:
        st.session_state.pop(k, None)


def _init_state_for_profile(profil):
    """(Re)initialiserer redigerbare felter i session_state fra en valgt
    profil — kalles KUN når profilvalget faktisk har endret seg (eller når
    en korrupt/inkonsistent kandidat er reparert), slik at brukerens egne
    redigeringer innenfor samme profil ikke overskrives ved hver rerun.

    Widgetene initialiseres HERFRA — fra den allerede normaliserte
    `profil["mash_steps"]` — ALDRI omvendt (widgetene skal aldri kunne
    skrive en gammel verdi tilbake OVER en nettopp normalisert profil)."""
    _ny_widget_revisjon()
    _fjern_alle_profil_widget_state()
    st.session_state["prosess_mash_steps"] = [dict(s) for s in profil["mash_steps"]]
    st.session_state["prosess_boil_minutes"] = profil["boil_minutes"]
    st.session_state["prosess_sparge_method"] = profil["sparge_method"]
    st.session_state["prosess_brukernotater"] = profil.get("brukernotater", "")

    dek = (profil.get("decoction_steps") or [None])[0]
    st.session_state["prosess_dek_uttak"] = dek["uttak_liter"] if dek else None
    st.session_state["prosess_dek_fra"] = dek["fra_temp_c"] if dek else 63.0
    st.session_state["prosess_dek_til"] = dek["til_temp_c"] if dek else 70.0
    st.session_state["prosess_dek_koketid"] = dek["koketid_min"] if dek else 12

    rm = profil.get("reiterated_mash")
    st.session_state["prosess_mesk1_andel"] = rm["mesk_1_andel"] if rm else 0.5


def _bygg_aktiv_profil(process_id, navn, mal):
    """Setter sammen den FULLSTENDIGE, aktive prosessprofilen fra gjeldende
    session_state — dette er objektet som lagres med oppskriften og brukes
    av bryggedagsplanen. Ingredienslisten (malt/humle/gjær) er aldri en del
    av dette objektet."""
    profil = {
        "process_id": process_id,
        "navn": navn,
        "beskrivelse": mal.get("beskrivelse", ""),
        "vanskelighetsgrad": mal.get("vanskelighetsgrad", "Middels"),
        # Uavhengig kopi — aldri samme listeobjekt som session_state
        # (som live-widgets fortsetter å mutere på senere reruns).
        "mash_steps": [dict(s) for s in st.session_state["prosess_mash_steps"]],
        "sparge_method": st.session_state["prosess_sparge_method"],
        "boil_minutes": st.session_state["prosess_boil_minutes"],
        "decoction_steps": None,
        "reiterated_mash": None,
        "anbefalte_stiler": mal.get("anbefalte_stiler", []),
        "utstyrsbegrensninger": mal.get("utstyrsbegrensninger", ""),
        "forventet_paavirkning": mal.get("forventet_paavirkning", ""),
        "ekstra_tid_min": mal.get("ekstra_tid_min", 0),
        "brukernotater": st.session_state["prosess_brukernotater"],
    }
    if process_id == "enkel_dekoksjon":
        profil["decoction_steps"] = [{
            "uttak_liter": st.session_state["prosess_dek_uttak"],
            "fra_temp_c": st.session_state["prosess_dek_fra"],
            "til_temp_c": st.session_state["prosess_dek_til"],
            "koketid_min": st.session_state["prosess_dek_koketid"],
            "kommentar": (mal.get("decoction_steps") or [{}])[0].get("kommentar", ""),
        }]
    if process_id == "reiterated_mash":
        profil["reiterated_mash"] = {"mesk_1_andel": st.session_state["prosess_mesk1_andel"]}
    return profil


def render_process_panel(ctx, malt_database=None):
    st.subheader("🧭 Bryggemåte")
    st.caption(
        "Prosessprofilen beskriver HVORDAN ølet meskes og kokes — helt "
        "adskilt fra oppskriften (malt/humle/gjær). Å bytte bryggemåte "
        "endrer aldri ingredienslisten."
    )

    eq = last_equipment()
    total_malt_kg = sum(m.get("mengde", 0.0) for m in st.session_state.get("valgt_malt", []))
    stil_navn = ctx.get("brygger_stil", "").strip() or ctx["style_analysis"].get("stil", "")

    historisk = st.checkbox(
        "Ønsker historisk autentisitet",
        key="prosess_historisk_autentisitet",
        help="Foretrekk historiske teknikker (f.eks. dekoksjon) der stilen støtter det.",
    )

    anbefalt_id, begrunnelse = anbefal_prosess(
        stil_navn, ctx["recipe"]["stats"], total_malt_kg, eq,
        historisk_autentisitet=historisk,
    )
    anbefalt_navn = hent_standardprofil(anbefalt_id)["navn"]
    st.info(f"💡 **Anbefalt bryggemåte: {anbefalt_navn}**\n\n" + "\n".join(f"- {b}" for b in begrunnelse))

    profiler = tilgjengelige_profiler()
    id_til_navn = {p["process_id"]: p["navn"] for p in profiler}
    valgbare_id = list(id_til_navn.keys())

    # Panelets EGET utvalg (valgt_prosess_id/prosess_mash_steps) må resynkes
    # fra den faktisk lastede oppskriftens aktiv_prosessprofil hver gang en
    # NY/ANNEN oppskrift blir aktiv — ellers overskriver panelet (som kun
    # oppdager bytter via SIN EGEN selectbox) stille den nettopp lastede
    # profilen med hva som helst som lå igjen i session_state fra FØR
    # (se ui/sidebar.py, som setter aktiv_prosessprofil direkte ved lasting
    # uten å gå via denne selectboxen).
    _aktiv_oppskrift = st.session_state.get("_last_loaded_recipe")
    _raa_kandidat = st.session_state.get("aktiv_prosessprofil")
    _ny_oppskrift_lastet = st.session_state.get("_prosess_synced_for", "__aldri_synket__") != _aktiv_oppskrift

    # Selv UTEN at en ny oppskrift er lastet, kan aktiv_prosessprofil ha
    # blitt korrigert et annet sted (f.eks. ui/brewday_panel.py sin egen
    # normalisering) — eller være en rest fra FØR denne rettelsen fantes —
    # uten at panelets EGNE bytte-triggere fikk vite om det. Sammenlign
    # kandidaten mot sin egen normaliserte form: widgetene skal ALDRI vise
    # noe annet enn det den normaliserte profilen faktisk sier.
    _krever_reparasjon = False
    if _raa_kandidat and not _ny_oppskrift_lastet:
        _normalisert_sjekk = normaliser_prosessprofil(_raa_kandidat)
        if _normalisert_sjekk.get("mash_steps") != _raa_kandidat.get("mash_steps"):
            _krever_reparasjon = True

    if _ny_oppskrift_lastet or _krever_reparasjon:
        if _raa_kandidat:
            # normaliser_prosessprofil() er DEN ENE, felles kilden for å
            # gjøre en aktiv kandidat trygg — se modules/process_profiles.py.
            # For en kjent standardprofil (Hochkurz osv.) returnerer den
            # ALLTID standardmalens egne, kanoniske meskesteg — aldri det
            # som måtte ligge i session_state/en lagret fil fra før.
            _normalisert = normaliser_prosessprofil(_raa_kandidat)
            _start_id = _normalisert.get("process_id", "enkel_infusjon")
            _init_state_for_profile(_normalisert)
        else:
            _start_id = anbefalt_id
            _init_state_for_profile(hent_standardprofil(anbefalt_id))
        st.session_state["valgt_prosess_id"] = _start_id
        st.session_state["_prosess_forrige_id"] = _start_id
        st.session_state["_prosess_synced_for"] = _aktiv_oppskrift
        st.session_state.pop("_prosess_egendefinert_navn", None)
        if _krever_reparasjon:
            st.toast(
                "En inkonsistent prosessprofil ble oppdaget og reparert til standardmalen.",
                icon="🛠️",
            )

    # En "ventende" forfremmelse til Egendefinert (satt av redigerings-
    # deteksjonen lenger ned, i FORRIGE rerun) MÅ appliseres HER — FØR
    # selectboxen under instansieres. Streamlit tillater ikke å skrive til
    # st.session_state["valgt_prosess_id"] etter at widgeten med den nøkkelen
    # allerede er opprettet i SAMME kjøring.
    _pending_navn = st.session_state.pop("_prosess_pending_egendefinert_navn", None)
    if _pending_navn is not None:
        st.session_state["valgt_prosess_id"] = "egendefinert"
        st.session_state["_prosess_forrige_id"] = "egendefinert"
        st.session_state["_prosess_egendefinert_navn"] = _pending_navn

    valgt_id = st.selectbox(
        "Velg bryggemåte (anbefalingen setter ALDRI valget automatisk — du må selv velge)",
        options=valgbare_id,
        format_func=lambda pid: id_til_navn[pid] + ("  ⭐ anbefalt" if pid == anbefalt_id else ""),
        key="valgt_prosess_id",
    )

    if st.session_state.get("_prosess_forrige_id") != valgt_id:
        _init_state_for_profile(hent_standardprofil(valgt_id))
        st.session_state["_prosess_forrige_id"] = valgt_id
        st.session_state.pop("_prosess_egendefinert_navn", None)

    mal = hent_standardprofil(valgt_id)
    navn_visning = st.session_state.get("_prosess_egendefinert_navn") or id_til_navn[valgt_id]

    info_col1, info_col2, info_col3 = st.columns(3)
    info_col1.metric("Vanskelighetsgrad", mal["vanskelighetsgrad"])
    info_col2.metric("Ekstra tidsbruk", f"+{mal['ekstra_tid_min']} min" if mal["ekstra_tid_min"] else "—")
    info_col3.metric("Skyllemetode", _SPARGE_NAVN.get(st.session_state["prosess_sparge_method"], "—"))

    if mal.get("beskrivelse"):
        st.caption(mal["beskrivelse"])
    if mal.get("utstyrsbegrensninger"):
        st.caption(f"⚙️ **Utstyr:** {mal['utstyrsbegrensninger']}")
    if mal.get("forventet_paavirkning"):
        st.caption(f"🧬 **Forventet påvirkning på kropp/utgjæring:** {mal['forventet_paavirkning']}")

    # ── Redigerbare meskesteg ────────────────────────────────────────────
    # Widgetnøklene bærer revisjonsnummeret (_process_widget_revision) —
    # se _ny_widget_revisjon(). Dette garanterer at widgetene ALLTID
    # rendres fra den (eventuelt nettopp reparerte) prosess_mash_steps satt
    # over, og aldri kan vise en fysisk gjenværende, gammel widget-verdi.
    revisjon = st.session_state.get("_process_widget_revision", 0)
    with st.expander("🌡️ Meskesteg (redigerbare)", expanded=True):
        steg_liste = st.session_state["prosess_mash_steps"]
        slett_indeks = None
        for i, steg in enumerate(steg_liste):
            c1, c2, c3, c4, c5 = st.columns([1, 1, 1.3, 2.2, 0.5])
            steg["temperatur"] = c1.number_input(
                "Temp (°C)", min_value=30.0, max_value=100.0, step=0.5,
                value=float(steg["temperatur"]), key=f"mash_temp_{revisjon}_{i}",
            )
            steg["varighet"] = c2.number_input(
                "Min", min_value=1, max_value=180, step=5,
                value=int(steg["varighet"]), key=f"mash_time_{revisjon}_{i}",
            )
            steg["stegtype"] = c3.selectbox(
                "Type", options=_STEGTYPE_KEYS,
                format_func=lambda k: _STEGTYPE_LABELS[k],
                index=_STEGTYPE_KEYS.index(steg["stegtype"]) if steg["stegtype"] in _STEGTYPE_KEYS else 0,
                key=f"mash_type_{revisjon}_{i}",
            )
            steg["kommentar"] = c4.text_input(
                "Kommentar", value=steg.get("kommentar", ""), key=f"mash_comment_{revisjon}_{i}",
            )
            if c5.button("🗑️", key=f"mash_delete_{revisjon}_{i}", help="Fjern steg"):
                slett_indeks = i

        if slett_indeks is not None and len(steg_liste) > 1:
            steg_liste.pop(slett_indeks)
            _ny_widget_revisjon()
            st.rerun()

        if st.button("➕ Legg til meskesteg", key="prosess_legg_til_steg"):
            steg_liste.append({"temperatur": 66.0, "varighet": 20, "stegtype": INFUSJON, "kommentar": ""})
            _ny_widget_revisjon()
            st.rerun()

    # ── Automatisk forfremmelse til Egendefinert ved redigering ─────────
    # Redigerer brukeren et meskesteg i en STANDARDPROFIL (uten å eksplisitt
    # velge "Egendefinert"), ville normaliser_prosessprofil() ved neste
    # reparasjon/bytte ellers overskrevet nettopp denne redigeringen
    # tilbake til standardmalen (standardprofiler er BEVISST alltid
    # kanoniske — se modules/process_profiles.py). Oppdages en avvikende
    # redigering, forfremmes profilen derfor til en Egendefinert-variant
    # ("Egendefinert – basert på X") slik at redigeringen bevares.
    if valgt_id != "egendefinert":
        _kanonisk_sammenlign = [
            (s["temperatur"], s["varighet"], s["stegtype"])
            for s in hent_standardprofil(valgt_id)["mash_steps"]
        ]
        _naavaerende_sammenlign = [
            (s["temperatur"], s["varighet"], s["stegtype"]) for s in steg_liste
        ]
        if _naavaerende_sammenlign != _kanonisk_sammenlign:
            # IKKE skriv til st.session_state["valgt_prosess_id"] her —
            # selectboxen med den nøkkelen er allerede instansiert denne
            # kjøringen. Legg igjen en "ventende" markør som appliseres
            # FØR selectboxen instansieres i NESTE kjøring (se toppen av
            # funksjonen).
            _nytt_navn = f"Egendefinert – basert på {navn_visning}"
            st.session_state["_prosess_pending_egendefinert_navn"] = _nytt_navn
            st.toast(
                f"Redigering oppdaget — byttet til «{_nytt_navn}» slik at endringene dine ikke overskrives.",
                icon="✏️",
            )
            st.rerun()

    st.session_state["prosess_boil_minutes"] = st.number_input(
        "Total koketid (min)",
        min_value=30, max_value=180, step=5,
        value=int(st.session_state["prosess_boil_minutes"]),
        key="prosess_boil_minutes_input",
    )
    st.session_state["prosess_sparge_method"] = st.selectbox(
        "Skyllemetode",
        options=_SPARGE_KEYS,
        format_func=lambda k: _SPARGE_NAVN[k],
        index=_SPARGE_KEYS.index(st.session_state["prosess_sparge_method"]),
        key="prosess_sparge_method_input",
    )

    # ── Dekoksjon ────────────────────────────────────────────────────────
    if valgt_id == "enkel_dekoksjon":
        with st.expander("🔥 Dekoksjonsdetaljer", expanded=True):
            vann_est = beregn_vann(total_malt_kg, ctx["volum"], st.session_state["prosess_boil_minutes"], eq,
                                    sparge_method=st.session_state["prosess_sparge_method"])
            d1, d2, d3 = st.columns(3)
            fra = d1.number_input("Fra temp (°C)", min_value=30.0, max_value=90.0, step=0.5,
                                   value=float(st.session_state["prosess_dek_fra"]), key="prosess_dek_fra_input")
            til = d2.number_input("Til temp (°C)", min_value=30.0, max_value=100.0, step=0.5,
                                   value=float(st.session_state["prosess_dek_til"]), key="prosess_dek_til_input")
            koketid_dek = d3.number_input("Koketid uttak (min)", min_value=5, max_value=30, step=1,
                                           value=int(st.session_state["prosess_dek_koketid"]), key="prosess_dek_koketid_input")
            st.session_state["prosess_dek_fra"] = fra
            st.session_state["prosess_dek_til"] = til
            st.session_state["prosess_dek_koketid"] = koketid_dek

            foreslatt = beregn_dekoksjon_uttak(vann_est["mash_vann_l"], fra, til)
            bruk_auto = st.checkbox("Bruk automatisk beregnet uttaksvolum", value=st.session_state["prosess_dek_uttak"] is None,
                                     key="prosess_dek_auto")
            if bruk_auto:
                st.session_state["prosess_dek_uttak"] = None
                st.metric("Foreslått uttaksvolum", f"{foreslatt:.2f} L")
            else:
                st.session_state["prosess_dek_uttak"] = st.number_input(
                    "Uttaksvolum (L) — overstyrt manuelt", min_value=0.0, max_value=50.0, step=0.5,
                    value=float(st.session_state["prosess_dek_uttak"] or foreslatt), key="prosess_dek_uttak_input",
                )

    # ── Reiterated mash ──────────────────────────────────────────────────
    if valgt_id == "reiterated_mash":
        with st.expander("🔁 Dobbelmesk — vann- og volumflyt", expanded=True):
            andel = st.slider(
                "Andel av maltmengden i mesk 1", min_value=0.1, max_value=0.9, step=0.05,
                value=float(st.session_state["prosess_mesk1_andel"]), key="prosess_mesk1_andel_input",
            )
            st.session_state["prosess_mesk1_andel"] = andel
            flyt = beregn_reiterated_mash(total_malt_kg, andel, eq)
            st.markdown(
                f"**Mesk 1:** {flyt['malt_1_kg']:.2f} kg malt + {flyt['vann_mesk_1_l']:.1f} L ferskt vann "
                f"→ **{flyt['vort_1_l']:.1f} L vørt**\n\n"
                f"**Mesk 2:** {flyt['malt_2_kg']:.2f} kg malt + {flyt['vann_mesk_2_l']:.1f} L "
                f"(= vørten fra mesk 1, IKKE ferskt vann) → **{flyt['vort_2_l']:.1f} L sluttvørt**"
            )
            for v in flyt["varsler"]:
                st.warning(v)

    # ── Utstyrsvarsler ───────────────────────────────────────────────────
    aktiv_profil = _bygg_aktiv_profil(valgt_id, navn_visning, mal)
    for varsel in sjekk_utstyrsbegrensninger(aktiv_profil, total_malt_kg, eq):
        st.warning(f"⚠️ {varsel}")

    st.session_state["prosess_brukernotater"] = st.text_area(
        "Egne notater om denne bryggemåten", value=st.session_state["prosess_brukernotater"],
        key="prosess_brukernotater_input", height=80,
    )
    aktiv_profil["brukernotater"] = st.session_state["prosess_brukernotater"]

    st.session_state["aktiv_prosessprofil"] = aktiv_profil
    return aktiv_profil
