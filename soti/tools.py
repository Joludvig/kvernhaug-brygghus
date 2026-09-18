"""
Sóti -- verktøygrensesnitt. En provider kan aldri kjøre vilkårlig kode:
den kan kun be SotiRuntime om å utføre ett av verktøyene eksplisitt
registrert i et ToolRegistry, og et ukjent verktøynavn er en feil, ikke en
stille no-op (se ToolRegistry.utfoer) -- runtime godkjenner alltid
handlingen, providersvaret kan aldri "oppfinne" en ny en.

Denne pakken registrerer to skrivebeskyttede verktøy:

1. `hent_ingrediens_info` -- oppslag mot Core sine kanoniske
   masterdatafiler, adressert via core/manifest.json
   (docs/development/KBH_CORE_CONTRACT.md §1: Core eier kanonisk
   masterdata, stabile ID-er og scheman) og lest med
   modules/master_data_io.py -- samme leseren App/Web-koden selv bruker.
2. `hent_verifisert_fagfakta` (V2-5C1, issue #317) -- oppslag mot
   Bryggeskolens Course Fact Registry, utelukkende via den betrodde
   verifiserte-only API-en i bryggeskole/course_fact_registry.py
   (`get_verified_record`/`find_verified_records`). Dette verktøyet
   leser ALDRI den rå registerfilen direkte og kaller ALDRI
   `read_registry_file()`/`validate_registry()` -- draft/reviewed/
   deprecated poster kan derfor aldri lekke gjennom dette verktøyet,
   uansett argumentkombinasjon. En ugyldig registerfil feiler synlig
   (CourseFactRegistryError forplanter seg til runtime-grensen) i
   stedet for å falle tilbake til rådata eller et oppdiktet svar.

Sóti dupliserer aldri denne dataen inn i et prompt (se soti.identity);
den slår den opp på nytt, skrivebeskyttet, for hver henvendelse.
"""
import json
import os
from dataclasses import dataclass
from typing import Callable

from bryggeskole.course_fact_registry import find_verified_records, get_verified_record, read_verified_records
from modules.master_data_io import les_master_json

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MANIFEST_PATH = os.path.join(_REPO_ROOT, "core", "manifest.json")
_COURSE_FACT_REGISTRY_PATH = os.path.join(_REPO_ROOT, "bryggeskole", "data", "course_fact_registry.json")

# Bevisst lite, eksplisitt whitelistet feltutvalg for verifisert fagfakta --
# beholder alltid stabil ID, påstand, klassifisering, verifiseringstidspunkt
# og kilder/proveniens (aldri strippet), pluss konsept-/modultilknytning der
# de finnes. Aldri 'status' (alltid 'verified' gjennom dette verktøyet uansett)
# og aldri 'notes' (redaksjonelt, ikke del av den trygge fagfakta-kontrakten).
_FAGFAKTA_FELT = ("id", "claim", "classification", "verified_at", "sources", "concepts", "modules")

# Bevisst lite, eksplisitt whitelistet feltutvalg -- aldri hele
# master-oppføringen (som blant annet inneholder butikk_match/pris-data,
# utenfor det Sóti trenger å eksponere til en bruker).
_TILLATTE_FELT = (
    "display_name", "produsent", "kategori", "type", "opprinnelse",
    "gjaertype", "smakstags", "ebc", "potensiale", "maks_prosent",
    "alfa_typisk", "attenuation", "anbefalte_stiler", "aliases",
)


@dataclass(frozen=True)
class Tool:
    navn: str
    beskrivelse: str
    handler: Callable[[dict], dict]


class ToolRegistry:
    """Konstruert-innhold registry: kun verktøy eksplisitt lagt til med
    registrer() kan kalles via utfoer()."""

    def __init__(self):
        self._verktoy = {}

    def registrer(self, tool):
        self._verktoy[tool.navn] = tool

    def __contains__(self, navn):
        return navn in self._verktoy

    def alle(self):
        return list(self._verktoy.values())

    def utfoer(self, navn, argumenter):
        if navn not in self._verktoy:
            raise KeyError(f"Ukjent verktøy: {navn!r} -- kun registrerte verktøy kan kalles")
        return self._verktoy[navn].handler(argumenter or {})


