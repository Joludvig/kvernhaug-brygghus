"""
Regresjonstester for modules/style_engine.py mot de FIRE ekte, lagrede
Kvernhaug-oppskriftene (recipes/*.json), kjørt gjennom hele den ekte
pipelinen: master-databasene (data/master_malt.json, master_humle_v2.json,
master_gjaer_v2.json) -> modules.flavor_engine.generer_smakshjul (ekte
sensorikk, ikke hardkodet flavor_profile) -> modules.style_engine.
analyser_stil_og_balanse.

Bakgrunn (Kvernhaug-gjennomgang 2026-07-27): tests/test_style_engine.py
dekker den generelle modellen med syntetiske oppskrifter og én
Wiesn-Märzen-lignende fixture bygget fra ekte maltdata. Denne filen tester i
tillegg de fire NAVNGITTE, faktisk lagrede oppskriftene direkte fra disk, slik
at en fremtidig endring i selve style_engine-logikken, maltdatabasen eller
smakshjulet blir fanget opp mot ekte bryggdata — ikke bare mot håndkonstruerte
tall.

VIKTIG: recipes/ ER gitignoret — brukerens private, lagrede oppskrifter
finnes IKKE i en fersk `git clone`/`git worktree`. Hver test her sjekker om
sin respektive recipes/-fil faktisk finnes, og hopper over (unittest.SkipTest)
med en tydelig begrunnelse hvis den mangler, i stedet for å feile. Dette
holder testfilen nyttig lokalt (mot ekte data når de finnes) uten å bryte en
fersk sjekk-ut/CI, som verken har eller skal ha disse private filene.
Filene leses uansett read-only, aldri skrevet til.

Assertions er bevisst relasjonelle/kategoriske der det er mulig (hvilken stil
vinner, om et avvik er kritisk, om scoren ligger over/under en fornuftig
terskel) fremfor å hardkode eksakte prosentpoeng — reelle oppskrifters
beregnede stats kan endre seg marginalt ved fremtidige kalkulasjonsendringer.
"""
import json
import os
import unittest

from modules.flavor_engine import generer_smakshjul
from modules.style_engine import analyser_stil_og_balanse

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _last_json(*deler):
    with open(os.path.join(_REPO_ROOT, *deler), encoding="utf-8") as f:
        return json.load(f)


def _flatt(db):
    return {info.get("display_name", k): info for k, info in db.items() if info}


def _analyser_ekte_oppskrift(recipe_filnavn):
    """Kjører en lagret oppskrift gjennom hele pipelinen, akkurat slik
    modules/recipe_context.py gjør det for en åpen oppskrift i appen.
    Hopper over testen (ikke feil) hvis den private recipes/-filen ikke
    finnes i dette miljøet — se modulens docstring."""
    oppskrift_sti = os.path.join(_REPO_ROOT, "recipes", recipe_filnavn)
    if not os.path.exists(oppskrift_sti):
        raise unittest.SkipTest(
            f"recipes/{recipe_filnavn} finnes ikke i dette miljøet (recipes/ er gitignoret, "
            "privat brukerdata) — testen kan ikke kjøre uten den lokale filen."
        )

    malt_db = _last_json("data", "master_malt.json")
    humle_db = _last_json("data", "master_humle_v2.json")
    gjaer_db = _last_json("data", "master_gjaer_v2.json")
    flatt_malt, flatt_humle, flatt_gjaer = _flatt(malt_db), _flatt(humle_db), _flatt(gjaer_db)

    r = _last_json("recipes", recipe_filnavn)

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
        _, resultat = _analyser_ekte_oppskrift("kvernhaug_wiesn-märzen_1872.json")
        self.assertEqual(resultat["stil"], "Historisk Wiesn-Märzen")

        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        self.assertEqual(wiesn["kritiske_avvik"], 0)
        self.assertGreaterEqual(wiesn["score"], 90)

    def test_canonical_marzen_scorer_klart_lavere_enn_historisk(self):
        # Bekrefter at splittet mellom canonical Märzen og den sterkere
        # historiske varianten fortsatt holder for de EKTE tallene i
        # oppskriften (OG ~1.064, ABV ~6.9 %) — ikke bare i teorien.
        _, resultat = _analyser_ekte_oppskrift("kvernhaug_wiesn-märzen_1872.json")
        wiesn = _finn_stil(resultat, "Historisk Wiesn-Märzen")
        canonical = _finn_stil(resultat, "Märzen")
        self.assertGreaterEqual(canonical["kritiske_avvik"], 2)
        self.assertGreater(wiesn["score"], canonical["score"] + 15)


