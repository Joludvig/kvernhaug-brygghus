# modules/recipe_storage.py
import json
import logging
import os
from config import DEMO_MODE

_log = logging.getLogger(__name__)


def _mappe():
    """Aktiv oppskriftsmappe — lest FRISKT ved hvert kall, aldri frosset
    ved modul-import.

    KVERNHAUG_RECIPES_DIR finnes KUN for testisolasjon. En tidligere
    variant leste miljøvariabelen inn i en modulnivå-konstant (`MAPPE =
    os.getenv(...)`) — det virker bare hvis testen setter miljøvariabelen
    FØR modulen importeres FØRSTE gang i hele prosessen. Siden andre
    testmoduler (f.eks. tests/test_process_profiles.py) importerer denne
    modulen ved modul-nivå, kan den ha blitt importert (og MAPPE dermed
    frosset til "recipes") lenge før en senere test rakk å sette
    miljøvariabelen — med det resultat at "isolerte" ende-til-ende-tester
    stille skrev ekte testoppskrifter til den virkelige recipes/-mappen.
    Løsningen er å ALDRI fryse verdien — les os.environ på nytt hver
    gang funksjonene under faktisk trenger stien."""
    return os.getenv("KVERNHAUG_RECIPES_DIR", "recipes")


def sikre_mappe():
    """Sørger for at recipes-mappen eksisterer på harddisken."""
    if not os.path.exists(_mappe()):
        os.makedirs(_mappe())

_TRANSLITERATION = {
    ord('æ'): 'ae', ord('Æ'): 'Ae',
    ord('ø'): 'o',  ord('Ø'): 'O',
    ord('å'): 'a',  ord('Å'): 'A',
    ord('ð'): 'd',  ord('Ð'): 'D',
}

def generer_filnavn(oppskrift_navn):
    """Lager et trygt, standardisert filnavn basert på oppskriftens navn."""
    translittert = oppskrift_navn.translate(_TRANSLITERATION)
    trygg_tittel = "".join([c for c in translittert if c.isalnum() or c in (" ", "_", "-")]).rstrip()
    trygg_tittel = trygg_tittel.replace(" ", "_").lower()
    return f"{trygg_tittel}.json"

def lagre_oppskrift(recipe):
    """Lagrer eller oppdaterer et Recipe Object som en JSON-fil."""
    if DEMO_MODE:
        return None
    sikre_mappe()
    filnavn = generer_filnavn(recipe["name"])
    filsti = os.path.join(_mappe(), filnavn)

    with open(filsti, "w", encoding="utf-8") as f:
        json.dump(recipe, f, ensure_ascii=False, indent=2)
    return filnavn

def _logg_filsti(oppskrift_navn):
    base = generer_filnavn(oppskrift_navn).replace(".json", "_logg.json")
    return os.path.join(_mappe(), base)

def lagre_logg_entry(oppskrift_navn, entry):
    """Legger til én loggoppføring i oppskriftens loggfil."""
    if DEMO_MODE:
        return
    sikre_mappe()
    filsti = _logg_filsti(oppskrift_navn)
    logg = hent_logg(oppskrift_navn)
    logg.append(entry)
    with open(filsti, "w", encoding="utf-8") as f:
        json.dump(logg, f, ensure_ascii=False, indent=2)

def hent_logg(oppskrift_navn):
    """Henter alle loggoppføringer for en oppskrift. Returnerer tom liste hvis ingen."""
    filsti = _logg_filsti(oppskrift_navn)
    if not os.path.exists(filsti):
        return []
    try:
        with open(filsti, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

def hent_alle_oppskrifter(mappe=None):
    """Henter alle lagrede oppskrifter fra harddisken og returnerer et kart.

    `mappe=None` (standard) betyr "den aktive oppskriftsmappen" — løst
    friskt via _mappe() ved KALLET, ikke ved funksjonsdefinisjonen (Python
    evaluerer default-argumentverdier ÉN gang, ved modul-import — akkurat
    samme felle som den gamle MAPPE-konstanten)."""
    if mappe is None:
        mappe = _mappe()
        sikre_mappe()
    elif not os.path.exists(mappe):
        return {}
    filer = [f for f in os.listdir(mappe) if f.endswith(".json") and not f.endswith("_logg.json")]
    oppskrifter = {}

    for f in filer:
        filsti = os.path.join(mappe, f)
        try:
            with open(filsti, "r", encoding="utf-8") as file_content:
                data = json.load(file_content)
                oppskrifter[data["name"]] = data
        except (json.JSONDecodeError, OSError, KeyError) as e:
            _log.warning("Kunne ikke lese oppskriftsfil %s: %s", f, e)
    return oppskrifter

def slett_oppskrift_fil(oppskrift_navn):
    """Sletter oppskriftsfilen fra harddisken."""
    if DEMO_MODE:
        return False
    filnavn = generer_filnavn(oppskrift_navn)
    filsti = os.path.join(_mappe(), filnavn)
    if os.path.exists(filsti):
        os.remove(filsti)
        return True
    return False
