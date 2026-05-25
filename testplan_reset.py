"""
TESTPLAN V2 — Steg 1: Komplett reset

Lager sikkerhetskopi av master-filer, tømmer butikk_match,
og sletter raw_data-filer. Etter kjøring er systemet klart
for en ekte end-to-end scrape+match-test.
"""
import json
import os
import shutil
from datetime import datetime

MASTER_FILES = [
    "data/master_humle_v2.json",
    "data/master_malt.json",
    "data/master_gjaer_v2.json",
]
RAW_FILES = [
    "raw_data/malt_raw.json",
    "raw_data/humle_raw.json",
    "raw_data/gjaer_raw.json",
    "raw_data/unmatched_hops.json",
    "raw_data/unmatched_malt.json",
    "raw_data/unmatched_gjaer.json",
]

def lag_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup/pre_testplan_{ts}"
    os.makedirs(backup_dir, exist_ok=True)
    for path in MASTER_FILES:
        if os.path.exists(path):
            shutil.copy2(path, backup_dir)
            print(f"  [BACKUP] {path} -> {backup_dir}/")
    return backup_dir

def tøm_butikk_match(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    endret = 0
    for entry in data.values():
        if "butikk_match" in entry and entry["butikk_match"]:
            entry["butikk_match"] = {}
            endret += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return endret

def slett_raw_filer():
    slettet = 0
    for path in RAW_FILES:
        if os.path.exists(path):
            os.remove(path)
            print(f"  [SLETTET] {path}")
            slettet += 1
    return slettet

def main():
    print("=" * 55)
    print("TESTPLAN V2 — RESET")
    print("=" * 55)

    print("\nSteg 1: Lager sikkerhetskopi...")
    backup_dir = lag_backup()
    print(f"  -> Backup lagret i: {backup_dir}")

    print("\nSteg 2: Tømmer butikk_match i master-filer...")
    for path in MASTER_FILES:
        n = tøm_butikk_match(path)
        print(f"  {path}: {n} oppføringer tømt")

    print("\nSteg 3: Sletter raw_data-filer...")
    n = slett_raw_filer()
    print(f"  -> {n} fil(er) slettet")

    print("\n" + "=" * 55)
    print("RESET KOMPLETT")
    print("Neste steg:")
    print("  1. Kjør full scrape:   python test_scraper.py")
    print("  2. Kjør matcher:       python -m modules.store_matcher")
    print("  3. Kjør verifisering:  python testplan_verify.py")
    print("=" * 55)

if __name__ == "__main__":
    main()
