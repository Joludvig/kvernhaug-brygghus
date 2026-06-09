# ui/recipe_card.py
import re
import os
import streamlit as st
from datetime import date
from modules.recipe_storage import lagre_oppskrift, slett_oppskrift_fil, lagre_logg_entry, hent_logg
from modules.recipe import bygg_recipe_object
from modules.card_template import render_card_html, render_a4_html
from ui.branding import _logo_base64

_LOGO_PATH = os.path.join("assets", "branding", "master_v1_transparent.png")

def _render_brewday_result_panel(ctx):
    if st.session_state.get("_last_loaded_recipe") != ctx["name"]:
        return

    logg = hent_logg(ctx["name"])

    with st.expander(f"📓 Bryggelogg ({len(logg)} oppføringer)" if logg else "📓 Bryggelogg", expanded=False):
        with st.form("brewday_logg_form"):
            st.markdown("**Nytt brygg**")
            col_og, col_fg = st.columns(2)
            with col_og:
                actual_og = st.number_input(
                    "Faktisk OG",
                    min_value=1.000, max_value=1.200, step=0.001, format="%.3f",
                    value=float(ctx["og"]),
                )
            with col_fg:
                actual_fg = st.number_input(
                    "Faktisk FG (valgfritt)",
                    min_value=1.000, max_value=1.200, step=0.001, format="%.3f",
                    value=float(ctx["fg"]),
                )
            col_dato, col_vol = st.columns(2)
            with col_dato:
                brew_date = st.date_input("Bryggedato", value=date.today())
            with col_vol:
                actual_volume = st.number_input(
                    "Volum til gjæring (L)",
                    min_value=0.0, max_value=200.0, step=0.5,
                    value=float(ctx["volum"]),
                )
            note = st.text_area("Notat", height=68)

            if st.form_submit_button("Legg til loggoppføring", use_container_width=True):
                entry = {
                    "date": brew_date.isoformat(),
                    "actual_volume_l": actual_volume,
                    "actual_og": actual_og,
                    "actual_fg": actual_fg,
                    "actual_abv": round((actual_og - actual_fg) * 131.25, 1),
                    "note": note.strip(),
                }
                lagre_logg_entry(ctx["name"], entry)
                st.toast("Loggoppføring lagret!", icon="📓")
                st.rerun()

        if logg:
            st.write("---")
            for entry in reversed(logg):
                abv_str = f" · ABV {entry['actual_abv']:.1f}%" if entry.get("actual_abv") else ""
                st.markdown(
                    f"**{entry.get('date', '-')}** · "
                    f"{entry.get('actual_volume_l', 0):.1f} L · "
                    f"OG {entry.get('actual_og', 1.0):.3f} · "
                    f"FG {entry.get('actual_fg', 1.0):.3f}"
                    f"{abv_str}"
                )
                if entry.get("note"):
                    st.caption(entry["note"])

