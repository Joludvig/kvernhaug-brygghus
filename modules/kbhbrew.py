# modules/kbhbrew.py
"""
PRI 3B1 -- ren App `.kbhbrew` V1-motor
(docs/development/CORE_KBHBREW_V1.md / core/kbhbrew_v1.schema.json).

Speiler mønsteret fra modules/kbh_contract.py (App -> .kbhrecipe) og
modules/kbh_import.py (.kbhrecipe -> App) for den nye, søster-
kontrakten `.kbhbrew`. Ren modul: ingen filsystem-tilgang, ingen
Streamlit-avhengighet, ingen sideeffekter -- selve lagring/identitet
eies av modules/kbhbrew_storage.py, akkurat som recipe_storage.py eier
disk-I/O for .kbhrecipe mens denne modulen kun oversetter.

Omfang (PRI 3B1, se issue): reader/writer + frosset snapshot-bygging
for NYE brygg. INGEN Streamlit-UI, INGEN konvertering/migrering av
eksisterende App-bryggelogger (recipes/_logs/) -- de leses/skrives
utelukkende av modules/recipe_storage.py, uendret, og denne modulen rører
dem aldri.

Fem-lags-modellen (CORE_KBHBREW_V1.md Section 1/5):
  1. Identitet/livssyklus  -- brewId/originBrewId/parentBrewId/recipeId,
     status, createdAt/brewedAt
  2. Snapshot (frosset)    -- recipe/ingredients/equipment/predicted/
     provenance, skrevet ÉN gang, aldri endret siden
  3. Actuals               -- instrumentmålinger (og/fg/volumeL/notes)
  4. Sensing                -- subjektiv, dokumentert opplevelse
  5. Learning                -- fremoverrettet lærdom

Owner-ratifiserte regler denne modulen håndhever (Section 8, issue #22):
  #2 Unknown-field passthrough er PÅKREVD på hvert lag (og konvolutten).
  #3 `actual_abv`/`abv`/`actualAbv` er ALDRI en kanonisk wire-verdi --
     kan IKKE eksporteres, selv via passthrough (App kan beholde en egen
     lokal cache-verdi, det er IKKE denne modulens ansvar/bekymring).
  #5 Ingen V1 "actual process used"-felt.
"""
import copy
import uuid

from modules.kbh_contract import recipe_to_kbhrecipe_payload

KBHBREW_FORMAT = "kbhbrew"
KBHBREW_VERSION = 1
_GENERATOR = "Kvernhaug Brygghus (Streamlit)"

# App sin kalkulasjonsmotor-versjon (CORE_KBHBREW_V1.md Section 5.12) --
# bumpes manuelt når modules/calculations.py, modules/flavor_engine.py
# eller modules/style_engine.py endrer output for samme input. Speiler
# Web sin engineVersion-konvensjon (samme felt, egen telling per app).
ENGINE_VERSION = 1

_TALLTYPER = (int, float)

_STATUS_VERDIER = frozenset({"active", "done", "discarded"})

# Kjente toppnivå-felt på selve brew-objektet (Section 5.3/5.11) --
# brewId/recipeId er LOKAL identitet og skrives ALDRI til en eksportert
# konvolutt (Section 5.3) men er likevel "kjente" begreper her, slik at
# de aldri kan smugles inn via passthrough (samme to-punkts-forsvar som
# kbh_contract.py/kbh_import.py sine ekvivalenter).
_KJENTE_BREW_FELT = frozenset({
    "brewId", "originBrewId", "parentBrewId", "recipeId", "status",
    "createdAt", "brewedAt", "snapshot", "actuals", "sensing", "learning",
})

_KJENTE_ENVELOPE_FELT = frozenset({"format", "version", "exportedAt", "generator", "brew"})

_KJENTE_ACTUALS_FELT = frozenset({"og", "fg", "volumeL", "notes"})
_KJENTE_SENSING_FELT = frozenset({"judgment", "flavorProfile", "notes"})
_KJENTE_LEARNING_FELT = frozenset({"whatWorked", "whatChanged", "nextTime"})

_GYLDIGE_JUDGMENT_VERDIER = frozenset({"yes", "maybe", "no"})

