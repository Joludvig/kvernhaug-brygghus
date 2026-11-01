"""
#548 — konsekvent NO/EN i bryggedagsflyten: bryggemåte (prosesspanelet),
vannkjemi, bryggedagsplanen (ui/brewday_panel.py) og det eksporterte
bryggedagsarket.

To lag, holdt adskilt:
  * AppTest (ekte panelkode, Streamlit-testrammeverket) -- det er IKKE en
    nettleserkontroll; ingen nettleser er brukt.
  * Rendret HTML fra render_brewday_html() for eksporten.

Dekker faktisk rendret tekst på begge språk, språkbytte NO -> EN -> NO,
dynamiske anbefalinger/varsler, og at beregninger, lagrede data (profil-
navn, id-er), brukerens egne tekster og planlagt gjæringstemperatur er
uendret av språkvalget.
"""
import copy
import html as _html
import os
import re
import unittest
from unittest import mock

from modules.brewday_calc import lag_brewday_plan
from modules.brewday_template import render_brewday_html
from modules.i18n import SPRAK_DEFAULT, TEKSTER, t
from modules.i18n_bryggedag import BRYGGEDAG_TEKSTER
from modules.process_profiles import (
    STANDARDPROFILER, anbefal_prosess, hent_standardprofil, normaliser_prosessprofil,
    profiltekst_visning, profilnavn_visning, mesketrinn_kommentar_visning,
    vanskelighetsgrad_visning, maskeplan_steg_visning,
)
from modules.water_chemistry import (
    alle_salter, anbefal_vannmaal, foreslaa_salter, generer_varsler, last_vannmaal,
    maalprofil_tekst, tomt_kildevann,
)

_HER = os.path.dirname(os.path.abspath(__file__))
_BREWDAY_APP = os.path.join(_HER, "_brewday_flow_i18n_app.py")
_PROSESS_APP = os.path.join(_HER, "_process_panel_app.py")
_VANN_APP = os.path.join(_HER, "_water_flow_i18n_app.py")

# Norske systemord som IKKE skal finnes i engelsk visning av de fire delene.
# (Oppskriftsnavn, stilnavn og andre brukerdata er bevisst holdt utenfor
# fixturene, eller listet i _TILLATT under.)
_NORSK_MARKORER = [
    "Meskevann", "Skyllevann", "Humle", "Gjær", "Bryggemåte", "Bryggeplan", "Vannkjemi",
    "Kildevann", "Målprofil", "Lagre ", "Tilsetning", "Koketid", "Mesking", "Sjekkliste",
    "Notater", "anbefalt", "Velg ", "Fjern", "Legg til", "Batchnummer", "Bryggedato",
    "Opprinnelse", "ukjent", "målområdet", "kjelekapasitet", "Kvernhaug-husprofil",
    "Vanskelighetsgrad", "Skyllemetode", "Dekoksjon", "Dobbelmesk", "Oppskrift",
    "Ingen ", "Kjøp", "Gjæring", "overskrider", "Pitching-temperatur", "Faktisk", "Beregnet",
    "Vann ", "Syre ", "tykkmesk", "ferskt vann", "Målt ", "Mål:",
    "Avvik", "Planlagt", "Effektivitet", "Brygghus", "pakke(r)", "Prøven", "Rediger",
]
# Brukerens/produktets egne navn og en eksplisitt utenfor-scope-knapp
# (Start nytt brygg / Brygghistorikk er en egen flyt, se sluttrapporten).
_TILLATT = ["Start nytt brygg", "Brygghistorikk", "Brew History", "Sommerglød", "Sommerstil",
            "Jordalsvatnet 2025", "Kvernhaug Brygghus", "Historisk Wiesn-Märzen"]


def _alle_tekster(at):
    """All synlig tekst (innhold, labels, plassholdere, alternativer) fra
    AppTest-treet."""
    ut = []
    for liste in (at.markdown, at.caption, at.info, at.warning, at.success, at.error,
                  at.subheader, at.toast):
        ut.extend(str(e.value) for e in liste)
    for e in at.metric:
        ut.append(f"{e.label} = {e.value}")
    for liste in (at.expander, at.checkbox, at.text_input, at.number_input, at.date_input,
                  at.multiselect, at.button, at.selectbox, at.slider, at.text_area):
        for e in liste:
            ut.append(str(e.label))
            if getattr(e, "placeholder", None):
                ut.append(str(e.placeholder))
            if hasattr(e, "options") and liste is not at.multiselect:
                ut.extend(str(o) for o in e.options)
            if liste is at.multiselect:
                ut.extend(str(o) for o in e.options)
    return ut


def _norske_treff(tekster):
    treff = []
    for tekst in tekster:
        renset = tekst
        for ok in _TILLATT:
            renset = renset.replace(ok, "")
        for m in _NORSK_MARKORER:
            if m in renset:
                treff.append((m, tekst[:140]))
    return treff


def _kjor(app, sprak, **state):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(app, default_timeout=60)
    at.session_state["sprak"] = sprak
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _bytt(at, sprak):
    at.session_state["sprak"] = sprak
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


# ── Tekstkatalogen ────────────────────────────────────────────────────────────
class TestKatalog(unittest.TestCase):
    def test_nokler_er_symmetriske_og_i_hovedkatalogen(self):
        self.assertEqual(set(BRYGGEDAG_TEKSTER["no"]), set(BRYGGEDAG_TEKSTER["en"]))
        for sprak in ("no", "en"):
            for nokkel in BRYGGEDAG_TEKSTER["no"]:
                self.assertIn(nokkel, TEKSTER[sprak])
        self.assertEqual(set(TEKSTER["no"]), set(TEKSTER["en"]))

    def test_plassholdere_er_like_pa_no_og_en(self):
        pat = re.compile(r"\{(\w+)\}")
        for nokkel, no in BRYGGEDAG_TEKSTER["no"].items():
            self.assertEqual(set(pat.findall(no)), set(pat.findall(BRYGGEDAG_TEKSTER["en"][nokkel])), nokkel)

    def test_en_er_oversatt_bortsett_fra_navn_enheter_og_fagord(self):
        # Bevisst identiske NO/EN-tekster: produkt-/fagord og enheter som er like
        # på begge språk (Whirlfloc, Fermaid-O, «Pre-boil», «Temp (°C)», «pH» ...).
        bevisst_like = {
            "bd.tils.fermaid_o.dose", "bd.tils.fermaid_o.navn", "bd.tils.whirlfloc.navn",
            "bd.tils.yeast_nutrient.dose", "bdp.malt_tittel", "bdp.postboil_est", "bdp.postboil_tittel",
            "bdp.preboil", "bdp.preboil_sg", "bx.malt_tittel", "bx.preboil", "bx.stat.pitch",
            "bx.stat.postboil_vol", "bx.stat.preboil_sg", "bx.stat.preboil_vol", "bx.th.dose",
            "pp.stegtype.mashout", "pr.min", "pr.temp", "pr.type", "wp.ion_min", "wp.ph",
            "wp.salt", "wp.type",
        }
        lik = {k for k, v in BRYGGEDAG_TEKSTER["no"].items() if v == BRYGGEDAG_TEKSTER["en"][k]}
        self.assertEqual(lik, bevisst_like)

    def test_ukjent_nokkel_far_synlig_markering_og_norsk_er_fallback(self):
        self.assertIn("??", t("bd.finnes.ikke", "en"))
        self.assertEqual(t("bx.notater", "xx"), t("bx.notater", "no"))


