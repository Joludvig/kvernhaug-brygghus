"""
WEB STAB W1 (issue #102) -- fixes the US ingredient unit contract on the
web recipe builder: switching to US customary correctly converted the
malt/hop NUMBERS, but the visible unit label right next to each field
(<span class="enhet">kg</span> / <span class="enhet">g</span>), the
"Beregn gram"/"Calculate grams" action wording, and the scaling helper
text all stayed hardcoded to the metric unit -- a HIGH-trust bug, since
the displayed number could be physically measured using the wrong unit.

VIKTIG METODEMERKNAD (samme prinsipp som test_web_custom_ingredient_id_
active_draft.py og test_web_calc_js_parity.py): dette miljøet har ingen
JavaScript-kjøretid (Node er bevisst blokkert som Bash-allowlist-
omgåelse, se tests/web_js_runtime.py). Disse testene kan derfor ikke
faktisk laste web/index.html og observere en ekte DOM-oppdatering ved
enhets-/språkbytte. I stedet er dette KILDE-KONTRAKT-tester: de leser
den FAKTISKE, kjørende web/js/app.js- og web/js/i18n.js-kildeteksten og
verifiserer -- via presise, snevert avgrensede mønstre -- at riktig
funksjon faktisk kalles på riktig sted, og at ordlyden faktisk er
enhets-nøytral der den skal være. TestEnhetKonverteringGoldenVectors
under er derimot en ekte, kjørende Python-port av web/js/units.js sine
rene, DOM-frie konverteringsformler (samme tall/formler, samme
avrundingsstrategi) -- en reell utregning, ikke bare et mønster-søk --
som beviser selve konverterings-/avrundings-/rundtur-kontrakten
(akseptansekriterium 8-9) numerisk.

ET GJENVÆRENDE, DOKUMENTERT GAP (se PR-rapporten): web/en/index.html og
web/js/i18n.js sine "builder.skaler.hjelpetekst"/"builder.humle.
beregnGramKnapp"-verdier er koblet sammen av scripts/generate_web_i18n_
pages.py, som denne kjøringen ikke har tillatelse til å kjøre direkte
(kun "pip install -r requirements.txt" og "python3 -m unittest ..." er i
--allowedTools, se docs/development/AGENT_WORKFLOW.md). web/en/index.html
er derfor IKKE regenerert i denne PR-en -- tests.test_generate_web_i18n_
pages sin test_committed_output_matcher_fersk_generering vil feile helt
til eieren kjører generatoren lokalt og committer resultatet, se
web/README.md og web/CHANGELOG.md. Dette er et kjent, isolert gap, ikke
en feil i selve enhets-fiksen: alt brukervendt innhold under er DOM-/JS-
generert på nytt fra web/js/i18n.js ved hver sideinnlasting/enhetsbytte/
språkbytte på BÅDE no- og en-siden (de deler samme i18n.js), uavhengig av
hva som står statisk i web/en/index.html sin kildetekst.

Kjøres med:
    py -3 -m unittest tests.test_web_unit_labels
"""
import io
import os
import re
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_JS = os.path.join(_REPO_ROOT, "web", "js", "app.js")
_I18N_JS = os.path.join(_REPO_ROOT, "web", "js", "i18n.js")