# Ratifisert Section 8 #3 -- disse skal ALDRI kunne nå .kbhbrew-wire,
# uansett hva en (evt. hånd-redigert/fremmed) passthrough-dict inneholder
# under et av disse navnene. Filtreres eksplisitt ved EKSPORT, uavhengig
# av at ingen av dem er i _KJENTE_ACTUALS_FELT.
FORBUDTE_ACTUALS_EKSPORTFELT = frozenset({"actual_abv", "abv", "actualAbv"})


# ─── Delte hjelpere (samme prinsipp som kbh_contract.py/kbh_import.py) ──

def _er_reelt_tall(v):
    if isinstance(v, bool):
        return False
    if not isinstance(v, _TALLTYPER):
        return False
    if v != v:  # NaN
        return False
    if v in (float("inf"), float("-inf")):
        return False
    return True


def _ikke_tom_streng(v):
    return isinstance(v, str) and v.strip() != ""


def _tall_eller_none(v):
    return v if _er_reelt_tall(v) else None


def _tekst_eller_none(v):
    t = _tekst_trimmet(v)
    return t if t else None


def _tekst_trimmet(v):
    return v.strip() if isinstance(v, str) else ""


def _bygg_passthrough(kilde, kjente_felt):
    """Fanger ethvert felt i `kilde` som IKKE er i `kjente_felt` inn i en
    ny, dyp-kopiert dict -- returnerer {} (aldri None) hvis ingenting er
    ukjent, slik kalleren enkelt kan sjekke `if passthrough:`."""
    if not isinstance(kilde, dict):
        return {}
    return {k: copy.deepcopy(v) for k, v in kilde.items() if k not in kjente_felt}


def _flett_inn_passthrough(payload, passthrough):
    """Fletter en bevart passthrough-dict inn i en allerede FERDIGBYGD
    payload -- hver nøkkel skrives KUN hvis den ikke allerede finnes i
    payload (kjente felt, satt over, vinner alltid). Muterer og
    returnerer `payload` i-place."""
    if not isinstance(passthrough, dict) or not passthrough:
        return payload
    for nokkel, verdi in passthrough.items():
        if nokkel in payload:
            continue
        payload[nokkel] = copy.deepcopy(verdi)
    return payload


class UgyldigKbhbrewForImport(ValueError):
    """Kastes når en `.kbhbrew`-fil ikke kan leses/importeres trygt av
    dagens App-motor. Én klasse, ikke et hierarki (samme mønster som
    modules/kbh_import.py sin UgyldigKbhrecipeForImport) -- `kategori`
    skiller feilårsaken maskinlesbart, `melding` er alltid en
    menneskelesbar, norsk tekst."""

    def __init__(self, kategori, melding, **detaljer):
        super().__init__(melding)
        self.kategori = kategori
        self.melding = melding
        for k, v in detaljer.items():
            setattr(self, k, v)


KATEGORI_INVALID_JSON = "invalid_json"
KATEGORI_INVALID_ENVELOPE = "invalid_envelope"
KATEGORI_UNSUPPORTED_VERSION = "unsupported_version"
KATEGORI_INVALID_BREW = "invalid_brew"
KATEGORI_INVALID_SNAPSHOT = "invalid_snapshot"


def _feil(kategori, melding, **detaljer):
    raise UgyldigKbhbrewForImport(kategori, melding, **detaljer)


# ══════════════════════════════════════════════════════════════════════
# Frosset snapshot-bygging (CORE_KBHBREW_V1.md Section 5.5) -- KUN for
# NYE brygg. Kalles ÉN gang, ved opprettelse -- selve frysing/aldri-
# endres-siden-policyen håndheves av modules/kbhbrew_storage.py (som
# aldri eksponerer en "oppdater snapshot"-funksjon i det hele tatt).
# ══════════════════════════════════════════════════════════════════════

