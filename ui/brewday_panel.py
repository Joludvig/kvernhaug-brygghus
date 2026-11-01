import streamlit as st
from config import DEMO_MODE
from modules.brewday_calc import (
    lag_brewday_plan, TILSETNINGER,
    beregn_effektivitet, beregn_post_boil_og, fermenteringstemp_linjer, bryggedag_noter,
    tilsetning_visning, maskeplan_label_visning,
)
from modules.calculations import beregn_abv_standard
from modules.kbhbrew_history_ui import parse_actual_tallfelt
from modules.kbhbrew_storage import hent_brew, oppdater_brew_lag
from modules.process_profiles import normaliser_prosessprofil, profilnavn_visning
from modules.export_format import fmt_og, fmt_fg, fmt_abv, stats_linje
from modules.brewday_template import render_brewday_html
from ui.kbhbrew_panel import aktiv_brew_id, render_kbhbrew_create_panel
from ui.kbhbrew_history_panel import render_kbhbrew_history_panel
from ui.i18n import gjeldende_sprak, t as _t

# App A1 (issue #170): et privat sentinel-objekt for å skille "Steg
# 4/5 sine målefelt er ALDRI synket mot et aktivt brygg før" fra "de er
# synket, og målet er (fortsatt) None" -- samme "unngå en falsk
# None==None-treff ved aller første rendring"-forsiktighet som
# ui/kbhbrew_history_panel.py sin _UKJENT_SENTINEL.
_BD_MAALINGER_INGEN_SENTINEL = object()

# Sjekklistepunktene vises via i18n-nøklene bdp.sjekk.0..7 (samme rekkefølge,
# og dermed samme widgetnøkler bd_chk_<i>, som før #548).
_SJEKKLISTE_ANTALL = 8

_BD_DEFAULTS = [
    ("bd_tilsetninger", []),
    ("bd_mash_start",   ""),
    ("bd_mash_end",     ""),
    ("bd_mash_temp_1",  0.0),
    ("bd_mash_temp_2",  0.0),
    ("bd_mash_temp_3",  0.0),
    ("bd_pre_boil_vol", 0.0),
    ("bd_pre_boil_sg",  1.000),
    ("bd_post_boil_vol",0.0),
    ("bd_pitch_temp",   0.0),
    ("bd_inkbird_temp", ""),
    ("bd_ferm_pressure",""),
    ("bd_transfer_note",""),
]


