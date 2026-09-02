# modules/kbh_contract.py
"""
Oversetter Streamlit sitt interne Recipe Object (modules/recipe.py::
bygg_recipe_object) til en KBH Core Recipe Payload V1, slik denne er
definert i docs/development/KBH_CORE_CONTRACT_V1.md §3–§11 (den
operative legacy .kbhrecipe-kontrakten; docs/development/
KBH_CORE_CONTRACT.md er dagens aktive, styrende Core Contract for
øvrig — se dens Section 3 for status på §3–§11).

Ren modul: ingen filsystem-tilgang, ingen Streamlit-avhengighet, ingen
sideeffekter (jf. .claude/rules/desktop.md — testbar uten Streamlit-
kontekst). Ansvaret er BEGRENSET til oversettelse: dette er ikke
recipe_storage.py (som eier disk-I/O for det interne formatet). Selve
.kbhrecipe-konvolutten ({format, version, exportedAt, generator,
recipe}) bygges av bygg_kbhrecipe_konvolutt() — også den uten
sideeffekter; eksporttidspunktet sendes inn av kalleren i stedet for
at modulen selv leser systemklokken.

Payloaden bygges felt for felt (KBH_CORE_CONTRACT_V1.md §4 — hvitelisten):
`stats` og `flavor_profile` blir aldri lest ut av `recipe` og finnes
derfor aldri i output, uansett hva `recipe` for øvrig inneholder.
"""
import copy

_TALLTYPER = (int, float)

KBHRECIPE_FORMAT = "kbhrecipe"
KBHRECIPE_VERSION = 1
_GENERATOR = "Kvernhaug Brygghus (Streamlit)"

# ─── PRI 2C2 -- re-eksport av bevart passthrough-metadata ───────────────
# Speiler (bevisst en egen, lokal kopi -- samme mønster som
# modules/kbh_import.py sin egen _KJENTE_PAYLOAD_FELT) hvilke V1-felt
# App AKTIVT bygger selv i denne modulen. Enhver nøkkel i denne listen
# skal ALDRI kunne overskrives av en (potensielt utdatert) passthrough-
# verdi -- selv om feltet ikke faktisk ble skrevet inn i `payload` DENNE
# runden (f.eks. `gjaerId` når ingen gjær er valgt), siden feltnavnet
# fortsatt betyr "dette er noe App selv eier/tolker".
_KJENTE_PAYLOAD_FELT = frozenset({
    "recipeSchemaVersion", "navn", "volum", "effektivitet", "malt", "humle",
    "gjaerId", "gjaerCustom", "attenuationOverride", "bryggerStil", "prosess", "vann",
})

# Felt som ALDRI skal kunne re-eksporteres via passthrough, uansett hva en
# (evt. hånd-redigert/korrupt) `_kbh_passthrough`-dict inneholder under det
# navnet -- samme to-uavhengige-punkter-forsvar som
# modules/kbh_import.py sin _FORBUDTE_PAYLOAD_FELT (PRI 2A/KBHR-009):
# `recipeId`/`stats`/`flavor_profile` er aldri kildedata, og containeren
# `_kbh_passthrough` selv skal aldri kunne bli et V1-felt i seg selv.
_FORBUDT_I_PASSTHROUGH_VED_REEKSPORT = frozenset({"recipeId", "stats", "flavor_profile", "_kbh_passthrough"})


