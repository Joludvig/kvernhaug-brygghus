import streamlit as st
from config import DEMO_MODE
from modules import pantry
from modules.humle_lager import les_lager as _les_gammelt_humlelager

_STATUS_VISNING = {
    "nok": "✅ Nok",
    "knapp": "🟡 Knapt",
    "mangler": "🔴 Mangler",
    "ukjent_match": "⚪ Kan ikke matches sikkert",
}

_TYPE_VISNING = {"malt": "Malt", "humle": "Humle", "gjaer": "Gjær"}
_STANDARD_ENHET = {"malt": "kg", "humle": "g", "gjaer": "pakke"}
_GYLDIGE_ENHETER = {"malt": ["kg", "g"], "humle": ["g"], "gjaer": ["pakke"]}


def _db_for_type(ingredient_type, malt_db, humle_db, gjaer_db):
    return {"malt": malt_db, "humle": humle_db, "gjaer": gjaer_db}[ingredient_type]


def _navn(ingredient_type, ingredient_id, malt_db, humle_db, gjaer_db):
    db = _db_for_type(ingredient_type, malt_db, humle_db, gjaer_db)
    return db.get(ingredient_id, {}).get("display_name", ingredient_id)


def _last_pantry_trygt():
    """Laster pantry og viser en tydelig feilmelding (uten å krasje resten
    av appen) hvis filen er korrupt — se modules.pantry.PantryCorruptError."""
    try:
        return pantry.last_pantry(), None
    except pantry.PantryCorruptError as e:
        return None, str(e)


def render_pantry_panel(ctx, malt_database, humle_database, gjaer_database):
    if DEMO_MODE:
        return

    st.subheader("📦 Lager")
    st.caption(
        "Svarer på ett spørsmål: har jeg nok malt, humle og gjær til å brygge denne oppskriften, "
        "og hva mangler? Priser, butikksammenligning og automatisk bestilling er ikke del av dette."
    )

    data, feil = _last_pantry_trygt()
    if feil:
        st.error(
            "📦 Lagerfilen (data/pantry.json) kunne ikke leses fordi innholdet er ugyldig JSON. "
            "Filen er IKKE overskrevet — rett den manuelt eller gjenopprett fra en backup-fil "
            f"(data/pantry.json.backup_*) før lageret kan vises.\n\nDetaljer: {feil}"
        )
        return

    varsler = pantry.valider_pantry(data)

    _render_oversikt(data, varsler, malt_database, humle_database, gjaer_database)
    st.write("---")
    _render_lagerliste(data, malt_database, humle_database, gjaer_database)
    st.write("---")
    _render_legg_til(data, malt_database, humle_database, gjaer_database)
    st.write("---")
    _render_oppskriftskontroll(ctx, data, malt_database, humle_database, gjaer_database)
    st.write("---")
    _render_humlelager_migrering(data, humle_database)


# ── 1. Oversikt ───────────────────────────────────────────────────────────
def _render_oversikt(data, varsler, malt_db, humle_db, gjaer_db):
    items = data.get("items", [])
    typer = {"malt": set(), "humle": set(), "gjaer": set()}
    for item in items:
        t = item.get("ingredient_type")
        if t in typer and item.get("ingredient_id"):
            typer[t].add(item["ingredient_id"])

    utloper_snart = sum(1 for v in varsler if v["type"] == "utloper_snart")
    utgatt = sum(1 for v in varsler if v["type"] == "utgatt")
    uten_id = sum(1 for v in varsler if v["type"] == "manglende_ingredient_id")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Malttyper", len(typer["malt"]))
    c2.metric("Humletyper", len(typer["humle"]))
    c3.metric("Gjærtyper", len(typer["gjaer"]))
    c4.metric("Utløper snart / utgått", f"{utloper_snart} / {utgatt}")
    c5.metric("Uten stabil ID", uten_id)

    ovrige_varsler = [v for v in varsler if v["type"] not in ("utloper_snart", "utgatt", "manglende_ingredient_id")]
    if ovrige_varsler:
        with st.expander(f"⚠️ {len(ovrige_varsler)} andre varsel om lagerdata"):
            for v in ovrige_varsler:
                st.caption(f"• {v['melding']}")


