"""
V2.2 G2D (issue #363) -- end-to-end AppTest regression for the
"🌱 Opprett neste variant" / next-variant-linkage flow, via the REAL,
full `app.py` (same "real user path, real widgets, real re-render"
principle as tests/test_app_a4_selector_orientation_apptest.py) rather
than a narrow, synthetic per-panel harness -- the identity-boundary
guarantee this issue exists to prove (docs/development/
v22_g2c_next_variant_linkage_contract.md §4.1/§6) spans TWO different
panels (ui/kbhbrew_history_panel.py's seed action, ui/recipe_card.py's
"Lagre som ny kopi" save), so only a real, full-app render actually
proves the two wire together correctly.

Covers (issue #363 "Required tests" 5/6/8 at the UI-wiring level -- the
pure identity-boundary logic itself is already covered, faster and
independent of Streamlit, in tests.test_kbhbrew_engine_readerwriter's
TestNesteVariantSeed):
  - the seeded draft's originRecipeId is fresh and differs from the
    source recipe's own (never inherited);
  - that SAME fresh id survives the very first "💾 Lagre som ny kopi"
    save unchanged (not re-minted a second time);
  - the source recipe's saved file is untouched;
  - ordinary "Lagre som ny kopi" (no next-variant seed involved) is
    completely unaffected -- still mints its own, unrelated fresh id,
    exactly as before this issue (regression guard for issue #283/#286).

Run with:
    python3 -m unittest tests.test_kbhbrew_next_variant_e2e_apptest -b
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.recipe_storage as recipe_storage
from modules.kbhbrew_storage import oppdater_brew_lag, opprett_og_lagre_ny_brew
from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")
_DATA_DIR = os.path.join(_REPO_ROOT, "data")

_BREW_ID = "brew-e2e-363"


def _last_master(filnavn):
    with open(os.path.join(_DATA_DIR, filnavn), encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _ss(at, key, default=None):
    """Trygg session_state-lesing -- AppTest sin session_state-proxy
    støtter ikke .get(), kun subscript (samme mønster som
    tests/test_app_a4_selector_orientation_apptest.py)."""
    try:
        return at.session_state[key]
    except KeyError:
        return default


class _MedIsolerteOppskrifter(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_dir = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_recipes_dir is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_recipes_dir
        self._tmpdir.cleanup()

    def _seed_kilde_og_brew(self):
        malt_db = _last_master("master_malt.json")
        humle_db = _last_master("master_humle_v2.json")
        gjaer_db = _last_master("master_gjaer_v2.json")
        malt_id = next(iter(malt_db))
        gjaer_id = next(iter(gjaer_db))

        recipe = bygg_recipe_object(
            "E2E Kildebrygg", 20.0, 0.75,
            [{"id": malt_id, "mengde": 5.0}], [],
            gjaer_id, 1.050, 1.012, 5.0, 20, 8, {},
        )
        filnavn = recipe_storage.lagre_oppskrift(recipe)
        kilde_origin_id = recipe_storage.sikre_origin_recipe_id(filnavn)
        self.assertTrue(kilde_origin_id)
        # Speiler en reell live-oppskrift som allerede har fått en
        # originRecipeId FØR brygget opprettes -- snapshotet skal fryse
        # nøyaktig denne verdien (Section 2.4 i kontraktbrevet).
        recipe["originRecipeId"] = kilde_origin_id

        equipment = {
            "efficiency": 0.75, "boil_off_l_per_hour": 4.0, "grain_absorption_l_per_kg": 1.0,
            "dead_space_l": 2.0, "mash_ratio_l_per_kg": 3.2, "kettle_capacity_l": 35.0,
            "default_boil_time_min": 60,
        }
        brew = opprett_og_lagre_ny_brew(
            recipe, malt_db, humle_db, gjaer_db, equipment,
            {"og": 1.050, "fg": 1.012, "abv": 5.0},
            recipe_id=filnavn, brew_id=_BREW_ID,
        )
        self.assertEqual(brew["snapshot"]["recipe"]["originRecipeId"], kilde_origin_id)
        oppdater_brew_lag(_BREW_ID, learning={"nextTime": "Hev røykmalt-andelen"})
        return kilde_origin_id


class TestNesteVariantE2EAppTest(_MedIsolerteOppskrifter):

    def test_opprett_neste_variant_seeder_fersk_id_og_lagre_som_ny_kopi_bevarer_den(self):
        kilde_origin_id = self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)

        at.selectbox(key="kbhbrew_historikk_valgt_id").select(_BREW_ID).run()
        self.assertFalse(at.exception)

        at.button(key=f"kbhbrew_hist_neste_variant_btn::{_BREW_ID}").click().run()
        self.assertFalse(at.exception)

        fersk_id = _ss(at, "_aktiv_kbh_origin_recipe_id")
        self.assertTrue(fersk_id)
        self.assertNotEqual(fersk_id, kilde_origin_id)
        self.assertEqual(_ss(at, "_aktiv_kbh_neste_variant_frossen_origin_id"), fersk_id)
        self.assertEqual(_ss(at, "gjeldende_navn"), "E2E Kildebrygg")
        # "import as new"-semantikk (kbh_import_apply.py) -- utkastet er
        # ulagret, "Lagre endringer" skal derfor ikke være tilgjengelig.
        self.assertIsNone(_ss(at, "_last_loaded_recipe"))

        at.text_input(key="gjeldende_navn").set_value("E2E Kildebrygg v2").run()
        self.assertFalse(at.exception)
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)

        lagrede = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("E2E Kildebrygg v2", lagrede)
        self.assertEqual(lagrede["E2E Kildebrygg v2"]["originRecipeId"], fersk_id)
        self.assertNotEqual(lagrede["E2E Kildebrygg v2"]["originRecipeId"], kilde_origin_id)

        # Kildeoppskriften er byte-for-byte uendret på disk.
        kilde = lagrede["E2E Kildebrygg"]
        self.assertEqual(kilde["originRecipeId"], kilde_origin_id)

    def test_neste_variant_kollisjon_ved_forste_lagring_bevarer_frossen_id_ved_retry(self):
        """Chief-review 5280874111 (issue #363): et utkast seedet av
        "🌱 Opprett neste variant" arver kildens navn (§4.1) -- et
        lagringsforsøk UTEN omdøp kolliderer derfor helt normalt med
        kildeoppskriften som allerede ligger på disk. Den frosne
        seed-IDen må overleve akkurat DETTE avviste forsøket uendret,
        slik at et påfølgende omdøp+retry gjenbruker den, ikke minter
        en andre, ny UUID."""
        kilde_origin_id = self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)

        at.selectbox(key="kbhbrew_historikk_valgt_id").select(_BREW_ID).run()
        self.assertFalse(at.exception)

        at.button(key=f"kbhbrew_hist_neste_variant_btn::{_BREW_ID}").click().run()
        self.assertFalse(at.exception)

        fersk_id = _ss(at, "_aktiv_kbh_origin_recipe_id")
        self.assertTrue(fersk_id)
        self.assertNotEqual(fersk_id, kilde_origin_id)
        self.assertEqual(_ss(at, "_aktiv_kbh_neste_variant_frossen_origin_id"), fersk_id)
        # Utkastet arver kildens navn ved seeding -- et lagringsforsøk
        # UTEN omdøp kolliderer derfor med kildeoppskriften på disk.
        self.assertEqual(_ss(at, "gjeldende_navn"), "E2E Kildebrygg")

        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)
        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(
            any("E2E Kildebrygg" in msg and "allerede" in msg for msg in feilmeldinger),
            feilmeldinger,
        )
        # Avvist -- ingen "E2E Kildebrygg"-duplikat er skrevet.
        lagrede_etter_kollisjon = recipe_storage.hent_alle_oppskrifter()
        self.assertNotIn("E2E Kildebrygg v2", lagrede_etter_kollisjon)

        # Den frosne seed-IDen skal ha overlevd det avviste forsøket
        # uendret, klar for et retry -- IKKE konsumert av
        # `.pop()` før selve lagringen faktisk lyktes.
        self.assertEqual(_ss(at, "_aktiv_kbh_neste_variant_frossen_origin_id"), fersk_id)
        self.assertEqual(_ss(at, "_aktiv_kbh_origin_recipe_id"), fersk_id)

        at.text_input(key="gjeldende_navn").set_value("E2E Kildebrygg v2").run()
        self.assertFalse(at.exception)
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)

        lagrede = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("E2E Kildebrygg v2", lagrede)
        # Kopien har NØYAKTIG den opprinnelige, seed-mintede IDen --
        # ikke en andre, ny UUID mintet ved retry-forsøket.
        self.assertEqual(lagrede["E2E Kildebrygg v2"]["originRecipeId"], fersk_id)
        self.assertNotEqual(lagrede["E2E Kildebrygg v2"]["originRecipeId"], kilde_origin_id)

        # Markøren er nå endelig konsumert, først etter suksess.
        self.assertIsNone(_ss(at, "_aktiv_kbh_neste_variant_frossen_origin_id"))

        # Kildeoppskriften/snapshotet er fortsatt byte-for-byte uendret.
        kilde = lagrede["E2E Kildebrygg"]
        self.assertEqual(kilde["originRecipeId"], kilde_origin_id)

    def test_lagre_som_ny_kopi_uten_seed_minter_fortsatt_ny_id_som_for(self):
        kilde_origin_id = self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)

        # Laster KILDE-oppskriften via den ordinære sidebar-selectboksen
        # (INGEN neste-variant-seed involvert) og duplikerer den --
        # regresjonsvakt: en vanlig "Lagre som ny kopi" skal fortsatt
        # minte en helt egen, ny id, akkurat som før denne saken
        # (issue #283/#286).
        at.selectbox(key="sidebar_recipe_selector").select("E2E Kildebrygg").run()
        self.assertFalse(at.exception)
        self.assertIsNone(_ss(at, "_aktiv_kbh_neste_variant_frossen_origin_id"))

        at.text_input(key="gjeldende_navn").set_value("E2E Kildebrygg Kopi").run()
        self.assertFalse(at.exception)
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)

        lagrede = recipe_storage.hent_alle_oppskrifter()
        kopi_id = lagrede["E2E Kildebrygg Kopi"]["originRecipeId"]
        self.assertTrue(kopi_id)
        self.assertNotEqual(kopi_id, kilde_origin_id)


# ─── issue #391 -- persistent bekreftelse + Oppskrift-fanens utkast-banner ──
#
# Reported bug: the seed succeeds, Streamlit reruns, the transient
# `st.success()` in ui/kbhbrew_history_panel.py's button handler (rendered
# right before its own st.rerun()) never actually reaches the user --
# reruns tear down and redraw the whole script tree, so nothing rendered
# just before a forced rerun can ever be seen. These tests prove the two
# NEW, persistent signals added in ui/sidebar.py and ui/recipe_card.py
# instead -- both of which are visible on the SAME rerun that follows the
# button click (the exact rerun the reported bug made look like "nothing
# happened"), not the doomed pre-rerun render.
_BEKREFTELSE_NO = "et ulagret utkast"
_BEKREFTELSE_EN = "an unsaved draft"


def _hovedside_success_tekster(at):
    """Chief-korreksjon (PR #396, issue #391): `at.success` (uskopert) i
    stedet for `at.sidebar.success` -- bekreftelsen rendres nå med et
    vanlig `st.success()` fra render_sidebar(), FØR st.tabs(...) i
    app.py sin scriptrekkefølge (se ui/sidebar.py sin egen kommentar),
    altså på HOVEDSIDEN, ikke inni selve sidebar-containeren. `at.success`
    fanger opp suksesselementer uansett hvor i tre-et de er rendret, så
    denne funksjonen beviser meldingen finnes -- den påfølgende
    `at.sidebar.success`-sjekken i testen under beviser i tillegg at den
    IKKE lenger er sidebar-scopet."""
    return [e.value for e in at.success]


def _info_tekster(at):
    return [e.value for e in at.info]


class TestNesteVariantSeedBekreftelseE2E(_MedIsolerteOppskrifter):

    def test_bekreftelse_vises_i_sidebar_paa_rerunen_etter_seed(self):
        self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)

        at.selectbox(key="kbhbrew_historikk_valgt_id").select(_BREW_ID).run()
        self.assertFalse(at.exception)

        # Ett eneste .click().run() dekker BEGGE reruns (knappens egen
        # st.rerun(), pluss AppTest sin automatiske gjennomkjøring av den)
        # -- se de tre eksisterende testene over, som allerede leser
        # ferdig hydrert session_state rett etter nøyaktig dette kallet.
        at.button(key=f"kbhbrew_hist_neste_variant_btn::{_BREW_ID}").click().run()
        self.assertFalse(at.exception)

        meldinger = _hovedside_success_tekster(at)
        self.assertTrue(
            any(_BEKREFTELSE_NO in m for m in meldinger),
            f"forventet en bekreftelse på hovedsiden om ulagret utkast, fikk: {meldinger}",
        )
        # Chief-korreksjon (issue #391): en sammenslått sidebar må ALDRI
        # kunne skjule denne -- beviser eksplisitt at den IKKE (lenger)
        # kun finnes inni selve sidebar-containeren.
        sidebar_meldinger = [e.value for e in at.sidebar.success]
        self.assertFalse(
            any(_BEKREFTELSE_NO in m for m in sidebar_meldinger),
            "bekreftelsen skal rendres på hovedsiden, ikke (kun) i sidebaren",
        )

    def test_bekreftelse_nokkelen_har_faktisk_ulik_no_og_en_tekst(self):
        """Beviser at EN-teksten finnes og faktisk skiller seg fra NO --
        på selve i18n-laget (samme mønster som
        tests/test_kbhbrew_terminology_apptest.py sin ren_t()-bruk),
        IKKE via en full AppTest-språkbytte gjennom
        kbhbrew_historikk_valgt_id/actuals-statusselectboksen: den
        kombinasjonen har en EKSISTERENDE, urelatert AppTest-
        widget-state-krasj ("'Aktiv' is not in list") når språk settes
        til "en" FØR første at.run() og en brygg-status-selectbox
        (kbhbrew_hist_status::{brew_id}, en helt annen, uendret widget)
        deretter rekomputeres -- reprodusert også UTEN denne
        korreksjonens egne endringer, altså ikke noe issue #391 skal
        fikse. Den FAKTISKE UI-koblingen (riktig nøkkel rendres på
        riktig sted) er allerede bevist på norsk over; her bevises kun
        at selve teksten er reell, tospråklig og ulik."""
        from modules.i18n import t as ren_t

        no_tekst = ren_t("brew_history.neste_variant_seed_bekreftelse", "no")
        en_tekst = ren_t("brew_history.neste_variant_seed_bekreftelse", "en")
        self.assertIn(_BEKREFTELSE_NO, no_tekst)
        self.assertIn(_BEKREFTELSE_EN, en_tekst)
        self.assertNotEqual(no_tekst, en_tekst)

    def test_bekreftelse_er_ett_gangs_og_forsvinner_paa_neste_urelaterte_rerun(self):
        """Test requirement 4: må ikke henge igjen for alltid."""
        self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        at.selectbox(key="kbhbrew_historikk_valgt_id").select(_BREW_ID).run()
        at.button(key=f"kbhbrew_hist_neste_variant_btn::{_BREW_ID}").click().run()
        self.assertTrue(any(_BEKREFTELSE_NO in m for m in _hovedside_success_tekster(at)))

        # En helt urelatert widget-interaksjon (omdøping av utkastet) --
        # ny rerun, INGEN ny seed-handling. Bekreftelsen skal IKKE dukke
        # opp igjen (den er konsumert av .pop() på NESTE_VARIANT_SEED_
        # PENDING_NOKKEL, akkurat som selve hydreringen den er koblet til).
        at.text_input(key="gjeldende_navn").set_value("E2E Kildebrygg v2").run()
        self.assertFalse(at.exception)
        self.assertFalse(
            any(_BEKREFTELSE_NO in m for m in _hovedside_success_tekster(at)),
            "bekreftelsen skal ikke overleve en senere, urelatert rerun",
        )

    def test_oppskrift_fanen_viser_utkast_banner_mens_uendret(self):
        """Recipe-tab-banneret er valgfritt per issue #391, men når det
        implementeres skal det faktisk vises mens utkastet står ulagret."""
        self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        at.selectbox(key="kbhbrew_historikk_valgt_id").select(_BREW_ID).run()
        at.button(key=f"kbhbrew_hist_neste_variant_btn::{_BREW_ID}").click().run()
        self.assertFalse(at.exception)

        infoer = _info_tekster(at)
        self.assertTrue(
            any("neste variant" in m and "utkast" in m for m in infoer),
            f"forventet et Oppskrift-fane-banner om det ferske utkastet, fikk: {infoer}",
        )

    def test_oppskrift_fanen_banner_forsvinner_etter_vellykket_lagring(self):
        self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        at.selectbox(key="kbhbrew_historikk_valgt_id").select(_BREW_ID).run()
        at.button(key=f"kbhbrew_hist_neste_variant_btn::{_BREW_ID}").click().run()
        self.assertFalse(at.exception)
        self.assertTrue(any("utkast" in m for m in _info_tekster(at)))

        at.text_input(key="gjeldende_navn").set_value("E2E Kildebrygg v2").run()
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)
        # Selve lagre-klikket popper markøren i session_state med det
        # samme (samme "success"-gren som allerede beviser dette i
        # TestNesteVariantE2EAppTest), men "Lagre som ny kopi" kaller
        # ALDRI sin egen st.rerun() (i motsetning til "Lagre endringer"
        # ved navneendring) -- render_recipe_card() sitt banner øverst i
        # funksjonen rekker derfor allerede å bli bygget FØR knappens
        # egen suksess-gren popper markøren, SAMME scriptkjøring. Ett
        # helt vanlig, påfølgende rerun (her: ingen ny widget-hendelse i
        # det hele tatt) er derfor nødvendig for at den ALLEREDE
        # oppdaterte session_state-verdien skal reflekteres i den
        # rendrede sida -- ikke en ny bug denne saken introduserer, men
        # samme generelle "trenger én rerun for å bli synlig"-mønster
        # som selve saken handler om.
        at.run()
        self.assertFalse(at.exception)

        infoer_etter = _info_tekster(at)
        self.assertFalse(
            any("neste variant" in m and "utkast" in m for m in infoer_etter),
            f"banneret skal forsvinne etter vellykket lagring, fikk: {infoer_etter}",
        )

    def test_oppskrift_fanen_viser_ikke_banner_for_en_vanlig_oppskrift(self):
        """Regresjonsvakt: banneret skal ALDRI vises for en oppskrift som
        ikke stammer fra en "Opprett neste variant"-seed."""
        self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)

        at.selectbox(key="sidebar_recipe_selector").select("E2E Kildebrygg").run()
        self.assertFalse(at.exception)

        infoer = _info_tekster(at)
        self.assertFalse(
            any("neste variant" in m and "utkast" in m for m in infoer),
            f"banneret skal ikke vises for en ordinær, ikke-seedet oppskrift, fikk: {infoer}",
        )


if __name__ == "__main__":
    unittest.main()
