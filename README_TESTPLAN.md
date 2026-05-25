# Kvernhaug Brygghus — TESTPLAN V2

Denne testen brukes før masterdatabasene regnes som stabile.

## Steg 1 — Reset

Lager automatisk backup før sletting.

```bash
python testplan_reset.py
```

## Steg 2 — Full scrape

```bash
python test_scraper.py
```

## Steg 3 — Matching

```bash
python -m modules.store_matcher
```

## Steg 4 — Verifisering

```bash
python testplan_verify.py
```

Sjekker:
- 0 unmatched (humle / malt / gjær)
- Ingen duplikat-aliaser
- Eclipse 2021 / 2024 separert med unike priser og URLs
- WLP-routing: WLP 080 → wlp_080 (ikke wlp_077), WLP 300 → wlp_300 (ikke wlp_380)
- Carafa Special I / II / III peker på riktige olbrygging-produkter
- 100g humle vinner over større pakker
- Dekning ≥ 70 % i alle kategorier

## Steg 5 — Backup etter godkjent test

```bash
xcopy /Y data\master_humle_v2.json backup\golden\
xcopy /Y data\master_gjaer_v2.json backup\golden\
xcopy /Y data\master_malt.json      backup\golden\
```