def _flett_inn_passthrough(payload, passthrough):
    """
    Fletter `_kbh_passthrough`-innholdet inn i en allerede FERDIGBYGD
    `payload` -- bevisst IKKE `payload.update(passthrough)`: hver nøkkel
    sjekkes eksplisitt mot både det kjente feltnavnerommet og den
    forbudte listen FØR den får lov til å skrives, og en nøkkel som av en
    eller annen grunn allerede finnes i `payload` (skal i praksis aldri
    skje for et kjent felt, siden passthrough per definisjon kun skal
    inneholde felt App ikke selv eier -- se modules/kbh_import.py sin
    _bygg_passthrough()) beholder ALLTID payloadens egen, ferske verdi.
    Muterer og returnerer `payload` i-place (kalt helt til slutt i
    recipe_to_kbhrecipe_payload(), etter at alle kjente felt allerede er
    satt).
    """
    if not isinstance(passthrough, dict) or not passthrough:
        return payload
    for nokkel, verdi in passthrough.items():
        if nokkel in _KJENTE_PAYLOAD_FELT or nokkel in _FORBUDT_I_PASSTHROUGH_VED_REEKSPORT:
            continue
        if nokkel in payload:
            continue
        payload[nokkel] = copy.deepcopy(verdi)
    return payload


class UgyldigOppskriftForEksport(ValueError):
    """
    Kastes når et Recipe Object ikke kan oversettes til en gyldig KBH
    Core Recipe Payload. KBH_CORE_CONTRACT_V1.md §9: data som ikke kan
    forstås skal markeres som feil, aldri gjettes eller fylles med
    fallback-verdier.
    """


def _er_gyldig_tall(verdi):
    return isinstance(verdi, _TALLTYPER) and not isinstance(verdi, bool)


def _valider_malt(malts):
    if not isinstance(malts, list):
        raise UgyldigOppskriftForEksport("malts må være en liste.")
    for i, rad in enumerate(malts):
        if not isinstance(rad, dict) or not rad.get("id"):
            raise UgyldigOppskriftForEksport(f"malts[{i}] mangler gyldig id.")
        mengde = rad.get("mengde")
        if not _er_gyldig_tall(mengde) or mengde <= 0:
            raise UgyldigOppskriftForEksport(
                f"malts[{i}] ({rad.get('id')}) har ugyldig mengde: {mengde!r}"
            )


def _valider_humle(hops):
    if not isinstance(hops, list):
        raise UgyldigOppskriftForEksport("hops må være en liste.")
    for i, rad in enumerate(hops):
        if not isinstance(rad, dict) or not rad.get("id"):
            raise UgyldigOppskriftForEksport(f"hops[{i}] mangler gyldig id.")
        gram = rad.get("gram")
        tid = rad.get("tid")
        if not _er_gyldig_tall(gram) or gram < 0:
            raise UgyldigOppskriftForEksport(
                f"hops[{i}] ({rad.get('id')}) har ugyldig gram: {gram!r}"
            )
        if not _er_gyldig_tall(tid) or tid < 0:
            raise UgyldigOppskriftForEksport(
                f"hops[{i}] ({rad.get('id')}) har ugyldig tid: {tid!r}"
            )


def _bygg_malt_rader(malts):
    return [{"id": rad["id"], "mengde": rad["mengde"]} for rad in malts]


def _bygg_humle_rader(hops):
    return [{"id": rad["id"], "gram": rad["gram"], "tid": rad["tid"]} for rad in hops]


def _bygg_vann_blokk(recipe):
    """
    Slår sammen de fire water_*-feltene (modules/water_chemistry.py) til
    én `vann`-blokk (KBH_CORE_CONTRACT_V1.md §3: kilde/maal/behandling/
    maalinger). Returnerer None hvis ingen av de fire er satt, slik at
    en oppskrift uten vannkjemi gir en payload helt uten `vann`-nøkkel
    — ikke en nøkkel med tomme/null-verdier.
    """
    felter = {
        "kilde": recipe.get("water_source_profile"),
        "maal": recipe.get("water_target_profile"),
        "behandling": recipe.get("water_treatment"),
        "maalinger": recipe.get("water_measurements"),
    }
    if all(verdi is None for verdi in felter.values()):
        return None
    return {navn: copy.deepcopy(verdi) for navn, verdi in felter.items() if verdi is not None}