# ── Standardprofiler: visning oversettes, data er uendret ────────────────────
class TestProsessprofilerVisning(unittest.TestCase):
    def test_standardtekster_oversettes_bare_ved_visning(self):
        for pid, profil in STANDARDPROFILER.items():
            kopi = copy.deepcopy(profil)
            self.assertNotEqual(profilnavn_visning(profil["navn"], "en", pid), profil["navn"], pid)
            for felt in ("beskrivelse", "utstyrsbegrensninger", "forventet_paavirkning"):
                if profil[felt]:
                    self.assertNotEqual(profiltekst_visning(felt, profil[felt], pid, "en"), profil[felt], (pid, felt))
                    self.assertEqual(profiltekst_visning(felt, profil[felt], pid, "no"), profil[felt])
            self.assertEqual(profil, kopi, "visning muterte standardprofilen")
        for v in ("Lett", "Middels", "Krevende"):
            self.assertNotEqual(vanskelighetsgrad_visning(v, "en"), v)
            self.assertEqual(vanskelighetsgrad_visning(v, "no"), v)

    def test_mesketrinnkommentarer_og_dekoksjonskommentar_oversettes(self):
        for pid, profil in STANDARDPROFILER.items():
            for steg in profil["mash_steps"]:
                if steg["kommentar"]:
                    self.assertNotEqual(mesketrinn_kommentar_visning(steg["kommentar"], pid, "en"), steg["kommentar"])
        dek = STANDARDPROFILER["enkel_dekoksjon"]["decoction_steps"][0]["kommentar"]
        self.assertNotEqual(mesketrinn_kommentar_visning(dek, "enkel_dekoksjon", "en"), dek)

    def test_tekstkollisjon_egne_navn_og_kommentarer_beholdes(self):
        # Egne navn/kommentarer som tilfeldigvis er lik en systemtekst.
        for kollisjon in ("Lett", "Middels", "Krevende", "Infusjon", "Mashout", "Enkel infusjon",
                          "Lavere temperaturhvile", "Hovedmesk — enzymatisk konvertering"):
            self.assertEqual(profilnavn_visning(kollisjon, "en", "egendefinert"), kollisjon)
            self.assertEqual(mesketrinn_kommentar_visning(kollisjon, "egendefinert", "en"), kollisjon)
        self.assertEqual(profilnavn_visning("Lett", "en", "egendefinert"), "Lett")
        self.assertEqual(profilnavn_visning("Enkel infusjon", "en", "egendefinert"), "Enkel infusjon")
        # Ingen kontekst (ukjent/manglende process_id) gir aldri oversettelse.
        self.assertEqual(profilnavn_visning("Enkel infusjon", "en"), "Enkel infusjon")
        self.assertEqual(profilnavn_visning("Enkel infusjon", "en", "min_egen_id"), "Enkel infusjon")
        # En standardprofils felt oversettes ikke når teksten er en annen enn standardens.
        self.assertEqual(profilnavn_visning("Lett", "en", "hochkurz"), "Lett")
        self.assertEqual(mesketrinn_kommentar_visning("Mesk 1 — fersk vann", "hochkurz", "en"), "Mesk 1 — fersk vann")
        # Egendefinert uten standardtekst i X
        self.assertEqual(
            profilnavn_visning("Egendefinert – basert på Lett", "en", "egendefinert"),
            "Custom – based on Lett",
        )

    def test_brukerens_egne_tekster_og_navn_beholdes(self):
        self.assertEqual(profilnavn_visning("Mors hytteprosess", "en", "egendefinert"), "Mors hytteprosess")
        self.assertEqual(
            profilnavn_visning("Egendefinert – basert på Hochkurz (stegmesk)", "en", "egendefinert"),
            "Custom – based on Hochkurz (step mash)",
        )
        self.assertEqual(
            profilnavn_visning("Egendefinert – basert på Mors prosess", "en", "egendefinert"),
            "Custom – based on Mors prosess",
        )

    def test_normalisering_er_sprakuavhengig(self):
        a = normaliser_prosessprofil(hent_standardprofil("hochkurz"))
        self.assertEqual(a["navn"], "Hochkurz (stegmesk)")
        self.assertEqual(a["mash_steps"][0]["kommentar"], "Lavere temperaturhvile")

    def test_anbefalingsmotor_no_uendret_og_en_oversatt(self):
        eq = {"kettle_capacity_l": 35.0, "mash_ratio_l_per_kg": 3.2}
        for stil, historisk, kg, og in (
            ("Märzen", False, 5.0, 1.055), ("Historisk Wiesn-Märzen", True, 5.0, 1.055),
            ("Pale Ale", False, 5.0, 1.050), ("Pale Ale", False, 5.0, 1.090),
            ("Pale Ale", False, 30.0, 1.050),
        ):
            id_no, b_no = anbefal_prosess(stil, {"og": og}, kg, eq, historisk)
            id_en, b_en = anbefal_prosess(stil, {"og": og}, kg, eq, historisk, sprak="en")
            self.assertEqual(id_no, id_en)  # valget er uavhengig av språk
            self.assertEqual(len(b_no), len(b_en))
            self.assertNotEqual(b_no, b_en)
            for linje in b_en:
                self.assertFalse(_norske_treff([linje.replace(stil, "")]), linje)


