# modules/store_scraper.py
import json
import os
import time
from modules.product_link_scraper import (
    finn_produktsider, finn_gjær_fra_sitemap, finn_humle_fra_sitemap,
    parse_produktside, finn_vestbrygg_malt_med_varianter,
)

def _sikre_raw_mappe():
    if not os.path.exists("raw_data"):
        os.makedirs("raw_data")

def _skann_maltprodukter():
    """
    Henter og bygger den komplette maltlisten (Vestbrygg + Ølbrygging) —
    samme kilde brukt av både kjor_malt_skanning() (Steg F9A) og
    malt-blokken i kjor_full_skanning(), slik at det finnes én
    maltimplementasjon å vedlikeholde, ikke to som kan drive fra
    hverandre over tid.

    Skriver ingenting selv — kalleren avgjør når/om resultatet skrives.
    Sprer videre enhver feil fra underliggende scraping uendret (bygger
    hele listen i minnet før den returneres, så en feil midtveis gir
    aldri en delvis liste tilbake til kalleren).
    """
    malt_lenker_vest = finn_produktsider("https://vestbrygg.no", "råvarer/malt", "malt")
    # Vestbrygg selger mange malter som mor-side + faktiske barn-/
    # variantprodukter (1 kg hel/knust, 100g knust, 25 kg hel/knust) —
    # se Steg E/F1. Erstatter enhver mor-URL med sine ekte barn-URL-er
    # (kun for Vestbrygg-malt; Ølbrygging er uendret, se linjen under).
    malt_lenker_vest = finn_vestbrygg_malt_med_varianter(malt_lenker_vest)
    # Oppdatert til den korrekte råvarebanen hos Ølbrygging: ol/raavarer/malt
    malt_lenker_ol = finn_produktsider("https://www.olbrygging.no", "ol/ingredienser/malt", "malt")

    malt_data = []
    for url in malt_lenker_vest:
        res = parse_produktside(url, "malt", "vestbrygg")
        if res: malt_data.append(res)
        time.sleep(1)

    for url in malt_lenker_ol:
        res = parse_produktside(url, "malt", "olbrygging")
        if res: malt_data.append(res)
        time.sleep(1)

    return malt_data

def kjor_malt_skanning():
    """
    Skraper KUN malt (Vestbrygg + Ølbrygging via _skann_maltprodukter())
    og skriver KUN raw_data/malt_raw.json — se scripts/scrape_malt_only.py.

    Rører aldri raw_data/humle_raw.json eller raw_data/gjaer_raw.json,
    og kaller aldri humle-/gjærinnhenting, matcher eller
    AI-normalisering.

    I motsetning til kjor_full_skanning() (som svelger feil for å
    garantere et trygt returverdi-triplet til Streamlit-UI-et) lar
    denne funksjonen enhver feil fra _skann_maltprodukter() forplante
    seg uendret til kalleren — et manuelt CLI-kjørt malt-only-scrape
    skal vise et ekte traceback ved feil, ikke stille late som ingenting
    skjedde. raw_data/malt_raw.json skrives først når hele
    maltinnhentingen er fullført, så en feil midtveis etterlater alltid
    filen urørt (aldri et delvis resultat).

    Returnerer antall maltprodukter skrevet.
    """
    _sikre_raw_mappe()
    malt_data = _skann_maltprodukter()
    with open("raw_data/malt_raw.json", "w", encoding="utf-8") as f:
        json.dump(malt_data, f, ensure_ascii=False, indent=2)
    return len(malt_data)