def _frys_ingredienser(recipe_payload, malt_db, humle_db, gjaer_db):
    """Full embed (Owner decision #1, Option A) -- de KOMPLETTE
    master-data-oppføringene for hver ingrediens oppskriften faktisk
    refererer til, dyp-kopiert. App har ingen custom-ingredienser i
    dagens datamodell (kbh_contract.py bygger aldri en "custom"-rad),
    så alle id-er slås opp direkte i databasen; en id som (uventet)
    mangler i databasen hoppes stille over her -- kun det som faktisk
    er tilgjengelig ved snapshot-tidspunktet kan fryses (Section 3 i
    issue #24 / Section 5.5)."""
    malt_db = malt_db or {}
    humle_db = humle_db or {}
    gjaer_db = gjaer_db or {}

    malt_ut = {}
    for rad in recipe_payload.get("malt") or []:
        id_ = rad.get("id")
        if id_ and id_ in malt_db:
            malt_ut[id_] = copy.deepcopy(malt_db[id_])

    humle_ut = {}
    for rad in recipe_payload.get("humle") or []:
        id_ = rad.get("id")
        if id_ and id_ in humle_db:
            humle_ut[id_] = copy.deepcopy(humle_db[id_])

    gjaer_ut = {}
    gjaer_id = recipe_payload.get("gjaerId")
    if gjaer_id and gjaer_id in gjaer_db:
        gjaer_ut[gjaer_id] = copy.deepcopy(gjaer_db[gjaer_id])

    return {"malt": malt_ut, "humle": humle_ut, "gjaer": gjaer_ut}


def _frys_predicted(predicted):
    """Kontrollert felt-for-felt-bygging (IKKE et blindt objekt-dump av
    hva kalleren måtte sende inn) -- reduserer alltid `style` til
    {stil, score} (Section 2/5.5: den lokaliserte balanse-/problemer-/
    mangler-teksten skal ALDRI fryses, samme regel som Web)."""
    predicted = predicted or {}
    ut = {}
    for felt in ("og", "fg", "abv", "ibu", "ebc", "buGu"):
        v = predicted.get(felt)
        if _er_reelt_tall(v):
            ut[felt] = v
    flavor_profile = predicted.get("flavorProfile")
    if isinstance(flavor_profile, dict) and flavor_profile:
        ut["flavorProfile"] = copy.deepcopy(flavor_profile)
    style = predicted.get("style")
    if isinstance(style, dict):
        ut["style"] = {"stil": style.get("stil"), "score": style.get("score")}
    return ut


def _bygg_provenance(engine_version, recipe_schema_version, captured_at, manifest_datasets):
    """Section 5.12 -- `datasets` (Core-manifest-avledet provenance)
    settes KUN hvis kalleren faktisk sendte inn troverdige verdier
    (`manifest_datasets`, lest av modules/kbhbrew_storage.py fra
    core/manifest.json). `manifest_datasets=None`/tom betyr en ærlig
    kjent hull, ALDRI fabrikert -- nøkkelen `datasets` utelates da helt
    i stedet for å skrive en tom/gjettet verdi."""
    provenance = {
        "engineVersion": engine_version,
        "recipeSchemaVersion": recipe_schema_version,
        "capturedAt": captured_at,
    }
    if isinstance(manifest_datasets, dict) and manifest_datasets:
        datasets = {}
        for navn in ("malt", "humle", "gjaer"):
            ds = manifest_datasets.get(navn)
            if isinstance(ds, dict) and ds:
                datasets[navn] = copy.deepcopy(ds)
        if datasets:
            provenance["datasets"] = datasets
    return provenance


