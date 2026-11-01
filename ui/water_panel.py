# ui/water_panel.py
"""
"💧 Vannkjemi" — HVILKET VANN ølet brygges med, helt adskilt fra
ingrediensoppskriften, prosessprofilen og utstyrsprofilen (se
modules/water_chemistry.py). Appen ANBEFALER, men endrer ALDRI vannplanen
uten et eksplisitt brukervalg — akkurat som ui/process_panel.py aldri
velger bryggemåte automatisk.
"""
import streamlit as st
from bryggeskole import pilot_raw_materials as _pilot_raavarer
from config import DEMO_MODE
from modules.equipment import last_equipment
from modules.brewday_calc import beregn_vann
from modules.process_profiles import normaliser_prosessprofil
from modules.water_chemistry import (
    IONER, alle_salter, hent_salt, beregn_saltbidrag,
    last_vannkilder, lagre_vannkilder, last_vannmaal, lagre_vannmaal,
    beregn_sluttprofil, fordel_alle_salter, bygg_ionrapport, cl_so4_forhold,
    generer_varsler, foreslaa_salter, anbefal_vannmaal, vurder_maaloppnaelse, bygg_syretilsetning, tomt_kildevann,
    PROPORSJONAL, ALT_I_MESK, EGENDEFINERT_FORDELING, SYRER,
    salt_navn as _salt_navn, salt_advarsler, syre_navn as _syre_navn, status_tekst,
    maalprofil_tekst, profiltype_tekst,
)
from ui import demo_state
from ui.i18n import gjeldende_sprak, t

def _demo_suffiks():
    return t("wp.demo_suffiks")


def _hent_vannkilder():
    return demo_state.hent_vannkilder() if DEMO_MODE else last_vannkilder()


def _lagre_vannkilder(kilder):
    if DEMO_MODE:
        demo_state.lagre_vannkilder(kilder)
    else:
        lagre_vannkilder(kilder)


def _hent_vannmaal():
    return demo_state.hent_vannmaal() if DEMO_MODE else last_vannmaal()


def _lagre_vannmaal(maalprofiler):
    if DEMO_MODE:
        demo_state.lagre_vannmaal(maalprofiler)
    else:
        lagre_vannmaal(maalprofiler)

_ION_LABELS = {"ca": "Ca", "mg": "Mg", "na": "Na", "cl": "Cl", "so4": "SO4", "hco3": "HCO3"}
_UKJENT_KILDE_ID = "__ukjent__"
_NY_KILDE_SENTINEL = "__ny_kilde__"

# Sjekklistepunktene vises via i18n-nøklene wp.utstyr.0..4 (#548).
_UTSTYR_SJEKKLISTE_ANTALL = 5

_VANN_WIDGET_PREFIKSER = (
    "vann_salt_id_", "vann_salt_gram_", "vann_salt_renhet_", "vann_salt_slett_", "vann_syre_",
)


def _ny_vann_widget_revisjon():
    """Samme mønster som ui/process_panel.py sin _ny_widget_revisjon(): et
    revisjonsnummer i widgetnøklene tvinger fram fysisk NYE widget-
    instanser når salt-/syrelistene byttes ut programmatisk (f.eks. etter
    «Beregn saltforslag» eller ved lasting av en annen oppskrift) — mer
    robust enn å stole utelukkende på eksplisitt sletting av nøkler."""
    st.session_state["_vann_widget_revisjon"] = st.session_state.get("_vann_widget_revisjon", 0) + 1
    for k in [k for k in st.session_state if k.startswith(_VANN_WIDGET_PREFIKSER)]:
        del st.session_state[k]
    return st.session_state["_vann_widget_revisjon"]


