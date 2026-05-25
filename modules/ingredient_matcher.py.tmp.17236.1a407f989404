# modules/ingredient_matcher.py
import re

def generer_stabil_id(navn):
    """Lager en ren, unik ID basert på produsent og type."""
    id_streng = navn.lower()
    id_streng = re.sub(r'\d+\s*(kg|g|gr|%)', '', id_streng)
    id_streng = re.sub(r'\bknust\b|\bcrushed\b|\bhel\b|\bwhole\b', '', id_streng)
    id_streng = id_streng.replace("malt", "").replace("humle", "").replace("gjær", "").replace("pellets", "")
    id_streng = "".join([c for c in id_streng if c.isalnum() or c in (" ", "_")]).strip()
    id_streng = id_streng.replace(" ", "_")
    return re.sub(r'_{2,}', '_', id_streng)[:30].strip("_")

def sjekk_om_samme_vare(navn1, navn2):
    """Kontrollerer om to produktnavn fra ulike butikker i realiteten er samme vare."""
    id1 = generer_stabil_id(navn1)
    id2 = generer_stabil_id(navn2)
    
    # Splitt opp i enkeltord for å sjekke overlapp (f.eks 'Carafa 3' vs 'Carafa III')
    ord1 = set(id1.split("_"))
    ord2 = set(id2.split("_"))
    
    # Sjekk romertall-variasjoner
    if "iii" in ord1 or "3" in ord1:
        if "iii" in ord2 or "3" in ord2:
            return True
            
    # Hvis mer enn 70% av ordene i navnet matcher, anser vi det som samme ingrediens
    felles = ord1.intersection(ord2)
    if len(felles) / max(len(ord1), len(ord2)) >= 0.7:
        return True
        
    return id1 == id2
