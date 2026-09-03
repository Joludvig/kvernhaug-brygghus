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


def _equipment_file():
    """Aktiv equipment-fil -- lest FRISKT ved hvert kall, aldri frosset i
    en modulnivå-konstant (samme begrunnelse som
    modules/recipe_storage.py::_mappe(): en tidlig-frosset os.getenv()-
    verdi kan bli lest FØR en test rekker å sette miljøvariabelen).

    KVERNHAUG_EQUIPMENT_FILE finnes KUN for testisolasjon (PRI 3B2) --
    lar en AppTest-harness peke last_equipment()/
    equipment_kilde_er_lagret() mot en midlertidig fil i stedet for den
    ekte data/equipment.json."""
    return os.getenv("KVERNHAUG_EQUIPMENT_FILE", _EQUIPMENT_FILE)


def last_equipment() -> dict:
    """Load equipment profile from disk. Falls back to BrewZilla 35L defaults on any error."""
    try:
        with open(_equipment_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULTS, **data}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return dict(DEFAULTS)


def equipment_kilde_er_lagret() -> bool:
    """True KUN hvis en gyldig utstyrsprofil faktisk er lagret på disk --
    False hvis filen mangler eller er korrupt, altså akkurat situasjonen
    der last_equipment() stille faller tilbake til DEFAULTS uten at
    kalleren kan se forskjellen (Chief review, PR #30 blocker 3: en
    .kbhbrew-opprettelse skal aldri fryse en ubekreftet default-profil
    som om den var brukerens faktiske utstyr). Leser IKKE `data`-
    innholdet -- kun om filen finnes og er gyldig JSON."""
    try:
        with open(_equipment_file(), "r", encoding="utf-8") as f:
            json.load(f)
        return True
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False


def lagre_equipment(data: dict) -> None:
    """Persist equipment profile to disk. No-op i DEMO_MODE -- samme
    mønster som modules/recipe_storage.py, modules/pantry.py og
    modules/humle_lager.py."""
    if DEMO_MODE:
        return
    filsti = _equipment_file()
    mappe = os.path.dirname(filsti)
    if mappe:
        os.makedirs(mappe, exist_ok=True)
    with open(filsti, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