def render_recipe_card(ctx, malt_database, humle_database, gjaer_database):
    # Bryggnavn, batchvolum og bryggerstil
    navn_col, vol_col = st.columns([3, 1.5])
    with navn_col:
        st.text_input("Bryggnavn", key="gjeldende_navn")
    with vol_col:
        st.number_input("Liter", min_value=1.0, max_value=200.0, step=1.0, key="batch_volum_input")
    st.text_input(
        "Bryggerstil (vises på kortet — BJCP-analysen vises sekundært)",
        key="brygger_stil",
        placeholder="Eksempel: Imperial Nordisk Røykstaut",
    )

    # Oppdater-knapp: kun når en oppskrift er aktivt lastet inn
    if st.session_state.get("_last_loaded_recipe"):
        if st.button("🔄 Oppdater oppskrift", use_container_width=True, key="oppdater_oppskrift_btn"):
            ny_recipe = bygg_recipe_object(
                ctx["name"], ctx["volum"], efficiency=ctx["effektivitet"],
                malts=st.session_state.valgt_malt, hops=st.session_state.valgt_humle,
                yeast=st.session_state.valgt_gjaer_id,
                og=ctx["og"], fg=ctx["fg"], abv=ctx["abv"],
                ibu=ctx["ibu"], ebc=ctx["ebc"], flavor_profile={},
                brygger_stil=ctx.get("brygger_stil", ""),
            )
            lagre_oppskrift(ny_recipe)
            st.session_state["_last_loaded_recipe"] = ctx["name"]
            st.toast(f"Oppdatert: {ctx['name']}", icon="🔄")
            st.rerun()

    # Lagre som ny/kopi og slett
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("💾 Lagre oppskrift", use_container_width=True):
            ny_recipe = bygg_recipe_object(ctx["name"], ctx["volum"], efficiency=ctx["effektivitet"], malts=st.session_state.valgt_malt, hops=st.session_state.valgt_humle, yeast=st.session_state.valgt_gjaer_id, og=ctx["og"], fg=ctx["fg"], abv=ctx["abv"], ibu=ctx["ibu"], ebc=ctx["ebc"], flavor_profile={}, brygger_stil=ctx.get("brygger_stil", ""))
            lagre_oppskrift(ny_recipe)
            st.toast(f"Oppskriften ble lagret!", icon="💾")
            st.rerun()
    with btn_col2:
        if st.button("🗑️ Slett gjeldende", use_container_width=True):
            if slett_oppskrift_fil(ctx["name"]):
                st.toast(f"Slettet {ctx['name']}", icon="🗑️")
                st.session_state.valgt_malt = [{"id": "weyermann_pilsner", "mengde": 5.0}]
                st.session_state.valgt_humle = [{"id": "magnum_de", "gram": 20, "tid": 60}]
                st.session_state.valgt_gjaer_id = "safale_us_05"
                st.session_state.gjeldende_navn = "Kvernhaug Spesial"
                st.session_state["_pending_brygger_stil_reset"] = True
                st.rerun()

    with st.expander("📐 Skaler oppskrift"):
        original = st.session_state.get("_original_batch_size")
        if original and abs(original - ctx["volum"]) > 0.01:
            st.caption(f"Original: {original:.0f} L · Gjeldende: {ctx['volum']:.0f} L")
        maal = st.number_input(
            "Skalér til (L)",
            min_value=1.0, max_value=200.0, step=0.5,
            value=float(ctx["volum"]),
            key="skaler_maal_volum",
        )
        if st.button("Skaler oppskrift", use_container_width=True, key="skaler_btn"):
            if abs(maal - ctx["volum"]) < 0.01:
                st.warning("Mål-volum er allerede lik gjeldende volum.")
            else:
                faktor = maal / ctx["volum"]
                st.session_state.valgt_malt = [
                    {**m, "mengde": round(m["mengde"] * faktor, 3)}
                    for m in st.session_state.valgt_malt
                ]
                st.session_state.valgt_humle = [
                    {**h, "gram": round(h["gram"] * faktor, 1)}
                    for h in st.session_state.valgt_humle
                ]
                st.session_state["_pending_batch_volum"] = maal
                base_navn = re.sub(r' - \d+(?:\.\d+)?L batch$', '', st.session_state.get("gjeldende_navn", ""))
                st.session_state["_pending_gjeldende_navn"] = f"{base_navn} - {maal:g}L batch"
                st.session_state["_pending_import_versjon_bump"] = True
                st.rerun()
        st.caption("💡 Endre navn før lagring for å ikke overskrive originalen.")

    logo_b64 = _logo_base64() if os.path.exists(_LOGO_PATH) else None

    # Dynamisk høyde: base + per rad malt/humle + ekstra for bryggerstil
    _n_malt = len(ctx["recipe"].get("malts", []))
    _n_humle = len(ctx["recipe"].get("hops", []))
    _card_h = 1110 + max(0, _n_malt - 3) * 30 + max(0, _n_humle - 3) * 30
    if ctx.get("brygger_stil", "").strip():
        _card_h += 30

    st.components.v1.html(
        render_card_html(ctx, malt_database, humle_database, gjaer_database, logo_b64=logo_b64),
        height=_card_h,
        scrolling=False,
    )

    _render_brewday_result_panel(ctx)

    if st.button("🖨️ Generer utskriftsvennlig ark (A4)", use_container_width=True):
        html_dokument = render_a4_html(ctx, malt_database, humle_database, gjaer_database)
        fil_navn = ctx["name"].replace(" ", "_").replace("/", "-") + ".html"
        st.download_button(
            label="📥 Last ned oppskriftsark",
            data=html_dokument,
            file_name=fil_navn,
            mime="text/html",
            use_container_width=True,
        )
        st.info("💡 Åpne filen i nettleseren og trykk **Ctrl + P** for å skrive ut.")
