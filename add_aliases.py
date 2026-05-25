import json

# Les master
with open("data/master_humle_v0_1.json", "r", encoding="utf-8") as f:
    master = json.load(f)

# Les unmatched
with open("raw_data/unmatched_hops.json", "r", encoding="utf-8") as f:
    unmatched = json.load(f)

# Manuelt mapping av 5kg-produkter til deres 100g-ekvivalenter
mapping = {
    "Azacca 2024 5 kg": "azacca",
    "Alora 2024 5 kg": "alora",
    "Cashmere 2023 - 5 kg": "cashmere",
    "Comet 2021 5 kg": None,  # Ikke i master
    "Centennial 2024 5 kg": "centennial",
    "Centennial 2025 5 kg": "centennial",
    "BRU-1 2022 100 g": "bru_1",
    "BRU-1 2024 5 kg": "bru_1",
    "Chinook 2024 5 kg": "chinook",
    "Akoya 2024 5 kg": "akoya",
    "Amarillo 2024 5 kg": "amarillo",
    "Citra 2024 5 kg": "citra",
    "BRU-1 2023 100 g": "bru_1",
}

# Legg til aliaser
for produkt_navn, master_id in mapping.items():
    if master_id and master_id in master:
        if produkt_navn not in master[master_id]["aliases"]:
            master[master_id]["aliases"].append(produkt_navn)

# Lagre oppdatert master
with open("data/master_humle_v0_1.json", "w", encoding="utf-8") as f:
    json.dump(master, f, ensure_ascii=False, indent=2)

print("Aliases added. Running matcher again...")

# Re-run matcher
from modules.store_matcher import match_store_data_to_master
matched, unmatched = match_store_data_to_master(
    "raw_data/humle_raw.json",
    "data/master_humle_v0_1.json",
    "raw_data/matched_hops.json",
    "raw_data/unmatched_hops.json",
)
print(f"Matched: {matched}")
print(f"Unmatched: {unmatched}")
