# modules/flavor_conflicts.py

def sjekk_smakskonflikter(recipe):
    """
    Analyserer smaksprofilen og de tekniske dataene for å finne 
    potensielle sensoriske konflikter og ubalanser i ølet.
    """
    flavor = recipe["flavor_profile"]
    stats = recipe["stats"]
    
    advarsler = []

    # 1. KONFLIKT: Røyk krasjer med moderne frukt/sitrus-humler
    if flavor.get("Røyk", 0) > 2.0 and (flavor.get("Sitrus", 0) > 4.0 or flavor.get("Tropisk", 0) > 4.0):
        advarsler.append(
            "💥 **Sensorisk krasj (Røyk vs Frukt):** Du har kombinert røykpreg med intense sitrus- eller tropiske humletoner. "
            "I den virkelige verden kan dette skape en ubehagelig ettersmak som minner om brent plast eller gummi. "
            "Vurder å bytte ut humlen med nøytrale sorter (f.eks. Magnum), eller fjerne røyk-ingrediensene."
        )

    # 2. KONFLIKT: Mørk brent kaffe krasjer med ekstrem humlebitterhet
    if flavor.get("Kaffe", 0) > 5.0 and flavor.get("Bitterhet", 0) > 7.0:
        advarsler.append(
            "☕ **Skarp og brent konflikt:** Kombinasjonen av kraftig kaffepreg (røstet korn) og veldig høy humlebitterhet "
            "kan skape en skarp, tørr og nesten medisinsk ettersmak. For en rundere munnfølelse, reduser humlen svakt "
            "eller bruk en gjærstamme som etterlater mer fylde (f.eks. S-04)."
        )

    # 3. KONFLIKT: Krydderestere krasjer med florale humler (Parfyme-fella)
    _FLORALE_HUMLE = {
        "cascade", "centennial", "east_kent_goldings", "saaz", "goldings",
        "harlequin", "hersbrucker", "jester", "mystic", "perle",
        "styrian_dragon", "styrian_golding", "tettnang", "hallertau_mittelfruh",
        "hallertau_blanc", "hallertau_tradition",
        "amarillo", "talus", "ella", "pacific_sunrise",
    }
    if flavor.get("Krydder", 0) > 3.0:
        for hop in recipe["hops"]:
            if hop.get("id") in _FLORALE_HUMLE and hop.get("gram", 0) >= 10:
                advarsler.append(
                    "🧼 **Parfyme-/såpefare:** Blomsterpreget humle sammen med krydret belgisk gjær "
                    "kan gi parfymeaktig preg. Vurder å bytte til nøytral gjær (US-05) eller "
                    "mer tropiske humler (Citra/Galaxy)."
                )
                break

    # 4. KONFLIKT: Klissete restsødme (Høy FG) krasjer med lav IBU
    _og = stats["og"]
    _fg = stats["fg"]
    _attenuation = (_og - _fg) / (_og - 1.0) if _og > 1.001 else 0.0

    _ROAST_MALTER = {
        "carafa_special_1", "carafa_special_2", "carafa_special_3",
        "chocolate_malt", "chocolate_wheat", "roasted_barley",
        "black_malt", "black_patent", "blackprinz",
    }
    _ROKE_MALTER = {"rauchmalz", "peated_malt", "smoked_malt"}

    _total_malt = sum(m.get("mengde", 0.0) for m in recipe.get("malts", []))
    if _total_malt > 0:
        _roast_pct  = sum(m.get("mengde", 0.0) for m in recipe.get("malts", []) if m["id"] in _ROAST_MALTER) / _total_malt
        _smoked_pct = sum(m.get("mengde", 0.0) for m in recipe.get("malts", []) if m["id"] in _ROKE_MALTER) / _total_malt
    else:
        _roast_pct = _smoked_pct = 0.0

    _avvaepnet = (
        _attenuation >= 0.70   # god utgjæring — FG er forventet, ikke et tegn på søthet
        or stats.get("abv", 0.0) >= 7.0   # høy alkohol tørker ut avslutningen
        or _roast_pct  >= 0.03  # ≥3% røstet malt gir tørr kaffe/sjokolade-bitterhet
        or _smoked_pct >= 0.08  # ≥8% røykmalt maskerer opplevd sødme
    )

    if _fg >= 1.020 and stats["ibu"] < 20 and not _avvaepnet:
        advarsler.append(
            "🥞 **Klissete profil:** Dette ølet ender med høy FG og nesten ingen bitterhet til å balansere det. "
            "Med lav alkohol og lys maltprofil risikerer du at ølet smaker som flytende vørter. "
            "Vurder å legge til 10–15 gram bitterhumle ved 60 min, eller bruk en gjær med høyere utgjæringsgrad."
        )

    return advarsler
