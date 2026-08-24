# -*- coding: utf-8 -*-
"""
Tester for Steg F11: matching precision guard i modules/store_matcher.py.

Bakgrunn: fuzzy matching (SequenceMatcher, terskel 0,7) skrev tidligere et
hvilket som helst treff over terskelen DIREKTE inn i master["butikk_match"].
En live validering av 84 Ølbrygging-malter viste at 14+ av 63 treff pekte på
et helt annet produkt -- "Carafa 1 Malt" (900 EBC) mot aliaset "Cara Malt" på
caramalt_30 (30 EBC) med likhet 0,818, "Flaket ris" mot flaked_corn, "Rye
Malt" fra Viking mot bonsak_rugmalt, og så videre.

Guarden fjerner IKKE fuzzy matching. Den nedgraderer et treff fra AUTO_MATCH
til REVIEW_REQUIRED når navnelikheten motsies av produktdataene (EBC,
produsent, korntype). Ingenting forkastes -- review-elementene går inn i den
EKSISTERENDE review-flyten (raw_data/unmatched_*.json -> ui/review_panel.py).

Testene bruker utelukkende syntetiske fixture-verdier og temp-filer. Ingen
ekte data/master_*.json eller raw_data/*.json røres. Verdiene i fixturene
(navn, EBC, produsent, URL-form) er hentet fra de faktisk observerte
butikkdataene, slik at regresjonstestene beskytter mot de reelle feilene.
"""
import json
import os
import shutil
import tempfile
import unittest

from modules.store_matcher import (
    MATCH_REVIEW,
    _ebc_konflikt,
    _kornkonflikt,
    _normaliser_produsentnavn,
    _produsentkonflikt,
    _produsentvokabular,
    match_store_data_to_master_malt,
    vurder_maltmatch,
)


# ── Fixture: et lite utsnitt av master_malt med de EKTE feltverdiene ──
def _master():
    def e(navn, ebc, produsent, aliases):
        return {"display_name": navn, "ebc": ebc, "produsent": produsent,
                "aliases": aliases, "butikk_match": {}, "verified": True}
    return {
        "caramalt_30": e("CaraMalt 30", 30.0, "Thomas Fawcett",
                         ["CaraMalt", "Cara Malt", "Caramalt 30", "Caramel Malt 30"]),
        "oat_malt": e("Oat Malt", 3.0, "Simpson's",
                      ["Oat Malt", "Simpsons Oat Malt", "Havremalt"]),
        "special_b": e("Special B", 350.0, "Castle Malting",
                       ["Special B", "Château Special B", "Special B Malt"]),
        "crystal": e("Crystal Malt", 150.0, "Thomas Fawcett",
                     ["Crystal Malt", "Crystal 150", "Caramel Malt"]),
        "chateau_cara_crystal": e("Château Cara Crystal", 120.0, "Castle Malting",
                                  ["Château Cara Crystal", "Cara Crystal", "Cara Gold"]),
        "caramunich_1": e("CaraMunich I", 90.0, "Weyermann",
                          ["CaraMunich I", "Caramunich 1", "CaraMunich 1 Malt"]),
        "rauchmalz": e("Rauchmalz", 5.0, "Weyermann",
                       ["Rauchmalz", "Smoked Malt", "Røykmalt"]),
        "melanoidin": e("Melanoidin", 70.0, "Weyermann",
                        ["Melanoidin Malt", "Melanoidin"]),
        "flaked_corn": e("Flaked Corn", 1.0, "Diverse",
                         ["Flaked Corn", "Flaket Mais", "Maize"]),
        "acidulated": e("Acidulated Malt", 4.0, "Ireks",
                        ["Acidulated Malt", "Sour Malt", "Château Acid",
                         "Château Acid Malt", "Chateau Acid Malt"]),
        # Master lagrer noen entries med FLERE produsenter. Denne er også
        # grunnen til at "viking" i det hele tatt finnes i vokabularet --
        # produsentsignalet er datadrevet fra master, så et merke master
        # aldri har sett gir ingen signal (se test_ukjent_url_segment...).
        "crystal_maple_carapils": e("Carapils / Dextrin", 8.0, "Viking / Weyermann",
                                    ["Carapils", "Dextrin Malt", "Carapils Malt"]),
        "jaermalt_pilsner": e("Jærmalt Pilsner", 3.0, "Jærmalt",
                              ["Jærmalt Pilsner", "Jærmalt Pilsner Malt"]),
        "bonsak_rugmalt": e("Bonsak Rugmalt", 4.0, "Bonsak",
                            ["Rugmalt", "Bonsak Rugmalt", "Rye Malt"]),
        "carared": e("CaraRed", 50.0, "Weyermann", ["CaraRed", "Carared Malt"]),
        "chocolate": e("Chocolate Malt", 1175.0, "Thomas Fawcett",
                       ["Chocolate Malt", "Chokolademalt"]),
        "golden_promise": e("Golden Promise", 6.0, "Simpsons",
                            ["Golden Promise"]),
        "biscuit": e("Château Biscuit", 50.0, "Brewferm / Castle Malting",
                     ["Château Biscuit", "Biscuit Malt"]),
        "roasted_barley": e("Roasted Barley", 1200.0, "Diverse",
                            ["Roasted Barley", "Ristet Bygg"]),
        "spray_light_68_ebc": e("Spraymalt Light", 7.0, "Muntons",
                                ["Spraymalt Light"]),
        "spray_extra_light": e("Spraymalt Extra Light", 5.0, "Muntons",
                               ["Spraymalt Extra Light"]),
    }


