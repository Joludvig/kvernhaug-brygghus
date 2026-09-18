"""
AppTest-basert dekning for ui/bryggeskole_panel.py::render_bryggeskole_panel()
(issue #327, BRYGGESKOLE V2-3C -- første integrerte Bryggeskole-UI).

Dekker akkurat de ni automatiserte akseptansepunktene issue #327 selv
lister (de tre siste -- full testsuite grønn, git diff --check, at
eksisterende bryggeskole/-tester forblir grønne uendret -- verifiseres
av selve CI-kjøringen/checkouten, ikke av denne filen):
    1. Bryggeskole er nåbar som topplinje-fane i app.py.
    2. Begge miljøvisninger (Hjemmebrygger/Bryggeri) rendrer.
    3. Begge miljøer ruter inn i SAMME gjæringspilot-innhold.
    4. Chunk -> spørsmål -> svar -> feedback -> fullføring virker.
    5. Riktig/feil-stier oppdaterer mastery via de eksisterende API-ene.
    6. Læringsvendt output viser ALDRI rå mastery/confidence/attempts
       eller rå numeriske skår.
    7. «Prøv igjen» virker mot PERSISTERT mastery (nullstiller den ikke).
    8. NO/EN virker via appens eksisterende språktilstand.
    9. DEMO_MODE utfører INGEN disk-skriving av lærer-tilstand.

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

from bryggeskole.mastery_store import _STATE_DIR_ENV, read_mastery_state

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "bryggeskole_harness.py")
_APP_PY = os.path.join(_REPO_ROOT, "app.py")

# Riktig svaralternativ-id for hvert spørsmål, per
# bryggeskole/data/pilot_fermentation_temperature.json -- brukt til å
# drive "alt riktig"-stien uten å duplisere selve fasit-logikken (den er
# allerede dekket av tests/test_pilot_fermentation.py).
_RIKTIG_SVAR = {0: "a", 1: "b"}
_FEIL_SVAR = {0: "b", 1: "a"}

_RAAT_TALL_MONSTER = re.compile(r"\b0\.\d+\b")
_SKJULTE_ORD = ("mastery", "confidence", "attempts")


def _knapp(at, key):
    knapper = [b for b in at.button if b.key == key]
    assert len(knapper) == 1, f"Fant ikke akkurat én knapp med key={key!r}: {[b.key for b in at.button]}"
    return knapper[0]


def _alle_synlige_tekster(at):
    """Samler all tekst en lærer faktisk ser -- markdown, caption,
    header/subheader, success/error-meldinger og knappelabels -- til én
    liste strenger, for no-raw-hidden-state-søket (punkt 6)."""
    tekster = []
    for samling in (at.markdown, at.caption, at.header, at.subheader, at.success, at.error):
        tekster.extend(e.value for e in samling)
    tekster.extend(b.label for b in at.button if b.label)
    return tekster


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

    def _velg_miljo_og_start_modul(self, at, miljo_knapp="bs_velg_hjemmebrygger_btn"):
        """Velger miljø og starter modulen -- lander på LEKSJON-fasen
        (chunk-teksten), ett steg FØR spørsmålene starter."""
        _knapp(at, miljo_knapp).click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved miljøvalg: {at.exception}")
        _knapp(at, "bs_start_modul_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved modulstart: {at.exception}")
        return at

    def _start_sporsmalsrunde(self, at):
        _knapp(at, "bs_start_sporsmal_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved spørsmålsstart: {at.exception}")
        return at

    def _velg_miljo_start_modul_og_sporsmal(self, at, miljo_knapp="bs_velg_hjemmebrygger_btn"):
        self._velg_miljo_og_start_modul(at, miljo_knapp)
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


# ─── 2 + 3: begge miljøer rendrer og ruter til SAMME pilotinnhold ──────────

class TestMiljovalgOgProsessoversikt(_MedIsolertTilstand):
    def test_miljovalg_vises_ved_start(self):
        at = self._ny_apptest()
        _knapp(at, "bs_velg_hjemmebrygger_btn")
        _knapp(at, "bs_velg_bryggeri_btn")

    def test_hjemmebrygger_rendrer_prosessoversikt_og_leksjon(self):
        at = self._ny_apptest()
        self._velg_miljo_og_start_modul(at, "bs_velg_hjemmebrygger_btn")
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Gjæringstemperatur påvirker", tekster)

    def test_bryggeri_rendrer_samme_pilotinnhold(self):
        at = self._ny_apptest()
        self._velg_miljo_og_start_modul(at, "bs_velg_bryggeri_btn")
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Gjæringstemperatur påvirker", tekster)

    def test_bytt_miljo_nullstiller_til_miljovalg(self):
        at = self._ny_apptest()
        _knapp(at, "bs_velg_hjemmebrygger_btn").click().run()
        _knapp(at, "bs_bytt_miljo_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")
        _knapp(at, "bs_velg_hjemmebrygger_btn")
        _knapp(at, "bs_velg_bryggeri_btn")

    def test_kun_gjaring_er_klikkbar_ingen_andre_leksjoner_pastas(self):
        at = self._ny_apptest()
        _knapp(at, "bs_velg_hjemmebrygger_btn").click().run()
        # Prosessoversikten viser flere stadier, men bare ett skal være
        # markert som en tilgjengelig leksjon -- resten er ren orientering.
        aktiv_badges = [c.value for c in at.caption if "Leksjon tilgjengelig" in c.value]
        self.assertEqual(len(aktiv_badges), 1)


# ─── 4 + 5 + 7: full lærings-flyt, mastery-oppdatering, «Prøv igjen» ───────

class TestLaeringsflyt(_MedIsolertTilstand):
    def test_full_flyt_alt_riktig_gir_oppsummering(self):
        at = self._ny_apptest()
        self._velg_miljo_start_modul_og_sporsmal(at)
        self._besvar_sporsmal(at, 0, 1, _RIKTIG_SVAR[0])
        self.assertTrue(len(at.success) >= 1, "Riktig svar skal vise en positiv feedback-melding.")
        self._fortsett(at, 0, 1)
        self._besvar_sporsmal(at, 1, 1, _RIKTIG_SVAR[1])
        self._fortsett(at, 1, 1)
        _knapp(at, "bs_prov_igjen_btn")

    def test_feil_svar_viser_forklarende_feedback_ikke_bare_feil(self):
        at = self._ny_apptest()
        self._velg_miljo_start_modul_og_sporsmal(at)
        self._besvar_sporsmal(at, 0, 1, _FEIL_SVAR[0])
        self.assertEqual(len(at.error), 1)
        feedback = at.error[0].value
        self.assertGreater(len(feedback), 40, "Feedback på feil svar skal forklare, ikke bare si «feil».")

    def test_riktig_svar_oker_mastery_for_alle_konsepter_spersmalet_dekker(self):
        at = self._ny_apptest()
        self._velg_miljo_start_modul_og_sporsmal(at)
        self._besvar_sporsmal(at, 0, 1, _RIKTIG_SVAR[0])
        tilstand = read_mastery_state()
        for konsept in ("fermentation.temperature", "fermentation.yeast_activity"):
            self.assertGreater(tilstand["concepts"][konsept]["mastery"], 0.0)
            self.assertEqual(tilstand["concepts"][konsept]["attempts"], 1)

    def test_feil_svar_oker_aldri_mastery(self):
        at = self._ny_apptest()
        self._velg_miljo_start_modul_og_sporsmal(at)
        self._besvar_sporsmal(at, 0, 1, _FEIL_SVAR[0])
        tilstand = read_mastery_state()
        for konsept in ("fermentation.temperature", "fermentation.yeast_activity"):
            self.assertEqual(tilstand["concepts"][konsept]["mastery"], 0.0)
            self.assertEqual(tilstand["concepts"][konsept]["attempts"], 1)

    def test_prov_igjen_bruker_persistert_mastery_ikke_nullstilling(self):
        at = self._ny_apptest()
        self._velg_miljo_start_modul_og_sporsmal(at)
        self._fullfor_alle_sporsmal(at, 1, _RIKTIG_SVAR)
        forste_runde_tilstand = read_mastery_state()
        forste_mastery = forste_runde_tilstand["concepts"]["fermentation.temperature"]["mastery"]
        self.assertGreater(forste_mastery, 0.0)

        _knapp(at, "bs_prov_igjen_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved Prøv igjen: {at.exception}")
        # Ny runde -- bs_runde er nå 2, spørsmål-widgetene har derfor nye
        # keys (bs_valg_r2_qX), akkurat som _start_sporsmal_runde() sin
        # egen docstring beskriver.
        self._fullfor_alle_sporsmal(at, 2, _RIKTIG_SVAR)

        andre_runde_tilstand = read_mastery_state()
        andre_mastery = andre_runde_tilstand["concepts"]["fermentation.temperature"]["mastery"]
        self.assertGreaterEqual(
            andre_mastery, forste_mastery,
            "«Prøv igjen» skal bygge videre på persistert mastery, ikke nullstille den.",
        )
        self.assertEqual(
            andre_runde_tilstand["concepts"]["fermentation.temperature"]["attempts"], 2,
            "Attempts skal telle opp over runder -- persistens skal ALDRI nullstilles av «Prøv igjen».",
        )


# ─── 6: aldri rå mastery/confidence/attempts eller rå tall i UI-teksten ────

class TestIngenRaaTilstandVisesLaereren(_MedIsolertTilstand):
    def test_ingen_rae_tall_eller_skjulte_ord_gjennom_hele_flyten(self):
        at = self._ny_apptest()
        self._velg_miljo_start_modul_og_sporsmal(at)
        self._fullfor_alle_sporsmal(at, 1, _RIKTIG_SVAR)
        # Nå på oppsummeringen -- den mest risikofylte skjermen for lekkasje.
        alle_tekster = " ".join(_alle_synlige_tekster(at)).lower()
        for ord in _SKJULTE_ORD:
            self.assertNotIn(ord, alle_tekster, f"Fant forbudt internt ord {ord!r} i lærervendt tekst.")
        self.assertIsNone(
            _RAAT_TALL_MONSTER.search(alle_tekster),
            "Fant et rått 0.xx-tall (mastery/confidence-form) i lærervendt tekst.",
        )


# ─── 8: NO/EN via appens eksisterende språktilstand ────────────────────────

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
        self._velg_miljo_og_start_modul(at)
        tekster = " ".join(_alle_synlige_tekster(at))
        self.assertIn("Fermentation temperature affects", tekster)


# ─── 9: DEMO_MODE skriver ALDRI lærer-tilstand til disk ────────────────────

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
                f"at = AppTest.from_file(r{_HARNESS!r}); at.run(); "
                "assert not at.exception, at.exception; "
                "knapp = lambda key: [b for b in at.button if b.key == key][0]; "
                "knapp('bs_velg_hjemmebrygger_btn').click().run(); "
                "assert not at.exception, at.exception; "
                "knapp('bs_start_modul_btn').click().run(); "
                "knapp('bs_start_sporsmal_btn').click().run(); "
                "at.radio(key='bs_valg_r1_q0').set_value('a').run(); "
                "knapp('bs_svar_btn_r1_q0').click().run(); "
                "knapp('bs_fortsett_btn_r1_q0').click().run(); "
                "at.radio(key='bs_valg_r1_q1').set_value('b').run(); "
                "knapp('bs_svar_btn_r1_q1').click().run(); "
                "knapp('bs_fortsett_btn_r1_q1').click().run(); "
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
