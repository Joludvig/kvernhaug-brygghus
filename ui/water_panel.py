# ui/water_panel.py
"""
"💧 Vannkjemi" — HVILKET VANN ølet brygges med, helt adskilt fra
ingrediensoppskriften, prosessprofilen og utstyrsprofilen (se
modules/water_chemistry.py). Appen ANBEFALER, men endrer ALDRI vannplanen
uten et eksplisitt brukervalg — akkurat som ui/process_panel.py aldri
velger bryggemåte automatisk.
"""
import streamlit as st
from modules.equipment import last_equipment
from modules.brewday_calc import beregn_vann
from modules.process_profiles import normaliser_prosessprofil
from modules.water_chemistry import (
    IONER, alle_salter, hent_salt, beregn_saltbidrag,
    last_vannkilder, lagre_vannkilder, last_vannmaal, lagre_vannmaal,
    beregn_sluttprofil, fordel_alle_salter, bygg_ionrapport, cl_so4_forhold,
    generer_varsler, foreslaa_salter, anbefal_vannmaal, vurder_maaloppnaelse, bygg_syretilsetning, tomt_kildevann,
    PROPORSJONAL, ALT_I_MESK, EGENDEFINERT_FORDELING, SYRER,
)

_ION_LABELS = {"ca": "Ca", "mg": "Mg", "na": "Na", "cl": "Cl", "so4": "SO4", "hco3": "HCO3"}
_UKJENT_KILDE_ID = "__ukjent__"
_NY_KILDE_SENTINEL = "__ny_kilde__"

_UTSTYR_SJEKKLISTE = [
    "pH-meter kalibrert med pH 4,01 og 7,00 bufferløsning",
    "Oppbevaringsvæske til elektroden",
    "Vekt med minst 0,1 g oppløsning — helst 0,01 g for små tilsetninger",
    "Rent prøveglass",
    "Avkjøl pH-prøven til måletemperatur før avlesning",
]

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
        ukjent = st.checkbox(f"{_ION_LABELS[ion]} ukjent", key=f"vann_ion_{ion}_ukjent")
        verdi = st.number_input(
            f"{_ION_LABELS[ion]} (ppm)", min_value=0.0, max_value=1000.0, step=0.1,
            key=f"vann_ion_{ion}_verdi", disabled=ukjent,
        )
    return None if ukjent else verdi


