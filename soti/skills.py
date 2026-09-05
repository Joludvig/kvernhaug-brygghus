"""
Sóti -- skills. En skill pakker instruksjoner + hvilke verktøy Sóti får
tilgang til for én bestemt oppgavetype, uten selv å duplisere Core sin
kanoniske data (se soti.identity, soti.tools). Denne MVP-runden definerer
nøyaktig én skill: bryggeoppslag -- svare på ingrediensspørsmål via det
skrivebeskyttede Core-oppslaget i soti.tools.
"""
from dataclasses import dataclass

from soti.tools import bygg_standard_registry


@dataclass(frozen=True)
class BryggeSkill:
    navn: str
    instruksjoner: str
    tillatte_verktoy: tuple


BRYGGE_OPPSLAG_SKILL = BryggeSkill(
    navn="brygge_oppslag",
    instruksjoner=(
        "Skill: brygge_oppslag. Når brukeren spør om en konkret malt-, "
        "humle- eller gjærtype, skal du bruke verktøyet "
        "'hent_ingrediens_info' for å slå opp Core sin kanoniske "
        "oppføring FØR du svarer -- ikke svar fra hukommelsen. Oppgi "
        "aldri fakta verktøyet ikke returnerte."
    ),
    tillatte_verktoy=("hent_ingrediens_info",),
)


def registry_for_skill(skill):
    """Bygger et ToolRegistry begrenset til nøyaktig verktøyene skillen
    tillater, selv om standardregistryen (soti.tools.bygg_standard_registry)
    inneholder flere -- en skill kan aldri gi tilgang ut over det som
    fantes i standardregistryen i utgangspunktet."""
    full_registry = bygg_standard_registry()
    begrenset = type(full_registry)()
    for verktoy in full_registry.alle():
        if verktoy.navn in skill.tillatte_verktoy:
            begrenset.registrer(verktoy)
    return begrenset
