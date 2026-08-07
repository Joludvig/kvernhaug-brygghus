"""
Regresjonstester for modules/style_engine.py mot fire FASTMONTERTE
oppskrift-fixtures (tests/fixtures/recipes/*.json), kjørt gjennom hele den
ekte pipelinen: master-databasene (data/master_malt.json, master_humle_v2.json,
master_gjaer_v2.json) -> modules.flavor_engine.generer_smakshjul (ekte
sensorikk, ikke hardkodet flavor_profile) -> modules.style_engine.
analyser_stil_og_balanse.

Bakgrunn (Kvernhaug-gjennomgang 2026-07-27): tests/test_style_engine.py
dekker den generelle modellen med syntetiske oppskrifter og én
Wiesn-Märzen-lignende fixture bygget fra ekte maltdata. Denne filen tester i
tillegg de fire NAVNGITTE, karakteristiske Kvernhaug-oppskriftene (Wiesn-
Märzen, Sommerglød, Varðeldr, Eldsvenn), slik at en fremtidig endring i selve
style_engine-logikken, maltdatabasen eller smakshjulet blir fanget opp mot
ekte bryggdata — ikke bare mot håndkonstruerte tall.

VIKTIG: dette er IKKE lenger de private, gitignorede filene i recipes/ —
recipes/ leses eller skrives ALDRI av denne filen. tests/fixtures/recipes/
inneholder committede, saniterte kopier med KUN feltene style_engine-
pipelinen faktisk trenger (name, stats, malts, hops, yeast) — ingen
bryggelogg, dato, batch-størrelse, notater eller annen privat/irrelevant
data. En tidligere versjon av denne filen leste fra recipes/ direkte og
hoppet over testene (SkipTest) når mappen manglet i en fersk sjekk-ut/CI;
det var akseptabelt som midlertidig diagnose, men ikke som permanent
regresjonsdekning — disse fire testsettene skal alltid kjøre og alltid
telle, i alle miljøer.

Assertions er bevisst relasjonelle/kategoriske der det er mulig (hvilken stil
vinner, om et avvik er kritisk, om scoren ligger over/under en fornuftig
terskel) fremfor å hardkode eksakte prosentpoeng — de underliggende tallene
kan endre seg marginalt ved fremtidige kalkulasjonsendringer.
"""
import json
import os
import unittest

from modules.flavor_engine import generer_smakshjul
from modules.style_engine import analyser_stil_og_balanse

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIXTURES_MAPPE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "recipes")


def _last_json(*deler):
    with open(os.path.join(_REPO_ROOT, *deler), encoding="utf-8") as f:
        return json.load(f)


def _last_fixture(filnavn):
    with open(os.path.join(_FIXTURES_MAPPE, filnavn), encoding="utf-8") as f:
        return json.load(f)


def _flatt(db):
    return {info.get("display_name", k): info for k, info in db.items() if info}


def _analyser_fixture_oppskrift(fixture_filnavn):
    """Kjører en fastmontert, sanitert oppskrift-fixture gjennom hele
    pipelinen, akkurat slik modules/recipe_context.py gjør det for en åpen
    oppskrift i appen. Leser KUN fra tests/fixtures/recipes/ — aldri fra den
    ekte, gitignorede recipes/-mappen."""
    malt_db = _last_json("data", "master_malt.json")
    humle_db = _last_json("data", "master_humle_v2.json")
    gjaer_db = _last_json("data", "master_gjaer_v2.json")
    flatt_malt, flatt_humle, flatt_gjaer = _flatt(malt_db), _flatt(humle_db), _flatt(gjaer_db)

    r = _last_fixture(fixture_filnavn)

    malt_calc = [
        {"navn": malt_db.get(m["id"], {}).get("display_name", m["id"]), "mengde": m["mengde"]}
        for m in r["malts"]
    ]
    humle_calc = [
        {"navn": humle_db.get(h["id"], {}).get("display_name", h["id"]), "gram": h["gram"], "tid": h["tid"]}
        for h in r["hops"]
    ]
    gjaer_navn = gjaer_db.get(r["yeast"], {}).get("display_name", r["yeast"])

    _, poeng = generer_smakshjul(
        malt_calc, flatt_malt, humle_calc, flatt_humle, r["stats"]["ibu"], gjaer_navn, flatt_gjaer
    )

    recipe_obj = {
        "stats": r["stats"], "flavor_profile": poeng,
        "malts": r["malts"], "hops": r["hops"], "yeast": r["yeast"],
    }
    return r, analyser_stil_og_balanse(recipe_obj)


def _finn_stil(resultat, navn):
    return next(s for s in resultat["stil_liste"] if s["stil"] == navn)