class TestSommerglod(unittest.TestCase):
    """Lys, lagergjæret sommeröl med et lite innslag røykmalt (EBC ~3.9 —
    altfor lyst til å regnes som Rauchbier). Skal lande som en lys
    lagerstil, IKKE som Klassisk Røykøl."""

    def test_lander_som_tysk_pilsner(self):
        _, resultat = _analyser_ekte_oppskrift("kvernhaug_sommerglød.json")
        self.assertEqual(resultat["stil"], "Tysk Pilsner")

    def test_rauchbier_scorer_lavt_til_tross_for_royktoner(self):
        # Selv om oppskriften har litt røyksmak, er den altfor lys og
        # lavalkoholisk til å regnes som Rauchbier (EBC-vindu 24-44) —
        # sensorisk røyknote alene skal ikke kunne overstyre fargekravet.
        _, resultat = _analyser_ekte_oppskrift("kvernhaug_sommerglød.json")
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
        _, resultat = _analyser_ekte_oppskrift("kvernhaug_sommerglød.json")
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
        _, resultat = _analyser_ekte_oppskrift("varðeldr.json")
        self.assertEqual(resultat["stil"], "Kreativt Brygg")

    def test_ingen_definert_stil_scorer_over_terskelen_for_navngitt_stil(self):
        _, resultat = _analyser_ekte_oppskrift("varðeldr.json")
        beste = max(s["raw_score"] for s in resultat["stil_liste"])
        self.assertLessEqual(beste, 40, "En stil scoret høyt nok til å vinne over Kreativt Brygg-fallbacken")


class TestEldsvenn(unittest.TestCase):
    """Svært sterk (OG ~1.092), mørk, lavbitter (IBU ~9.9) ale med engelsk
    gjær og betydelig røyk-/mørkmaltinnslag. Både OG og FG ligger langt
    utenfor selv Robust Porter sitt vindu — en reell, flerdimensjonal miss,
    ikke en enkelt grensesak. Skal også falle til «Kreativt Brygg», og
    balanseanalysen skal korrekt lese den som maltdominert."""

    def test_lander_som_kreativt_brygg(self):
        _, resultat = _analyser_ekte_oppskrift("eldsvenn_v1.json")
        self.assertEqual(resultat["stil"], "Kreativt Brygg")

    def test_robust_porter_har_flere_kritiske_avvik(self):
        # Robust Porter er den tematisk nærmeste stilen (engelsk gjær +
        # mørk malt trigger normalt signaturboost), men OG/FG/ABV/IBU/EBC
        # er alle langt utenfor vinduet samtidig — bekrefter at det er
        # reelle talldata, ikke en tilfeldig cap, som styrer utfallet.
        _, resultat = _analyser_ekte_oppskrift("eldsvenn_v1.json")
        porter = _finn_stil(resultat, "Robust Porter")
        self.assertGreaterEqual(porter["kritiske_avvik"], 2)

    def test_lav_bitterhet_gir_maltdominert_balansenotat(self):
        _, resultat = _analyser_ekte_oppskrift("eldsvenn_v1.json")
        self.assertLess(resultat["bu_gu"], 0.38)
        self.assertTrue(any("Maltdominert" in n for n in resultat["balanse"]))


if __name__ == "__main__":
    unittest.main()