def _raw(navn, url, ebc=None, produsent="Ukjent", pris=49.0, pakke_gram=1000.0,
         butikk="olbrygging", er_knust=False):
    return {"navn": navn, "url": url, "ebc": ebc, "produsent": produsent,
            "pris": pris, "pakke_gram": pakke_gram, "butikk": butikk,
            "er_knust": er_knust, "kategori": "malt"}


def _ol(merke, varenr, slug):
    return "https://www.olbrygging.no/{}/{}/{}".format(merke, varenr, slug)


def _kjor(testcase, raw_liste, master=None):
    """Kjører en ekte dry-run gjennom det offisielle entrypointet -- samme
    kodebane som en skrivende kjøring (se _bygg_malt_matchresultat), bare
    uten filskriving."""
    master = master if master is not None else _master()
    tmp = tempfile.mkdtemp()
    testcase.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
    raw_path = os.path.join(tmp, "malt_raw.json")
    master_path = os.path.join(tmp, "master_malt.json")
    unmatched_path = os.path.join(tmp, "unmatched_malt.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_liste, f, ensure_ascii=False)
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False)
    return match_store_data_to_master_malt(raw_path, master_path, unmatched_path,
                                           dry_run=True)


def _utfall(resultat, navn):
    """(status, foreslatt_master_id) for ett produktnavn. status er
    MATCH_REVIEW, "pending_review", eller "auto_match" når raden ikke
    ligger i unmatched i det hele tatt -- da ER den skrevet."""
    for u in resultat["unmatched"]:
        if u["navn"] == navn:
            return u["status"], u.get("foreslatt_master_id")
    return "auto_match", None


def _auto_matchet_id(resultat, opprinnelig_master):
    """Master-IDene som FAKTISK fikk et nytt butikk_match-forslag."""
    return {
        m_id for m_id, entry in resultat["master_forslag"].items()
        if entry.get("butikk_match") != opprinnelig_master[m_id].get("butikk_match")
    }


