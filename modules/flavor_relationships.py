# modules/flavor_relationships.py

def sjekk_raavare_kombinasjoner(recipe):
    """
    Skanner de unike ID-ene i oppskriften for å gjenkjenne 
    klassiske, historiske råvarekombinasjoner.
    """
    # Hent ut ID-ene på det som faktisk er valgt med mengde over 0
    malt_ids = [m["id"] for m in recipe["malts"] if m["mengde"] > 0]
    hop_ids = [h["id"] for h in recipe["hops"] if h["gram"] > 0]
    gjaer_id = recipe["yeast"]

    # 1. SJEKK: Norsk Kveik-tradisjon (Bonsak + Voss Kveik)
    if ("bonsak_fairytale" in malt_ids or "bonsak_floyen" in malt_ids) and gjaer_id == "lallemand_voss":
        return (
            "🇳🇴 **Norsk Gårdsøl-tradisjon:** Du bruker trøndersk gårds-malt fra Bonsak sammen med "
            "tradisjonell Voss Kveik. Dette trekker linjene rett tilbake til det tradisjonelle norske gårdsølet. "
            "Gjæres dette varmt (rundt 35–38°C), vil kveiken eksplodere i en herlig og saftig appelsinaroma!"
        )

    # 2. SJEKK: Klassisk Britisk Ale (Maris Otter + EKG + S-04)
    if "fawcett_maris_otter" in malt_ids and "ekg_uk" in hop_ids and gjaer_id == "fermentis_s04":
        return (
            "🇬🇧 **Tradisjonell Britisk Ale-profil:** Du har satt sammen Maris Otter, "
            "East Kent Goldings og engelsk ale-gjær. Dette er den udødelige ryggraden i britiske "
            "bittere og brown ales. Forvent en herlig, jordlig humlearoma balansert mot en rik og nøtteaktig maltbunn."
        )

    # 3. SJEKK: Moderne Hazy IPA-retning (Havregryn + Citra/Mosaic + Verdant)
    if "oats_flake" in malt_ids and ("us_citra" in hop_ids or "us_mosaic" in hop_ids) and gjaer_id == "lallemand_verdant":
        return (
            "🍊 **Moderne Juicy / Hazy IPA-retning:** Kombinasjonen av havregryn, "
            "fruktorienterte humler og Verdant-gjæren er selve suksessoppskriften på en New England IPA. "
            "Dette vil gi en intens, tåkete og juice-aktig munnfølelse proppfull av aprikos og tropiske frukter!"
        )

    return None
