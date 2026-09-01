# modules/recipe.py

# PRI 2C0 (KBHR-019) -- efficiency er recipe-scoped semantikk NAR en
# konkret recipe faktisk har en gyldig verdi. Ren, testbar policy-funksjon
# (ingen Streamlit-avhengighet, ingen sideeffekt): avgjør om en
# lagret/importert oppskrifts "efficiency"-felt er en brukbar override,
# eller om kalleren skal falle tilbake til gjeldende utstyrsprofil (som
# for en helt ny oppskrift). Brukes av ui/sidebar.py ved lasting -- selve
# fallback-verdien (utstyrsprofilen) hentes IKKE her, siden denne
# funksjonen ikke skal ha noen kunnskap om hvor default-verdien kommer
# fra (samme separasjon som resten av recipe-modulen).
def resolve_recipe_efficiency(recipe_efficiency):
    """
    Returnerer `recipe_efficiency` uendret hvis den er et ekte, positivt
    tall (ikke bool, ikke NaN) -- ellers None, som eksplisitt betyr
    "ingen recipe-scoped override finnes", IKKE en verdi å bruke.

    None dekker BÅDE "feltet mangler helt" (eldre oppskrift, se
    docs/development/CORE_KBHRECIPE_V1.md) OG "feltet finnes, men er
    ugyldig" (feil type, negativ, null, NaN) -- i begge tilfeller skal
    IKKE en gjettet/feil verdi brukes som om den var brukerens eksplisitte
    valg (samme prinsipp som modules/kbh_contract.py sin "ingen fuzzy-
    matching, ingen fallback-data" for eksport, speilvendt for import).
    """
    if isinstance(recipe_efficiency, bool):
        return None
    if not isinstance(recipe_efficiency, (int, float)):
        return None
    if recipe_efficiency != recipe_efficiency:  # NaN (uten å importere math)
        return None
    if recipe_efficiency <= 0:
        return None
    return recipe_efficiency


def bygg_recipe_object(navn, batch_size, efficiency, malts, hops, yeast, og, fg, abv, ibu, ebc, flavor_profile,
                        brygger_stil="", process_profile=None,
                        water_source_profile=None, water_target_profile=None,
                        water_treatment=None, water_measurements=None):
    """
    `process_profile` (se modules/process_profiles.py) er bevisst et helt
    separat, valgfritt felt — HVORDAN ølet brygges (meskesteg, skyllemetode,
    koketid, ev. dekoksjon/dobbeltmesk), adskilt fra HVA det er laget av
    (malts/hops/yeast over). Å endre prosessprofil skal ALDRI endre
    ingredienslisten, og omvendt.

    `water_*`-feltene (se modules/water_chemistry.py) er på samme måte en
    helt separat, valgfri del — HVILKET VANN ølet brygges med og hvordan
    det justeres med salter/syrer. Å endre vannbehandlingen skal ALDRI
    endre malt/humle/gjær, prosessprofilen eller utstyrsprofilen, og
    omvendt. Gamle oppskrifter uten disse feltene (None) må fortsatt kunne
    åpnes uendret.
    """
    recipe = {
        "name": navn if navn else "Navnløs Brygg",
        "batch_size": batch_size,
        "efficiency": efficiency,
        "brygger_stil": brygger_stil,
        "malts": malts,
        "hops": hops,
        "yeast": yeast,
        "stats": {
            "og": og,
            "fg": fg,
            "abv": abv,
            "ibu": ibu,
            "ebc": ebc
        },
        "flavor_profile": flavor_profile,
        "process_profile": process_profile,
        "water_source_profile": water_source_profile,
        "water_target_profile": water_target_profile,
        "water_treatment": water_treatment,
        "water_measurements": water_measurements,
    }
    return recipe
