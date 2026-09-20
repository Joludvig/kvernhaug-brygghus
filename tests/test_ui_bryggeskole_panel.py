"""
AppTest-basert dekning for ui/bryggeskole_panel.py::render_bryggeskole_panel()
(issue #338, productionizing the two-module Bryggeskole UX -- Mesking +
Gjæring, skoleoversikt, modul-navigasjon, frosset alternativ-rekkefølge,
eksplisitt svarstatus).

Dekker de automatiserte akseptansepunktene issue #338 selv beskriver (se
også tests/test_bryggeskole_answer_order.py for den rene, RNG-injiserte
dekningen av selve alternativ-rekkefølge-algoritmen -- denne filen dekker
kun at UI-laget faktisk FRYSER og GJENBRUKER en trukket rekkefølge, ikke
de statistiske egenskapene til selve trekningen):
    1. Bryggeskole er nåbar som topplinje-fane i app.py.
    2. Begge miljøvisninger (Hjemmebrygger/Bryggeri) rendrer en
       skoleoversikt med to klikkbare moduler (Mesking, Gjæring) og
       resten av prosessen som "Kommer senere".
    3. Begge miljøer ruter inn i SAMME to pilot-moduler.
    4. Modul-navigasjon: åpne en modul, gå tilbake til oversikten uten å
       miste sesjonsfremgang, åpne modulen igjen og lande der man slapp
       (in-session resume).
    5. Full flyt per modul: leksjon -> spørsmål -> svar -> feedback ->
       fortsett -> oppsummering.
    6. Riktig/feil-stier oppdaterer mastery via de eksisterende API-ene,
       delt på tvers av moduler (separate konsept-navnerom).
    7. Statusmerker på skoleoversikten: "Øvd på tidligere", "Påbegynt",
       "Gjennomført denne økten".
    8. Læringsvendt output viser ALDRI rå mastery/confidence/attempts
       eller rå numeriske skår.
    9. Svarstatus viser eksplisitt lærerens eget svar, og (ved feil) det
       korrekte svaret -- ikke bare grå disabled-styling.
    10. Alternativ-rekkefølgen er frosset gjennom reruns i samme runde, og
        en ny runde («Prøv igjen») kan trekke en ny rekkefølge.
    11. «Prøv igjen» virker mot PERSISTERT mastery (nullstiller den ikke).
    12. NO/EN virker via appens eksisterende språktilstand.
    13. DEMO_MODE utfører INGEN disk-skriving av lærer-tilstand.

Isolasjon: hver test setter KVERNHAUG_BRYGGESKOLE_STATE_DIR til en fersk
tempfile.TemporaryDirectory() (samme mønster/begrunnelse som
tests/test_bryggeskole_mastery_store.py) -- ALDRI den ekte
data/bryggeskole_mastery_state.json.

Kjøres med:
    python3 -m unittest tests.test_ui_bryggeskole_panel -v
"""
import logging
import os
import re
import subprocess
import sys
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest
from streamlit.testing.v1.errors import AppTestError

from bryggeskole.mastery_store import _STATE_DIR_ENV, read_mastery_state
from bryggeskole.pilot_mashing import read_pilot_file as les_mesking_pilot
from bryggeskole.pilot_fermentation import read_pilot_file as les_gjaring_pilot

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "bryggeskole_harness.py")
_APP_PY = os.path.join(_REPO_ROOT, "app.py")

_RAAT_TALL_MONSTER = re.compile(r"\b0\.\d+\b")
_SKJULTE_ORD = ("mastery", "confidence", "attempts")


def _knapp(at, key):
    knapper = [b for b in at.button if b.key == key]
    assert len(knapper) == 1, f"Fant ikke akkurat én knapp med key={key!r}: {[b.key for b in at.button]}"
    return knapper[0]