def _slug(navn):
    translitterert = navn.translate({ord('æ'): 'ae', ord('Æ'): 'Ae', ord('ø'): 'o', ord('Ø'): 'O', ord('å'): 'a', ord('Å'): 'A'})
    trygg = "".join(c for c in translitterert if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_").lower()
    return trygg or "kilde"


def _tom_kilde(navn, kilde_id):
    d = {"water_id": kilde_id, "name": navn, "location": "", "source_type": "ukjent", "source_year": None}
    d.update(tomt_kildevann())
    d["ph"] = None
    d["notes"] = "Ukjent — ingen analyse registrert ennå."
    d["is_default"] = False
    return d


def _init_kilde_widgets(kilde):
    for ion in IONER:
        st.session_state[f"vann_ion_{ion}_ukjent"] = kilde.get(ion) is None
        st.session_state[f"vann_ion_{ion}_verdi"] = float(kilde.get(ion) or 0.0)
    st.session_state["vann_kilde_navn_input"] = kilde.get("name", "")
    st.session_state["vann_kilde_lokasjon_input"] = kilde.get("location", "")
    st.session_state["vann_kilde_aar_input"] = int(kilde.get("source_year") or 0)
    st.session_state["vann_kilde_ph_ukjent"] = kilde.get("ph") is None
    st.session_state["vann_kilde_ph_input"] = float(kilde.get("ph") or 7.0)
    st.session_state["vann_kilde_notater_input"] = kilde.get("notes", "")


def _init_maal_widgets(maal):
    for ion in IONER:
        st.session_state[f"vann_maal_{ion}_min"] = float(maal.get(f"{ion}_min") or 0.0)
        st.session_state[f"vann_maal_{ion}_max"] = float(maal.get(f"{ion}_max") or 0.0)
    st.session_state["vann_maal_ph_min_input"] = float(maal.get("mash_ph_min") or 5.2)
    st.session_state["vann_maal_ph_max_input"] = float(maal.get("mash_ph_max") or 5.6)


def _ion_felt(kol, ion):
    with kol:
        ukjent = st.checkbox(t("wp.ion_ukjent", ion=_ION_LABELS[ion]), key=f"vann_ion_{ion}_ukjent")
        verdi = st.number_input(
            f"{_ION_LABELS[ion]} (ppm)", min_value=0.0, max_value=1000.0, step=0.1,
            key=f"vann_ion_{ion}_verdi", disabled=ukjent,
        )
    return None if ukjent else verdi


# V2.2 G3P-7 (issue #462): Learn -> Plan-bro som gjenbruker
# CHUNK-RAW-J/K fra den eksisterende, verifiserte Råvarer-piloten
# (bryggeskole.pilot_raw_materials) uendret -- ingen ny undervisningstekst
# forfattes her. Read-only, ingen mastery-kall, ingen ny lagringstilstand.
_LAER_BRO_CHUNK_IDER = ("CHUNK-RAW-J", "CHUNK-RAW-K")


def _render_laer_bro(sprak):
    """Kollapset Learn -> Plan-bro, rendret nøyaktig én gang per panel,
    før de avanserte vannkjemi-kontrollene. Ugyldig pilotinnhold
    (PilotContentError) skal aldri krasje Oppskrift-fanen."""
    with st.expander(t("raavarer.vann.laer_bro.tittel"), expanded=False):
        try:
            pilot = _pilot_raavarer.read_pilot_file()
            chunker = {c["id"]: c for c in pilot["chunks"]}
            tekster = [
                _pilot_raavarer.render_chunk(chunker[chunk_id], sprak)["text"]
                for chunk_id in _LAER_BRO_CHUNK_IDER
            ]
        except _pilot_raavarer.PilotContentError:
            st.error(t("bryggeskole.feil.innhold_ugyldig"))
            return
        for tekst in tekster:
            st.markdown(tekst)
        st.caption(t("raavarer.vann.laer_bro.footer"))


def render_water_panel(ctx, malt_database=None):
    sprak = gjeldende_sprak()
    st.subheader(t("wp.tittel"))
    _render_laer_bro(sprak)
    st.caption(t("wp.intro"))

    with st.expander(t("wp.hvorfor_tittel")):
        st.markdown(t("wp.hvorfor"))

    # ── Resync ved bytte av oppskrift ────────────────────────────────────
    # Samme mønster som ui/process_panel.py: panelets EGET utvalg må
    # resynkes fra den faktisk lastede oppskriftens lagrede vannfelter hver
    # gang en NY oppskrift blir aktiv — ellers overskriver panelet stille
    # det nettopp lastede med hva som helst som lå igjen i session_state.
    _aktiv_oppskrift = st.session_state.get("_last_loaded_recipe")
    _ny_oppskrift_lastet = st.session_state.get("_vann_synced_for", "__aldri_synket__") != _aktiv_oppskrift

    kilder = _hent_vannkilder()
    maalprofiler = _hent_vannmaal()

    if _ny_oppskrift_lastet:
        _lagret_kilde = st.session_state.get("_lastet_water_source_profile")
        _lagret_maal = st.session_state.get("_lastet_water_target_profile")
        _lagret_behandling = st.session_state.get("_lastet_water_treatment") or {}
        _lagret_maalinger = st.session_state.get("_lastet_water_measurements") or {}

        # Gamle oppskrifter uten vannprofil (eller helt nye oppskrifter)
        # faller BEVISST tilbake til "ukjent kilde" — Jordalsvatnet (eller
        # noen annen lagret kilde) settes ALDRI inn automatisk uten at
        # brukeren selv velger det i selectboxen.
        if _lagret_kilde and _lagret_kilde.get("water_id") in kilder:
            st.session_state["vann_kilde_valgt_id"] = _lagret_kilde["water_id"]
        elif _lagret_kilde:
            # Kilden lå snapshotet i oppskriften, men finnes ikke (lenger) i
            # kildedatabasen — bruk snapshotet direkte som en "løs" kilde.
            kilder[_lagret_kilde["water_id"]] = _lagret_kilde
            st.session_state["vann_kilde_valgt_id"] = _lagret_kilde["water_id"]
        else:
            st.session_state["vann_kilde_valgt_id"] = _UKJENT_KILDE_ID

        if _lagret_maal and _lagret_maal.get("target_id") in maalprofiler:
            st.session_state["vann_maal_valgt_id"] = _lagret_maal["target_id"]
        elif _lagret_maal:
            maalprofiler[_lagret_maal["target_id"]] = _lagret_maal
            st.session_state["vann_maal_valgt_id"] = _lagret_maal["target_id"]
        elif maalprofiler:
            st.session_state["vann_maal_valgt_id"] = next(iter(maalprofiler))

        st.session_state["vann_salter"] = [dict(s) for s in _lagret_behandling.get("salter", [])]
        st.session_state["vann_fordelingsmetode"] = _lagret_behandling.get("fordelingsmetode", PROPORSJONAL)
        st.session_state["vann_fordeling_egendefinert_andel"] = _lagret_behandling.get("egendefinert_meskeandel") or 0.5
        st.session_state["vann_syrer"] = [dict(s) for s in _lagret_maalinger.get("syrer", [])]
        st.session_state["vann_maalt_ph"] = float(_lagret_maalinger.get("maalt_mash_ph") or 0.0)
        st.session_state["vann_maaletid_min"] = int(_lagret_maalinger.get("maaletidspunkt_min") or 12)
        st.session_state["vann_maalt_romtemp"] = bool(_lagret_maalinger.get("malt_ved_romtemperatur", False))

        st.session_state["_vann_forrige_kilde_id"] = None  # tving re-init av kildefeltene under
        st.session_state["_vann_forrige_maal_id"] = None
        _ny_vann_widget_revisjon()
        st.session_state["_vann_synced_for"] = _aktiv_oppskrift

    # ── En "ventende" ny kilde (opprettet i FORRIGE kjøring) må appliseres
    # FØR selectboxen instansieres — samme Streamlit-begrensning som i
    # ui/process_panel.py (kan ikke skrive til en widgets nøkkel etter at
    # selve widgeten er opprettet i SAMME kjøring).
    _pending_ny_kilde_id = st.session_state.pop("_vann_pending_ny_kilde_id", None)
    if _pending_ny_kilde_id is not None:
        st.session_state["vann_kilde_valgt_id"] = _pending_ny_kilde_id

    # ══════════════════════════════════════════════════════════════════
    # VANNBEHANDLING (FORBEREDELSE) -- Brewday Tab UX Cleanup V1 (MUST 2):
    # kildevann, målprofil, vannmengder, saltforslag, fordeling,
    # forventet sluttprofil, varsler og syrer er alle
    # FORBEREDELSE/PLANLEGGING som normalt gjøres FØR selve bryggedagen --
    # lagt bak én lukket expander for å redusere støy i selve
    # bryggedagsverktøyet. Meske-pH (under) er BEVISST utenfor: en faktisk
    # målt verdi er relevant DER OG DA, under selve mesking. Ren
    # visuell/strukturell endring -- ALL beregning, alle session_state-
    # oppdateringer og selve snapshot-bygget under kjører nøyaktig som før,
    # uavhengig av om expanderen er åpen eller lukket.
    with st.expander(t("wp.vannbehandling_tittel"), expanded=False):
        # ══════════════════════════════════════════════════════════════════
        # KILDEVANN
        # ══════════════════════════════════════════════════════════════════
        st.markdown(t("wp.kildevann"))
        kilde_id_valg = [_UKJENT_KILDE_ID] + list(kilder.keys()) + [_NY_KILDE_SENTINEL]
        _kilde_navn = {**{kid: k["name"] for kid, k in kilder.items()},
                       _UKJENT_KILDE_ID: t("wp.ukjent_kildevann"), _NY_KILDE_SENTINEL: t("wp.ny_kilde_valg")}

        valgt_kilde_id = st.selectbox(
            t("wp.velg_kildevann"), options=kilde_id_valg,
            format_func=lambda k: _kilde_navn.get(k, k),
            key="vann_kilde_valgt_id",
        )

        if valgt_kilde_id == _NY_KILDE_SENTINEL:
            nytt_navn = st.text_input(t("wp.ny_kilde_navn"), key="vann_ny_kilde_navn", placeholder=t("wp.ny_kilde_placeholder"))
            if st.button(t("wp.opprett_kilde"), key="vann_opprett_kilde_btn") and nytt_navn.strip():
                ny_id = _slug(nytt_navn.strip())
                while ny_id in kilder:
                    ny_id += "_2"
                kilder[ny_id] = _tom_kilde(nytt_navn.strip(), ny_id)
                _lagre_vannkilder(kilder)
                st.session_state["_vann_pending_ny_kilde_id"] = ny_id
                melding = t("wp.opprettet_kilde", navn=nytt_navn.strip())
                if DEMO_MODE:
                    melding += _demo_suffiks()
                st.toast(melding, icon="💧")
                st.rerun()
            aktiv_kilde_full = _tom_kilde("(ny, ikke opprettet ennå)", _NY_KILDE_SENTINEL)
            aktiv_kilde_ioner = tomt_kildevann()
        elif valgt_kilde_id == _UKJENT_KILDE_ID:
            st.caption(t("wp.ingen_ionverdier"))
            aktiv_kilde_full = _tom_kilde("Ukjent kildevann", _UKJENT_KILDE_ID)
            aktiv_kilde_ioner = tomt_kildevann()
        else:
            if st.session_state.get("_vann_forrige_kilde_id") != valgt_kilde_id:
                _init_kilde_widgets(kilder[valgt_kilde_id])
                st.session_state["_vann_forrige_kilde_id"] = valgt_kilde_id

            with st.expander(t("wp.rediger_kilde"), expanded=False):
                m1, m2 = st.columns(2)
                with m1:
                    st.text_input(t("wp.navn"), key="vann_kilde_navn_input")
                    st.text_input(t("wp.sted"), key="vann_kilde_lokasjon_input")
                with m2:
                    st.number_input(t("wp.analyseaar"), min_value=0, max_value=2100, step=1, key="vann_kilde_aar_input")
                    ph_ukjent = st.checkbox(t("wp.ph_ukjent"), key="vann_kilde_ph_ukjent")
                    st.number_input(t("wp.ph"), min_value=0.0, max_value=14.0, step=0.1, key="vann_kilde_ph_input", disabled=ph_ukjent)

                ion_kols = st.columns(3)
                ioner_verdier = {}
                for i, ion in enumerate(IONER):
                    ioner_verdier[ion] = _ion_felt(ion_kols[i % 3], ion)

                st.text_area(t("wp.kilde_notater"), key="vann_kilde_notater_input", height=68)

                if st.button(t("wp.lagre_kilde"), key="vann_lagre_kilde_btn"):
                    kilder[valgt_kilde_id] = {
                        "water_id": valgt_kilde_id,
                        "name": st.session_state["vann_kilde_navn_input"] or valgt_kilde_id,
                        "location": st.session_state["vann_kilde_lokasjon_input"],
                        "source_type": kilder[valgt_kilde_id].get("source_type", "ukjent"),
                        "source_year": st.session_state["vann_kilde_aar_input"] or None,
                        **ioner_verdier,
                        "ph": None if ph_ukjent else st.session_state["vann_kilde_ph_input"],
                        "notes": st.session_state["vann_kilde_notater_input"],
                        "is_default": kilder[valgt_kilde_id].get("is_default", False),
                    }
                    _lagre_vannkilder(kilder)
                    st.toast(t("wp.kilde_lagret") + (_demo_suffiks() if DEMO_MODE else ""), icon="💾")

            aktiv_kilde_full = kilder[valgt_kilde_id]
            aktiv_kilde_ioner = {ion: aktiv_kilde_full.get(ion) for ion in IONER}

        # ══════════════════════════════════════════════════════════════════
        # MÅLPROFIL
        # ══════════════════════════════════════════════════════════════════
        st.markdown(t("wp.maalprofil"))
        st.caption(t("wp.maalprofil_forklaring"))
        if not maalprofiler:
            st.info(t("wp.ingen_maalprofiler"))
            aktiv_maal = None
        else:
            maal_id_valg = list(maalprofiler.keys())
            if st.session_state.get("vann_maal_valgt_id") not in maal_id_valg:
                st.session_state["vann_maal_valgt_id"] = maal_id_valg[0]

            stil_navn = (ctx.get("brygger_stil") or "").strip() or ctx.get("style_analysis", {}).get("stil", "")
            anbefalt_maal_id, maal_begrunnelse = anbefal_vannmaal(stil_navn, maalprofiler, sprak=sprak)
            if anbefalt_maal_id:
                anbefalt_maal_navn = (
                    maalprofil_tekst(maalprofiler[anbefalt_maal_id], "name", sprak) or anbefalt_maal_id
                )
                st.info(
                    t("wp.anbefalt_maal", navn=anbefalt_maal_navn) + "\n\n"
                    + "\n".join(f"- {b}" for b in maal_begrunnelse)
                )

            _anbefalt_suffiks = t("wp.anbefalt_suffiks")
            valgt_maal_id = st.selectbox(
                t("wp.velg_maal"),
                options=maal_id_valg,
                format_func=lambda k: (maalprofil_tekst(maalprofiler[k], "name", sprak) or k) + (_anbefalt_suffiks if k == anbefalt_maal_id else ""),
                key="vann_maal_valgt_id",
            )
            aktiv_maal_mal = maalprofiler[valgt_maal_id]

            # Kompakt hjelpetekst rett under valget — ALDRI en del av selve
            # navnet/dropdown-teksten (den skal forbli ryddig, se format_func
            # over) eller av eksportenes "Målprofil: <navn>"-linje. Faller
            # tilbake til den lengre beskrivelsen for profiler som mangler
            # den nye, korte teksten (f.eks. en eldre egendefinert profil).
            if aktiv_maal_mal.get("kort_hjelpetekst"):
                st.caption(maalprofil_tekst(aktiv_maal_mal, "kort_hjelpetekst", sprak))
            elif aktiv_maal_mal.get("description"):
                st.caption(maalprofil_tekst(aktiv_maal_mal, "description", sprak))

            if st.session_state.get("_vann_forrige_maal_id") != valgt_maal_id:
                _init_maal_widgets(aktiv_maal_mal)
                st.session_state["_vann_forrige_maal_id"] = valgt_maal_id

            with st.expander(t("wp.rediger_maal"), expanded=False):
                if aktiv_maal_mal.get("description"):
                    st.caption(maalprofil_tekst(aktiv_maal_mal, "description", sprak))
                _herkomst_deler = []
                if aktiv_maal_mal.get("origin"):
                    _herkomst_deler.append(t("wp.opprinnelse", x=maalprofil_tekst(aktiv_maal_mal, "origin", sprak)))
                if aktiv_maal_mal.get("profile_type"):
                    _herkomst_deler.append(t("wp.type", x=profiltype_tekst(aktiv_maal_mal['profile_type'], sprak)))
                if aktiv_maal_mal.get("historical_profile"):
                    _herkomst_deler.append(t("wp.historisk_profil"))
                if _herkomst_deler:
                    st.caption(" · ".join(_herkomst_deler))

                maal_verdier = {}
                for ion in IONER:
                    c1, c2 = st.columns(2)
                    maal_verdier[f"{ion}_min"] = c1.number_input(
                        t("wp.ion_min", ion=_ION_LABELS[ion]), min_value=0.0, max_value=1000.0, step=1.0,
                        key=f"vann_maal_{ion}_min",
                    )
                    maal_verdier[f"{ion}_max"] = c2.number_input(
                        t("wp.ion_maks", ion=_ION_LABELS[ion]), min_value=0.0, max_value=1000.0, step=1.0,
                        key=f"vann_maal_{ion}_max",
                    )
                c1, c2 = st.columns(2)
                maal_verdier["mash_ph_min"] = c1.number_input(t("wp.ph_min"), min_value=4.0, max_value=7.0, step=0.01, format="%.2f", key="vann_maal_ph_min_input")
                maal_verdier["mash_ph_max"] = c2.number_input(t("wp.ph_maks"), min_value=4.0, max_value=7.0, step=0.01, format="%.2f", key="vann_maal_ph_max_input")

                if st.button(t("wp.lagre_maal"), key="vann_lagre_maal_btn"):
                    maalprofiler[valgt_maal_id] = {
                        **aktiv_maal_mal, **maal_verdier,
                        "target_id": valgt_maal_id,
                        "name": aktiv_maal_mal.get("name", valgt_maal_id),
                    }
                    _lagre_vannmaal(maalprofiler)
                    st.toast(t("wp.maal_lagret") + (_demo_suffiks() if DEMO_MODE else ""), icon="💾")

            aktiv_maal = maalprofiler[valgt_maal_id]

        # ══════════════════════════════════════════════════════════════════
        # VANNMENGDER (fra bryggedagsplanen)
        # ══════════════════════════════════════════════════════════════════
        st.markdown(t("wp.vannmengder"))
        eq = last_equipment()
        total_malt_kg = sum(m.get("mengde", 0.0) for m in st.session_state.get("valgt_malt", []))
        _kandidat_prosess = st.session_state.get("aktiv_prosessprofil")
        prosess_profil = normaliser_prosessprofil(_kandidat_prosess) if _kandidat_prosess else None
        boil_min = (prosess_profil or {}).get("boil_minutes") or eq["default_boil_time_min"]
        sparge_method = (prosess_profil or {}).get("sparge_method")
        vann_est = beregn_vann(total_malt_kg, ctx["volum"], boil_min, eq, sparge_method=sparge_method)
        meskevann_l, skyllevann_l = vann_est["mash_vann_l"], vann_est["sparge_vann_l"]
        totalvann_l = meskevann_l + skyllevann_l

        # Full metric-visning (Meskevann/Skyllevann/Totalt) ligger prominent i
        # Bryggeplan (ui/brewday_panel.py, Steg 1) -- der tallene faktisk
        # brukes under selve bryggingen. Her, i forberedelsesdelen, holder en
        # kompakt tekstlinje -- beregn_vann()-kallet og alle tre variablene
        # over er UENDRET og brukes fortsatt videre av saltberegningen,
        # fordelingen mesk/skyll og snapshotene lenger ned.
        st.caption(t(
            "wp.vannmengder_linje", mesk=f"{meskevann_l:.1f}", skyll=f"{skyllevann_l:.1f}",
            total=f"{totalvann_l:.1f}",
        ))

        # ══════════════════════════════════════════════════════════════════
        # FORESLÅTTE SALTER
        # ══════════════════════════════════════════════════════════════════
        st.markdown(t("wp.salter_tittel"))
        # Water Recommendation Quality Audit V1 fant at et grønt/innenfor-treff
        # på HCO3 lett kan leses som "meske-pH er i orden", selv om appen aldri
        # regner ut meske-pH -- foreslaa_salter() løser kun Cl/SO4 og ser aldri
        # kornregningen. Én stille, alltid synlig setning her (ikke bare etter
        # klikk) rammer inn HELE seksjonen riktig, uten å gjøre selve forslaget
        # alarmerende -- det er fortsatt et brukbart førsteutkast.
        st.caption(t("wp.salter_forklaring"))
        if st.button(t("wp.beregn_forslag"), key="vann_beregn_forslag_btn", disabled=aktiv_maal is None):
            forslag, forklaring = foreslaa_salter(aktiv_kilde_ioner, aktiv_maal, totalvann_l, sprak=sprak)
            st.session_state["vann_salter"] = forslag
            _ny_vann_widget_revisjon()
            st.info(forklaring)
            st.toast(t("wp.forslag_toast"), icon="🧮")

        revisjon = st.session_state.get("_vann_widget_revisjon", 0)
        salt_liste = st.session_state.get("vann_salter", [])
        salt_valg = [s["salt_id"] for s in alle_salter()]
        salt_navn = {s["salt_id"]: f"{_salt_navn(s['salt_id'], sprak)} ({s['formel']})" for s in alle_salter()}

        slett_salt_idx = None
        for i, s in enumerate(salt_liste):
            c1, c2, c3, c4 = st.columns([2.2, 1, 1, 0.5])
            s["salt_id"] = c1.selectbox(
                t("wp.salt"), options=salt_valg, format_func=lambda k: salt_navn[k],
                index=salt_valg.index(s["salt_id"]) if s["salt_id"] in salt_valg else 0,
                key=f"vann_salt_id_{revisjon}_{i}", label_visibility="collapsed" if i else "visible",
            )
            s["gram"] = c2.number_input(
                t("wp.gram_totalt"), min_value=0.0, max_value=200.0, step=0.05, format="%.2f",
                value=float(s.get("gram", 0.0)), key=f"vann_salt_gram_{revisjon}_{i}",
                label_visibility="collapsed" if i else "visible",
            )
            s["renhet"] = c3.number_input(
                t("wp.renhet"), min_value=1.0, max_value=100.0, step=1.0,
                value=float(s.get("renhet", 1.0)) * 100.0, key=f"vann_salt_renhet_{revisjon}_{i}",
                label_visibility="collapsed" if i else "visible",
            ) / 100.0
            if c4.button("🗑️", key=f"vann_salt_slett_{revisjon}_{i}", help=t("wp.fjern_salt")):
                slett_salt_idx = i

        if slett_salt_idx is not None:
            salt_liste.pop(slett_salt_idx)
            _ny_vann_widget_revisjon()
            st.rerun()

        if st.button(t("wp.legg_til_salt"), key="vann_legg_til_salt_btn"):
            salt_liste.append({"salt_id": salt_valg[0], "gram": 0.0, "renhet": 1.0})
            _ny_vann_widget_revisjon()
            st.rerun()

        for salt in alle_salter():
            if salt["salt_id"] in {s["salt_id"] for s in salt_liste} and salt["advarsler"]:
                for a in salt_advarsler(salt["salt_id"], sprak):
                    st.caption(f"⚠️ {_salt_navn(salt['salt_id'], sprak)}: {a}")

        # ══════════════════════════════════════════════════════════════════
        # FORDELING MESK / SKYLLING
        # ══════════════════════════════════════════════════════════════════
        st.markdown(t("wp.fordeling_tittel"))
        _FORDELING_NAVN = {
            PROPORSJONAL: t("wp.fordeling.proporsjonal"),
            ALT_I_MESK: t("wp.fordeling.alt_i_mesk"),
            EGENDEFINERT_FORDELING: t("wp.fordeling.egendefinert"),
        }
        fordelingsmetode = st.selectbox(
            t("wp.fordelingsmetode"), options=[PROPORSJONAL, ALT_I_MESK, EGENDEFINERT_FORDELING],
            format_func=lambda k: _FORDELING_NAVN[k], key="vann_fordelingsmetode",
        )
        egendefinert_andel = None
        if fordelingsmetode == EGENDEFINERT_FORDELING:
            egendefinert_andel = st.slider(
                t("wp.fordeling_andel"), min_value=0.0, max_value=1.0, step=0.05,
                key="vann_fordeling_egendefinert_andel",
            )

        salt_fordelt = fordel_alle_salter(salt_liste, meskevann_l, skyllevann_l, metode=fordelingsmetode, egendefinert_meskeandel=egendefinert_andel)
        if salt_fordelt:
            header = t("wp.tabell_salt_header") + "\n|---|---|---|---|"
            rows = "\n".join(
                f"| {_salt_navn(s['salt_id'], sprak)} | {s['gram']:.2f} g | {s['gram_mesk']:.2f} g | {s['gram_skyll']:.2f} g |"
                for s in salt_fordelt
            )
            st.markdown(f"{header}\n{rows}")
        else:
            st.caption(t("wp.ingen_salter"))

        # ══════════════════════════════════════════════════════════════════
        # FORVENTET SLUTTPROFIL
        # ══════════════════════════════════════════════════════════════════
        st.markdown(t("wp.sluttprofil"))
        sluttprofil = beregn_sluttprofil(aktiv_kilde_ioner, salt_liste, totalvann_l)
        rapport = bygg_ionrapport(sluttprofil, aktiv_maal)
        _STATUS_IKON = {"innenfor": "✅", "under": "🔽", "over": "🔼", "ukjent": "❔"}

        # Overordnet måloppnåelse — MÅ vises tydelig og ALDRI kunne forveksles:
        # fullt oppnådd / delvis / uoppnåelig med de FAKTISK VALGTE saltene
        # (se modules/water_chemistry.py sin vurder_maaloppnaelse()). Ingen
        # automatisk syre-/fortynnings-/RO-korreksjon foreslås her i V1 — kun
        # tydelig informasjon om hva som IKKE er løst med gjeldende salgvalg.
        _MAALOPPNAELSE_IKON = {
            "full_match": "✅", "delvis_match": "🟡",
            "uoppnaelig_med_valgte_salter": "🔴", "ukjent": "❔",
        }
        maaloppnaelse = vurder_maaloppnaelse(sluttprofil, aktiv_maal, salt_liste)
        ikon, tekst = _MAALOPPNAELSE_IKON[maaloppnaelse["status"]], t(f"wp.mo.{maaloppnaelse['status']}")
        st.markdown(f"{ikon} **{tekst}**")
        if maaloppnaelse["avvik"]:
            for a in maaloppnaelse["avvik"]:
                merknad = (
                    t("wp.mo.merknad_kan")
                    if a["kan_justeres_med_valgte_salter"]
                    else t("wp.mo.merknad_kan_ikke")
                )
                st.caption(t(
                    "wp.mo.avvik_linje", ion=_ION_LABELS[a['ion']],
                    status=status_tekst(a['status'], sprak), merknad=merknad,
                ))

        def _f(v):
            return "—" if v is None else f"{v:.1f}"

        def _maal_str(r):
            if r["maal_min"] is None:
                return "—"
            return f"{r['maal_min']:.0f}–{r['maal_maks']:.0f}"

        header = t("wp.ionrapport_header") + "\n|---|---|---|---|---|---|"
        rows = "\n".join(
            f"| {_ION_LABELS[r['ion']]} | {_f(r['start'])} | {_f(r['tilfort'])} | {_f(r['slutt'])} | "
            f"{_maal_str(r)} | {_STATUS_IKON[r['status']]} {status_tekst(r['status'], sprak)} |"
            for r in rapport
        )
        st.markdown(f"{header}\n{rows}")

        forhold = cl_so4_forhold(sluttprofil["slutt"].get("cl"), sluttprofil["slutt"].get("so4"))
        fc1, fc2 = st.columns(2)
        fc1.metric(t("wp.klorid"), _f(sluttprofil["slutt"].get("cl")) + " ppm")
        fc2.metric(t("wp.sulfat"), _f(sluttprofil["slutt"].get("so4")) + " ppm")
        st.caption(
            (t("wp.forhold", x=f"{forhold:.2f}") if forhold else t("wp.forhold_ukjent"))
            + t("wp.forhold_note")
        )

        # ══════════════════════════════════════════════════════════════════
        # VARSLER
        # ══════════════════════════════════════════════════════════════════
        st.markdown(t("wp.varsler_tittel"))
        syrer = st.session_state.get("vann_syrer", [])
        varsler = generer_varsler(aktiv_kilde_ioner, aktiv_maal, sluttprofil, salt_fordelt, syrer=syrer, sprak=sprak)
        if varsler:
            for v in varsler:
                st.warning(f"⚠️ {v}")
        else:
            st.success(t("wp.ingen_varsler"))

        # ══════════════════════════════════════════════════════════════════
        # SYRER
        # ══════════════════════════════════════════════════════════════════
        st.markdown(t("wp.syrer_tittel"))
        syre_valg = list(SYRER.keys())
        slett_syre_idx = None
        for i, syre in enumerate(syrer):
            c1, c2, c3 = st.columns([1.5, 1, 1])
            syre["syre_id"] = c1.selectbox(
                t("wp.syre"), options=syre_valg, format_func=lambda k: _syre_navn(k, sprak),
                index=syre_valg.index(syre["syre_id"]) if syre["syre_id"] in syre_valg else 0,
                key=f"vann_syre_id_{revisjon}_{i}", label_visibility="collapsed" if i else "visible",
            )
            prosent = c2.number_input(
                t("wp.konsentrasjon"), min_value=0.0, max_value=100.0, step=1.0,
                value=float(syre.get("prosent") or 0.0), key=f"vann_syre_prosent_{revisjon}_{i}",
                label_visibility="collapsed" if i else "visible", help=t("wp.konsentrasjon_hjelp"),
            )
            syre["prosent"] = prosent or None
            syre["mengde_ml"] = c3.number_input(
                t("wp.mengde_ml"), min_value=0.0, max_value=200.0, step=0.5,
                value=float(syre.get("mengde_ml", 0.0)), key=f"vann_syre_ml_{revisjon}_{i}",
                label_visibility="collapsed" if i else "visible",
            )
            syre["navn"] = SYRER[syre["syre_id"]]["navn"]
            syre["formel"] = SYRER[syre["syre_id"]]["formel"]
            if st.button(t("wp.fjern_syre"), key=f"vann_syre_slett_{revisjon}_{i}"):
                slett_syre_idx = i

        if slett_syre_idx is not None:
            syrer.pop(slett_syre_idx)
            _ny_vann_widget_revisjon()
            st.rerun()

        if st.button(t("wp.legg_til_syre"), key="vann_legg_til_syre_btn"):
            syrer.append(bygg_syretilsetning(syre_valg[0]))
            _ny_vann_widget_revisjon()
            st.rerun()

    # ══════════════════════════════════════════════════════════════════
    # MÅLT MESKE-pH
    # ══════════════════════════════════════════════════════════════════
    st.markdown(t("wp.meske_ph_tittel"))
    if aktiv_maal and aktiv_maal.get("mash_ph_min") is not None:
        st.caption(t("wp.onsket_ph", x=f"{aktiv_maal['mash_ph_min']:.2f}–{aktiv_maal['mash_ph_max']:.2f}"))
    ph1, ph2, ph3 = st.columns(3)
    with ph1:
        st.number_input(
            t("wp.maalt_ph"), min_value=0.0, max_value=14.0, step=0.01, format="%.2f",
            key="vann_maalt_ph", help=t("wp.maalt_ph_hjelp"),
        )
    with ph2:
        st.number_input(
            t("wp.maaletid"), min_value=0, max_value=120, step=1,
            key="vann_maaletid_min", help=t("wp.maaletid_hjelp"),
        )
    with ph3:
        st.checkbox(t("wp.romtemp"), key="vann_maalt_romtemp")
    st.caption(t("wp.kilde_ph_advarsel"))

    with st.expander(t("wp.utstyr_tittel")):
        for i in range(_UTSTYR_SJEKKLISTE_ANTALL):
            st.write(f"- {t(f'wp.utstyr.{i}')}")
        st.caption(t("wp.utstyr_info"))

    # ══════════════════════════════════════════════════════════════════
    # BYGG AKTIV VANNBEHANDLING (lagres sammen med oppskriften)
    # ══════════════════════════════════════════════════════════════════
    salter_med_ionbidrag = [
        {
            **s,
            "navn": hent_salt(s["salt_id"])["navn"],
            "kjemisk_form": hent_salt(s["salt_id"])["formel"],
            "ionbidrag_ppm": beregn_saltbidrag(s["salt_id"], s["gram"], s.get("renhet"), totalvann_l),
        }
        for s in salt_fordelt
    ]

    aktiv_vannbehandling = {
        "vannkilde_id": None if valgt_kilde_id in (_UKJENT_KILDE_ID, _NY_KILDE_SENTINEL) else valgt_kilde_id,
        "fordelingsmetode": fordelingsmetode,
        "egendefinert_meskeandel": egendefinert_andel,
        "salter": salter_med_ionbidrag,
    }
    aktiv_vannmaalinger = {
        "maalt_mash_ph": st.session_state["vann_maalt_ph"] or None,
        "maaletidspunkt_min": st.session_state["vann_maaletid_min"],
        "malt_ved_romtemperatur": st.session_state["vann_maalt_romtemp"],
        "syrer": syrer,
    }

    st.session_state["aktiv_vannkilde_snapshot"] = aktiv_kilde_full
    st.session_state["aktiv_vannmaal_snapshot"] = aktiv_maal
    st.session_state["aktiv_vannbehandling"] = aktiv_vannbehandling
    st.session_state["aktiv_vannmaalinger"] = aktiv_vannmaalinger

    return {
        "water_source_profile": aktiv_kilde_full,
        "water_target_profile": aktiv_maal,
        "water_treatment": aktiv_vannbehandling,
        "water_measurements": aktiv_vannmaalinger,
    }
