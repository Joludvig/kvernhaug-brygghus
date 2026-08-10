"""
Tester for modules/style_engine.py — BJCP stil-matching.

Dekker inkonsistensen der UI viste 100 % match samtidig som
forklaringspanelet listet reelle avvik (OG for lav, manglende toast,
og en falsk "Mangler 0 IBU" fra flyttallsstøy).

Kjøres uten pytest (ikke installert i miljøet):
    py -3 -m unittest tests.test_style_engine
"""
import json
import os
import unittest

from modules.style_engine import (
    analyser_stil_og_balanse,
    _avvik_numerisk,
    _avvik_sensorisk,
    _kombiner_styrkeklynge,
    _EPS_IBU,
    _EPS_OG,
    _EPS_FG,
    _EPS_ABV,
    _TAK_AVVIK,
    _TAK_FLERE_AVVIK,
    _TAK_KRITISK,
    _MANGE_AVVIK_ANTALL_FOR_TAK,
    _STYRKEKLYNGE_NEST_VEKT,
    _STYRKEKLYNGE_TREDJE_VEKT,
)
from modules.flavor_engine import generer_smakshjul


def _lag_oppskrift(og, fg, ibu, ebc, abv, flavor_profile=None, yeast="safale_us_05",
                    malts=None, hops=None):
    return {
        "stats": {"og": og, "fg": fg, "ibu": ibu, "ebc": ebc, "abv": abv},
        "flavor_profile": flavor_profile or {},
        "malts": malts or [],
        "hops": hops or [],
        "yeast": yeast,
    }


def _finn_stil(resultat, navn):
    return next(s for s in resultat["stil_liste"] if s["stil"] == navn)


class TestAvvikNumeriskHelper(unittest.TestCase):
    """Tester selve sammenligningshjelperen som både score og mangel-tekst bygger på."""

    def _under(self, verdi, lo=1.064, hi=1.072, eps=0.0005, vekt=30):
        return _avvik_numerisk(
            verdi, lo, hi, eps, vekt, vekt,
            lambda diff: f"under (diff={diff:.4f})",
            lambda diff: f"over (diff={diff:.4f})",
        )

    def test_verdi_naar_grensen_gir_ikke_avvik(self):
        # Krav 9: verdi nøyaktig på minimumsgrensen skal ikke telle som avvik.
        d, tekst, kritisk = self._under(1.064)
        self.assertEqual(d, 0.0)
        self.assertIsNone(tekst)
        self.assertFalse(kritisk)

    def test_verdi_innenfor_epsilon_gir_ikke_avvik(self):
        # Krav 9: verdi marginalt under grensen, men innenfor epsilon.
        d, tekst, kritisk = self._under(1.064 - 0.0002)
        self.assertEqual(d, 0.0)
        self.assertIsNone(tekst)
        self.assertFalse(kritisk)

    def test_verdi_marginalt_under_grensen_gir_avvik_men_ikke_kritisk(self):
        # Krav 9: verdi marginalt under grensen (utenfor epsilon) skal fortsatt
        # flagges som et avvik, men et lite avvik er ikke "kritisk".
        d, tekst, kritisk = self._under(1.064 - 0.0008)  # ~10 % av vinduet (0.008)
        self.assertLess(d, 0.0)
        self.assertIn("under", tekst)
        self.assertFalse(kritisk)

    def test_avvik_over_halve_vinduet_er_kritisk(self):
        # Et avvik >= halve stilens eget toleransevindu er "kritisk".
        d, tekst, kritisk = self._under(1.064 - 0.004)  # halve vinduet (0.008)
        self.assertLess(d, 0.0)
        self.assertTrue(kritisk)

    def test_straff_normaliseres_mot_stilens_vindubredde(self):
        # Kjerneregelen i denne omarbeidingen: samme absolutte avvik skal
        # straffes hardere for en stil med et smalt toleransevindu enn for en
        # stil med et bredt vindu, fordi straffen normaliseres mot bredden.
        smalt_vindu_straff, _, _ = _avvik_numerisk(
            0.996, 1.000, 1.004, 0.0, 30, 30, lambda d: "u", lambda d: "o"
        )  # vindu = 0.004, avvik = 0.004 -> normalisert avvik = 1.0
        bredt_vindu_straff, _, _ = _avvik_numerisk(
            0.996, 1.000, 1.020, 0.0, 30, 30, lambda d: "u", lambda d: "o"
        )  # vindu = 0.020, samme absolutte avvik = 0.004 -> normalisert avvik = 0.2
        self.assertLess(smalt_vindu_straff, bredt_vindu_straff)


class TestAvvikSensoriskHelper(unittest.TestCase):

    def test_sensorisk_innenfor_epsilon_gir_ikke_avvik(self):
        d, diff = _avvik_sensorisk(1.98, 2.0)
        self.assertEqual(d, 0.0)
        self.assertIsNone(diff)

    def test_sensorisk_under_epsilon_gir_avvik(self):
        d, diff = _avvik_sensorisk(0.0, 2.0)
        self.assertLess(d, 0.0)
        self.assertAlmostEqual(diff, 2.0)


class TestIbuFlyttallsbugFikset(unittest.TestCase):
    """Regresjonstest for «Mangler 0 IBU»-bugen (krav 3)."""

    def test_ibu_differanse_under_0_5_gir_ikke_mangel(self):
        # Krav 9: differanse under 0.5 IBU skal ikke gi et "Mangler 0 IBU"-utslag.
        oppskrift = _lag_oppskrift(og=1.062, fg=1.011, ibu=22.98, ebc=17, abv=6.7)
        resultat = analyser_stil_og_balanse(oppskrift)
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        self.assertFalse(
            any("IBU" in m for m in bock["mangler"]),
            f"Uventet IBU-mangel: {bock['mangler']}",
        )

    def test_ibu_differanse_over_epsilon_vises_med_desimaler(self):
        # Et reelt IBU-avvik skal aldri vises avrundet til "0 IBU".
        ibu_under_grense = 23 - (_EPS_IBU + 0.6)
        oppskrift = _lag_oppskrift(og=1.068, fg=1.014, ibu=ibu_under_grense, ebc=17, abv=6.7)
        resultat = analyser_stil_og_balanse(oppskrift)
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        ibu_mangel = next((m for m in bock["mangler"] if "IBU" in m), None)
        self.assertIsNotNone(ibu_mangel)
        self.assertNotIn("Mangler 0 IBU", ibu_mangel)


