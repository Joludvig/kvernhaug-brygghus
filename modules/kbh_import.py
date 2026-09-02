# modules/kbh_import.py
"""
PRI 2C1 -- ren App-reader for `.kbhrecipe` V1
(docs/development/CORE_KBHRECIPE_V1.md). Speilbildet av
modules/kbh_contract.py (som oversetter App -> V1-payload): denne
modulen oversetter V1-payload -> App-native recipe-data.

Ren modul: ingen filsystem-tilgang, ingen Streamlit-avhengighet, ingen
session_state, ingen sideeffekter, deterministisk. Ikke koblet inn i
App UI-et ennå -- det er PRI 2C2/2C3 sin jobb (se scope guard i PRI 2C1-
rapporten).

VIKTIG PRESISERING (se OPPGAVE M i PRI 2C1-rapporten): kategoriene under
("unsupported_custom_ingredient", "unsupported_process", osv.) beskriver
hva DAGENS App klarer å representere trygt -- IKKE en universell
V1-regel for alle fremtidige lesere. En annen leser (eller en fremtidig
App-versjon med custom-ingrediens-/prosess-støtte) kan lovlig akseptere
mer enn dette uten å bryte selve V1-kontrakten.

STRENGERE ENN kbh_contract.py sin `_er_gyldig_tall()`: JSON tillater i
Python (men ikke i strict JSON/JS) bokstavelige NaN/Infinity-tokens via
`json.loads()`. Disse avvises eksplisitt allerede ved parsing
(`parse_constant`), og alle numeriske felt sjekkes i tillegg mot et
strengere `_er_reelt_tall()` (avviser bool, NaN, ±inf) som forsvar i
dybden -- en importert fil er utrengt input, ulikt et App-internt
Recipe Object.
"""
import copy

from modules.process_profiles import normaliser_prosessprofil, STANDARDPROFILER

KBHRECIPE_FORMAT = "kbhrecipe"
KBHRECIPE_VERSION = 1

# Egen, lokal konstant -- IKKE modules/recipe_storage.py sin ekvivalent
# (denne modulen har ingen slik fil å dele med i Python, men følger
# samme prinsipp som Web sin KBHRECIPE_STOTTET_RECIPE_SCHEMA_VERSION:
# atskilt fra andre versjonskonstanter, oppdateres bevisst sammen med
# dem hvis/når et nytt recipe-schema noensinne innføres).
KBH_STOTTET_RECIPE_SCHEMA_VERSION = 1

# Strukturelle prosessprofil-felt normaliser_prosessprofil() enten
# erstatter helt (kjent standardprofil) eller bevarer uendret
# (egendefinert) -- se _valider_og_bygg_prosess().
_PROSESS_STRUKTURELLE_FELT = (
    "mash_steps", "sparge_method", "boil_minutes", "decoction_steps", "reiterated_mash",
)

# V1-payloadfelt App AKTIVT forstår/håndterer (native slot, bevisst
# forkastet-med-feilmelding, eller eksplisitt sjekket). Alt ANNET på
# toppnivå havner i passthrough (OPPGAVE I/J) -- se _bygg_passthrough().
_KJENTE_PAYLOAD_FELT = frozenset({
    "recipeSchemaVersion", "navn", "volum", "effektivitet", "malt", "humle",
    "gjaerId", "gjaerCustom", "attenuationOverride", "bryggerStil", "prosess", "vann",
})

# Felt som ALDRI skal havne i passthrough, uansett hva en (evt. hånd-
# redigert/fremmed) fil inneholder under det navnet -- samme
# to-uavhengige-punkter-forsvar som Web sin KBHRECIPE_FORBUDTE_FELT
# (PRI 2A/KBHR-009). `stats`/`flavor_profile` er ALLTID App-beregnet,
# ALDRI kildedata (OPPGAVE I/test 15); `recipeId` er alltid lokal
# lagringsidentitet (KBHR-010) -- ingen av dem skal kunne smugles
# gjennom import som "et ukjent felt appen bare bevarer".
_FORBUDTE_PAYLOAD_FELT = frozenset({"recipeId", "stats", "flavor_profile"})