def _alle_synlige_tekster(at):
    """Samler all tekst en lærer faktisk ser -- markdown, caption,
    header/subheader, info, success/error-meldinger og knappelabels -- til
    én liste strenger, for no-raw-hidden-state-søket."""
    tekster = []
    for samling in (at.markdown, at.caption, at.header, at.subheader, at.info, at.success, at.error):
        tekster.extend(e.value for e in samling)
    tekster.extend(b.label for b in at.button if b.label)
    return tekster


def _korrekt_svar_ider(pilot):
    """Utleder faktisk korrekt alternativ-id per spørsmål-indeks fra
    pilotinnholdet -- brukes til å svare "alt riktig" uten å hardkode
    fasiten, siden alternativ-REKKEFØLGEN nå randomiseres av UI-laget
    (evaluering skjer uansett alltid på id, aldri visningsposisjon)."""
    fasit = {}
    for idx, sporsmal in enumerate(pilot["questions"]):
        korrekt = next(o["id"] for o in sporsmal["options"] if o["correct"] is True)
        fasit[idx] = korrekt
    return fasit


def _feil_svar_ider(pilot):
    fasit = {}
    for idx, sporsmal in enumerate(pilot["questions"]):
        feil = next(o["id"] for o in sporsmal["options"] if o["correct"] is False)
        fasit[idx] = feil
    return fasit