# ══════════════════════════════════════════════════════════════════════
#  1. NEGATIV REGRESJON -- de dokumenterte feilmatchene
# ══════════════════════════════════════════════════════════════════════
class TestDokumenterteFeilmatcherBlokkeres(unittest.TestCase):
    """Hver av disse ble faktisk skrevet til butikk_match før Steg F11.
    De skal nå ende som REVIEW_REQUIRED -- aldri som AUTO_MATCH."""

    # (produktnavn, url, ebc, feil master-ID den fuzzy-matchet til)
    FEILMATCHER = [
        ("Carafa 1 Malt 250 g Knust",
         _ol("weyermann", "104512", "carafa-1-malt-900-ebc"), 900.0, "caramalt_30"),
        ("Simpsons DRC® Malt 250 g Knust",
         _ol("simpsons-malt", "105811", "drc-malt-320-ebc"), 320.0, "oat_malt"),
        ("Château Spelt 1 kg Knust",
         _ol("castle-malting", "101233", "chateau-spelt-7-ebc"), 7.0, "special_b"),
        ("Caramel Pale Malt 250 g Knust",
         _ol("viking-malt", "106401", "caramel-pale-malt-10-ebc"), 10.0, "crystal"),
        ("CaraBody 250 g Hel",
         _ol("viking-malt", "106233", "carabody-8-ebc"), 8.0, "chateau_cara_crystal"),
        ("Munich Light Malt 1 kg Hel",
         _ol("j%c3%a6rmalt", "106902", "munich-light-malt-15-ebc"), 15.0, "caramunich_1"),
        ("Cookie Malt 250 g Knust",
         _ol("viking-malt", "106510", "cookie-malt-60-ebc"), 60.0, "rauchmalz"),
        ("Special N Malt 1 kg Hel",
         _ol("bonsak-g%c3%a5rdsmalteri", "106760", "special-n-malt-80-ebc"), 80.0, "special_b"),
        ("Triple Melanoidin Malt 1 kg Hel",
         _ol("bonsak-g%c3%a5rdsmalteri", "106761", "triple-melanoidin-200-ebc"), 200.0, "melanoidin"),
        ("Flaket ris 1 kg",
         _ol("viking-malt", "106120", "flaket-ris"), 3.0, "flaked_corn"),
        ("Château Oat Malt 250 g Hel",
         _ol("castle-malting", "100912", "chateau-oat-malt-2-ebc"), 2.0, "acidulated"),
        ("Eraclea Pilsner Malt 1 kg Hel",
         _ol("weyermann", "104120", "eraclea-pilsner-malt-4-ebc"), 4.0, "jaermalt_pilsner"),
        ("Fairytale Pilsner Malt 1 kg Hel",
         _ol("bonsak-g%c3%a5rdsmalteri", "106758", "fairytale-pilsner-malt-4-ebc"), 4.0, "jaermalt_pilsner"),
        ("Rye Malt 1 kg knust",
         _ol("viking-malt", "106330", "rye-malt-10-ebc"), 10.0, "bonsak_rugmalt"),
        ("Château Cara Clair 1 kg knust",
         _ol("castle-malting", "101120", "chateau-cara-clair-5-ebc"), 5.0, "chateau_cara_crystal"),
    ]

    def test_ingen_dokumentert_feilmatch_auto_matcher(self):
        master = _master()
        raw = [_raw(n, u, ebc=e) for n, u, e, _ in self.FEILMATCHER]
        res = _kjor(self, raw, master)

        self.assertEqual(res["statistikk"]["auto_match_totalt"], 0,
                         "Ingen av de dokumenterte feilmatchene skal auto-matche.")
        self.assertEqual(_auto_matchet_id(res, master), set(),
                         "Ingen master-entry skal ha fått et nytt butikk_match-forslag.")

    def test_hver_feilmatch_havner_i_review_med_forklaring(self):
        master = _master()
        for navn, url, ebc, feil_id in self.FEILMATCHER:
            with self.subTest(navn=navn):
                res = _kjor(self, [_raw(navn, url, ebc=ebc)], master)
                status, foreslatt = _utfall(res, navn)
                self.assertEqual(status, MATCH_REVIEW,
                                 f"«{navn}» skal til review, ikke skrives.")
                self.assertEqual(foreslatt, feil_id,
                                 "Kandidaten skal følge med som forslag, ikke kastes.")
                post = res["unmatched"][0]
                self.assertTrue(post["konflikter"],
                                "Review-elementet må si HVORFOR det ble holdt tilbake.")
                for k in post["konflikter"]:
                    self.assertIn(k["signal"], {"ebc", "produsent", "korn"})
                    self.assertTrue(k["forklaring"].strip())

    def test_review_skriver_aldri_butikk_match(self):
        master = _master()
        raw = [_raw(n, u, ebc=e) for n, u, e, _ in self.FEILMATCHER]
        res = _kjor(self, raw, master)
        for m_id, entry in res["master_forslag"].items():
            self.assertEqual(entry.get("butikk_match"), {},
                             f"{m_id} fikk butikk_match fra et review-element.")


