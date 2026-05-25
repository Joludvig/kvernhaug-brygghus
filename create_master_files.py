import json

# Read existing malt.json
with open("data/malt.json", "r", encoding="utf-8") as f:
    malt_data = json.load(f)

# Convert to master format with aliases and butikk_match
malt_master = {}

for malt_id, malt_info in malt_data.items():
    malt_master[malt_id] = {
        "display_name": malt_info["display_name"],
        "produsent": malt_info["produsent"],
        "kategori": malt_info["kategori"],
        "smakstags": malt_info["smakstags"],
        "kategorier": malt_info["kategorier"],
        "maks_prosent": malt_info["maks_prosent"],
        "anbefalte_stiler": malt_info["anbefalte_stiler"],
        "knust_tilgjengelig": malt_info["knust_tilgjengelig"],
        "ebc": malt_info["ebc"],
        "potensiale": malt_info["potensiale"],
        "aliases": [malt_info["display_name"]],
        "butikk_match": {
            "vestbrygg": {
                "search_terms": [malt_info["display_name"]],
                "pris": malt_info["pris_vestbrygg"],
                "url": None
            },
            "olbrygging": {
                "search_terms": [malt_info["display_name"]],
                "pris": malt_info["pris_olbrygging"],
                "url": None
            }
        },
        "verified": False,
        "source": "master_seed_v0_1"
    }

# Save master_malt.json
with open("data/master_malt.json", "w", encoding="utf-8") as f:
    json.dump(malt_master, f, ensure_ascii=False, indent=2)

print("✅ master_malt.json created")

# Read existing gjaer.json
with open("data/gjaer.json", "r", encoding="utf-8") as f:
    gjaer_data = json.load(f)

# Convert to master format
gjaer_master = {}

for gjaer_id, gjaer_info in gjaer_data.items():
    gjaer_master[gjaer_id] = {
        "display_name": gjaer_info["display_name"],
        "produsent": gjaer_info["produsent"],
        "kategori": gjaer_info["kategori"],
        "smakstags": gjaer_info["smakstags"],
        "kategorier": gjaer_info["kategorier"],
        "maks_prosent": gjaer_info["maks_prosent"],
        "anbefalte_stiler": gjaer_info["anbefalte_stiler"],
        "knust_tilgjengelig": gjaer_info["knust_tilgjengelig"],
        "attenuation": gjaer_info["attenuation"],
        "pris_per_pakke": gjaer_info["pris_per_pakke"],
        "aliases": [gjaer_info["display_name"]],
        "butikk_match": {
            "vestbrygg": {
                "search_terms": [gjaer_info["display_name"]],
                "pris": gjaer_info["pris_vestbrygg"],
                "url": None
            },
            "olbrygging": {
                "search_terms": [gjaer_info["display_name"]],
                "pris": gjaer_info["pris_olbrygging"],
                "url": None
            }
        },
        "verified": False,
        "source": "master_seed_v0_1"
    }

# Save master_gjaer.json
with open("data/master_gjaer.json", "w", encoding="utf-8") as f:
    json.dump(gjaer_master, f, ensure_ascii=False, indent=2)

print("✅ master_gjaer.json created")