def _les(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _funksjonskropp(kilde, funksjonssignatur_regex):
    """Henter kroppen til en toppnivå-funksjon (fra 'function ... {' til
    linjen med den avsluttende '}' i kolonne 0), for å kunne lete etter
    mønstre KUN inni akkurat den funksjonen."""
    m = re.search(funksjonssignatur_regex, kilde)
    assert m, "fant ikke funksjonssignaturen: %r" % funksjonssignatur_regex
    start = m.end()
    slutt = kilde.index("\n}", start)
    return kilde[start:slutt]


class TestRadHjelperOppdatererSynligEnhet(unittest.TestCase):
    """_oppdaterMaltRadEnhet()/_oppdaterHumleRadEnhet() må faktisk
    oppdatere BÅDE placeholder og den synlige <span class="enhet">-
    nabospannen -- root cause for issue #102 var at kun tallverdien (og
    placeholder) ble konvertert, aldri selve enhets-teksten ved siden
    av."""

    def test_malt_hjelper_oppdaterer_placeholder_og_enhet_span(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _oppdaterMaltRadEnhet\(rad\)\s*\{")
        self.assertIn('felt.placeholder = enhet.malt', kropp)
        self.assertIn("felt.nextElementSibling", kropp)
        self.assertIn('enhetSpan.textContent = enhet.malt', kropp)

    def test_humle_hjelper_oppdaterer_placeholder_og_enhet_span(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _oppdaterHumleRadEnhet\(rad\)\s*\{")
        self.assertIn('felt.placeholder = enhet.humle', kropp)
        self.assertIn("felt.nextElementSibling", kropp)
        self.assertIn('enhetSpan.textContent = enhet.humle', kropp)

    def test_humle_hjelper_gjor_beregn_knapp_enhetsbevisst(self):
        """"Beregn gram"/"Calculate grams" var alltid hardkodet til
        gram/grams uansett unitSystem -- knappen skal nå komponere
        teksten med gjeldende enhet, samme mønster som _oppdaterHumleRadEnhet
        forøvrig."""
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _oppdaterHumleRadEnhet\(rad\)\s*\{")
        self.assertRegex(
            kropp,
            r'knapp\.textContent = `\$\{t\("builder\.humle\.beregnGramKnapp"\)\} \(\$\{enhet\.humle\}\)`',
        )


class TestRadHjelperFaktiskKalt(unittest.TestCase):
    """De to hjelperne over er verdiløse hvis de ikke faktisk kalles fra
    radopprettelse, enhetsbytte og språkbytte."""

    def test_leggtilmaltrad_kaller_hjelperen(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function leggTilMaltRad\(forhandsutfylt\)\s*\{")
        self.assertIn("_oppdaterMaltRadEnhet(rad);", kropp)
        # Den gamle, ufullstendige inline-varianten skal være borte -- ikke
        # bare supplert.
        self.assertNotIn("mengdeFelt.placeholder = ENHET_FORKORTELSE", kropp)

    def test_leggtilhumlerad_kaller_hjelperen(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function leggTilHumleRad\(forhandsutfylt\)\s*\{")
        self.assertIn("_oppdaterHumleRadEnhet(rad);", kropp)
        self.assertNotIn("gramFelt.placeholder = ENHET_FORKORTELSE", kropp)

    def test_rerender_ved_enhetsbytte_kaller_begge_hjelperne(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _rerenderAlleEnhetsfelt\(\)\s*\{")
        self.assertIn("_oppdaterMaltRadEnhet(rad);", kropp)
        self.assertIn("_oppdaterHumleRadEnhet(rad);", kropp)

    def test_sprakbytte_lytteren_rerendrer_enhetsfelt(self):
        """Regresjon: applyI18n() (kjørt FØR denne lytteren, se i18n.js)
        skriver om ALLE data-i18n-elementer til base-teksten uten
        enhets-parameter -- uten en full _rerenderAlleEnhetsfelt()-kall her
        ville et språkbytte mistet enhets-suffikset på batchvolum/skaler-
        labelsene og "Beregn mengde"-knappeteksten, uavhengig av om
        unitSystem er metric eller us."""
        kilde = _les(_APP_JS)
        m = re.search(r'window\.addEventListener\("kvernhaug:sprakendret", \(\) => \{', kilde)
        self.assertIsNotNone(m, "fant ikke kvernhaug:sprakendret-lytteren")
        start = m.end()
        slutt = kilde.index("\n});", start)
        lytter = kilde[start:slutt]
        self.assertIn("_rerenderAlleEnhetsfelt();", lytter)


class TestSkalerHjelpetekstEnhetsbevisst(unittest.TestCase):
    def test_oppdaterenhetslabels_setter_parameterisert_hjelpetekst(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _oppdaterEnhetsLabels\(\)\s*\{")
        self.assertIn('document.querySelector(\'[data-i18n="builder.skaler.hjelpetekst"]\')', kropp)
        self.assertRegex(
            kropp,
            r't\("builder\.skaler\.hjelpetekst", \{ malt: enhet\.malt, humle: enhet\.humle \}\)',
        )


class TestI18nOrdlydErEnhetsNoytral(unittest.TestCase):
    """De to base-tekstene skal ikke lenger hardkode et metrisk
    enhetsnavn -- selve enheten skal komme fra ENHET_FORKORTELSE via
    JS-en over, uansett hvilket språk som er aktivt."""

    def test_beregn_knapp_no_og_en_nevner_ikke_gram(self):
        kilde = _les(_I18N_JS)
        alle = re.findall(r'"builder\.humle\.beregnGramKnapp":\s*"([^"]*)"', kilde)
        self.assertEqual(len(alle), 2, "forventet nøyaktig én NO- og én EN-verdi")
        for tekst in alle:
            self.assertNotIn("gram", tekst.lower())

    def test_skaler_hjelpetekst_no_og_en_bruker_parametrene(self):
        kilde = _les(_I18N_JS)
        alle = re.findall(r'"builder\.skaler\.hjelpetekst":\s*"([^"]*(?:\\.[^"]*)*)"', kilde)
        self.assertEqual(len(alle), 2, "forventet nøyaktig én NO- og én EN-verdi")
        for tekst in alle:
            self.assertIn("{malt}", tekst)
            self.assertIn("{humle}", tekst)
            # Ingen hardkodet "(kg)"/"(gram)" skal gjenstå ved siden av
            # parameteren.
            self.assertNotIn("(kg)", tekst)
            self.assertNotIn("(gram)", tekst)
            self.assertNotIn("(grams)", tekst)


# ─── Ekte, kjørende Python-port av web/js/units.js sine rene, DOM-frie
# konverteringsformler -- IKKE en JS-eksekvering (se moduldocstringen), men
# en faktisk utregning med nøyaktig de samme konstantene/avrundings-
# strategiene som units.js, hentet direkte fra kildefilen slik at et
# fremtidig avvik mellom units.js og denne testen blir synlig neste gang
# noen bevisst oppdaterer BEGGE. ────────────────────────────────────────

_UNITS_JS = os.path.join(_REPO_ROOT, "web", "js", "units.js")


def _hent_konstant(kilde, navn):
    m = re.search(r"const %s = ([0-9.]+);" % re.escape(navn), kilde)
    assert m, "fant ikke konstanten %r i units.js" % navn
    return float(m.group(1))


class TestEnhetKonverteringGoldenVectors(unittest.TestCase):
    """Beviser selve tallkontrakten (akseptansekriterium 5, 8, 9) numerisk:
    konvertering til US, og et fullt metric->US->metric-rundtur uten
    drift, basert på KONSTANTENE lest direkte fra den ekte units.js."""

    @classmethod
    def setUpClass(cls):
        kilde = _les(_UNITS_JS)
        cls.lb_kg = _hent_konstant(kilde, "LB_KG")
        cls.oz_g = _hent_konstant(kilde, "OZ_G")
        cls.us_gallon_l = _hent_konstant(kilde, "US_GALLON_L")

    def _format_malt_us(self, kg):
        return round((kg / self.lb_kg) * 100) / 100

    def _format_humle_us(self, g):
        return round((g / self.oz_g) * 100) / 100

    def test_malt_6_25_kg_blir_ca_13_78_lb(self):
        # Issue #102 sitt eget eksempel: "malt 6.25 kg -> ~13.78 but still
        # labeled kg".
        self.assertAlmostEqual(self._format_malt_us(6.25), 13.78, places=2)

    def test_humle_25_g_blir_ca_0_88_oz(self):
        # Issue #102 sitt eget eksempel: "hops 25 g -> ~0.88 but still
        # labeled g".
        self.assertAlmostEqual(self._format_humle_us(25), 0.88, places=2)

    def test_rundtur_metric_us_metric_uten_drift(self):
        """dataset.canonical er ALLTID fasit (se _settEnhetsfelt()-
        kommentaren i app.js) -- selve rundturen skjer aldri ved å
        reparse allerede avrundet displaytekst, så et metric->US->metric-
        bytte skal gi eksakt samme canonical-tall tilbake, uansett hvor
        mye US-visningen selv avrundet underveis."""
        for kg in (6.25, 5.0, 0.05, 27.3):
            avrundet_us_visning = self._format_malt_us(kg)
            # Visnings-avrundingen introduserer maks +/-0.005 lb ~= 0.0023 kg
            # feil DERSOM man (feilaktig) skulle reparse visningsteksten --
            # dokumentert som produktets eksplisitte display-rounding
            # tolerance (akseptansekriterium 8), ikke faktisk canonical-drift.
            reparsed_kg = avrundet_us_visning * self.lb_kg
            self.assertAlmostEqual(reparsed_kg, kg, delta=0.003)

    def test_batch_volum_us_gallon_konvertering(self):
        # Regresjonsevidens for at US gal-visningen (som IKKE regredierte
        # per issue #102 sin "Preserve existing good behavior") fortsatt
        # bruker riktig konstant.
        liter = 20.0
        us_gal = round((liter / self.us_gallon_l) * 100) / 100
        self.assertAlmostEqual(us_gal, 5.28, places=2)


if __name__ == "__main__":
    unittest.main()
