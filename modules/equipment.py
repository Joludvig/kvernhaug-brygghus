# modules/equipment.py
import json
import os

from config import DEMO_MODE

_EQUIPMENT_FILE = os.path.join("data", "equipment.json")

DEFAULTS = {
    "efficiency": 0.75,
    "boil_off_l_per_hour": 4.0,
    "grain_absorption_l_per_kg": 1.0,
    "dead_space_l": 2.0,
    "mash_ratio_l_per_kg": 3.2,
    "kettle_capacity_l": 35.0,
    "default_boil_time_min": 60,
}


def last_equipment() -> dict:
    """Load equipment profile from disk. Falls back to BrewZilla 35L defaults on any error."""
    try:
        with open(_EQUIPMENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def lagre_equipment(data: dict) -> None:
    """Persist equipment profile to disk. No-op i DEMO_MODE -- samme
    mønster som modules/recipe_storage.py, modules/pantry.py og
    modules/humle_lager.py."""
    if DEMO_MODE:
        return
    os.makedirs("data", exist_ok=True)
    with open(_EQUIPMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
