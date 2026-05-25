"""
Sjekker at runtime-databaser (malt.json) er i sync med masterdatabasene.
Kjør direkte: python -m modules.validate_sync
"""
import json
import os
import sys

# master -> (runtime, required_fields_i_runtime)
MASTER_TIL_RUNTIME = {
    "data/master_malt.json": (
        "data/malt.json",
        ["display_name", "kategori", "ebc", "potensiale", "smakstags",
         "pris_vestbrygg", "pris_olbrygging"],
    ),
}

# Masterfiler som leses direkte av appen (ingen separat runtime-fil)
MASTER_DIREKTE = [
    "data/master_humle_v2.json",
    "data/master_gjaer_v2.json",
]


def _last_json(sti):
    if not os.path.exists(sti):
        return None
    with open(sti, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def validate_sync(base_dir="."):
    problemer = []

    for master_sti, (runtime_sti, required_fields) in MASTER_TIL_RUNTIME.items():
        master_full = os.path.join(base_dir, master_sti)
        runtime_full = os.path.join(base_dir, runtime_sti)

        master = _last_json(master_full)
        runtime = _last_json(runtime_full)

        if master is None:
            problemer.append(f"MANGLER master: {master_sti}")
            continue
        if runtime is None:
            problemer.append(f"MANGLER runtime: {runtime_sti}")
            continue

        master_ids = set(master.keys())
        runtime_ids = set(runtime.keys())

        bare_i_master = master_ids - runtime_ids
        bare_i_runtime = runtime_ids - master_ids

        if bare_i_master:
            problemer.append(
                f"Runtime mangler {len(bare_i_master)} entries fra master: "
                + ", ".join(sorted(bare_i_master))
            )
        if bare_i_runtime:
            problemer.append(
                f"Runtime har {len(bare_i_runtime)} entries ikke i master: "
                + ", ".join(sorted(bare_i_runtime))
            )

        for entry_id, entry in runtime.items():
            for felt in required_fields:
                if felt not in entry:
                    problemer.append(
                        f"{runtime_sti}/{entry_id}: mangler påkrevd felt '{felt}'"
                    )

        master_kats = {v.get("kategori") for v in master.values() if v.get("kategori")}
        runtime_kats = {v.get("kategori") for v in runtime.values() if v.get("kategori")}
        kun_i_master = master_kats - runtime_kats
        if kun_i_master:
            problemer.append(
                f"Kategorier i master men ikke runtime: {', '.join(sorted(kun_i_master))}"
            )

    for sti in MASTER_DIREKTE:
        full = os.path.join(base_dir, sti)
        if not os.path.exists(full):
            problemer.append(f"MANGLER masterfil (brukes direkte av appen): {sti}")

    return problemer


if __name__ == "__main__":
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    problemer = validate_sync(base_dir=base)
    if problemer:
        print(f"Fant {len(problemer)} synkroniseringsproblemer:")
        for p in problemer:
            print(f"  - {p}")
        sys.exit(1)
    else:
        print("OK: master og runtime er i sync.")
        sys.exit(0)