# ══════════════════════════════════════════════════════════════════════
#  2. POSITIV REGRESJON -- gode matcher skal fortsatt gå gjennom
# ══════════════════════════════════════════════════════════════════════
class TestGodeMatcherOverlever(unittest.TestCase):
    """Guarden skal koste så få ekte treff som mulig. Alle disse er
    bekreftet riktige matcher fra det samme live-datasettet."""

    GODE = [
        # eksakt alias, produsent og EBC stemmer
        ("Carared 1 kg hel", _ol("weyermann", "104201", "carared-50-ebc"), 50.0, "carared"),
        # variant/pakningsstørrelse av samme malt -- samme master-ID
        ("Carared 25 kg knust", _ol("weyermann", "104204", "carared-25kg-knust-50-ebc"),
         50.0, "carared"),
        # ekte lys basemalt, 4 EBC (verdien som FØR var en silent default)
        ("Golden Promise 1 kg hel", _ol("simpsons-malt", "105801", "golden-promise-6-ebc"),
         6.0, "golden_promise"),
        # generisk master med produsent "Diverse" -- aldri produsentkonflikt
        ("Flaket mais 1 Kg", _ol("viking-malt", "106121", "flaket-mais"), 4.0, "flaked_corn"),
        ("Roasted Barley 250 g Hel", _ol("viking-malt", "106610", "roasted-barley-1200-ebc"),
         1200.0, "roasted_barley"),
        # master med FLERE produsenter ("Brewferm / Castle Malting")
        ("Château Biscuit® 1 kg hel", _ol("castle-malting", "101301", "chateau-biscuit-50-ebc"),
         50.0, "biscuit"),
        # produsent + navn stemmer, EBC innenfor normal variasjon
        ("Chocolate Malt 1 kg hel", _ol("thomas-fawcetts", "20401", "chocolate-malt-1000-ebc"),
         1000.0, "chocolate"),
        # butikken oppga ingen EBC -- ukjent er aldri et negativt bevis
        ("Carared 1 kg knust", _ol("weyermann", "104202", "carared-knust"), None, "carared"),
    ]

    def test_gode_matcher_auto_matcher_fortsatt(self):
        master = _master()
        for navn, url, ebc, forventet_id in self.GODE:
            with self.subTest(navn=navn):
                res = _kjor(self, [_raw(navn, url, ebc=ebc)], master)
                self.assertEqual(
                    res["unmatched"], [],
                    f"«{navn}» skulle auto-matchet, men havnet i review/unmatched: "
                    f"{res['unmatched']}")
                self.assertEqual(_auto_matchet_id(res, master), {forventet_id})

    def test_ukjent_produsent_paa_butikksiden_blokkerer_ikke(self):
        """URL-segmentet er en KATEGORI, ikke et merke -- da finnes det
        ingen produsentsignal, og fravær av signal er ikke en konflikt."""
        master = _master()
        raw = _raw("Chocolate Malt 1 kg hel",
                   "https://vestbrygg.no/ekstrakt-spraymalt/20401/chocolate-malt",
                   ebc=1000.0, butikk="vestbrygg")
        res = _kjor(self, [raw], master)
        self.assertEqual(res["unmatched"], [])

    def test_eksisterende_extra_light_vern_er_uendret(self):
        """Steg F8F sitt kvalifikatorvern (Light vs. Extra Light) ligger
        FØR guarden i kjeden og skal virke nøyaktig som før -- treffet
        oppstår aldri, så elementet er unmatched, ikke review."""
        master = _master()
        raw = _raw("1 Kg Spraymalt EXTRA Light",
                   "https://vestbrygg.no/ekstrakt-spraymalt/104598/spraymalt-extra-light",
                   ebc=5.0, butikk="vestbrygg")
        res = _kjor(self, [raw], master)
        self.assertEqual(_auto_matchet_id(res, master), {"spray_extra_light"})