# ── Vannkjemi: logikk ────────────────────────────────────────────────────────
class TestVannkjemiLogikk(unittest.TestCase):
    def _varsler(self, sprak):
        kilde = {**tomt_kildevann(), "na": 80.0, "mg": 30.0, "cl": 300.0, "so4": 300.0, "ca": 10.0}
        sluttprofil = {
            "start": dict(kilde), "tilfort": {}, "slutt": dict(kilde),
        }
        maal = {"ca_min": 50, "ca_max": 65, "mg_min": 0, "mg_max": 8, "na_min": 0, "na_max": 20,
                "cl_min": 50, "cl_max": 70, "so4_min": 30, "so4_max": 45, "hco3_min": 25, "hco3_max": 60}
        fordeling = [{"salt_id": "gips", "gram": 0.04, "gram_mesk": 0.02, "gram_skyll": 0.0}]
        syrer = [{"syre_id": "melkesyre", "navn": "Melkesyre", "prosent": None, "mengde_ml": 1.0}]
        return generer_varsler(kilde, maal, sluttprofil, fordeling, syrer=syrer, sprak=sprak)

    def test_varsler_no_er_uendret_standard_og_en_er_oversatt(self):
        no = self._varsler("no")
        self.assertEqual(no, self._varsler(SPRAK_DEFAULT))
        en = self._varsler("en")
        self.assertEqual(len(no), len(en))
        self.assertGreaterEqual(len(en), 9)  # representative: Na, Mg, Cl, SO4, Ca lav, mål, kilde, syre, vekt
        for linje in en:
            self.assertFalse(_norske_treff([linje]), linje)
        self.assertTrue(any("sodium" in v for v in en))
        self.assertTrue(any("is below the target range" in v for v in en))
        self.assertTrue(any("Lactic acid" in v for v in en))
        self.assertTrue(any("Gypsum" in v for v in en))

    def test_ukjent_kilde_og_hco3_varsler(self):
        tom = {"start": tomt_kildevann(), "tilfort": {}, "slutt": tomt_kildevann()}
        self.assertEqual(generer_varsler(tomt_kildevann(), None, tom, [], sprak="en"),
                         ["Source water is unknown — no ion values are registered. The app does not make up numbers."])
        halv = {**tomt_kildevann(), "ca": 50.0}
        v = generer_varsler(halv, None, {"start": halv, "tilfort": {}, "slutt": halv}, [], sprak="en")
        self.assertIn("Alkalinity/HCO3 is missing for the source water — the mash pH assessment becomes less reliable.", v)

    def test_saltforslag_forklaring_no_og_en(self):
        kilde = {**tomt_kildevann(), "ca": 5.0, "cl": 5.0, "so4": 5.0, "hco3": 200.0}
        maal = {"cl_min": 50, "cl_max": 70, "so4_min": 30, "so4_max": 45, "hco3_min": 25, "hco3_max": 60,
                "ca_min": 50, "ca_max": 65, "mg_min": 0, "mg_max": 8, "na_min": 0, "na_max": 20}
        f_no, forkl_no = foreslaa_salter(kilde, maal, 20.0)
        f_en, forkl_en = foreslaa_salter(kilde, maal, 20.0, sprak="en")
        self.assertEqual(f_no, f_en)  # selve forslaget (gram) er språkuavhengig
        self.assertIn("kan IKKE nås", forkl_no)
        self.assertIn("can NOT be reached", forkl_en)
        self.assertFalse(_norske_treff([forkl_en]), forkl_en)
        self.assertEqual(foreslaa_salter(kilde, maal, 0, sprak="en")[1],
                         "Invalid water volume — cannot calculate a salt suggestion.")
        self.assertIn("Ugyldig vannvolum", foreslaa_salter(kilde, maal, 0)[1])

    def test_anbefalt_maalprofil_og_profiltekster(self):
        maal = last_vannmaal()
        tid, begr = anbefal_vannmaal("Pale Ale", maal, sprak="en")
        self.assertEqual(tid, anbefal_vannmaal("Pale Ale", maal)[0])
        self.assertIn("is listed under recommended styles for “Hop-forward beer”", begr[0])
        tid2, begr2 = anbefal_vannmaal("Ukjent stil", maal, sprak="en")
        self.assertEqual(tid2, "balansert_ale")
        self.assertIn("“Balanced ale” is a neutral starting point", begr2[0])
        self.assertEqual(maalprofil_tekst(maal["balansert_ale"], "name", "en"), "Balanced ale")
        self.assertEqual(maalprofil_tekst(maal["balansert_ale"], "name", "no"), "Balansert ale")
        # Omdøpt/redigert profil og brukerens egne profiler vises ALLTID uendret.
        redigert = {**maal["balansert_ale"], "name": "Mitt vann hjemme"}
        self.assertEqual(maalprofil_tekst(redigert, "name", "en"), "Mitt vann hjemme")
        egen = {"target_id": "min_egen", "name": "Balansert ale"}
        self.assertEqual(maalprofil_tekst(egen, "name", "en"), "Balansert ale")

    def test_alle_medfoelgende_malprofiler_har_en_visning(self):
        for tid, profil in last_vannmaal().items():
            for felt in ("name", "description", "kort_hjelpetekst"):
                self.assertNotEqual(maalprofil_tekst(profil, felt, "en"), profil[felt], (tid, felt))
        from modules.water_chemistry import salt_navn
        for salt in alle_salter():
            self.assertNotEqual(salt_navn(salt["salt_id"], "en"), salt["navn"], salt["salt_id"])
            self.assertEqual(salt_navn(salt["salt_id"], "no"), salt["navn"])


# ── Bryggedagsplan: beregninger er språkuavhengige ───────────────────────────
_MALT_DB = {"vienna": {"display_name": "Vienna Malt", "potensiale": 1.036}}
_HUMLE_DB = {"magnum": {"display_name": "Magnum", "alfa": 12.0}}


def _plan(sprak, profil_id="reiterated_mash", tils=("whirlfloc", "fermaid_o"), gjaertype="Lager"):
    return lag_brewday_plan(
        malt_valg=[{"id": "vienna", "mengde": 25.0}],
        humle_valg=[{"id": "magnum", "gram": 20, "tid": 90}],
        gjaer_id="g", gjaer_info={"display_name": "Min gjær", "gjaertype": gjaertype},
        og=1.050, batch_volum_l=30.0, humle_database=_HUMLE_DB, malt_database=_MALT_DB,
        tilsetninger_valgt=list(tils),
        process_profile=hent_standardprofil(profil_id) if profil_id else None,
        sprak=sprak,
    )


_TEKSTFELT = {"utstyrsvarsler", "reiterated_mash_flyt", "tilsetninger", "noter", "noter_nokler"}


