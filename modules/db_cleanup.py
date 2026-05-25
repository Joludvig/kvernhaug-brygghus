# modules/db_cleanup.py
import json

# ── ID-kart: alle gamle IDer → ny kanonisk ID ──────────────────────────────
ID_MAP = {
    # Mangrove Jack's M-serie
    "empire_ale_m_15":        "mangrove_m15_empire_ale",
    "empire_ale_m15":         "mangrove_m15_empire_ale",
    "bavarian_wheat_m_20":    "mangrove_m20_bavarian_wheat",
    "bavarian_wheat_m20":     "mangrove_m20_bavarian_wheat",
    "belgian_wit_m_21":       "mangrove_m21_belgian_wit",
    "belgian_wit_m21":        "mangrove_m21_belgian_wit",
    "french_saison_m_29":     "mangrove_m29_french_saison",
    "french_saison_m29":      "mangrove_m29_french_saison",
    "belgian_tripel_m_31":    "mangrove_m31_belgian_tripel",
    "belgian_tripel_m31":     "mangrove_m31_belgian_tripel",
    "belgian_ale_m_41":       "mangrove_m41_belgian_ale",
    "belgian_ale_m41":        "mangrove_m41_belgian_ale",
    "california_lager_m_54":  "mangrove_m54_california_lager",
    "california_lager_m54":   "mangrove_m54_california_lager",
    "bavarian_lager_m_76":    "mangrove_m76_bavarian_lager",
    "bavarian_lager_m76":     "mangrove_m76_bavarian_lager",
    "bohemian_lager_m_84":    "mangrove_m84_bohemian_lager",
    "bohemian_lager_m84":     "mangrove_m84_bohemian_lager",
    # LalBrew / Lallemand
    "lalbrew_house_ale":      "lalbrew_house_ale",
    "lalbrew_new_england":    "lalbrew_new_england",
    "lalbrew_munich_classic": "lalbrew_munich_classic",
    "lalbrew_diamond_lager":  "lalbrew_diamond_lager",
    "lalbrew_voss_kveik":     "lalbrew_voss_kveik",
    "lalbrew_verdant":        "lalbrew_verdant",
    # Kveik Yeastery
    "k1_voss_homebrew":       "kveikyeastery_k1_voss",
    "k1_voss":                "kveikyeastery_k1_voss",
    "k9_ebbegarden_homebrew": "kveikyeastery_k9_ebbegarden",
    "k9_ebbegarden":          "kveikyeastery_k9_ebbegarden",
    "k14_eitrheim_homebrew":  "kveikyeastery_k14_eitrheim",
    "k14_eitrheim":           "kveikyeastery_k14_eitrheim",
    "k22_stalljen_homebrew":  "kveikyeastery_k22_stalljen",
    "k22_stalljen":           "kveikyeastery_k22_stalljen",
    # Fermentis
    "safale_us_05":           "fermentis_us05",
    "safale_s04":             "fermentis_s04",
    "saflager_w3470":         "fermentis_w3470",
    # Wyeast
    "wyeast_1318":            "wyeast_1318",
}

# Gammel master-ID → ny kanonisk ID (for å slå opp master-data)
MASTER_ID_MAP = {
    "k1_voss":          "kveikyeastery_k1_voss",
    "k9_ebbegarden":    "kveikyeastery_k9_ebbegarden",
    "k14_eitrheim":     "kveikyeastery_k14_eitrheim",
    "k22_stalljen":     "kveikyeastery_k22_stalljen",
    "bohemian_lager_m84":    "mangrove_m84_bohemian_lager",
    "belgian_ale_m41":       "mangrove_m41_belgian_ale",
    "bavarian_wheat_m20":    "mangrove_m20_bavarian_wheat",
    "california_lager_m54":  "mangrove_m54_california_lager",
    "empire_ale_m15":        "mangrove_m15_empire_ale",
    "french_saison_m29":     "mangrove_m29_french_saison",
    "belgian_tripel_m31":    "mangrove_m31_belgian_tripel",
    "belgian_wit_m21":       "mangrove_m21_belgian_wit",
    "bavarian_lager_m76":    "mangrove_m76_bavarian_lager",
}

PLACEHOLDER_SMAKS = {"humlearoma"}
PLACEHOLDER_KAT   = {"Bitterhet": 5, "Sitrus": 2}
JUNK_FIELDS       = {"maks_prosent", "anbefalte_stiler", "knust_tilgjengelig"}


