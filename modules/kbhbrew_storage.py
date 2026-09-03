# modules/kbhbrew_storage.py
"""
PRI 3B1 -- konservativ lokal lagring/identitet for NYE Core `.kbhbrew`
V1-brygg (docs/development/CORE_KBHBREW_V1.md).

Eier disk-I/O for det NYE, separate navnerommet recipes/_kbhbrew/ --
ETT JSON-lagret brygg per fil, navngitt etter dets lokale `brewId`.
Dette er BEVISST atskilt fra modules/recipe_storage.py sin
`recipes/_logs/`-flate loggliste-modell: en ny Core V1-brew har en helt
annen form (frosset snapshot, egen identitet) og skal ALDRI kunne
overskrive, slås sammen med, eller på annen måte røre den eksisterende
legacy-loggen for samme oppskrift. `modules/recipe_storage.py` er
uendret av denne modulen og forblir alene ansvarlig for
`recipes/_logs/`/legacy-loggfiler.

Ren oversettelse (parsing/frysing/eksport-bygging) skjer i
modules/kbhbrew.py -- denne modulen kaller den og legger KUN til det
minimale filsystem-/identitetslaget rundt: minting av lokal `brewId`,
duplikat-sjekk på `originBrewId` ved import (Section 5.14), og
atomisk skriving/lesing (samme mønster som recipe_storage.py sin
_skriv_json_atomisk).

Ingen backend/cloud/database -- lokal-først, som resten av App.
Respekterer DEMO_MODE på alle skrivinger, samme etablerte mønster som
recipe_storage.py/pantry.py/equipment.py.
"""
import copy
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from config import DEMO_MODE
from modules.kbhbrew import (
    bygg_kbhbrew_konvolutt,
    bygg_ny_brew,
    parse_kbhbrew_json,
)

_log = logging.getLogger(__name__)

_KBHBREW_UNDERMAPPE = "_kbhbrew"
_MANIFEST_FILSTI = os.path.join("core", "manifest.json")


def _mappe():
    """Aktiv oppskriftsmappe -- lest FRISKT ved hvert kall, aldri
    frosset ved modul-import. Samme begrunnelse og samme miljøvariabel
    (KVERNHAUG_RECIPES_DIR, KUN for testisolasjon) som
    modules/recipe_storage.py::_mappe() -- se den for full forklaring.
    Ikke importert derfra: hver modul i dette laget eier sin egen
    filstilogikk (samme etablerte mønster som modules/pantry.py/
    modules/equipment.py)."""
    return os.getenv("KVERNHAUG_RECIPES_DIR", "recipes")


def _kbhbrew_mappe():
    return os.path.join(_mappe(), _KBHBREW_UNDERMAPPE)


def _sikre_kbhbrew_mappe():
    mappe = _kbhbrew_mappe()
    if not os.path.exists(mappe):
        os.makedirs(mappe)


def _brew_filsti(brew_id):
    return os.path.join(_kbhbrew_mappe(), f"{brew_id}.json")


def _skriv_json_atomisk(filsti, data):
    """Skriver JSON til en midlertidig fil og erstatter deretter
    målfilen med os.replace (atomisk på både Windows og POSIX) -- samme
    mønster som modules/recipe_storage.py::_skriv_json_atomisk()."""
    tmp_sti = filsti + f".tmp_{uuid.uuid4().hex[:8]}"
    try:
        with open(tmp_sti, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_sti, filsti)
    except Exception:
        try:
            os.remove(tmp_sti)
        except OSError:
            pass
        raise