class TestPlanBeregningUendret(unittest.TestCase):
    def test_tall_og_struktur_er_identiske_pa_no_og_en(self):
        for profil_id in (None, "enkel_infusjon", "hochkurz", "enkel_dekoksjon", "reiterated_mash"):
            no, en = _plan("no", profil_id), _plan("en", profil_id)
            self.assertEqual(set(no), set(en))
            for k in no:
                if k not in _TEKSTFELT:
                    self.assertEqual(no[k], en[k], (profil_id, k))
            if no["reiterated_mash_flyt"]:
                for k, v in no["reiterated_mash_flyt"].items():
                    if k != "varsler":
                        self.assertEqual(v, en["reiterated_mash_flyt"][k])
            self.assertEqual(len(no["utstyrsvarsler"]), len(en["utstyrsvarsler"]))
            self.assertEqual(no["tilsetninger"], en["tilsetninger"])

    def test_no_planen_har_samme_tekst_som_for_548(self):
        plan = _plan("no")
        self.assertEqual(plan["reiterated_mash_flyt"]["varsler"][0],
                         "Lang bryggedag: to fulle meske- og lauteresykluser etter hverandre.")
        self.assertTrue(plan["utstyrsvarsler"][0].startswith("Mesk 1: estimert meskevolum"))
        self.assertEqual(plan["noter"], ["Lagergjær — fermenterer kaldere enn ale. Bruk dobbel pitching rate."])

    def test_en_plan_har_oversatte_dynamiske_varsler(self):
        plan = _plan("en")
        tekst = plan["reiterated_mash_flyt"]["varsler"] + plan["utstyrsvarsler"]
        self.assertTrue(any("exceeds the kettle capacity" in x for x in tekst))
        self.assertFalse(_norske_treff(tekst), tekst)


# ── Eksportert ark ───────────────────────────────────────────────────────────
def _ctx(navn="Sommerglød"):
    return {
        "name": navn, "brygger_stil": "Sommerstil", "og": 1.050, "fg": 1.012, "abv": 5.0,
        "ibu": 20.0, "ebc": 15.0, "volum": 30.0, "effektivitet": 0.75,
        "recipe": {"fermentation_temp_target_c": 14.0},
    }


def _vann(maal_id="kvernhaug_maltpreget_tysk_lager", kilde_id="__ukjent__"):
    maal = dict(last_vannmaal()[maal_id])
    return {
        "kilde": {"water_id": kilde_id, "name": "Ukjent kildevann"} if kilde_id == "__ukjent__"
        else {"water_id": kilde_id, "name": "Jordalsvatnet 2025"},
        "maal": maal,
        "behandling": {"salter": [
            {"salt_id": "cacl2_vannfri", "navn": "Kalsiumklorid (vannfri)", "kjemisk_form": "CaCl2",
             "gram_mesk": 2.0, "gram_skyll": 1.0},
            {"salt_id": "gips", "navn": "Gips", "kjemisk_form": "CaSO4·2H2O", "gram_mesk": 1.5, "gram_skyll": 0.0},
        ]},
        "maalinger": {"maalt_mash_ph": 5.4, "malt_ved_romtemperatur": True, "syrer": [
            {"syre_id": "melkesyre", "navn": "Melkesyre", "mengde_ml": 2.0, "prosent": None},
            {"syre_id": "fosforsyre", "navn": "Fosforsyre", "mengde_ml": 1.0, "prosent": 10.0},
        ]},
    }


def _tekst_av_html(html):
    kropp = html.split("</style>", 1)[1]
    return _html.unescape(re.sub(r"<[^>]+>", " ", kropp).replace("&nbsp;", " "))


class TestEksportNoOgEn(unittest.TestCase):
    def _html(self, sprak, profil_id="reiterated_mash", **kw):
        plan = _plan(sprak, profil_id)
        log = {"pre_boil_sg": 1.040, "pre_boil_vol": 38.0, "post_boil_vol": 31.0, "og": "1.049",
               "fg": "1.011", "abv": "5.0", "pitch_temp": 12.0, "mash_eff": 0.7, "brewhouse_eff": 0.74}
        return render_brewday_html(_ctx(), plan, log, water=_vann(**kw), sprak=sprak)

    def test_en_ark_har_ingen_norsk_systemtekst(self):
        for profil_id in (None, "hochkurz", "enkel_dekoksjon", "reiterated_mash"):
            html = self._html("en", profil_id)
            self.assertIn('<html lang="en">', html)
            tekst = _tekst_av_html(html)
            self.assertFalse(_norske_treff([tekst]), (profil_id, _norske_treff([tekst])))
            self.assertIn("Brew day sheet — Sommerglød", html)

    def test_en_ark_innhold(self):
        html = self._html("en", "reiterated_mash")
        for forventet in (
            "Brewing method: Reiterated mash (double mash)", "Water source: <strong>Unknown source water</strong>",
            "Target profile: <strong>Malt-forward German lager</strong>",
            "Calcium chloride (anhydrous) (CaCl2) in mash water: <strong>2.00 g</strong>",
            "Gypsum (CaSO4·2H2O) in mash water: <strong>1.50 g</strong>",
            "Calcium chloride (anhydrous) (CaCl2) in sparge water: <strong>1.00 g</strong>",
            "Lactic acid 2.0 mL (concentration not specified)", "Phosphoric acid 1.0 mL (10%)",
            "Room temperature", "Double mash: Mash 1", "Whirlfloc", "½ tablet per 20 L",
            "15 min before end of boil", "Fermaid-O", "Start of fermentation (0–24 h)",
            "DEVIATION: hop time exceeds total boil time", "Planned IBU", "Actually achievable IBU",
            "Manufacturer's", "General guidance", "Your planned fermentation temperature: 14°C",
            "Lager yeast — ferments cooler than ale.", "Brew day checklist", "Cold crash / packaging",
            "Brewhouse efficiency (plan: 75%)", "Efficiency 75%", "Target: ", "Actual:", "Measured:",
            "Mash 2 — mash water is wort from mash 1",
        ):
            if forventet in ("Manufacturer's",):
                continue
            self.assertIn(forventet, html, forventet)

    def test_no_ark_er_uendret_norsk(self):
        html = self._html("no", "reiterated_mash")
        self.assertIn('<html lang="no">', html)
        for forventet in (
            "Bryggedagsark — Sommerglød", "Bryggemåte: Reiterated mash (dobbel mesk)",
            "Vannkilde: <strong>Ukjent kildevann</strong>", "Målprofil: <strong>Maltpreget tysk lager</strong>",
            "i meskevann: <strong>2.00 g</strong>", "Melkesyre 2.0 mL (konsentrasjon ikke angitt)",
            "Romtemperatur", "Dobbelmesk: Mesk 1", "½ tablett per 20 L", "15 min til kok slutt",
            "AVVIK: humletid overstiger total koketid", "Bryggedags-sjekkliste", "Cold crash / tapping",
            "Brygghuseffektivitet (plan: 75%)", "Effektivitet 75%", "pakke(r) anbefalt",
            "Din planlagte gjæringstemperatur: 14°C", "Notater", "Faktisk:", "Målt:",
        ):
            self.assertIn(forventet, html, forventet)

    def test_brukerdata_og_tall_er_uendret_mellom_sprak(self):
        no, en = self._html("no", "hochkurz"), self._html("en", "hochkurz")
        for beholdt in ("Sommerglød", "Sommerstil", "Magnum", "Min gjær", "1.049", "1.011",
                        "12.0°C", "70.0%", "74.0%", "14°C"):
            self.assertIn(beholdt, no)
            self.assertIn(beholdt, en)
        tall = lambda h: re.findall(r"\d+(?:\.\d+)?", _tekst_av_html(h))
        self.assertEqual(tall(no), tall(en))

    def test_omdobt_maalprofil_og_egen_kilde_beholdes_i_en(self):
        vann = _vann(kilde_id="egen_bronn")
        vann["maal"]["name"] = "Mitt vann hjemme"
        html = render_brewday_html(_ctx(), _plan("en"), {}, water=vann, sprak="en")
        self.assertIn("<strong>Mitt vann hjemme</strong>", html)
        self.assertIn("<strong>Jordalsvatnet 2025</strong>", html)
        self.assertNotIn("Unknown source water", html)

    def test_ukjent_sprak_gir_norsk_ark(self):
        html = render_brewday_html(_ctx(), _plan("no"), {}, water=_vann(), sprak="xx")
        self.assertIn("Bryggedags-sjekkliste", html)

    def test_ark_uten_vannprofil_og_uten_profil_kraesjer_ikke(self):
        html = render_brewday_html(_ctx(), _plan("en", None), None, sprak="en")
        self.assertIn("Target profile: <strong>Not selected</strong>", html)