class TestWiesnMarzen1872(unittest.TestCase):
    """Den sterke, Munich/Vienna-dominerte, W-34/70-gjærede referanseoppskriften
    som selve Historisk Wiesn-Märzen-stilen ble laget for (se style_engine.py).
    Skal fortsatt lande som nærmeste stil for den faktisk lagrede
    oppskriften — ikke bare for den håndbygde fixturen i test_style_engine.py."""

    def test_lander_som_historisk_wiesn_marzen(self):
        _, resultat = _analyser_fixture_oppskrift("wiesn_marzen_1872.json")
        self.assertEqual(resultat["stil"], "Historisk Wiesn-Märzen")

        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        self.assertEqual(wiesn["kritiske_avvik"], 0)
        self.assertGreaterEqual(wiesn["score"], 90)

    def test_canonical_marzen_scorer_klart_lavere_enn_historisk(self):
        # Bekrefter at splittet mellom canonical Märzen og den sterkere
        # historiske varianten fortsatt holder for de EKTE tallene i
        # oppskriften (OG ~1.064, ABV ~6.9 %) — ikke bare i teorien.
        #
        # Steg F11K (Modell C): terskelen senket fra >= 2 til >= 1. OG og ABV
        # er her begge kritiske (samme underliggende "for sterk vørter"), men
        # grupperes nå til MAKS ett kritisk avvik i stedet for to separate
        # (se _kombiner_styrkeklynge i style_engine.py) — testens opprinnelige
        # ">= 2" var en konsekvens av den gamle, ukorrelerte tellingen.
        # Det faste "+15 poeng"-margin-kravet er også fjernet her, av samme
        # grunn som i test_style_engine.py::test_marzen_rangerer_klart_over_
        # pilsnerstilene: canonical Märzen sin score steg fra 69 % til 82 %
        # under Modell C (OG/ABV-avviket er korrelert og dempes nå delvis),
        # mens Wiesn sin 95 % er UPÅVIRKET (dens eneste mangel er et EBC-avvik
        # fra fixturens kjent utdaterte fargeverdi — se F11B/F11G — og EBC
        # inngår ikke i styrkeklyngen). Faktisk observert margin: 13 poeng.
        #
        # Steg F11K-R (pre-commit review): en ren `assertGreater` (>) uten
        # minimumsmargin beskytter ikke ordet "klart" i testnavnet. Terskelen
        # under (>= 8) er bevisst satt LAVERE enn det observerte minimumet
        # (13), med slingringsmonn, og er IKKE tunet til å treffe et eksakt
        # tall — den skal bare utelukke en nesten-lik/sammenfallende score.
        _MINSTE_MARGIN = 8
        _, resultat = _analyser_fixture_oppskrift("wiesn_marzen_1872.json")
        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        canonical = _finn_stil(resultat, "Märzen")
        self.assertGreaterEqual(canonical["kritiske_avvik"], 1)
        self.assertGreaterEqual(
            wiesn["score"] - canonical["score"], _MINSTE_MARGIN,
            f"Wiesn ({wiesn['score']}%) skal rangere KLART over canonical Märzen ({canonical['score']}%)",
        )


class TestSommerglod(unittest.TestCase):
    """Lys, lagergjæret sommeröl med et lite innslag røykmalt (EBC ~3.9 —
    altfor lyst til å regnes som Rauchbier). Skal lande som en lys
    lagerstil, IKKE som Klassisk Røykøl."""

    def test_lander_som_tysk_pilsner(self):
        _, resultat = _analyser_fixture_oppskrift("sommerglod.json")
        self.assertEqual(resultat["stil"], "Tysk Pilsner")

    def test_rauchbier_scorer_lavt_til_tross_for_royktoner(self):
        # Selv om oppskriften har litt røyksmak, er den altfor lys og
        # lavalkoholisk til å regnes som Rauchbier (EBC-vindu 24-44) —
        # sensorisk røyknote alene skal ikke kunne overstyre fargekravet.
        _, resultat = _analyser_fixture_oppskrift("sommerglod.json")
        rauchbier = _finn_stil(resultat, "Klassisk Røykøl (Rauchbier)")
        self.assertGreaterEqual(rauchbier["kritiske_avvik"], 1)
        self.assertLess(rauchbier["score"], 50)


