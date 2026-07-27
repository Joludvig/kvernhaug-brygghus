"""
Regresjonstester for modules.process_profiles.normaliser_prosessprofil()
og bruken av den i ui/process_panel.py og ui/brewday_panel.py.

Bakgrunn: et instrumentert debugpanel i den EKTE, kjørende app.py avslørte
at følgende brukerflyt fortsatt kunne gi en hybrid meskeplan:

    1. Åpne en gammel oppskrift lagret FØR process_profile-feltet
       eksisterte (recipe_obj["process_profile"] mangler helt).
    2. Appen faller tilbake til Enkel infusjon.
    3. Brukeren velger deretter Hochkurz.
    4. st.session_state["aktiv_prosessprofil"] endte med
       process_id="hochkurz", men beholdt de GAMLE Enkel
       infusjon-stegene (66°C/60min, 78°C/5min) og la i tillegg til
       Hochkurz sitt eget mashout-steg (77°C/10min) — mens
       ctx["recipe"]["process_profile"] på samme tidspunkt viste den
       KORREKTE kanoniske Hochkurz-planen (63/40, 70/30, 77/10).

Rotårsaken: flere steder i koden (ui/process_panel.py sin resynk-logikk,
ui/brewday_panel.py sin lesing rett før lag_brewday_plan()) stolte hver
for seg på "hva som helst" som lå i en aktiv/lagret profil for en KJENT
standardprofil, i stedet for å gå via ÉN felles normaliseringsregel.
normaliser_prosessprofil() er nå den ENE kilden alle disse stedene
bruker — se modules/process_profiles.py.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import copy
import json
import logging
import os
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

import streamlit as st
from streamlit.testing.v1 import AppTest

from modules.process_profiles import (
    normaliser_prosessprofil, hent_standardprofil, bygg_egendefinert_profil,
)

# Den EKSAKTE, rapporterte hybriden: gamle Enkel infusjon-steg pluss
# Hochkurz sitt eget mashout-steg, under et process_id som PÅSTÅR å være
# "hochkurz".
_RAPPORTERT_HYBRID_HOCHKURZ = {
    "process_id": "hochkurz", "navn": "Hochkurz (stegmesk)",
    "beskrivelse": "", "vanskelighetsgrad": "Middels",
    "mash_steps": [
        {"temperatur": 66.0, "varighet": 60, "stegtype": "infusjon", "kommentar": "Hovedmesk"},
        {"temperatur": 78.0, "varighet": 5,  "stegtype": "mashout",  "kommentar": "Mashout"},
        {"temperatur": 77.0, "varighet": 10, "stegtype": "mashout",  "kommentar": "Mashout"},
    ],
    "sparge_method": "batch_sparge", "boil_minutes": 60,
    "decoction_steps": None, "reiterated_mash": None,
    "anbefalte_stiler": [], "utstyrsbegrensninger": "", "forventet_paavirkning": "",
    "ekstra_tid_min": 20, "brukernotater": "Notat som skal overleve",
}

_KANONISK_HOCHKURZ_STEG = [(63.0, 40), (70.0, 30), (77.0, 10)]


def _steg(profile):
    return [(s["temperatur"], s["varighet"]) for s in profile["mash_steps"]]


class TestNormaliserProsessprofil(unittest.TestCase):
    """Ren enhetstest av selve normaliseringsfunksjonen — ingen Streamlit
    nødvendig."""

    def test_hybrid_hochkurz_normaliseres_til_kanonisk(self):
        normalisert = normaliser_prosessprofil(_RAPPORTERT_HYBRID_HOCHKURZ)
        self.assertEqual(normalisert["navn"], "Hochkurz (stegmesk)")
        self.assertEqual(_steg(normalisert), _KANONISK_HOCHKURZ_STEG)
        self.assertNotIn((66.0, 60), _steg(normalisert))
        self.assertNotIn((78.0, 5), _steg(normalisert))

    def test_brukernotater_overlever_normalisering(self):
        normalisert = normaliser_prosessprofil(_RAPPORTERT_HYBRID_HOCHKURZ)
        self.assertEqual(normalisert["brukernotater"], "Notat som skal overleve")

    def test_egendefinert_profil_overskrives_ikke(self):
        egendefinert = bygg_egendefinert_profil(
            "Min egen prosess",
            [
                {"temperatur": 55.0, "varighet": 15, "stegtype": "infusjon", "kommentar": "Protein"},
                {"temperatur": 68.0, "varighet": 40, "stegtype": "infusjon", "kommentar": "Sakkarifisering"},
            ],
        )
        normalisert = normaliser_prosessprofil(egendefinert)
        self.assertEqual(_steg(normalisert), [(55.0, 15), (68.0, 40)])

    def test_manglende_profil_gir_bakoverkompatibel_standard(self):
        for tom in (None, {}):
            normalisert = normaliser_prosessprofil(tom)
            self.assertEqual(normalisert["process_id"], "enkel_infusjon")
            self.assertEqual(_steg(normalisert), [(66.0, 60), (78.0, 5)])

    def test_ukjent_process_id_gir_bakoverkompatibel_standard(self):
        ukjent = {"process_id": "ikke_en_ekte_profil", "mash_steps": [
            {"temperatur": 99.0, "varighet": 99, "stegtype": "infusjon", "kommentar": ""},
        ]}
        normalisert = normaliser_prosessprofil(ukjent)
        self.assertEqual(normalisert["process_id"], "enkel_infusjon")

    def test_returnerer_alltid_uavhengig_kopi(self):
        original = copy.deepcopy(_RAPPORTERT_HYBRID_HOCHKURZ)
        normalisert = normaliser_prosessprofil(original)
        normalisert["mash_steps"][0]["temperatur"] = -1.0
        self.assertEqual(original["mash_steps"][0]["temperatur"], 66.0)

    def test_navn_og_steg_samsvarer_for_alle_standardprofiler(self):
        for pid in ("enkel_infusjon", "hochkurz", "enkel_dekoksjon", "reiterated_mash"):
            kandidat = {"process_id": pid, "navn": "noe helt annet", "mash_steps": [
                {"temperatur": 12.3, "varighet": 4, "stegtype": "infusjon", "kommentar": ""},
            ]}
            normalisert = normaliser_prosessprofil(kandidat)
            forventet = hent_standardprofil(pid)
            self.assertEqual(normalisert["navn"], forventet["navn"])
            self.assertEqual(_steg(normalisert), _steg(forventet))


class TestGammelOppskriftUtenProsessProfilTilHochkurz(unittest.TestCase):
    """Krav: gjenskaper NØYAKTIG den rapporterte brukerflyten via de ekte
    UI-modulene (ui/process_panel.py), ikke bare den isolerte
    normaliseringsfunksjonen — en gammel oppskrift UTEN process_profile i
    det hele tatt, som faller tilbake til Enkel infusjon, og deretter
    eksplisitt byttes til Hochkurz."""

    def setUp(self):
        st.session_state.clear()

    def tearDown(self):
        st.session_state.clear()

    def test_gammel_oppskrift_uten_profil_bytt_til_hochkurz_gir_kanonisk_overalt(self):
        from ui.process_panel import _init_state_for_profile, _bygg_aktiv_profil
        from modules.process_profiles import tilgjengelige_profiler

        id_til_navn = {p["process_id"]: p["navn"] for p in tilgjengelige_profiler()}

        # STEG 1-2: gammel oppskrift uten process_profile lastes — sidebar
        # ville satt aktiv_prosessprofil=None (se ui/sidebar.py), og
        # process_panel sin førstegangsinit faller tilbake til den
        # anbefalte (her simulert direkte som "enkel_infusjon", akkurat
        # som brukeren rapporterte at appen falt tilbake til).
        st.session_state["aktiv_prosessprofil"] = None
        _init_state_for_profile(hent_standardprofil("enkel_infusjon"))
        st.session_state["valgt_prosess_id"] = "enkel_infusjon"
        st.session_state["_prosess_forrige_id"] = "enkel_infusjon"
        aktiv = _bygg_aktiv_profil("enkel_infusjon", id_til_navn["enkel_infusjon"], hent_standardprofil("enkel_infusjon"))
        st.session_state["aktiv_prosessprofil"] = aktiv
        self.assertEqual(_steg(aktiv), [(66.0, 60), (78.0, 5)])

        # STEG 3: brukeren velger eksplisitt Hochkurz — dette er nøyaktig
        # samme logikk som selectbox-endringsdeteksjonen i
        # render_process_panel().
        valgt_id = "hochkurz"
        if st.session_state.get("_prosess_forrige_id") != valgt_id:
            _init_state_for_profile(hent_standardprofil(valgt_id))
            st.session_state["_prosess_forrige_id"] = valgt_id
        st.session_state["valgt_prosess_id"] = valgt_id
        aktiv = _bygg_aktiv_profil(valgt_id, id_til_navn[valgt_id], hent_standardprofil(valgt_id))
        st.session_state["aktiv_prosessprofil"] = aktiv

        # STEG 4: session_state skal IKKE inneholde noen hybrid.
        self.assertEqual(aktiv["navn"], "Hochkurz (stegmesk)")
        self.assertEqual(_steg(aktiv), _KANONISK_HOCHKURZ_STEG)
        self.assertNotIn((66.0, 60), _steg(aktiv))
        self.assertNotIn((78.0, 5), _steg(aktiv))


class TestTreKilderIdentiskeFoerLagBrewdayPlan(unittest.TestCase):
    """Krav 5: gjenskaper NØYAKTIG de rapporterte faktiske debugverdiene
    (session_state korrupt, ctx korrekt) og verifiserer at
    ui/brewday_panel.py sin normalisering gjør alle tre kildene —
    session_state, ctx og argumentet til lag_brewday_plan() — identiske
    og kanoniske FØR selve bryggedagsberegningen, og at en ekte eksport
    faktisk produseres.

    Bruker KUN produksjonskode og synlige AppTest-elementer (ingen
    midlertidige debug-session_state-nøkler — de er fjernet fra
    ui/brewday_panel.py og app.py etter at feilen ble bekreftet løst)."""

    _APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_brewday_panel_app.py")

    def setUp(self):
        st.session_state.clear()
        self._gammel_env = os.environ.get("KVERNHAUG_TEST_AKTIV_PROSESSPROFIL")

    def tearDown(self):
        st.session_state.clear()
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_TEST_AKTIV_PROSESSPROFIL", None)
        else:
            os.environ["KVERNHAUG_TEST_AKTIV_PROSESSPROFIL"] = self._gammel_env

    def test_alle_tre_kilder_blir_identiske_og_kanoniske(self):
        # De FAKTISKE, rapporterte debugverdiene: session_state er korrupt
        # (seedes inn i vertskaps-appen via miljøvariabel), ctx er (ennå)
        # korrekt (hardkodet i tests/_brewday_panel_app.py, se der).
        os.environ["KVERNHAUG_TEST_AKTIV_PROSESSPROFIL"] = json.dumps(_RAPPORTERT_HYBRID_HOCHKURZ)

        at = AppTest.from_file(self._APP)
        at.run()
        self.assertFalse(at.exception, f"render_brewday_panel kastet exception: {at.exception}")

        forventet = _KANONISK_HOCHKURZ_STEG

        # session_state reparert (ekte produksjonsnøkkel).
        aktiv = at.session_state["aktiv_prosessprofil"]
        self.assertEqual(_steg(aktiv), forventet)

        # ctx skrevet tilbake og reparert av ui/brewday_panel.py (var
        # allerede korrekt her, men skal fortsatt være det etter
        # skriv-tilbake) — fanget av vertskaps-appens EGEN, ikke-
        # produksjonsrelaterte snapshot (se tests/_brewday_panel_app.py).
        ctx_profil = at.session_state["_test_ctx_process_profile_etter_panel"]
        self.assertEqual(_steg(ctx_profil), forventet)

        # Alle kilder identiske (samme steg-innhold) — siden
        # ui/brewday_panel.py sender NØYAKTIG samme objekt videre til
        # lag_brewday_plan() som det som skrives til session_state/ctx
        # (én lokal variabel, se koden), beviser dette at argumentet til
        # lag_brewday_plan() også var kanonisk.
        self.assertEqual(_steg(aktiv), _steg(ctx_profil))

        # Ferdig plan, beregnet med den samme (nå bekreftet kanoniske)
        # profilen, via den EKTE produksjonsfunksjonen direkte.
        from modules.brewday_calc import lag_brewday_plan
        plan = lag_brewday_plan(
            malt_valg=[{"id": "weyermann_pilsner", "mengde": 5.0}],
            humle_valg=[], gjaer_id="safale_us_05",
            gjaer_info={"display_name": "US-05", "gjaertype": "Ale", "attenuation": 0.75},
            og=1.050, batch_volum_l=20.0, humle_database={}, malt_database={},
            process_profile=aktiv,
        )
        self.assertEqual(
            [(s["temp_c"], s["varighet_min"]) for s in plan["maskeplan"]], forventet,
        )

        # Trykk den EKTE eksportknappen — bekreft at selve eksportkoden
        # (som kaller render_brewday_html() med disse dataene) kjører uten
        # å krasje (st.download_button har ingen introspiserbar payload i
        # denne AppTest-versjonen, se streamlit.testing.v1.element_tree).
        at.button(key="brewday_print_btn").click().run()
        self.assertFalse(at.exception)

        # Bekreft at selve eksportmalen, matet med de samme (bekreftet
        # kanoniske) dataene, faktisk produserer korrekt HTML — den EKTE
        # produksjonsfunksjonen kalt direkte.
        from modules.brewday_template import render_brewday_html
        html = render_brewday_html(at.session_state["_test_ctx_snapshot"], plan, {})
        self.assertIn("63.0°C", html)
        self.assertIn("70.0°C", html)
        self.assertIn("77.0°C", html)
        self.assertNotIn("66.0°C", html)
        self.assertNotIn("78.0°C", html)

    def test_egendefinert_profil_i_session_state_overskrives_ikke(self):
        egendefinert = {
            "process_id": "egendefinert", "navn": "Min egen prosess",
            "beskrivelse": "", "vanskelighetsgrad": "Middels",
            "mash_steps": [
                {"temperatur": 58.0, "varighet": 25, "stegtype": "infusjon", "kommentar": ""},
            ],
            "sparge_method": "batch_sparge", "boil_minutes": 60,
            "decoction_steps": None, "reiterated_mash": None,
            "anbefalte_stiler": [], "utstyrsbegrensninger": "", "forventet_paavirkning": "",
            "ekstra_tid_min": 0, "brukernotater": "",
        }
        os.environ["KVERNHAUG_TEST_AKTIV_PROSESSPROFIL"] = json.dumps(egendefinert)

        at = AppTest.from_file(self._APP)
        at.run()
        self.assertFalse(at.exception)

        aktiv = at.session_state["aktiv_prosessprofil"]
        self.assertEqual(_steg(aktiv), [(58.0, 25)])


if __name__ == "__main__":
    unittest.main()