def bygg_ny_brew_snapshot(recipe, malt_db, humle_db, gjaer_db, equipment_profile, predicted,
                           captured_at, engine_version=None, manifest_datasets=None):
    """Bygger et frosset V1-snapshot for en NY brew (Section 5.5). Ren
    funksjon: leser kun argumentene sine, dyp-kopierer/rekonstruerer alt
    -- ingen sideeffekter, ingen disk-/Streamlit-tilgang, ingen levende
    referanse tilbake til `recipe`/`malt_db`/... beholdes noe sted i
    resultatet (bevist av tests/test_kbhbrew_snapshot.py sine
    mutasjonstester).

    `recipe` er et App Recipe Object (modules/recipe.py::
    bygg_recipe_object) -- oversettes til en .kbhrecipe-formet nyttelast
    via den ALLEREDE eksisterende, godkjente kbh_contract.py-skriveren
    (Section 5.4: "en frosset KOPI av en .kbhrecipe-formet nyttelast").
    Kaster UgyldigOppskriftForEksport (fra kbh_contract.py) hvis
    `recipe` ikke er gyldig -- en ny brew kan aldri fryses fra en
    oppskrift App selv ikke kunne eksportert.

    `predicted` er et App-internt dict kalleren already har beregnet
    ({og, fg, abv, ibu, ebc, buGu, flavorProfile, style: {stil, score}})
    -- denne funksjonen beregner ALDRI selv, kun fryser (samme
    ansvarsgrense som Web sin byggBrewSnapshot()).

    `manifest_datasets`, hvis satt, må være
    {"malt"|"humle"|"gjaer": {"schema_version", "data_version",
    "checksum"}, ...} -- typisk lest av modules/kbhbrew_storage.py fra
    core/manifest.json. `None` betyr "ingen troverdig kilde tilgjengelig
    nå" og fabrikerer ALDRI en verdi (Section 5.12)."""
    recipe_payload = recipe_to_kbhrecipe_payload(recipe)
    return {
        "recipe": recipe_payload,
        "ingredients": _frys_ingredienser(recipe_payload, malt_db, humle_db, gjaer_db),
        "equipment": copy.deepcopy(equipment_profile) if equipment_profile else None,
        "predicted": _frys_predicted(predicted),
        "provenance": _bygg_provenance(
            engine_version if engine_version is not None else ENGINE_VERSION,
            recipe_payload.get("recipeSchemaVersion"),
            captured_at,
            manifest_datasets,
        ),
    }


def bygg_ny_brew(recipe, malt_db, humle_db, gjaer_db, equipment_profile, predicted,
                  created_at, brew_id, recipe_id=None, engine_version=None,
                  manifest_datasets=None):
    """Oppretter et NYTT, App-native Core V1 brew-objekt med et frosset
    snapshot. Ren funksjon -- `brew_id` MÅ sendes inn av kalleren
    (modules/kbhbrew_storage.py minter en fersk lokal id der; denne
    modulen minter ALDRI selv en id på egen hånd, for å holde den fri
    for tilfeldighet/sideeffekter og enkel å teste deterministisk).
    `originBrewId` defaulter til `brew_id` ved opprettelse (Section
    5.3) -- de er samme streng for et brygg som aldri har vært
    eksportert/importert.

    `status` settes alltid til "active" for en ny brew (Section 5.10:
    metadata, ikke en tvungen tilstandsmaskin -- kalleren kan endre den
    senere via modules/kbhbrew_storage.py sin lag-oppdaterer).
    `parentBrewId` er alltid None i V1 (reservert, Section 5.3)."""
    snapshot = bygg_ny_brew_snapshot(
        recipe, malt_db, humle_db, gjaer_db, equipment_profile, predicted,
        captured_at=created_at, engine_version=engine_version, manifest_datasets=manifest_datasets,
    )
    return {
        "brewId": brew_id,
        "originBrewId": brew_id,
        "parentBrewId": None,
        "recipeId": recipe_id,
        "status": "active",
        "createdAt": created_at,
        "brewedAt": None,
        "snapshot": snapshot,
        "actuals": {},
        "sensing": {},
        "learning": {},
    }


# ══════════════════════════════════════════════════════════════════════
# Skriver: App-native brew -> .kbhbrew V1-konvolutt
# ══════════════════════════════════════════════════════════════════════

def _bygg_actuals_payload(actuals):
    actuals = actuals if isinstance(actuals, dict) else {}
    ut = {}
    for felt in ("og", "fg", "volumeL"):
        v = _tall_eller_none(actuals.get(felt))
        if v is not None:
            ut[felt] = v
    notes = _tekst_eller_none(actuals.get("notes"))
    if notes is not None:
        ut["notes"] = notes
    _flett_inn_passthrough(ut, actuals.get("_kbh_brew_actuals_passthrough"))
    # Ratifisert forbud (Section 8 #3) -- håndheves UAVHENGIG av
    # ovenstående passthrough-fletting, som et eget, uavhengig vern
    # (samme "to uavhengige punkter"-prinsipp som Web sin
    # BREW_ACTUALS_FORBUDTE_EKSPORTFELT-filtrering, PR #23).
    for forbudt in FORBUDTE_ACTUALS_EKSPORTFELT:
        ut.pop(forbudt, None)
    return ut