class TestBelgiskWitbierNumeriskOverlappUtenSignatur(unittest.TestCase):
    """
    KJENT, PRE-EKSISTERENDE MODELLBEGRENSNING — ikke en regresjon fra denne
    omarbeidingen (samme utfall oppstod med den gamle, ikke-normaliserte
    scoreformelen, siden Witbier sitt vindu numerisk sett fullstendig
    overlapper Sommerglød sine tall, og ingen av avvikene i seg selv er
    "kritiske" nok til å utløse taket).

    Sommerglød (lagergjær, ingen korianderfrø/appelsinskall, ingen belgisk
    gjærsignatur) scorer likevel ~75 % på "Belgisk Witbier", fordi OG/FG/
    ABV/IBU/EBC tilfeldigvis alle havner innenfor Witbiers brede numeriske
    vindu — kun de to sensoriske smak_krav-feltene (Fruktighet, Krydder)
    trekker scoren ned, og disse teller aldri som "kritiske avvik" (det gjør
    kun OG/FG/IBU/EBC/ABV, jf. krav 3/5). Modellen mangler en
    signatur-basert MOTVEKT for Witbier (tilsvarende _LAGER_BOCK_PENALTY for
    english_ale mot lagerstiler) som kunne straffet fraværet av belgisk
    gjærsignatur eksplisitt.

    Denne testen er bevisst en TAK-vakt (ikke en "riktig oppførsel"-test):
    den sikrer at scoren ikke stiger YTTERLIGERE ved en fremtidig endring,
    og dokumenterer gapet slik at det ikke går ubemerket videre. Vurdert til
    IKKE å rettes i denne opprydningsrunden (ville krevd en ny
    signatur-mekanisme, ikke en konstant-justering) — se statusrapporten for
    anbefaling.
    """

    def test_witbier_score_overstiger_ikke_dagens_niva(self):
        _, resultat = _analyser_fixture_oppskrift("sommerglod.json")
        witbier = _finn_stil(resultat, "Belgisk Witbier")
        self.assertEqual(witbier["kritiske_avvik"], 0, "Testforutsetningen (ingen kritiske avvik) endret seg")
        self.assertLessEqual(
            witbier["score"], 85,
            "Belgisk Witbier-scoren på en ikke-belgisk oppskrift har økt utover dagens kjente nivå",
        )


class TestVardeldr(unittest.TestCase):
    """Sterk, mørk, røykpreget ale (OG ~1.088, ABV ~9.1 %, EBC ~45). Passer
    ikke komfortabelt inn i noen definert BJCP-kandidat og skal falle
    tilbake til «Kreativt Brygg» — det tiltenkte resultatet for oppskrifter
    utenfor bibliotekets kategorier, ikke en feil."""

    def test_lander_som_kreativt_brygg(self):
        _, resultat = _analyser_fixture_oppskrift("vardeldr.json")
        self.assertEqual(resultat["stil"], "Kreativt Brygg")

    def test_ingen_definert_stil_scorer_over_terskelen_for_navngitt_stil(self):
        _, resultat = _analyser_fixture_oppskrift("vardeldr.json")
        beste = max(s["raw_score"] for s in resultat["stil_liste"])
        self.assertLessEqual(beste, 40, "En stil scoret høyt nok til å vinne over Kreativt Brygg-fallbacken")

    def test_english_bitter_knuses_fortsatt_ikke_modell_d_feilen(self):
        # Steg F11K (Modell C): regresjonsvakt mot den SPESIFIKKE feilen som
        # diskvalifiserte den forkastede "Modell D" (gruppe-cap) i F11F — der
        # flatet et gruppetak straffen ut rundt 50 % uansett hvor ekstremt
        # avviket var, og ga Varðeldr et falskt høyt treff mot English
        # Bitter. Modell C demper kun det NEST og TREDJE største avviket —
        # det største teller alltid fullt og er ubegrenset, så en reell
        # ekstrem avstand (her: OG 1,088 mot et 1,030-1,039-vindu, mer enn
        # 5x vindusbredden) skal fortsatt knuse scoren til 0, ikke flate ut.
        _, resultat = _analyser_fixture_oppskrift("vardeldr.json")
        bitter = _finn_stil(resultat, "English Bitter")
        self.assertEqual(bitter["score"], 0)
        self.assertEqual(bitter["raw_score"], 0)
        self.assertNotEqual(resultat["stil"], "English Bitter")


class TestEldsvenn(unittest.TestCase):
    """Svært sterk (OG ~1.092), mørk, lavbitter (IBU ~9.9) ale med engelsk
    gjær og betydelig røyk-/mørkmaltinnslag. Både OG og FG ligger langt
    utenfor selv Robust Porter sitt vindu — en reell, flerdimensjonal miss,
    ikke en enkelt grensesak. Skal også falle til «Kreativt Brygg», og
    balanseanalysen skal korrekt lese den som maltdominert."""

    def test_lander_som_kreativt_brygg(self):
        _, resultat = _analyser_fixture_oppskrift("eldsvenn_v1.json")
        self.assertEqual(resultat["stil"], "Kreativt Brygg")

    def test_robust_porter_har_flere_kritiske_avvik(self):
        # Robust Porter er den tematisk nærmeste stilen (engelsk gjær +
        # mørk malt trigger normalt signaturboost), men OG/FG/ABV/IBU/EBC
        # er alle langt utenfor vinduet samtidig — bekrefter at det er
        # reelle talldata, ikke en tilfeldig cap, som styrer utfallet.
        _, resultat = _analyser_fixture_oppskrift("eldsvenn_v1.json")
        porter = _finn_stil(resultat, "Robust Porter")
        self.assertGreaterEqual(porter["kritiske_avvik"], 2)

    def test_lav_bitterhet_gir_maltdominert_balansenotat(self):
        _, resultat = _analyser_fixture_oppskrift("eldsvenn_v1.json")
        self.assertLess(resultat["bu_gu"], 0.38)
        self.assertTrue(any("Maltdominert" in n for n in resultat["balanse"]))


if __name__ == "__main__":
    unittest.main()