# ─── Feilmodell (OPPGAVE K) ─────────────────────────────────────────────

KATEGORI_INVALID_JSON = "invalid_json"
KATEGORI_INVALID_ENVELOPE = "invalid_envelope"
KATEGORI_UNSUPPORTED_VERSION = "unsupported_version"
KATEGORI_UNSUPPORTED_RECIPE_SCHEMA = "unsupported_recipe_schema"
KATEGORI_INVALID_PAYLOAD = "invalid_payload"
KATEGORI_UNKNOWN_INGREDIENT_IDS = "unknown_ingredient_ids"
KATEGORI_UNSUPPORTED_CUSTOM_INGREDIENT = "unsupported_custom_ingredient"
KATEGORI_UNSUPPORTED_CALCULATION_OVERRIDE = "unsupported_calculation_override"
KATEGORI_UNSUPPORTED_PROCESS = "unsupported_process"


class UgyldigKbhrecipeForImport(ValueError):
    """
    Kastes når en `.kbhrecipe`-fil ikke kan importeres trygt av dagens
    App. Én klasse, ikke et hierarki (OPPGAVE K) -- `kategori` skiller
    feilårsaken maskinlesbart, `melding` er alltid en menneskelesbar,
    norsk tekst. Ekstra strukturerte detaljer (f.eks. `unknown_malt`)
    kan være satt som vanlige attributter, se
    _valider_kanoniske_ider().
    """

    def __init__(self, kategori, melding, **detaljer):
        super().__init__(melding)
        self.kategori = kategori
        self.melding = melding
        for k, v in detaljer.items():
            setattr(self, k, v)


def _feil(kategori, melding, **detaljer):
    raise UgyldigKbhrecipeForImport(kategori, melding, **detaljer)


# ─── Små, delte valideringshjelpere ────────────────────────────────────

def _er_reelt_tall(v):
    """Strengere enn kbh_contract.py sin `_er_gyldig_tall()` (som ikke
    trenger å sjekke NaN/inf siden den validerer App sin EGEN, allerede
    beregnede data) -- denne validerer UTRENGT fildata og avviser derfor
    eksplisitt bool (en int-subklasse i Python), NaN og ±inf i tillegg."""
    if isinstance(v, bool):
        return False
    if not isinstance(v, (int, float)):
        return False
    if v != v:  # NaN
        return False
    if v in (float("inf"), float("-inf")):
        return False
    return True


def _ikke_tom_streng(v):
    return isinstance(v, str) and v.strip() != ""


def _har_faktisk_dict_innhold(v):
    """True kun for et objekt (dict) med minst én nøkkel -- None, {},
    manglende felt, eller feil type regnes IKKE som "faktisk innhold"."""
    return isinstance(v, dict) and len(v) > 0


def _avvis_json_konstant(navn):
    # json.loads() godtar i Python (i strid med streng JSON/JS) bokstavelige
    # NaN/Infinity/-Infinity-tokens med mindre parse_constant overstyres.
    raise ValueError(f"JSON-konstanten '{navn}' er ikke gyldig i en .kbhrecipe-fil.")


# ─── OPPGAVE B -- envelope-validering ───────────────────────────────────

def _parse_json(tekst):
    import json
    try:
        return json.loads(tekst, parse_constant=_avvis_json_konstant)
    except (ValueError, TypeError) as e:
        _feil(KATEGORI_INVALID_JSON, f"Filen kunne ikke leses som gyldig JSON: {e}")