# ── 2. Lagerliste ─────────────────────────────────────────────────────────
def _utlopsstatus(item):
    dager = pantry.dager_til_utlop(item.get("best_before"))
    if dager is None:
        return None
    if dager < 0:
        return "utgatt"
    if dager <= pantry.UTLOPER_SNART_DAGER:
        return "utloper_snart"
    return None


def _render_lagerliste(data, malt_db, humle_db, gjaer_db):
    st.markdown("**Lagerliste**")
    items = data.get("items", [])

    filter_valg = st.radio(
        "Filter", ["Alle", "Malt", "Humle", "Gjær", "Lav beholdning", "Utløper snart"],
        horizontal=True, key="pantry_filter", label_visibility="collapsed",
    )

    def _passerer_filter(item):
        if filter_valg == "Malt":
            return item["ingredient_type"] == "malt"
        if filter_valg == "Humle":
            return item["ingredient_type"] == "humle"
        if filter_valg == "Gjær":
            return item["ingredient_type"] == "gjaer"
        if filter_valg == "Utløper snart":
            return _utlopsstatus(item) in ("utloper_snart", "utgatt")
        if filter_valg == "Lav beholdning":
            return item.get("quantity", 0) <= 0
        return True

    synlige = [i for i in items if _passerer_filter(i)]

    if not synlige:
        st.caption("Ingen lagerposter i denne visningen ennå.")
    else:
        for item in synlige:
            navn = _navn(item["ingredient_type"], item.get("ingredient_id"), malt_db, humle_db, gjaer_db) \
                or item.get("name_snapshot", "?")
            utlop = _utlopsstatus(item)
            utlop_tekst = {"utgatt": " · 🔴 Utgått", "utloper_snart": " · 🟡 Utløper snart"}.get(utlop, "")

            col_navn, col_type, col_mengde, col_apnet, col_bf, col_sted, col_rediger, col_slett = st.columns(
                [2.4, 1.0, 1.2, 0.9, 1.3, 1.3, 0.9, 0.9]
            )
            col_navn.write(navn)
            col_type.write(_TYPE_VISNING[item["ingredient_type"]])
            col_mengde.write(f"{item['quantity']:g} {item['unit']}")
            col_apnet.write("Åpnet" if item.get("opened") else "Uåpnet")
            col_bf.write((item.get("best_before") or "–") + utlop_tekst)
            col_sted.write(item.get("storage_location") or "–")

            if col_rediger.button("✏️", key=f"pantry_rediger_{item['pantry_item_id']}", help="Rediger post"):
                st.session_state["_pantry_rediger_id"] = item["pantry_item_id"]
            if col_slett.button("🗑️", key=f"pantry_slett_{item['pantry_item_id']}", help="Slett post"):
                st.session_state["_pantry_slett_kandidat"] = item["pantry_item_id"]

    _render_slett_bekreftelse(data, malt_db, humle_db, gjaer_db)
    _render_rediger_post(data)


def _render_slett_bekreftelse(data, malt_db, humle_db, gjaer_db):
    kandidat_id = st.session_state.get("_pantry_slett_kandidat")
    if not kandidat_id:
        return
    item = next((i for i in data.get("items", []) if i["pantry_item_id"] == kandidat_id), None)
    if item is None:
        st.session_state.pop("_pantry_slett_kandidat", None)
        return

    navn = _navn(item["ingredient_type"], item.get("ingredient_id"), malt_db, humle_db, gjaer_db)
    st.warning(f"Slette **{navn}** ({item['quantity']:g} {item['unit']}) fra lageret? Dette kan ikke angres.")
    col_ja, col_avbryt = st.columns(2)
    if col_ja.button("Ja, slett", key="pantry_slett_bekreft", type="primary"):
        nytt = pantry.slett_pantry_item(data, kandidat_id)
        pantry.lagre_pantry(nytt)
        st.session_state.pop("_pantry_slett_kandidat", None)
        st.rerun()
    if col_avbryt.button("Avbryt", key="pantry_slett_avbryt"):
        st.session_state.pop("_pantry_slett_kandidat", None)
        st.rerun()