def render_water_panel(ctx, malt_database=None):
    st.subheader("💧 Vannkjemi")
    st.caption(
        "Vannbehandlingen beskriver HVILKET VANN ølet brygges med og "
        "hvordan det justeres med salter/syrer — helt adskilt fra "
        "oppskriften, bryggemåten og utstyrsprofilen. Appen anbefaler, men "
        "endrer aldri vannplanen uten at du selv velger det."
    )

    # ── Resync ved bytte av oppskrift ────────────────────────────────────
    # Samme mønster som ui/process_panel.py: panelets EGET utvalg må
    # resynkes fra den faktisk lastede oppskriftens lagrede vannfelter hver
    # gang en NY oppskrift blir aktiv — ellers overskriver panelet stille
    # det nettopp lastede med hva som helst som lå igjen i session_state.
    _aktiv_oppskrift = st.session_state.get("_last_loaded_recipe")
    _ny_oppskrift_lastet = st.session_state.get("_vann_synced_for", "__aldri_synket__") != _aktiv_oppskrift

    kilder = last_vannkilder()
    maalprofiler = last_vannmaal()

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
    # 1. KILDEVANN
    # ══════════════════════════════════════════════════════════════════
    st.markdown("**1. Kildevann**")
    kilde_id_valg = [_UKJENT_KILDE_ID] + list(kilder.keys()) + [_NY_KILDE_SENTINEL]
    _kilde_navn = {**{kid: k["name"] for kid, k in kilder.items()},
                   _UKJENT_KILDE_ID: "❓ Ukjent kildevann", _NY_KILDE_SENTINEL: "➕ Ny egendefinert kilde …"}

    valgt_kilde_id = st.selectbox(
        "Velg kildevann", options=kilde_id_valg,
        format_func=lambda k: _kilde_navn.get(k, k),
        key="vann_kilde_valgt_id",
    )

    if valgt_kilde_id == _NY_KILDE_SENTINEL:
        nytt_navn = st.text_input("Navn på ny kilde", key="vann_ny_kilde_navn", placeholder="f.eks. Egen brønn 2026")
        if st.button("➕ Opprett kilde", key="vann_opprett_kilde_btn") and nytt_navn.strip():
            ny_id = _slug(nytt_navn.strip())
            while ny_id in kilder:
                ny_id += "_2"
            kilder[ny_id] = _tom_kilde(nytt_navn.strip(), ny_id)
            lagre_vannkilder(kilder)
            st.session_state["_vann_pending_ny_kilde_id"] = ny_id
            st.toast(f"Opprettet kilde «{nytt_navn.strip()}» — fyll inn ionverdier under.", icon="💧")
            st.rerun()
        aktiv_kilde_full = _tom_kilde("(ny, ikke opprettet ennå)", _NY_KILDE_SENTINEL)
        aktiv_kilde_ioner = tomt_kildevann()
    elif valgt_kilde_id == _UKJENT_KILDE_ID:
        st.caption("Ingen ionverdier registrert — appen dikter ikke opp tall for en ukjent kilde.")
        aktiv_kilde_full = _tom_kilde("Ukjent kildevann", _UKJENT_KILDE_ID)
        aktiv_kilde_ioner = tomt_kildevann()
    else:
        if st.session_state.get("_vann_forrige_kilde_id") != valgt_kilde_id:
            _init_kilde_widgets(kilder[valgt_kilde_id])
            st.session_state["_vann_forrige_kilde_id"] = valgt_kilde_id

        with st.expander("🔬 Rediger kildeprofil", expanded=False):
            m1, m2 = st.columns(2)
            with m1:
                st.text_input("Navn", key="vann_kilde_navn_input")
                st.text_input("Sted/lokasjon", key="vann_kilde_lokasjon_input")
            with m2:
                st.number_input("Analyseår", min_value=0, max_value=2100, step=1, key="vann_kilde_aar_input")
                ph_ukjent = st.checkbox("pH ukjent", key="vann_kilde_ph_ukjent")
                st.number_input("pH", min_value=0.0, max_value=14.0, step=0.1, key="vann_kilde_ph_input", disabled=ph_ukjent)

            ion_kols = st.columns(3)
            ioner_verdier = {}
            for i, ion in enumerate(IONER):
                ioner_verdier[ion] = _ion_felt(ion_kols[i % 3], ion)

            st.text_area("Notater (laboratorium/kilde, måletype osv.)", key="vann_kilde_notater_input", height=68)

            if st.button("💾 Lagre denne kildeprofilen", key="vann_lagre_kilde_btn"):
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
                lagre_vannkilder(kilder)
                st.toast("Kildeprofil lagret!", icon="💾")

        aktiv_kilde_full = kilder[valgt_kilde_id]
        aktiv_kilde_ioner = {ion: aktiv_kilde_full.get(ion) for ion in IONER}

    # ══════════════════════════════════════════════════════════════════
    # 2. MÅLPROFIL
    # ══════════════════════════════════════════════════════════════════
    st.markdown("**2. Målprofil**")
    st.caption(
        "Målprofilen er en HELT ANNEN ting enn kildevannet over — kildevannet "
        "er hva som faktisk kommer ut av springen/brønnen din, målprofilen er "
        "hva du ØNSKER å oppnå etter salttilsetning. Jordalsvatnet 2025 er "
        "aldri et valg her, kun under «1. Kildevann»."
    )
    if not maalprofiler:
        st.info("Ingen målprofiler er lagret ennå.")
        aktiv_maal = None
    else:
        maal_id_valg = list(maalprofiler.keys())
        if st.session_state.get("vann_maal_valgt_id") not in maal_id_valg:
            st.session_state["vann_maal_valgt_id"] = maal_id_valg[0]

        stil_navn = (ctx.get("brygger_stil") or "").strip() or ctx.get("style_analysis", {}).get("stil", "")
        anbefalt_maal_id, maal_begrunnelse = anbefal_vannmaal(stil_navn, maalprofiler)
        if anbefalt_maal_id:
            anbefalt_maal_navn = maalprofiler[anbefalt_maal_id].get("name", anbefalt_maal_id)
            st.info(
                f"💡 **Anbefalt målprofil: {anbefalt_maal_navn}**\n\n"
                + "\n".join(f"- {b}" for b in maal_begrunnelse)
            )

        valgt_maal_id = st.selectbox(
            "Velg målprofil (anbefalingen setter ALDRI valget automatisk — du må selv velge)",
            options=maal_id_valg,
            format_func=lambda k: maalprofiler[k].get("name", k) + ("  ⭐ anbefalt" if k == anbefalt_maal_id else ""),
            key="vann_maal_valgt_id",
        )
        aktiv_maal_mal = maalprofiler[valgt_maal_id]

        # Kompakt hjelpetekst rett under valget — ALDRI en del av selve
        # navnet/dropdown-teksten (den skal forbli ryddig, se format_func
        # over) eller av eksportenes "Målprofil: <navn>"-linje. Faller
        # tilbake til den lengre beskrivelsen for profiler som mangler
        # den nye, korte teksten (f.eks. en eldre egendefinert profil).
        if aktiv_maal_mal.get("kort_hjelpetekst"):
            st.caption(aktiv_maal_mal["kort_hjelpetekst"])
        elif aktiv_maal_mal.get("description"):
            st.caption(aktiv_maal_mal["description"])

        if st.session_state.get("_vann_forrige_maal_id") != valgt_maal_id:
            _init_maal_widgets(aktiv_maal_mal)
            st.session_state["_vann_forrige_maal_id"] = valgt_maal_id

        with st.expander("🎯 Rediger målprofil (min/maks per ion)", expanded=False):
            if aktiv_maal_mal.get("description"):
                st.caption(aktiv_maal_mal["description"])
            _herkomst_deler = []
            if aktiv_maal_mal.get("origin"):
                _herkomst_deler.append(f"Opprinnelse: {aktiv_maal_mal['origin']}")
            if aktiv_maal_mal.get("profile_type"):
                _herkomst_deler.append(f"Type: {aktiv_maal_mal['profile_type']}")
            if aktiv_maal_mal.get("historical_profile"):
                _herkomst_deler.append("Historisk profil")
            if _herkomst_deler:
                st.caption(" · ".join(_herkomst_deler))

            maal_verdier = {}
            for ion in IONER:
                c1, c2 = st.columns(2)
                maal_verdier[f"{ion}_min"] = c1.number_input(
                    f"{_ION_LABELS[ion]} min (ppm)", min_value=0.0, max_value=1000.0, step=1.0,
                    key=f"vann_maal_{ion}_min",
                )
                maal_verdier[f"{ion}_max"] = c2.number_input(
                    f"{_ION_LABELS[ion]} maks (ppm)", min_value=0.0, max_value=1000.0, step=1.0,
                    key=f"vann_maal_{ion}_max",
                )
            c1, c2 = st.columns(2)
            maal_verdier["mash_ph_min"] = c1.number_input("Meske-pH min", min_value=4.0, max_value=7.0, step=0.01, format="%.2f", key="vann_maal_ph_min_input")
            maal_verdier["mash_ph_max"] = c2.number_input("Meske-pH maks", min_value=4.0, max_value=7.0, step=0.01, format="%.2f", key="vann_maal_ph_max_input")

            if st.button("💾 Lagre målprofil", key="vann_lagre_maal_btn"):
                maalprofiler[valgt_maal_id] = {
                    **aktiv_maal_mal, **maal_verdier,
                    "target_id": valgt_maal_id,
                    "name": aktiv_maal_mal.get("name", valgt_maal_id),
                }
                lagre_vannmaal(maalprofiler)
                st.toast("Målprofil lagret!", icon="💾")

        aktiv_maal = maalprofiler[valgt_maal_id]

    # ══════════════════════════════════════════════════════════════════
    # 3. VANNMENGDER (fra bryggedagsplanen)
    # ══════════════════════════════════════════════════════════════════
    st.markdown("**3. Vannmengder (fra bryggedagsplanen)**")
    eq = last_equipment()
    total_malt_kg = sum(m.get("mengde", 0.0) for m in st.session_state.get("valgt_malt", []))
    _kandidat_prosess = st.session_state.get("aktiv_prosessprofil")
    prosess_profil = normaliser_prosessprofil(_kandidat_prosess) if _kandidat_prosess else None
    boil_min = (prosess_profil or {}).get("boil_minutes") or eq["default_boil_time_min"]
    sparge_method = (prosess_profil or {}).get("sparge_method")
    vann_est = beregn_vann(total_malt_kg, ctx["volum"], boil_min, eq, sparge_method=sparge_method)
    meskevann_l, skyllevann_l = vann_est["mash_vann_l"], vann_est["sparge_vann_l"]

    vc1, vc2, vc3 = st.columns(3)
    vc1.metric("Meskevann", f"{meskevann_l:.1f} L")
    vc2.metric("Skyllevann", f"{skyllevann_l:.1f} L")
    vc3.metric("Totalt", f"{meskevann_l + skyllevann_l:.1f} L")
    totalvann_l = meskevann_l + skyllevann_l

    # ══════════════════════════════════════════════════════════════════
    # 4. FORESLÅTTE SALTER
    # ══════════════════════════════════════════════════════════════════
    st.markdown("**4. Foreslåtte salter**")
    if st.button("🧮 Beregn saltforslag", key="vann_beregn_forslag_btn", disabled=aktiv_maal is None):
        forslag, forklaring = foreslaa_salter(aktiv_kilde_ioner, aktiv_maal, totalvann_l)
        st.session_state["vann_salter"] = forslag
        _ny_vann_widget_revisjon()
        st.info(forklaring)
        st.toast("Saltforslag beregnet — fritt redigerbart under.", icon="🧮")

    revisjon = st.session_state.get("_vann_widget_revisjon", 0)
    salt_liste = st.session_state.get("vann_salter", [])
    salt_valg = [s["salt_id"] for s in alle_salter()]
    salt_navn = {s["salt_id"]: f"{s['navn']} ({s['formel']})" for s in alle_salter()}

    slett_salt_idx = None
    for i, s in enumerate(salt_liste):
        c1, c2, c3, c4 = st.columns([2.2, 1, 1, 0.5])
        s["salt_id"] = c1.selectbox(
            "Salt", options=salt_valg, format_func=lambda k: salt_navn[k],
            index=salt_valg.index(s["salt_id"]) if s["salt_id"] in salt_valg else 0,
            key=f"vann_salt_id_{revisjon}_{i}", label_visibility="collapsed" if i else "visible",
        )
        s["gram"] = c2.number_input(
            "Gram (totalt)", min_value=0.0, max_value=200.0, step=0.05, format="%.2f",
            value=float(s.get("gram", 0.0)), key=f"vann_salt_gram_{revisjon}_{i}",
            label_visibility="collapsed" if i else "visible",
        )
        s["renhet"] = c3.number_input(
            "Renhet (%)", min_value=1.0, max_value=100.0, step=1.0,
            value=float(s.get("renhet", 1.0)) * 100.0, key=f"vann_salt_renhet_{revisjon}_{i}",
            label_visibility="collapsed" if i else "visible",
        ) / 100.0
        if c4.button("🗑️", key=f"vann_salt_slett_{revisjon}_{i}", help="Fjern salt"):
            slett_salt_idx = i

    if slett_salt_idx is not None:
        salt_liste.pop(slett_salt_idx)
        _ny_vann_widget_revisjon()
        st.rerun()

    if st.button("➕ Legg til salt manuelt", key="vann_legg_til_salt_btn"):
        salt_liste.append({"salt_id": salt_valg[0], "gram": 0.0, "renhet": 1.0})
        _ny_vann_widget_revisjon()
        st.rerun()

    for salt in alle_salter():
        if salt["salt_id"] in {s["salt_id"] for s in salt_liste} and salt["advarsler"]:
            for a in salt["advarsler"]:
                st.caption(f"⚠️ {salt['navn']}: {a}")

    # ══════════════════════════════════════════════════════════════════
    # 5. FORDELING MESK / SKYLLING
    # ══════════════════════════════════════════════════════════════════
    st.markdown("**5. Fordeling mellom meske- og skyllevann**")
    _FORDELING_NAVN = {
        PROPORSJONAL: "Proporsjonalt (etter vannmengde)",
        ALT_I_MESK: "Alt i meskevannet",
        EGENDEFINERT_FORDELING: "Egendefinert andel",
    }
    fordelingsmetode = st.selectbox(
        "Fordelingsmetode", options=[PROPORSJONAL, ALT_I_MESK, EGENDEFINERT_FORDELING],
        format_func=lambda k: _FORDELING_NAVN[k], key="vann_fordelingsmetode",
    )
    egendefinert_andel = None
    if fordelingsmetode == EGENDEFINERT_FORDELING:
        egendefinert_andel = st.slider(
            "Andel av hvert salt i meskevannet", min_value=0.0, max_value=1.0, step=0.05,
            key="vann_fordeling_egendefinert_andel",
        )

    salt_fordelt = fordel_alle_salter(salt_liste, meskevann_l, skyllevann_l, metode=fordelingsmetode, egendefinert_meskeandel=egendefinert_andel)
    if salt_fordelt:
        header = "| Salt | Totalt | Meskevann | Skyllevann |\n|---|---|---|---|"
        rows = "\n".join(
            f"| {hent_salt(s['salt_id'])['navn']} | {s['gram']:.2f} g | {s['gram_mesk']:.2f} g | {s['gram_skyll']:.2f} g |"
            for s in salt_fordelt
        )
        st.markdown(f"{header}\n{rows}")
    else:
        st.caption("Ingen salter lagt til ennå.")

    # ══════════════════════════════════════════════════════════════════
    # 6. FORVENTET SLUTTPROFIL
    # ══════════════════════════════════════════════════════════════════
    st.markdown("**6. Forventet sluttprofil**")
    sluttprofil = beregn_sluttprofil(aktiv_kilde_ioner, salt_liste, totalvann_l)
    rapport = bygg_ionrapport(sluttprofil, aktiv_maal)
    _STATUS_IKON = {"innenfor": "✅", "under": "🔽", "over": "🔼", "ukjent": "❔"}

    # Overordnet måloppnåelse — MÅ vises tydelig og ALDRI kunne forveksles:
    # fullt oppnådd / delvis / uoppnåelig med de FAKTISK VALGTE saltene
    # (se modules/water_chemistry.py sin vurder_maaloppnaelse()). Ingen
    # automatisk syre-/fortynnings-/RO-korreksjon foreslås her i V1 — kun
    # tydelig informasjon om hva som IKKE er løst med gjeldende salgvalg.
    _MAALOPPNAELSE_VISNING = {
        "full_match": ("✅", "Målprofilen er fullt oppnådd med de valgte saltene."),
        "delvis_match": ("🟡", "Delvis måloppnåelse — noen ioner er utenfor, men kan justeres ved å endre mengden av de valgte saltene."),
        "uoppnaelig_med_valgte_salter": ("🔴", "Målprofilen kan IKKE nås fullt ut med de valgte saltene alene."),
        "ukjent": ("❔", "Ingen målprofil valgt — måloppnåelse kan ikke vurderes."),
    }
    maaloppnaelse = vurder_maaloppnaelse(sluttprofil, aktiv_maal, salt_liste)
    ikon, tekst = _MAALOPPNAELSE_VISNING[maaloppnaelse["status"]]
    st.markdown(f"{ikon} **{tekst}**")
    if maaloppnaelse["avvik"]:
        for a in maaloppnaelse["avvik"]:
            merknad = (
                "kan justeres med et av de valgte saltene"
                if a["kan_justeres_med_valgte_salter"]
                else "IKKE oppnåelig med de valgte saltene (krever andre salter, eller kildevannet er allerede utenfor i en retning salter ikke kan rette)"
            )
            st.caption(f"– {_ION_LABELS[a['ion']]}: {a['status']} målområdet — {merknad}.")

    def _f(v):
        return "—" if v is None else f"{v:.1f}"

    def _maal_str(r):
        if r["maal_min"] is None:
            return "—"
        return f"{r['maal_min']:.0f}–{r['maal_maks']:.0f}"

    header = "| Ion | Start | Tilført | Ferdig | Mål | Status |\n|---|---|---|---|---|---|"
    rows = "\n".join(
        f"| {_ION_LABELS[r['ion']]} | {_f(r['start'])} | {_f(r['tilfort'])} | {_f(r['slutt'])} | "
        f"{_maal_str(r)} | {_STATUS_IKON[r['status']]} {r['status']} |"
        for r in rapport
    )
    st.markdown(f"{header}\n{rows}")

    forhold = cl_so4_forhold(sluttprofil["slutt"].get("cl"), sluttprofil["slutt"].get("so4"))
    fc1, fc2 = st.columns(2)
    fc1.metric("Klorid (Cl)", _f(sluttprofil["slutt"].get("cl")) + " ppm")
    fc2.metric("Sulfat (SO4)", _f(sluttprofil["slutt"].get("so4")) + " ppm")
    st.caption(
        f"Cl:SO4-forhold ≈ {forhold:.2f}" if forhold else "Cl:SO4-forhold: —"
        " — kun en referanse, ikke det eneste kvalitetsmålet. Se de absolutte ionnivåene over."
    )

    # ══════════════════════════════════════════════════════════════════
    # 7. VARSLER
    # ══════════════════════════════════════════════════════════════════
    st.markdown("**7. Varsler**")
    syrer = st.session_state.get("vann_syrer", [])
    varsler = generer_varsler(aktiv_kilde_ioner, aktiv_maal, sluttprofil, salt_fordelt, syrer=syrer)
    if varsler:
        for v in varsler:
            st.warning(f"⚠️ {v}")
    else:
        st.success("Ingen varsler.")

    # ══════════════════════════════════════════════════════════════════
    # 8. MÅLT MESKE-pH
    # ══════════════════════════════════════════════════════════════════
    st.markdown("**8. Meske-pH**")
    if aktiv_maal and aktiv_maal.get("mash_ph_min") is not None:
        st.caption(f"🎯 Ønsket meske-pH: **{aktiv_maal['mash_ph_min']:.2f}–{aktiv_maal['mash_ph_max']:.2f}**")
    ph1, ph2, ph3 = st.columns(3)
    with ph1:
        st.number_input(
            "Faktisk målt meske-pH", min_value=0.0, max_value=14.0, step=0.01, format="%.2f",
            key="vann_maalt_ph", help="0.00 = ikke målt ennå.",
        )
    with ph2:
        st.number_input(
            "Måletidspunkt (min etter innmesk)", min_value=0, max_value=120, step=1,
            key="vann_maaletid_min", help="Standard: 10–15 minutter etter innmesk.",
        )
    with ph3:
        st.checkbox("Prøven avkjølt til romtemperatur før måling", key="vann_maalt_romtemp")
    st.caption(
        "Vannets kildepH brukes ALDRI alene til å forutsi meske-pH — dette "
        "feltet registrerer kun en faktisk, egen måling."
    )

    with st.expander("🧰 Utstyr og måling (sjekkliste)"):
        for item in _UTSTYR_SJEKKLISTE:
            st.write(f"- {item}")
        st.caption("Informasjonstekst, ikke produktanbefaling.")

    # ══════════════════════════════════════════════════════════════════
    # 9. SYRER
    # ══════════════════════════════════════════════════════════════════
    st.markdown("**9. Syrer**")
    syre_valg = list(SYRER.keys())
    slett_syre_idx = None
    for i, syre in enumerate(syrer):
        c1, c2, c3 = st.columns([1.5, 1, 1])
        syre["syre_id"] = c1.selectbox(
            "Syre", options=syre_valg, format_func=lambda k: SYRER[k]["navn"],
            index=syre_valg.index(syre["syre_id"]) if syre["syre_id"] in syre_valg else 0,
            key=f"vann_syre_id_{revisjon}_{i}", label_visibility="collapsed" if i else "visible",
        )
        prosent = c2.number_input(
            "Konsentrasjon (%)", min_value=0.0, max_value=100.0, step=1.0,
            value=float(syre.get("prosent") or 0.0), key=f"vann_syre_prosent_{revisjon}_{i}",
            label_visibility="collapsed" if i else "visible", help="0 = ikke angitt.",
        )
        syre["prosent"] = prosent or None
        syre["mengde_ml"] = c3.number_input(
            "Mengde (mL)", min_value=0.0, max_value=200.0, step=0.5,
            value=float(syre.get("mengde_ml", 0.0)), key=f"vann_syre_ml_{revisjon}_{i}",
            label_visibility="collapsed" if i else "visible",
        )
        syre["navn"] = SYRER[syre["syre_id"]]["navn"]
        syre["formel"] = SYRER[syre["syre_id"]]["formel"]
        if st.button("🗑️ Fjern syre", key=f"vann_syre_slett_{revisjon}_{i}"):
            slett_syre_idx = i

    if slett_syre_idx is not None:
        syrer.pop(slett_syre_idx)
        _ny_vann_widget_revisjon()
        st.rerun()

    if st.button("➕ Legg til syre", key="vann_legg_til_syre_btn"):
        syrer.append(bygg_syretilsetning(syre_valg[0]))
        _ny_vann_widget_revisjon()
        st.rerun()

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