def _valider_envelope(parsed):
    if not isinstance(parsed, dict):
        _feil(KATEGORI_INVALID_ENVELOPE, "Toppnivået i filen må være et JSON-objekt.")

    if parsed.get("format") != KBHRECIPE_FORMAT:
        # OPPGAVE B -- App-importereren aksepterer IKKE Web sin wrapperløse
        # legacy rå-JSON-fallback (CORE_KBHRECIPE_V1.md §12). Den er
        # dokumentert som en Web-spesifikk, udokumentert-i-selve-V1-teksten
        # bakoverkompatibilitetsvei (`_erGyldigOppskriftForm()` i
        # web/js/kbhrecipe.js) -- kontrakten sier ingen steder at ALLE
        # V1-lesere må gjenskape den, kun at Web gjør det. Se PRI 2C1-
        # rapporten punkt 4 for full begrunnelse.
        _feil(KATEGORI_INVALID_ENVELOPE, "Filen mangler en gyldig .kbhrecipe-konvolutt (format).")

    versjon = parsed.get("version")
    if not _er_reelt_tall(versjon):
        _feil(KATEGORI_UNSUPPORTED_VERSION, "Filen mangler gyldig versjonsinformasjon (version).")
    if versjon != KBHRECIPE_VERSION:
        _feil(
            KATEGORI_UNSUPPORTED_VERSION,
            f"Denne filen bruker .kbhrecipe versjon {versjon!r}, som ikke støttes her (kun versjon 1).",
        )

    recipe = parsed.get("recipe")
    if not isinstance(recipe, dict):
        _feil(KATEGORI_INVALID_ENVELOPE, "Filen mangler selve oppskriften (recipe).")
    return recipe


# ─── OPPGAVE C -- payload-validering (grunnfelt) ────────────────────────

def _valider_recipe_schema_version(payload):
    verdi = payload.get("recipeSchemaVersion")
    if not _er_reelt_tall(verdi):
        _feil(
            KATEGORI_UNSUPPORTED_RECIPE_SCHEMA,
            "Oppskriften mangler gyldig recipeSchemaVersion.",
        )
    if verdi != KBH_STOTTET_RECIPE_SCHEMA_VERSION:
        _feil(
            KATEGORI_UNSUPPORTED_RECIPE_SCHEMA,
            f"Oppskriftens recipeSchemaVersion ({verdi!r}) støttes ikke av denne App-versjonen "
            f"(kun {KBH_STOTTET_RECIPE_SCHEMA_VERSION}).",
        )


def _valider_grunnfelt(payload):
    navn = payload.get("navn")
    if not _ikke_tom_streng(navn):
        _feil(KATEGORI_INVALID_PAYLOAD, "navn mangler eller er tom.")

    volum = payload.get("volum")
    if not _er_reelt_tall(volum) or volum <= 0:
        _feil(KATEGORI_INVALID_PAYLOAD, f"volum har ugyldig verdi: {volum!r}")

    effektivitet = payload.get("effektivitet")
    if not _er_reelt_tall(effektivitet) or effektivitet <= 0:
        _feil(KATEGORI_INVALID_PAYLOAD, f"effektivitet har ugyldig verdi: {effektivitet!r}")

    malt = payload.get("malt")
    if not isinstance(malt, list):
        _feil(KATEGORI_INVALID_PAYLOAD, "malt må være en liste.")

    humle = payload.get("humle")
    if not isinstance(humle, list):
        _feil(KATEGORI_INVALID_PAYLOAD, "humle må være en liste.")

    return navn, volum, effektivitet, malt, humle


# ─── OPPGAVE D -- ingrediensrad-validering ──────────────────────────────

