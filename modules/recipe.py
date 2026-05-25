# modules/recipe.py

def bygg_recipe_object(navn, batch_size, efficiency, malts, hops, yeast, og, fg, abv, ibu, ebc, flavor_profile):
    """
    Samler alle løse variabler, råvarer og beregnede verdier 
    til ett felles, strukturert oppskriftsobjekt.
    """
    recipe = {
        "name": navn if navn else "Navnløs Brygg",
        "batch_size": batch_size,
        "efficiency": efficiency,
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
        "flavor_profile": flavor_profile
    }
    return recipe