def _render_rediger_post(data):
    rediger_id = st.session_state.get("_pantry_rediger_id")
    if not rediger_id:
        return
    item = next((i for i in data.get("items", []) if i["pantry_item_id"] == rediger_id), None)
    if item is None:
        st.session_state.pop("_pantry_rediger_id", None)
        return

    with st.expander(f"Rediger: {item.get('name_snapshot')}", expanded=True):
        ny_mengde = st.number_input(
            "Ny mengde", min_value=0.0, value=float(item["quantity"]), step=0.1,
            key=f"pantry_rediger_mengde_{rediger_id}",
        )
        col_pluss, col_minus, col_sett = st.columns(3)
        justering = st.number_input(
            "Juster med", min_value=0.0, value=0.0, step=0.1, key=f"pantry_juster_delta_{rediger_id}",
        )
        if col_pluss.button("+ Legg til", key=f"pantry_pluss_{rediger_id}"):
            pantry.oppdater_pantry_item(data, rediger_id, quantity=float(item["quantity"]) + justering)
            pantry.lagre_pantry(data)
            st.rerun()
        if col_minus.button("− Trekk fra", key=f"pantry_minus_{rediger_id}"):
            ny = max(0.0, float(item["quantity"]) - justering)
            pantry.oppdater_pantry_item(data, rediger_id, quantity=ny)
            pantry.lagre_pantry(data)
            st.rerun()
        if col_sett.button("Sett ny mengde", key=f"pantry_sett_{rediger_id}"):
            pantry.oppdater_pantry_item(data, rediger_id, quantity=ny_mengde)
            pantry.lagre_pantry(data)
            st.rerun()

        apnet = st.checkbox("Åpnet", value=bool(item.get("opened")), key=f"pantry_apnet_{rediger_id}")
        sett_bf = st.checkbox(
            "Sett best-før-dato", value=bool(item.get("best_before")), key=f"pantry_har_bf_{rediger_id}",
        )
        ny_bf = None
        if sett_bf:
            import datetime as _dt
            forrige = item.get("best_before")
            default_dato = _dt.date.fromisoformat(forrige) if forrige else _dt.date.today()
            valgt = st.date_input("Best før", value=default_dato, key=f"pantry_bf_dato_{rediger_id}")
            ny_bf = valgt.isoformat()
        lagersted = st.text_input(
            "Lagersted", value=item.get("storage_location", ""), key=f"pantry_sted_{rediger_id}",
        )
        notater = st.text_area("Notater", value=item.get("notes", ""), key=f"pantry_notater_{rediger_id}")

        if st.button("Lagre endringer", key=f"pantry_lagre_endringer_{rediger_id}"):
            pantry.oppdater_pantry_item(
                data, rediger_id, opened=apnet, best_before=ny_bf,
                storage_location=lagersted, notes=notater,
            )
            pantry.lagre_pantry(data)
            st.session_state.pop("_pantry_rediger_id", None)
            st.rerun()
        if st.button("Lukk", key=f"pantry_lukk_rediger_{rediger_id}"):
            st.session_state.pop("_pantry_rediger_id", None)
            st.rerun()


# ── 3. Legg til vare ──────────────────────────────────────────────────────
def _render_legg_til(data, malt_db, humle_db, gjaer_db):
    st.markdown("**Legg til vare**")

    ingredient_type_visning = st.selectbox(
        "Type", ["Malt", "Humle", "Gjær"], key="pantry_ny_type",
    )
    ingredient_type = {"Malt": "malt", "Humle": "humle", "Gjær": "gjaer"}[ingredient_type_visning]
    db = _db_for_type(ingredient_type, malt_db, humle_db, gjaer_db)

    if not db:
        st.caption(f"Ingen {ingredient_type_visning.lower()} funnet i masterdatabasen.")
        return

    ingredient_id = st.selectbox(
        "Ingrediens", options=sorted(db.keys()),
        format_func=lambda k: db.get(k, {}).get("display_name", k),
        key="pantry_ny_ingrediens",
    )
    navn = db.get(ingredient_id, {}).get("display_name", ingredient_id)

    col_mengde, col_enhet = st.columns(2)
    mengde = col_mengde.number_input("Mengde", min_value=0.0, value=1.0, step=0.1, key="pantry_ny_mengde")
    enhet = col_enhet.selectbox(
        "Enhet", _GYLDIGE_ENHETER[ingredient_type],
        index=_GYLDIGE_ENHETER[ingredient_type].index(_STANDARD_ENHET[ingredient_type]),
        key="pantry_ny_enhet",
    )

    with st.expander("Metadata (valgfritt)"):
        lot_number = st.text_input("Lot-nummer", key="pantry_ny_lot")
        storage_location = st.text_input("Lagersted", key="pantry_ny_sted")
        notes = st.text_area("Notater", key="pantry_ny_notater")
        sett_bf = st.checkbox("Sett best-før-dato", key="pantry_ny_har_bf")
        best_before = None
        if sett_bf:
            import datetime as _dt
            best_before = st.date_input("Best før", value=_dt.date.today(), key="pantry_ny_bf").isoformat()
        opened = st.checkbox("Allerede åpnet", key="pantry_ny_apnet")

    if st.button("Legg til i lager", key="pantry_legg_til_btn", use_container_width=True):
        nytt_item = pantry.opprett_pantry_item(
            ingredient_type=ingredient_type, ingredient_id=ingredient_id, name_snapshot=navn,
            quantity=mengde, unit=enhet, opened=opened, best_before=best_before,
            lot_number=lot_number, storage_location=storage_location, notes=notes,
        )
        data["items"].append(nytt_item)
        pantry.lagre_pantry(data)
        st.rerun()