def _valider_og_bygg_malt(malt_rader):
    """Returnerer (rader, ider_aa_sjekke). Kaster umiddelbart ved
    malformert rad eller faktisk custom-innhold (OPPGAVE D) -- custom
    sjekkes FØR raden legges til ID-sjekklisten, siden en custom-rads
    id aldri er ment å være en kanonisk master-ID (se PRI 2C-rapporten,
    Scenario 2)."""
    rader, ider = [], []
    for i, rad in enumerate(malt_rader):
        if not isinstance(rad, dict):
            _feil(KATEGORI_INVALID_PAYLOAD, f"malt[{i}] er ikke et objekt.")
        id_ = rad.get("id")
        if not _ikke_tom_streng(id_):
            _feil(KATEGORI_INVALID_PAYLOAD, f"malt[{i}] mangler gyldig id.")
        if _har_faktisk_dict_innhold(rad.get("custom")):
            _feil(
                KATEGORI_UNSUPPORTED_CUSTOM_INGREDIENT,
                f"malt[{i}] ({id_}) bruker en egendefinert (custom) malt, som ikke støttes "
                "av dagens App-import.",
            )
        mengde = rad.get("mengde")
        if not _er_reelt_tall(mengde) or mengde <= 0:
            _feil(KATEGORI_INVALID_PAYLOAD, f"malt[{i}] ({id_}) har ugyldig mengde: {mengde!r}")
        rader.append({"id": id_, "mengde": mengde})
        ider.append(id_)
    return rader, ider


def _valider_og_bygg_humle(humle_rader):
    rader, ider = [], []
    for i, rad in enumerate(humle_rader):
        if not isinstance(rad, dict):
            _feil(KATEGORI_INVALID_PAYLOAD, f"humle[{i}] er ikke et objekt.")
        id_ = rad.get("id")
        if not _ikke_tom_streng(id_):
            _feil(KATEGORI_INVALID_PAYLOAD, f"humle[{i}] mangler gyldig id.")
        if _har_faktisk_dict_innhold(rad.get("custom")):
            _feil(
                KATEGORI_UNSUPPORTED_CUSTOM_INGREDIENT,
                f"humle[{i}] ({id_}) bruker en egendefinert (custom) humle, som ikke støttes "
                "av dagens App-import.",
            )
        alfa_override = rad.get("alfaOverride")
        if alfa_override is not None:
            if not _er_reelt_tall(alfa_override):
                _feil(KATEGORI_INVALID_PAYLOAD, f"humle[{i}] ({id_}) har ugyldig alfaOverride: {alfa_override!r}")
            _feil(
                KATEGORI_UNSUPPORTED_CALCULATION_OVERRIDE,
                f"humle[{i}] ({id_}) har en aktiv alfaOverride, som ikke støttes av dagens App-import.",
            )
        gram = rad.get("gram")
        tid = rad.get("tid")
        if not _er_reelt_tall(gram) or gram < 0:
            _feil(KATEGORI_INVALID_PAYLOAD, f"humle[{i}] ({id_}) har ugyldig gram: {gram!r}")
        if not _er_reelt_tall(tid) or tid < 0:
            _feil(KATEGORI_INVALID_PAYLOAD, f"humle[{i}] ({id_}) har ugyldig tid: {tid!r}")
        rader.append({"id": id_, "gram": gram, "tid": tid})
        ider.append(id_)
    return rader, ider


# ─── OPPGAVE E -- gjær-validering ────────────────────────────────────────

def _valider_og_bygg_gjaer(payload):
    """Returnerer (yeast_id_eller_None, ider_aa_sjekke). Kaster ved
    faktisk gjaerCustom/attenuationOverride-innhold (OPPGAVE E/KBHR-017).
    Manglende gjaerId betyr "ikke oppgitt" -- ALDRI gjettet til et
    default (f.eks. safale_us_05)."""
    if _har_faktisk_dict_innhold(payload.get("gjaerCustom")):
        _feil(
            KATEGORI_UNSUPPORTED_CALCULATION_OVERRIDE,
            "Oppskriften bruker en egendefinert (custom) gjær (gjaerCustom), som ikke "
            "støttes av dagens App-import.",
        )
    elif payload.get("gjaerCustom") is not None and not isinstance(payload.get("gjaerCustom"), dict):
        _feil(KATEGORI_INVALID_PAYLOAD, f"gjaerCustom har ugyldig type: {payload.get('gjaerCustom')!r}")

    attenuation_override = payload.get("attenuationOverride")
    if attenuation_override is not None:
        if not _er_reelt_tall(attenuation_override):
            _feil(KATEGORI_INVALID_PAYLOAD, f"attenuationOverride har ugyldig verdi: {attenuation_override!r}")
        _feil(
            KATEGORI_UNSUPPORTED_CALCULATION_OVERRIDE,
            "Oppskriften har en aktiv attenuationOverride, som ikke støttes av dagens App-import.",
        )

    gjaer_id = payload.get("gjaerId")
    if gjaer_id is None:
        return None, []
    if not _ikke_tom_streng(gjaer_id):
        _feil(KATEGORI_INVALID_PAYLOAD, f"gjaerId har ugyldig verdi: {gjaer_id!r}")
    return gjaer_id, [gjaer_id]


