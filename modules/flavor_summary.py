# modules/flavor_summary.py


def _formater_noter(noter: list[str]) -> str:
    if not noter:
        return ""
    if len(noter) == 1:
        return noter[0]
    return ", ".join(noter[:-1]) + f" og {noter[-1]}"


def generer_smakssammendrag(flavor_profile: dict) -> str:
    """
    Produserer et karakterspesifikt narrativ basert på dominante smaksnivåer.
    Skiller mellom røyk-/mørk-, tropisk-, malt- og balansert karakter.
    Bold-markering (**) beholdes — fjernes i card_template ved visning der.
    """
    if not flavor_profile:
        return "Ingen utpreget smaksprofil ennå."

    fp = flavor_profile
    sorterte = sorted(fp.items(), key=lambda x: x[1], reverse=True)

    tydelige = [(k.lower(), v) for k, v in sorterte if v >= 2.0]
    bakgrunn = [k.lower() for k, v in sorterte if 1.0 <= v < 2.0]

    if not tydelige:
        return "Dette blir et veldig mildt og nøytralt øl uten dominerende smaksnoter."

    røyk      = fp.get("Røyk", 0)
    sjokolade = fp.get("Sjokolade", 0)
    kaffe     = fp.get("Kaffe", 0)
    tropisk   = fp.get("Tropisk", 0)
    sitrus    = fp.get("Sitrus", 0)
    maltfylde = fp.get("Maltfylde", 0)
    bitterhet = fp.get("Bitterhet", 0)

    topp = [k for k, v in tydelige[:4]]

    mørk_profil    = sjokolade >= 3 or kaffe >= 3
    røyk_profil    = røyk >= 3
    tropisk_profil = tropisk >= 4 or sitrus >= 4

    # ── Åpningssetning ──────────────────────────────────────────────────────
    if røyk_profil and mørk_profil:
        noter_str = _formater_noter(topp[:3])
        åpning = f"Et mørkt, røykpreget brygg med dype noter av **{noter_str}**"

    elif røyk_profil:
        støtte = [n for n in topp if n != "røyk"][:2]
        if støtte:
            åpning = f"**Røyk** setter tonen, understøttet av {_formater_noter(støtte)}"
        else:
            åpning = "**Røyk** dominerer hele smaksbildet"

    elif mørk_profil:
        mørke = [n for n in topp if n in ("sjokolade", "kaffe", "toast", "brød")][:2]
        rest  = [n for n in topp if n not in mørke][:2]
        if mørke and rest:
            åpning = f"Dyp, mørk profil med **{_formater_noter(mørke)}** og innslag av {_formater_noter(rest)}"
        else:
            åpning = f"Dyp, mørk profil dominert av **{_formater_noter(topp[:2])}**"

    elif tropisk_profil:
        åpning = f"Saftig og fruktig karakter med dominerende **{topp[0]}**"
        if len(topp) > 1:
            åpning += f", understøttet av {_formater_noter(topp[1:3])}"

    elif maltfylde >= 4.5 and bitterhet < 4:
        åpning = f"Fyldig og rund maltkarakter med tydelig **{topp[0]}**"
        if len(topp) > 1:
            åpning += f" og innslag av {_formater_noter(topp[1:3])}"

    else:
        if len(topp) == 1:
            åpning = f"Tydelig karakter av **{topp[0]}**"
        elif len(topp) == 2:
            åpning = f"Balansert profil med **{topp[0]}** og **{topp[1]}**"
        else:
            åpning = f"Balansert profil med **{_formater_noter(topp[:2])}** og innslag av {_formater_noter(topp[2:4])}"

    resultat = åpning + "."

    # ── Bakgrunnsnoter ──────────────────────────────────────────────────────
    bak_noter = [k for k in bakgrunn[:2] if k not in topp]
    if bak_noter:
        resultat += f" I bakgrunnen aner man {_formater_noter(bak_noter)}."

    return resultat