# ── Bryggedagsplan i appen (AppTest) ─────────────────────────────────────────
class TestBryggedagspanelAppTest(unittest.TestCase):
    PROFILER = (None, "hochkurz", "enkel_dekoksjon", "reiterated_mash")

    def _kjor_panel(self, sprak, profil_id=None, **state):
        s = dict(state)
        if profil_id:
            s["aktiv_prosessprofil"] = hent_standardprofil(profil_id)
        return _kjor(_BREWDAY_APP, sprak, **s)

    def test_en_panel_har_ingen_norsk_systemtekst(self):
        for profil_id in self.PROFILER:
            at = self._kjor_panel("en", profil_id)
            treff = _norske_treff(_alle_tekster(at))
            self.assertFalse(treff, (profil_id, treff))

    def test_en_panel_representativt_innhold(self):
        at = self._kjor_panel("en", "reiterated_mash")
        tekst = "\n".join(_alle_tekster(at))
        for forventet in (
            "Brewing method: **Reiterated mash (double mash)**", "Double mash: Mash 1",
            "Hop additions", "Time left", "Added after", "BrewZilla 35 Gen4", "exceeds the recommended maximum of 30 L",
            "Long brew day", "exceeds the kettle capacity of 35 L", "Wort from mash 1",
            "hop addition(s) marked above have a longer own boil time", "IBU — actually achievable in this process",
            "Whirlfloc", "Fining agent.", "Organic yeast nutrient", "Select additions",
            "Brew day checklist", "Equipment clean", "Generate brew day sheet",
            "locked until the deviation above is confirmed", "Save OG/FG/post-boil volume + brew date",
            "Enter pre-boil SG and volume (Step 3) for mash efficiency.",
            "Lager yeast — ferments cooler than ale.", "Mash 1 — fresh water",
        ):
            self.assertIn(forventet, tekst, forventet)

    def test_dekoksjon_i_en(self):
        at = self._kjor_panel("en", "enkel_dekoksjon", valgt_malt=[{"id": "vienna", "mengde": 5.0}])
        tekst = "\n".join(_alle_tekster(at))
        self.assertIn("Decoction: pull **", tekst)
        self.assertIn("of thick mash at 63.0°C", tekst.replace("63°C", "63.0°C"))
        self.assertFalse(_norske_treff(_alle_tekster(at)))

    def test_no_panel_uendret_norsk_og_ingen_engelsk_systemtekst(self):
        at = self._kjor_panel("no", "reiterated_mash")
        tekst = "\n".join(_alle_tekster(at))
        for forventet in (
            "Bryggemåte: **Reiterated mash (dobbel mesk)**", "Humletilsetninger", "Tid igjen", "Tilsatt etter",
            "BrewZilla 35 Gen4", "overskrider anbefalt maks 30 L", "Lang bryggedag", "overskrider kjelekapasitet",
            "Jeg har sett avviket", "Bryggedagsarket er låst", "Generer Bryggedagsark", "Bryggedags-sjekkliste",
            "Utstyr rent", "Lagergjær — fermenterer kaldere enn ale.", "½ tablett per 20 L",
            "Lagre OG/FG/post-boil-volum + bryggedato", "Meskevann", "Gjær & Fermentering",
        ):
            self.assertIn(forventet, tekst, forventet)
        for engelsk in ("Hop additions", "Time left", "Brew day checklist", "Generate brew day sheet",
                        "Select additions", "Equipment clean"):
            self.assertNotIn(engelsk, tekst, engelsk)

    def test_sprakbytte_no_en_no_gir_identisk_visning_og_urort_tilstand(self):
        for profil_id in (None, "reiterated_mash"):
            at = self._kjor_panel("no", profil_id, gjaering_temp_maal_c=14.0)
            forste_no = _alle_tekster(at)
            state_for = {k: copy.deepcopy(at.session_state[k]) for k in
                         ("valgt_malt", "valgt_humle", "valgt_gjaer_id", "bd_tilsetninger", "gjaering_temp_maal_c")}
            profil_for = copy.deepcopy(at.session_state["aktiv_prosessprofil"])
            _bytt(at, "en")
            en = _alle_tekster(at)
            self.assertNotEqual(forste_no, en)
            self.assertFalse(_norske_treff(en), _norske_treff(en))
            self.assertIn("Your planned fermentation temperature: 14°C", "\n".join(en))
            for k, v in state_for.items():
                self.assertEqual(at.session_state[k], v, f"{k} endret av språkbytte")
            self.assertEqual(at.session_state["aktiv_prosessprofil"], profil_for)
            _bytt(at, "no")
            self.assertEqual(_alle_tekster(at), forste_no)
            self.assertIn("Din planlagte gjæringstemperatur: 14°C", "\n".join(_alle_tekster(at)))

    def test_eksport_fra_panelet_far_valgt_sprak_og_gir_samme_tall(self):
        faktisk = {}
        ekte = render_brewday_html

        def spion(*a, **kw):
            html = ekte(*a, **kw)
            faktisk["sprak"] = kw.get("sprak")
            faktisk["html"] = html
            return html

        resultater = {}
        for sprak in ("no", "en"):
            faktisk.clear()
            with mock.patch("ui.brewday_panel.render_brewday_html", spion):
                at = self._kjor_panel(sprak, "hochkurz")
                at.session_state["bd_bekreft"] = True
                for cb in at.checkbox:
                    if str(cb.key).startswith("bd_bekreft_humletid_avvik::"):
                        cb.check()
                at.run()
                at.button(key="brewday_print_btn").click().run()
            self.assertFalse(at.exception, [e.value for e in at.exception])
            self.assertEqual(faktisk.get("sprak"), sprak)
            resultater[sprak] = faktisk["html"]
        self.assertIn("Brew day checklist", resultater["en"])
        self.assertIn("Bryggedags-sjekkliste", resultater["no"])
        self.assertFalse(_norske_treff([_tekst_av_html(resultater["en"])]))
        self.assertEqual(
            re.findall(r"\d+(?:\.\d+)?", _tekst_av_html(resultater["no"])),
            re.findall(r"\d+(?:\.\d+)?", _tekst_av_html(resultater["en"])),
        )


