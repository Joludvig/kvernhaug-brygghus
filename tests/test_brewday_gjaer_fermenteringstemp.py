"""
Regresjonstest for #546: bryggedagsplanen viste den generelle lagerstandarden
8–12 °C som om den gjaldt den valgte gjæren (SafLager W-34/70). Dokumentert
produsentdata (masterdata-feltet `fermenteringstemp`) skal gå foran, generell
kategoriveiledning skal merkes som det, og bryggerens egen planlagte
temperatur skal holdes adskilt. App-panelet og HTML-arket deler samme
tekstkilde (modules.brewday_calc.fermenteringstemp_linjer).

Kjøres med:
    py -3 -m unittest tests.test_brewday_gjaer_fermenteringstemp -b
"""
import copy
import json
import os
import unittest

from modules.brewday_calc import bryggedag_noter, fermenteringstemp_linjer, lag_brewday_plan
from modules.brewday_template import render_brewday_html

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(_ROOT, "data", "master_gjaer_v2.json"), encoding="utf-8") as _f:
    _GJAER = json.load(_f)

_MALT_DB = {"vienna": {"display_name": "Vienna Malt", "potensiale": 1.036}}
_HUMLE_DB = {"magnum": {"display_name": "Magnum", "alfa": 12.0}}


def _plan(gjaer_id, gjaer_info):
    return lag_brewday_plan(
        malt_valg=[{"id": "vienna", "mengde": 5.0}],
        humle_valg=[{"id": "magnum", "gram": 20, "tid": 60}],
        gjaer_id=gjaer_id, gjaer_info=gjaer_info,
        og=1.050, batch_volum_l=20.0, humle_database=_HUMLE_DB, malt_database=_MALT_DB,
    )


def _ctx(planlagt=None):
    return {
        "name": "T", "brygger_stil": "", "og": 1.050, "fg": 1.012, "abv": 5.0,
        "ibu": 20.0, "ebc": 15.0, "volum": 20.0, "effektivitet": 0.75,
        "recipe": {"fermentation_temp_target_c": planlagt},
    }


class TestW3470ProdusentData(unittest.TestCase):
    def setUp(self):
        self.plan = _plan("saflager_w3470", _GJAER["saflager_w3470"])

    def test_plan_bruker_dokumentert_12_18(self):
        self.assertEqual((self.plan["temp_min"], self.plan["temp_maks"]), (12, 18))
        self.assertEqual(self.plan["temp_kilde"], "produsent")
        self.assertIn("fermentis.com", self.plan["temp_kilde_ref"])

    def test_gammel_8_12_paastand_er_borte_fra_noter(self):
        tekst = " ".join(self.plan["noter"])
        self.assertNotIn("8–12", tekst)
        self.assertNotIn("8-12", tekst)

    def test_panel_og_ark_viser_samme_linjer_med_kilde(self):
        linjer = fermenteringstemp_linjer(self.plan, None)
        self.assertEqual(len(linjer), 1)
        self.assertIn("Produsentens ideelle område: 12–18°C", linjer[0])
        self.assertIn("fermentis.com", linjer[0])
        html = render_brewday_html(_ctx(), self.plan)
        self.assertIn(linjer[0], html)
        self.assertNotIn("8–12", html)

    def test_brygerens_planlagte_temp_vises_separat_og_endrer_ikke_omraadet(self):
        linjer = fermenteringstemp_linjer(self.plan, 14.5)
        self.assertEqual(linjer[1], "Din planlagte gjæringstemperatur: 14.5°C")
        html = render_brewday_html(_ctx(14.5), self.plan)
        self.assertIn("Din planlagte gjæringstemperatur: 14.5°C", html)
        self.assertEqual((self.plan["temp_min"], self.plan["temp_maks"]), (12, 18))


