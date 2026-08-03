"""Minimal testvert for å rendre ui.smart_shopping_list_panel sin
_render_malt_pakningsforslag() isolert i «bestill til eksakt mål»-modus
(Steg F3) — UTEN Pantry, oppskrift eller ekte masterdata. Tester kun selve
rendringen av et allerede ferdigbygget kjøpsresultat-objekt.

Se tests/_normal_pakningsforslag_render_app.py for normalmodus-varianten —
holdt i EGNE app-filer (ikke samme kjøring) slik at testene kan sjekke at
eksakt-mål-teksten ALDRI lekker inn i normalmodus-rendringen uten risiko
for å blande widget-utdata fra to seksjoner i samme kjøring.

Ikke en del av selve applikasjonen, og plukkes ikke opp av
`unittest discover` (matcher ikke test*.py)."""
import streamlit as st
from ui.smart_shopping_list_panel import _render_malt_pakningsforslag

_EKSAKT_MAL_FORSLAG = {
    "anbefalt_kombinasjon": {
        "antall_pakninger": [
            {"pakningsstorrelse_gram": 1000, "antall": 1},
            {"pakningsstorrelse_gram": 100, "antall": 3},
        ],
        "total_gram": 1300.0,
        "malttype": "knust",
        "overkjop_gram": 70.0,
        "total_pris": 75.0,
    },
    "alternative_kombinasjoner": [],
    "advarsel": None,
    "kjopsresultat": {
        "pris": 75.0,
        "mottatt_mengde": 1230.0,
        "bestilling": {
            "pakninger": [
                {"pakningsstorrelse_gram": 1000, "antall": 1},
                {"pakningsstorrelse_gram": 100, "antall": 3},
            ],
            "eksakt_onsket_mengde_gram": 1230.0,
        },
    },
}

_render_malt_pakningsforslag(_EKSAKT_MAL_FORSLAG)
