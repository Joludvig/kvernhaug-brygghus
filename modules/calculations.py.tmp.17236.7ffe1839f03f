# modules/calculations.py
import math

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
    return 1 + ((totale_poeng * effektivitet) / volum) / 1000


def beregn_ebc(valgt_malt_liste, malt_data, volum):
    """Beregner ølfarge i EBC ved bruk av Morey's formel."""
    if volum == 0:
        return 0
    mcu = 0
    for m in valgt_malt_liste:
        navn = m["navn"]
        mengde = m["mengde"]
        if navn in malt_data:
            ebc_verdi = malt_data[navn]["ebc"]
            mcu += (mengde * ebc_verdi) / (volum * 0.264)
    return 1.97 * (mcu ** 0.685)


def beregn_fg_og_abv(og, attenuation):
    """Beregner forventet FG og alkoholprosent (ABV) basert på gjærens utgjæring."""
    if og <= 1.000:
        return 1.000, 0.0
    fg = 1 + ((og - 1) * (1 - attenuation))
    abv = (og - fg) * 131.25
    return fg, abv


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
        
        if navn in humle_data and gram > 0:
            alfa = humle_data[navn]["alfa"]
            
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
