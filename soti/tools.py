"""
Sóti -- verktøygrensesnitt. En provider kan aldri kjøre vilkårlig kode:
den kan kun be SotiRuntime om å utføre ett av verktøyene eksplisitt
registrert i et ToolRegistry, og et ukjent verktøynavn er en feil, ikke en
stille no-op (se ToolRegistry.utfoer) -- runtime godkjenner alltid
handlingen, providersvaret kan aldri "oppfinne" en ny en.

Denne MVP-runden registrerer nøyaktig ett verktøy: et skrivebeskyttet
oppslag mot Core sine kanoniske masterdatafiler, adressert via
core/manifest.json (docs/development/KBH_CORE_CONTRACT.md §1: Core eier
kanonisk masterdata, stabile ID-er og scheman) og lest med
modules/master_data_io.py -- samme leseren App/Web-koden selv bruker.
Sóti dupliserer aldri denne dataen inn i et prompt (se soti.identity);
den slår den opp på nytt, skrivebeskyttet, for hver henvendelse.
"""
import json
import os
from dataclasses import dataclass
from typing import Callable

from modules.master_data_io import les_master_json

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MANIFEST_PATH = os.path.join(_REPO_ROOT, "core", "manifest.json")

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


def bygg_standard_registry():
    """Registry med Sóti sitt eneste MVP-verktøy: Core-oppslaget over."""
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
    return registry