def _bygg_sensing_payload(sensing):
    sensing = sensing if isinstance(sensing, dict) else {}
    ut = {}
    judgment = sensing.get("judgment")
    if judgment in _GYLDIGE_JUDGMENT_VERDIER:
        ut["judgment"] = judgment
    flavor_profile = sensing.get("flavorProfile")
    if isinstance(flavor_profile, dict) and flavor_profile:
        ut["flavorProfile"] = copy.deepcopy(flavor_profile)
    notes = _tekst_eller_none(sensing.get("notes"))
    if notes is not None:
        ut["notes"] = notes
    _flett_inn_passthrough(ut, sensing.get("_kbh_brew_sensing_passthrough"))
    return ut


def _bygg_learning_payload(learning):
    learning = learning if isinstance(learning, dict) else {}
    ut = {}
    for felt in ("whatWorked", "whatChanged", "nextTime"):
        v = _tekst_eller_none(learning.get(felt))
        if v is not None:
            ut[felt] = v
    _flett_inn_passthrough(ut, learning.get("_kbh_brew_learning_passthrough"))
    return ut


def brew_to_kbhbrew_payload(brew):
    """Oversetter et App-native brew-objekt til en Core `.kbhbrew` V1
    `brew`-nyttelast (KBH_CORE_CONTRACT.md-mønsteret, speilbildet av
    kbh_contract.py::recipe_to_kbhrecipe_payload()).

    `brewId`/`recipeId` skrives ALDRI til den eksporterte nyttelasten
    -- begge er LOKAL identitet (Section 5.3), en kanonisk eksportert
    fil bærer dem aldri (se den frosne legacy Web-fixturen,
    tests/fixtures/legacy/web/kbhbrew_v1.json, som heller ikke har dem).

    `snapshot` skrives som en uendret dyp kopi -- den er allerede
    "effectively passthrough-safe" (Section 5.13: frosset ved
    opprettelse, aldri filtrert), akkurat som Web sin ekvivalent.

    Kjente felt (over) vinner ALLTID over en (potensielt utdatert)
    `_kbh_brew_passthrough`-verdi under samme navn -- se
    _flett_inn_passthrough()."""
    if not isinstance(brew, dict):
        raise ValueError("brew må være et objekt (dict).")

    origin = brew.get("originBrewId") or brew.get("brewId")
    if not _ikke_tom_streng(origin):
        raise ValueError("Brew mangler en gyldig originBrewId/brewId å eksportere.")

    status = brew.get("status")
    if status not in _STATUS_VERDIER:
        raise ValueError(f"Brew har ugyldig status for eksport: {status!r}")

    created_at = brew.get("createdAt")
    if not _ikke_tom_streng(created_at):
        raise ValueError("Brew mangler en gyldig createdAt for eksport.")

    snapshot = brew.get("snapshot")
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("recipe"), dict) \
            or not isinstance(snapshot.get("predicted"), dict):
        raise ValueError("Brew mangler et gyldig snapshot (recipe + predicted) for eksport.")

    payload = {
        "originBrewId": origin,
        "parentBrewId": brew.get("parentBrewId"),
        "status": status,
        "createdAt": created_at,
        "snapshot": copy.deepcopy(snapshot),
    }
    brewed_at = brew.get("brewedAt")
    if _ikke_tom_streng(brewed_at):
        payload["brewedAt"] = brewed_at

    actuals_payload = _bygg_actuals_payload(brew.get("actuals"))
    if actuals_payload:
        payload["actuals"] = actuals_payload

    sensing_payload = _bygg_sensing_payload(brew.get("sensing"))
    if sensing_payload:
        payload["sensing"] = sensing_payload

    learning_payload = _bygg_learning_payload(brew.get("learning"))
    if learning_payload:
        payload["learning"] = learning_payload

    _flett_inn_passthrough(payload, brew.get("_kbh_brew_passthrough"))
    return payload