class TestAndreGjaerArverIkkeW3470(unittest.TestCase):
    def test_gjaer_uten_fermenteringstemp_far_ikke_produsentpastand(self):
        # Fixture-basert (ikke en låsing av hele katalogen): en gjær uten
        # gruppen får aldri produsentopphav, selv om en annen har det.
        for k, v in _GJAER.items():
            if "fermenteringstemp" in v:
                continue
            with self.subTest(gjaer=k):
                self.assertEqual(_plan(k, v)["temp_kilde"], "generell_kategori")

    def test_annen_lagergjaer_far_merket_generell_veiledning(self):
        annen = next(
            k for k, v in _GJAER.items()
            if v.get("gjaertype") == "Lager" and k != "saflager_w3470"
        )
        plan = _plan(annen, _GJAER[annen])
        self.assertEqual(plan["temp_kilde"], "generell_kategori")
        self.assertEqual((plan["temp_min"], plan["temp_maks"]), (8, 12))
        linje = fermenteringstemp_linjer(plan)[0]
        self.assertIn("Generell veiledning", linje)
        self.assertIn("ikke dokumentert for denne gjærstammen", linje)
        self.assertNotIn("Produsentens", linje)

    def test_ukjent_gjaer_uten_data_faller_tilbake_merket(self):
        plan = _plan("finnes_ikke", {"display_name": "X"})
        self.assertEqual(plan["temp_kilde"], "generell_kategori")
        self.assertEqual((plan["temp_min"], plan["temp_maks"]), (18, 22))

    def test_ugyldig_fermenteringstemp_ignoreres(self):
        for ugyldig in ({"min_c": 18, "max_c": 12}, {"min_c": "12", "max_c": 18}, {"min_c": True, "max_c": 18}, "12-18"):
            with self.subTest(v=ugyldig):
                plan = _plan("x", {"display_name": "X", "gjaertype": "Lager", "fermenteringstemp": ugyldig})
                self.assertEqual(plan["temp_kilde"], "generell_kategori")

    def test_lagernote_har_ikke_tall_for_noen_lager(self):
        plan = _plan("x", {"display_name": "X", "gjaertype": "Lager"})
        self.assertNotIn("8–12", " ".join(plan["noter"]))
        self.assertIn("dobbel pitching rate", " ".join(plan["noter"]))  # pitch-veiledning uendret


def _gjaer_med(**endringer):
    info = copy.deepcopy(_GJAER["saflager_w3470"])
    for k, v in endringer.items():
        if v is _FJERN:
            info["fermenteringstemp"].pop(k, None)
        else:
            info["fermenteringstemp"][k] = v
    return info


_FJERN = object()


class TestBeviskravForProdusentPaastand(unittest.TestCase):
    def test_komplett_gruppe_godkjennes(self):
        self.assertEqual(_plan("x", _gjaer_med())["temp_kilde"], "produsent")

    def test_verified_at_med_tidssone_gir_kun_dato_i_ui(self):
        plan = _plan("x", _gjaer_med(verified_at="2026-11-01T17:39:54+01:00"))
        self.assertEqual(plan["temp_kilde_dato"], "2026-11-01")
        self.assertIn("kontrollert 2026-11-01)", fermenteringstemp_linjer(plan)[0])

    def test_ugyldig_kilde_krasjer_aldri_i_plan_eller_ark(self):
        plan = _plan("x", _gjaer_med(source_ref="https://["))
        self.assertEqual(plan["temp_kilde"], "generell_kategori")
        self.assertIn("Generell veiledning", render_brewday_html(_ctx(), plan))
        # Selv en manuelt konstruert plan med ugyldig kilde skal ikke krasje.
        manuell = dict(plan, temp_kilde="produsent", temp_kilde_ref="https://[", temp_kilde_dato=None)
        self.assertIn("Produsentens ideelle område", fermenteringstemp_linjer(manuell)[0])

    def test_manglende_eller_uforenlige_bevis_gir_aerlig_fallback(self):
        tilfeller = {
            "uten_betydning": {"betydning": _FJERN},
            "feil_betydning": {"betydning": "rehydration_range"},
            "uten_claim_type": {"claim_type": _FJERN},
            "feil_claim_type": {"claim_type": "assumption"},
            "uten_kildetype": {"source_type": _FJERN},
            "feil_kildetype": {"source_type": "crawler_suggestion"},
            "uten_kildehenvisning": {"source_ref": _FJERN},
            "tom_kildehenvisning": {"source_ref": ""},
            "ikke_url": {"source_ref": "fermentis datablad"},
            "uten_verified_at": {"verified_at": _FJERN},
            "ugyldig_verified_at": {"verified_at": "i går"},
            "verified_at_med_etterheng": {"verified_at": "2026-11-01T17:39:54+01:00not-a-date"},
            "verified_at_dato_med_etterheng": {"verified_at": "2026-11-01not-a-date"},
            "verified_at_kun_dato": {"verified_at": "2026-11-01"},
            "verified_at_uten_tidssone": {"verified_at": "2026-11-01T17:39:54"},
            "verified_at_ikke_tekst": {"verified_at": 20261101},
            "kilde_parserfeil": {"source_ref": "https://["},
            "kilde_uten_vert": {"source_ref": "https:///sti"},
            "kilde_feil_skjema": {"source_ref": "ftp://fermentis.com/x"},
        }
        for navn, endring in tilfeller.items():
            with self.subTest(tilfelle=navn):
                plan = _plan("x", _gjaer_med(**endring))
                self.assertEqual(plan["temp_kilde"], "generell_kategori")
                self.assertIsNone(plan["temp_kilde_ref"])
                self.assertIn("Generell veiledning", fermenteringstemp_linjer(plan)[0])
                self.assertNotIn("Produsentens", fermenteringstemp_linjer(plan)[0])

    def test_ikke_endelige_og_ikke_numeriske_grenser_avvises(self):
        inf, nan = float("inf"), float("nan")
        for navn, endring in {
            "max_inf": {"max_c": inf}, "min_minus_inf": {"min_c": -inf},
            "nan_min": {"min_c": nan}, "nan_max": {"max_c": nan},
            "bool_max": {"max_c": True}, "tekst_min": {"min_c": "12"},
            "lik": {"min_c": 15, "max_c": 15},
        }.items():
            with self.subTest(tilfelle=navn):
                plan = _plan("x", _gjaer_med(**endring))
                self.assertEqual(plan["temp_kilde"], "generell_kategori")
                for linje in fermenteringstemp_linjer(plan):
                    self.assertNotIn("inf", linje)
                    self.assertNotIn("nan", linje)

    def test_ikke_endelig_planlagt_mal_vises_ikke(self):
        plan = _plan("saflager_w3470", _GJAER["saflager_w3470"])
        for v in (float("inf"), float("-inf"), float("nan"), True, "14", None):
            with self.subTest(v=v):
                self.assertEqual(len(fermenteringstemp_linjer(plan, v)), 1)
                self.assertNotIn("planlagte", render_brewday_html(_ctx(v), plan))

    def test_brukerens_mal_beholdes_uten_faglige_grenser(self):
        plan = _plan("saflager_w3470", _GJAER["saflager_w3470"])
        for v, tekst in ((2, "2°C"), (-3.5, "-3.5°C"), (35, "35°C")):
            with self.subTest(v=v):
                self.assertIn(f"Din planlagte gjæringstemperatur: {tekst}", fermenteringstemp_linjer(plan, v))


