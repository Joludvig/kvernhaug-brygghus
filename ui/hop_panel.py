import streamlit as st
from modules.calculations import beregn_gram_fra_ibu

from bryggeskole import pilot_boil_hop as _pilot_koking
from ui.i18n import gjeldende_sprak, t

FORETRUKKET_HUMLE_OPPRINNELSE = [
    "Norsk", "Britisk", "Tysk", "Tsjekkisk", "Belgisk",
    "Australsk", "Newzealandsk",
]

# De fire eksisterende, verifiserte Koking/humle-læringsbolkene denne
# Learn -> Plan-broen viser (V2.2 G3M, issue #388) -- nøyaktig disse
# fire, i denne rekkefølgen, per docs/development/
# v22_g3l_boil_hop_learn_plan_contract.md §3/§4. CHUNK-BOILHOP-A/B
# (generell kokekjemi) gjenbrukes bevisst IKKE her -- de svarer på
# "hvorfor koker vi i det hele tatt", ikke "hvorfor betyr NÅR jeg
# tilsetter humle noe". Ingen ny undervisningstekst forfattes her; broen
# gjenbruker bryggeskole.pilot_boil_hop sin egen
# read_pilot_file()/render_chunk() uendret, akkurat som
# ui/process_panel.py/ui/yeast_panel.py allerede gjør for sine broer.
_LAER_BRO_CHUNK_IDER = (
    "CHUNK-BOILHOP-C", "CHUNK-BOILHOP-D", "CHUNK-BOILHOP-E", "CHUNK-BOILHOP-F",
)


def _render_laer_bro(sprak):
    """Kontekstuell Learn -> Plan-bro (V2.2 G3M, issue #388): en
    kollapset expander rett under humle-panelets header som viser
    CHUNK-BOILHOP-C/D/E/F fra den eksisterende, verifiserte
    Koking/humle-piloten -- read-only, ingen mastery-kall
    (evaluate_answer/apply_answer), ingen ny lagringstilstand, ingen
    Registry-/pilot-mutasjon. Rendres nøyaktig én gang uansett antall
    humlerader (ikke per rad). Ugyldig pilotinnhold (PilotContentError)
    skal aldri krasje Oppskrift-fanen, samme mønster som
    ui/process_panel.py/ui/yeast_panel.py/ui/bryggeskole_panel.py.

    Guardrailen etter chunkene disloserer, uten å reparere, at det
    eksisterende "Tid (Min)"-feltet, IBU/gram-kalkulatoren og
    bryggedagsplanen kun modellerer aktiv koketid i minutter -- en
    ekte flameout/whirlpool/hop-stand er ikke representert av dette
    feltet i dagens App (kontrakten §5/§8), og læreren skal derfor
    aldri late som om et vilkårlig lavt minuttall er en trofast
    whirlpool-koding."""
    with st.expander(t("koking.laer_bro.tittel"), expanded=False):
        try:
            pilot = _pilot_koking.read_pilot_file()
        except _pilot_koking.PilotContentError:
            st.error(t("bryggeskole.feil.innhold_ugyldig"))
            return
        chunker = {c["id"]: c for c in pilot["chunks"]}
        for chunk_id in _LAER_BRO_CHUNK_IDER:
            st.markdown(_pilot_koking.render_chunk(chunker[chunk_id], sprak)["text"])
        st.warning(t("koking.laer_bro.guardrail"))
        st.caption(t("koking.laer_bro.footer"))


