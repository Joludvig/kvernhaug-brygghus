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
    # Siden du hater dette, setter vi et strengt flagg her!
    if flavor.get("Krydder", 0) > 4.0 and (flavor.get("Sitrus", 0) > 3.0 or flavor.get("Fruktighet", 0) > 4.0):
        # Vi sjekker om det er parfymerte humler aktive i oppskriften
        for hop in recipe["hops"]:
            if hop["id"] in ["us_cascade", "ekg_uk", "saaz_cz"]:
                advarsler.append(
                    "🧼 **Parfyme- og såpe-alarm!** Gjæren din produserer mye krydder/estere, samtidig som du bruker en floral "
                    "humle (som Cascade, Saaz eller EKG). Dette vil forsterke den intense **blomster- og parfymerte smaken** "
                    "som du hater. Vurder å bytte til en helt ren gjær (US-05) eller mer tropiske humler (Citra/Galaxy)."
                )
                break

    # 4. KONFLIKT: Klissete restsødme (Høy FG) krasjer med lav IBU
    if stats["fg"] >= 1.020 and stats["ibu"] < 20:
        advarsler.append(
            "🥞 **Klissete profil:** Dette ølet ender med en veldig høy FG (mye uforgjærbart sukker), men har nesten ingen "
            "bitterhet til å balansere det. Ølet vil smake som flytende vørter eller sirup. "
            "Vurder å legge til 10-15 gram ekstra bitterhumle ved 60 minutter kok."
        )

    return advarsler
