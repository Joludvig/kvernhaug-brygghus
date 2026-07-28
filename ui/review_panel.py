# ui/review_panel.py
import streamlit as st
import json
import os
import re

from modules.master_data_io import skriv_master_json_atomisk

# De TRE masterdatabasene appen faktisk laster ved oppstart (se app.py:
# last_json_data("master_malt.json") / ("master_humle_v2.json") /
# ("master_gjaer_v2.json")) -- en review-godkjenning her skriver derfor
# DIREKTE til samme fil appens runtime leser, ingen separat synk-steg.
MASTER_PATHS = {
    "humle": "data/master_humle_v2.json",
    "malt":  "data/master_malt.json",
    "gjaer": "data/master_gjaer_v2.json",
}

UNMATCHED_PATHS = {
    "humle": "raw_data/unmatched_hops.json",
    "malt":  "raw_data/unmatched_malt.json",
    "gjaer": "raw_data/unmatched_gjaer.json",
}


class TomMasterId(Exception):
    """Reist når det innskrevne navnet gir en tom auto-generert ID (f.eks.
    et navn som bare består av tegn _lag_kanonisk_id() strimler bort).
    En tom streng kan ALDRI brukes som nøkkel i masterdatabasen."""
    pass


class MasterIdKollisjon(Exception):
    """Reist når «Opprett i master» ville overskrevet en ALLEREDE
    eksisterende ingrediens stille -- samme genererte ID matcher en
    entry som finnes fra før. Siden review nå skriver DIREKTE til de
    aktive masterdatabasene appen laster ved oppstart (se MASTER_PATHS
    over), ville dette ellers vært en stille datatap-hendelse. Bærer den
    kolliderende ID-en og navnet på den eksisterende ingrediensen, slik
    at kallestedet kan vise akkurat hvilken oppføring som er i veien."""

    def __init__(self, ny_id, eksisterende_navn):
        self.ny_id = ny_id
        self.eksisterende_navn = eksisterende_navn
        super().__init__(
            f"ID \"{ny_id}\" finnes allerede i master som «{eksisterende_navn}»."
        )


class MasterLesefeil(Exception):
    """Reist når en EKSISTERENDE masterfil finnes på disk men ikke kan
    leses og valideres som et gyldig dict -- tom fil (0 byte), korrupt
    JSON, eller JSON som parser til noe annet enn et objekt (f.eks. en
    liste eller en streng), eller en annen lesefeil (rettigheter e.l.).

    Skiller seg bevisst fra "filen finnes ikke" -- det er helt normalt
    (masteren er bare ikke opprettet ennå) og gir {} uten feil, se
    _les_master(). En EKSISTERENDE, men uleselig fil skal derimot ALDRI
    stille behandles som en tom master og deretter overskrives med kun
    den ene nye/endrede ingrediensen -- det ville slettet resten av
    databasen stille. Kallestedene (_render_kategori, _render_match_tab,
    og de tre _render_ny_*-formene) fanger denne og viser en tydelig
    feil i UI-et i stedet, uten å skrive noe eller fjerne pending-
    elementet."""
    pass