def render_hop_panel(humle_database):
    st.header("🌿 Humle-tilsetninger")
    _render_laer_bro(gjeldende_sprak())

    _default_h_id = next(
        (hid for hid in humle_database if "east_kent" in hid),
        next(iter(humle_database), "citra"),
    )
    if st.button("➕ Legg til humle", key="add_hop_btn"):
        st.session_state.valgt_humle.append({"id": _default_h_id, "gram": 20, "tid": 5})
        st.rerun()

    humle_id_kart = {}
    humle_etter_opprinnelse = {}
    for h_id, info in humle_database.items():
        if info:
            opprinnelse = info.get("opprinnelse") or "Andre"
            if opprinnelse == "Ukjent":
                opprinnelse = "Andre"
            visnings_navn = (
                f"{info.get('display_name', h_id)} ({opprinnelse})"
                if opprinnelse != "Andre"
                else info.get("display_name", h_id)
            )
            humle_id_kart[visnings_navn] = h_id
            humle_etter_opprinnelse.setdefault(opprinnelse, []).append(visnings_navn)

    alle_oppr = set(humle_etter_opprinnelse)
    sortert_oppr = [o for o in FORETRUKKET_HUMLE_OPPRINNELSE if o in alle_oppr]
    sortert_oppr += sorted(o for o in alle_oppr if o not in FORETRUKKET_HUMLE_OPPRINNELSE)

    humle_meny_valg = []
    for oppr in sortert_oppr:
        humle_meny_valg.append(f"--- {oppr.upper()} ---")
        humle_meny_valg.extend(sorted(humle_etter_opprinnelse[oppr]))

    if not humle_meny_valg:
        standard_visning = "Citra"
        humle_meny_valg = [standard_visning]
        humle_id_kart[standard_visning] = "citra"

    _v = st.session_state.get("import_versjon", 0)

    # Apply pending gram update before any widget is instantiated (avoids StreamlitAPIException)
    if "_pending_humle_gram" in st.session_state:
        _pg = st.session_state.pop("_pending_humle_gram")
        if _pg.get("v") == _v:
            st.session_state[f"humle_gram_{_pg['j']}_v{_v}"] = _pg["gram"]

    oppdatert_humle_liste = []
    for j, h_item in enumerate(st.session_state.valgt_humle):
        with st.container():
            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([2.8, 1.0, 1.2, 1.2, 1.3, 0.5])
            gjeldende_h_id = h_item["id"]
            gjeldende_h_visning = next((v for v, hid in humle_id_kart.items() if hid == gjeldende_h_id), None)
            if not gjeldende_h_visning or gjeldende_h_visning not in humle_meny_valg:
                gjeldende_h_visning = next(
                    (v for v in humle_meny_valg if not v.startswith("---")),
                    humle_meny_valg[0] if humle_meny_valg else "",
                )
            standard_h_indeks = humle_meny_valg.index(gjeldende_h_visning)

            with h_col1:
                valgt_h_visning = st.selectbox(f"Humle #{j+1}", humle_meny_valg, key=f"humle_ui_{j}_v{_v}", index=standard_h_indeks)
                if valgt_h_visning and valgt_h_visning.startswith("---"):
                    valgt_h_visning = next((v for v in humle_meny_valg if not v.startswith("---")), valgt_h_visning)
                ny_h_id = humle_id_kart.get(valgt_h_visning, next(iter(humle_id_kart.values()), ""))
            with h_col2:
                nytt_gram = st.number_input("Gram", min_value=0.0, value=float(h_item["gram"]), step=5.0, key=f"humle_gram_{j}_v{_v}")
            with h_col3:
                ny_tid = st.number_input("Tid (Min)", min_value=0, max_value=120, value=h_item["tid"], step=5, key=f"humle_tid_{j}_v{_v}")

            h_alfa, h_smak, h_pris = 0.0, "", "0.0 kr"
            if ny_h_id in humle_database:
                h_info = humle_database[ny_h_id]
                h_alfa = h_info.get("alfa_typisk") or h_info.get("alfa", 12.0)
                smakstags_liste = h_info.get("smakstags") or []
                h_smak = ", ".join(smakstags_liste)
                butikk_navn = st.session_state.get("global_butikk", "Ølbrygging.no")
                h_pris_nokkel = "pris_olbrygging" if butikk_navn == "Ølbrygging.no" else "pris_vestbrygg"
                h_pris = f"{(nytt_gram * h_info.get(h_pris_nokkel, 99.0) / 100):.1f} kr"
            else:
                h_alfa = 12.0
                h_pris = f"{(nytt_gram * 99.0 / 100):.1f} kr"

            bruk_type = "Bitter" if ny_tid >= 60 else ("Smak" if ny_tid >= 15 else ("Aroma" if ny_tid > 0 else "Tørrhumle"))
            with h_col4: st.text_input("Bruk", value=f"{bruk_type} ({h_alfa}% Alfa)", disabled=True, key=f"humle_type_{j}_v{_v}")
            with h_col5: st.text_input("Pris", value=h_pris, disabled=True, key=f"humle_pris_{j}_v{_v}")
            with h_col6:
                st.write(" ")
                if st.button("❌", key=f"slett_humle_{j}_v{_v}"):
                    st.session_state.valgt_humle.pop(j)
                    st.rerun()
            if h_smak:
                st.caption(f"👃 *Smak:* {h_smak}")

            if ny_tid > 0:
                ibu_col, beregn_col = st.columns([1.5, 1.5])
                with ibu_col:
                    maal_ibu = st.number_input(
                        "Mål-IBU (denne tilsetningen)",
                        min_value=0.0, value=0.0, step=1.0, format="%.1f",
                        key=f"humle_maal_ibu_{j}_v{_v}",
                    )
                with beregn_col:
                    st.write(" ")
                    if st.button("Beregn gram", key=f"humle_beregn_{j}_v{_v}", width="stretch"):
                        if maal_ibu > 0:
                            _og = st.session_state.get("_last_og", 1.050)
                            _volum = st.session_state.get("batch_volum_input", 20.0)
                            _gram = beregn_gram_fra_ibu(maal_ibu, h_alfa, ny_tid, _volum, _og)
                            if _gram > 0:
                                st.session_state["_pending_humle_gram"] = {"j": j, "v": _v, "gram": _gram}
                                st.rerun()
                        else:
                            st.warning("Skriv inn ønsket IBU først.")

            st.write("")
            oppdatert_humle_liste.append({"id": ny_h_id, "gram": nytt_gram, "tid": ny_tid})
    st.session_state.valgt_humle = oppdatert_humle_liste