def recipe_to_kbhrecipe_payload(recipe):
    """
    Oversetter et Streamlit Recipe Object til en KBH Core Recipe
    Payload V1 (docs/development/KBH_CORE_CONTRACT_V1.md §3).

    Ren funksjon: leser kun `recipe`, skriver ingenting til disk,
    viser ingen UI, har ingen sideeffekter. Kaster
    UgyldigOppskriftForEksport ved ugyldige data — ingen fuzzy-
    matching, ingen fallback-data, ingen automatisk gjetting (§9).

    Feltoversettelse (§3/§5):
        name              -> navn
        batch_size        -> volum
        efficiency (0.75) -> effektivitet (75)   [× 100, §5]
        malts             -> malt
        hops              -> humle
        yeast             -> gjaerId
        brygger_stil      -> bryggerStil
        process_profile   -> prosess
        water_*           -> vann.{kilde, maal, behandling, maalinger}

    `stats` og `flavor_profile` leses aldri ut av `recipe` og finnes
    derfor aldri i returverdien (§4).

    PRI 2C2 -- `recipe["_kbh_passthrough"]` (se modules/recipe.py sin
    `kbh_passthrough`-parameter), hvis satt, flettes til slutt inn i den
    allerede ferdigbygde payloaden som ukjente V1-toppnivåfelt (se
    _flett_inn_passthrough()) -- ALDRI kritisk for kjente Core-felt (de
    er allerede satt over, og vinner alltid), og ALDRI for
    recipeId/stats/flavor_profile/containeren selv (se
    _FORBUDT_I_PASSTHROUGH_VED_REEKSPORT).
    """
    if not isinstance(recipe, dict):
        raise UgyldigOppskriftForEksport("recipe må være et objekt (dict).")

    efficiency = recipe.get("efficiency")
    if not _er_gyldig_tall(efficiency) or efficiency <= 0:
        raise UgyldigOppskriftForEksport(f"efficiency har ugyldig verdi: {efficiency!r}")

    volum = recipe.get("batch_size")
    if not _er_gyldig_tall(volum) or volum <= 0:
        raise UgyldigOppskriftForEksport(f"batch_size har ugyldig verdi: {volum!r}")

    malts = recipe.get("malts")
    hops = recipe.get("hops")
    _valider_malt(malts)
    _valider_humle(hops)

    payload = {
        "recipeSchemaVersion": 1,
        "navn": recipe.get("name") or "Navnløs Brygg",
        "volum": volum,
        "effektivitet": round(efficiency * 100, 4),
        "malt": _bygg_malt_rader(malts),
        "humle": _bygg_humle_rader(hops),
    }

    yeast = recipe.get("yeast")
    if yeast:
        payload["gjaerId"] = yeast

    brygger_stil = recipe.get("brygger_stil")
    if brygger_stil:
        payload["bryggerStil"] = brygger_stil

    process_profile = recipe.get("process_profile")
    if process_profile is not None:
        payload["prosess"] = copy.deepcopy(process_profile)

    vann = _bygg_vann_blokk(recipe)
    if vann is not None:
        payload["vann"] = vann

    _flett_inn_passthrough(payload, recipe.get("_kbh_passthrough"))

    return payload


def bygg_kbhrecipe_konvolutt(recipe, generert_tidspunkt):
    """
    Bygger en komplett .kbhrecipe-konvolutt (KBH_CORE_CONTRACT_V1.md §3):
        {format, version, exportedAt, generator, recipe}

    `generert_tidspunkt` sendes inn eksplisitt (ISO 8601-streng) i
    stedet for at funksjonen selv leser systemklokken — det holder
    funksjonen ren og deterministisk/testbar. Kalleren (UI-laget) er
    ansvarlig for å hente faktisk eksporttidspunkt.

    Kaster UgyldigOppskriftForEksport hvis `recipe` ikke lar seg
    oversette (se recipe_to_kbhrecipe_payload).
    """
    payload = recipe_to_kbhrecipe_payload(recipe)
    return {
        "format": KBHRECIPE_FORMAT,
        "version": KBHRECIPE_VERSION,
        "exportedAt": generert_tidspunkt,
        "generator": _GENERATOR,
        "recipe": payload,
    }