# ── 4. Oppskriftskontroll ─────────────────────────────────────────────────
def _render_oppskriftskontroll(ctx, data, malt_db, humle_db, gjaer_db):
    recipe = (ctx or {}).get("recipe")
    if not recipe:
        return

    st.markdown(f"**Lagerstatus for: {recipe.get('name', 'gjeldende oppskrift')}**")
    rader = pantry.beregn_mangler(recipe, data, malt_db, humle_db, gjaer_db)

    if not rader:
        st.caption("Ingen ingredienser å sjekke ennå.")
        return

    for rad in rader:
        trenger = "–" if rad["required_base"] is None else f"{rad['required_base']:g} {rad['base_unit']}"
        pa_lager = "–" if rad["available_base"] is None else f"{rad['available_base']:g} {rad['base_unit']}"
        mangler = "–" if rad["missing_base"] is None else f"{rad['missing_base']:g} {rad['base_unit']}"
        col_navn, col_trenger, col_pa_lager, col_mangler, col_status = st.columns([2.2, 1.3, 1.3, 1.3, 1.6])
        col_navn.write(rad["name"])
        col_trenger.write(trenger)
        col_pa_lager.write(pa_lager)
        col_mangler.write(mangler)
        col_status.write(_STATUS_VISNING[rad["status"]])

    antall_mangler = sum(1 for r in rader if r["status"] == "mangler")
    antall_ukjent = sum(1 for r in rader if r["status"] == "ukjent_match")

    st.write("")
    if antall_mangler == 0 and antall_ukjent == 0:
        st.success("✅ Klar til brygging — alle ingredienser er på lager.")
    else:
        if antall_mangler:
            st.error(f"🔴 Mangler {antall_mangler} ingrediens(er).")
        if antall_ukjent:
            st.warning(f"⚪ {antall_ukjent} ingrediens(er) må kontrolleres manuelt (usikker match eller ukjent behov).")


# ── Migrering fra gammelt humlelager ──────────────────────────────────────
def _render_humlelager_migrering(data, humle_db):
    gammelt_lager = _les_gammelt_humlelager()
    if not gammelt_lager:
        return

    with st.expander("🔄 Migrer fra gammelt humlelager"):
        st.caption(
            "Fant registrert humle i det gamle humlelageret (data/humle_lager.json). "
            "Se over forslaget under før du eventuelt importerer — originalfilen røres ikke."
        )
        forslag = pantry.forhandsvis_humlelager_migrering(gammelt_lager, humle_db)
        if not forslag:
            st.caption("Ingen gyldige poster å migrere.")
            return

        for f in forslag:
            st.write(f"• {f['name_snapshot']}: {f['quantity']:g} g")

        bekreft = st.checkbox(
            "Jeg har sett gjennom listen og vil importere disse til Pantry",
            key="pantry_migrer_bekreft",
        )
        if st.button("Importer til Pantry", key="pantry_migrer_importer_btn", disabled=not bekreft):
            backup_sti = pantry.lag_pantry_backup()
            nytt = pantry.importer_humlelager_migrering(data, forslag)
            pantry.lagre_pantry(nytt)
            if backup_sti:
                st.success(f"Importert. Backup av forrige pantry-tilstand lagret som {backup_sti}.")
            else:
                st.success("Importert.")
            st.rerun()