def bygg_kbhbrew_konvolutt(brew, generert_tidspunkt):
    """Bygger en komplett `.kbhbrew`-konvolutt: {format, version,
    exportedAt, generator, brew}. `generert_tidspunkt` sendes inn
    eksplisitt (ISO 8601-streng) av kalleren -- samme rene, testbare
    mønster som kbh_contract.py::bygg_kbhrecipe_konvolutt().

    Kaster ValueError hvis `brew` ikke lar seg oversette (se
    brew_to_kbhbrew_payload)."""
    payload = brew_to_kbhbrew_payload(brew)
    envelope = {
        "format": KBHBREW_FORMAT,
        "version": KBHBREW_VERSION,
        "exportedAt": generert_tidspunkt,
        "generator": _GENERATOR,
        "brew": payload,
    }
    _flett_inn_passthrough(envelope, brew.get("_kbh_brew_envelope_passthrough"))
    return envelope


# ══════════════════════════════════════════════════════════════════════
# Leser: .kbhbrew V1 JSON-tekst -> App-native brew-objekt
# ══════════════════════════════════════════════════════════════════════

def _parse_json(tekst):
    import json

    def _avvis_json_konstant(navn):
        raise ValueError(f"JSON-konstanten '{navn}' er ikke gyldig i en .kbhbrew-fil.")

    try:
        return json.loads(tekst, parse_constant=_avvis_json_konstant)
    except (ValueError, TypeError) as e:
        _feil(KATEGORI_INVALID_JSON, f"Filen kunne ikke leses som gyldig JSON: {e}")


def _normaliser_actuals(raw):
    """Toleranse-normalisering (Section 5.16): kjente felt tallsjekkes/
    trimmes; alt annet havner i en per-lag passthrough-container.
    ALDRI en stille reject av hele brygget for et malformert enkeltfelt
    -- kun det ENE feltet forkastes (samme prinsipp som Web sine
    _tallEllerUndefined()/_tekstEllerUndefined()). Et evt. `actual_abv`/
    `abv`/`actualAbv`-felt i filen fanges her SOM passthrough (bevart
    for lesing/rundtur), men kan ALDRI re-eksporteres -- se
    FORBUDTE_ACTUALS_EKSPORTFELT i skriveren over."""
    raw = raw if isinstance(raw, dict) else {}
    ut = {}
    for felt in ("og", "fg", "volumeL"):
        v = _tall_eller_none(raw.get(felt))
        if v is not None:
            ut[felt] = v
    notes = _tekst_eller_none(raw.get("notes"))
    if notes is not None:
        ut["notes"] = notes
    passthrough = _bygg_passthrough(raw, _KJENTE_ACTUALS_FELT)
    if passthrough:
        ut["_kbh_brew_actuals_passthrough"] = passthrough
    return ut


def _normaliser_sensing(raw):
    raw = raw if isinstance(raw, dict) else {}
    ut = {}
    judgment = raw.get("judgment")
    if judgment in _GYLDIGE_JUDGMENT_VERDIER:
        ut["judgment"] = judgment
    flavor_profile = raw.get("flavorProfile")
    if isinstance(flavor_profile, dict) and flavor_profile:
        ut["flavorProfile"] = copy.deepcopy(flavor_profile)
    notes = _tekst_eller_none(raw.get("notes"))
    if notes is not None:
        ut["notes"] = notes
    passthrough = _bygg_passthrough(raw, _KJENTE_SENSING_FELT)
    if passthrough:
        ut["_kbh_brew_sensing_passthrough"] = passthrough
    return ut


def _normaliser_learning(raw):
    raw = raw if isinstance(raw, dict) else {}
    ut = {}
    for felt in ("whatWorked", "whatChanged", "nextTime"):
        v = _tekst_eller_none(raw.get(felt))
        if v is not None:
            ut[felt] = v
    passthrough = _bygg_passthrough(raw, _KJENTE_LEARNING_FELT)
    if passthrough:
        ut["_kbh_brew_learning_passthrough"] = passthrough
    return ut