class TestScoreOgManglerKonsistens(unittest.TestCase):
    """Regresjonstest for hovedbugen: 100 % match samtidig som forklaringen
    listet reelle avvik (OG for lav + manglende toast)."""

    def test_rapportert_scenario_gir_ikke_100_prosent(self):
        oppskrift = _lag_oppskrift(
            og=1.062, fg=1.011, ibu=22.98, ebc=17, abv=6.7,
            flavor_profile={"Maltfylde": 7.0, "Brød": 6.0, "Bitterhet": 3.0},  # ingen Toast
            yeast="wlp_830",  # lagergjær -> trigger signatur-boost for Bock-stiler
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")

        self.assertLess(bock["score"], 100, "Stilen fikk 100 % til tross for reelle avvik")
        self.assertTrue(bock["mangler"], "OG-avviket skal fortsatt vises som mangel")
        self.assertTrue(
            any("OG" in m or "sukkermengde" in m for m in bock["mangler"]),
            f"Forventet OG-mangel, fikk: {bock['mangler']}",
        )
        self.assertFalse(
            any("IBU" in m for m in bock["mangler"]),
            f"IBU skal ikke lenger trigge falsk mangel: {bock['mangler']}",
        )
        self.assertTrue(
            any("toast" in s.lower() for s in bock["onsket_sensorisk"]),
            "Toast skal presenteres som ønsket sensorisk preg, ikke som rød mangel",
        )
        self.assertFalse(
            any("toast" in m.lower() for m in bock["mangler"]),
            f"Toast skal ikke lenger ligge i mangler-listen: {bock['mangler']}",
        )

    def test_full_match_gir_faktisk_100_prosent(self):
        # Krav 8: 100 % skal fortsatt være oppnåelig ved et reelt fullt treff
        # (ingen mangler, ingen ønsket sensorisk preg utestående).
        oppskrift = _lag_oppskrift(
            og=1.068, fg=1.014, ibu=29, ebc=17, abv=6.8,
            flavor_profile={"Maltfylde": 6.0, "Brød": 5.0, "Toast": 2.0, "Bitterhet": 2.0},
            yeast="wlp_830",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        self.assertEqual(bock["mangler"], [])
        self.assertEqual(bock["onsket_sensorisk"], [])
        self.assertEqual(bock["score"], 100)

    def test_score_som_ellers_ville_blitt_lostet_til_100_blir_begrenset(self):
        # En score som (før tak) ville blitt løftet til/mot 100 via
        # signaturbonus, men som fortsatt har et reelt (ikke-kritisk) avvik,
        # skal begrenses til _TAK_AVVIK og ikke vises som 100.
        oppskrift = _lag_oppskrift(
            og=1.063, fg=1.011, ibu=23, ebc=17, abv=6.7,
            flavor_profile={"Maltfylde": 7.0, "Brød": 6.0, "Toast": 3.0, "Bitterhet": 3.0},
            yeast="wlp_830",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        self.assertTrue(bock["mangler"])
        self.assertEqual(bock["kritiske_avvik"], 0)
        self.assertLess(bock["score"], 100)


class TestGenerelleRegler(unittest.TestCase):
    """Regler som skal gjelde for ALLE stiler, ikke bare de tre nevnt i saken.
    Sjekker invarianter på tvers av hele stil_liste i stedet for å slå opp
    enkeltstiler ved navn."""

    def test_kritiske_avvik_gir_alltid_tak_uansett_stil(self):
        # En oppskrift som er ekstremt langt unna alle stiler (høy OG, høy
        # ABV, høy IBU, mørk farge). Uansett hvilken stil det gjelder, eller
        # om den får signaturbonus, skal ingen stil med >= 2 kritiske avvik
        # overstige _TAK_KRITISK.
        oppskrift = _lag_oppskrift(
            og=1.110, fg=1.030, ibu=90, ebc=120, abv=13.0,
            flavor_profile={}, yeast="wlp_830",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        antall_sjekket = 0
        for s in resultat["stil_liste"]:
            if s["kritiske_avvik"] >= 2:
                antall_sjekket += 1
                self.assertLessEqual(
                    s["score"], 80,
                    f"{s['stil']} har {s['kritiske_avvik']} kritiske avvik men score {s['score']}%",
                )
        self.assertGreater(antall_sjekket, 0, "Testoppskriften traff ingen stiler med kritiske avvik")

    def test_signaturbonus_kan_ikke_lofte_forbi_kritisk_tak(self):
        # Samme ekstreme oppskrift, men med en gjær som gir signaturbonus for
        # flere av stilene den ellers ikke passer til (lager -> Bock/Pilsner).
        # Bonusen skal aldri klare å løfte en stil med kritiske avvik forbi taket.
        oppskrift = _lag_oppskrift(
            og=1.110, fg=1.030, ibu=90, ebc=120, abv=13.0,
            flavor_profile={}, yeast="wlp_830",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        for s in resultat["stil_liste"]:
            if s["kritiske_avvik"] >= 2:
                self.assertLessEqual(s["score"], 80)

    def test_hundre_prosent_krever_ingen_mangler_eller_onsket_sensorikk(self):
        # Generell invariant (krav 2/8): uansett stil kan score kun være 100
        # dersom både mangler og onsket_sensorisk er tomme.
        oppskrift = _lag_oppskrift(
            og=1.068, fg=1.014, ibu=29, ebc=17, abv=6.8,
            flavor_profile={"Maltfylde": 6.0, "Brød": 5.0, "Toast": 2.0, "Bitterhet": 2.0},
            yeast="wlp_830",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        for s in resultat["stil_liste"]:
            if s["score"] >= 100:
                self.assertEqual(s["mangler"], [], f"{s['stil']} fikk 100 % med mangler: {s['mangler']}")
                self.assertEqual(
                    s["onsket_sensorisk"], [],
                    f"{s['stil']} fikk 100 % med ønsket sensorisk preg: {s['onsket_sensorisk']}",
                )


class TestMunichDominertBockScenario(unittest.TestCase):
    """
    Regresjonstest for den rapporterte saken: en sterk, Munich-dominert
    lager (OG ~1.062, FG ~1.011, ABV ~6.7 %, IBU ~23, EBC ~12, W-34/70) ble
    vist som Heller Bock 99 %, Tsjekkisk Pilsner 93 %, Tysk Pilsner 91 % —
    urealistisk høye pilsner-prosenter for et øl med feil OG-område, feil
    farge og feil ABV for pilsnerstilene.

    Assertions er relasjonelle (rangering, terskler) — ingen eksakt scoretall
    for denne ene oppskriften er hardkodet, slik at testen speiler den
    generelle modellen og ikke et spesialtilfelle.
    """

    def _oppskrift(self):
        return _lag_oppskrift(
            og=1.062, fg=1.011, ibu=23.0, ebc=12.0, abv=6.7,
            flavor_profile={
                "Maltfylde": 8.0, "Brød": 7.0, "Toast": 4.0,
                "Bitterhet": 2.9, "Sitrus": 0.0,
            },
            yeast="saflager_w3470",  # W-34/70
            malts=[
                {"id": "munich", "mengde": 3.6},
                {"id": "vienna", "mengde": 1.56},
                {"id": "pilsner_malt", "mengde": 0.78},
            ],
        )

    def test_heller_bock_er_naermeste_stil(self):
        # OG 1.062 var, da denne testen ble skrevet, en liten (0.002) miss
        # for Heller Bock (1.064-1.072) og dermed nærmeste kandidat kun ved
        # eliminasjon. Etter at Historisk Wiesn-Märzen (1.060-1.068) fikk et
        # eget, korrekt OG-vindu (jf. 2026-07-26-oppfølgingen), er OG 1.062
        # en presis (0 avviks) treff for DEN stilen — som nå korrekt vinner
        # som nærmeste stil for akkurat denne oppskriften.
        resultat = analyser_stil_og_balanse(self._oppskrift())
        self.assertEqual(resultat["stil"], "Historisk Wiesn-Märzen")

    def test_heller_bock_far_ikke_99_prosent(self):
        resultat = analyser_stil_og_balanse(self._oppskrift())
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        self.assertNotEqual(bock["score"], 99)

    def test_pilsnerstiler_far_ikke_over_90_prosent(self):
        resultat = analyser_stil_og_balanse(self._oppskrift())
        for navn in ("Tysk Pilsner", "Tsjekkisk Pilsner"):
            stil = _finn_stil(resultat, navn)
            self.assertLessEqual(stil["score"], 90, f"{navn} fikk {stil['score']}%")

    def test_heller_bock_scorer_hoyere_enn_pilsnerstilene(self):
        resultat = analyser_stil_og_balanse(self._oppskrift())
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        for navn in ("Tysk Pilsner", "Tsjekkisk Pilsner"):
            stil = _finn_stil(resultat, navn)
            self.assertGreater(
                bock["score"], stil["score"],
                f"Heller Bock ({bock['score']}%) skal rangere over {navn} ({stil['score']}%)",
            )

    def test_pilsnerstiler_har_flere_kritiske_avvik(self):
        # Bekrefter at det er OG/ABV/farge-avvikene (ikke en tilfeldig
        # scorejustering) som faktisk trigger taket for pilsnerstilene.
        #
        # Steg F11K (Modell C): terskelen senket fra >= 2 til >= 1. OG/FG/ABV
        # er matematisk korrelerte og grupperes nå til MAKS ett kritisk avvik
        # i stedet for opptil tre separate (se _kombiner_styrkeklynge i
        # style_engine.py). For Tsjekkisk Pilsner i dette scenarioet er OG,
        # FG OG ABV alle kritiske, men bidrar nå kun med 1 (ikke 3) til
        # kritiske_avvik — testens opprinnelige ">= 2" var en direkte
        # konsekvens av den gamle, ukorrelerte tellingen, ikke et selvstendig
        # krav. Tysk Pilsner har fortsatt >= 2 (styrkeklyngen + kritisk EBC),
        # så IBU/EBC sin uavhengige telling er uendret og fortsatt dekket.
        resultat = analyser_stil_og_balanse(self._oppskrift())
        for navn in ("Tysk Pilsner", "Tsjekkisk Pilsner"):
            stil = _finn_stil(resultat, navn)
            self.assertGreaterEqual(
                stil["kritiske_avvik"], 1,
                f"{navn} forventet >= 1 kritisk avvik, fikk {stil['kritiske_avvik']}",
            )


class TestMarzenIBiblioteket(unittest.TestCase):
    """
    Regresjonstest for at Märzen (og søskenstilene Festbier/Vienna Lager)
    manglet helt fra BJCP-biblioteket i style_engine.py — de fantes ikke som
    kandidat i det hele tatt, uavhengig av oppskriftens tall. Det var ikke et
    filtrerings- eller scoreproblem, men et datahull.

    Testene bruker en Munich I/Munich II/Vienna-dominert sterk lager, men
    assertions er relasjonelle/generelle (rangering, alltid-til-stede), ikke
    hardkodede scoretall for denne ene oppskriften.
    """

    def _munich_vienna_oppskrift(self, **overrides):
        base = dict(
            og=1.062, fg=1.011, ibu=23.0, ebc=12.0, abv=6.7,
            flavor_profile={
                "Maltfylde": 8.0, "Brød": 7.0, "Toast": 4.0,
                "Bitterhet": 2.9, "Sitrus": 0.0,
            },
            yeast="saflager_w3470",  # W-34/70
            malts=[
                {"id": "munich_1", "mengde": 2.52},
                {"id": "munich_2", "mengde": 1.08},
                {"id": "vienna", "mengde": 1.56},
                {"id": "pilsner_malt", "mengde": 0.78},
            ],
        )
        base.update(overrides)
        return _lag_oppskrift(**base)

    def test_marzen_finnes_alltid_som_kandidat(self):
        # Generell regel: candidate-listen skal aldri filtrere bort en
        # definert stil basert på oppskriftens tall — kun scoren skal variere.
        # Sjekkes både for en "normal" og en ekstrem (langt utenfor alle
        # stilvinduer) oppskrift.
        for oppskrift in (
            self._munich_vienna_oppskrift(),
            _lag_oppskrift(og=1.150, fg=1.040, ibu=120, ebc=200, abv=15.0),
        ):
            resultat = analyser_stil_og_balanse(oppskrift)
            navn_i_lista = {s["stil"] for s in resultat["stil_liste"]}
            self.assertIn("Märzen", navn_i_lista)
            self.assertIn("Festbier", navn_i_lista)
            self.assertIn("Vienna Lager", navn_i_lista)

    def test_marzen_ligger_ikke_utenfor_vinduet_uten_a_bli_flagget_riktig(self):
        # Selv med 1-2 verdier litt utenfor stilvinduet skal Märzen fortsatt
        # dukke opp med en meningsfull (ikke-null) score, ikke forsvinne.
        resultat = analyser_stil_og_balanse(self._munich_vienna_oppskrift())
        marzen = _finn_stil(resultat, "Märzen")
        self.assertGreater(marzen["score"], 0)

    def test_marzen_rangerer_klart_over_pilsnerstilene(self):
        # Steg F11K (Modell C): det faste "+15 poeng"-margin-kravet er
        # fjernet. Modell C demper korrelerte OG/FG/ABV-straffer for ALLE
        # stiler likt — inkludert Tsjekkisk Pilsner, som her også har et
        # korrelert (om enn mindre presist) styrkeavvik og derfor får en
        # mindre streng straff enn før (score 65 -> 80 i denne testens
        # scenario). Marginen på 15 poeng var en tilfeldig konsekvens av den
        # gamle uavhengige trippeltellingen, ikke et selvstendig krav.
        #
        # Steg F11K-R (pre-commit review): en ren `assertGreater` (>) uten
        # noen minimumsmargin beskytter ikke lenger ordet "klart" i
        # testnavnet — den ville bestått selv med en 1 poengs forskjell.
        # Faktisk observert margin i dette scenarioet er 85-80=5 (mot
        # Tsjekkisk Pilsner) og 85-20=65 (mot Tysk Pilsner). Terskelen under
        # (>= 3) er bevisst satt LAVERE enn det faktisk observerte minimumet
        # (5), med litt slingringsmonn, og er IKKE tunet til å treffe et
        # eksakt tall — den skal bare utelukke en nesten-lik/sammenfallende
        # score, som en bar `>` ikke gjør.
        _MINSTE_MARGIN = 3
        resultat = analyser_stil_og_balanse(self._munich_vienna_oppskrift())
        marzen = _finn_stil(resultat, "Märzen")
        for navn in ("Tysk Pilsner", "Tsjekkisk Pilsner"):
            pils = _finn_stil(resultat, navn)
            self.assertGreaterEqual(
                marzen["score"] - pils["score"], _MINSTE_MARGIN,
                f"Märzen ({marzen['score']}%) skal rangere KLART over {navn} ({pils['score']}%), "
                f"ikke bare marginalt",
            )

    def test_heller_bock_kan_fortsatt_ranger_forst_naar_og_abv_tilsier_det(self):
        # ABV 6.7 % er midt i Bock-intervallet, men over canonical Märzens
        # øvre grense (6.3 %) — Heller Bock skal fortsatt slå CANONICAL
        # Märzen på raw_score, uendret av senere endringer.
        #
        # Selve "nærmeste stil"-headlinen peker derimot nå på Historisk
        # Wiesn-Märzen (1.060-1.068), siden OG 1.062 er et presist (0 avviks)
        # treff for DEN stilen mot et lite (0.002) miss for Heller Bock
        # (1.064-1.072) — jf. 2026-07-26-oppfølgingen som ga den historiske
        # stilen sitt eget, korrekte OG-vindu. Dette er ikke en regresjon i
        # Bock-vs-Märzen-sammenligningen testen egentlig handler om.
        resultat = analyser_stil_og_balanse(self._munich_vienna_oppskrift())
        self.assertEqual(resultat["stil"], "Historisk Wiesn-Märzen")
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        marzen = _finn_stil(resultat, "Märzen")
        self.assertGreater(bock["raw_score"], marzen["raw_score"])

    def test_marzen_kan_ranger_forst_naar_og_abv_tilsier_det(self):
        # Motsatt tilfelle: når OG/ABV/EBC ligger tydelig i Märzens eget
        # vindu og tydelig utenfor Heller Bocks, skal Märzen vinne som
        # nærmeste stil — modellen skal ikke ha en fast favoritt.
        oppskrift = self._munich_vienna_oppskrift(og=1.057, abv=6.1, ebc=18)
        resultat = analyser_stil_og_balanse(oppskrift)
        self.assertEqual(resultat["stil"], "Märzen")


class TestVisningsscoreBevarerRangering(unittest.TestCase):
    """Regresjonstester for oppryddingen 2026-07-26: den viste prosenten
    ("score") skal ikke lenger kunne kollapse to stiler med tydelig ulik
    raw_score til samme tall, en stil med flere synlige numeriske avvik
    skal ikke kunne vises som nesten perfekt, og signaturbonus skal kunne
    endre rangeringen mellom stiler uten å fjerne/skjule mangler-listen."""

    def _munich_vienna_oppskrift(self, **overrides):
        # Samme rapporterte oppskrift som TestMunichDominertBockScenario/
        # TestMarzenIBiblioteket: Heller Bock (raw høy, ett avvik) og Märzen
        # (raw lavere, tre avvik) endte begge på 95 % før denne fiksen.
        base = dict(
            og=1.062, fg=1.011, ibu=23.0, ebc=12.0, abv=6.7,
            flavor_profile={
                "Maltfylde": 8.0, "Brød": 7.0, "Toast": 4.0,
                "Bitterhet": 2.9, "Sitrus": 0.0,
            },
            yeast="saflager_w3470",
            malts=[
                {"id": "munich_1", "mengde": 2.52},
                {"id": "munich_2", "mengde": 1.08},
                {"id": "vienna", "mengde": 1.56},
                {"id": "pilsner_malt", "mengde": 0.78},
            ],
        )
        base.update(overrides)
        return _lag_oppskrift(**base)

    def test_ulik_raw_score_gir_ikke_lik_visningsscore(self):
        resultat = analyser_stil_og_balanse(self._munich_vienna_oppskrift())
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        marzen = _finn_stil(resultat, "Märzen")

        self.assertGreater(
            bock["raw_score"], marzen["raw_score"],
            "Testforutsetningen (Heller Bock har høyere raw_score enn Märzen) holder ikke lenger",
        )
        self.assertNotEqual(
            bock["score"], marzen["score"],
            "To stiler med tydelig ulik raw_score vises fortsatt med identisk prosent til brukeren",
        )
        self.assertGreater(
            bock["score"], marzen["score"],
            "Visningsscoren bevarer ikke rangeringen raw_score uttrykker",
        )

    def test_tre_numeriske_avvik_hindrer_naer_perfekt_score(self):
        resultat = analyser_stil_og_balanse(self._munich_vienna_oppskrift())
        marzen = _finn_stil(resultat, "Märzen")

        self.assertGreaterEqual(
            len(marzen["mangler"]), _MANGE_AVVIK_ANTALL_FOR_TAK,
            "Testforutsetningen (Märzen har minst tre synlige numeriske avvik) holder ikke lenger",
        )
        self.assertLessEqual(
            marzen["score"], _TAK_FLERE_AVVIK,
            "En stil med flere reelle numeriske avvik ble likevel vist nær perfekt",
        )
        self.assertLess(marzen["score"], _TAK_AVVIK)

    def test_signaturbonus_endrer_rangering_uten_a_skjule_avvik(self):
        # Identisk tallprofil og mangler, kun gjæren endres. Lagergjær skal
        # utløse signaturbonus for Heller Bock (påvirker rangering), men
        # OG-avviket (mangel) skal fortsatt vises uendret uansett gjærvalg.
        felles_kwargs = dict(
            og=1.062, fg=1.011, ibu=23.0, ebc=12.0, abv=6.7,
            flavor_profile={"Maltfylde": 8.0, "Brød": 7.0, "Toast": 4.0, "Bitterhet": 2.9},
        )
        uten_signatur = _lag_oppskrift(yeast="safale_us_05", **felles_kwargs)
        med_signatur = _lag_oppskrift(yeast="saflager_w3470", **felles_kwargs)

        r1 = _finn_stil(analyser_stil_og_balanse(uten_signatur), "Heller Bock (Mai-Bock)")
        r2 = _finn_stil(analyser_stil_og_balanse(med_signatur), "Heller Bock (Mai-Bock)")

        self.assertEqual(
            r1["mangler"], r2["mangler"],
            "Signaturbonus endret/skjulte den reelle mangel-listen",
        )
        self.assertEqual(r1["raw_score"], r2["raw_score"])
        self.assertEqual(r1["signaturbonus"], 0)
        self.assertGreater(r2["signaturbonus"], 0)
        self.assertGreater(
            r2["score"], r1["score"],
            "Signaturbonus skal kunne endre den viste rangeringen for stilen",
        )


class TestHistoriskWiesnMarzenVindu(unittest.TestCase):
    """
    Regresjonstest for at Historisk Wiesn-Märzen ved en feil beholdt samme
    OG-vindu (1.054-1.060) som canonical Märzen da stilen først ble lagt til
    — kun FG/ABV ble utvidet den gangen. En reell sterk Wiesn-oppskrift
    (OG ~1.064-1.065, ABV ~6.7 %) ble dermed feilaktig vist med "For høy OG"
    og "For høy ABV" mot sin EGEN historiske stil.

    Bruker en representativ oppskrift bygget på ekte maltdata
    (data/master_malt.json) og de tallene brukeren oppga (OG/ABV/IBU), ikke
    en hardkodet "fasit"-poengsum — assertions er relasjonelle.
    """

    def _malt_flavor(self):
        malt_db_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "master_malt.json",
        )
        with open(malt_db_path, encoding="utf-8") as f:
            malt_db = json.load(f)
        flatt_malt = {info.get("display_name", k): info for k, info in malt_db.items() if info}
        malt_calc = [
            {"navn": "Munich I", "mengde": 0.70},
            {"navn": "Munich II", "mengde": 4.60},
            {"navn": "Vienna Malt", "mengde": 1.80},
        ]
        _, poeng = generer_smakshjul(malt_calc, flatt_malt, [], {}, 23.5, "SafLager W-34/70", {})
        return poeng

    def _wiesn_oppskrift(self, **overrides):
        base = dict(
            og=1.064, fg=1.013, ibu=23.5, ebc=17.5, abv=6.7,
            flavor_profile=self._malt_flavor(),
            yeast="saflager_w3470",
            malts=[
                {"id": "weyermann_munich_1", "mengde": 0.70},
                {"id": "munich_ii", "mengde": 4.60},
                {"id": "vienna", "mengde": 1.80},
            ],
        )
        base.update(overrides)
        return _lag_oppskrift(**base)

    # -- 1. Canonical Märzen er urørt -------------------------------------
    def test_canonical_marzen_beholder_offisielle_grenser(self):
        # OG 1.062 er over canonical Märzens offisielle 2021-maks (1.060) —
        # skal fortsatt flagges som "for høy" for DENNE stilen, uavhengig av
        # at Historisk Wiesn-Märzen nå tillater akkurat denne verdien.
        oppskrift = self._wiesn_oppskrift(og=1.062)
        resultat = analyser_stil_og_balanse(oppskrift)
        canonical = _finn_stil(resultat, "Märzen")
        # Teksten ble bevisst forbedret i Steg F11C (2026-08-06) til å vise
        # oppskriftens faktiske verdi og avviksstørrelse, ikke bare grensen —
        # sjekker derfor det nye "styrke i vørteren"-merket og
        # komma-formatert "1,060" i stedet for det gamle "sukkermengde"/"1.060".
        self.assertTrue(
            any("styrke i vørteren" in m and "1,060" in m for m in canonical["mangler"]),
            f"Canonical Märzen sitt OG-tak ser ut til å ha endret seg: {canonical['mangler']}",
        )

    # -- 2. Historisk Wiesn-Märzen tillater OG ~1.065 / ABV ~6.7 % --------
    def test_historisk_wiesn_marzen_tillater_sterkere_profil(self):
        resultat = analyser_stil_og_balanse(self._wiesn_oppskrift())
        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        self.assertFalse(
            any("OG" in m or "sukkermengde" in m for m in wiesn["mangler"]),
            f"OG ~1.064 skal være innenfor det historiske vinduet: {wiesn['mangler']}",
        )
        self.assertFalse(
            any("alkohol" in m for m in wiesn["mangler"]),
            f"ABV ~6.7% skal være innenfor det historiske vinduet: {wiesn['mangler']}",
        )

    # -- 3. En svak MODERNE Märzen får ikke automatisk perfekt historisk match
    def test_svak_moderne_marzen_far_ikke_automatisk_perfekt_historisk_match(self):
        # OG midt i canonical Märzens vindu (1.057) ligger UNDER det
        # historiske vinduets nedre grense (1.060) — skal gi et synlig avvik
        # for Historisk Wiesn-Märzen, ikke 100 %.
        svak_moderne = self._wiesn_oppskrift(og=1.057, fg=1.011, abv=6.0, ibu=21.0)
        resultat = analyser_stil_og_balanse(svak_moderne)
        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        self.assertTrue(wiesn["mangler"], "En moderne-styrke Märzen ga likevel ingen avvik mot historisk stil")
        self.assertLess(wiesn["score"], 100)

    # -- 7. Full match gir faktisk 100 % -----------------------------------
    def test_passende_historisk_wiesn_oppskrift_kan_na_100_prosent(self):
        resultat = analyser_stil_og_balanse(self._wiesn_oppskrift())
        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        self.assertEqual(wiesn["mangler"], [], f"Uventede mangler: {wiesn['mangler']}")
        self.assertEqual(wiesn["onsket_sensorisk"], [], f"Uventet ønsket sensorisk preg: {wiesn['onsket_sensorisk']}")
        self.assertEqual(wiesn["score"], 100)

    # -- 8. Signaturbonus alene kan ikke gi 100 % med reelle mangler -------
    def test_signaturbonus_kan_ikke_alene_gi_100_med_reelle_mangler(self):
        # Samme oppskrift, men med EBC dratt godt over det historiske
        # vinduet (32) — en reell mangel som lagergjær-signaturbonusen
        # (+20) ikke skal kunne dekke over.
        oppskrift = self._wiesn_oppskrift(ebc=40.0)
        resultat = analyser_stil_og_balanse(oppskrift)
        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        self.assertTrue(wiesn["mangler"])
        self.assertGreater(wiesn["signaturbonus"], 0, "Forventet at lagergjær fortsatt gir signaturbonus")
        self.assertLess(wiesn["score"], 100)

    # -- 9. Den rapporterte oppskriften rangerer historisk foran moderne/pils
    def test_rapportert_oppskrift_rangerer_historisk_foran_moderne_og_pilsner(self):
        resultat = analyser_stil_og_balanse(self._wiesn_oppskrift())
        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        for navn in ("Märzen", "Tysk Pilsner", "Tsjekkisk Pilsner"):
            andre = _finn_stil(resultat, navn)
            self.assertGreater(
                wiesn["score"], andre["score"],
                f"Historisk Wiesn-Märzen ({wiesn['score']}%) skal rangere over {navn} ({andre['score']}%)",
            )


class TestGodtInnenforStil(unittest.TestCase):
    """Regresjonstest (Kvernhaug-gjennomgang 2026-07-27, krav 1): en oppskrift
    som ligger komfortabelt MIDT I en stils vindu på alle numeriske felt, med
    god margin over alle smak_krav-minimumer, skal score 100 % — ingen avvik,
    ingen ønsket sensorikk utestående. Ingen gjær-/humle-/malt-signatur er
    involvert her (US-05, ingen signaturhumler), slik at testen isolerer det
    rene numerisk+sensorisk grunnlaget fra signaturbonusen."""

    def test_midt_i_tysk_pilsner_vinduet_gir_100_prosent(self):
        # Tysk Pilsner: og(1.044,1.050) fg(1.008,1.013) ibu(22,40) ebc(4,8)
        # abv(4.4,5.2) — alle verdier under er midtpunktet i sitt vindu.
        oppskrift = _lag_oppskrift(
            og=1.047, fg=1.0105, ibu=31.0, ebc=6.0, abv=4.8,
            flavor_profile={"Brød": 6.0, "Sitrus": 3.0, "Bitterhet": 6.0},
            yeast="safale_us_05",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        pils = _finn_stil(resultat, "Tysk Pilsner")
        self.assertEqual(pils["mangler"], [])
        self.assertEqual(pils["onsket_sensorisk"], [])
        self.assertEqual(pils["kritiske_avvik"], 0)
        self.assertEqual(pils["score"], 100)
        self.assertEqual(pils["raw_score"], 100)


class TestTydeligAvvikUtenAVaereKritisk(unittest.TestCase):
    """Regresjonstest (krav 1): et avvik som er klart større enn epsilon-
    støyen, men under _KRITISK_NORM_TERSKEL (halve stilens vindu), skal gi et
    synlig mangel-oppslag og redusert score — men verken bli slettet som støy
    (som epsilon-testene sjekker) eller trigge kritisk-taket (som
    TestGenerelleRegler sjekker). Dette dekker mellomsjiktet mellom de to."""

    def test_alenestaaende_abv_avvik_pa_kvart_vindu_gir_synlig_men_ikke_kritisk_mangel(self):
        # Tysk Pilsner ABV-vindu (4.4, 5.2), bredde 0.8. ABV=5.45 er 0.25 over
        # grensen -> normalisert avvik 0.3125: klart mer enn epsilon (0.05),
        # men under det kritiske skillet på 0.5. Alle andre felt ligger midt
        # i vinduet slik at ABV er det ENESTE avviket.
        oppskrift = _lag_oppskrift(
            og=1.047, fg=1.0105, ibu=31.0, ebc=6.0, abv=5.45,
            flavor_profile={"Brød": 6.0, "Sitrus": 3.0, "Bitterhet": 6.0},
            yeast="safale_us_05",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        pils = _finn_stil(resultat, "Tysk Pilsner")
        self.assertEqual(len(pils["mangler"]), 1)
        self.assertIn("alkohol", pils["mangler"][0])
        self.assertEqual(pils["kritiske_avvik"], 0)
        self.assertLess(pils["score"], 100)
        self.assertGreater(pils["score"], 80, "Ett enkelt, ikke-kritisk avvik straffet uforholdsmessig hardt")


class TestLiteGrenseavvikToleresIHelePipelinen(unittest.TestCase):
    """Krav 1 (supplement til TestAvvikNumeriskHelper/TestIbuFlyttallsbugFikset):
    samme epsilon-toleranse bekreftet via det offentlige, hele
    analyser_stil_og_balanse-grensesnittet for et ANNET felt enn IBU (OG),
    slik at dekningen ikke er avhengig av kun én tidligere skrevet test."""

    def test_og_marginalt_under_grensen_innenfor_epsilon_gir_ikke_mangel(self):
        # Tysk Pilsner OG-min er 1.044. _EPS_OG er 0.0005 - en verdi 0.0002
        # under grensen skal absorberes av epsilon og ikke gi noe utslag.
        oppskrift = _lag_oppskrift(
            og=1.044 - 0.0002, fg=1.0105, ibu=31.0, ebc=6.0, abv=4.8,
            flavor_profile={"Brød": 6.0, "Sitrus": 3.0, "Bitterhet": 6.0},
            yeast="safale_us_05",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        pils = _finn_stil(resultat, "Tysk Pilsner")
        self.assertFalse(any("sukkermengde" in m for m in pils["mangler"]))
        self.assertEqual(pils["score"], 100)


class TestNumeriskNaermesteVsSamletTopp(unittest.TestCase):
    """
    Regresjonstest (Kvernhaug-gjennomgang 2026-07-27, krav 3): ui/style_panel.py
    viser to forskjellige rangeringer på samme side — headline «Nærmeste stil»
    (basert på raw_score, FØR signaturbonus) og prosentlisten under (sortert
    på den justerte, endelige `score`, som inkluderer signaturbonus/-straff).
    Disse to er MED VILJE forskjellige begreper (se kommentaren i
    style_engine.py ved `topp_match_reell`), men kan derfor peke på to ulike
    stiler for samme oppskrift — noe brukergrensesnittet tidligere ikke
    forklarte, og som kunne lest ut som et motstridende resultat.

    Denne testen bruker en funnet, reproduserbar oppskrift (belgisk gjær +
    en engelsk-bitter-lignende tallprofil) der English Bitter vinner
    headline på raw_score, mens English Dark Mild vinner toppen av den
    sorterte prosentlisten — fordi belgisk gjærsignatur straffer
    _ENGLISH_STYLES_BASE (som English Bitter er medlem av) med -15, mens
    English Dark Mild ikke er medlem av den gruppen og forblir upåvirket.

    Fasit her er IKKE at scoringsmodellen skal endres (ikke rør stilgrensene
    eller signaturreglene) — fasiten er at UI-et (ui/style_panel.py) skal
    forklare forskjellen tydelig i stedet for å late som de to tallene alltid
    er enige. Se TestUiTeksterForklarerNumeriskVsSamlet i
    tests/test_style_panel_ui.py for selve UI-regresjonen."""

    def _oppskrift(self):
        return _lag_oppskrift(
            og=1.031, fg=1.0082, ibu=32.2, ebc=17.7, abv=2.99,
            flavor_profile={
                "Brød": 6.0, "Sitrus": 1.3, "Bitterhet": 2.0, "Fruktighet": 3.6,
                "Krydder": 6.4, "Maltfylde": 3.4, "Toast": 6.3, "Karamell": 0.4,
                "Nøtter": 1.7, "Sjokolade": 2.1, "Kaffe": 3.1, "Røyk": 3.0,
                "Honning": 0.3, "Jordlig": 5.2, "Tropisk": 5.3, "Steinfrukt": 3.2,
            },
            yeast="wlp500",  # belgisk signatur
        )

    @staticmethod
    def _ui_sortert_toppstil(resultat):
        # Speiler EKSAKT sorteringsnøkkelen ui/style_panel.py bruker for
        # prosentlisten: (-score, prio) — ikke style_engine.py sin interne
        # (prio, -score)-sortering av stil_liste, som brukes til andre formål.
        return sorted(resultat["stil_liste"], key=lambda s: (-s["score"], s["prio"]))[0]

    def test_headline_og_listetopp_kan_peke_pa_ulike_stiler(self):
        resultat = analyser_stil_og_balanse(self._oppskrift())
        headline_stil = resultat["stil"]
        listetopp = self._ui_sortert_toppstil(resultat)

        self.assertEqual(headline_stil, "English Bitter")
        self.assertEqual(listetopp["stil"], "English Dark Mild")
        self.assertNotEqual(
            headline_stil, listetopp["stil"],
            "Testforutsetningen (avvikende rangering) holder ikke lenger — "
            "scenariet under er ikke lenger et eksempel på divergens",
        )

    def test_arsaken_er_signaturstraff_ikke_en_feil_i_selve_tallene(self):
        # Bekrefter MEKANISMEN bak avviket: English Bitter rammes av
        # signaturstraffen (medlem av _ENGLISH_STYLES_BASE), English Dark
        # Mild er ikke medlem og er derfor upåvirket — dette er dokumentert,
        # tiltenkt oppførsel i signaturjusteringen, ikke en scoringsbug.
        resultat = analyser_stil_og_balanse(self._oppskrift())
        bitter = _finn_stil(resultat, "English Bitter")
        mild = _finn_stil(resultat, "English Dark Mild")

        self.assertLess(bitter["signaturbonus"], 0, "Forventet at belgisk gjær straffer English Bitter")
        self.assertEqual(mild["signaturbonus"], 0, "English Dark Mild skal ikke påvirkes av belgisk signatur")
        self.assertGreater(bitter["raw_score"], mild["raw_score"], "English Bitter skal fortsatt vinne på rene tall")
        self.assertGreater(mild["score"], bitter["score"], "Men straffen skal gjøre at Dark Mild vinner den viste scoren")


class TestBjcpOffisiellKlassifisering(unittest.TestCase):
    """Regresjonstest (Kvernhaug-gjennomgang 2026-07-27, krav 2, utvidet
    2026-08-10): Vienna Lager, Märzen og Festbier er ekte BJCP 2021-
    kategorier og skal behandles som ordinære stiler (bjcp_offisiell=True,
    standardverdien). Historisk Wiesn-Märzen, Tradisjonelt Norsk Gårdsøl /
    Kveik og Tradisjonelt Norsk Juleøl er alle Kvernhaug-oppfunnede,
    ikke-offisielle kategorier (se forklarende kommentarer i
    style_engine.py) og skal være eksplisitt merket bjcp_offisiell=False —
    kun metadata/visning, IKKE stilgrensene, som denne testen bevisst
    ikke rører. De to norske stilene manglet dette flagget frem til
    2026-08-10 (oppdaget under kartlegging før web-versjonens stilmatch
    skulle omtales presist)."""

    def _stil_liste(self):
        oppskrift = _lag_oppskrift(og=1.055, fg=1.012, ibu=20, ebc=15, abv=6.0)
        return analyser_stil_og_balanse(oppskrift)["stil_liste"]

    def test_vienna_lager_marzen_festbier_er_offisielle_bjcp_stiler(self):
        stiler = self._stil_liste()
        for navn in ("Vienna Lager", "Märzen", "Festbier"):
            stil = _finn_stil({"stil_liste": stiler}, navn)
            self.assertTrue(stil["bjcp_offisiell"], f"{navn} skal være merket som offisiell BJCP-stil")

    def test_historisk_wiesn_marzen_er_ikke_offisiell_bjcp(self):
        stiler = self._stil_liste()
        wiesn = _finn_stil({"stil_liste": stiler}, "Historisk Wiesn-Märzen")
        self.assertFalse(wiesn["bjcp_offisiell"], "Historisk Wiesn-Märzen skal IKKE være merket som offisiell BJCP-stil")

    def test_kveik_og_juleol_er_ikke_offisiell_bjcp(self):
        stiler = self._stil_liste()
        for navn in ("Tradisjonelt Norsk Gårdsøl / Kveik", "Tradisjonelt Norsk Juleøl"):
            stil = _finn_stil({"stil_liste": stiler}, navn)
            self.assertFalse(stil["bjcp_offisiell"], f"{navn} skal IKKE være merket som offisiell BJCP-stil")

    def test_de_fleste_andre_stiler_er_ogsaa_offisielle(self):
        # Stikkprøve på tvers av kategorier — bekrefter at default=True
        # faktisk gjelder for det store flertallet, ikke bare de navngitte.
        stiler = self._stil_liste()
        for navn in ("Tysk Pilsner", "Heller Bock (Mai-Bock)", "Robust Porter", "Belgisk Tripel", "Hazy IPA / NEIPA"):
            stil = _finn_stil({"stil_liste": stiler}, navn)
            self.assertTrue(stil["bjcp_offisiell"], f"{navn} skal være merket som offisiell BJCP-stil")

    def test_kun_tre_stiler_i_hele_biblioteket_er_ikke_offisielle(self):
        stiler = self._stil_liste()
        ikke_offisielle = {s["stil"] for s in stiler if not s["bjcp_offisiell"]}
        self.assertEqual(
            ikke_offisielle,
            {"Historisk Wiesn-Märzen", "Tradisjonelt Norsk Gårdsøl / Kveik", "Tradisjonelt Norsk Juleøl"},
        )

    def test_stilgrensene_for_historisk_wiesn_marzen_er_uendret(self):
        # Bekrefter at kun metadata ble lagt til, ikke selve OG/FG/IBU/EBC/
        # ABV-vinduet (krav: "Ikke endre stilgrensene").
        oppskrift = _lag_oppskrift(og=1.064, fg=1.013, ibu=23.5, ebc=17.5, abv=6.7, yeast="saflager_w3470")
        resultat = analyser_stil_og_balanse(oppskrift)
        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        self.assertEqual(wiesn["mangler"], [], "OG/FG/ABV innenfor det historiske vinduet skal fortsatt gi 0 mangler")


class TestManglerTekstformatering(unittest.TestCase):
    """Steg F11C (2026-08-06): mangel-tekstene for numeriske avvik (OG/FG/
    IBU/EBC/ABV) skal vise hva som er for høyt/lavt, oppskriftens faktiske
    verdi, stilens tillatte område og avviket fra nærmeste grense — ikke
    bare grensen, slik de gjorde før. Disse testene låser kun det NYE
    tekstformatet; selve scoringsmatematikken (_avvik_numerisk) er ikke
    endret og dekkes fortsatt av de eksisterende testene over."""

    _FLAVOR = {"Brød": 6.0, "Sitrus": 3.0, "Bitterhet": 6.0}

    def _pils(self, **overrides):
        base = dict(og=1.047, fg=1.0105, ibu=31.0, ebc=6.0, abv=4.8,
                    flavor_profile=self._FLAVOR, yeast="safale_us_05")
        base.update(overrides)
        resultat = analyser_stil_og_balanse(_lag_oppskrift(**base))
        return _finn_stil(resultat, "Tysk Pilsner")

    def test_og_rett_over_ovre_grense(self):
        pils = self._pils(og=1.051)
        mangel = next(m for m in pils["mangler"] if "styrke i vørteren" in m)
        self.assertEqual(mangel, "For høy styrke i vørteren: OG 1,051 — stilområde 1,044–1,050 — 0,001 over")

    def test_og_langt_over_ovre_grense_viser_storre_avvik_enn_marginalt(self):
        # Selve poenget med F11C: et stort avvik skal IKKE se identisk ut som
        # et marginalt et (jf. F11B punkt 14 — begge fikk samme ❌ og samme
        # grense-tekst før denne endringen).
        pils_marginalt = self._pils(og=1.051)
        pils_stort = self._pils(og=1.080)
        mangel_marginalt = next(m for m in pils_marginalt["mangler"] if "styrke i vørteren" in m)
        mangel_stort = next(m for m in pils_stort["mangler"] if "styrke i vørteren" in m)
        self.assertNotEqual(mangel_marginalt, mangel_stort)
        self.assertIn("0,001 over", mangel_marginalt)
        self.assertIn("0,030 over", mangel_stort)
        self.assertIn("OG 1,080", mangel_stort)

    def test_og_under_nedre_grense(self):
        pils = self._pils(og=1.040)
        mangel = next(m for m in pils["mangler"] if "styrke i vørteren" in m)
        self.assertEqual(mangel, "For lav styrke i vørteren: OG 1,040 — stilområde 1,044–1,050 — 0,004 under")

    def test_fg_over_omradet(self):
        pils = self._pils(fg=1.017)
        mangel = next(m for m in pils["mangler"] if m.startswith("For høy FG"))
        self.assertEqual(mangel, "For høy FG: 1,017 — stilområde 1,008–1,013 — 0,004 over")

    def test_fg_under_omradet(self):
        pils = self._pils(fg=1.004)
        mangel = next(m for m in pils["mangler"] if m.startswith("For lav FG"))
        self.assertEqual(mangel, "For lav FG: 1,004 — stilområde 1,008–1,013 — 0,004 under")

    def test_abv_over_omradet(self):
        pils = self._pils(abv=5.45)
        mangel = next(m for m in pils["mangler"] if "alkohol" in m)
        self.assertEqual(mangel, "For høy alkohol: 5,45 % — stilområde 4,4–5,2 % — 0,25 prosentpoeng over")

    def test_abv_under_omradet(self):
        pils = self._pils(abv=4.0)
        mangel = next(m for m in pils["mangler"] if "alkohol" in m)
        self.assertEqual(mangel, "For lav alkohol: 4,00 % — stilområde 4,4–5,2 % — 0,40 prosentpoeng under")

    def test_ibu_over_omradet(self):
        pils = self._pils(ibu=45.0)
        mangel = next(m for m in pils["mangler"] if "bitterhet" in m.lower())
        self.assertEqual(mangel, "For høy bitterhet: 45,0 IBU — stilområde 22–40 IBU — 5,0 IBU over")

    def test_ibu_under_omradet(self):
        pils = self._pils(ibu=15.0)
        mangel = next(m for m in pils["mangler"] if "bitterhet" in m.lower())
        self.assertEqual(mangel, "For lav bitterhet: 15,0 IBU — stilområde 22–40 IBU — 7,0 IBU under")

    def test_ebc_over_omradet(self):
        pils = self._pils(ebc=20.0)
        mangel = next(m for m in pils["mangler"] if "farge" in m)
        self.assertEqual(mangel, "For mørk farge: 20,0 EBC — stilområde 4–8 EBC — 12,0 EBC over")

    def test_ebc_under_omradet(self):
        pils = self._pils(ebc=2.0)
        mangel = next(m for m in pils["mangler"] if "farge" in m)
        self.assertEqual(mangel, "For lys farge: 2,0 EBC — stilområde 4–8 EBC — 2,0 EBC under")

    def test_norsk_desimalkomma_ikke_engelsk_punktum(self):
        pils = self._pils(og=1.070)
        mangel = next(m for m in pils["mangler"] if "styrke i vørteren" in m)
        self.assertNotIn(".", mangel)
        self.assertIn(",", mangel)

    def test_ingen_flyttallsstoy_i_teksten(self):
        # og=1.0644 er kjent for å gi flyttallsstøy i en rå python-subtraksjon
        # (1.0644 - 1.050 = 0.014400000000000079) -- teksten skal likevel
        # vise en ren, avrundet streng uten støyen.
        pils = self._pils(og=1.0644)
        mangel = next(m for m in pils["mangler"] if "styrke i vørteren" in m)
        self.assertEqual(mangel, "For høy styrke i vørteren: OG 1,064 — stilområde 1,044–1,050 — 0,014 over")
        for stoy in ("0000000", "9999999", "00001", "99999"):
            self.assertNotIn(stoy, mangel)

    def test_verdi_pa_grensen_gir_fortsatt_ingen_manglertekst(self):
        pils = self._pils(og=1.050)
        self.assertFalse(any("styrke i vørteren" in m for m in pils["mangler"]))

    def test_verdi_innenfor_epsilon_gir_fortsatt_ingen_manglertekst(self):
        pils = self._pils(og=1.050 + 0.0002)
        self.assertFalse(any("styrke i vørteren" in m for m in pils["mangler"]))

    def test_sensorisk_tekst_er_uendret(self):
        # Fase 5-krav: sensoriske forklaringer ("har X, stilen ber om Y+")
        # skal IKKE endres i dette steget.
        pils = self._pils(flavor_profile={"Brød": 2.0, "Sitrus": 3.0, "Bitterhet": 6.0})
        onsket = next(o for o in pils["onsket_sensorisk"] if "brød" in o.lower())
        self.assertEqual(onsket, "Ønsket sensorisk preg av *brød* (har 2.0, stilen ber om 4.0+)")

    def test_score_og_kritiske_avvik_uendret_for_isolert_abv_avvik(self):
        # Bekrefter at selve scoringen (ikke bare teksten) er identisk med
        # TestTydeligAvvikUtenAVaereKritisk sitt scenario (samme tall) —
        # score/kritiske_avvik/mangler-lengde er upåvirket av tekstendringen.
        pils = self._pils(abv=5.45)
        self.assertEqual(len(pils["mangler"]), 1)
        self.assertEqual(pils["kritiske_avvik"], 0)
        self.assertEqual(pils["score"], 92)


class TestWiesnMarzenReferansenGirFortsattRiktigProsentEtterTekstendring(unittest.TestCase):
    """Steg F11C: bekrefter, med de samme LIVE-beregnede tallene som Steg
    F11B verifiserte reproduserer det brukeren så i UI-et (batchvolum 25 L,
    dagens data/master_malt.json — se F11B punkt 2/15), at 100 %/95 %/69 %-
    resultatet er UENDRET etter tekstforbedringen, og at de nye tekstene
    faktisk viser riktig verdi/avvik for akkurat denne oppskriften.

    Bruker bevisst IKKE tests/fixtures/recipes/wiesn_marzen_1872.json — den
    fixturens "stats"-felt er kjent utdatert (EBC 15.06 mot dagens
    live-beregnede 20.74, se F11B punkt 15) og skal ikke røres i dette
    steget. Tallene under er bygget direkte, slik
    _analyser_fixture_oppskrift() i test_style_engine_recipes.py gjør det
    internt, uten å lese eller skrive fixture-filen."""

    def _oppskrift(self):
        return _lag_oppskrift(
            og=1.0639925272000001, fg=1.011518654896, abv=6.887195739900018,
            ibu=22.19577066725207, ebc=20.743948714358822,
            flavor_profile={
                "Bitterhet": 2.7744713334065088, "Brød": 5.695774647887324,
                "Maltfylde": 7.473239436619719, "Toast": 4.850704225352113,
            },
            yeast="saflager_w3470",
            malts=[
                {"id": "weyermann_munich_1", "mengde": 0.70},
                {"id": "munich_ii", "mengde": 4.60},
                {"id": "vienna", "mengde": 1.80},
            ],
        )

    def test_prosentene_er_uendret(self):
        # Steg F11K (Modell C, 2026-08-07): Märzen sin prosent endret seg
        # fra 69 % til 82 % -- en TILSIKTET konsekvens av at OG- og
        # ABV-avvikene her er korrelerte (begge uttrykker samme underliggende
        # "for sterk vørter") og nå kun straffes fullt for ett av dem, dempet
        # for det andre, i stedet for full uavhengig dobbeltstraff (se
        # _kombiner_styrkeklynge i style_engine.py). Wiesn (0 avvik) og
        # Heller Bock (kun 1 isolert IBU-avvik, ingen styrkeklynge-endring)
        # er UPÅVIRKET og forblir 100 %/95 %, som forventet siden Modell C er
        # bakoverkompatibel når høyst ett styrkefelt avviker.
        resultat = analyser_stil_og_balanse(self._oppskrift())
        self.assertEqual(resultat["stil"], "Historisk Wiesn-Märzen")
        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        marzen = _finn_stil(resultat, "Märzen")
        self.assertEqual(wiesn["score"], 100)
        self.assertEqual(bock["score"], 95)
        self.assertEqual(marzen["score"], 82)

    def test_marzen_forklaringen_viser_faktisk_verdi_og_avvik(self):
        resultat = analyser_stil_og_balanse(self._oppskrift())
        marzen = _finn_stil(resultat, "Märzen")
        og_mangel = next(m for m in marzen["mangler"] if "styrke i vørteren" in m)
        abv_mangel = next(m for m in marzen["mangler"] if "alkohol" in m)
        self.assertEqual(og_mangel, "For høy styrke i vørteren: OG 1,064 — stilområde 1,054–1,060 — 0,004 over")
        self.assertEqual(abv_mangel, "For høy alkohol: 6,89 % — stilområde 5,8–6,3 % — 0,59 prosentpoeng over")

    def test_heller_bock_forklaringen_viser_ibu_avvik_uten_a_endre_scoren(self):
        resultat = analyser_stil_og_balanse(self._oppskrift())
        bock = _finn_stil(resultat, "Heller Bock (Mai-Bock)")
        self.assertEqual(bock["score"], 95)
        ibu_mangel = next(m for m in bock["mangler"] if "bitterhet" in m.lower())
        self.assertEqual(ibu_mangel, "For lav bitterhet: 22,2 IBU — stilområde 23–35 IBU — 0,8 IBU under")


class TestKombinerStyrkeklyngeHelper(unittest.TestCase):
    """Steg F11K (Modell C): direkte enhetstester av selve
    _kombiner_styrkeklynge()-hjelperen, uavhengig av resten av
    stilmatchingen."""

    def test_konstantene_har_forventet_verdi(self):
        self.assertEqual(_STYRKEKLYNGE_NEST_VEKT, 0.375)
        self.assertEqual(_STYRKEKLYNGE_TREDJE_VEKT, 0.175)

    def test_eksempel_fra_spesifikasjonen(self):
        # OG=-20, FG=0, ABV=-30 -> -30 - (20*0.375) = -37.5, IKKE -50.
        self.assertEqual(_kombiner_styrkeklynge(-20, 0, -30), -37.5)

    def test_kun_ett_avvikende_felt_gir_identisk_resultat_uansett_posisjon(self):
        self.assertEqual(_kombiner_styrkeklynge(-20, 0, 0), -20)
        self.assertEqual(_kombiner_styrkeklynge(0, -20, 0), -20)
        self.assertEqual(_kombiner_styrkeklynge(0, 0, -20), -20)

    def test_ingen_avvik_gir_null(self):
        self.assertEqual(_kombiner_styrkeklynge(0, 0, 0), 0)

    def test_trippelavvik_folger_1_0_375_0_175_formelen(self):
        # Størst=-30, nest=-20, tredje=-10 (rekkefølgen på argumentene skal
        # ikke ha noe å si -- funksjonen sorterer selv etter størrelse).
        forventet = -(30 + 20 * 0.375 + 10 * 0.175)
        self.assertEqual(_kombiner_styrkeklynge(-20, -30, -10), forventet)
        self.assertEqual(_kombiner_styrkeklynge(-10, -20, -30), forventet)


class TestModellCBakoverkompatibilitetIsolerteAvvik(unittest.TestCase):
    """Steg F11K, krav 7: dersom KUN ett av OG/FG/ABV avviker, skal
    raw_score, kritiske_avvik og final score være bit-for-bit identiske med
    koden slik den var før Modell C (verifisert direkte mot HEAD-versjonen
    av style_engine.py fra Git-historikken under selve implementasjonen —
    se F11K-sluttrapporten). Basisoppskriften er "midt i Tysk Pilsner sitt
    vindu" (samme mønster som TestGodtInnenforStil/
    TestTydeligAvvikUtenAVaereKritisk), med kun ett felt dratt ut av vinduet
    om gangen."""

    _FLAVOR = {"Brød": 6.0, "Sitrus": 3.0, "Bitterhet": 6.0}

    def _pils(self, **overrides):
        base = dict(og=1.047, fg=1.0105, ibu=31.0, ebc=6.0, abv=4.8,
                    flavor_profile=self._FLAVOR, yeast="safale_us_05")
        base.update(overrides)
        resultat = analyser_stil_og_balanse(_lag_oppskrift(**base))
        return _finn_stil(resultat, "Tysk Pilsner")

    def test_kun_og_avviker(self):
        pils = self._pils(og=1.055)
        self.assertEqual(pils["raw_score"], 75)
        self.assertEqual(pils["score"], 75)
        self.assertEqual(pils["kritiske_avvik"], 1)

    def test_kun_fg_avviker(self):
        pils = self._pils(fg=1.016)
        self.assertEqual(pils["raw_score"], 84)
        self.assertEqual(pils["score"], 84)
        self.assertEqual(pils["kritiske_avvik"], 1)

    def test_kun_abv_avviker(self):
        pils = self._pils(abv=5.6)
        self.assertEqual(pils["raw_score"], 87)
        self.assertEqual(pils["score"], 87)
        self.assertEqual(pils["kritiske_avvik"], 0)


class TestModellCKorrelerteDobbelavvik(unittest.TestCase):
    """Steg F11K, krav 8: to av de tre styrkefeltene avviker samtidig.
    Største straff teller fullt, nest største dempes til
    _STYRKEKLYNGE_NEST_VEKT, og de kritiske styrkefeltene grupperes til
    maks ett bidrag til kritiske_avvik."""

    _FLAVOR = {"Brød": 6.0, "Sitrus": 3.0, "Bitterhet": 6.0}

    def _pils(self, **overrides):
        base = dict(og=1.047, fg=1.0105, ibu=31.0, ebc=6.0, abv=4.8,
                    flavor_profile=self._FLAVOR, yeast="safale_us_05")
        base.update(overrides)
        resultat = analyser_stil_og_balanse(_lag_oppskrift(**base))
        return _finn_stil(resultat, "Tysk Pilsner")

    def test_a_og_pluss_abv(self):
        # d_og=-25 (kritisk), d_abv=-12.5 (ikke kritisk) -> 25 + 12.5*0.375
        # = 29.6875 -> raw_score 100-29.6875 = 70.3125 -> int() = 70
        pils = self._pils(og=1.055, abv=5.6)
        self.assertEqual(pils["raw_score"], 70)
        self.assertEqual(pils["kritiske_avvik"], 1)

    def test_b_og_pluss_fg(self):
        # d_og=-25 (kritisk), d_fg=-15 (kritisk) -> 25 + 15*0.375 = 30.625
        # -> raw_score 100-30.625 = 69.375 -> int() = 69
        pils = self._pils(og=1.055, fg=1.016)
        self.assertEqual(pils["raw_score"], 69)
        self.assertEqual(pils["kritiske_avvik"], 1)

    def test_c_fg_pluss_abv(self):
        # d_fg=-15 (kritisk), d_abv=-12.5 (ikke kritisk) -> 15 + 12.5*0.375
        # = 19.6875 -> raw_score 100-19.6875 = 80.3125 -> int() = 80
        pils = self._pils(fg=1.016, abv=5.6)
        self.assertEqual(pils["raw_score"], 80)
        self.assertEqual(pils["kritiske_avvik"], 1)


class TestModellCTrippelavvik(unittest.TestCase):
    """Steg F11K, krav 9: OG, FG og ABV avviker samtidig. Bekrefter den
    eksplisitte 1.0/0.375/0.175-formelen, og at kritiske_avvik fra
    styrkeklyngen er <= 1 selv når alle tre enkeltfelt er kritiske."""

    def test_trippelavvik_folger_formelen_og_grupperer_kritisk(self):
        oppskrift = _lag_oppskrift(
            og=1.055, fg=1.016, ibu=31.0, ebc=6.0, abv=5.6,
            flavor_profile={"Brød": 6.0, "Sitrus": 3.0, "Bitterhet": 6.0},
            yeast="safale_us_05",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        pils = _finn_stil(resultat, "Tysk Pilsner")

        d_og, _, k_og = _avvik_numerisk(1.055, 1.044, 1.050, _EPS_OG, 30, 30, lambda d: "u", lambda d: "o")
        d_fg, _, k_fg = _avvik_numerisk(1.016, 1.008, 1.013, _EPS_FG, 25, 25, lambda d: "u", lambda d: "o")
        d_abv, _, k_abv = _avvik_numerisk(5.6, 4.4, 5.2, _EPS_ABV, 25, 25, lambda d: "u", lambda d: "o")
        self.assertTrue(k_og and k_fg)
        self.assertFalse(k_abv)

        forventet_kombinert = _kombiner_styrkeklynge(d_og, d_fg, d_abv)
        forventet_raw = max(0, min(int(100 + forventet_kombinert), 100))
        self.assertEqual(pils["raw_score"], forventet_raw)
        self.assertLessEqual(pils["kritiske_avvik"], 1)
        self.assertEqual(pils["kritiske_avvik"], 1, "OG/FG er kritiske -- styrkeklyngen skal gi nøyaktig 1")


class TestModellCIbuEbcUavhengighet(unittest.TestCase):
    """Steg F11K, krav 10: IBU og EBC skal fortsatt straffes FULLT og
    UAVHENGIG av styrkeklyngen -- Modell C reduserer kun dobbelttelling
    INNEN OG/FG/ABV, ikke den generelle strengheten i modellen."""

    _STYRKE = dict(og=1.055, fg=1.016, abv=5.6)  # styrkeklynge, kritiske_avvik=1

    def _pils(self, **overrides):
        base = dict(ibu=31.0, ebc=6.0, flavor_profile={"Brød": 6.0, "Sitrus": 3.0, "Bitterhet": 6.0},
                     yeast="safale_us_05")
        base.update(self._STYRKE)
        base.update(overrides)
        resultat = analyser_stil_og_balanse(_lag_oppskrift(**base))
        return _finn_stil(resultat, "Tysk Pilsner")

    def test_a_styrkeklynge_pluss_kritisk_ebc(self):
        pils = self._pils(ebc=25.0)
        d_ebc, _, k_ebc = _avvik_numerisk(25.0, 4, 8, 0.5, 15, 12, lambda d: "u", lambda d: "o")
        self.assertTrue(k_ebc)
        self.assertEqual(pils["kritiske_avvik"], 2, "styrkeklynge (1) + kritisk EBC (1) = 2")
        self.assertLessEqual(pils["score"], _TAK_KRITISK)

    def test_b_styrkeklynge_pluss_kritisk_ibu(self):
        pils = self._pils(ibu=5.0)
        d_ibu, _, k_ibu = _avvik_numerisk(5.0, 22, 40, _EPS_IBU, 25, 20, lambda d: "u", lambda d: "o")
        self.assertTrue(k_ibu)
        self.assertEqual(pils["kritiske_avvik"], 2, "styrkeklynge (1) + kritisk IBU (1) = 2")
        self.assertLessEqual(pils["score"], _TAK_KRITISK)

    def test_c_styrkeklynge_pluss_kritisk_ibu_og_ebc(self):
        pils = self._pils(ibu=5.0, ebc=25.0)
        self.assertEqual(pils["kritiske_avvik"], 3, "styrkeklynge (1) + IBU (1) + EBC (1) = 3")
        self.assertLessEqual(pils["score"], _TAK_KRITISK)

    def test_signaturbonus_kan_ikke_lofte_forbi_tak_kritisk_med_ebc(self):
        # Uten signatur ville raw+bonus (66+20=86) overskredet _TAK_KRITISK
        # (80) -- bekrefter at taket fortsatt faktisk engasjerer seg for den
        # NYE, grupperte kritiske_avvik-telleren, ikke bare i teorien. Merk:
        # FG/ABV nullstilles eksplisitt til stilens midtpunkt her -- dette
        # scenarioet skal isolere "styrkeklynge fra KUN OG" + kritisk EBC,
        # ikke arve klassens _STYRKE-basisverdier (som også setter FG/ABV).
        pils_uten = self._pils(og=1.055, fg=1.0105, abv=4.8, ebc=11.0, yeast="safale_us_05")
        pils_med = self._pils(og=1.055, fg=1.0105, abv=4.8, ebc=11.0, yeast="saflager_w3470")
        self.assertEqual(pils_uten["kritiske_avvik"], 2)
        self.assertEqual(pils_med["kritiske_avvik"], 2)
        self.assertGreater(pils_med["signaturbonus"], 0)
        self.assertGreater(
            pils_uten["raw_score"] + pils_med["signaturbonus"], _TAK_KRITISK,
            "Testforutsetningen (bonus ville løftet forbi taket uten det) holder ikke lenger",
        )
        self.assertEqual(pils_med["score"], _TAK_KRITISK)

    def test_signaturbonus_kan_ikke_lofte_forbi_tak_kritisk_med_ibu(self):
        pils_uten = self._pils(og=1.055, fg=1.0105, abv=4.8, ibu=13.0, ebc=6.0, yeast="safale_us_05")
        pils_med = self._pils(og=1.055, fg=1.0105, abv=4.8, ibu=13.0, ebc=6.0, yeast="saflager_w3470")
        self.assertEqual(pils_uten["kritiske_avvik"], 2)
        self.assertEqual(pils_med["kritiske_avvik"], 2)
        self.assertGreater(
            pils_uten["raw_score"] + pils_med["signaturbonus"], _TAK_KRITISK,
            "Testforutsetningen (bonus ville løftet forbi taket uten det) holder ikke lenger",
        )
        self.assertEqual(pils_med["score"], _TAK_KRITISK)


class TestModellCEkstremStyrkeKnusesFortsatt(unittest.TestCase):
    """Steg F11K, krav 11: gjentar F11F sin syntetiske kontroll mot en
    ~5 %-stil (Tysk Pilsner). Modellen skal være MONOTONT strengere når
    styrkeavviket øker -- IKKE flate ut slik den forkastede "Modell D"
    gjorde (som ga en fast ~50 % straff uansett hvor ekstremt avviket var).
    FG/ABV er utledet med en fast, realistisk 75 % utgjæring, som
    style_engine.py-formlene selv ville produsert."""

    def _score_ved_og(self, og, attenuation=0.75):
        fg = 1 + (og - 1) * (1 - attenuation)
        abv = (og - fg) * 131.25
        oppskrift = _lag_oppskrift(
            og=og, fg=fg, ibu=31.0, ebc=6.0, abv=abv,
            flavor_profile={"Brød": 6.0, "Sitrus": 3.0, "Bitterhet": 6.0},
            yeast="safale_us_05",
        )
        resultat = analyser_stil_og_balanse(oppskrift)
        return _finn_stil(resultat, "Tysk Pilsner")["score"]

    def test_score_er_monotont_synkende_med_okende_styrkeavvik(self):
        scorer = [self._score_ved_og(og) for og in (1.051, 1.060, 1.075, 1.100)]
        for i in range(len(scorer) - 1):
            self.assertLessEqual(
                scorer[i + 1], scorer[i],
                f"Score økte ved høyere OG-avvik ({scorer}) -- modellen flater ikke lenger monotont",
            )
        # Kvalitative krav fra F11K-spesifikasjonen:
        self.assertGreater(scorer[0], 80, "OG 1.051 (marginalt avvik) straffet uforholdsmessig hardt")
        self.assertLess(scorer[1], scorer[0], "OG 1.060 skal gi en tydelig straff sammenlignet med 1.051")
        self.assertEqual(scorer[3], 0, "OG 1.100 (ekstremt avvik) skal knuses til praktisk talt 0")

    def test_ekstrem_styrke_flatlinjer_ikke_slik_modell_d_gjorde(self):
        # Modell D-feilen: en fast ~50 %-straff uansett avvikets størrelse.
        # Bekrefter eksplisitt at et MODERAT avvik (1.060) og et EKSTREMT
        # avvik (1.100) IKKE lander på samme (eller nær samme) score.
        moderat = self._score_ved_og(1.060)
        ekstrem = self._score_ved_og(1.100)
        self.assertNotAlmostEqual(moderat, ekstrem, delta=5)
        self.assertGreater(moderat - ekstrem, 20)


if __name__ == "__main__":
    unittest.main()