# ══════════════════════════════════════════════════════════════════════
#  3. ENHETSTESTER AV DE TRE SIGNALENE
# ══════════════════════════════════════════════════════════════════════
class TestEbcSanity(unittest.TestCase):
    def test_ukjent_ebc_gir_aldri_konflikt(self):
        for a, b in [(None, 30.0), (900.0, None), (None, None)]:
            self.assertFalse(_ebc_konflikt(a, b))

    def test_ikke_maalt_ebc_gir_aldri_konflikt(self):
        """0 og negative verdier er ingen reell måling -- bl.a. den kjente
        URL-intervall-parsefeilen ("2.5-5.0 EBC" -> 0). Ukjent skal ikke
        kunne bli til et negativt bevis."""
        self.assertFalse(_ebc_konflikt(0.0, 1500.0))
        self.assertFalse(_ebc_konflikt(-1.0, 1500.0))

    def test_smaa_absolutte_avvik_er_aldri_konflikt(self):
        """Under 8 EBC differanse -- normal variasjon mellom produsenter
        og partier, og hele basismaltområdet der ratio er upålitelig."""
        self.assertFalse(_ebc_konflikt(4.0, 1.0))    # ratio 4, men bare 3 EBC
        self.assertFalse(_ebc_konflikt(12.0, 4.0))   # ratio 3, men bare 8 EBC
        self.assertFalse(_ebc_konflikt(3.0, 5.0))

    def test_store_avvik_uten_dobling_er_ikke_konflikt(self):
        self.assertFalse(_ebc_konflikt(1000.0, 1175.0))
        self.assertFalse(_ebc_konflikt(300.0, 350.0))
        self.assertFalse(_ebc_konflikt(80.0, 70.0))

    def test_uforenlige_farger_er_konflikt(self):
        for a, b in [(900.0, 30.0), (320.0, 3.0), (350.0, 7.0), (150.0, 10.0),
                     (120.0, 5.0), (90.0, 15.0), (60.0, 5.0), (200.0, 70.0)]:
            with self.subTest(par=(a, b)):
                self.assertTrue(_ebc_konflikt(a, b))
                self.assertTrue(_ebc_konflikt(b, a), "Regelen må være symmetrisk.")

    def test_ugyldig_type_gir_ikke_konflikt(self):
        self.assertFalse(_ebc_konflikt("ukjent", 30.0))


