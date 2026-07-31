# ui/demo_state.py
"""
Session-scoped datalag for DEMO_MODE.

Pantry, vannkjemi, utstyrsprofil og det gamle humlelageret skal oppleves
akkurat som i fullversjonen i demo-modus: brukeren skal kunne legge til,
endre og "lagre" ting og faktisk SE endringen i UI-et — men ingenting skal
noensinne skrives til disk, og ingen ekte private data (data/pantry.json,
data/equipment.json, data/humle_lager.json) skal noensinne leses inn.

Dette laget holder derfor en midlertidig kopi i st.session_state (varer
kun så lenge nettleserøkten varer) i stedet for å kalle de virkelige
last_*()/lagre_*()-funksjonene i modules/ for disse fire tingene.

modules/pantry.py, modules/water_chemistry.py, modules/equipment.py og
modules/humle_lager.py forblir upåvirket av dette laget og importerer
aldri streamlit selv (se deres egne moduldocstrings) — dette laget bor
bevisst i ui/ og kalles KUN når config.DEMO_MODE er True. Utenfor
DEMO_MODE går alle paneler fortsatt rett på de virkelige
modules/-funksjonene, helt uendret.

Vannkilder/-mål er et unntak fra "aldri les ekte fil": data/water_sources.json
og data/water_targets.json er delt, git-versjonert referansedata (Jordalsvatnet
2025 og de innebygde målprofilene) -- ikke privat brukerdata -- så de brukes
bevisst som utgangspunkt (kopiert inn i økten ÉN gang), akkurat som i
fullversjonen. Selve skrivingen er likevel alltid session-scoped i demo.
"""
import copy
import json
import os

import streamlit as st

from modules import equipment as _equipment
from modules import pantry as _pantry
from modules import water_chemistry as _water

_EKSEMPEL_PANTRY_FIL = os.path.join("data", "pantry.example.json")

_EKSEMPEL_HUMLELAGER = {"citra": 150.0, "cascade": 80.0, "east_kent_goldings": 40.0}


def _hent(nokkel, fabrikk):
    """Henter en session-scoped demo-verdi, og seeder den (via `fabrikk`,
    kalt maks én gang per økt) første gang nøkkelen etterspørres i denne
    nettleserøkten."""
    full_nokkel = f"_demo_{nokkel}"
    if full_nokkel not in st.session_state:
        st.session_state[full_nokkel] = fabrikk()
    return st.session_state[full_nokkel]


def _sett(nokkel, verdi):
    st.session_state[f"_demo_{nokkel}"] = verdi


# ── Pantry ───────────────────────────────────────────────────────────────
def _pantry_eksempel():
    """Demo-lager seedet fra data/pantry.example.json (git-versjonert
    eksempeldata) -- ALDRI fra brukerens ekte data/pantry.json, som aldri
    leses i demo-modus. Faller trygt tilbake til et tomt, gyldig lager hvis
    eksempelfilen mot formodning mangler eller er korrupt."""
    try:
        with open(_EKSEMPEL_PANTRY_FIL, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"schema_version": _pantry.SCHEMA_VERSION, "updated_at": None, "items": []}
    return _pantry.migrer_pantry_schema(copy.deepcopy(data))


def hent_pantry():
    return _hent("pantry", _pantry_eksempel)


def lagre_pantry(data):
    _sett("pantry", data)


# ── Gammelt humlelager (legacy) ────────────────────────────────────────────
def hent_gammelt_humlelager():
    return _hent("humle_lager", lambda: dict(_EKSEMPEL_HUMLELAGER))


def lagre_gammelt_humlelager(lager):
    _sett("humle_lager", lager)


# ── Vannkjemi ────────────────────────────────────────────────────────────
def hent_vannkilder():
    return _hent("vannkilder", lambda: copy.deepcopy(_water.last_vannkilder()))


def lagre_vannkilder(kilder):
    _sett("vannkilder", kilder)


def hent_vannmaal():
    return _hent("vannmaal", lambda: copy.deepcopy(_water.last_vannmaal()))


def lagre_vannmaal(maalprofiler):
    _sett("vannmaal", maalprofiler)


# ── Utstyrsprofil ────────────────────────────────────────────────────────
def hent_equipment():
    return _hent("equipment", lambda: dict(_equipment.DEFAULTS))


def lagre_equipment(data):
    _sett("equipment", data)
