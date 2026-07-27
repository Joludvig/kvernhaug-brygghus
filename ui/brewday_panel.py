import streamlit as st
from modules.brewday_calc import (
    lag_brewday_plan, TILSETNINGER,
    beregn_effektivitet, beregn_post_boil_og,
)
from modules.process_profiles import normaliser_prosessprofil
from modules.export_format import fmt_og, fmt_fg, fmt_abv, stats_linje
from modules.brewday_template import render_brewday_html

_SJEKKLISTE = [
    "Utstyr rent", "Meskevann varmt", "Skylling ferdig", "Kok startet",
    "Humle tilsatt", "Nedkjøling ferdig", "Gjær tilsatt", "Gjæring startet",
]

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
    )

    # ── HEADER (alltid synlig) ───────────────────────────────────────────────
    st.subheader(ctx["name"])
    if ctx.get("brygger_stil"):
        st.caption(ctx["brygger_stil"])
    st.caption(stats_linje(ctx))
    if plan.get("prosess_profil"):
        st.caption(f"🧭 Bryggemåte: **{plan['prosess_profil']['navn']}**")

    bi1, bi2, bi3 = st.columns(3)
    with bi1:
        st.text_input("Batchnummer", placeholder="f.eks. 2026-001", key="bd_batchnr")
    with bi2:
        st.date_input("Bryggedato", key="bd_dato")
    with bi3:
        st.text_input("Brygger", placeholder="Navn", key="bd_brygger")

    st.write("---")

    # ── STEG 1: BRYGGEPLAN ──────────────────────────────────────────────────
    with st.expander("🗒️ 1. Bryggeplan", expanded=True):
        bd_left, bd_right = st.columns(2)

        with bd_left:
            st.markdown(f"**🌾 Malt — {plan['total_korn_kg']:.2f} kg**")
            for i, m in enumerate(plan["malt_liste"]):
                st.checkbox(f"{m['mengde']:.2f} kg — {m['navn']}", key=f"bd_malt_{i}")

            st.write("")
            st.markdown("**💧 Vann**")
            w = plan["vann"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Meskevann",  f"{w['mash_vann_l']:.1f} L")
            c2.metric("Skyllevann", f"{w['sparge_vann_l']:.1f} L")
            c3.metric("Pre-boil",   f"{w['pre_boil_l']:.1f} L")

            if plan["brewzilla_varsel"]:
                st.warning(
                    f"⚠️ **BrewZilla 35 Gen4:** Estimert pre-boil {w['pre_boil_l']:.1f} L "
                    f"overskrider anbefalt maks 30 L. Vurder å redusere batchstørrelse."
                )

            st.write("")
            st.markdown("**🌡️ Mesking**")
            for steg in plan["maskeplan"]:
                st.write(f"- {steg['temp_c']}°C  ·  {steg['varighet_min']} min  —  *{steg['label']}*")

            if plan.get("dekoksjon"):
                d = plan["dekoksjon"]
                st.caption(
                    f"🔥 Dekoksjon: ta ut **{d['uttak_liter']:.2f} L** tykkmesk ved "
                    f"{d['fra_temp_c']}°C, kok {d['koketid_min']} min, før tilbake "
                    f"for å nå {d['til_temp_c']}°C."
                )
            if plan.get("reiterated_mash_flyt"):
                r = plan["reiterated_mash_flyt"]
                st.caption(
                    f"🔁 Dobbelmesk: Mesk 1 ({r['malt_1_kg']:.2f} kg + {r['vann_mesk_1_l']:.1f} L "
                    f"ferskt vann → {r['vort_1_l']:.1f} L vørt) brukes som meskevann til "
                    f"Mesk 2 ({r['malt_2_kg']:.2f} kg → {r['vort_2_l']:.1f} L sluttvørt)."
                )
                for v in r["varsler"]:
                    st.warning(v)

            for varsel in plan.get("utstyrsvarsler", []):
                st.warning(f"⚠️ {varsel}")

            st.write("")
            st.markdown("**🔥 Koking**")
            e1, e2, e3 = st.columns(3)
            e1.metric("Koketid",        f"{plan['koketid_min']} min")
            e2.metric("Est. koketap",   f"{plan['estimert_koketap_l']:.1f} L")
            e3.metric("Est. post-boil", f"{plan['estimert_post_boil_l']:.1f} L")
            if not plan.get("prosess_profil") and plan["koketid_min"] == 90:
                st.caption("90 min anbefalt for Pilsnermalt.")

        with bd_right:
            st.markdown("**🌿 Humletilsetninger**")
            if plan["humleplan"]:
                header = "| Tid igjen | Tilsatt etter | Humle | Gram | IBU |\n|-----|-----|-------|------|-----|"
                rows   = "\n".join(
                    f"| {'⚠️ ' if h['tid_over_koketid'] else ''}{h['tid']} min "
                    f"| {h['tilsatt_etter_min']} min | {h['navn']} | {h['gram']:.0f} g | {h['ibu_bidrag']:.1f} |"
                    for h in plan["humleplan"]
                )
                st.markdown(f"{header}\n{rows}")
                st.caption(
                    "«Tid igjen» = humlens egen koketid. «Tilsatt etter» = minutter "
                    f"etter kokestart, gitt {plan['koketid_min']} min total koketid."
                )

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
                    st.warning(
                        f"⚠️ {len(plan['humle_over_koketid'])} humle markert over har lengre "
                        f"egen koketid enn total koketid ({plan['koketid_min']} min): {_humle_navn}. "
                        "IBU-tabellen over viser oppskriftens PLANLAGTE bidrag (uendret tid) — "
                        "se sammenligningen under for hva som faktisk er oppnåelig i denne koken."
                    )
                    ibu_c1, ibu_c2 = st.columns(2)
                    ibu_c1.metric("IBU — oppskriftens planlagte", f"{plan['ibu_planlagt']:.1f}")
                    ibu_c2.metric(
                        "IBU — prosessens faktisk mulige", f"{plan['ibu_faktisk_prosess']:.1f}",
                        delta=f"{plan['ibu_faktisk_prosess'] - plan['ibu_planlagt']:.1f}",
                        delta_color="inverse",
                    )
            else:
                st.caption("Ingen humle i oppskriften.")

            st.write("")
            st.markdown("**🧫 Gjær & Fermentering**")
            st.write(f"- **{plan['gjaer_navn']}** — {plan['pakker']} pakke(r)")
            st.write(f"- Temp: **{plan['temp_min']}–{plan['temp_maks']}°C**")
            for note in plan["noter"]:
                st.info(note)

            st.write("")
            st.markdown("**🧪 Tilsetninger**")
            st.multiselect(
                "Velg tilsetninger",
                options=list(TILSETNINGER.keys()),
                format_func=lambda k: TILSETNINGER[k]["navn"],
                key="bd_tilsetninger",
                label_visibility="collapsed",
            )
            for k in st.session_state.get("bd_tilsetninger", []):
                t = TILSETNINGER[k]
                st.caption(f"**{t['navn']}** · {t['dose']} · {t['timing']}")

    # ── STEG 2: MESKING ─────────────────────────────────────────────────────
    with st.expander("🌡️ 2. Mesking"):
        m_left, m_right = st.columns(2)
        with m_left:
            st.text_input("Meskestart", placeholder="08:30", key="bd_mash_start")
            st.text_input("Meskeslutt", placeholder="09:30", key="bd_mash_end")
        with m_right:
            t1, t2, t3 = st.columns(3)
            t1.number_input("Temp obs. 1 (°C)", min_value=0.0, max_value=100.0, step=0.5,
                            format="%.1f", key="bd_mash_temp_1")
            t2.number_input("Temp obs. 2 (°C)", min_value=0.0, max_value=100.0, step=0.5,
                            format="%.1f", key="bd_mash_temp_2")
            t3.number_input("Temp obs. 3 (°C)", min_value=0.0, max_value=100.0, step=0.5,
                            format="%.1f", key="bd_mash_temp_3")

    # ── STEG 3: KOKING & PRØVER ─────────────────────────────────────────────
    with st.expander("🔥 3. Koking & Prøver"):
        st.markdown("**📐 Pre-boil målinger**")
        pb1, pb2, pb3 = st.columns(3)
        with pb1:
            pre_boil_vol = st.number_input(
                "Pre-boil volum (L)",
                min_value=0.0, max_value=50.0, step=0.5, format="%.1f",
                key="bd_pre_boil_vol",
            )
        with pb2:
            pre_boil_sg = st.number_input(
                "Pre-boil SG",
                min_value=1.000, max_value=1.200, step=0.001, format="%.3f",
                key="bd_pre_boil_sg",
            )
        with pb3:
            koketap      = plan["estimert_koketap_l"]
            post_boil_est = max(0.0, pre_boil_vol - koketap) if pre_boil_vol > 0 else 0.0
            st.metric(
                "Estimert post-boil",
                f"{post_boil_est:.1f} L" if post_boil_est > 0 else "—",
                help=f"Pre-boil minus {koketap:.1f} L estimert koketap",
            )

        if pre_boil_vol > 30.0:
            st.warning(
                f"⚠️ Målt pre-boil {pre_boil_vol:.1f} L overskrider BrewZilla 35 anbefalt maks (30 L)."
            )

        if pre_boil_sg > 1.001 and pre_boil_vol > 0 and post_boil_est > 0:
            forventet_og = beregn_post_boil_og(pre_boil_sg, pre_boil_vol, post_boil_est)
            og_diff      = forventet_og - ctx["og"]
            st.write("")
            fo1, fo2, fo3 = st.columns(3)
            fo1.metric("Planlagt OG",           fmt_og(ctx["og"]))
            fo2.metric("Forventet OG (etter kok)", fmt_og(forventet_og))
            fo3.metric("Avvik",                 f"{og_diff:+.3f}",
                       delta_color="inverse" if abs(og_diff) > 0.005 else "off")

        # Koking-tilsetninger
        kok_sett = [t for t in plan["tilsetninger"] if t["fase"] == "koking"]
        if kok_sett:
            st.write("")
            st.markdown("**🧪 Tilsetninger i koking**")
            for t in kok_sett:
                st.write(f"- **{t['navn']}** · {t['dose']} · {t['timing']}")
                st.caption(f"  {t['note']}")

        st.write("")
        st.markdown("**📐 Post-boil**")
        st.number_input(
            "Post-boil volum (L)",
            min_value=0.0, max_value=50.0, step=0.5, format="%.1f",
            key="bd_post_boil_vol",
        )

    # ── STEG 4: OVERFØRING & OG ─────────────────────────────────────────────
    with st.expander("⚗️ 4. Overføring & OG"):
        ov1, ov2, ov3 = st.columns(3)
        with ov1:
            st.text_input(
                f"OG (mål: {fmt_og(ctx['og'])})", placeholder="Faktisk", key="bd_og",
            )
        with ov2:
            st.number_input(
                "Pitching-temperatur (°C)",
                min_value=0.0, max_value=40.0, step=0.5, format="%.1f",
                key="bd_pitch_temp",
            )
        with ov3:
            st.text_input(
                "Notat ved overføring", placeholder="f.eks. klart, god aroma",
                key="bd_transfer_note",
            )

    # ── STEG 5: GJÆRING ─────────────────────────────────────────────────────
    with st.expander("🧬 5. Gjæring"):
        gjær_sett = [t for t in plan["tilsetninger"] if t["fase"] == "gjæring"]
        for t in gjær_sett:
            st.info(f"**{t['navn']}:** {t['dose']} — {t['note']}")

        ferm1, ferm2 = st.columns(2)
        with ferm1:
            st.date_input("Gjæringsstart", key="bd_ferm_start")
        with ferm2:
            st.date_input("Cold crash / tapping", key="bd_ferm_slutt")

        mon1, mon2 = st.columns(2)
        with mon1:
            st.text_input(
                "Inkbird-temperatur (°C)", placeholder="f.eks. 20.2",
                key="bd_inkbird_temp",
            )
        with mon2:
            st.text_input(
                "Gjæringstrykk", placeholder="f.eks. 0.8 bar",
                key="bd_ferm_pressure",
            )

        st.write("")
        fg1, fg2, fg3 = st.columns(3)
        with fg1:
            st.text_input(
                f"FG (mål: {fmt_fg(ctx['fg'])})", placeholder="Faktisk", key="bd_fg",
            )
        with fg2:
            st.text_input(
                f"ABV (mål: {fmt_abv(ctx['abv'])})", placeholder="Beregnet", key="bd_abv",
            )
        with fg3:
            try:
                og_f  = float(st.session_state.get("bd_og", "") or 0)
                fg_f  = float(st.session_state.get("bd_fg", "") or 0)
                if og_f > 1.001 and fg_f > 1.000:
                    st.metric("Beregnet ABV", f"{(og_f - fg_f) * 131.25:.1f}%")
            except (ValueError, TypeError):
                pass

    # ── STEG 6: EFFEKTIVITET ────────────────────────────────────────────────
    with st.expander("📊 6. Effektivitet"):
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
            "Maskeeffektivitet",
            f"{eff['mash_eff'] * 100:.1f}%" if pre_sg > 1.001 and pre_vol > 0 else "—",
        )
        ef2.metric(
            "Brygghuseffektivitet",
            f"{eff['brewhouse_eff'] * 100:.1f}%" if og_faktisk > 1.001 else "—",
        )
        ef3.metric("Planlagt effektivitet", f"{ctx['effektivitet'] * 100:.0f}%")

        if pre_sg <= 1.001 or pre_vol <= 0:
            st.caption("Fyll inn pre-boil SG og volum (Steg 3) for maskeeffektivitet.")
        if og_faktisk <= 1.001:
            st.caption("Fyll inn faktisk OG (Steg 4) for brygghuseffektivitet.")

    # ── SJEKKLISTE ──────────────────────────────────────────────────────────
    st.write("---")
    st.markdown("**✅ Bryggedags-sjekkliste**")
    chk_cols = st.columns(4)
    for i, item in enumerate(_SJEKKLISTE):
        chk_cols[i % 4].checkbox(item, key=f"bd_chk_{i}")

    # ── PRINT-ARK ───────────────────────────────────────────────────────────
    st.write("")
    # Eksport blokkeres ALDRI stille -- men ved en umulig humletid (se
    # varselet/IBU-sammenligningen over) må brukeren eksplisitt bekrefte
    # at avviket er sett før arket kan genereres, slik at et bryggedagsark
    # med en IBU som ikke er fysisk oppnåelig ikke presenteres som gyldig
    # uten videre.
    _eksport_ok = True
    if plan["humle_over_koketid"]:
        _eksport_ok = st.checkbox(
            "Jeg har sett avviket mellom planlagt og faktisk mulig IBU over, og vil eksportere likevel",
            key="bd_bekreft_humletid_avvik",
        )
        if not _eksport_ok:
            st.caption("🔒 Bryggedagsarket er låst til avviket over er bekreftet.")
    if st.button("🖨️ Generer Bryggedagsark", width="stretch", key="brewday_print_btn", disabled=not _eksport_ok):
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
        html     = render_brewday_html(ctx, plan, log, water=water)
        fil_navn = ctx["name"].replace(" ", "_").replace("/", "-") + "_bryggedag.html"
        st.download_button(
            label="📥 Last ned bryggedagsark",
            data=html,
            file_name=fil_navn,
            mime="text/html",
            width="stretch",
            key="brewday_download_btn",
        )
        st.info("💡 Åpne filen i nettleseren og trykk **Ctrl + P** for å skrive ut.")
