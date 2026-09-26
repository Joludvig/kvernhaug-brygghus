"""
Regresjonstester for issue #400 -- "Språkbytte gir blandet NO/EN og kan
krasje oppskriftsvelger ved EN->NO".

To atskilte, IKKE nødvendigvis samme-rotårsak-feil (bevisst ikke antatt
å henge sammen, se issue #400 sin egen advarsel):

  A) MIXED NO/EN: ui/hop_panel.py og ui/yeast_panel.py sine header-/
     knapp-/label-tekster ("🌿 Humle-tilsetninger", "➕ Legg til humle",
     "🧫 Gjærstamme", "Velg gjær:") var ALDRI koblet til i18n-laget i det
     hele tatt -- ren, statisk manglende dekning, ikke et rerun-/
     koherensproblem. De sitter side om side med ALLEREDE i18n-aktiverte
     Learn->Plan-bro-tekster i SAMME filer.

  B) EN->NO-KRASJ: oppskrift-selectboksens plassholder-tekst
     (t("sidebar.velg_placeholder")) ble kalt LIVE inne i selve
     format_func-lambdaen -- format_func kan bli re-invokert av
     Streamlit/AppTest sin egen widget-state-rekonsiliering PÅ ET
     TIDSPUNKT der st.session_state["sprak"] allerede er endret til det
     NYE språket, mens selectboksens faktisk RENDREDE options-liste
     fortsatt reflekterer det GAMLE språket -- et selvmotsigende utfall
     der format_func(sentinel) produserer en STRENG som ikke finnes i
     options-lista for DENNE rendringen. Reprodusert direkte via den
     ekte, produksjonsbrukte SelectboxSerde/AppTest-widget-state-
     maskineriet (samme underliggende Streamlit-mekanisme som traff
     brukeren i en ekte nettleserøkt).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")


class _MedIsolertOppskriftsmappe(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def _lagre_test_oppskrift(self, navn="I400 Testbrygg"):
        import modules.recipe_storage as recipe_storage
        recipe = bygg_recipe_object(
            navn, 20.0, 0.72,
            [{"id": "weyermann_pilsner", "mengde": 4.5}],
            [{"id": "magnum", "gram": 20, "tid": 60}],
            "safale_us_05", 1.048, 1.011, 4.9, 22, 8, {},
        )
        recipe_storage.lagre_oppskrift(recipe)
        return navn


# ─── A) Blandet NO/EN på Humle-/Gjær-panelet ───────────────────────────────

class TestHumleGjaerPanelSpraakKoherens(_MedIsolertOppskriftsmappe):
    """De fire konkrete strengene issue #400 selv navnga som "still
    Norwegian" mens andre kontroller i samme visning allerede var
    engelske. Ren, deterministisk statisk-innhold-sjekk: ingen rerun-
    koreografi involvert -- beviser at disse fire IKKE er koblet til
    t(), uansett hvilket språk som er aktivt."""

    def _hent_hovedside_markdown_og_widgettekster(self, at):
        tekster = []
        tekster += [w.value for w in at.header]
        tekster += [getattr(w, "label", None) for w in at.button]
        tekster += [getattr(w, "label", None) for w in at.selectbox]
        return [t for t in tekster if t]

    def test_humle_og_gjaer_header_knapp_label_bytter_til_engelsk(self):
        """Post-fix regresjon (issue #400, rotårsak A): disse fire
        strengene skal nå faktisk bytte språk sammen med resten av
        allerede-i18n-aktiverte kontroller på samme flate -- ikke lenger
        stå igjen på norsk. (Pre-fix bevis, at de faktisk STO igjen på
        norsk, ble kjørt og bekreftet manuelt før fiksen ble
        implementert.)"""
        self._lagre_test_oppskrift()
        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.session_state["sprak"] = "en"
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception: {at.exception}")

        alle = self._hent_hovedside_markdown_og_widgettekster(at)
        for norsk_streng in ("🌿 Humle-tilsetninger", "➕ Legg til humle", "🧫 Gjærstamme", "Velg gjær:"):
            self.assertNotIn(
                norsk_streng, alle,
                f"{norsk_streng!r} skal ikke lenger stå igjen på norsk når sprak=en",
            )
        for engelsk_streng in ("🌿 Hop additions", "➕ Add hop", "🧫 Yeast strain", "Select yeast:"):
            self.assertIn(
                engelsk_streng, alle,
                f"forventet {engelsk_streng!r} i den rendrede engelske UI-en, fikk: {alle}",
            )

    def test_humle_og_gjaer_header_knapp_label_forblir_norsk_som_default(self):
        """Motsatt retning: default-språket (norsk) skal fortsatt vise
        de norske tekstene -- fiksen skal ALDRI hardkode engelsk."""
        self._lagre_test_oppskrift()
        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["sprak"], "no")

        alle = self._hent_hovedside_markdown_og_widgettekster(at)
        for norsk_streng in ("🌿 Humle-tilsetninger", "➕ Legg til humle", "🧫 Gjærstamme", "Velg gjær:"):
            self.assertIn(norsk_streng, alle, f"forventet {norsk_streng!r} som norsk default, fikk: {alle}")

    def test_koking_humle_bro_er_allerede_engelsk_ved_siden_av_de_norske(self):
        """Beviser at PROBLEMET faktisk er blandet -- ikke bare at ALT
        er norsk (som ville vært en helt annen, enklere feil)."""
        self._lagre_test_oppskrift()
        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.session_state["sprak"] = "en"
        at.run()
        self.assertFalse(at.exception)

        # Learn->Plan-broens EGEN, allerede i18n-aktiverte tittel (issue
        # #388) -- rendres som en expander-label, ikke <header>. Vi
        # sjekker heller en tekst broen faktisk skriver.
        alle_markdown = [w.value for w in at.markdown]
        alle_caption = [w.value for w in at.caption]
        self.assertTrue(
            any("hop timing" in (m or "").lower() or "fermentation temperature" in (m or "").lower()
                for m in alle_markdown + alle_caption),
            "forventet at Learn->Plan-broens engelske tekst faktisk vises (delvis i18n-dekning)",
        )


# ─── B) EN->NO krasjer oppskriftsvelgeren ──────────────────────────────────

class TestOppskriftsvelgerSprakbytteKrasj(_MedIsolertOppskriftsmappe):
    """Reproduserer issue #400 sin `KeyError: '-- Velg oppskrift --'`
    direkte via AppTest -- samme SelectboxSerde/widget-state-maskineri
    en ekte nettleserøkt bruker (se ui/sidebar.py linje ~186)."""

    def test_en_til_no_krasjer_ikke_med_ingen_oppskrift_valgt(self):
        self._lagre_test_oppskrift()
        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.session_state["sprak"] = "en"
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart i EN: {at.exception}")

        # Ingen oppskrift valgt -- plassholderen er aktiv. Bytt SPRÅK
        # TILBAKE til norsk UTEN å røre selve selectboksen -- nøyaktig
        # brukerflyten fra issue #400.
        at.sidebar.radio(key="sprak").set_value("no").run()
        self.assertFalse(
            at.exception,
            f"forventet (pre-fix) at EN->NO krasjer med KeyError på plassholderteksten: {at.exception}",
        )

    def test_no_til_en_til_no_krasjer_ikke(self):
        """Toveis-runde, start i norsk (App sin faktiske default)."""
        self._lagre_test_oppskrift()
        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["sprak"], "no")

        at.sidebar.radio(key="sprak").set_value("en").run()
        self.assertFalse(at.exception, f"NO->EN kastet exception: {at.exception}")

        at.sidebar.radio(key="sprak").set_value("no").run()
        self.assertFalse(
            at.exception,
            f"forventet (pre-fix) at den ANDRE (tilbake-til-NO) rerunen krasjer: {at.exception}",
        )

    def test_ingen_oppskrift_valgt_sentinelen_overlever_begge_retninger(self):
        self._lagre_test_oppskrift()
        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertNotIn("_last_loaded_recipe", at.session_state)

        at.sidebar.radio(key="sprak").set_value("en").run()
        self.assertFalse(at.exception)
        self.assertNotIn("_last_loaded_recipe", at.session_state)

        at.sidebar.radio(key="sprak").set_value("no").run()
        self.assertFalse(at.exception)
        self.assertNotIn(
            "_last_loaded_recipe", at.session_state,
            "en stale plassholder-verdi skal ALDRI bli tolket som en ekte oppskrift-lasting",
        )

    def test_ekte_valgt_oppskrift_overlever_sprakbytte_begge_veier(self):
        """Acceptance-punkt 6: en FAKTISK valgt oppskrift skal
        bevares/gjenlastes riktig gjennom språkbytte -- denne banen er
        IKKE forventet å krasje verken før eller etter fiksen, siden
        format_func for en ekte oppskrift returnerer verdien uendret
        (språkuavhengig) -- men testen låser dette fast som et eksplisitt
        akseptansekrav, ikke en tilfeldighet."""
        navn = self._lagre_test_oppskrift("I400 Ekte Valgt")
        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select(navn).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["_last_loaded_recipe"], navn)

        at.sidebar.radio(key="sprak").set_value("en").run()
        self.assertFalse(at.exception, f"NO->EN med ekte oppskrift valgt kastet exception: {at.exception}")
        self.assertEqual(at.session_state["_last_loaded_recipe"], navn)
        self.assertEqual(at.session_state["gjeldende_navn"], navn)

        at.sidebar.radio(key="sprak").set_value("no").run()
        self.assertFalse(at.exception, f"EN->NO med ekte oppskrift valgt kastet exception: {at.exception}")
        self.assertEqual(at.session_state["_last_loaded_recipe"], navn)
        self.assertEqual(at.session_state["gjeldende_navn"], navn)


if __name__ == "__main__":
    unittest.main()
