# ui/recipe_card.py
import json
import re
import os
import uuid
import streamlit as st
from datetime import date, datetime, timezone
from config import DEMO_MODE
from modules.recipe_storage import (
    lagre_oppskrift,
    slett_oppskrift_fil,
    lagre_logg_entry,
    hent_logg,
    sikre_origin_recipe_id,
    OppskriftNavnKollisjon,
    UgyldigKildefilnavn,
    LoggKorruptError,
    LegacyLoggKandidatUkjent,
)
from modules.calculations import beregn_abv_standard
from modules.recipe import bygg_recipe_object
from modules.kbh_contract import bygg_kbhrecipe_konvolutt, UgyldigOppskriftForEksport
from modules.kbh_import_apply import NESTE_VARIANT_FROSSEN_ORIGIN_ID_NOKKEL
from modules.kbhbrew_storage import hent_alle_brews
from modules.kbhbrew_ui import oppskrift_har_kbhbrew
from modules.card_template import render_card_html, render_a4_html
from ui.branding import _logo_base64
from ui.sidebar import _SETT_OPPSKRIFT_SELECTOR_NESTE_RENDER

_LOGO_PATH = os.path.join("assets", "branding", "kbh_emblem_master.png")

def _render_brewday_result_panel(ctx):
    if st.session_state.get("_last_loaded_recipe") != ctx["name"]:
        return

    # En korrupt loggfil skal ALDRI stille fremstå som "ingen brygg
    # registrert" -- det ville latt et påfølgende "Legg til
    # loggoppføring"-klikk overskrive hele den (fortsatt bevarte, se
    # modules/recipe_storage.py::hent_logg()) historikken med bare den
    # ene, nye oppføringen. Vis i stedet en tydelig feil og la
    # skjemaet stå av til filen er reparert/gjenopprettet manuelt.
    try:
        logg = hent_logg(ctx["name"])
        logg_korrupt = None
    except LoggKorruptError as e:
        logg = []
        logg_korrupt = e

    # Issue #256 (Phase 3B durable decision #253) -- App eier det
    # gjeldende strukturerte bryggrecordet; Web/legacy-loggen er ALDRI
    # en parallell "live" logg. Skal ALDRI skjule den gamle Bryggeloggen
    # (historisk kompatibilitet, se saken), men et brygg som allerede
    # finnes som .kbhbrew for DENNE oppskriften skal advares tydelig FØR
    # skjemaet under -- samme batch skal aldri logges dobbelt.
    if oppskrift_har_kbhbrew(hent_alle_brews(), st.session_state.get("_last_loaded_recipe_file")):
        st.warning(
            "⚠️ Denne oppskriften har ett eller flere registrerte brygg i "
            "**Bryggdag** (`.kbhbrew`). Bruk Bryggdag for å logge det "
            "aktive/nåværende brygget — den gamle Bryggeloggen under er kun "
            "historisk, og samme batch skal ikke logges begge steder."
        )

    with st.expander(f"📓 Bryggelogg ({len(logg)} oppføringer)" if logg else "📓 Bryggelogg", expanded=False):
        if logg_korrupt is not None:
            st.error(f"❌ Bryggeloggen for «{ctx['name']}» kunne ikke leses: {logg_korrupt}")
            return

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

            if st.form_submit_button("Legg til loggoppføring", width="stretch"):
                _profil = st.session_state.get("aktiv_prosessprofil")
                try:
                    actual_abv = round(beregn_abv_standard(actual_og, actual_fg), 1)
                except ValueError:
                    # Ugyldig måling (f.eks. FG > OG) -- lagre ingen ABV
                    # fremfor en stille feil negativ verdi.
                    actual_abv = None
                entry = {
                    "date": brew_date.isoformat(),
                    "actual_volume_l": actual_volume,
                    "actual_og": actual_og,
                    "actual_fg": actual_fg,
                    "actual_abv": actual_abv,
                    "note": note.strip(),
                    "process_profile_navn": _profil["navn"] if _profil else None,
                }
                try:
                    lagre_logg_entry(ctx["name"], entry)
                except LoggKorruptError as e:
                    st.error(f"❌ Kunne ikke lagre loggoppføringen: {e}")
                else:
                    st.toast("Loggoppføring lagret!", icon="📓")
                    st.rerun()

        if logg:
            st.write("---")
            for entry in reversed(logg):
                abv_str = f" · ABV {entry['actual_abv']:.1f}%" if entry.get("actual_abv") else ""
                prosess_str = f" · {entry['process_profile_navn']}" if entry.get("process_profile_navn") else ""
                st.markdown(
                    f"**{entry.get('date', '-')}** · "
                    f"{entry.get('actual_volume_l', 0):.1f} L · "
                    f"OG {entry.get('actual_og', 1.0):.3f} · "
                    f"FG {entry.get('actual_fg', 1.0):.3f}"
                    f"{abv_str}{prosess_str}"
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

    def _bygg_recipe_fra_session(ctx, origin_recipe_id=None):
        return bygg_recipe_object(
            st.session_state.get("gjeldende_navn") or "Kvernhaug Spesial",
            st.session_state.get("batch_volum_input", 20.0),
            efficiency=ctx["effektivitet"],
            malts=st.session_state.get("valgt_malt", []),
            hops=st.session_state.get("valgt_humle", []),
            yeast=st.session_state.get("valgt_gjaer_id", "safale_us_05"),
            og=ctx["og"], fg=ctx["fg"], abv=ctx["abv"],
            ibu=ctx["ibu"], ebc=ctx["ebc"],
            # Den faktisk BEREGNEDE smaksprofilen (ctx["recipe"] er
            # ferskt bygget av bygg_recipe_context() for denne konteksten)
            # -- IKKE en hardkodet tom dict, som tidligere kastet bort
            # smakspoengene ved hver lagring.
            flavor_profile=ctx["recipe"].get("flavor_profile", {}),
            brygger_stil=st.session_state.get("brygger_stil", ""),
            process_profile=st.session_state.get("aktiv_prosessprofil"),
            water_source_profile=st.session_state.get("aktiv_vannkilde_snapshot"),
            water_target_profile=st.session_state.get("aktiv_vannmaal_snapshot"),
            water_treatment=st.session_state.get("aktiv_vannbehandling"),
            water_measurements=st.session_state.get("aktiv_vannmaalinger"),
            # PRI 2C2 (KBHR-011/KBHR-014) -- ikke-beregningspåvirkende
            # metadata bevart opakt fra en tidligere .kbhrecipe-import
            # (hydrert av ui/sidebar.py ved load, se
            # _aktiv_kbh_passthrough) må følge med gjennom HVER
            # rebygging, akkurat som brygger_stil/prosessprofil/vann
            # over -- ellers ville et vanlig "Lagre endringer"-klikk
            # stille mistet metadataen.
            kbh_passthrough=st.session_state.get("_aktiv_kbh_passthrough"),
            # issue #283 (CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md §3.2/§3.5) --
            # kalleren avgjør EKSPLISITT hva som skal skje med identiteten
            # for HVER handling (preserve ved "Lagre endringer"/eksport,
            # fresh mint ved "Lagre som ny kopi") -- ALDRI et implisitt
            # session_state-fallback her, siden det ville latt en kopi
            # arve kildens origin ved en feil.
            origin_recipe_id=origin_recipe_id,
        )

    if not DEMO_MODE:
        # Lagre endringer: overskriv aktiv oppskrift (i tilfelle av
        # navneendring: skriver ny fil FØRST, arkiverer deretter den
        # gamle kildefilen -- se
        # modules/recipe_storage.py::lagre_oppskrift()).
        if st.session_state.get("_last_loaded_recipe"):
            if st.button("💾 Lagre endringer", width="stretch", key="lagre_endringer_btn"):
                # issue #283 -- en vanlig redigering/re-lagring av SAMME
                # oppskrift skal ALDRI endre originRecipeId (§3.2 siste
                # kulepunkt: "aldri re-mintet av en senere vanlig
                # redigering/re-lagring") -- preserver den aktive verdien
                # uendret (None hvis oppskriften ennå ikke har noen).
                ny_recipe = _bygg_recipe_fra_session(
                    ctx, origin_recipe_id=st.session_state.get("_aktiv_kbh_origin_recipe_id")
                )
                _gammelt_filnavn = st.session_state.get("_last_loaded_recipe_file")
                try:
                    nytt_filnavn = lagre_oppskrift(
                        ny_recipe,
                        kilde_filnavn=_gammelt_filnavn,
                    )
                except (OppskriftNavnKollisjon, UgyldigKildefilnavn, LegacyLoggKandidatUkjent) as e:
                    st.error(f"❌ {e}")
                else:
                    st.session_state["_last_loaded_recipe"] = ny_recipe["name"]
                    st.session_state["_last_loaded_recipe_file"] = nytt_filnavn
                    st.session_state["_gjeldende_navn_preserved"] = ny_recipe["name"]
                    st.toast(f"Lagret: {ny_recipe['name']}", icon="💾")
                    # App A3 (issue #237, fiks A3-4) -- en navneendring her
                    # ugyldiggjør et evt. aktivt Bryggdag-brygg (App A1,
                    # issue #170, via ui/kbhbrew_panel.py::
                    # _sinkroniser_aktiv_brew_mot_oppskrift() sin
                    # identitetssjekk mot NETTOPP _last_loaded_recipe_file)
                    # -- uten en umiddelbar rerun forble det usynlig helt
                    # til neste, urelaterte rerun. Et lagre-klikk UTEN
                    # navneendring får INGEN ny rerun-oppførsel (samme
                    # synlige suksess-semantikk som før denne fiksen).
                    if nytt_filnavn != _gammelt_filnavn:
                        # App A4-3 (issue #246) -- uten dette forblir
                        # ui/sidebar.py sin "sidebar_recipe_selector"-widget
                        # bundet til det GAMLE navnet, som ikke lenger finnes
                        # i den ferske oppskrift-listen etter omdøpingen.
                        # Streamlit faller da selv tilbake til plassholder-
                        # indeksen for widgeten, og sidebarens EGEN,
                        # eksisterende "elif valgt_lagret_navn ==
                        # _INGEN_OPPSKRIFT_VALGT"-gren (ment for et bevisst
                        # plassholder-valg) tolker det som nettopp det -- og
                        # sletter _last_loaded_recipe/_last_loaded_recipe_file
                        # vi NETTOPP satte over, rett før de i det hele tatt
                        # rekker å bli lest andre steder i denne rerunen. Kan
                        # ikke settes direkte her (selectboksen er allerede
                        # instansiert lenger OPPE i script-kjøringen enn
                        # denne knappen) -- samme fallgruve/løsningsmønster
                        # som _nullstill_oppskrift_selector_neste_render
                        # (issue #242, se ui/sidebar.py): et engangsflagg
                        # konsumert i render_sidebar() FØR selectboksen
                        # instansieres på den kommende rerunen.
                        st.session_state[_SETT_OPPSKRIFT_SELECTOR_NESTE_RENDER] = ny_recipe["name"]
                        st.rerun()

        # Lagre som ny kopi og slett
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("💾 Lagre som ny kopi", width="stretch", key="lagre_ny_kopi_btn"):
                # issue #283 (§3.5, Chief-korreksjon PR #286) -- "Lagre som
                # ny kopi" skal ALDRI arve kildeoppskriftens originRecipeId
                # (ville kollidert med kilden ved en senere .kbhrecipe-
                # import av begge), men skal heller ikke lagres UTEN en
                # egen origin i mellomtiden -- kontrakten krever at kopien
                # får en FRESH originRecipeId med det samme, ikke først ved
                # en senere eksport. Mintes derfor her, direkte -- dette er
                # det ENE unntaket fra "App minter aldri ved lagring"
                # (§3.2/§8), siden §3.5 eksplisitt krever mint nettopp ved
                # denne handlingen.
                #
                # issue #363 (V2.2 G2D) unntak fra unntaket: en oppskrift
                # seedet av "🌱 Opprett neste variant"
                # (ui/kbhbrew_history_panel.py) har ALLEREDE fått en
                # fersk originRecipeId mintet VED seed-tidspunktet
                # (kontraktens §4.1-krav -- FØR utkastet i det hele tatt
                # ble redigerbart), og den ID-en må overleve UENDRET til
                # denne aller første lagringen -- IKKE erstattes av enda
                # en, ANNEN fersk id her. `_frossen_neste_variant_id`
                # gjenbrukes KUN når den fortsatt er lik den nåværende
                # aktive origin-ID-en (dvs. ingenting -- et sidebar-load,
                # en .kbhrecipe-import, en annen lagring -- har rukket å
                # overskrive den i mellomtiden); ellers mintes det som før.
                # Konsumeres (fjernes) her uansett utfall av selve
                # mint-avgjørelsen, slik at et senere, urelatert
                # "Lagre som ny kopi"-klikk aldri kan gjenbruke en gammel,
                # frossen id fra en tidligere seed-handling.
                _frossen_neste_variant_id = st.session_state.pop(NESTE_VARIANT_FROSSEN_ORIGIN_ID_NOKKEL, None)
                _origin_recipe_id_for_kopi = (
                    _frossen_neste_variant_id
                    if _frossen_neste_variant_id is not None
                    and _frossen_neste_variant_id == st.session_state.get("_aktiv_kbh_origin_recipe_id")
                    else str(uuid.uuid4())
                )
                ny_recipe = _bygg_recipe_fra_session(ctx, origin_recipe_id=_origin_recipe_id_for_kopi)
                try:
                    # kilde_filnavn=None -- en ny kopi har per definisjon
                    # ingen kjent tidligere kildefil.
                    # bloker_ved_navnekollisjon=True: skal ALDRI kunne
                    # overskrive en annen eksisterende oppskrift stille.
                    lagre_oppskrift(ny_recipe, kilde_filnavn=None, bloker_ved_navnekollisjon=True)
                except OppskriftNavnKollisjon as e:
                    st.error(f"❌ {e}")
                else:
                    st.toast(f"Lagret: {ny_recipe['name']}", icon="💾")
        with btn_col2:
            # Arkivering skal ALLTID skje på den FAKTISKE kildefilen
            # oppskriften ble lastet fra (_last_loaded_recipe_file, satt
            # av ui/sidebar.py) -- ALDRI gjettet på nytt fra det
            # redigerbare navnefeltet via generer_filnavn(). Et filnavn
            # på disk kan avvike fra det navnet nå produserer (se
            # modules/recipe_storage.py::slett_oppskrift_fil()).
            _kilde_filnavn = st.session_state.get("_last_loaded_recipe_file")
            _slett_bekreft_naavaerende = st.session_state.get("_pending_slett_bekreft") == ctx["name"]
            if not _slett_bekreft_naavaerende:
                if st.button(
                    "🗑️ Slett gjeldende", width="stretch", key="slett_gjeldende_btn",
                    disabled=not _kilde_filnavn,
                ):
                    st.session_state["_pending_slett_bekreft"] = ctx["name"]
                    st.rerun()
                if not _kilde_filnavn:
                    st.caption("Ingen lagret kildefil å arkivere ennå — lagre oppskriften først.")
            else:
                st.warning(f"Arkivere «{ctx['name']}»? Filen flyttes til _archive/, ikke slettes permanent.")
                bekreft_col, avbryt_col = st.columns(2)
                with bekreft_col:
                    if st.button("✅ Bekreft", width="stretch", key="slett_bekreft_btn"):
                        try:
                            arkivert = slett_oppskrift_fil(_kilde_filnavn) if _kilde_filnavn else False
                        except (UgyldigKildefilnavn, LegacyLoggKandidatUkjent) as e:
                            st.error(f"❌ Kunne ikke arkivere «{ctx['name']}»: {e}")
                        else:
                            if arkivert:
                                st.toast(f"Arkivert: {ctx['name']}", icon="🗑️")
                                st.session_state.valgt_malt = [{"id": "weyermann_pilsner", "mengde": 5.0}]
                                st.session_state.valgt_humle = [{"id": "magnum_de", "gram": 20, "tid": 60}]
                                st.session_state.valgt_gjaer_id = "safale_us_05"
                                # PRI 2C0 (KBHR-019) -- en ny, blank oppskrift skal
                                # igjen følge utstyrsprofilen, ikke arve efficiency
                                # fra oppskriften som nettopp ble arkivert. Ikke
                                # widget-bundet -- kan settes direkte (se app.py).
                                st.session_state["_aktiv_recipe_efficiency"] = None
                                # PRI 2C2 (KBHR-011/KBHR-014) -- en ny,
                                # blank oppskrift skal IKKE arve den
                                # nettopp arkiverte oppskriftens bevarte
                                # import-metadata. Ikke widget-bundet --
                                # kan settes direkte, samme mønster som
                                # _aktiv_recipe_efficiency over.
                                st.session_state["_aktiv_kbh_passthrough"] = None
                                # issue #283 -- samme prinsipp som
                                # _aktiv_kbh_passthrough over: en ny, blank
                                # oppskrift skal ikke arve den nettopp
                                # arkiverte oppskriftens originRecipeId.
                                st.session_state["_aktiv_kbh_origin_recipe_id"] = None
                                # "gjeldende_navn" er bundet til Bryggnavn-widgeten
                                # (instansiert lenger opp i DENNE samme renderingen)
                                # -- kan derfor ikke settes direkte her (Streamlit
                                # tillater ikke å skrive til en widget-bundet nøkkel
                                # etter at widgeten selv er opprettet). Bruker samme
                                # "pending"-mønster som skaleringsflyten
                                # (app.py løser den opp FØR widgeten instansieres
                                # i neste kjøring).
                                st.session_state["_pending_gjeldende_navn"] = "Kvernhaug Spesial"
                                st.session_state["_pending_brygger_stil_reset"] = True
                                st.session_state.pop("_last_loaded_recipe_file", None)
                            else:
                                # Aldri nullstill oppskriften i UI-et når arkiveringen
                                # feilet -- brukeren skal fortsatt se (og kunne prøve
                                # på nytt med) den samme, urørte oppskriften.
                                st.error(
                                    f"❌ Fant ikke kildefilen for «{ctx['name']}» — "
                                    "ingenting ble arkivert. Prøv å laste oppskriften på nytt."
                                )
                        st.session_state.pop("_pending_slett_bekreft", None)
                        st.rerun()
                with avbryt_col:
                    if st.button("Avbryt", width="stretch", key="slett_avbryt_btn"):
                        st.session_state.pop("_pending_slett_bekreft", None)
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
        if st.button("Skaler oppskrift", width="stretch", key="skaler_btn"):
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

    # height="content" ber Streamlit måle kortets FAKTISKE rendrede
    # DOM-høyde i nettleseren og sette iframen til nøyaktig den høyden --
    # ingen Python-side pikselanslag (tittellengde, antall rader,
    # smaksprofillengde, fontrendering, vindusbredde, ...) kan noen gang
    # komme i utakt med det ekte innholdet, siden vi ikke lenger gjetter i
    # det hele tatt. Bekreftet støttet i den installerte Streamlit-versjonen
    # (se requirements.txt, hevet til å matche); ikke verifisert mot den
    # gamle nedre grensen 1.35.
    st.iframe(
        render_card_html(ctx, malt_database, humle_database, gjaer_database, logo_b64=logo_b64),
        width="stretch",
        height="content",
    )

    if not DEMO_MODE:
        _render_brewday_result_panel(ctx)

    with st.expander("📐 Eksporter / arkiver oppskrift"):
        st.caption("Lag et statisk A4-ark med ingrediensliste, stilanalyse og smaksprofil. Bryggedagsarket (under) er primær utskrift for selve bryggingen.")
        if st.button("🖨️ Generer utskriftsvennlig ark (A4)", width="stretch"):
            html_dokument = render_a4_html(ctx, malt_database, humle_database, gjaer_database)
            fil_navn = ctx["name"].replace(" ", "_").replace("/", "-") + ".html"
            st.download_button(
                label="📥 Last ned oppskriftsark",
                data=html_dokument,
                file_name=fil_navn,
                mime="text/html",
                width="stretch",
            )
            st.info("💡 Åpne filen i nettleseren og trykk **Ctrl + P** for å skrive ut.")

        st.write("---")
        st.caption("Eksporter oppskriften som en portabel .kbhrecipe-fil (KBH Core Contract V1) — kan åpnes i Kvernhaug Brygghus Web.")
        if st.button("📦 Eksporter KBH-oppskrift (.kbhrecipe)", width="stretch"):
            # issue #283 (CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md §3.2) --
            # App sitt ENESTE mint-tidspunkt: hvis den lagrede kildefilen
            # (om noen) mangler en gyldig originRecipeId, mintes en fresh
            # uuid4 og skrives atomisk tilbake til AKKURAT den ene filen
            # HER, FØR selve eksporten bygges -- aldri ved vanlig
            # lasting/redigering/lagring (se
            # modules/recipe_storage.py::sikre_origin_recipe_id()). En
            # HELT ny, aldri lagret oppskrift har ingen fil å mint til --
            # da faller vi tilbake til en evt. allerede-aktiv origin (f.eks.
            # nettopp importert, men ikke lagret ennå); en helt fersk,
            # aldri importert oppskrift eksporteres da uten feltet
            # (valgfritt V1-felt, §3.1).
            _kilde_filnavn_eksport = st.session_state.get("_last_loaded_recipe_file")
            if _kilde_filnavn_eksport:
                _origin_recipe_id = sikre_origin_recipe_id(_kilde_filnavn_eksport)
                if _origin_recipe_id:
                    st.session_state["_aktiv_kbh_origin_recipe_id"] = _origin_recipe_id
            else:
                _origin_recipe_id = st.session_state.get("_aktiv_kbh_origin_recipe_id")
            eksport_recipe = _bygg_recipe_fra_session(ctx, origin_recipe_id=_origin_recipe_id)
            generert_tidspunkt = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            try:
                konvolutt = bygg_kbhrecipe_konvolutt(eksport_recipe, generert_tidspunkt)
            except UgyldigOppskriftForEksport as e:
                st.error(f"❌ Kunne ikke eksportere «{eksport_recipe['name']}»: {e}")
            else:
                fil_navn = eksport_recipe["name"].replace(" ", "_").replace("/", "-") + ".kbhrecipe"
                st.download_button(
                    label="📥 Last ned .kbhrecipe",
                    data=json.dumps(konvolutt, ensure_ascii=False, indent=2),
                    file_name=fil_navn,
                    mime="application/json",
                    width="stretch",
                    key="last_ned_kbhrecipe_btn",
                )
