"""
Manuell, avgrenset kjøring av KUN maltskraping (Steg F9A).

Dette gjør ekte HTTP-kall mot vestbrygg.no / olbrygging.no og skriver
KUN raw_data/malt_raw.json. Den rører aldri raw_data/humle_raw.json
eller raw_data/gjaer_raw.json, og kjører aldri matcher eller
AI-normalisering — se modules/store_scraper.py::kjor_malt_skanning().

Skal KUN kjøres manuelt av en person som har tenkt seg å skrape malt —
aldri importeres av testoppsett.

Kjøres fra repo-roten:
    py -3 scripts/scrape_malt_only.py

For å skrape hele katalogen (malt + humle + gjær) i én kjøring, bruk i
stedet scripts/scrape_malt.py.
"""
from modules.store_scraper import kjor_malt_skanning


def main():
    antall_malt = kjor_malt_skanning()
    print(f"\n=== RESULTAT ===\nMalt: {antall_malt}")


if __name__ == "__main__":
    main()