# ─── OPPGAVE F -- kanonisk ID-validering (samlet) ───────────────────────

def _valider_kanoniske_ider(malt_ider, humle_ider, gjaer_ider, malt_db, humle_db, gjaer_db):
    ukjent_malt = [i for i in malt_ider if i not in (malt_db or {})]
    ukjent_humle = [i for i in humle_ider if i not in (humle_db or {})]
    ukjent_gjaer = [i for i in gjaer_ider if i not in (gjaer_db or {})]

    if not (ukjent_malt or ukjent_humle or ukjent_gjaer):
        return

    linjer = ["Oppskriften refererer til ID-er som ikke finnes i dagens masterdata:"]
    if ukjent_malt:
        linjer.append(f"unknown malt: {ukjent_malt}")
    if ukjent_humle:
        linjer.append(f"unknown hops: {ukjent_humle}")
    if ukjent_gjaer:
        linjer.append(f"unknown yeast: {ukjent_gjaer}")
    _feil(
        KATEGORI_UNKNOWN_INGREDIENT_IDS,
        "\n".join(linjer),
        unknown_malt=ukjent_malt, unknown_hops=ukjent_humle, unknown_yeast=ukjent_gjaer,
    )


# ─── OPPGAVE G -- prosess-sikkerhet ──────────────────────────────────────

def _valider_og_bygg_prosess(prosess_raw):
    """
    KBHR-018/020 + PR #3 Chief review, CORRECTED owner decision (option
    B, 2026-09-02): an earlier round of this PR briefly implemented
    option A (losslessly converting a divergent known process to
    "egendefinert" -- see git history, commit `ce4ab4c`, now reverted).
    The owner's actual decision was **B**: keep strict rejection.
    `.kbhrecipe` process-profile import compatibility is DELIBERATELY
    safe-subset-only for now -- a known standard `process_id` whose
    structural data diverges from today's canonical App profile is
    REJECTED, not converted or normalized. A dedicated, separately
    scoped compatibility task may revisit this later (see
    CORE_KBHRECIPE_V1.md §13). Reverting A also closed a real technical
    gap A had: `_bygg_egendefinert_fra_avvikende_standard()`'s
    conversion was not wire-lossless on re-export (App's writer has no
    passthrough slot for the original `process_id`/payload, so an
    import -> re-export roundtrip could not reproduce the original
    process representation) -- a correct A would need a separately
    designed raw/opaque preservation mechanism, out of scope here.

    `prosess` importeres KUN dersom App kan representere den UTEN at
    normaliser_prosessprofil() endrer semantikken STILLE -- ALDRI en
    stille fallback til enkel_infusjon for en ukjent process_id, og
    ALDRI en stille erstatning av avvikende meskesteg med en kanonisk
    standardprofils egne steg.

      - Mangler `prosess` -> None (helt lovlig, se modules/recipe.py).
      - process_id == "egendefinert" -> normaliser_prosessprofil()
        deep-copier UBETINGET (se modules/process_profiles.py) -- ALDRI
        tap av semantikk mulig for denne grenen, alltid trygt å
        importere.
      - process_id er en KJENT standardprofil (i STANDARDPROFILER) ->
        normaliser_prosessprofil() erstatter ALLE strukturelle felt
        (mash_steps/sparge_method/boil_minutes/decoction_steps/
        reiterated_mash) med sin egen kanoniske versjon, uansett hva
        payloaden sa. Importen er derfor kun lovlig hvis payloadens
        egne strukturelle felt er IDENTISKE med den kanoniske profilen
        -- avviker de (custom meskesteg under et kjent process_id),
        ville import stille kastet brukerens faktiske data.
      - Ukjent process_id (verken "egendefinert" eller i
        STANDARDPROFILER) -> normaliser_prosessprofil() ville falt
        tilbake til "enkel_infusjon" STILLE. Import avviser dette
        eksplisitt i stedet.
    """
    if prosess_raw is None:
        return None
    if not isinstance(prosess_raw, dict):
        _feil(KATEGORI_INVALID_PAYLOAD, f"prosess har ugyldig type: {prosess_raw!r}")

    process_id = prosess_raw.get("process_id")

    if process_id == "egendefinert":
        return copy.deepcopy(prosess_raw)

    if process_id not in STANDARDPROFILER:
        _feil(
            KATEGORI_UNSUPPORTED_PROCESS,
            f"Oppskriften bruker en ukjent prosessprofil (process_id={process_id!r}), som "
            "ikke støttes av dagens App-import (unngår stille fallback til enkel infusjon).",
        )

    kanonisk = normaliser_prosessprofil(prosess_raw)
    for felt in _PROSESS_STRUKTURELLE_FELT:
        if prosess_raw.get(felt) != kanonisk.get(felt):
            _feil(
                KATEGORI_UNSUPPORTED_PROCESS,
                f"Oppskriftens prosessprofil ({process_id}) har avvikende {felt} som ikke "
                "samsvarer med Appens kanoniske standardprofil, og ville blitt stille "
                "erstattet -- dagens App-import støtter derfor ikke denne filen (owner "
                "decision B, PR #3: import av .kbhrecipe-prosessdata er bevisst "
                "safe-subset-only inntil videre).",
            )
    return kanonisk