def kjor_full_skanning():
    """Hovedmotor som kjører den nye dype link- og produktskanning-pipelinen med krasjsikring."""
    _sikre_raw_mappe()
    
    # Initialiser tellere slik at vi ALDRI returnerer None til Streamlit
    antall_malt = 0
    antall_humle = 0
    antall_gjaer = 0
    
    try:
        # --- 1. SKANNER MALT ---
        print("==================================================")
        print("Skanner MALT via strukturerte produktlenker...")
        print("==================================================")
        malt_data = _skann_maltprodukter()
        with open("raw_data/malt_raw.json", "w", encoding="utf-8") as f:
            json.dump(malt_data, f, ensure_ascii=False, indent=2)
        antall_malt = len(malt_data)

        # --- 2. SKANNER HUMLE ---
        print("==================================================")
        print("Skanner HUMLE via strukturerte produktlenker...")
        print("==================================================")
        # Sitemap er primærkilde for vestbrygg (ASP.NET støtter ikke ?page=N)
        humle_urls_vest = set(finn_humle_fra_sitemap("https://vestbrygg.no"))
        for sti in ["råvarer/humle", "råvarer/humle/pellets"]:
            humle_urls_vest |= set(finn_produktsider("https://vestbrygg.no", sti, "humle"))

        # Sitemap er primærkilde for olbrygging også — finner alle 80 produkter
        humle_urls_ol = set(finn_humle_fra_sitemap("https://www.olbrygging.no"))
        humle_urls_ol |= set(finn_produktsider("https://www.olbrygging.no", "ol/ingredienser/humle", "humle"))

        # Fast injeksjon av produkter ikke indeksert i sitemapen
        VESTBRYGG_HUMLE_EXTRA = [
            "https://vestbrygg.no/pellets/104539/styrian-dragon-2024-pellets-100g-slovenia",
            "https://vestbrygg.no/pellets/104073/styrian-golding-2023-pellets-100g-slovenia",
        ]
        humle_urls_vest |= set(VESTBRYGG_HUMLE_EXTRA)

        humle_data = []
        for url in humle_urls_vest:
            res = parse_produktside(url, "humle", "vestbrygg")
            if res: humle_data.append(res)
            time.sleep(1)

        for url in humle_urls_ol:
            res = parse_produktside(url, "humle", "olbrygging")
            if res: humle_data.append(res)
            time.sleep(1)
            
        with open("raw_data/humle_raw.json", "w", encoding="utf-8") as f:
            json.dump(humle_data, f, ensure_ascii=False, indent=2)
        antall_humle = len(humle_data)

        # --- 3. SKANNER GJÆR ---
        print("==================================================")
        print("Skanner GJÆR via strukturerte produktlenker...")
        print("==================================================")
        # Sitemap er primærkilde — eneste måten å finne alle gjær inkl. Fermentis
        gjaer_urls_vest = set(finn_gjær_fra_sitemap("https://vestbrygg.no"))
        # Kategorisider som supplement for evt. produkter sitemap mangler
        for sti in ["råvarer/gjær", "råvarer/gjær/tørrgjær", "råvarer/gjær/fersk-gjær"]:
            gjaer_urls_vest |= set(finn_produktsider("https://vestbrygg.no", sti, "gjaer"))

        # Sitemap er primærkilde for olbrygging også
        gjaer_urls_ol = set(finn_gjær_fra_sitemap("https://www.olbrygging.no"))
        # Kategorisider som supplement
        for sti in ["ol/ingredienser/yeast/dryyeast", "ol/ingredienser/yeast/freshyeast"]:
            gjaer_urls_ol |= set(finn_produktsider("https://www.olbrygging.no", sti, "gjaer"))

        # Fast injeksjon av Wyeast 1318 fra Litebrygg
        london_1318_url = "https://www.litebrygg.no/products/wyeast-1318---london-ale-iii"

        gjaer_data = []
        print(f"[FAST INJEKSJON] Henter offisielle data for Wyeast 1318...")
        res_1318 = parse_produktside(london_1318_url, "gjaer", "litebrygg")
        if res_1318:
            res_1318["attenuation"] = 0.73
            res_1318["produsent"] = "Wyeast"
            gjaer_data.append(res_1318)

        sett_vest_urls = {r["url"] for r in gjaer_data}
        for url in gjaer_urls_vest:
            if url in sett_vest_urls:
                continue
            res = parse_produktside(url, "gjaer", "vestbrygg")
            if res:
                gjaer_data.append(res)
                sett_vest_urls.add(url)
            time.sleep(1)

        sett_ol_urls = sett_vest_urls.copy()
        for url in gjaer_urls_ol:
            if url in sett_ol_urls:
                continue
            res = parse_produktside(url, "gjaer", "olbrygging")
            if res:
                gjaer_data.append(res)
                sett_ol_urls.add(url)
            time.sleep(1)
            
        with open("raw_data/gjaer_raw.json", "w", encoding="utf-8") as f:
            json.dump(gjaer_data, f, ensure_ascii=False, indent=2)
        antall_gjaer = len(gjaer_data)
        
    except Exception as e:
        print(f"[ERROR] Det skjedde en feil under den globale skanningen: {e}")
        
    # SIKKERHETS-RETURN: Returnerer alltid tallverdier uansett om noe feilet, så Streamlit aldri krasjer
    return antall_malt, antall_humle, antall_gjaer