class TestGjaerpanelHjelpEr(unittest.TestCase):
    def test_hjelp_er_ikke_motstridende_paa_no_og_en(self):
        from modules.i18n import TEKSTER as _TEKSTER
        for sprak, forbudt in (("no", "lagrer ikke et verifisert"), ("en", "does not store a verified")):
            with self.subTest(sprak=sprak):
                tekst = _TEKSTER[sprak]["gjaering.temp_maal.hjelp"]
                self.assertNotIn(forbudt, tekst)
                self.assertTrue("dokumentert" in tekst or "documented" in tekst)
                self.assertTrue("ale varmt" in tekst or "ales warm" in tekst)  # guardrail beholdt


class TestSprakNoOgEn(unittest.TestCase):
    """Faktisk rendret NO/EN for panel (via felles helper + ekte AppTest) og
    eksportert ark. Eldre språkgjeld i resten av bryggedagsvisningen er
    registrert separat (#548) og testes ikke her."""

    def setUp(self):
        self.w = _plan("saflager_w3470", _GJAER["saflager_w3470"])
        annen = next(k for k, v in _GJAER.items() if v.get("gjaertype") == "Lager" and k != "saflager_w3470")
        self.g = _plan(annen, _GJAER[annen])

    def test_w3470_no_og_en(self):
        no = fermenteringstemp_linjer(self.w, 14, "no")
        en = fermenteringstemp_linjer(self.w, 14, "en")
        self.assertEqual(no[0], "Produsentens ideelle område: 12–18°C (kilde: fermentis.com, kontrollert 2026-11-01)")
        self.assertEqual(en[0], "Manufacturer's ideal range: 12–18°C (source: fermentis.com, checked 2026-11-01)")
        self.assertEqual(no[1], "Din planlagte gjæringstemperatur: 14°C")
        self.assertEqual(en[1], "Your planned fermentation temperature: 14°C")

    def test_generell_fallback_no_og_en(self):
        self.assertEqual(
            fermenteringstemp_linjer(self.g, None, "no")[0],
            "Generell veiledning for gjærtypen: 8–12°C (ikke dokumentert for denne gjærstammen)")
        self.assertEqual(
            fermenteringstemp_linjer(self.g, None, "en")[0],
            "General guidance for the yeast type: 8–12°C (not documented for this yeast strain)")

    def test_lagernote_no_og_en(self):
        self.assertEqual(bryggedag_noter(self.w, "no"), ["Lagergjær — fermenterer kaldere enn ale. Bruk dobbel pitching rate."])
        self.assertEqual(bryggedag_noter(self.w, "en"), ["Lager yeast — ferments cooler than ale. Use a double pitching rate."])

    def test_ukjent_sprak_faller_tilbake_til_norsk_og_andre_noter_urort(self):
        self.assertIn("Produsentens", fermenteringstemp_linjer(self.w, None, "xx")[0])
        kveik = _plan("k", {"display_name": "K", "gjaertype": "Kveik"})
        self.assertEqual(bryggedag_noter(kveik, "en"), kveik["noter"])  # ikke utvidet (#548)

    def test_eksportert_ark_no_og_en_deler_kilde_med_panelet(self):
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                html = render_brewday_html(_ctx(14), self.w, sprak=sprak)
                for linje in fermenteringstemp_linjer(self.w, 14, sprak):
                    self.assertIn(linje.replace("'", "&#x27;"), html)
                self.assertIn(bryggedag_noter(self.w, sprak)[0], html)
        en = render_brewday_html(_ctx(14), self.w, sprak="en")
        self.assertNotIn("Produsentens", en)
        self.assertNotIn("Lagergjær", en)
        self.assertNotIn("Din planlagte", en)
        # standard uten sprak-argument er uendret norsk
        self.assertIn("Produsentens ideelle område", render_brewday_html(_ctx(14), self.w))

    def test_sprakbytte_endrer_ikke_omraade_eller_maal(self):
        for sprak in ("no", "en"):
            linjer = fermenteringstemp_linjer(self.w, 14, sprak)
            self.assertIn("12–18°C", linjer[0])
            self.assertIn("14°C", linjer[1])
        self.assertEqual((self.w["temp_min"], self.w["temp_maks"]), (12, 18))


