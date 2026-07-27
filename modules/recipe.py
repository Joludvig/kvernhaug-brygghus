# modules/recipe.py

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