def _last_core_manifest():
    with open(_MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _finn_i_datasett(datasett, sok):
    sok_lav = sok.strip().lower()
    if not sok_lav:
        return None
    if sok in datasett:  # eksakt ID-treff
        return sok, datasett[sok]
    for ingrediens_id, oppslag in datasett.items():
        navn = str(oppslag.get("display_name", "")).lower()
        aliaser = [str(a).lower() for a in oppslag.get("aliases", [])]
        if sok_lav == ingrediens_id.lower() or sok_lav == navn or sok_lav in aliaser:
            return ingrediens_id, oppslag
    return None


def hent_ingrediens_info(argumenter):
    """Skrivebeskyttet Core-oppslag.

    argumenter: {"datasett": "malt"|"humle"|"gjaer", "sok": "<id, navn eller alias>"}.
    Returnerer {"funnet": False, "feil": ...} for et ukjent datasett eller
    et manglende treff, ellers {"funnet": True, "id": ..., "datasett": ...,
    "felt": {...whitelistede felt...}}. Skriver aldri til noen fil.
    """
    datasett_navn = str((argumenter or {}).get("datasett", "")).strip().lower()
    sok = str((argumenter or {}).get("sok", ""))
    manifest = _last_core_manifest()
    datasett_info = manifest.get("datasets", {}).get(datasett_navn)
    if datasett_info is None:
        return {"funnet": False, "feil": f"Ukjent Core-datasett: {datasett_navn!r}"}
    kildesti = os.path.join(_REPO_ROOT, datasett_info["source_path"])
    datasett = les_master_json(kildesti)
    treff = _finn_i_datasett(datasett, sok)
    if treff is None:
        return {"funnet": False, "feil": f"Fant ingen {datasett_navn}-oppføring for {sok!r}"}
    ingrediens_id, oppslag = treff
    return {
        "funnet": True,
        "id": ingrediens_id,
        "datasett": datasett_navn,
        "felt": {felt: oppslag[felt] for felt in _TILLATTE_FELT if felt in oppslag},
    }


def _fagfakta_til_felt(record):
    return {felt: record[felt] for felt in _FAGFAKTA_FELT if felt in record}


def hent_verifisert_fagfakta(argumenter):
    """Skrivebeskyttet oppslag mot den betrodde, verifiserte-only Course
    Fact Registry-API-en (bryggeskole.course_fact_registry) -- returnerer
    utelukkende status='verified'-poster, aldri draft/reviewed/deprecated,
    og leser aldri den rå registerfilen selv.

    argumenter: {"id": "<FACT-DOMENE-####>"} for eksakt, deterministisk
    ID-oppslag, ELLER {"concept": "<konsept>", "module": "<modul>"} (én
    eller begge) for et bundet, deterministisk filteroppslag -- ingen
    fritekst-/semantisk søk, ingen embeddings, ingen RAG. Et argument-
    objekt UTEN noen av de tre (tomt, eller kun ukjente nøkler) gjør ALDRI
    oppslag i registeret og "lister ikke alt" -- det gir et bundet
    ikke-funnet-svar direkte (se Chief-korreksjon PR #320, issue #317):
    et gjettet/feilformet verktøykall fra modellen for et spørsmål
    utenfor registeret skal aldri kunne returnere urelaterte verifiserte
    fakta i stedet for den påkrevde "ingen verifisert treff"-stien.

    Returnerer {"funnet": False, "feil": ...} hvis ingen verifisert post
    matcher (en ukjent ID og en ID som finnes men ikke er verifisert er
    med hensikt umulige å skille fra hverandre her -- se den betrodde
    API-ens egen dokumentasjon), ellers {"funnet": True, "fakta": [...]}
    med én eller flere poster, hver med stabil ID, påstand, klassifisering,
    verifiseringstidspunkt og kilder/proveniens intakt. En ugyldig
    registerfil forplanter CourseFactRegistryError uendret -- feiler
    synlig i stedet for å falle tilbake til rådata eller hukommelse --
    men KUN når et faktisk oppslag skjer; et argumentobjekt uten
    anerkjent selector rører aldri registerfilen."""
    args = argumenter or {}
    fact_id = args.get("id")
    concept = args.get("concept")
    module = args.get("module")

    if not (fact_id or concept or module):
        return {
            "funnet": False,
            "feil": (
                "Ingen anerkjent søkeparameter oppgitt -- oppgi 'id', "
                "eller 'concept'/'module' (én eller begge)."
            ),
        }

    if fact_id:
        record = get_verified_record(_COURSE_FACT_REGISTRY_PATH, str(fact_id))
        records = [record] if record is not None else []
    else:
        records = find_verified_records(_COURSE_FACT_REGISTRY_PATH, concept=concept, module=module)

    if not records:
        return {"funnet": False, "feil": "Ingen verifisert fagfakta matcher søket."}
    return {"funnet": True, "fakta": [_fagfakta_til_felt(record) for record in records]}


def hent_verifiserte_konsepter_og_moduler():
    """Henter de faktiske, unike concept-/module-verdiene som forekommer
    på de VERIFISERTE postene akkurat nå -- utelukkende via den betrodde
    `read_verified_records()`-API-en, aldri rå/uverifiserte poster. Brukes
    til å bygge et selvoppdaterende verktøyskjema for
    `hent_verifisert_fagfakta` (se `hent_verifisert_fagfakta_skjema()`
    under) i stedet for en hardkodet vokabularliste som stille kan gå ut
    av synk med registeret (Chief-korreksjon runde 2, PR #320, issue
    #317). Returnerer (konsepter, moduler) som to sorterte lister --
    aldri None. Kaster CourseFactRegistryError uendret for et ugyldig
    register, uten noen fallback."""
    poster = read_verified_records(_COURSE_FACT_REGISTRY_PATH)
    konsepter = sorted({konsept for post in poster for konsept in (post.get("concepts") or [])})
    moduler = sorted({modul for post in poster for modul in (post.get("modules") or [])})
    return konsepter, moduler


def hent_verifisert_fagfakta_skjema():
    """Bygger et ferskt JSON-skjema for `hent_verifisert_fagfakta` sine
    argumenter, med 'enum' på 'concept'/'module' satt til dagens faktiske
    verifiserte vokabular (se `hent_verifiserte_konsepter_og_moduler()`
    over). Kalt på nytt av soti.ollama_provider for hvert providerkall --
    aldri en frosset kopi tatt ved oppstart -- slik at modellen alltid ser
    de faktiske gyldige selector-verdiene FØR den velger argumenter, i
    stedet for å gjette et bundet, men ikke-eksisterende, filter. Ingen
    'enum' legges til for et felt uten noen kjente verdier (et tomt
    register/tomt vokabular gir det uendrede åpne strengfeltet)."""
    konsepter, moduler = hent_verifiserte_konsepter_og_moduler()
    skjema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "concept": {"type": "string"},
            "module": {"type": "string"},
        },
    }
    if konsepter:
        skjema["properties"]["concept"]["enum"] = konsepter
    if moduler:
        skjema["properties"]["module"]["enum"] = moduler
    return skjema


