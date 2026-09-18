"""
Sóti -- skills. En skill pakker instruksjoner + hvilke verktøy Sóti får
tilgang til for én bestemt oppgavetype, uten selv å duplisere Core sin
kanoniske data (se soti.identity, soti.tools).

To skiller defineres her:
- BRYGGE_OPPSLAG_SKILL (uendret, bevart for kompatibilitet) -- kun
  ingrediensoppslaget, for eksisterende brukssteder/tester som
  konstruerer SotiRuntime uten et eksplisitt skill-valg.
- SOTI_KOMBINERT_SKILL (V2-5C1, issue #317) -- det lokale CLI-et sin
  faktiske skill: ingredienssoppslaget PLUSS det verifiserte
  fagfakta-oppslaget mot Bryggeskolens Course Fact Registry, med
  instruksjoner som eksplisitt skiller de to verktøyene og som forbyr
  å presentere modellens egen hukommelse som en verifisert
  Kvernhaug-fakta.
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


SOTI_KOMBINERT_SKILL = BryggeSkill(
    navn="soti_kombinert",
    instruksjoner=(
        "Skill: soti_kombinert. Du har to skrivebeskyttede verktøy, og de "
        "dekker to ulike typer spørsmål:\n"
        "1) 'hent_ingrediens_info' -- for konkrete spørsmål om identitet "
        "eller egenskaper til en bestemt malt-, humle- eller gjærtype "
        "(Core sin kanoniske masterdata). Bruk dette verktøyet FØR du "
        "svarer på den typen spørsmål -- ikke svar fra hukommelsen.\n"
        "2) 'hent_verifisert_fagfakta' -- for spørsmål innenfor "
        "Bryggeskolens verifiserte fagkonsepter (Course Fact Registry). "
        "Bruk dette verktøyet FØR du svarer på den typen spørsmål.\n"
        "Presenter aldri egen hukommelse eller generell kunnskap som en "
        "verifisert Kvernhaug-fakta. Hvis 'hent_verifisert_fagfakta' ikke "
        "finner noe treff, si tydelig at den verifiserte "
        "Kvernhaug-kunnskapsbasen foreløpig ikke inneholder svar på det -- "
        "ikke dikt opp et svar. For identitet, hyggeprat eller spørsmål "
        "som ikke handler om brygging, trenger du ikke tvinge frem et "
        "verktøykall."
    ),
    tillatte_verktoy=("hent_ingrediens_info", "hent_verifisert_fagfakta"),
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