# ─── OPPGAVE H -- vann ────────────────────────────────────────────────

def _bygg_vann(vann_raw):
    if vann_raw is None:
        return None, None, None, None
    if not isinstance(vann_raw, dict):
        _feil(KATEGORI_INVALID_PAYLOAD, f"vann har ugyldig type: {vann_raw!r}")
    return (
        copy.deepcopy(vann_raw.get("kilde")) if vann_raw.get("kilde") is not None else None,
        copy.deepcopy(vann_raw.get("maal")) if vann_raw.get("maal") is not None else None,
        copy.deepcopy(vann_raw.get("behandling")) if vann_raw.get("behandling") is not None else None,
        copy.deepcopy(vann_raw.get("maalinger")) if vann_raw.get("maalinger") is not None else None,
    )


# ─── OPPGAVE I/J -- passthrough for ikke-beregningspåvirkende metadata ──

def _bygg_passthrough(payload):
    """
    Web-only metadata (brygger/bryggeri/notater/valgtStil, KBHR-014) og
    ethvert ukjent fremtidig toppnivåfelt (OPPGAVE J) bevares opakt her
    -- App-intern metadata, IKKE et Core V1-felt i seg selv (samme
    prinsipp som Web sin _kbhUkjenteFelt, PRI 2A/KBHR-002). Feltnavn som
    ALLEREDE ble avvist (custom-ingredienser, alfaOverride, gjaerCustom,
    attenuationOverride) kan ALDRI havne her -- de kastet en
    UgyldigKbhrecipeForImport lenge før denne funksjonen kalles i det
    hele tatt (OPPGAVE J: "ikke legg kjente unsupported calculation
    fields der for å omgå reject-policy").

    KBHR-015: bryggerStil og valgtStil er IKKE samme semantikk -- ingen
    mapping. bryggerStil har en native App-slot (brygger_stil,
    OPPGAVE I); valgtStil har INGEN native App-slot (App beregner sin
    egen stilmatch, se modules/style_engine.py) og havner derfor her,
    uendret, sammen med brygger/bryggeri/notater.

    Forbudte feltnavn (_FORBUDTE_PAYLOAD_FELT) filtreres bort HER i
    tillegg -- et uavhengig andre vern, i tilfelle en fremmed/hånd-
    redigert fil skulle inneholde f.eks. en bokstavelig `stats`-nøkkel
    på toppnivå.
    """
    ukjente = {
        nokkel: verdi for nokkel, verdi in payload.items()
        if nokkel not in _KJENTE_PAYLOAD_FELT and nokkel not in _FORBUDTE_PAYLOAD_FELT
    }
    return copy.deepcopy(ukjente)


