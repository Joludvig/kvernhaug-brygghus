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
from pathlib import Path
import sys

# Direkte kjøring (py -3 scripts/scrape_malt.py) setter sys.path[0]
# til scripts/, ikke repo-roten — modules/ blir da ikke funnet uten dette.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from modules.store_scraper import kjor_full_skanning


def main():
    malt, humle, gjaer = kjor_full_skanning()
    print(f"\n=== RESULTAT ===\nMalt: {malt}\nHumle: {humle}\nGjær: {gjaer}")


if __name__ == "__main__":
    main()
