# modules/recipe_storage.py
import json
import os

MAPPE = "recipes"

def sikre_mappe():
    """Sørger for at recipes-mappen eksisterer på harddisken."""
    if not os.path.exists(MAPPE):
        os.makedirs(MAPPE)

def generer_filnavn(oppskrift_navn):
    """Lager et trygt, standardisert filnavn basert på oppskriftens navn."""
    trygg_tittel = "".join([c for c in oppskrift_navn if c.isalnum() or c in (" ", "_", "-")]).rstrip()
    trygg_tittel = trygg_tittel.replace(" ", "_").lower()
    return f"{trygg_tittel}.json"

def lagre_oppskrift(recipe):
    """Lagrer eller oppdaterer et Recipe Object som en JSON-fil."""
    sikre_mappe()
    filnavn = generer_filnavn(recipe["name"])
    filsti = os.path.join(MAPPE, filnavn)
    
    with open(filsti, "w", encoding="utf-8") as f:
        json.dump(recipe, f, ensure_ascii=False, indent=2)
    return filnavn

def hent_alle_oppskrifter():
    """Henter alle lagrede oppskrifter fra harddisken og returnerer et kart."""
    sikre_mappe()
    filer = [f for f in os.listdir(MAPPE) if f.endswith(".json")]
    oppskrifter = {}
    
    for f in filer:
        filsti = os.path.join(MAPPE, f)
        try:
            with open(filsti, "r", encoding="utf-8") as file_content:
                data = json.load(file_content)
                # Vi bruker oppskriftens visningsnavn som nøkkel
                oppskrifter[data["name"]] = data
        except:
            continue
    return oppskrifter

def slett_oppskrift_fil(oppskrift_navn):
    """Sletter oppskriftsfilen fra harddisken."""
    filnavn = generer_filnavn(oppskrift_navn)
    filsti = os.path.join(MAPPE, filnavn)
    if os.path.exists(filsti):
        os.remove(filsti)
        return True
    return False