def parse_kbhbrew_json(tekst):
    """Parser og validerer en `.kbhbrew` V1-fils tekstinnhold, og bygger
    App-native brew-data (reverse adapter av
    bygg_kbhbrew_konvolutt()/brew_to_kbhbrew_payload()).

    Returnerer et App-native brew-dict:
        {
          "originBrewId", "parentBrewId", "status", "createdAt",
          "brewedAt", "snapshot",                  # uendret dyp kopi
          "actuals", "sensing", "learning",         # normalisert, se over
          "_kbh_brew_passthrough": {...},           # kun hvis ikke-tom
          "_kbh_brew_envelope_passthrough": {...},  # kun hvis ikke-tom
        }

    IKKE inkludert med vilje: `brewId`, `recipeId`. Import er "import
    as new" (Section 5.14) -- en fersk lokal `brewId` mintes av
    modules/kbhbrew_storage.py, aldri av denne rene leseren, og
    `recipeId` er lokal-maskin-scoped og droppes ved import (samme
    begrunnelse som Web sin importerBrygg(), Section 2).

    Kaster UgyldigKbhbrewForImport (se kategoriene over) ved ethvert
    valideringsbrudd på konvolutt-/identitets-/snapshot-nivå -- ALDRI
    en fallback-/gjettet verdi, ALDRI fuzzy-matching."""
    parsed = _parse_json(tekst)
    if not isinstance(parsed, dict):
        _feil(KATEGORI_INVALID_ENVELOPE, "Toppnivået i filen må være et JSON-objekt.")

    if parsed.get("format") != KBHBREW_FORMAT:
        _feil(KATEGORI_INVALID_ENVELOPE, "Filen mangler en gyldig .kbhbrew-konvolutt (format).")

    versjon = parsed.get("version")
    if not _er_reelt_tall(versjon):
        _feil(KATEGORI_UNSUPPORTED_VERSION, "Filen mangler gyldig versjonsinformasjon (version).")
    if versjon != KBHBREW_VERSION:
        _feil(
            KATEGORI_UNSUPPORTED_VERSION,
            f"Denne filen bruker .kbhbrew versjon {versjon!r}, som ikke støttes her (kun versjon 1).",
        )

    brew_payload = parsed.get("brew")
    if not isinstance(brew_payload, dict):
        _feil(KATEGORI_INVALID_ENVELOPE, "Filen mangler selve bryggrekorden (brew).")

    origin = brew_payload.get("originBrewId")
    if not _ikke_tom_streng(origin):
        _feil(KATEGORI_INVALID_BREW, "Bryggrekorden mangler gyldig originBrewId.")

    status = brew_payload.get("status")
    if status not in _STATUS_VERDIER:
        _feil(KATEGORI_INVALID_BREW, f"Bryggrekorden har ugyldig eller manglende status: {status!r}")

    created_at = brew_payload.get("createdAt")
    if not _ikke_tom_streng(created_at):
        _feil(KATEGORI_INVALID_BREW, "Bryggrekorden mangler gyldig createdAt.")

    snapshot = brew_payload.get("snapshot")
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("recipe"), dict) \
            or not isinstance(snapshot.get("predicted"), dict):
        _feil(
            KATEGORI_INVALID_SNAPSHOT,
            "Bryggrekorden mangler et gyldig snapshot (recipe- og predicted-objekt kreves).",
        )

    native = {
        "originBrewId": origin,
        "parentBrewId": brew_payload.get("parentBrewId"),
        "status": status,
        "createdAt": created_at,
        "brewedAt": brew_payload.get("brewedAt") if _ikke_tom_streng(brew_payload.get("brewedAt")) else None,
        # Frosset lag -- uendret, ufiltrert dyp kopi. Aldri re-tolket her;
        # samme "already effectively passthrough-safe" begrunnelse som
        # skriveren (Section 5.13).
        "snapshot": copy.deepcopy(snapshot),
        "actuals": _normaliser_actuals(brew_payload.get("actuals")),
        "sensing": _normaliser_sensing(brew_payload.get("sensing")),
        "learning": _normaliser_learning(brew_payload.get("learning")),
    }

    brew_passthrough = _bygg_passthrough(brew_payload, _KJENTE_BREW_FELT)
    if brew_passthrough:
        native["_kbh_brew_passthrough"] = brew_passthrough

    envelope_passthrough = _bygg_passthrough(parsed, _KJENTE_ENVELOPE_FELT)
    if envelope_passthrough:
        native["_kbh_brew_envelope_passthrough"] = envelope_passthrough

    return native