class TestPanelSprakAppTest(unittest.TestCase):
    """Ekte ui/brewday_panel.py via AppTest."""

    _APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_brewday_ferm_temp_app.py")

    def _kjor(self, sprak, gjaer_id="saflager_w3470", maal=14.0):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(self._APP, default_timeout=30)
        at.session_state["sprak"] = sprak
        at.session_state["valgt_gjaer_id"] = gjaer_id
        at.session_state["gjaering_temp_maal_c"] = maal
        at.run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        tekst = " ".join(str(m.value) for m in at.markdown) + " " + " ".join(str(i.value) for i in at.info)
        return tekst

    def test_panel_viser_en_og_no(self):
        en = self._kjor("en")
        self.assertIn("Manufacturer's ideal range: 12–18°C (source: fermentis.com, checked 2026-11-01)", en)
        self.assertIn("Your planned fermentation temperature: 14°C", en)
        self.assertIn("Lager yeast — ferments cooler than ale. Use a double pitching rate.", en)
        self.assertNotIn("Produsentens ideelle", en)
        no = self._kjor("no")
        self.assertIn("Produsentens ideelle område: 12–18°C (kilde: fermentis.com, kontrollert 2026-11-01)", no)
        self.assertIn("Din planlagte gjæringstemperatur: 14°C", no)
        self.assertIn("Lagergjær — fermenterer kaldere enn ale. Bruk dobbel pitching rate.", no)

    def test_panel_generell_fallback_en(self):
        annen = next(k for k, v in _GJAER.items() if v.get("gjaertype") == "Lager" and k != "saflager_w3470")
        en = self._kjor("en", gjaer_id=annen, maal=None)
        self.assertIn("General guidance for the yeast type: 8–12°C (not documented for this yeast strain)", en)
        self.assertNotIn("Manufacturer's ideal range", en)
        self.assertNotIn("planned fermentation temperature", en)


class TestMasterdataIntegritet(unittest.TestCase):
    def test_w3470_felt_har_dokumentert_proveniens(self):
        ft = _GJAER["saflager_w3470"]["fermenteringstemp"]
        self.assertEqual((ft["min_c"], ft["max_c"]), (12, 18))
        self.assertEqual(ft["claim_type"], "documented_fact")
        self.assertTrue(ft["source_ref"].startswith("https://fermentis.com/"))
        self.assertEqual(ft["verified_at"], "2026-11-01T17:39:54+01:00")
        self.assertIsNone(ft["source_date"])

    def test_identitet_og_attenuation_uendret(self):
        e = _GJAER["saflager_w3470"]
        self.assertEqual(e["display_name"], "SafLager W-34/70")
        self.assertEqual(e["attenuation"], 0.82)
        self.assertEqual(e["gjaertype"], "Lager")


if __name__ == "__main__":
    unittest.main()
