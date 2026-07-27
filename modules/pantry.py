# modules/pantry.py
"""
Supply Engine / Pantry V1 — kjernemotor.

Svarer på ETT konkret spørsmål: «Har jeg nok malt, humle og gjær til å
brygge denne oppskriften, og hva mangler?»

Ren Python — importerer ALDRI streamlit. UI-laget (ui/pantry_panel.py) kaller
disse funksjonene og gjør all rendering selv.

Ikke i V1 (bevisst utelatt, se statusrapport): priser, butikksammenligning,
automatisk bestilling, automatisk lagertrekk etter brygging, reservasjoner
mot planlagte batcher, transaksjonshistorikk, strekkoder, avansert
holdbarhetsmodell, Smart Handleliste.
"""
import json
import os
import shutil
import uuid
from datetime import date, datetime

from config import DEMO_MODE
from modules.brewday_calc import beregn_pakker

SCHEMA_VERSION = 1

INGREDIENT_TYPES = {"malt", "humle", "gjaer"}

# Standard sikkerhetsmarginer (konfigurerbare — se beregn_mangler/
# vurder_tilgjengelighet sin `marginer`-parameter). Uttrykt som andel
# (0.05 = 5 %) OVER nødvendig mengde før noe regnes som trygt "nok".
STANDARD_MARGIN = {"malt": 0.05, "humle": 0.10, "gjaer": 0.0}

# "Utløper snart" — antall dager frem i tid. Lagerinformasjon, ikke en
# automatisk kvalitetsdom (se modulens statusrapport-omtale).
UTLOPER_SNART_DAGER = 60

_GYLDIGE_ENHETER = {"malt": {"kg", "g"}, "humle": {"g"}, "gjaer": {"pakke"}}


class PantryCorruptError(Exception):
    """data/pantry.json (eller KVERNHAUG_PANTRY_DIR-ekvivalenten) finnes,
    men inneholder ugyldig/korrupt JSON. Filen overskrives ALDRI automatisk
    når dette skjer — feilen må nå helt opp til brukeren, som selv velger å
    rette filen manuelt eller gjenopprette fra en backup."""


# ── Lagringssti ──────────────────────────────────────────────────────────
def _pantry_mappe():
    """Aktiv pantry-mappe — lest FRISKT ved hvert kall, aldri frosset ved
    modul-import (samme velprøvde mønster som modules/recipe_storage.py sin
    _mappe() og modules/water_chemistry.py sine _vannkilder_fil()/
    _vannmaal_fil(): en modulnivå-konstant evaluert kun ved første import
    kan bli frosset FØR en test rekker å sette miljøvariabelen i sin egen
    setUp(), med fare for at "isolerte" tester stille skriver til ekte
    data/. KVERNHAUG_PANTRY_DIR finnes KUN for testisolasjon."""
    return os.getenv("KVERNHAUG_PANTRY_DIR", "data")


def _pantry_fil():
    return os.path.join(_pantry_mappe(), "pantry.json")


# ── Lagring ──────────────────────────────────────────────────────────────
def _tomt_pantry():
    return {"schema_version": SCHEMA_VERSION, "updated_at": None, "items": []}


def migrer_pantry_schema(pantry):
    """No-op for schema_version 1 — strukturen fremtidige versjoner kan
    henge migreringssteg på, ett `if pantry.get("schema_version") == N:`
    om gangen, uten å måtte røre alt eksisterende kall-steder."""
    if pantry.get("schema_version") != SCHEMA_VERSION:
        pantry = dict(pantry)
        pantry["schema_version"] = SCHEMA_VERSION
    return pantry