# ── Bryggemåte-panelet (AppTest) ─────────────────────────────────────────────
class TestBryggemaatePanelAppTest(unittest.TestCase):
    def test_en_for_alle_standardprofiler_uten_norsk_systemtekst(self):
        for pid in ("enkel_infusjon", "hochkurz", "enkel_dekoksjon", "reiterated_mash", "egendefinert"):
            at = _kjor(_PROSESS_APP, "en", aktiv_prosessprofil=hent_standardprofil(pid))
            treff = _norske_treff(_alle_tekster(at))
            self.assertFalse(treff, (pid, treff))
            # Lagret profil er uendret (norsk datakontrakt) selv i EN.
            self.assertEqual(at.session_state["aktiv_prosessprofil"]["navn"], STANDARDPROFILER[pid]["navn"])
            self.assertEqual(at.session_state["aktiv_prosessprofil"]["process_id"], pid)

    def test_en_innhold_og_no_uendret(self):
        en = "\n".join(_alle_tekster(_kjor(_PROSESS_APP, "en", aktiv_prosessprofil=hent_standardprofil("hochkurz"))))
        for forventet in (
            "Hochkurz (step mash)", "Classic German two-step mash", "⚙️ **Equipment:**",
            "Expected effect on body/attenuation", "Difficulty = Medium", "Extra time = +20 min",
            "Sparge method = Batch sparge", "Prefer historical authenticity", "Add mash step",
            "Choose brewing method", "⭐ recommended", "Total boil time (min)", "Decoction pull-off",
            "Your own notes on this brewing method", "Mash steps (editable)",
            "No special requirements found for the selected/closest style",
        ):
            self.assertIn(forventet, en, forventet)
        no = "\n".join(_alle_tekster(_kjor(_PROSESS_APP, "no", aktiv_prosessprofil=hent_standardprofil("hochkurz"))))
        for forventet in (
            "Hochkurz (stegmesk)", "Klassisk tysk to-trinns stegmesk", "⚙️ **Utstyr:**",
            "Forventet påvirkning på kropp/utgjæring", "Vanskelighetsgrad = Middels", "Ekstra tidsbruk = +20 min",
            "Skyllemetode = Batch sparge (skyller i én/to porsjoner)", "Ønsker historisk autentisitet",
            "Legg til meskesteg", "⭐ anbefalt", "Total koketid (min)", "Dekoksjon-uttak",
        ):
            self.assertIn(forventet, no, forventet)
        self.assertNotIn("Prefer historical", no)

    def test_dynamiske_varsler_i_en_og_no(self):
        malt = [{"id": "vienna", "mengde": 25.0}]
        humle = [{"id": "magnum", "gram": 20, "tid": 90}]
        at = _kjor(_PROSESS_APP, "en", aktiv_prosessprofil=hent_standardprofil("enkel_infusjon"),
                   valgt_malt=malt, valgt_humle=humle)
        en = "\n".join(_alle_tekster(at))
        self.assertIn("exceeds the kettle capacity", en)
        self.assertIn("hop addition(s) have a longer own boil time than the total boil time", en)
        self.assertIn("Total grain bill", en)  # anbefalingsmotoren: kapasitet -> reiterated mash
        self.assertFalse(_norske_treff(_alle_tekster(at)), _norske_treff(_alle_tekster(at)))
        _bytt(at, "no")
        no = "\n".join(_alle_tekster(at))
        self.assertIn("overskrider kjelekapasitet", no)
        self.assertIn("humletilsetning(er) har lengre egen koketid", no)
        self.assertIn("Total maltmengde", no)

    def test_sprakbytte_no_en_no_endrer_ikke_profil_eller_tall(self):
        at = _kjor(_PROSESS_APP, "no", aktiv_prosessprofil=hent_standardprofil("hochkurz"))
        for_profil = copy.deepcopy(at.session_state["aktiv_prosessprofil"])
        no1 = _alle_tekster(at)
        _bytt(at, "en")
        self.assertNotEqual(no1, _alle_tekster(at))
        self.assertEqual(at.session_state["aktiv_prosessprofil"], for_profil)
        self.assertEqual(at.session_state["valgt_prosess_id"], "hochkurz")
        _bytt(at, "no")
        self.assertEqual(_alle_tekster(at), no1)
        self.assertEqual(at.session_state["aktiv_prosessprofil"], for_profil)

    def test_profilbytte_i_en_lagrer_norsk_navn_og_oversatt_visning(self):
        at = _kjor(_PROSESS_APP, "en")
        at.selectbox(key="valgt_prosess_id").set_value("enkel_dekoksjon").run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        profil = at.session_state["aktiv_prosessprofil"]
        self.assertEqual(profil["navn"], "Enkel dekoksjon")
        self.assertEqual(profil["process_id"], "enkel_dekoksjon")
        self.assertEqual(profil["mash_steps"][0]["kommentar"], "Startmesk — før uttak")
        tekst = "\n".join(_alle_tekster(at))
        self.assertIn("Decoction details", tekst)
        self.assertIn("Single decoction", tekst)
        self.assertFalse(_norske_treff(_alle_tekster(at)), _norske_treff(_alle_tekster(at)))
        # Kommentarfeltet viser oversatt standardtekst i EN, men lagrer den ikke.
        kommentarer = [w.value for w in at.text_input if str(w.label) == "Comment"]
        self.assertIn("Start mash — before pull-off", kommentarer)
        _bytt(at, "no")
        self.assertEqual(at.session_state["aktiv_prosessprofil"]["mash_steps"][0]["kommentar"], "Startmesk — før uttak")
        self.assertIn("Startmesk — før uttak", [w.value for w in at.text_input if str(w.label) == "Kommentar"])

    def test_brukerens_endrede_kommentar_overlever_sprakbytte(self):
        # (En redigert kommentar i en STANDARDprofil repareres bevisst tilbake til
        # standardmalen av normaliser_prosessprofil -- uendret oppførsel -- så
        # brukerens egen tekst testes på «egendefinert».)
        at = _kjor(_PROSESS_APP, "en", aktiv_prosessprofil=hent_standardprofil("egendefinert"))
        felt = next(w for w in at.text_input if str(w.label) == "Comment")
        felt.set_value("Min egen hvile").run()
        self.assertEqual(at.session_state["aktiv_prosessprofil"]["mash_steps"][0]["kommentar"], "Min egen hvile")
        _bytt(at, "no")
        self.assertEqual(at.session_state["aktiv_prosessprofil"]["mash_steps"][0]["kommentar"], "Min egen hvile")
        self.assertIn("Min egen hvile", [w.value for w in at.text_input if str(w.label) == "Kommentar"])