def _les_json(sti, default):
    """Enkel, svelgende lesing -- brukt for de ARBEIDSFILENE
    (raw_data/unmatched_*.json) som ikke er masterdata og der en
    lesefeil trygt kan behandles som "ingen pending review ennå". Selve
    masterfilene MÅ leses via _les_master() i stedet, som skiller
    lesefeil fra en reell, tom master (se MasterLesefeil)."""
    if os.path.exists(sti) and os.path.getsize(sti) > 0:
        try:
            with open(sti, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _les_master(sti):
    """Leser en masterfil og skiller tydelig mellom:
      - filen finnes ikke ennå -> {} (helt normalt, ingen feil)
      - filen finnes men er 0 byte -> MasterLesefeil (ikke gyldig JSON)
      - filen finnes men er ugyldig JSON -> MasterLesefeil
      - filen finnes og er gyldig JSON, men ikke et objekt (f.eks. en
        liste eller en streng) -> MasterLesefeil
      - annen lesefeil (rettigheter e.l., eller ugyldige UTF-8-bytes)
        -> MasterLesefeil
      - filen finnes og er et gyldig (ev. tomt) JSON-objekt -> selve
        dict-en, uendret (inkludert en tom {})

    `UnicodeDecodeError`/`UnicodeError` (en masterfil med ugyldige
    UTF-8-bytes) er IKKE en OSError og må fanges eksplisitt her --
    ellers ville den sluppet forbi denne funksjonens kontrollerte
    feilhåndtering og krasjet appen i stedet for å vises som en vanlig,
    forståelig feil i UI-et (datasikkerheten var uansett bevart siden
    filen aldri blir skrevet ved en lesefeil, men appen skal ikke
    krasje)."""
    if not os.path.exists(sti):
        return {}
    try:
        with open(sti, "r", encoding="utf-8") as f:
            raw = f.read()
    except (OSError, UnicodeError) as e:
        raise MasterLesefeil(f"Kunne ikke lese masterfilen {sti}: {e}") from e
    if not raw.strip():
        raise MasterLesefeil(f"Masterfilen {sti} finnes, men er tom (0 byte) -- ikke gyldig JSON.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise MasterLesefeil(f"Masterfilen {sti} inneholder ugyldig JSON og ble IKKE endret ({e}).") from e
    if not isinstance(data, dict):
        raise MasterLesefeil(
            f"Masterfilen {sti} inneholder gyldig JSON, men av feil type "
            f"({type(data).__name__} i stedet for et objekt/dict). Filen ble IKKE endret."
        )
    return data


def _skriv_json(sti, data):
    """Enkel skriving for de ARBEIDSFILENE (raw_data/unmatched_*.json) som
    ikke regnes som masterdata -- selve masterfilene skrives via
    skriv_master_json_atomisk() i stedet (se _legg_til_alias_og_fjern og
    _opprett_og_fjern under), som er atomisk og tar backup."""
    with open(sti, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _lag_kanonisk_id(navn):
    s = navn.lower()
    s = s.replace("æ", "ae").replace("ø", "o").replace("å", "aa")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _fjern_fra_unmatched(kat, index):
    sti = UNMATCHED_PATHS[kat]
    items = _les_json(sti, [])
    if 0 <= index < len(items):
        items.pop(index)
        _skriv_json(sti, items)


def _legg_til_alias_og_fjern(kat, master_id, item, index):
    """Reiser MasterLesefeil (uten å skrive noe eller fjerne pending-
    elementet) hvis den eksisterende masterfilen ikke kan leses og
    valideres -- se _les_master()."""
    master_sti = MASTER_PATHS[kat]
    master = _les_master(master_sti)
    if master_id not in master:
        return
    navn = item.get("navn", "")
    aliaser = master[master_id].setdefault("aliases", [])
    if navn and navn not in aliaser:
        aliaser.append(navn)
    butikk = item.get("butikk", "")
    pris = item.get("pris", 0)
    url = item.get("url", "")
    if butikk:
        bm = master[master_id].setdefault("butikk_match", {})
        if butikk not in bm:
            bm[butikk] = {"pris": None, "url": None}
        if pris:
            bm[butikk]["pris"] = pris
        if url:
            bm[butikk]["url"] = url
    skriv_master_json_atomisk(master_sti, master)
    _fjern_fra_unmatched(kat, index)


def _opprett_og_fjern(kat, ny_id, ny_entry, index):
    """Oppretter en helt NY ingrediens i master. Reiser TomMasterId hvis
    `ny_id` er tom, eller MasterIdKollisjon hvis `ny_id` allerede finnes
    -- i BEGGE tilfeller uten å skrive noe til master OG uten å fjerne
    pending-elementet, slik at review-elementet fortsatt står klart til
    et nytt forsøk (f.eks. via «🔗 Match eksisterende» i stedet, eller
    med et justert navn)."""
    if not ny_id:
        raise TomMasterId("Navnet gir en tom auto-generert ID.")
    master_sti = MASTER_PATHS[kat]
    master = _les_master(master_sti)
    if ny_id in master:
        eksisterende_navn = master[ny_id].get("display_name", ny_id)
        raise MasterIdKollisjon(ny_id, eksisterende_navn)
    master[ny_id] = ny_entry
    skriv_master_json_atomisk(master_sti, master)
    _fjern_fra_unmatched(kat, index)


def _render_match_tab(kat, item, index, master):
    if not master:
        st.info("Master-fil ikke funnet.")
        return
    options = {v.get("display_name", k): k for k, v in master.items()}
    valgt = st.selectbox(
        "Match mot eksisterende entry:",
        sorted(options.keys()),
        key=f"sel_{kat}_{index}",
    )
    st.caption("Produktnavnet legges til som alias, og pris/URL oppdateres i master.")
    if st.button("Legg til alias + oppdater pris", key=f"match_btn_{kat}_{index}", type="primary"):
        try:
            _legg_til_alias_og_fjern(kat, options[valgt], item, index)
        except MasterLesefeil as e:
            st.error(f"❌ Kunne ikke oppdatere master: {e}")
        else:
            st.toast(f"Matchet til «{valgt}»", icon="✅")
            st.rerun()


def _render_avvis_tab(kat, item, index):
    navn = item.get("navn", "Ukjent")
    st.caption(f"«{navn}» fjernes fra pending. Ingenting skrives til master.")
    if st.button("Bekreft avvis", key=f"avvis_{kat}_{index}"):
        _fjern_fra_unmatched(kat, index)
        st.toast(f"«{navn}» avvist", icon="🗑️")
        st.rerun()


def _render_ny_humle(item, index):
    navn = item.get("navn", "")
    butikk = item.get("butikk", "")
    pris = item.get("pris", 0)
    url = item.get("url", "")
    with st.form(key=f"ny_humle_{index}"):
        display_name = st.text_input("Navn", value=navn)
        aliases_tekst = st.text_area("Aliases (én per linje)", value=navn, height=80)
        alfa = st.number_input("Alfa-syre (%)", 0.0, 25.0, 5.0, 0.1)
        kategori = st.selectbox("Kategori", ["Aroma", "Bitterhet", "Dual"])
        smakstags_tekst = st.text_area("Smakstags (én per linje)", height=80)
        origin = st.text_input("Opprinnelse (land)", value="")
        st.caption(f"Auto-ID basert på navn: `{_lag_kanonisk_id(navn)}`")
        if st.form_submit_button("Opprett i master", type="primary"):
            ny_id = _lag_kanonisk_id(display_name)
            aliases = [a.strip() for a in aliases_tekst.splitlines() if a.strip()]
            smakstags = [s.strip() for s in smakstags_tekst.splitlines() if s.strip()]
            entry = {
                "display_name": display_name,
                "kategori": kategori,
                "alfa_typisk": alfa,
                "aliases": aliases,
                "smakstags": smakstags,
                "origin": origin,
                "butikk_match": {butikk: {"pris": pris, "url": url}} if butikk else {},
                "verified": True,
            }
            try:
                _opprett_og_fjern("humle", ny_id, entry, index)
            except TomMasterId:
                st.error("❌ Navnet gir en tom auto-ID — skriv inn et navn med minst én bokstav eller ett tall.")
            except MasterIdKollisjon as e:
                st.error(
                    f"❌ ID-en `{e.ny_id}` finnes allerede i master som «{e.eksisterende_navn}». "
                    "Bruk «🔗 Match eksisterende» i stedet, eller endre navnet slik at det gir en annen ID."
                )
            except MasterLesefeil as e:
                st.error(f"❌ Kunne ikke opprette i master: {e}")
            else:
                st.toast(f"«{display_name}» opprettet i master!", icon="✅")
                st.rerun()


def _render_ny_malt(item, index):
    navn = item.get("navn", "")
    butikk = item.get("butikk", "")
    pris = item.get("pris", 0)
    url = item.get("url", "")
    ebc_raw = float(item.get("ebc") or 4.0)
    with st.form(key=f"ny_malt_{index}"):
        display_name = st.text_input("Navn", value=navn)
        aliases_tekst = st.text_area("Aliases (én per linje)", value=navn, height=80)
        produsent = st.text_input("Produsent", value=item.get("produsent", ""))
        kategori = st.selectbox("Kategori", ["Basemalt", "Karamell", "Spesialmalt", "Spraymalt", "Røkt"])
        ebc = st.number_input("EBC", 0.0, 2000.0, ebc_raw, 1.0)
        smakstags_tekst = st.text_area("Smakstags (én per linje)", height=80)
        st.caption(f"Auto-ID basert på navn: `{_lag_kanonisk_id(navn)}`")
        if st.form_submit_button("Opprett i master", type="primary"):
            ny_id = _lag_kanonisk_id(display_name)
            aliases = [a.strip() for a in aliases_tekst.splitlines() if a.strip()]
            smakstags = [s.strip() for s in smakstags_tekst.splitlines() if s.strip()]
            entry = {
                "display_name": display_name,
                "produsent": produsent,
                "kategori": kategori,
                "ebc": ebc,
                "aliases": aliases,
                "smakstags": smakstags,
                "butikk_match": {butikk: {"pris": pris, "url": url}} if butikk else {},
                "verified": True,
            }
            try:
                _opprett_og_fjern("malt", ny_id, entry, index)
            except TomMasterId:
                st.error("❌ Navnet gir en tom auto-ID — skriv inn et navn med minst én bokstav eller ett tall.")
            except MasterIdKollisjon as e:
                st.error(
                    f"❌ ID-en `{e.ny_id}` finnes allerede i master som «{e.eksisterende_navn}». "
                    "Bruk «🔗 Match eksisterende» i stedet, eller endre navnet slik at det gir en annen ID."
                )
            except MasterLesefeil as e:
                st.error(f"❌ Kunne ikke opprette i master: {e}")
            else:
                st.toast(f"«{display_name}» opprettet i master!", icon="✅")
                st.rerun()


def _render_ny_gjaer(item, index):
    navn = item.get("navn", "")
    butikk = item.get("butikk", "")
    pris = item.get("pris", 0)
    url = item.get("url", "")
    with st.form(key=f"ny_gjaer_{index}"):
        display_name = st.text_input("Navn", value=navn)
        aliases_tekst = st.text_area("Aliases (én per linje)", value=navn, height=80)
        produsent = st.text_input("Produsent", value=item.get("produsent", ""))
        kategori = st.selectbox("Kategori", ["Tørrgjær", "Flytende gjær", "Kveik"])
        gjaertype = st.selectbox("Gjærtype", ["Ale", "Lager", "Wheat", "Belgian", "Kveik", "Annet"])
        attenuation = st.number_input("Attenuation", 0.60, 0.90, 0.75, 0.01, format="%.2f")
        smakstags_tekst = st.text_area("Smakstags (én per linje)", height=80)
        st.caption(f"Auto-ID basert på navn: `{_lag_kanonisk_id(navn)}`")
        if st.form_submit_button("Opprett i master", type="primary"):
            ny_id = _lag_kanonisk_id(display_name)
            aliases = [a.strip() for a in aliases_tekst.splitlines() if a.strip()]
            smakstags = [s.strip() for s in smakstags_tekst.splitlines() if s.strip()]
            entry = {
                "display_name": display_name,
                "produsent": produsent,
                "kategori": kategori,
                "gjaertype": gjaertype,
                "attenuation": attenuation,
                "aliases": aliases,
                "smakstags": smakstags,
                "butikk_match": {butikk: {"pris": pris, "url": url}} if butikk else {},
                "verified": True,
            }
            try:
                _opprett_og_fjern("gjaer", ny_id, entry, index)
            except TomMasterId:
                st.error("❌ Navnet gir en tom auto-ID — skriv inn et navn med minst én bokstav eller ett tall.")
            except MasterIdKollisjon as e:
                st.error(
                    f"❌ ID-en `{e.ny_id}` finnes allerede i master som «{e.eksisterende_navn}». "
                    "Bruk «🔗 Match eksisterende» i stedet, eller endre navnet slik at det gir en annen ID."
                )
            except MasterLesefeil as e:
                st.error(f"❌ Kunne ikke opprette i master: {e}")
            else:
                st.toast(f"«{display_name}» opprettet i master!", icon="✅")
                st.rerun()


_NY_FORM = {
    "humle": _render_ny_humle,
    "malt":  _render_ny_malt,
    "gjaer": _render_ny_gjaer,
}


def _render_kategori(kat, label, emoji):
    unmatched = _les_json(UNMATCHED_PATHS[kat], [])
    try:
        master = _les_master(MASTER_PATHS[kat])
    except MasterLesefeil as e:
        st.error(
            f"❌ Masterfilen for {label} kan ikke leses ({e}). Review er midlertidig "
            "deaktivert for denne kategorien til filen er reparert eller gjenopprettet fra "
            "en backup i data/ -- ingen endringer skjer automatisk."
        )
        return

    if not unmatched:
        st.success(f"✅ Ingen {label} pending review.")
        return

    st.warning(f"⚠️ {len(unmatched)} {label} matchet ikke master")

    for i, item in enumerate(unmatched):
        navn = item.get("navn", "Ukjent")
        butikk = item.get("butikk", "")
        pris = item.get("pris", 0)
        url = item.get("url", "")

        with st.expander(f"{emoji} **{navn}** — {butikk} — {pris} kr"):
            if url:
                st.markdown(f"[Åpne produktside]({url})")

            tab_match, tab_ny, tab_avvis = st.tabs(["🔗 Match eksisterende", "➕ Ny ingrediens", "🚫 Avvis"])

            with tab_match:
                _render_match_tab(kat, item, i, master)
            with tab_ny:
                _NY_FORM[kat](item, i)
            with tab_avvis:
                _render_avvis_tab(kat, item, i)


def render_review_panel():
    st.write("---")
    st.subheader("📋 Pending Review")

    tab_malt, tab_humle, tab_gjaer = st.tabs(["🌾 Malt", "🌿 Humle", "🧫 Gjær"])

    with tab_malt:
        _render_kategori("malt", "malter", "🌾")
    with tab_humle:
        _render_kategori("humle", "humler", "🌿")
    with tab_gjaer:
        _render_kategori("gjaer", "gjærsorter", "🧫")
