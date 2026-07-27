# modules/calculations.py
import math

# Enhetskonstanter brukt av beregn_ebc() -- se funksjonsdokstrengen for
# hele konverteringskjeden og kildene til hver konstant.
_KG_TIL_LB = 2.2046226218
_LITER_TIL_US_GALLON = 0.2641720524
# Anerkjent ASBC/EBC-harmoniseringsfaktor mellom SRM/°Lovibond og °EBC
# (samme konvensjon brukt av bl.a. BeerSmith og Brewer's Friend sine
# MCU/Morey-kalkulatorer): °EBC = 1.97 x °SRM, og for maltfarge spesifikt
# °Lovibond = °EBC / 1.97 (°Lovibond behandles som numerisk ~= °SRM for
# selve maltkornet, som er standardpraksisen i Morey-baserte kalkulatorer).
_EBC_TIL_SRM_FAKTOR = 1.97

def beregn_og(valgt_malt_liste, malt_data, volum, effektivitet):
    """Beregner Original Gravity (OG) basert på maltmengde og meskeeffektivitet."""
    totale_poeng = 0
    for m in valgt_malt_liste:
        navn = m["navn"]
        mengde = m["mengde"]
        if navn in malt_data:
            potensiale = malt_data[navn].get("potensiale", 1.036)
            totale_poeng += (mengde * (potensiale - 1) * 1000)
    if volum == 0:
        return 1.000
    # 8.3454 konverterer fra lbs/gallon (PPG) til kg/liter (metrisk)
    return 1 + ((totale_poeng * effektivitet * 8.3454) / volum) / 1000


def beregn_ebc(valgt_malt_liste, malt_data, volum):
    """Beregner ølfarge i EBC ved bruk av Morey's formel.

    master_malt.json lagrer maltfarge i °EBC (verifisert mot produsentenes
    egne datablad, f.eks. Weyermann Bohemian Pilsner Floor = 4.0 EBC,
    CaraHell = 25.0 EBC). Morey-formelen er derimot definert i imperiale
    enheter (lb, US gallon) og °Lovibond, så hvert malt konverteres i tur:

      1. °EBC -> °Lovibond:  L = EBC / 1.97
      2. kg -> lb:           lb = kg * 2.2046226218
      3. liter -> US gallon: gal = L * 0.2641720524
      4. MCU (malt color units), summert over alle malttyper:
             MCU = sum( (lb_i * L_i) / gal_total )
      5. Morey: SRM = 1.4922 * MCU^0.6859
      6. °SRM -> °EBC:       EBC = SRM * 1.97
    """
    if volum <= 0:
        return 0
    mcu = 0.0
    volum_gal = volum * _LITER_TIL_US_GALLON
    for m in valgt_malt_liste:
        navn = m["navn"]
        mengde_kg = m["mengde"]
        if navn in malt_data:
            malt_ebc = malt_data[navn]["ebc"]
            malt_lovibond = malt_ebc / _EBC_TIL_SRM_FAKTOR
            mengde_lb = mengde_kg * _KG_TIL_LB
            mcu += (mengde_lb * malt_lovibond) / volum_gal
    srm = 1.4922 * (mcu ** 0.6859)
    return srm * _EBC_TIL_SRM_FAKTOR


def beregn_fg_og_abv(og, attenuation):
    """Beregner forventet FG og alkoholprosent (ABV) basert på gjærens utgjæring."""
    if og <= 1.000:
        return 1.000, 0.0
    fg = 1 + ((og - 1) * (1 - attenuation))
    abv = (og - fg) * 131.25
    return fg, abv


def beregn_gram_fra_ibu(maal_ibu, alfa_prosent, tid, volum, beregnet_og):
    """Invers Tinseth: beregner gram humle for ønsket IBU-bidrag på én tilsetning."""
    if alfa_prosent <= 0 or volum <= 0 or beregnet_og <= 1.000 or maal_ibu <= 0 or tid <= 0:
        return 0.0
    bigness = 1.65 * (0.000125 ** (beregnet_og - 1))
    times = (1 - math.exp(-0.04 * tid)) / 4.15
    utnyttelse = bigness * times
    if utnyttelse <= 0:
        return 0.0
    return round((maal_ibu * volum) / (1000 * (alfa_prosent / 100.0) * utnyttelse), 1)


def beregn_total_ibu(valgt_humle_liste, humle_data, volum, beregnet_og):
    """
    Beregner nøyaktig bitterhet (IBU) ved bruk av Glenn Tinseths offisielle formel.
    Formelen tar hensyn til både koketid og vørterens tetthet (OG).
    """
    if volum == 0 or beregnet_og <= 1.000:
        return 0
        
    total_ibu = 0.0
    
    # 1. Bigness-faktor: Reduserer utnyttelsen dersom vørteren er veldig tykk/sukkerrik
    # Formel: 1.65 * 0.000125^(OG - 1)
    bigness_faktor = 1.65 * (0.000125 ** (beregnet_og - 1))
    
    for h in valgt_humle_liste:
        navn = h["navn"]
        gram = h["gram"]
        tid = h["tid"]
        
        entry = humle_data.get(navn, {})
        if isinstance(entry, dict) and gram > 0:
            alfa = entry.get("alfa") or entry.get("alfa_typisk") or 5.0
            
            # 2. Times-faktor: Beregner utnyttelseskurven basert på antall minutter i koketiden
            # Formel: (1 - e^(-0.04 * tid)) / 4.15
            times_faktor = (1 - math.exp(-0.04 * tid)) / 4.15
            
            # Total utnyttelse (Decimalandel, f.eks. 0.24 for 24% utnyttelse)
            utnyttelse = bigness_faktor * times_faktor
            
            # Dersom det er tørrhumle (0 min), skal den ikke gi kokebitterhet overhodet
            if tid == 0:
                utnyttelse = 0.0
                
            # 3. Beregn IBU for denne tilsetningen (Tinseth bruker mg/l alfa-syre)
            # Formel: (Gram * Alfa% * Utnyttelse * 10) / Volum
            # (Vi ganger alfa med 10 fordi den ligger som f.eks 13.5 i stedet for 0.135 i JSON)
            alfa_desimal = alfa / 100.0
            mg_per_liter_alfa = (gram * 1000 * alfa_desimal) / volum
            
            total_ibu += mg_per_liter_alfa * utnyttelse
            
    return total_ibu
