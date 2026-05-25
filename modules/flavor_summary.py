# modules/flavor_summary.py

def generer_smakssammendrag(flavor_profile):
    """
    Analyserer de 18 smaksverdiene fra smakshjulet, sorterer ut toppnotene,
    og returnerer en naturlig tekstbeskrivelse av ølets dominerende karakter.
    """
    if not flavor_profile:
        return "Ingen utpreget smaksprofil ennå."

    # Sorter alle kategorier basert på poengsum (høyest først)
    sorterte_smaker = sorted(flavor_profile.items(), key=lambda x: x[1], reverse=True)
    
    # Filtrer ut svake smaker (alt under 2.0 i intensitet overses)
    kraftige_smaker = [smak.lower() for smak, verdi in sorterte_smaker if verdi >= 2.0]
    
    if not kraftige_smaker:
        return "Dette blir et veldig mildt og nøytralt øl uten dominerende smaksnoter."
        
    # Ta de opptil 4 mest dominerende smaksnotene
    topp_noter = kraftige_smaker[:4]
    
    if len(topp_noter) == 1:
        return f"Dette ølet vil ha en tydelig dominerende smak av **{topp_noter[0]}**."
    
    # Bygg en naturlig språklig setning (f.eks: "sjokolade, kaffe og karamell")
    setning = ", ".join(topp_noter[:-1]) + f" og {topp_noter[-1]}"
    
    return f"Det ferdige brygget vil preges av en tydelig balanse med noter av **{setning}**."