def _les_manifest_datasets():
    """Leser core/manifest.json og trekker ut schema_version/
    data_version/checksum per datasett (malt/humle/gjaer) -- Core sitt
    normative provenance-mål (CORE_KBHBREW_V1.md Section 5.12). I
    motsetning til Web (som kun har tilgang til genererte web/data/*.json
    UTEN manifest-metadata, se CORE_KBHBREW_V1.md "Provenance
    implementation status") kan App lese core/manifest.json direkte --
    ingen build-pipeline-endring nødvendig her.

    Returnerer None (ALDRI en fabrikert/tom placeholder) hvis manifestet
    mangler, er korrupt, eller ikke inneholder noen gyldige datasett-
    oppføringer -- et ærlig, dokumentert hull er alltid å foretrekke
    fremfor en gjettet verdi (Section 5.12)."""
    try:
        with open(_MANIFEST_FILSTI, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    datasets = manifest.get("datasets")
    if not isinstance(datasets, dict):
        return None
    ut = {}
    for navn in ("malt", "humle", "gjaer"):
        ds = datasets.get(navn)
        if not isinstance(ds, dict):
            continue
        entry = {}
        if "schema_version" in ds:
            entry["schema_version"] = ds["schema_version"]
        if "data_version" in ds:
            entry["data_version"] = ds["data_version"]
        if isinstance(ds.get("checksum"), dict):
            entry["checksum"] = copy.deepcopy(ds["checksum"])
        if entry:
            ut[navn] = entry
    return ut or None


def _skann_alle_brews():
    """Leser alle gyldige .kbhbrew-lagrede brygg i recipes/_kbhbrew/.
    Returnerer en liste av (filnavn, brew_dict). En enkelt korrupt/
    ufullstendig fil logges og hoppes over -- speiler
    recipe_storage.py::_skann_oppskriftsfiler() sin toleranse -- i
    stedet for å la ÉN skadet fil velte hele oversikten."""
    mappe = _kbhbrew_mappe()
    if not os.path.exists(mappe):
        return []
    ut = []
    for filnavn in os.listdir(mappe):
        if not filnavn.endswith(".json"):
            continue
        filsti = os.path.join(mappe, filnavn)
        try:
            with open(filsti, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("brewId"):
                ut.append((filnavn, data))
        except (OSError, json.JSONDecodeError) as e:
            _log.warning("Kunne ikke lese kbhbrew-fil %s: %s", filsti, e)
    return ut


def finnes_brew_med_origin(origin_brew_id):
    """True hvis et lokalt lagret brygg allerede har akkurat denne
    `originBrewId` -- duplikat-nøkkelen for import (Section 5.14)."""
    return any(brew.get("originBrewId") == origin_brew_id for _, brew in _skann_alle_brews())


def hent_brew(brew_id):
    """Henter ett lokalt lagret brygg ved dets lokale brewId. Returnerer
    None hvis det ikke finnes -- helt normalt, ikke en feiltilstand."""
    filsti = _brew_filsti(brew_id)
    if not os.path.exists(filsti):
        return None
    with open(filsti, "r", encoding="utf-8") as f:
        return json.load(f)


def hent_alle_brews():
    """Kart fra lokal brewId -> brew-dict for alle NYE Core V1-brygg.
    Rører ALDRI recipes/_logs/ -- fullstendig uavhengig navnerom fra
    den eksisterende, uendrede legacy-loggen (modules/recipe_storage.py)."""
    return {brew["brewId"]: brew for _, brew in _skann_alle_brews()}


def opprett_og_lagre_ny_brew(recipe, malt_db, humle_db, gjaer_db, equipment_profile, predicted,
                              recipe_id=None, engine_version=None, brew_id=None):
    """Oppretter og lagrer en HELT NY Core V1-brew: minter en fersk lokal
    identitet (med mindre `brew_id` sendes inn -- KUN for testbarhet/
    deterministiske fixtures, aldri fra brukerinput), fryser snapshotet
    (modules/kbhbrew.py::bygg_ny_brew(), inkl. Core-manifest-provenance
    der tilgjengelig, se _les_manifest_datasets()), og skriver den til
    recipes/_kbhbrew/<brewId>.json.

    No-op (returnerer None) i DEMO_MODE -- samme etablerte mønster som
    recipe_storage.py::lagre_oppskrift()/pantry.py/equipment.py.

    Kaster UgyldigOppskriftForEksport (fra modules/kbh_contract.py, via
    modules/kbhbrew.py) hvis `recipe` ikke er en gyldig, eksporterbar
    oppskrift -- ingen ny brew kan noensinne fryses fra ugyldige data."""
    if DEMO_MODE:
        return None
    minted_brew_id = brew_id or f"brew-{uuid.uuid4()}"
    now = datetime.now(timezone.utc).isoformat()
    brew = bygg_ny_brew(
        recipe, malt_db, humle_db, gjaer_db, equipment_profile, predicted,
        created_at=now, brew_id=minted_brew_id, recipe_id=recipe_id,
        engine_version=engine_version, manifest_datasets=_les_manifest_datasets(),
    )
    _sikre_kbhbrew_mappe()
    _skriv_json_atomisk(_brew_filsti(minted_brew_id), brew)
    return brew


def oppdater_brew_lag(brew_id, actuals=None, sensing=None, learning=None, status=None, brewed_at=None):
    """Oppdaterer KUN de mutable lagene (Section 5.5: status, actuals,
    sensing, learning, brewedAt) på et allerede lagret brygg. Godtar
    bevisst IKKE et `snapshot`-argument i det hele tatt -- det frosne
    laget kan ALDRI endres etter opprettelse, denne funksjonen har
    ingen kodevei som i det hele tatt kunne skrevet over det.

    Kun de lagene som faktisk sendes inn (ikke None) oppdateres; øvrige
    lag beholder sin nåværende, lagrede verdi uendret. No-op (returnerer
    None) i DEMO_MODE eller hvis `brew_id` ikke finnes lokalt fra før."""
    if DEMO_MODE:
        return None
    brew = hent_brew(brew_id)
    if brew is None:
        return None
    if actuals is not None:
        brew["actuals"] = copy.deepcopy(actuals)
    if sensing is not None:
        brew["sensing"] = copy.deepcopy(sensing)
    if learning is not None:
        brew["learning"] = copy.deepcopy(learning)
    if status is not None:
        brew["status"] = status
    if brewed_at is not None:
        brew["brewedAt"] = brewed_at
    _skriv_json_atomisk(_brew_filsti(brew_id), brew)
    return brew


def eksporter_kbhbrew(brew_id):
    """Bygger en komplett `.kbhbrew` V1-konvolutt for et lokalt lagret
    brygg, klar for kalleren å skrive til fil/tilby som nedlasting (selve
    fil-/nedlastings-UX-en er en fremtidig PRI 3B2-bekymring -- denne
    funksjonen returnerer kun den ferdigbygde dict-strukturen). Returnerer
    None hvis `brew_id` ikke finnes lokalt."""
    brew = hent_brew(brew_id)
    if brew is None:
        return None
    generert_tidspunkt = datetime.now(timezone.utc).isoformat()
    return bygg_kbhbrew_konvolutt(brew, generert_tidspunkt)


def importer_kbhbrew(tekst):
    """Importerer en `.kbhbrew` V1-fils tekstinnhold som et NYTT, lokalt
    brygg. Speiler Web sin importerBrygg()-policy (Section 5.14):

      - en fersk lokal `brewId` mintes ALLTID (aldri lest fra filen);
      - `recipeId` droppes alltid ved import (lokal-maskin-scoped,
        meningsløst på en mottakende maskin, Section 2);
      - finnes det allerede et lokalt lagret brygg med samme
        `originBrewId`, avvises importen eksplisitt som duplikat
        ({"ok": False, "duplicate": True}) -- ALDRI en stille
        overskriving eller sammenslåing.

    Valideringen (modules/kbhbrew.py::parse_kbhbrew_json, som kan kaste
    UgyldigKbhbrewForImport) skjer FØR duplikat-sjekken, slik at en
    ugyldig fil aldri kan late som en (falsk) duplikatkonflikt.

    Returnerer {"ok": False, "demo_mode": True} uten å skrive noe i
    DEMO_MODE -- selve parsingen/valideringen kjøres likevel, slik at
    en ugyldig fil fortsatt kaster samme feil i demo som i normal
    drift (konsistent feiloppførsel, kun selve skrivingen er en no-op)."""
    native = parse_kbhbrew_json(tekst)
    origin = native["originBrewId"]

    if DEMO_MODE:
        return {"ok": False, "demo_mode": True, "originBrewId": origin}

    if finnes_brew_med_origin(origin):
        return {"ok": False, "duplicate": True, "originBrewId": origin}

    minted_brew_id = f"brew-{uuid.uuid4()}"
    brew = dict(native)
    brew["brewId"] = minted_brew_id
    brew["recipeId"] = None

    _sikre_kbhbrew_mappe()
    _skriv_json_atomisk(_brew_filsti(minted_brew_id), brew)
    return {"ok": True, "brewId": minted_brew_id, "originBrewId": origin, "brew": brew}