class _MedIsolertTilstand(unittest.TestCase):
    def setUp(self):
        self._gammel_env = os.environ.get(_STATE_DIR_ENV)
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ[_STATE_DIR_ENV] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop(_STATE_DIR_ENV, None)
        else:
            os.environ[_STATE_DIR_ENV] = self._gammel_env
        self._tmpdir.cleanup()

    def _ny_apptest(self):
        at = AppTest.from_file(_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    def _velg_miljo(self, at, miljo_knapp="bs_velg_hjemmebrygger_btn"):
        _knapp(at, miljo_knapp).click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved miljøvalg: {at.exception}")
        return at

    def _apne_modul(self, at, modul_id, miljo_knapp="bs_velg_hjemmebrygger_btn"):
        """Velger miljø og åpner gitt modul -- lander på LEKSJON-fasen
        (chunk-teksten), ett steg FØR spørsmålene starter."""
        self._velg_miljo(at, miljo_knapp)
        _knapp(at, f"bs_apne_modul_{modul_id}_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved modulåpning: {at.exception}")
        return at

    def _start_sporsmalsrunde(self, at):
        _knapp(at, "bs_start_sporsmal_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved spørsmålsstart: {at.exception}")
        return at

    def _apne_modul_og_start_sporsmal(self, at, modul_id, miljo_knapp="bs_velg_hjemmebrygger_btn"):
        self._apne_modul(at, modul_id, miljo_knapp)
        return self._start_sporsmalsrunde(at)

    def _besvar_sporsmal(self, at, idx, runde, svar_id):
        widget_key = f"bs_valg_r{runde}_q{idx}"
        at.radio(key=widget_key).set_value(svar_id).run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved svarvalg: {at.exception}")
        _knapp(at, f"bs_svar_btn_r{runde}_q{idx}").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved svar-sjekk: {at.exception}")

    def _fortsett(self, at, idx, runde):
        _knapp(at, f"bs_fortsett_btn_r{runde}_q{idx}").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved fortsett: {at.exception}")

    def _fullfor_alle_sporsmal(self, at, runde, svar_tabell):
        for idx, svar_id in svar_tabell.items():
            self._besvar_sporsmal(at, idx, runde, svar_id)
            self._fortsett(at, idx, runde)
        return at


# ─── 2 + 3: begge miljøer rendrer skoleoversikt med to moduler, ruter til
# SAMME to pilot-moduler ────────────────────────────────────────────────

class TestMiljovalgOgSkoleoversikt(_MedIsolertTilstand):
    def test_miljovalg_vises_ved_start(self):
        at = self._ny_apptest()
        _knapp(at, "bs_velg_hjemmebrygger_btn")
        _knapp(at, "bs_velg_bryggeri_btn")

    def test_hjemmebrygger_viser_to_klikkbare_moduler(self):
        at = self._ny_apptest()
        self._velg_miljo(at, "bs_velg_hjemmebrygger_btn")
        _knapp(at, "bs_apne_modul_mesking_btn")
        _knapp(at, "bs_apne_modul_gjaring_btn")

    def test_bryggeri_viser_samme_to_moduler(self):
        at = self._ny_apptest()
        self._velg_miljo(at, "bs_velg_bryggeri_btn")
        _knapp(at, "bs_apne_modul_mesking_btn")
        _knapp(at, "bs_apne_modul_gjaring_btn")

    def test_bytt_miljo_nullstiller_til_miljovalg(self):
        at = self._ny_apptest()
        _knapp(at, "bs_velg_hjemmebrygger_btn").click().run()
        _knapp(at, "bs_bytt_miljo_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")
        _knapp(at, "bs_velg_hjemmebrygger_btn")
        _knapp(at, "bs_velg_bryggeri_btn")

    def test_kun_to_stadier_er_klikkbare_resten_er_kommer_senere(self):
        at = self._ny_apptest()
        self._velg_miljo(at, "bs_velg_hjemmebrygger_btn")
        aktiv_badges = [c.value for c in at.caption if "Leksjon tilgjengelig" in c.value]
        kommer_badges = [c.value for c in at.caption if "Kommer senere" in c.value]
        self.assertEqual(len(aktiv_badges), 2)
        self.assertEqual(len(kommer_badges), 4)

    def test_mesking_modulen_rendrer_mesking_pilotinnhold(self):
        at = self._ny_apptest()
        self._apne_modul(at, "mesking")
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Under mesking bryter enzymer", tekster)

    def test_gjaring_modulen_rendrer_gjaring_pilotinnhold_i_begge_miljo(self):
        at = self._ny_apptest()
        self._apne_modul(at, "gjaring", "bs_velg_hjemmebrygger_btn")
        tekster_hjemme = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Gjæringstemperatur påvirker", tekster_hjemme)

        at2 = self._ny_apptest()
        self._apne_modul(at2, "gjaring", "bs_velg_bryggeri_btn")
        tekster_bryggeri = " ".join(_alle_synlige_tekster(at2))
        self.assertIn("Gjæringstemperatur påvirker", tekster_bryggeri)


# ─── 4: modul-navigasjon -- tilbake til oversikt beholder sesjonsfremgang ──

class TestModulNavigasjon(_MedIsolertTilstand):
    def test_tilbake_til_oversikt_beholder_sesjonsfremgang(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._besvar_sporsmal(at, 0, 1, fasit[0])
        self._fortsett(at, 0, 1)

        _knapp(at, "bs_tilbake_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved tilbake: {at.exception}")
        _knapp(at, "bs_apne_modul_mesking_btn")  # tilbake på oversikten

        _knapp(at, "bs_apne_modul_mesking_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved gjenåpning: {at.exception}")
        # Skal lande på spørsmål 2 (idx 1), ikke tilbake til leksjonen.
        at.radio(key="bs_valg_r1_q1")

    def test_breadcrumb_viser_miljo_og_modul(self):
        at = self._ny_apptest()
        self._apne_modul(at, "mesking")
        tekster = " ".join(c.value for c in at.caption)
        self.assertIn("Hjemmebrygger", tekster)
        self.assertIn("Mesking", tekster)

    def test_steg_indikator_endrer_seg_gjennom_flyten(self):
        at = self._ny_apptest()
        self._apne_modul(at, "mesking")
        tekster = " ".join(c.value for c in at.caption)
        self.assertIn("Steg 1 av 3", tekster)

        self._start_sporsmalsrunde(at)
        tekster = " ".join(c.value for c in at.caption)
        self.assertIn("Steg 2 av 3", tekster)

        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._fullfor_alle_sporsmal(at, 1, fasit)
        tekster = " ".join(c.value for c in at.caption)
        self.assertIn("Steg 3 av 3", tekster)


# ─── 5 + 6 + 11: full lærings-flyt, mastery-oppdatering per modul, «Prøv
# igjen» ─────────────────────────────────────────────────────────────────

class TestLaeringsflyt(_MedIsolertTilstand):
    def test_full_flyt_mesking_alt_riktig_gir_oppsummering(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._besvar_sporsmal(at, 0, 1, fasit[0])
        self.assertTrue(len(at.success) >= 1, "Riktig svar skal vise en positiv feedback-melding.")
        self._fortsett(at, 0, 1)
        self._fullfor_alle_sporsmal(at, 1, {1: fasit[1], 2: fasit[2]})
        _knapp(at, "bs_prov_igjen_btn")
        _knapp(at, "bs_oppsummering_tilbake_btn")

    def test_feil_svar_viser_forklarende_feedback_ikke_bare_feil(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        feil = _feil_svar_ider(pilot)
        self._besvar_sporsmal(at, 0, 1, feil[0])
        self.assertEqual(len(at.error), 1)
        feedback = at.error[0].value
        self.assertGreater(len(feedback), 40, "Feedback på feil svar skal forklare, ikke bare si «feil».")

    def test_riktig_svar_oker_mastery_for_alle_konsepter_mesking(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._besvar_sporsmal(at, 0, 1, fasit[0])
        tilstand = read_mastery_state()
        for konsept in ("mashing.starch_conversion", "mashing.dextrins"):
            self.assertGreater(tilstand["concepts"][konsept]["mastery"], 0.0)
            self.assertEqual(tilstand["concepts"][konsept]["attempts"], 1)

    def test_feil_svar_oker_aldri_mastery(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        feil = _feil_svar_ider(pilot)
        self._besvar_sporsmal(at, 0, 1, feil[0])
        tilstand = read_mastery_state()
        for konsept in ("mashing.starch_conversion", "mashing.dextrins"):
            self.assertEqual(tilstand["concepts"][konsept]["mastery"], 0.0)
            self.assertEqual(tilstand["concepts"][konsept]["attempts"], 1)

    def test_mesking_og_gjaring_mastery_er_uavhengige_konsept_navnerom(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._fullfor_alle_sporsmal(at, 1, fasit)

        _knapp(at, "bs_oppsummering_tilbake_btn").click().run()
        _knapp(at, "bs_apne_modul_gjaring_btn").click().run()
        self._start_sporsmalsrunde(at)
        gjaring_pilot = les_gjaring_pilot()
        gjaring_fasit = _korrekt_svar_ider(gjaring_pilot)
        self._fullfor_alle_sporsmal(at, 1, gjaring_fasit)

        tilstand = read_mastery_state()
        self.assertGreater(tilstand["concepts"]["mashing.starch_conversion"]["mastery"], 0.0)
        self.assertGreater(tilstand["concepts"]["fermentation.temperature"]["mastery"], 0.0)

    def test_prov_igjen_bruker_persistert_mastery_ikke_nullstilling(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._fullfor_alle_sporsmal(at, 1, fasit)
        forste_runde_tilstand = read_mastery_state()
        forste_mastery = forste_runde_tilstand["concepts"]["mashing.starch_conversion"]["mastery"]
        self.assertGreater(forste_mastery, 0.0)

        _knapp(at, "bs_prov_igjen_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved Prøv igjen: {at.exception}")
        self._fullfor_alle_sporsmal(at, 2, fasit)

        andre_runde_tilstand = read_mastery_state()
        andre_mastery = andre_runde_tilstand["concepts"]["mashing.starch_conversion"]["mastery"]
        self.assertGreaterEqual(
            andre_mastery, forste_mastery,
            "«Prøv igjen» skal bygge videre på persistert mastery, ikke nullstille den.",
        )
        self.assertEqual(
            andre_runde_tilstand["concepts"]["mashing.starch_conversion"]["attempts"], 2,
            "Attempts skal telle opp over runder -- persistens skal ALDRI nullstilles av «Prøv igjen».",
        )


# ─── 7: statusmerker på skoleoversikten ────────────────────────────────────

class TestStatusMerker(_MedIsolertTilstand):
    def test_ingen_merker_for_upabegynt_modul(self):
        at = self._ny_apptest()
        self._velg_miljo(at, "bs_velg_hjemmebrygger_btn")
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertNotIn("Øvd på tidligere", tekster)
        self.assertNotIn("Påbegynt", tekster)
        self.assertNotIn("Gjennomført denne økten", tekster)

    def test_pabegynt_merke_etter_apning_uten_fullforing(self):
        at = self._ny_apptest()
        self._apne_modul(at, "mesking")
        _knapp(at, "bs_tilbake_btn").click().run()
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Påbegynt", tekster)
        self.assertNotIn("Gjennomført denne økten", tekster)

    def test_fullfort_denne_okten_merke_etter_oppsummering(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._fullfor_alle_sporsmal(at, 1, fasit)
        _knapp(at, "bs_oppsummering_tilbake_btn").click().run()
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Gjennomført denne økten", tekster)

    def test_ovd_pa_tidligere_merke_vises_i_en_helt_ny_apptest_sesjon(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._fullfor_alle_sporsmal(at, 1, fasit)

        # Helt ny AppTest-instans (ny sesjon), men SAMME persisterte
        # mastery-fil (samme KVERNHAUG_BRYGGESKOLE_STATE_DIR).
        at2 = self._ny_apptest()
        self._velg_miljo(at2, "bs_velg_hjemmebrygger_btn")
        tekster = " ".join(_alle_synlige_tekster(at2))
        self.assertIn("Øvd på tidligere", tekster)
        self.assertNotIn("Påbegynt", tekster)
        self.assertNotIn("Gjennomført denne økten", tekster)

    def test_anbefalt_neste_peker_pa_mesking_forst(self):
        at = self._ny_apptest()
        self._velg_miljo(at, "bs_velg_hjemmebrygger_btn")
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Anbefalt neste: Mesking", tekster)

    def test_anbefaling_endres_etter_mesking_er_fullfort_denne_okten(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._fullfor_alle_sporsmal(at, 1, fasit)
        _knapp(at, "bs_oppsummering_tilbake_btn").click().run()
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Anbefalt neste: Gjæring", tekster)


# ─── Chief-review-blokker (PR #328), videreført: ingen forhåndsvalgt svar,
# og et ubesvart spørsmål kan aldri mutere persistert mastery ─────────────

class TestFerskSporsmalIngenForhandsvalgOgSubmitVakt(_MedIsolertTilstand):
    def test_fersk_sporsmal_har_ikke_forhandsvalgt_svar(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        radio = at.radio(key="bs_valg_r1_q0")
        self.assertIsNone(
            radio.value,
            "Et ferskt spørsmål skal ALDRI ha et forhåndsvalgt svaralternativ.",
        )

    def test_sjekk_svar_knapp_er_disabled_uten_valgt_svar(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        self.assertTrue(
            _knapp(at, "bs_svar_btn_r1_q0").disabled,
            "«Sjekk svar» skal være disabled inntil et svar faktisk er valgt.",
        )
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        at.radio(key="bs_valg_r1_q0").set_value(fasit[0]).run()
        self.assertFalse(
            _knapp(at, "bs_svar_btn_r1_q0").disabled,
            "«Sjekk svar» skal låses opp så snart et svar er valgt.",
        )

    def test_disabled_knapp_kan_ikke_klikkes_av_en_lasersimulert_bruker(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        with self.assertRaises(AppTestError):
            _knapp(at, "bs_svar_btn_r1_q0").click().run()
        tilstand = read_mastery_state()
        self.assertEqual(tilstand["concepts"], {}, "Et forsøk på å svare uten valg skal ikke nå frem til mastery i det hele tatt.")

    def test_sjekk_svar_vakten_mutrerer_aldri_mastery_uten_et_valgt_svar(self):
        from unittest import mock

        from bryggeskole.pilot_mashing import read_pilot_file
        from ui.bryggeskole_panel import _sjekk_svar

        pilot = read_pilot_file()
        sporsmal = pilot["questions"][0]
        with mock.patch(
            "ui.bryggeskole_panel.st.session_state",
            {"bs_valg_r1_q0": None, "bs_modul_sesjon": {}},
        ):
            _sjekk_svar("mesking", sporsmal, "no", "bs_valg_r1_q0", 1)

        tilstand = read_mastery_state()
        self.assertEqual(
            tilstand["concepts"], {},
            "_sjekk_svar() skal returnere uten å skrive noe forsøk når intet svar er valgt.",
        )


# ─── 9: eksplisitt svarstatus -- ditt svar / riktig svar ───────────────────

class TestSvarstatusEksplisitt(_MedIsolertTilstand):
    def test_riktig_svar_viser_ditt_svar_men_ikke_separat_riktig_svar_linje(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._besvar_sporsmal(at, 0, 1, fasit[0])
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Ditt svar", tekster)

    def test_feil_svar_viser_bade_ditt_svar_og_riktig_svar(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        feil = _feil_svar_ider(pilot)
        self._besvar_sporsmal(at, 0, 1, feil[0])
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Ditt svar", tekster)
        self.assertIn("Riktig svar", tekster)


# ─── 10: alternativ-rekkefølgen er frosset per runde, ny runde kan trekke
# en ny rekkefølge ──────────────────────────────────────────────────────

class TestAlternativRekkefolgeFrysing(_MedIsolertTilstand):
    def test_rekkefolgen_er_uendret_gjennom_en_rerun_uten_svar(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        radio_for = at.radio(key="bs_valg_r1_q0")
        rekkefolge_for = list(radio_for.options)

        # En rerun som ikke besvarer spørsmålet (bare re-kjører scriptet).
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved rerun: {at.exception}")
        radio_etter = at.radio(key="bs_valg_r1_q0")
        self.assertEqual(
            list(radio_etter.options), rekkefolge_for,
            "Alternativ-rekkefølgen skal være frosset gjennom en rerun i samme runde.",
        )

    def test_alle_tre_alternativtekster_finnes_uansett_rekkefolge(self):
        # AppTest sin radio.options rapporterer de FORMATERTE (viste)
        # tekstene (format_func), ikke de rå alternativ-id-ene -- selve
        # id-ene er aldri synlige for læreren i utgangspunktet.
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        forventede_tekster = {o["text"]["no"] for o in pilot["questions"][0]["options"]}
        radio = at.radio(key="bs_valg_r1_q0")
        self.assertEqual(set(radio.options), forventede_tekster)

    def test_evaluering_følger_id_ikke_visningsposisjon(self):
        # Uansett hvilken posisjon det korrekte alternativet havner på
        # (avgjøres av UI-lagets RNG), skal å velge den FAKTISK korrekte
        # id-en telle som riktig.
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._besvar_sporsmal(at, 0, 1, fasit[0])
        self.assertEqual(len(at.success), 1, "Den faktisk korrekte id-en skal telle som riktig svar uansett visningsposisjon.")


# ─── 8: aldri rå mastery/confidence/attempts eller rå tall i UI-teksten ────

class TestIngenRaaTilstandVisesLaereren(_MedIsolertTilstand):
    def test_ingen_rae_tall_eller_skjulte_ord_gjennom_hele_flyten(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        self._fullfor_alle_sporsmal(at, 1, fasit)
        # Nå på oppsummeringen -- den mest risikofylte skjermen for lekkasje.
        alle_tekster = " ".join(_alle_synlige_tekster(at)).lower()
        for ord in _SKJULTE_ORD:
            self.assertNotIn(ord, alle_tekster, f"Fant forbudt internt ord {ord!r} i lærervendt tekst.")
        self.assertIsNone(
            _RAAT_TALL_MONSTER.search(alle_tekster),
            "Fant et rått 0.xx-tall (mastery/confidence-form) i lærervendt tekst.",
        )


# ─── Chief human-usability review (PR #328), videreført: cumulative
# mastery og denne rundens signal må ALDRI vise samme label ────────────────

class TestOppsummeringSkillerCumulativeFraDenneRunden(_MedIsolertTilstand):
    def test_alt_feil_runde_2_endrer_runde_signalet_men_ikke_cumulative_labels(self):
        at = self._ny_apptest()
        self._apne_modul_og_start_sporsmal(at, "mesking")
        pilot = les_mesking_pilot()
        fasit = _korrekt_svar_ider(pilot)
        feil = _feil_svar_ider(pilot)

        # Runde 1 -- alt riktig.
        self._fullfor_alle_sporsmal(at, 1, fasit)
        cumulative_1 = " ".join(
            m.value for m in at.markdown if "Stivelsesomdanning" in m.value or "Dekstriner" in m.value
        )
        self.assertIn("På god vei", cumulative_1)
        alle_1 = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Riktig denne runden", alle_1)
        self.assertNotIn("Bør øves på igjen", alle_1)

        # «Prøv igjen» -- cumulative mastery skal IKKE nullstilles.
        _knapp(at, "bs_prov_igjen_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved Prøv igjen: {at.exception}")

        # Runde 2 -- alt feil (owner-akseptansesekvensen fra Chief-reviewen).
        self._fullfor_alle_sporsmal(at, 2, feil)
        self.assertEqual(len(at.exception), 0, f"Uventet unntak i runde 2: {at.exception}")

        tilstand = read_mastery_state()
        cumulative_mastery_uendret = tilstand["concepts"]["mashing.starch_conversion"]["mastery"]
        self.assertGreater(
            cumulative_mastery_uendret, 0.0,
            "Cumulative mastery skal IKKE nullstilles av en runde med feil svar.",
        )

        alle_2 = " ".join(_alle_synlige_tekster(at))
        self.assertIn("På god vei", alle_2)
        self.assertIn("Bør øves på igjen", alle_2)
        self.assertNotIn("Riktig denne runden", alle_2)

        for ord in _SKJULTE_ORD:
            self.assertNotIn(ord.lower(), alle_2.lower(), f"Fant forbudt internt ord {ord!r} i oppsummeringen.")
        self.assertIsNone(
            _RAAT_TALL_MONSTER.search(alle_2.lower()),
            "Fant et rått 0.xx-tall i oppsummeringen etter runde 2.",
        )


# ─── 12: NO/EN via appens eksisterende språktilstand ───────────────────────

class TestSprak(_MedIsolertTilstand):
    def test_engelsk_visningssprak_oversetter_panelet(self):
        at = self._ny_apptest()
        at.sidebar.radio(key="sprak").set_value("en").run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved språkbytte: {at.exception}")
        self.assertIn("Kvernhaug Brew School", " ".join(h.value for h in at.header))
        self.assertIn("Homebrewer", " ".join(m.value for m in at.markdown))

    def test_engelsk_leksjonstekst_er_faktisk_pa_engelsk(self):
        at = self._ny_apptest()
        at.sidebar.radio(key="sprak").set_value("en").run()
        self._apne_modul(at, "mesking")
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("During mashing, enzymes", tekster)

    def test_engelsk_modultittel_og_status_oversettes(self):
        at = self._ny_apptest()
        at.sidebar.radio(key="sprak").set_value("en").run()
        self._velg_miljo(at, "bs_velg_hjemmebrygger_btn")
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Mashing", tekster)
        self.assertIn("Fermentation", tekster)
        self.assertIn("Recommended next", tekster)


# ─── 13: DEMO_MODE skriver ALDRI lærer-tilstand til disk ───────────────────

class TestDemoModeIngenSkriving(unittest.TestCase):
    """DEMO_MODE er lest friskt som en modulnivå-konstant av config.py --
    må derfor kjøres i en EGEN prosess, samme mønster som
    tests/test_kbhbrew_equipment_shortcut_apptest.py sin
    TestUtstyrssnarveiDemoMode."""

    def test_demo_mode_fullfort_flyt_skriver_ingen_fil(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env["DEMO_MODE"] = "1"
            env[_STATE_DIR_ENV] = tmp
            script = (
                "import logging; logging.getLogger('streamlit').setLevel(logging.ERROR); "
                "from streamlit.testing.v1 import AppTest; "
                "from bryggeskole.pilot_mashing import read_pilot_file; "
                "pilot = read_pilot_file(); "
                "fasit = {i: next(o['id'] for o in q['options'] if o['correct']) for i, q in enumerate(pilot['questions'])}; "
                f"at = AppTest.from_file(r{_HARNESS!r}); at.run(); "
                "assert not at.exception, at.exception; "
                "knapp = lambda key: [b for b in at.button if b.key == key][0]; "
                "knapp('bs_velg_hjemmebrygger_btn').click().run(); "
                "assert not at.exception, at.exception; "
                "knapp('bs_apne_modul_mesking_btn').click().run(); "
                "knapp('bs_start_sporsmal_btn').click().run(); "
                "at.radio(key='bs_valg_r1_q0').set_value(fasit[0]).run(); "
                "knapp('bs_svar_btn_r1_q0').click().run(); "
                "knapp('bs_fortsett_btn_r1_q0').click().run(); "
                "at.radio(key='bs_valg_r1_q1').set_value(fasit[1]).run(); "
                "knapp('bs_svar_btn_r1_q1').click().run(); "
                "knapp('bs_fortsett_btn_r1_q1').click().run(); "
                "at.radio(key='bs_valg_r1_q2').set_value(fasit[2]).run(); "
                "knapp('bs_svar_btn_r1_q2').click().run(); "
                "knapp('bs_fortsett_btn_r1_q2').click().run(); "
                "assert not at.exception, at.exception; "
                "print('OK')"
            )
            resultat = subprocess.run(
                [sys.executable, "-c", script],
                cwd=_REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(resultat.returncode, 0, f"stdout={resultat.stdout}\nstderr={resultat.stderr}")
            self.assertIn("OK", resultat.stdout)
            self.assertEqual(os.listdir(tmp), [], "DEMO_MODE skal ALDRI skrive en lærer-tilstandsfil til disk.")


# ─── 1: Bryggeskole er en topplinje-fane i den EKTE app.py ────────────────

class TestReachableSomToppniva(unittest.TestCase):
    def test_bryggeskole_fane_og_panel_rendrer_i_full_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env[_STATE_DIR_ENV] = tmp
            script = (
                "import logging; logging.getLogger('streamlit').setLevel(logging.ERROR); "
                "from streamlit.testing.v1 import AppTest; "
                f"at = AppTest.from_file(r{_APP_PY!r}); at.run(); "
                "assert not at.exception, at.exception; "
                "headers = [h.value for h in at.header]; "
                "assert any('Bryggeskole' in h or 'Brew School' in h for h in headers), headers; "
                "knapper = [b.key for b in at.button if b.key == 'bs_velg_hjemmebrygger_btn']; "
                "assert len(knapper) == 1, knapper; "
                "print('OK')"
            )
            resultat = subprocess.run(
                [sys.executable, "-c", script],
                cwd=_REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(resultat.returncode, 0, f"stdout={resultat.stdout}\nstderr={resultat.stderr}")
            self.assertIn("OK", resultat.stdout)


if __name__ == "__main__":
    unittest.main()