# ── Vannkjemi-panelet (AppTest) ──────────────────────────────────────────────
class TestVannkjemiPanelAppTest(unittest.TestCase):
    def test_en_panel_har_ingen_norsk_systemtekst(self):
        at = _kjor(_VANN_APP, "en")
        treff = _norske_treff(_alle_tekster(at))
        self.assertFalse(treff, treff)

    def test_en_representativt_innhold_og_no_uendret(self):
        en = "\n".join(_alle_tekster(_kjor(_VANN_APP, "en")))
        for forventet in (
            "Water treatment (preparation)", "Source water", "Unknown source water", "Choose target profile",
            "Balanced ale  ⭐ recommended", "Malt-forward German lager", "Suggested salts",
            "Calculate salt suggestion", "Split between mash and sparge water",
            "| Salt | Total | Mash water | Sparge water |", "Calcium chloride (anhydrous)",
            "Anhydrous CaCl2 is strongly hygroscopic", "Very low solubility in water without CO2",
            "Expected final profile", "| Ion | Start | Added | Final | Target | Status |", "unknown",
            "Warnings", "Source water is unknown", "below the scale's practical resolution",
            "Lactic acid: concentration (%) is not specified", "Acids", "Add acid", "Remove acid",
            "Mash pH", "Desired mash pH", "Actual measured mash pH", "Time of measurement",
            "Sample cooled to room temperature before measuring",
            "pH meter calibrated with pH 4.01 and 7.00 buffer solutions",
            "Informational text, not a product recommendation.", "Edit target profile",
            "Kvernhaug house profile made for malt-forward German lagers.",
        ):
            self.assertIn(forventet, en, forventet)
        no = "\n".join(_alle_tekster(_kjor(_VANN_APP, "no")))
        for forventet in (
            "Vannbehandling (forberedelse)", "Kildevann", "Ukjent kildevann", "Velg målprofil",
            "Balansert ale  ⭐ anbefalt", "Maltpreget tysk lager", "Foreslåtte salter", "Beregn saltforslag",
            "Fordeling mellom meske- og skyllevann", "| Salt | Totalt | Meskevann | Skyllevann |",
            "Kalsiumklorid (vannfri)", "Forventet sluttprofil", "Varsler", "Syrer", "Legg til syre",
            "Ønsket meske-pH", "Faktisk målt meske-pH", "Kvernhaug-husprofil laget for maltpregede tyske lagerøl.",
        ):
            self.assertIn(forventet, no, forventet)

    def test_sprakbytte_no_en_no_og_urort_vanntilstand(self):
        at = _kjor(_VANN_APP, "no")
        no1 = _alle_tekster(at)
        tilstand = {k: copy.deepcopy(at.session_state[k]) for k in
                    ("vann_salter", "vann_syrer", "vann_kilde_valgt_id", "vann_maal_valgt_id",
                     "vann_fordelingsmetode", "aktiv_vannbehandling", "aktiv_vannmaalinger")}
        _bytt(at, "en")
        self.assertNotEqual(no1, _alle_tekster(at))
        for k, v in tilstand.items():
            self.assertEqual(at.session_state[k], v, f"{k} endret av språkbytte")
        self.assertEqual(at.session_state["aktiv_vannmaal_snapshot"]["name"], "Maltpreget tysk lager")
        _bytt(at, "no")
        self.assertEqual(_alle_tekster(at), no1)

    def test_beregn_saltforslag_forklaring_i_en(self):
        at = _kjor(_VANN_APP, "en")
        at.button(key="vann_beregn_forslag_btn").click().run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        info = "\n".join(str(i.value) for i in at.info)
        self.assertTrue("Calcium chloride raises Ca and Cl" in info or "gypsum raises Ca and SO4" in info
                        or "already close to the target range" in info, info)
        self.assertFalse(_norske_treff([info]), info)
        _bytt(at, "no")
        no_tekst = "\n".join(_alle_tekster(at))
        self.assertNotIn("Calcium chloride raises", no_tekst)


# ── Kontekst: egne profilnavn/kommentarer, Mashing-etikett, profiltype ───────
def _egen_profil(navn="Lett"):
    from modules.process_profiles import bygg_egendefinert_profil
    steg = [
        {"temperatur": 66.0, "varighet": 60, "stegtype": "infusjon", "kommentar": "Infusjon"},
        {"temperatur": 72.0, "varighet": 15, "stegtype": "infusjon", "kommentar": ""},
        {"temperatur": 78.0, "varighet": 5, "stegtype": "mashout", "kommentar": "Lavere temperaturhvile"},
    ]
    return bygg_egendefinert_profil(navn, steg)