def last_pantry():
    """Laster pantry.json. Håndterer en manglende fil TRYGT (f.eks. første
    oppstart, eller en fersk sjekk-ut uten lokal pantry-fil) ved å returnere
    en tom, gyldig struktur — UTEN å skrive noe til disk selv. Filen skrives
    først når brukeren faktisk gjør noe (samme skrivebeskyttet-til-lagring-
    mønster som modules/humle_lager.py sin les_lager()): en ren "les"
    (f.eks. bare det å rendre lagerpanelet) skal aldri ha sideeffekten at
    den oppretter en fil på disk — ellers ville enhver test som rendrer
    hele app.py (uten selv å bry seg om Pantry) utilsiktet skrevet til den
    ekte data/pantry.json. Kaster PantryCorruptError (uten å røre filen)
    hvis innholdet finnes men ikke er gyldig JSON."""
    filsti = _pantry_fil()
    if not os.path.exists(filsti):
        return _tomt_pantry()

    with open(filsti, encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise PantryCorruptError(
            f"{filsti} inneholder ugyldig JSON og ble IKKE overskrevet ({e}). "
            "Rett filen manuelt, eller gjenopprett fra en backup (se lag_pantry_backup()), "
            "før lageret kan lastes igjen."
        ) from e
    return migrer_pantry_schema(data)


# Standard antall backupfiler som beholdes (se lagre_pantry()/
# _rydd_gamle_pantry_backupfiler()). Konfigurerbart per kall — sett til 0
# eller mindre for å beholde alle (typisk kun i tester).
PANTRY_BACKUP_MAKS_ANTALL = 20


def lagre_pantry(pantry, maks_backup_antall=PANTRY_BACKUP_MAKS_ANTALL):
    """Lagrer pantry atomisk: skriver til en midlertidig fil og erstatter
    originalen (os.replace er atomisk på både Windows og POSIX), slik at en
    krasj midtveis i skrivingen aldri kan etterlate en halvskrevet/korrupt
    fil. No-op i DEMO_MODE, samme mønster som modules/recipe_storage.py og
    modules/humle_lager.py.

    Lager AUTOMATISK en tidsstemplet backup av den EKSISTERENDE filen (hvis
    en finnes) rett før den overskrives — dette er det ENE, felles
    lagringspunktet ALLE reelle endringer (oppdatering, sletting av vare,
    hurtigjustering, full overskriving, import/migrering) til slutt går
    gjennom, så automatisk backup her dekker samtlige uten at hvert enkelt
    kall-sted (ui/pantry_panel.py) selv må huske å be om det. Den aller
    første lagringen (ingen eksisterende fil ennå) trenger ingen backup —
    det finnes ingenting å miste. Beholder kun de `maks_backup_antall`
    nyeste backupfilene etterpå (se _rydd_gamle_pantry_backupfiler)."""
    if DEMO_MODE:
        return
    mappe = _pantry_mappe()
    os.makedirs(mappe, exist_ok=True)

    filsti = _pantry_fil()
    if os.path.exists(filsti):
        lag_pantry_backup()
        _rydd_gamle_pantry_backupfiler(maks_backup_antall)

    pantry = dict(pantry)
    pantry["schema_version"] = SCHEMA_VERSION
    pantry["updated_at"] = datetime.now().isoformat(timespec="seconds")

    tmp_sti = filsti + ".tmp"
    with open(tmp_sti, "w", encoding="utf-8") as f:
        json.dump(pantry, f, ensure_ascii=False, indent=2)
    os.replace(tmp_sti, filsti)


def lag_pantry_backup():
    """Kopierer gjeldende pantry.json til en tidsstemplet backup-fil i
    samme mappe (mikrosekund-presisjon i tidsstempelet — sekund-presisjon
    var ikke nok til å garantere unike filnavn nå som lagre_pantry() kaller
    denne automatisk ved HVER reell endring, ikke bare ved migrering — en
    kort tilfeldig hex-suffiks er lagt til i tillegg, siden datetime.now()
    sin mikrosekund-oppløsning i praksis ikke er garantert unik mellom to
    kjapt påfølgende lagringer på enkelte systemer/klokker).
    Returnerer backup-stien, eller None hvis det ikke finnes noen
    pantry.json å sikkerhetskopiere ennå."""
    kilde = _pantry_fil()
    if not os.path.exists(kilde):
        return None
    tidsstempel = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + "_" + uuid.uuid4().hex[:6]
    mal = f"{kilde}.backup_{tidsstempel}"
    shutil.copy2(kilde, mal)
    return mal


def _list_pantry_backup_stier():
    """Sorterte (ELDST -> nyest) stier til alle pantry.json.backup_*-filer
    i den aktive pantry-mappen. Filnavnets tidsstempel sorterer korrekt
    kronologisk som ren tekstsortering (fast bredde, mest signifikant
    først). Skriver og endrer ingenting."""
    mappe = _pantry_mappe()
    if not os.path.isdir(mappe):
        return []
    prefiks = os.path.basename(_pantry_fil()) + ".backup_"
    treff = sorted(f for f in os.listdir(mappe) if f.startswith(prefiks))
    return [os.path.join(mappe, f) for f in treff]


def _rydd_gamle_pantry_backupfiler(maks_antall=PANTRY_BACKUP_MAKS_ANTALL):
    """Sletter de ELDSTE backupfilene slik at kun de `maks_antall` NYESTE
    blir igjen. `maks_antall <= 0` (eller None) betyr «behold alt» (ingen
    opprydding) — brukt av enkelte tester som eksplisitt vil telle opp alle
    backupfilene som noensinne er laget i en isolert testmappe."""
    if not maks_antall or maks_antall <= 0:
        return
    stier = _list_pantry_backup_stier()
    for gammel_sti in stier[:-maks_antall]:
        try:
            os.remove(gammel_sti)
        except OSError:
            pass  # en mislykket opprydding er ikke kritisk -- filen lagres uansett


def list_pantry_backups():
    """Liste over tilgjengelige pantry-backupfiler, NYEST FØRST — til bruk
    i en forhåndsvisning før en eksplisitt gjenoppretting (se
    gjenopprett_pantry_fra_backup()). Hvert element er
    {"sti", "filnavn", "tidsstempel"}. Skriver og endrer ingenting."""
    resultat = []
    for sti in reversed(_list_pantry_backup_stier()):
        filnavn = os.path.basename(sti)
        tidsstempel = filnavn.split(".backup_", 1)[-1]
        resultat.append({"sti": sti, "filnavn": filnavn, "tidsstempel": tidsstempel})
    return resultat


def les_pantry_backup_innhold(backup_sti):
    """Laster og validerer JSON-innholdet i én spesifikk backupfil, til
    bruk i en FORHÅNDSVISNING før brukeren eksplisitt bekrefter en
    gjenoppretting (se ui/pantry_panel.py). Skriver ingenting selv. Kaster
    PantryCorruptError (samme unntakstype som last_pantry() for en korrupt
    hovedfil) hvis backupfilen mot formodning ikke er gyldig JSON."""
    with open(backup_sti, encoding="utf-8") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise PantryCorruptError(f"Backupfilen {backup_sti} inneholder ugyldig JSON ({e}).") from e


def gjenopprett_pantry_fra_backup(backup_sti):
    """Returnerer pantry-strukturen fra en gitt backupfil, KLAR til å
    lagres — lagrer ALDRI selv. UI-et er ansvarlig for å ha vist en
    forhåndsvisning (les_pantry_backup_innhold/list_pantry_backups) og
    innhentet en EKSPLISITT bekreftelse før resultatet sendes videre til
    lagre_pantry() — ingen gjenoppretting skjer noensinne automatisk.
    Selve gjenopprettingen er i praksis en helt vanlig lagring, så
    lagre_pantry() sin egen automatiske backup-mekanisme tar samtidig vare
    på tilstanden slik den var RETT FØR gjenopprettingen, uten noe eget
    unntak her."""
    data = les_pantry_backup_innhold(backup_sti)
    return migrer_pantry_schema(data)


# ── Normalisering ────────────────────────────────────────────────────────
def normaliser_mengde(ingredient_type, quantity, unit):
    """Normaliserer en brukeroppgitt mengde til lagerets interne basisenhet:
    malt og humle -> gram, gjær -> pakker (V1). Returnerer
    (base_quantity, base_unit). Kaster ValueError på ukjent type/enhet i
    stedet for å gjette — en feil enhet skal aldri stille regnes som gram."""
    if ingredient_type not in INGREDIENT_TYPES:
        raise ValueError(f"Ukjent ingredienstype: {ingredient_type!r} (forventet malt/humle/gjaer)")
    quantity = float(quantity)

    if ingredient_type == "malt":
        if unit == "kg":
            return quantity * 1000.0, "g"
        if unit == "g":
            return quantity, "g"
        raise ValueError(f"Ukjent enhet for malt: {unit!r} (forventet 'kg' eller 'g')")

    if ingredient_type == "humle":
        if unit == "g":
            return quantity, "g"
        raise ValueError(f"Ukjent enhet for humle: {unit!r} (forventet 'g')")

    # gjaer
    if unit == "pakke":
        return quantity, "pakke"
    raise ValueError(f"Ukjent enhet for gjær: {unit!r} (forventet 'pakke')")


# ── CRUD på lagerposter ──────────────────────────────────────────────────
def opprett_pantry_item(ingredient_type, ingredient_id, name_snapshot, quantity, unit,
                         opened=False, best_before=None, lot_number="",
                         storage_location="", notes="", is_custom=False):
    """Bygger en ny, komplett lagerpost (med fersk pantry_item_id). Skriver
    IKKE til disk selv — kalleren legger den til i en pantry["items"]-liste
    og kaller lagre_pantry()."""
    base_quantity, base_unit = normaliser_mengde(ingredient_type, quantity, unit)
    return {
        "pantry_item_id": str(uuid.uuid4()),
        "ingredient_type": ingredient_type,
        "ingredient_id": ingredient_id,
        "name_snapshot": name_snapshot,
        "quantity": float(quantity),
        "unit": unit,
        "base_quantity": base_quantity,
        "base_unit": base_unit,
        "opened": bool(opened),
        "best_before": best_before,
        "lot_number": lot_number,
        "storage_location": storage_location,
        "notes": notes,
        "is_custom": bool(is_custom),
    }


def _generer_custom_ingredient_id():
    """Stabil ID for en egendefinert (ikke-master-DB) ingrediens. Genereres
    ÉN gang ved opprettelse og endres ALDRI senere, heller ikke når
    brukeren redigerer visningsnavnet — «stabil» betyr her at ID-en
    identifiserer ingrediensen for godt, uavhengig av senere redigering."""
    return f"custom_{uuid.uuid4().hex[:12]}"


def opprett_egendefinert_pantry_item(ingredient_type, navn, quantity, unit,
                                      opened=False, best_before=None, lot_number="",
                                      storage_location="", notes=""):
    """Oppretter en lagerpost for en EGENDEFINERT ingrediens — noe brukeren
    har hjemme som ikke finnes i master-databasen (f.eks. hjemmelaget
    honning, en gjenbrukt gjærkake, en spesialgjær kjøpt til noe annet enn
    øl). `ingredient_type` er fortsatt malt/humle/gjaer (styrer basisenhet
    og sikkerhetsmargin), men får en fersk custom_-ingredient_id i stedet
    for en ID fra masterdatabasen. Krever et ikke-tomt navn — kaster
    ValueError ellers.

    Dette er nettopp DERFOR egendefinerte varer aldri matches automatisk
    mot en oppskrift: beregn_mangler() slår opp oppskriftens ingrediens-
    ID-er (som alltid kommer fra malt_db/humle_db/gjaer_db) mot lagerets
    ingredient_id-er — en custom_-ID vil aldri finnes i en oppskrift med
    mindre brukeren en gang i fremtiden får en egen, eksplisitt
    koblingsfunksjon (ikke bygget i V1)."""
    navn = (navn or "").strip()
    if not navn:
        raise ValueError("Egendefinert ingrediens krever et navn.")

    item = opprett_pantry_item(
        ingredient_type=ingredient_type,
        ingredient_id=_generer_custom_ingredient_id(),
        name_snapshot=navn,
        quantity=quantity, unit=unit, opened=opened, best_before=best_before,
        lot_number=lot_number, storage_location=storage_location, notes=notes,
        is_custom=True,
    )
    return item


def oppdater_pantry_item(pantry, pantry_item_id, **endringer):
    """Oppdaterer feltene i `endringer` på posten med gitt pantry_item_id.
    Reberegner base_quantity/base_unit automatisk hvis quantity og/eller
    unit endres. Muterer og returnerer samme `pantry`-dict. Kaster
    KeyError hvis posten ikke finnes — kalleren bør validere at ID-en
    faktisk eksisterer (f.eks. via en selectbox bygget fra pantry["items"])
    før dette kalles."""
    for item in pantry.get("items", []):
        if item["pantry_item_id"] == pantry_item_id:
            item.update(endringer)
            if "quantity" in endringer or "unit" in endringer:
                base_q, base_u = normaliser_mengde(item["ingredient_type"], item["quantity"], item["unit"])
                item["base_quantity"] = base_q
                item["base_unit"] = base_u
            return pantry
    raise KeyError(f"Ingen pantry-post med pantry_item_id={pantry_item_id!r}")


def slett_pantry_item(pantry, pantry_item_id):
    """Fjerner posten med gitt pantry_item_id. Selve slette-BEKREFTELSEN
    («krev eksplisitt handling») er et UI-ansvar (ui/pantry_panel.py) — denne
    funksjonen sletter ubetinget når den kalles, akkurat som
    slett_oppskrift_fil() i modules/recipe_storage.py."""
    pantry = dict(pantry)
    pantry["items"] = [i for i in pantry.get("items", []) if i["pantry_item_id"] != pantry_item_id]
    return pantry


def summer_beholdning_per_ingredient(pantry):
    """Returnerer {(ingredient_type, ingredient_id): total_base_quantity},
    summert på tvers av ALLE lagerposter for samme ingrediens — flere
    poser/lot-nummer/holdbarhetsdatoer av samme ingrediens er tillatt og
    summeres sammen. Nøkkelen inkluderer ingredient_type for å unngå enhver
    (usannsynlig, men mulig) ID-kollisjon på tvers av malt/humle/gjær-
    navnerommene. Utgåtte poster telles fortsatt med (se modulens
    docstring: dette er lagerinformasjon, ikke en automatisk
    kvalitetsdom) — bruk valider_pantry() for utløpsvarsler."""
    sum_ = {}
    for item in pantry.get("items", []):
        key = (item.get("ingredient_type"), item.get("ingredient_id"))
        try:
            mengde = float(item.get("base_quantity", 0.0))
        except (TypeError, ValueError):
            continue
        sum_[key] = sum_.get(key, 0.0) + mengde
    return sum_


# ── Tilgjengelighetsvurdering ────────────────────────────────────────────
def vurder_tilgjengelighet(required, available, ingredient_type, marginer=None):
    """Klassifiserer én ingrediens som 'nok' / 'knapp' / 'mangler' /
    'ukjent_match'. `required=None` betyr at oppskriften ikke oppgir en
    pålitelig nødvendig mengde (typisk gjær i V1, som mangler et lagret
    anbefalt pakkeantall) — IKKE at mengden er 0, som ville gitt en
    misvisende 'nok'-status."""
    if required is None:
        return "ukjent_match"
    marginer = marginer if marginer is not None else STANDARD_MARGIN
    margin = marginer.get(ingredient_type, 0.0)
    if available < required:
        return "mangler"
    if available < required * (1.0 + margin):
        return "knapp"
    return "nok"


def _resolve_navn(ingredient_type, ingredient_id, malt_db, humle_db, gjaer_db):
    db = {"malt": malt_db, "humle": humle_db, "gjaer": gjaer_db}.get(ingredient_type) or {}
    return db.get(ingredient_id, {}).get("display_name", ingredient_id)


def _bygg_rad(ingredient_type, ingredient_id, required_base, tilgjengelig,
              malt_db, humle_db, gjaer_db, marginer):
    navn = _resolve_navn(ingredient_type, ingredient_id, malt_db, humle_db, gjaer_db)
    available_base = tilgjengelig.get((ingredient_type, ingredient_id), 0.0)
    base_unit = "pakke" if ingredient_type == "gjaer" else "g"

    if required_base is None:
        return {
            "ingredient_type": ingredient_type, "ingredient_id": ingredient_id, "name": navn,
            "required_base": None, "available_base": available_base, "missing_base": None,
            "recommended_base": None, "recommendation_gap_base": None,
            "base_unit": base_unit, "status": "ukjent_match",
        }

    margin = (marginer if marginer is not None else STANDARD_MARGIN).get(ingredient_type, 0.0)
    # Faktisk minimumsmangel — UTEN sikkerhetsmargin (krav: "Ikke trekk
    # marginen inn i «mangler»-mengden").
    missing_base = max(0.0, required_base - available_base)
    # Anbefalt mengde MED sikkerhetsmargin, og hvor mye det evt. mangler for
    # å nå DEN — et separat, mykere tall enn faktisk minimumsmangel.
    recommended_base = required_base * (1.0 + margin)
    recommendation_gap_base = max(0.0, recommended_base - available_base)
    status = vurder_tilgjengelighet(required_base, available_base, ingredient_type, marginer)

    return {
        "ingredient_type": ingredient_type, "ingredient_id": ingredient_id, "name": navn,
        "required_base": required_base, "available_base": available_base, "missing_base": missing_base,
        "recommended_base": recommended_base, "recommendation_gap_base": recommendation_gap_base,
        "base_unit": base_unit, "status": status,
    }


def _beregn_gjaer_pakker_anbefalt(recipe, gjaer_id, gjaer_db):
    """Anbefalt gjærpakkeantall for en oppskrift — SAMME formel og
    pitch-rate-tabell som bryggedagsarket (modules/brewday_calc sin
    beregn_pakker(), brukt av lag_brewday_plan()), slik at Pantry/Smart
    Handleliste og bryggedagsarket ALDRI kan vise to ulike anbefalte
    pakkeantall for samme oppskrift.

    Returnerer None (IKKE en gjettet "1 pakke") hvis oppskriften mangler
    det som trengs for å beregne det pålitelig: en reell OG, et positivt
    batchvolum, eller en gjær som faktisk finnes i databasen (uten den vet
    vi ikke pitch-raten/gjærtypen). Et eksplisitt "gjaer_pakker_anbefalt"-
    felt på selve oppskriften (satt av fremtidig kode) overstyrer denne
    beregningen — se beregn_mangler()."""
    stats = recipe.get("stats") or {}
    og = stats.get("og")
    batch_size = recipe.get("batch_size")
    if not og or og <= 1.000 or not batch_size or batch_size <= 0:
        return None

    gjaer_info = (gjaer_db or {}).get(gjaer_id)
    if gjaer_info is None:
        return None

    gjaer_type_key = gjaer_info.get("gjaertype", "Ale").lower()
    return float(beregn_pakker(og, batch_size, gjaer_type_key))


def _ukjent_rad(ingredient_type, navn):
    return {
        "ingredient_type": ingredient_type, "ingredient_id": None, "name": navn or "?",
        "required_base": None, "available_base": None, "missing_base": None,
        "recommended_base": None, "recommendation_gap_base": None,
        "base_unit": "pakke" if ingredient_type == "gjaer" else "g", "status": "ukjent_match",
    }


def beregn_mangler(recipe, pantry, malt_db=None, humle_db=None, gjaer_db=None, marginer=None):
    """Sammenligner en oppskrifts ingrediensbehov mot lageret og returnerer
    én rad per unik ingrediens (malt/humle/gjær). Leser KUN fra `recipe` —
    endrer aldri oppskriften, prosessprofilen, vannkjemien eller
    scale-faktoren. Kall denne på nytt (ingen caching) hver gang oppskriften
    endres/skaleres, slik at mangellisten alltid reflekterer gjeldende
    ingrediensmengder live.

    `recipe` forventes å ha samme form som modules/recipe.py sitt
    Recipe Object: "malts": [{"id", "mengde" (kg)}], "hops": [{"id", "gram", "tid"}],
    "yeast": <id-streng>. Malt-mengde konverteres fra kg til gram her.

    Gjær har i dagens oppskriftsmodell ikke noe eksplisitt lagret
    "gjaer_pakker_anbefalt"-felt (støttet her hvis en fremtidig oppskrift
    faktisk setter det), så "required" for gjær beregnes i stedet med
    SAMME pitch-rate-formel som bryggedagsarket (se
    _beregn_gjaer_pakker_anbefalt() / modules/brewday_calc.beregn_pakker())
    — aldri en gjettet "1 pakke". Mangler oppskriften det formelen trenger
    (reell OG, positivt batchvolum, gjæren finnes i databasen), forblir
    "required" bevisst None (status 'ukjent_match')."""
    tilgjengelig = summer_beholdning_per_ingredient(pantry)
    rader = []

    trenger_malt = {}
    for m in recipe.get("malts", []):
        m_id = m.get("id")
        if not m_id:
            rader.append(_ukjent_rad("malt", m.get("navn")))
            continue
        trenger_malt[m_id] = trenger_malt.get(m_id, 0.0) + float(m.get("mengde", 0.0)) * 1000.0
    for m_id, required_base in trenger_malt.items():
        rader.append(_bygg_rad("malt", m_id, required_base, tilgjengelig, malt_db, humle_db, gjaer_db, marginer))

    trenger_humle = {}
    for h in recipe.get("hops", []):
        h_id = h.get("id")
        if not h_id:
            rader.append(_ukjent_rad("humle", h.get("navn")))
            continue
        trenger_humle[h_id] = trenger_humle.get(h_id, 0.0) + float(h.get("gram", 0.0))
    for h_id, required_base in trenger_humle.items():
        rader.append(_bygg_rad("humle", h_id, required_base, tilgjengelig, malt_db, humle_db, gjaer_db, marginer))

    gjaer_id = recipe.get("yeast")
    if gjaer_id:
        required_base = recipe.get("gjaer_pakker_anbefalt")
        if required_base is None:
            required_base = _beregn_gjaer_pakker_anbefalt(recipe, gjaer_id, gjaer_db)
        rader.append(_bygg_rad("gjaer", gjaer_id, required_base, tilgjengelig, malt_db, humle_db, gjaer_db, marginer))

    return rader


# ── Validering / varsler ─────────────────────────────────────────────────
def valider_pantry(pantry, i_dag=None):
    """Går gjennom hele lageret og returnerer en liste med varsler (dicts
    med "type"/"pantry_item_id"/"melding") — manglende ingredient_id,
    ugyldig/negativ mengde, ukjent enhet, korrupt/duplikat pantry_item_id,
    utgått vare, vare som utløper snart. Rent informativt: endrer aldri
    lageret selv."""
    i_dag = i_dag or date.today()
    varsler = []
    sette_ider = set()

    for item in pantry.get("items", []):
        pid = item.get("pantry_item_id")
        navn = item.get("name_snapshot") or item.get("ingredient_id") or "?"

        if not pid:
            varsler.append({"type": "manglende_pantry_id", "pantry_item_id": None,
                             "melding": f"Post uten pantry_item_id: {navn}"})
        elif pid in sette_ider:
            varsler.append({"type": "duplikat_id", "pantry_item_id": pid,
                             "melding": f"Duplikat pantry_item_id: {pid} ({navn})"})
        else:
            sette_ider.add(pid)

        if not item.get("ingredient_id"):
            varsler.append({"type": "manglende_ingredient_id", "pantry_item_id": pid,
                             "melding": f"{navn} mangler stabil ingredient_id"})

        mengde = item.get("quantity")
        if not isinstance(mengde, (int, float)) or isinstance(mengde, bool):
            varsler.append({"type": "ugyldig_mengde", "pantry_item_id": pid,
                             "melding": f"{navn} har ugyldig mengde: {mengde!r}"})
        elif mengde < 0:
            varsler.append({"type": "negativ_mengde", "pantry_item_id": pid,
                             "melding": f"{navn} har negativ mengde: {mengde}"})

        gyldige_enheter = _GYLDIGE_ENHETER.get(item.get("ingredient_type"), set())
        if item.get("unit") not in gyldige_enheter:
            varsler.append({"type": "ukjent_enhet", "pantry_item_id": pid,
                             "melding": f"{navn} har ukjent enhet: {item.get('unit')!r}"})

        bf = item.get("best_before")
        if bf:
            try:
                bf_dato = date.fromisoformat(bf) if isinstance(bf, str) else bf
                dager_igjen = (bf_dato - i_dag).days
                if dager_igjen < 0:
                    varsler.append({"type": "utgatt", "pantry_item_id": pid,
                                     "melding": f"{navn} er utgått ({bf})"})
                elif dager_igjen <= UTLOPER_SNART_DAGER:
                    varsler.append({"type": "utloper_snart", "pantry_item_id": pid,
                                     "melding": f"{navn} utløper snart ({bf})"})
            except (ValueError, TypeError):
                varsler.append({"type": "ugyldig_dato", "pantry_item_id": pid,
                                 "melding": f"{navn} har ugyldig best_before-dato: {bf!r}"})

    return varsler


def dager_til_utlop(best_before, i_dag=None):
    """Hjelpefunksjon for UI-visning: antall dager til best_before (negativt
    hvis passert), eller None hvis best_before ikke er satt/ugyldig."""
    if not best_before:
        return None
    i_dag = i_dag or date.today()
    try:
        bf_dato = date.fromisoformat(best_before) if isinstance(best_before, str) else best_before
    except (ValueError, TypeError):
        return None
    return (bf_dato - i_dag).days


# ── Migrering fra det gamle, hump-spesifikke humlelageret ───────────────
def forhandsvis_humlelager_migrering(gammelt_lager, humle_db=None):
    """Bygger en PREVIEW-liste over pantry-poster migreringen VILLE
    opprettet fra det gamle, flate humlelager-formatet
    ({humle_id: gram_på_lager}, se modules/humle_lager.py). Skriver
    INGENTING — verken til pantry.json eller til kildefilen
    (data/humle_lager.json). UI-et skal vise denne previewen og innhente
    eksplisitt brukerbekreftelse før importer_humlelager_migrering()
    kalles."""
    humle_db = humle_db or {}
    forslag = []
    for humle_id, gram in gammelt_lager.items():
        if not isinstance(gram, (int, float)) or gram < 0:
            continue
        navn = humle_db.get(humle_id, {}).get("display_name", humle_id)
        forslag.append(opprett_pantry_item(
            ingredient_type="humle", ingredient_id=humle_id, name_snapshot=navn,
            quantity=float(gram), unit="g",
            notes="Migrert fra det gamle humlelageret (data/humle_lager.json)",
        ))
    return forslag


def importer_humlelager_migrering(pantry, forslag):
    """Legger de (brukerbekreftede) forslagene fra
    forhandsvis_humlelager_migrering() til i pantry og returnerer det
    oppdaterte pantry-objektet. Skriver ALDRI til disk selv, og rører
    ALDRI det opprinnelige humlelager-datasettet — kalleren (UI) er
    ansvarlig for å ha vist previewen, innhentet bekreftelse, tatt en
    backup (lag_pantry_backup()) og til slutt kalt lagre_pantry()."""
    nytt = dict(pantry)
    nytt["items"] = list(pantry.get("items", [])) + list(forslag)
    return nytt
