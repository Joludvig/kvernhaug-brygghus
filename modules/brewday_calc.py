import math
from modules.equipment import last_equipment

# Fermentation temperature ranges by gjaertype (Norwegian labels)
_TEMP = {
    "ale":                  (18, 22),
    "belgisk ale":          (20, 26),
    "hvetegjær":            (18, 22),
    "lager":                (8,  12),
    "kveik":                (30, 40),
    "saison":               (22, 26),
    "kondisjoneringsgjær":  (18, 22),
    "spesialgjær":          (18, 22),
    "wild/brett-lignende":  (18, 24),
}

# Pitching rate in million cells / mL / °P
_PITCH_RATE = {
    "lager": 1.5,
    "kveik": 0.25,
}
_PITCH_RATE_DEFAULT = 0.75

_DRY_YEAST_BILLION_CELLS = 200  # per 11g pack


def _plato(og):
    return (og - 1.0) * 250


def beregn_vann(total_korn_kg, batch_volum_l, koketid_min, eq):
    mash_vann     = round(total_korn_kg * eq["mash_ratio_l_per_kg"], 1)
    absorpsjon    = total_korn_kg * eq["grain_absorption_l_per_kg"]
    pre_boil      = batch_volum_l + eq["dead_space_l"] + eq["boil_off_l_per_hour"] * (koketid_min / 60)
    wort_fra_mask = mash_vann - absorpsjon
    sparge        = max(0.0, pre_boil - wort_fra_mask)
    return {
        "mash_vann_l":   mash_vann,
        "sparge_vann_l": round(sparge, 1),
        "pre_boil_l":    round(pre_boil, 1),
    }


def _koketid(malt_ider, default_min):
    """90 min if any pilsner base malt present (drives off DMS precursor)."""
    return 90 if any("pilsner" in m.lower() or m in ("best_pils", "belgian_pils") for m in malt_ider) else default_min


def _gjær_type_key(gjaer_info):
    return gjaer_info.get("gjaertype", "Ale").lower()


def beregn_pakker(og, batch_volum_l, gjaer_type_key):
    plato      = _plato(og)
    pitch_rate = _PITCH_RATE.get(gjaer_type_key, _PITCH_RATE_DEFAULT)
    celler_mrd = pitch_rate * batch_volum_l * plato
    return max(1, math.ceil(celler_mrd / _DRY_YEAST_BILLION_CELLS))


def lag_brewday_plan(malt_valg, humle_valg, gjaer_id, gjaer_info, og, batch_volum_l, humle_database):
    eq            = last_equipment()
    total_korn_kg = sum(m["mengde"] for m in malt_valg)
    malt_ider     = {m["id"] for m in malt_valg}
    koketid       = _koketid(malt_ider, eq["default_boil_time_min"])
    gjaer_key     = _gjær_type_key(gjaer_info)

    vann = beregn_vann(total_korn_kg, batch_volum_l, koketid, eq)

    maskeplan = [
        {"temp_c": 66, "varighet_min": 60, "label": "Mashing"},
        {"temp_c": 78, "varighet_min": 5,  "label": "Mashout"},
    ]

    humleplan = sorted(
        [
            {
                "navn": humle_database.get(h["id"], {}).get("display_name", h["id"]),
                "gram": h["gram"],
                "tid":  h["tid"],
            }
            for h in humle_valg
        ],
        key=lambda x: x["tid"],
        reverse=True,
    )

    pakker         = beregn_pakker(og, batch_volum_l, gjaer_key)
    temp_min, temp_maks = _TEMP.get(gjaer_key, (18, 22))

    noter = []
    if gjaer_key == "lager":
        noter.append("Lagergjær — fermenterer kaldt (8–12°C). Bruk dobbel pitching rate.")
    elif gjaer_key == "kveik":
        noter.append("Kveik — tåler høy temperatur (30–40°C). Underpitching er OK.")
    elif gjaer_key == "saison":
        noter.append("Saison — start lavt (20°C), la temperaturen stige gradvis til 26°C.")
    elif gjaer_key == "belgisk ale":
        noter.append("Belgisk gjær — temperatur påvirker esterkarakter sterkt. Start lavt for ryddigere profil.")

    return {
        "total_korn_kg": round(total_korn_kg, 2),
        "koketid_min":   koketid,
        "vann":          vann,
        "maskeplan":     maskeplan,
        "humleplan":     humleplan,
        "gjaer_navn":    gjaer_info.get("display_name", gjaer_id),
        "pakker":        pakker,
        "temp_min":      temp_min,
        "temp_maks":     temp_maks,
        "noter":         noter,
        "er_lager":      gjaer_key == "lager",
    }