class TestProdusentsignal(unittest.TestCase):
    def test_normalisering_er_lik_paa_begge_sider(self):
        par = [
            ("simpsons-malt", "Simpson's"), ("simpsons-malt", "Simpsons"),
            ("castle-malting", "Castle Malting"), ("viking-malt", "Viking Malt"),
            ("bonsak-gårdsmalteri", "Bonsak"), ("jærmalt", "Jærmalt"),
            ("thomas-fawcetts", "Thomas Fawcett"), ("weyermann", "Weyermann"),
        ]
        for url_segment, master_verdi in par:
            with self.subTest(par=(url_segment, master_verdi)):
                self.assertEqual(_normaliser_produsentnavn(url_segment),
                                 _normaliser_produsentnavn(master_verdi))

    def test_ulike_produsenter_normaliseres_ikke_sammen(self):
        navn = ["Weyermann", "Viking Malt", "Castle Malting", "Thomas Fawcett",
                "Bonsak", "Jærmalt", "Simpson's", "Ireks"]
        nokler = [_normaliser_produsentnavn(n) for n in navn]
        self.assertEqual(len(set(nokler)), len(navn))

    def test_generisk_master_gir_aldri_konflikt(self):
        master = _master()
        vok = _produsentvokabular(master)
        raw = _raw("Flaket mais 1 Kg", _ol("viking-malt", "106121", "flaket-mais"))
        self.assertFalse(_produsentkonflikt(raw, master["flaked_corn"], vok))

    def test_ukjent_url_segment_gir_aldri_konflikt(self):
        """Segmentet må ligge i masterdatabasens eget produsentvokabular.
        Kategorisegmenter ("tilbud", "ekstrakt-spraymalt") og ukjente
        merker gir INGEN signal -- aldri en konflikt."""
        master = _master()
        vok = _produsentvokabular(master)
        for segment in ["tilbud", "ekstrakt-spraymalt", "young-s", "ol"]:
            with self.subTest(segment=segment):
                raw = _raw("Carared 1 kg hel", _ol(segment, "104201", "carared"))
                self.assertFalse(_produsentkonflikt(raw, master["carared"], vok))

    def test_flerprodusent_master_matcher_paa_en_av_dem(self):
        master = _master()
        vok = _produsentvokabular(master)
        raw = _raw("Château Biscuit® 1 kg hel", _ol("castle-malting", "101301", "biscuit"))
        self.assertFalse(_produsentkonflikt(raw, master["biscuit"], vok))

    def test_eksplisitt_ulik_produsent_er_konflikt(self):
        master = _master()
        vok = _produsentvokabular(master)
        raw = _raw("Rye Malt 1 kg knust", _ol("viking-malt", "106330", "rye-malt"))
        self.assertTrue(_produsentkonflikt(raw, master["bonsak_rugmalt"], vok))

    def test_vokabularet_bygges_fra_master_ikke_hardkodet(self):
        vok = _produsentvokabular(_master())
        self.assertIn(_normaliser_produsentnavn("Weyermann"), vok)
        self.assertNotIn("diverse", vok)
        self.assertNotIn("ukjent", vok)
        # Et merke master ikke kjenner skal ikke finnes i vokabularet
        self.assertNotIn(_normaliser_produsentnavn("Crisp Malting"), vok)


class TestKorntype(unittest.TestCase):
    def test_ris_mot_mais_er_konflikt(self):
        master = _master()
        self.assertTrue(_kornkonflikt(_raw("Flaket ris 1 kg", ""), master["flaked_corn"]))

    def test_samme_korn_er_ikke_konflikt(self):
        master = _master()
        self.assertFalse(_kornkonflikt(_raw("Flaket mais 1 Kg", ""), master["flaked_corn"]))

    def test_korn_bare_paa_en_side_er_ikke_konflikt(self):
        master = _master()
        self.assertFalse(_kornkonflikt(_raw("Smoked Wheat Malt", ""), master["rauchmalz"]))
        self.assertFalse(_kornkonflikt(_raw("Carared 1 kg hel", ""), master["flaked_corn"]))

    def test_tokenbasert_ikke_substreng(self):
        """"Crisp" inneholder bokstavrekken "ris", men er et annet ord."""
        master = _master()
        self.assertFalse(_kornkonflikt(_raw("Crisp Maris Otter", ""), master["flaked_corn"]))

    def test_norsk_og_engelsk_korn_er_samme_raavare(self):
        master = _master()
        rugmalt = master["bonsak_rugmalt"]
        self.assertFalse(_kornkonflikt(_raw("Rye Malt 1 kg knust", ""), rugmalt))
        self.assertFalse(_kornkonflikt(_raw("Rugmalt 1 kg", ""), rugmalt))