def render_brewday_panel(ctx, humle_database, gjaer_database, malt_database=None):
    for key, default in _BD_DEFAULTS:
        if key not in st.session_state:
            st.session_state[key] = default

    gjaer_id   = st.session_state.get("valgt_gjaer_id", "")
    gjaer_info = gjaer_database.get(gjaer_id, {})

    # Leses direkte fra session_state (satt av ui/process_panel.py) i stedet
    # for via ctx["recipe"]["process_profile"], slik at et nettopp endret
    # profilvalg oppdaterer bryggedagsarket UMIDDELBART i samme rerun — ctx
    # ble bygget tidligere i skriptet (tab_oppskrift) og kan derfor henge
    # ett rerun etter når prosessprofilen endres inne i denne fanen.
    #
    # Kandidaten normaliseres FØR den brukes noe sted — normaliser_
    # prosessprofil() er den ENE, felles kilden (se
    # modules/process_profiles.py) som garanterer at en kjent
    # standardprofil (Hochkurz osv.) ALDRI kan bæres videre med en
    # korrupt/hybrid meskeplan, uansett hva som måtte ligge i
    # session_state fra før. Den normaliserte profilen skrives STRAKS
    # tilbake til BÅDE session_state og ctx, slik at alle tre — session_
    # state, ctx og argumentet til lag_brewday_plan() — blir nøyaktig
    # samme objektinnhold resten av denne kjøringen.
    _kandidat = st.session_state.get("aktiv_prosessprofil")
    prosess_profil = normaliser_prosessprofil(_kandidat) if _kandidat else None
    st.session_state["aktiv_prosessprofil"] = prosess_profil
    ctx["recipe"]["process_profile"] = prosess_profil

    plan = lag_brewday_plan(
        malt_valg          = st.session_state.get("valgt_malt", []),
        humle_valg         = st.session_state.get("valgt_humle", []),
        gjaer_id           = gjaer_id,
        gjaer_info         = gjaer_info,
        og                 = ctx["og"],
        batch_volum_l      = ctx["volum"],
        humle_database     = humle_database,
        malt_database      = malt_database,
        tilsetninger_valgt = st.session_state.get("bd_tilsetninger", []),
        process_profile    = prosess_profil,
        sprak              = gjeldende_sprak(),
    )
    sprak = gjeldende_sprak()

    # ── HEADER (alltid synlig) ───────────────────────────────────────────────
    st.subheader(ctx["name"])
    if ctx.get("brygger_stil"):
        st.caption(ctx["brygger_stil"])
    st.caption(stats_linje(ctx))
    if plan.get("prosess_profil"):
        st.caption(_t("bdp.bryggemaate", navn=profilnavn_visning(plan['prosess_profil']['navn'], sprak, plan['prosess_profil'].get('process_id'))))

    bi1, bi2, bi3 = st.columns(3)
    with bi1:
        st.text_input(_t("bdp.batchnr"), placeholder=_t("bdp.batchnr.placeholder"), key="bd_batchnr")
    with bi2:
        st.date_input(_t("bdp.dato"), key="bd_dato")
    with bi3:
        st.text_input(_t("bdp.brygger"), placeholder=_t("bdp.brygger.placeholder"), key="bd_brygger")

    render_kbhbrew_create_panel(ctx, malt_database, humle_database, gjaer_database)
    render_kbhbrew_history_panel(malt_database, humle_database, gjaer_database)

    # ── SYNKRONISER STEG 4/5-MÅLEFELT MOT AKTIVT BRYGG (App A1, issue #170) ──
    # Når det aktive brygg-målet (ui/kbhbrew_panel.py::aktiv_brew_id() --
    # samme peker "Start nytt brygg"/Brygghistorikk-utvalget over nettopp
    # kan ha endret) er ANNERLEDES enn ved forrige kjente synk, må
    # bd_og/bd_fg/bd_post_boil_vol re-synkes FØR widgetene under
    # instansieres i DENNE kjøringen -- enten forhåndsutfylt fra det NYE
    # målets EGNE lagrede actuals (aldri en gjettet verdi, samme prefill-
    # prinsipp som ui/kbhbrew_history_panel.py::_render_actuals_skjema()),
    # eller tømt hvis intet aktivt brygg finnes. Dette hindrer at et
    # utypet, ulagret tall fra FORRIGE mål (eller fra FØR noe brygg i det
    # hele tatt var aktivt) stille kan bli tilskrevet et nytt brygg, eller
    # fortsette å vises som om det fortsatt gjaldt et brygg som nettopp
    # ble ugyldiggjort av et oppskriftsbytte (issue #170 "Identity
    # safety"). Må kjøres FØR Steg 3/4/5 sine widgets under -- ETTER at
    # session_state for en widget-bundet nøkkel er satt her, kan den
    # fortsatt brukes som widgetens verdi FOR DENNE kjøringen, men KUN
    # fordi ingen av disse tre widgetene er instansiert ennå på dette
    # punktet i skriptet.
    _bd_maalinger_brew_id = aktiv_brew_id() or _BD_MAALINGER_INGEN_SENTINEL
    if st.session_state.get("_bd_maalinger_synket_brew_id", object()) != _bd_maalinger_brew_id:
        _bd_brew_for_prefill = (
            hent_brew(_bd_maalinger_brew_id) if _bd_maalinger_brew_id is not _BD_MAALINGER_INGEN_SENTINEL else None
        )
        _bd_actuals_for_prefill = (_bd_brew_for_prefill or {}).get("actuals") or {}
        st.session_state["bd_og"] = (
            "" if _bd_actuals_for_prefill.get("og") is None else str(_bd_actuals_for_prefill["og"])
        )
        st.session_state["bd_fg"] = (
            "" if _bd_actuals_for_prefill.get("fg") is None else str(_bd_actuals_for_prefill["fg"])
        )
        _bd_volum_for_prefill = _bd_actuals_for_prefill.get("volumeL")
        st.session_state["bd_post_boil_vol"] = (
            float(_bd_volum_for_prefill)
            if isinstance(_bd_volum_for_prefill, (int, float)) and not isinstance(_bd_volum_for_prefill, bool)
            else 0.0
        )
        st.session_state["_bd_maalinger_synket_brew_id"] = _bd_maalinger_brew_id

    st.write("---")

    # ── STEG 1: BRYGGEPLAN ──────────────────────────────────────────────────
    with st.expander(_t("bdp.steg1"), expanded=True):
        bd_left, bd_right = st.columns(2)

        with bd_left:
            st.markdown(_t("bdp.malt_tittel", kg=f"{plan['total_korn_kg']:.2f}"))
            for i, m in enumerate(plan["malt_liste"]):
                st.checkbox(f"{m['mengde']:.2f} kg — {m['navn']}", key=f"bd_malt_{i}")

            st.write("")
            st.markdown(_t("bdp.vann_tittel"))
            w = plan["vann"]
            c1, c2, c3 = st.columns(3)
            c1.metric(_t("bdp.meskevann"),  f"{w['mash_vann_l']:.1f} L")
            c2.metric(_t("bdp.skyllevann"), f"{w['sparge_vann_l']:.1f} L")
            c3.metric(_t("bdp.preboil"),    f"{w['pre_boil_l']:.1f} L")

            if plan["brewzilla_varsel"]:
                st.warning(_t("bdp.brewzilla_varsel", l=f"{w['pre_boil_l']:.1f}"))

            st.write("")
            st.markdown(_t("bdp.mesking_tittel"))
            for steg in plan["maskeplan"]:
                st.write(
                    f"- {steg['temp_c']}°C  ·  {steg['varighet_min']} min  —  "
                    f"*{maskeplan_label_visning(steg, (plan.get('prosess_profil') or {}).get('process_id'), sprak)}*"
                )

            if plan.get("dekoksjon"):
                d = plan["dekoksjon"]
                st.caption(_t(
                    "bdp.dekoksjon", uttak=f"{d['uttak_liter']:.2f}", fra=d['fra_temp_c'],
                    min=d['koketid_min'], til=d['til_temp_c'],
                ))
            if plan.get("reiterated_mash_flyt"):
                r = plan["reiterated_mash_flyt"]
                st.caption(_t(
                    "bdp.dobbelmesk", m1=f"{r['malt_1_kg']:.2f}", v1=f"{r['vann_mesk_1_l']:.1f}",
                    w1=f"{r['vort_1_l']:.1f}", m2=f"{r['malt_2_kg']:.2f}", w2=f"{r['vort_2_l']:.1f}",
                ))
                for v in r["varsler"]:
                    st.warning(v)

            for varsel in plan.get("utstyrsvarsler", []):
                st.warning(f"⚠️ {varsel}")

            st.write("")
            st.markdown(_t("bdp.koking_tittel"))
            e1, e2, e3 = st.columns(3)
            e1.metric(_t("bdp.koketid"),        f"{plan['koketid_min']} min")
            e2.metric(_t("bdp.koketap"),        f"{plan['estimert_koketap_l']:.1f} L")
            e3.metric(_t("bdp.postboil_est"),   f"{plan['estimert_post_boil_l']:.1f} L")
            if not plan.get("prosess_profil") and plan["koketid_min"] == 90:
                st.caption(_t("bd.kok.pilsner_anbefalt"))

        with bd_right:
            st.markdown(_t("bdp.humle_tittel"))
            if plan["humleplan"]:
                header = _t("bdp.humle_header") + "\n|-----|-----|-------|------|-----|"
                rows   = "\n".join(
                    f"| {'⚠️ ' if h['tid_over_koketid'] else ''}{h['tid']} min "
                    f"| {h['tilsatt_etter_min']} min | {h['navn']} | {h['gram']:.0f} g | {h['ibu_bidrag']:.1f} |"
                    for h in plan["humleplan"]
                )
                st.markdown(f"{header}\n{rows}")
                st.caption(_t("bdp.humle_forklaring", koketid=plan['koketid_min']))

                # Umulig humletid: en tilsetning med lengre egen koketid enn
                # selve kokens totale lengde kan ikke fysisk oppnå IBU-en
                # tabellen over viser (den bruker brukerens OPPGITTE tid,
                # uendret — se modules/brewday_calc.py::_bygg_humle_entry).
                # Muterer ALDRI oppskriften automatisk her; viser i stedet
                # BEGGE tallene side om side og lar brukeren selv avgjøre.
                if plan["humle_over_koketid"]:
                    _humle_navn = ", ".join(
                        f"{h['navn']} ({h['tid']} min)" for h in plan["humle_over_koketid"]
                    )
                    st.warning(_t(
                        "bdp.humle_over_varsel", n=len(plan['humle_over_koketid']),
                        koketid=plan['koketid_min'], navn=_humle_navn,
                    ))
                    ibu_c1, ibu_c2 = st.columns(2)
                    ibu_c1.metric(_t("bdp.ibu_planlagt"), f"{plan['ibu_planlagt']:.1f}")
                    ibu_c2.metric(
                        _t("bdp.ibu_faktisk"), f"{plan['ibu_faktisk_prosess']:.1f}",
                        delta=f"{plan['ibu_faktisk_prosess'] - plan['ibu_planlagt']:.1f}",
                        delta_color="inverse",
                    )
            else:
                st.caption(_t("bdp.ingen_humle"))

            st.write("")
            st.markdown(_t("bdp.gjaer_tittel"))
            st.write(_t("bdp.gjaer_pakker", navn=plan['gjaer_navn'], pakker=plan['pakker']))
            for _temp_linje in fermenteringstemp_linjer(
                plan, (ctx.get("recipe") or {}).get("fermentation_temp_target_c"),
                sprak,
            ):
                st.write(f"- {_temp_linje}")
            for note in bryggedag_noter(plan, sprak):
                st.info(note)

            st.write("")
            st.markdown(_t("bdp.tils_tittel"))
            st.multiselect(
                _t("bdp.tils_velg"),
                options=list(TILSETNINGER.keys()),
                format_func=lambda k: tilsetning_visning({**TILSETNINGER[k], "id": k}, sprak)["navn"],
                key="bd_tilsetninger",
                label_visibility="collapsed",
            )
            for k in st.session_state.get("bd_tilsetninger", []):
                tv = tilsetning_visning({**TILSETNINGER[k], "id": k}, sprak)
                st.caption(f"**{tv['navn']}** · {tv['dose']} · {tv['timing']}")

    # ── STEG 2: MESKING ─────────────────────────────────────────────────────
    with st.expander(_t("bdp.steg2")):
        m_left, m_right = st.columns(2)
        with m_left:
            st.text_input(_t("bdp.mesk_start"), placeholder="08:30", key="bd_mash_start")
            st.text_input(_t("bdp.mesk_slutt"), placeholder="09:30", key="bd_mash_end")
        with m_right:
            t1, t2, t3 = st.columns(3)
            t1.number_input(_t("bdp.mesk_temp", n=1), min_value=0.0, max_value=100.0, step=0.5,
                            format="%.1f", key="bd_mash_temp_1")
            t2.number_input(_t("bdp.mesk_temp", n=2), min_value=0.0, max_value=100.0, step=0.5,
                            format="%.1f", key="bd_mash_temp_2")
            t3.number_input(_t("bdp.mesk_temp", n=3), min_value=0.0, max_value=100.0, step=0.5,
                            format="%.1f", key="bd_mash_temp_3")

    # ── STEG 3: KOKING & PRØVER ─────────────────────────────────────────────
    with st.expander(_t("bdp.steg3")):
        st.markdown(_t("bdp.preboil_maalinger"))
        pb1, pb2, pb3 = st.columns(3)
        with pb1:
            pre_boil_vol = st.number_input(
                _t("bdp.preboil_vol"),
                min_value=0.0, max_value=50.0, step=0.5, format="%.1f",
                key="bd_pre_boil_vol",
            )
        with pb2:
            pre_boil_sg = st.number_input(
                _t("bdp.preboil_sg"),
                min_value=1.000, max_value=1.200, step=0.001, format="%.3f",
                key="bd_pre_boil_sg",
            )
        with pb3:
            koketap      = plan["estimert_koketap_l"]
            post_boil_est = max(0.0, pre_boil_vol - koketap) if pre_boil_vol > 0 else 0.0
            st.metric(
                _t("bdp.postboil_estimert"),
                f"{post_boil_est:.1f} L" if post_boil_est > 0 else "—",
                help=_t("bdp.postboil_hjelp", koketap=f"{koketap:.1f}"),
            )

        if pre_boil_vol > 30.0:
            st.warning(_t("bdp.preboil_over_30", l=f"{pre_boil_vol:.1f}"))

        if pre_boil_sg > 1.001 and pre_boil_vol > 0 and post_boil_est > 0:
            forventet_og = beregn_post_boil_og(pre_boil_sg, pre_boil_vol, post_boil_est)
            og_diff      = forventet_og - ctx["og"]
            st.write("")
            fo1, fo2, fo3 = st.columns(3)
            fo1.metric(_t("bdp.planlagt_og"),   fmt_og(ctx["og"]))
            fo2.metric(_t("bdp.forventet_og"),  fmt_og(forventet_og))
            fo3.metric(_t("bdp.avvik"),         f"{og_diff:+.3f}",
                       delta_color="inverse" if abs(og_diff) > 0.005 else "off")

        # Koking-tilsetninger
        kok_sett = [x for x in plan["tilsetninger"] if x["fase"] == "koking"]
        if kok_sett:
            st.write("")
            st.markdown(_t("bdp.kok_tils_tittel"))
            for tilsetning in kok_sett:
                tv = tilsetning_visning(tilsetning, sprak)
                st.write(f"- **{tv['navn']}** · {tv['dose']} · {tv['timing']}")
                st.caption(f"  {tv['note']}")

        st.write("")
        st.markdown(_t("bdp.postboil_tittel"))
        st.number_input(
            _t("bdp.postboil_vol"),
            min_value=0.0, max_value=50.0, step=0.5, format="%.1f",
            key="bd_post_boil_vol",
        )

    # ── STEG 4: OVERFØRING & OG ─────────────────────────────────────────────
    with st.expander(_t("bdp.steg4")):
        ov1, ov2, ov3 = st.columns(3)
        with ov1:
            st.text_input(
                _t("bdp.og_maal", x=fmt_og(ctx['og'])), placeholder=_t("bdp.faktisk"), key="bd_og",
            )
        with ov2:
            st.number_input(
                _t("bdp.pitch_temp"),
                min_value=0.0, max_value=40.0, step=0.5, format="%.1f",
                key="bd_pitch_temp",
            )
        with ov3:
            st.text_input(
                _t("bdp.overforing_notat"), placeholder=_t("bdp.overforing_notat.placeholder"),
                key="bd_transfer_note",
            )

    # ── STEG 5: GJÆRING ─────────────────────────────────────────────────────
    with st.expander(_t("bdp.steg5")):
        gjær_sett = [x for x in plan["tilsetninger"] if x["fase"] == "gjæring"]
        for tilsetning in gjær_sett:
            tv = tilsetning_visning(tilsetning, sprak)
            st.info(f"**{tv['navn']}:** {tv['dose']} — {tv['note']}")

        ferm1, ferm2 = st.columns(2)
        with ferm1:
            st.date_input(_t("bdp.gjaering_start"), key="bd_ferm_start")
        with ferm2:
            st.date_input(_t("bdp.coldcrash"), key="bd_ferm_slutt")

        mon1, mon2 = st.columns(2)
        with mon1:
            st.text_input(
                _t("bdp.inkbird"), placeholder=_t("bdp.inkbird.placeholder"),
                key="bd_inkbird_temp",
            )
        with mon2:
            st.text_input(
                _t("bdp.trykk"), placeholder=_t("bdp.trykk.placeholder"),
                key="bd_ferm_pressure",
            )

        st.write("")
        fg1, fg2, fg3 = st.columns(3)
        with fg1:
            st.text_input(
                _t("bdp.fg_maal", x=fmt_fg(ctx['fg'])), placeholder=_t("bdp.faktisk"), key="bd_fg",
            )
        with fg2:
            st.text_input(
                _t("bdp.abv_maal", x=fmt_abv(ctx['abv'])), placeholder=_t("bdp.beregnet"), key="bd_abv",
            )
        with fg3:
            try:
                og_f  = float(st.session_state.get("bd_og", "") or 0)
                fg_f  = float(st.session_state.get("bd_fg", "") or 0)
                if og_f > 1.001 and fg_f > 1.000:
                    st.metric(_t("bdp.beregnet_abv"), f"{beregn_abv_standard(og_f, fg_f):.1f}%")
            except (ValueError, TypeError):
                # Inkluderer Core sin ValueError for ugyldig måling
                # (f.eks. FG > OG) -- ingen metric vises da, i stedet
                # for en stille negativ ABV.
                pass

    # ── LAGRE MÅLINGER TIL AKTIVT BRYGG (App A1, issue #170) ─────────────────
    # Ett eksplisitt lagre-klikk skriver Steg 4/5 sine A1-kjernemålinger
    # (OG/FG/post-boil-volum) + bryggedato til DET AKTIVE brygget
    # (ui/kbhbrew_panel.py::aktiv_brew_id()) via SAMME
    # oppdater_brew_lag()-skrivevei og SAMME strenge tallvalidering
    # (parse_actual_tallfelt()) som Brygghistorikk-skjemaet bruker --
    # ALDRI en ny skrivevei. Rendring/typing/rerun alene skriver ALDRI
    # noe -- kun tilgjengelig inne i `if st.button(...)`-blokken, samme
    # garanti som ui/kbhbrew_history_panel.py::_render_actuals_skjema().
    # Skjules helt i DEMO_MODE, samme mønster som render_kbhbrew_
    # create_panel()/render_kbhbrew_history_panel().
    if not DEMO_MODE:
        st.write("---")
        st.markdown(_t("bdp.lagre_tittel"))
        _lagre_mal_brew_id = aktiv_brew_id()
        _lagre_mal_brew = hent_brew(_lagre_mal_brew_id) if _lagre_mal_brew_id else None
        if _lagre_mal_brew is None:
            st.caption(_t("bdp.lagre_ingen_aktivt"))
        else:
            _lagre_mal_navn = ((_lagre_mal_brew.get("snapshot") or {}).get("recipe") or {}).get("navn") or _t("bdp.uten_navn")
            st.caption(_t("bdp.lagre_maal", navn=_lagre_mal_navn, id=_lagre_mal_brew_id))
            # App A3 (issue #237, fiks A3-3) -- Brygghistorikk sitt
            # eksplisitte utvalg retargetterer BEVISST dette skrivemålet
            # (App A1, issue #170 "Identity safety" #3) -- det beholdes
            # UENDRET her. Denne advarselen legger KUN til synlig
            # orientering FØR selve lagre-klikket når målet ikke lenger har
            # lagret status "active", uten å deaktivere knappen eller endre
            # noen skrivevei (se docs/development/
            # app_a3_state_orientation_preflight.md Section 8, funn A3-3).
            if _lagre_mal_brew.get("status") != "active":
                st.warning(_t(
                    "kbhbrew.advarsel_ikke_aktiv_status",
                    status=_t(f"brew_history.status.{_lagre_mal_brew.get('status')}"),
                ))
        if st.button(
            _t("bdp.lagre_knapp"),
            key="bd_lagre_maalinger_btn",
            disabled=_lagre_mal_brew is None,
        ):
            _og_ok, _og_verdi = parse_actual_tallfelt(st.session_state.get("bd_og", ""))
            _fg_ok, _fg_verdi = parse_actual_tallfelt(st.session_state.get("bd_fg", ""))
            _ugyldige_felt = []
            if not _og_ok:
                _ugyldige_felt.append("OG")
            if not _fg_ok:
                _ugyldige_felt.append("FG")
            if _ugyldige_felt:
                st.error(_t("bdp.lagre_ugyldig", felt=", ".join(_ugyldige_felt)))
            else:
                _post_boil_verdi = st.session_state.get("bd_post_boil_vol", 0.0)
                _bd_dato_verdi = st.session_state.get("bd_dato")
                oppdater_brew_lag(
                    _lagre_mal_brew_id,
                    actuals={
                        "og": "" if _og_verdi is None else _og_verdi,
                        "fg": "" if _fg_verdi is None else _fg_verdi,
                        "volumeL": _post_boil_verdi if _post_boil_verdi and _post_boil_verdi > 0 else "",
                    },
                    brewed_at=_bd_dato_verdi.isoformat() if hasattr(_bd_dato_verdi, "isoformat") else "",
                )
                st.success(_t("bdp.lagre_ok", id=_lagre_mal_brew_id))

    # ── STEG 6: EFFEKTIVITET ────────────────────────────────────────────────
    with st.expander(_t("bdp.steg6")):
        pre_sg  = st.session_state.get("bd_pre_boil_sg",  1.000)
        pre_vol = st.session_state.get("bd_pre_boil_vol", 0.0)
        try:
            og_faktisk = float(st.session_state.get("bd_og", "") or 0)
        except (ValueError, TypeError):
            og_faktisk = 0.0

        eff = beregn_effektivitet(
            malt_valg     = st.session_state.get("valgt_malt", []),
            malt_database = malt_database or {},
            pre_boil_sg   = pre_sg,
            pre_boil_vol  = pre_vol,
            og            = og_faktisk,
            batch_vol     = ctx["volum"],
        )

        ef1, ef2, ef3 = st.columns(3)
        ef1.metric(
            _t("bdp.eff_mesk"),
            f"{eff['mash_eff'] * 100:.1f}%" if pre_sg > 1.001 and pre_vol > 0 else "—",
        )
        ef2.metric(
            _t("bdp.eff_bryggeri"),
            f"{eff['brewhouse_eff'] * 100:.1f}%" if og_faktisk > 1.001 else "—",
        )
        ef3.metric(_t("bdp.eff_planlagt"), f"{ctx['effektivitet'] * 100:.0f}%")

        if pre_sg <= 1.001 or pre_vol <= 0:
            st.caption(_t("bdp.eff_fyll_mesk"))
        if og_faktisk <= 1.001:
            st.caption(_t("bdp.eff_fyll_bryggeri"))

    # ── SJEKKLISTE ──────────────────────────────────────────────────────────
    st.write("---")
    st.markdown(_t("bdp.sjekkliste_tittel"))
    chk_cols = st.columns(4)
    for i in range(_SJEKKLISTE_ANTALL):
        chk_cols[i % 4].checkbox(_t(f"bdp.sjekk.{i}"), key=f"bd_chk_{i}")

    # ── PRINT-ARK ───────────────────────────────────────────────────────────
    st.write("")
    # Eksport blokkeres ALDRI stille -- men ved en umulig humletid (se
    # varselet/IBU-sammenligningen over) må brukeren eksplisitt bekrefte
    # at avviket er sett før arket kan genereres, slik at et bryggedagsark
    # med en IBU som ikke er fysisk oppnåelig ikke presenteres som gyldig
    # uten videre.
    #
    # Nøkkelen til bekreftelses-checkboxen er BEVISST avledet av en
    # signatur på gjeldende oppskrift + total koketid + akkurat HVILKE
    # humler/tider som er i avvik -- IKKE en fast nøkkel. En fast nøkkel
    # ville latt en bekreftelse for én oppskrift følge med "gratis" ved
    # et direkte bytte til en ANNEN oppskrift med et helt annet (eller
    # like ugyldig) avvik, siden Streamlit sin egen widget-state for en
    # uendret nøkkel overlever på tvers av reruns. En endring i
    # signaturen (annen oppskrift, endret koketid, endret humleliste) gir
    # en NY, ubekreftet widget-instans -- samme mønster som
    # ui/process_panel.py sin _process_widget_revision for meskestegene.
    _eksport_ok = True
    if plan["humle_over_koketid"]:
        _avvik_signatur = (
            f"{ctx['name']}|koketid={plan['koketid_min']}|"
            + ",".join(f"{h['navn']}:{h['tid']}" for h in plan["humle_over_koketid"])
        )
        _eksport_ok = st.checkbox(
            _t("bdp.bekreft_avvik"),
            key=f"bd_bekreft_humletid_avvik::{_avvik_signatur}",
        )
        if not _eksport_ok:
            st.caption(_t("bdp.last_avvik"))
    if st.button(_t("bdp.generer"), width="stretch", key="brewday_print_btn", disabled=not _eksport_ok):
        log = {
            "pre_boil_sg":   st.session_state.get("bd_pre_boil_sg",  1.000),
            "pre_boil_vol":  st.session_state.get("bd_pre_boil_vol", 0.0),
            "post_boil_vol": st.session_state.get("bd_post_boil_vol",0.0),
            "og":            st.session_state.get("bd_og",  ""),
            "fg":            st.session_state.get("bd_fg",  ""),
            "abv":           st.session_state.get("bd_abv", ""),
            "pitch_temp":    st.session_state.get("bd_pitch_temp", 0.0),
            "mash_eff":      eff["mash_eff"],
            "brewhouse_eff": eff["brewhouse_eff"],
        }
        water = {
            "kilde":      st.session_state.get("aktiv_vannkilde_snapshot"),
            "maal":       st.session_state.get("aktiv_vannmaal_snapshot"),
            "behandling": st.session_state.get("aktiv_vannbehandling"),
            "maalinger":  st.session_state.get("aktiv_vannmaalinger"),
        }
        html     = render_brewday_html(ctx, plan, log, water=water, sprak=sprak)
        fil_navn = ctx["name"].replace(" ", "_").replace("/", "-") + "_bryggedag.html"
        st.download_button(
            label=_t("bdp.last_ned"),
            data=html,
            file_name=fil_navn,
            mime="text/html",
            width="stretch",
            key="brewday_download_btn",
        )
        st.info(_t("bdp.print_hint"))
