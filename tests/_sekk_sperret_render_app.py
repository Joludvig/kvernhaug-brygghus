"""Minimal testvert for å rendre ui.smart_shopping_list_panel sin
_render_malt_pakningsforslag() isolert for Steg F5-sperren — når den
anbefalte kombinasjonen inneholder en hel 25 kg-sekk, skal kjøpsresultatet
falle tilbake til den ORDINÆRE (ikke-eksakte) kontrakten, selv om brukeren
har krysset av for eksakt mål. "bestilling" er derfor en vanlig, flat liste
her (nøyaktig som modules/malt_packaging.py faktisk returnerer i dette
tilfellet, se _kjopsresultat_fra_kombinasjon()), UTEN
"eksakt_onsket_mengde_gram" — testene bekrefter at
_render_eksakt_mal_instruks() dermed ikke viser noen instruks.

Ikke en del av selve applikasjonen, og plukkes ikke opp av
`unittest discover` (matcher ikke test*.py)."""
import streamlit as st
from ui.smart_shopping_list_panel import _render_malt_pakningsforslag

_SEKK_SPERRET_FORSLAG = {
    "anbefalt_kombinasjon": {
        "antall_pakninger": [
            {"pakningsstorrelse_gram": 25000, "antall": 1},
        ],
        "total_gram": 25000.0,
        "malttype": "knust",
        "overkjop_gram": 2000.0,
        "total_pris": 700.0,
    },
    "alternative_kombinasjoner": [],
    "advarsel": None,
    "kjopsresultat": {
        "pris": 700.0,
        "mottatt_mengde": 25000.0,
        "bestilling": [
            {"pakningsstorrelse_gram": 25000, "antall": 1},
        ],
    },
}

_render_malt_pakningsforslag(_SEKK_SPERRET_FORSLAG)