class TestKontekstOgEtiketter(unittest.TestCase):
    def test_plan_merker_bare_appens_egne_labeler(self):
        plan = _plan("en", None)
        self.assertEqual([s["label"] for s in plan["maskeplan"]], ["Mashing", "Mashout"])  # lagret label uendret
        egen = lag_brewday_plan(
            malt_valg=[{"id": "vienna", "mengde": 5.0}], humle_valg=[], gjaer_id="g",
            gjaer_info={"display_name": "G", "gjaertype": "Ale"}, og=1.050, batch_volum_l=20.0,
            humle_database=_HUMLE_DB, malt_database=_MALT_DB, process_profile=_egen_profil(),
        )
        self.assertEqual([s.get("label_nokkel") for s in egen["maskeplan"]],
                         [None, "pp.stegtype.infusjon", None])
        self.assertEqual([s["label"] for s in egen["maskeplan"]],
                         ["Infusjon", "Infusjon", "Lavere temperaturhvile"])

    def test_standard_mashing_etikett_no_og_en_i_visning_og_ark(self):
        plan = _plan("no", None)
        no_steg, en_steg = plan["maskeplan"][0], plan["maskeplan"][0]
        self.assertEqual(maskeplan_steg_visning(no_steg, None, "no"), "Mesking")
        self.assertEqual(maskeplan_steg_visning(en_steg, None, "en"), "Mashing")
        self.assertEqual(maskeplan_steg_visning(plan["maskeplan"][1], None, "no"), "Mashout")
        self.assertIn("(Mesking)", render_brewday_html(_ctx(), plan, {}, sprak="no"))
        self.assertIn("(Mashing)", render_brewday_html(_ctx(), _plan("en", None), {}, sprak="en"))
        self.assertEqual(plan["maskeplan"][0]["label"], "Mashing")  # plandata uendret

    def test_egen_profil_i_eksport_bevarer_navn_og_kommentarer(self):
        plan = lag_brewday_plan(
            malt_valg=[{"id": "vienna", "mengde": 5.0}], humle_valg=[], gjaer_id="g",
            gjaer_info={"display_name": "G", "gjaertype": "Ale"}, og=1.050, batch_volum_l=20.0,
            humle_database=_HUMLE_DB, malt_database=_MALT_DB, process_profile=_egen_profil(), sprak="en",
        )
        en = render_brewday_html(_ctx(), plan, {}, sprak="en")
        no = render_brewday_html(_ctx(), plan, {}, sprak="no")
        for html in (en, no):
            self.assertIn("Lett", html)
            self.assertIn("<em>(Infusjon)</em>", html)           # egen kommentar
            self.assertIn("<em>(Lavere temperaturhvile)</em>", html)  # egen kommentar = standardtekst
        self.assertIn("Brewing method: Lett", en)
        self.assertIn("Bryggemåte: Lett", no)
        self.assertIn("<em>(Infusion)</em>", en)   # tom kommentar -> appens stegtype-fallback
        self.assertEqual(no.count("<em>(Infusjon)</em>"), 2)

    def test_standardprofil_i_eksport_oversettes_fortsatt(self):
        html = render_brewday_html(_ctx(), _plan("en", "hochkurz"), {}, sprak="en")
        self.assertIn("Brewing method: Hochkurz (step mash)", html)
        self.assertIn("<em>(Lower temperature rest)</em>", html)
        self.assertIn("<em>(Mashout — stops enzyme activity)</em>", html)

    def test_panel_med_egen_profil_no_en_no(self):
        from tests.test_brewday_flow_i18n import _kjor  # noqa: F401 (samme modul)
        at = _kjor(_BREWDAY_APP, "no", aktiv_prosessprofil=_egen_profil())
        no1 = _alle_tekster(at)
        self.assertIn("🧭 Bryggemåte: **Lett**", "\n".join(no1))
        self.assertIn("*Infusjon*", "\n".join(no1))
        _bytt(at, "en")
        en = "\n".join(_alle_tekster(at))
        self.assertIn("🧭 Brewing method: **Lett**", en)
        self.assertIn("*Infusjon*", en)              # egen kommentar beholdt (steg 1)
        self.assertIn("*Infusion*", en)              # appens fallback oversatt (steg 2)
        self.assertIn("*Lavere temperaturhvile*", en)  # egen kommentar beholdt (steg 3)
        self.assertEqual(at.session_state["aktiv_prosessprofil"]["navn"], "Lett")
        _bytt(at, "no")
        self.assertEqual(_alle_tekster(at), no1)

    def test_panel_uten_profil_viser_mesking_og_mashing(self):
        at = _kjor(_BREWDAY_APP, "no")
        self.assertIn("*Mesking*", "\n".join(_alle_tekster(at)))
        _bytt(at, "en")
        en = "\n".join(_alle_tekster(at))
        self.assertIn("*Mashing*", en)
        self.assertNotIn("Mesking*", en)
        _bytt(at, "no")
        self.assertIn("*Mesking*", "\n".join(_alle_tekster(at)))

    def test_prosesspanel_egen_profil_beholder_kommentarer_og_standard_oversettes(self):
        at = _kjor(_PROSESS_APP, "en", aktiv_prosessprofil=_egen_profil())
        kommentarer = [w.value for w in at.text_input if str(w.label) == "Comment"]
        self.assertEqual(kommentarer, ["Infusjon", "", "Lavere temperaturhvile"])
        std = _kjor(_PROSESS_APP, "en", aktiv_prosessprofil=hent_standardprofil("hochkurz"))
        self.assertEqual([w.value for w in std.text_input if str(w.label) == "Comment"][0], "Lower temperature rest")
        _bytt(std, "no")
        self.assertEqual([w.value for w in std.text_input if str(w.label) == "Kommentar"][0], "Lavere temperaturhvile")
        self.assertEqual(std.session_state["aktiv_prosessprofil"]["mash_steps"][0]["kommentar"], "Lavere temperaturhvile")

    def test_profiltype_koder_vises_forstaelig_men_lagres_uendret(self):
        from modules.water_chemistry import profiltype_tekst
        self.assertEqual(profiltype_tekst("house_profile", "en"), "House profile")
        self.assertEqual(profiltype_tekst("house_profile", "no"), "Husprofil")
        self.assertEqual(profiltype_tekst("custom_profile", "en"), "Custom profile")
        self.assertEqual(profiltype_tekst("custom_profile", "no"), "Egendefinert profil")
        self.assertEqual(profiltype_tekst("min_spesialtype", "en"), "min_spesialtype")
        at = _kjor(_VANN_APP, "en")
        self.assertIn("Origin: Kvernhaug Brygghus · Type: House profile", "\n".join(_alle_tekster(at)))
        self.assertEqual(at.session_state["aktiv_vannmaal_snapshot"]["profile_type"], "house_profile")
        _bytt(at, "no")
        self.assertIn("Opprinnelse: Kvernhaug Brygghus · Type: Husprofil", "\n".join(_alle_tekster(at)))
        self.assertEqual(at.session_state["aktiv_vannmaal_snapshot"]["profile_type"], "house_profile")


if __name__ == "__main__":
    unittest.main()
