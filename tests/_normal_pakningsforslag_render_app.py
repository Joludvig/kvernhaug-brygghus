"""Minimal testvert for å rendre ui.smart_shopping_list_panel sin
_render_malt_pakningsforslag() isolert i NORMALMODUS (dvs. samme
kjøpsresultat-form som før Steg F3 innførte «bestill til eksakt mål»),
UTEN Pantry, oppskrift eller ekte masterdata.

Se tests/_eksakt_mal_render_app.py for eksakt-mål-varianten. Holdt i egen
fil, ikke samme kjøring, slik testene aldri risikerer å blande widget-
utdata fra begge modiene i samme AppTest-resultat.

Ikke en del av selve applikasjonen, og plukkes ikke opp av
`unittest discover` (matcher ikke test*.py)."""
from ui.smart_shopping_list_panel import _render_malt_pakningsforslag

_NORMAL_FORSLAG = {
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
        "mottatt_mengde": 1300.0,
        "bestilling": [
            {"pakningsstorrelse_gram": 1000, "antall": 1},
            {"pakningsstorrelse_gram": 100, "antall": 3},
        ],
    },
}

_render_malt_pakningsforslag(_NORMAL_FORSLAG)
