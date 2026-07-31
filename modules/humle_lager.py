import json
import math
import os
from config import DEMO_MODE

_LAGER_FIL = "data/humle_lager.json"
_FALLBACK_PAKKE_GRAM = 100.0


def les_lager() -> dict:
    """Leser data/humle_lager.json. Returnerer alltid {} i DEMO_MODE UTEN å
    røre disken -- dette er brukerens ekte, private lagerdata og skal
    aldri leses inn i en demo-økt (se ui/humle_lager_panel.py, som i
    stedet bruker en egen, session-scoped demo-versjon via
    ui/demo_state.py)."""
    if DEMO_MODE:
        return {}
    if not os.path.exists(_LAGER_FIL):
        return {}
    try:
        with open(_LAGER_FIL, encoding="utf-8") as f:
            data = json.load(f)
        return {k: float(v) for k, v in data.items() if isinstance(v, (int, float)) and v >= 0}
    except (json.JSONDecodeError, IOError):
        return {}


def lagre_lager(lager: dict) -> None:
    if DEMO_MODE:
        return
    os.makedirs("data", exist_ok=True)
    with open(_LAGER_FIL, "w", encoding="utf-8") as f:
        json.dump(lager, f, ensure_ascii=False, indent=2)


def beregn_status(valgt_humle, lager, humle_db=None, butikk_nokkel=None) -> dict:
    """
    Summerer gram per humle-ID på tvers av alle tilsettinger og sammenligner mot lager.

    Returnerer dict: { humle_id: { trenger, hjemme, mangler, kjop, rest } }
      - kjop = 0 hvis mangler == 0, ellers rundet opp til nærmeste pakke
      - rest = hjemme + kjop - trenger (alltid >= 0)
    """
    trenger_per_id: dict[str, float] = {}
    for h in valgt_humle:
        h_id = h["id"]
        trenger_per_id[h_id] = trenger_per_id.get(h_id, 0.0) + float(h["gram"])

    resultat = {}
    for h_id, trenger in trenger_per_id.items():
        hjemme = lager.get(h_id, 0.0)
        mangler = max(0.0, trenger - hjemme)

        kjop = 0.0
        if mangler > 0:
            pakke = _FALLBACK_PAKKE_GRAM
            if humle_db and butikk_nokkel:
                bm = humle_db.get(h_id, {}).get("butikk_match", {}).get(butikk_nokkel, {})
                pakke = float(bm.get("pakke_gram") or _FALLBACK_PAKKE_GRAM)
            kjop = math.ceil(mangler / pakke) * pakke

        rest = hjemme + kjop - trenger

        resultat[h_id] = {
            "trenger": trenger,
            "hjemme": hjemme,
            "mangler": mangler,
            "kjop": kjop,
            "rest": rest,
        }

    return resultat
