"""
LEGACY / FULL-SCAN: manuell kjøring av den fulle skrape-pipelinen
(malt + humle + gjær i én kjøring), til tross for filnavnet.

Dette gjør ekte HTTP-kall mot vestbrygg.no / olbrygging.no / litebrygg.no og
overskriver raw_data/malt_raw.json, raw_data/humle_raw.json og
raw_data/gjaer_raw.json. Skal KUN kjøres manuelt av en person som har tenkt
seg å skrape hele katalogen — aldri importeres av testoppsett.

Trenger du KUN malt (uten å røre humle-/gjærdata), bruk i stedet det nye,
avgrensede entrypointet:
    py -3 scripts/scrape_malt_only.py

Kjøres fra repo-roten:
    py -3 scripts/scrape_malt.py
"""
from modules.store_scraper import kjor_full_skanning


def main():
    malt, humle, gjaer = kjor_full_skanning()
    print(f"\n=== RESULTAT ===\nMalt: {malt}\nHumle: {humle}\nGjær: {gjaer}")


if __name__ == "__main__":
    main()
