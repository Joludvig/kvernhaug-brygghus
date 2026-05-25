import json

with open('raw_data/gjaer_raw.json') as f:
    data = json.load(f)

print(f"Total gjær produkter: {len(data)}\n")
for i, d in enumerate(data, 1):
    print(f"{i}. {d['navn']}")