# ─── Offentlig API ────────────────────────────────────────────────────

def parse_kbhrecipe_json(tekst, malt_db=None, humle_db=None, gjaer_db=None):
    """
    Parser og validerer en `.kbhrecipe` V1-fils tekstinnhold, og bygger
    App-native recipe-data (reverse adapter av
    modules/kbh_contract.py::recipe_to_kbhrecipe_payload()).

    Returnerer:
        {
          "recipe": {
              "name", "batch_size", "efficiency", "brygger_stil",
              "malts", "hops", "yeast",
              "process_profile",
              "water_source_profile", "water_target_profile",
              "water_treatment", "water_measurements",
          },
          "passthrough": {...},   # se _bygg_passthrough() -- kan være {}
        }

    `recipe` inneholder BEVISST IKKE `stats`/`flavor_profile` (OPPGAVE I)
    -- disse beregnes av App, aldri importert som om de var kildedata.
    `recipe` inneholder heller ingen lokal identitet (recipeId) --
    import er "import as new" (KBHR-010), håndtert av kalleren (PRI 2C2).

    Kaster UgyldigKbhrecipeForImport (se kategoriene øverst i denne
    filen) ved ethvert valideringsbrudd -- ALDRI en fallback-/gjettet
    verdi, ALDRI fuzzy-matching, ALDRI en delvis importert oppskrift.
    """
    parsed = _parse_json(tekst)
    payload = _valider_envelope(parsed)
    _valider_recipe_schema_version(payload)
    navn, volum, effektivitet, malt_raw, humle_raw = _valider_grunnfelt(payload)

    malt_rader, malt_ider = _valider_og_bygg_malt(malt_raw)
    humle_rader, humle_ider = _valider_og_bygg_humle(humle_raw)
    gjaer_id, gjaer_ider = _valider_og_bygg_gjaer(payload)

    # OPPGAVE F -- samlet, ETT sted, ETTER at custom-/override-avvisning
    # allerede har passert: en custom-rads id skal ALDRI rapporteres som
    # "unknown" (den var aldri ment å være en kanonisk master-ID).
    _valider_kanoniske_ider(malt_ider, humle_ider, gjaer_ider, malt_db, humle_db, gjaer_db)

    prosess = _valider_og_bygg_prosess(payload.get("prosess"))
    kilde, maal, behandling, maalinger = _bygg_vann(payload.get("vann"))

    bryggerstil = payload.get("bryggerStil")
    if bryggerstil is not None and not isinstance(bryggerstil, str):
        _feil(KATEGORI_INVALID_PAYLOAD, f"bryggerStil har ugyldig type: {bryggerstil!r}")

    native = {
        "name": navn,
        "batch_size": volum,
        # KBHR-019 -- V1 lagrer effektivitet som prosent (68); App-native
        # er en fraksjon (0.68). Konverteres KUN her, etter validering.
        "efficiency": effektivitet / 100.0,
        "brygger_stil": bryggerstil or "",
        "malts": malt_rader,
        "hops": humle_rader,
        "yeast": gjaer_id,
        "process_profile": prosess,
        "water_source_profile": kilde,
        "water_target_profile": maal,
        "water_treatment": behandling,
        "water_measurements": maalinger,
    }
    return {"recipe": native, "passthrough": _bygg_passthrough(payload)}