def bygg_standard_registry():
    """Registry med Sóti sine skrivebeskyttede standardverktøy: Core-
    oppslaget og det verifiserte fagfakta-oppslaget over. Hvilke av disse
    en gitt henvendelse faktisk får tilgang til, styres av skillen (se
    soti.skills.registry_for_skill) -- ikke av dette registryet alene."""
    registry = ToolRegistry()
    registry.registrer(Tool(
        navn="hent_ingrediens_info",
        beskrivelse=(
            "Skrivebeskyttet oppslag i Core sine kanoniske masterdatafiler "
            "(malt/humle/gjær) via core/manifest.json. Argumenter: "
            "{datasett: 'malt'|'humle'|'gjaer', sok: id/navn/alias}."
        ),
        handler=hent_ingrediens_info,
    ))
    registry.registrer(Tool(
        navn="hent_verifisert_fagfakta",
        beskrivelse=(
            "Skrivebeskyttet oppslag i den verifiserte Course Fact Registry-"
            "API-en (bryggeskole.course_fact_registry) -- returnerer kun "
            "status='verified'-poster, aldri draft/reviewed/deprecated, og "
            "aldri rå registerdata. Argumenter: {id: '<FACT-...>'} for "
            "eksakt oppslag, eller {concept: ..., module: ...} (én eller "
            "begge) for et bundet filteroppslag. Ingen fritekst-/semantisk "
            "søk. Minst én av id/concept/module må oppgis -- uten noen av "
            "dem gis et bundet 'ingen treff'-svar, aldri en full liste. "
            "Gyldige verdier for 'concept'/'module' er akkurat nå listet "
            "som 'enum' i dette verktøyets eget JSON-skjema (aldri "
            "hardkodet her -- avledet på nytt fra registeret for hvert "
            "kall) -- velg alltid en av dem, gjett aldri en verdi som "
            "ikke er listet der."
        ),
        handler=hent_verifisert_fagfakta,
    ))
    return registry
