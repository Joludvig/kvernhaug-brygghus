import json

with open('raw_data/malt_raw.json') as f:
    data = json.load(f)

malt_list = [d for d in data if d['kategori'] == 'malt']
spraymalt_list = [d for d in data if d['kategori'] == 'spraymalt']

print(f"MALT: {len(malt_list)} produkter")
print(f"SPRAYMALT: {len(spraymalt_list)} produkter\n")

print("Spraymalt produkter:")
for d in spraymalt_list:
    print(f"  - {d['navn']}")

print("\nVert malt (sample):")
for d in malt_list[:10]:
    print(f"  - {d['navn']}")

# Sjekk for ekstrakt som skulle vært blokkert
liquid_check = [d for d in data if 'liquid' in d['navn'].lower() and d['kategori'] != 'spraymalt']
print(f"\nLiquid produkter som IKKJE er spraymalt: {len(liquid_check)}")
if liquid_check:
    for d in liquid_check:
        print(f"  ERROR: {d['navn']} (kategori: {d['kategori']})")