# ══════════════════════════════════════════════════════════════════════
#  4. KONTRAKT: utfall, review-flyt og skrivesikkerhet
# ══════════════════════════════════════════════════════════════════════
class TestUtfallOgReviewflyt(unittest.TestCase):
    def test_tre_utfall_er_gjensidig_utelukkende(self):
        master = _master()
        raw = [
            _raw("Carared 1 kg hel", _ol("weyermann", "104201", "carared"), ebc=50.0),
            _raw("Carafa 1 Malt 250 g Knust", _ol("weyermann", "104512", "carafa-1"), ebc=900.0),
            _raw("Et Produkt Uten Master 1 kg", _ol("weyermann", "109999", "ukjent-vare")),
        ]
        res = _kjor(self, raw, master)
        s = res["statistikk"]
        self.assertEqual(s["auto_match_totalt"], 1)
        self.assertEqual(s["review_required_totalt"], 1)
        statuser = sorted(u["status"] for u in res["unmatched"])
        self.assertEqual(statuser, sorted([MATCH_REVIEW, "pending_review"]))
        self.assertEqual(s["raw_totalt"], 3)

    def test_review_bruker_eksisterende_unmatched_flyt(self):
        """Review-elementene skal ligge i den SAMME unmatched-lista som
        ui/review_panel.py allerede leser -- ingen ny fil, ingen ny UI."""
        res = _kjor(self, [_raw("Flaket ris 1 kg", _ol("viking-malt", "106120", "flaket-ris"),
                                ebc=3.0)])
        post = res["unmatched"][0]
        for felt in ("navn", "butikk", "pris", "url", "kategori", "ebc", "status"):
            self.assertIn(felt, post, f"«{felt}» kreves av den eksisterende review-flyten.")
        self.assertEqual(post["status"], MATCH_REVIEW)
        self.assertEqual(post["foreslatt_master_id"], "flaked_corn")

    def test_uten_kandidat_beholder_pending_review_uendret(self):
        res = _kjor(self, [_raw("Helt Ukjent Vare 1 kg", _ol("weyermann", "109999", "ukjent"))])
        post = res["unmatched"][0]
        self.assertEqual(post["status"], "pending_review")
        self.assertNotIn("foreslatt_master_id", post)
        self.assertNotIn("konflikter", post)

    def test_dry_run_skriver_ingenting(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        raw_path = os.path.join(tmp, "malt_raw.json")
        master_path = os.path.join(tmp, "master_malt.json")
        unmatched_path = os.path.join(tmp, "unmatched_malt.json")
        master = _master()
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump([_raw("Carafa 1 Malt 250 g Knust",
                            _ol("weyermann", "104512", "carafa-1"), ebc=900.0)], f)
        with open(master_path, "w", encoding="utf-8") as f:
            json.dump(master, f, ensure_ascii=False)
        for_hash = open(master_path, "rb").read()

        match_store_data_to_master_malt(raw_path, master_path, unmatched_path, dry_run=True)

        self.assertFalse(os.path.exists(unmatched_path))
        self.assertEqual(open(master_path, "rb").read(), for_hash)

    def test_vurder_maltmatch_muterer_ingenting(self):
        master = _master()
        entry = master["caramalt_30"]
        for_json = json.dumps(entry, sort_keys=True, ensure_ascii=False)
        raw = _raw("Carafa 1 Malt 250 g Knust", _ol("weyermann", "104512", "carafa-1"), ebc=900.0)
        for_raw = json.dumps(raw, sort_keys=True, ensure_ascii=False)

        konflikter = vurder_maltmatch(raw, entry, _produsentvokabular(master))

        self.assertTrue(konflikter)
        self.assertEqual(json.dumps(entry, sort_keys=True, ensure_ascii=False), for_json)
        self.assertEqual(json.dumps(raw, sort_keys=True, ensure_ascii=False), for_raw)

    def test_guarden_kan_aldri_lage_en_match(self):
        """Guarden er rent negativ: den nedgraderer, aldri oppgraderer.
        Et produkt uten fuzzy-treff skal aldri få en master-ID av den."""
        master = _master()
        res = _kjor(self, [_raw("Xyzzy Plugh 1 kg", _ol("weyermann", "109998", "xyzzy"),
                                ebc=50.0)], master)
        self.assertEqual(_auto_matchet_id(res, master), set())
        self.assertIsNone(res["unmatched"][0].get("foreslatt_master_id"))


if __name__ == "__main__":
    unittest.main()