def _er_placeholder(entry):
    smaks = set(entry.get("smakstags", []))
    kat   = entry.get("kategorier", {})
    return smaks == PLACEHOLDER_SMAKS or kat == PLACEHOLDER_KAT


def _data_quality(entry):
    if _er_placeholder(entry):
        return "low"
    har_gjaertype  = bool(entry.get("gjaertype"))
    ekte_att       = entry.get("attenuation", 0.75) != 0.75
    kjent_produsent = entry.get("produsent", "Ukjent") not in ("Ukjent", "")
    poeng = sum([har_gjaertype, ekte_att, kjent_produsent])
    return "high" if poeng >= 2 else "medium"


def _beste_pris(entries, felt):
    return max((e.get(felt, 0) or 0 for e in entries), default=0)


def _merge(entries, master_oppslag):
    """
    Slår sammen duplikater. Master-data vinner for sensoriske felt.
    Priser hentes fra det beste tilgjengelige entry.
    """
    ikke_placeholder = [e for e in entries if not _er_placeholder(e)]
    base_kilde = ikke_placeholder[0] if ikke_placeholder else entries[0]

    # Start med ikke-placeholder base
    result = {k: v for k, v in base_kilde.items() if k not in JUNK_FIELDS}

    # Berik med master-data hvis tilgjengelig
    if master_oppslag:
        for felt in ("smakstags", "gjaertype", "attenuation", "produsent", "kategori"):
            if felt in master_oppslag:
                result[felt] = master_oppslag[felt]

    # Ta beste pris fra alle entries
    for pf in ("pris_vestbrygg", "pris_olbrygging", "pris_per_pakke"):
        beste = _beste_pris(entries, pf)
        result[pf] = beste

    # Fjern placeholder-kategorier
    if result.get("kategorier") == PLACEHOLDER_KAT:
        result.pop("kategorier", None)

    result["data_quality"] = _data_quality(result)
    return result


def rydd_gjaer(inn_sti, master_sti, ut_sti):
    with open(inn_sti, "r", encoding="utf-8") as f:
        gjaer = json.load(f)
    with open(master_sti, "r", encoding="utf-8") as f:
        master = json.load(f)

    # Grupper alle gamle entries på ny kanonisk ID
    grupper: dict[str, list] = {}
    ukjente = []
    for gammel_id, data in gjaer.items():
        ny_id = ID_MAP.get(gammel_id)
        if ny_id:
            grupper.setdefault(ny_id, []).append(data)
        else:
            ukjente.append(gammel_id)

    if ukjente:
        print(f"  ADVARSEL: {len(ukjente)} IDer uten mapping — hoppes over: {ukjente}")

    # Bygg ny renset DB
    renset = {}
    antall_duplikater = 0
    antall_placeholder_fjernet = 0

    for ny_id, entries in grupper.items():
        if len(entries) > 1:
            antall_duplikater += len(entries) - 1

        placeholder_entries = [e for e in entries if _er_placeholder(e)]
        antall_placeholder_fjernet += len(placeholder_entries)

        # Finn master-oppslag: prøv ny ID, deretter omvendt map
        master_oppslag = master.get(ny_id)
        if not master_oppslag:
            gammel_master_id = next(
                (gml for gml, ny in MASTER_ID_MAP.items() if ny == ny_id), None
            )
            if gammel_master_id:
                master_oppslag = master.get(gammel_master_id)

        renset[ny_id] = _merge(entries, master_oppslag)

    with open(ut_sti, "w", encoding="utf-8") as f:
        json.dump(renset, f, ensure_ascii=False, indent=2)

    print(f"  Duplikater merget:          {antall_duplikater}")
    print(f"  Placeholder-entries fjernet: {antall_placeholder_fjernet}")
    print(f"  Entries i renset DB:         {len(renset)}")
    kvalitet = {"high": 0, "medium": 0, "low": 0}
    for v in renset.values():
        kvalitet[v.get("data_quality", "low")] += 1
    print(f"  Data quality — high:{kvalitet['high']}  medium:{kvalitet['medium']}  low:{kvalitet['low']}")
    return renset


if __name__ == "__main__":
    print("=== db_cleanup: Gjær ===")
    rydd_gjaer(
        "data/gjaer.json",
        "data/master_gjaer_v2.json",
        "data/gjaer_cleaned.json",
    )
    print("Skrevet til data/gjaer_cleaned.json")
