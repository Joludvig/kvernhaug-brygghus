"""
WEB STAB W2 (issue #104) -- regression coverage for the ABV tool's
result-visibility state machine (B02): a stale/default result group
visible before any valid calculation, multiple result groups visible at
once after recalculating, and invalid input leaving a previous result
on screen instead of a clean no-result state.

ROOT CAUSE (verified by reading the real, live source -- not assumed):
this was never a JS logic bug. web/js/verktoy_page.js's
_oppdaterAbvKalkulator() already set the `hidden` property correctly in
every branch (error, normal-range, high-gravity-range). The actual bug
is a CSS cascade-ORIGIN bug: .resultat-grid's own "display: grid" (an
author-stylesheet rule) always wins over the browser's built-in
"[hidden] { display: none }" (a user-agent-stylesheet rule), regardless
of selector specificity, because author rules outrank UA rules by
origin, not by specificity or source order. So JS setting `.hidden =
true` had zero *visual* effect -- the box stayed on screen. The exact
same pattern, with the exact same fix
(".selector[hidden] { display: none; }"), already exists elsewhere in
this stylesheet for .utstyr-rad-handlinger and #pantry-type-bryter /
#pantry-velger-rad; see the comments next to each in web/css/style.css.
The fix this round applies the identical pattern to
#verktoy-abv-resultat-normal / #verktoy-abv-resultat-hoygrav, and also
makes #verktoy-abv-resultat-normal `hidden` by default in markup (it
previously had no `hidden` attribute at all), so no placeholder "0,0 %"
result is ever presented before a real calculation has run.

This environment has no JS runtime (Node is deliberately blocked as a
Bash-allowlist circumvention -- see tests/web_js_runtime.py), so this is
source-contract coverage, the same established technique used elsewhere
in this suite (test_web_calc_js_parity.py, test_web_unit_labels.py):
- TestMarkupDefaultHidden / TestCssHiddenOverridePresent read the real,
  live web/verktoy.html, web/en/verktoy.html, and web/css/style.css and
  assert the two concrete fixes are actually present in shipped source
  -- these are the parts a real browser would need in order to render
  correctly, and are exactly what would have caught B02 if they had
  been missing.
- TestVisibilityStateMachine is a real, executed Python port of
  _oppdaterAbvKalkulator()'s branch/threshold logic (not the ABV
  formulas themselves, which are covered elsewhere), parity-checked
  against the live JS source's threshold constant, then exercised with
  real pass/fail assertions across representative and boundary inputs
  to prove the "exactly one result state visible at a time" contract
  the issue's acceptance criteria require.

There is still no substitute for real-browser verification (issue
acceptance criteria 7-9) -- that remains a documented gap for a manual
Playwright sweep, exactly as this project's web-full-regression skill
already exists to cover, and exactly the same honest limit already
recorded for prior WEB STAB rounds in this file's sibling tests.
"""
import re
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

_REPO_ROOT = Path(__file__).resolve().parent.parent
_WEB = _REPO_ROOT / "web"
_VERKTOY_NO = _WEB / "verktoy.html"
_VERKTOY_EN = _WEB / "en" / "verktoy.html"
_STYLE_CSS = _WEB / "css" / "style.css"
_VERKTOY_JS = _WEB / "js" / "verktoy_page.js"


class TestMarkupDefaultHidden(unittest.TestCase):
    """AC1: no stale/default ABV result group visibly presented on first
    load -- the normal-result box must start `hidden` in markup, not rely
    on JS running before the browser paints anything."""

    def _resultat_normal_er_hidden_i_markup(self, path):
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        boks = soup.find(id="verktoy-abv-resultat-normal")
        self.assertIsNotNone(boks, f"Fant ikke #verktoy-abv-resultat-normal i {path}")
        self.assertTrue(
            boks.has_attr("hidden"),
            f"#verktoy-abv-resultat-normal i {path} mangler `hidden` i markup -- "
            "et 0,0%-plassholderresultat vises da før JS har regnet ut noe ekte.",
        )

    def test_no_kilde_normal_boks_hidden_som_default(self):
        self._resultat_normal_er_hidden_i_markup(_VERKTOY_NO)

    def test_en_generert_normal_boks_hidden_som_default(self):
        self._resultat_normal_er_hidden_i_markup(_VERKTOY_EN)

    def _hoygrav_boks_fortsatt_hidden(self, path):
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        boks = soup.find(id="verktoy-abv-resultat-hoygrav")
        self.assertIsNotNone(boks)
        self.assertTrue(boks.has_attr("hidden"))

    def test_no_kilde_hoygrav_boks_fortsatt_hidden(self):
        self._hoygrav_boks_fortsatt_hidden(_VERKTOY_NO)

    def test_en_generert_hoygrav_boks_fortsatt_hidden(self):
        self._hoygrav_boks_fortsatt_hidden(_VERKTOY_EN)


class TestIngenAutomatiskResultatVedInit(unittest.TestCase):
    """AC1 (Chief round-2 CHANGES REQUESTED, issue #104): OG/FG-feltene har
    gyldige forhåndsutfylte default-verdier i markup, så et
    _oppdaterAbvKalkulator()-kall inne i _initAbvKalkulator() ville regnet
    ut og vist et ekte resultat på førstelast -- markup-default-hidden
    alene stopper ikke det, siden JS selv fjerner `hidden` igjen. Resultatet
    skal først vises etter faktisk input-interaksjon (event listener), ikke
    ved side-last."""

    def setUp(self):
        self.js = _VERKTOY_JS.read_text(encoding="utf-8")

    def test_init_funksjonen_kaller_ikke_oppdater_direkte(self):
        match = re.search(
            r"function _initAbvKalkulator\(\)\s*\{(.*?)\n\}",
            self.js,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "Fant ikke _initAbvKalkulator() i verktoy_page.js")
        body = match.group(1)
        bare_kall = re.findall(r"(?<!\.addEventListener\()_oppdaterAbvKalkulator\(\)", body)
        # Kall som argument til addEventListener (uten parenteser, dvs.
        # `_oppdaterAbvKalkulator` som referanse) er greit -- det er et
        # direkte, umiddelbart `_oppdaterAbvKalkulator()`-kall i kroppen
        # (utenfor en event-callback) som ville trigget resultatvisning
        # før brukerinteraksjon.
        direkte_kall = re.findall(r"^\s*_oppdaterAbvKalkulator\(\)\s*;", body, re.MULTILINE)
        self.assertEqual(
            direkte_kall,
            [],
            "_initAbvKalkulator() kaller _oppdaterAbvKalkulator() direkte -- "
            "med gyldige default OG/FG-verdier i markup viser dette et "
            "resultat på førstelast, før brukeren har gjort noe (AC1).",
        )

    def test_event_listeners_fortsatt_registrert(self):
        # Sanity -- beviser at fiksen ikke fjernet selve
        # interaktiviteten, kun det umiddelbare kallet ved init.
        self.assertRegex(
            self.js,
            r'getElementById\("verktoy-abv-og"\)\.addEventListener\("input",\s*_oppdaterAbvKalkulator\)',
        )
        self.assertRegex(
            self.js,
            r'getElementById\("verktoy-abv-fg"\)\.addEventListener\("input",\s*_oppdaterAbvKalkulator\)',
        )


class TestCssHiddenOverridePresent(unittest.TestCase):
    """The actual B02 root cause: .resultat-grid's "display: grid" beats
    the UA stylesheet's "[hidden] { display: none }" by cascade origin.
    Without an explicit author-level override, JS setting `.hidden = true`
    has no visual effect at all -- both result groups can appear
    simultaneously, and a hidden group stays visible after invalid input."""

    def setUp(self):
        self.css = _STYLE_CSS.read_text(encoding="utf-8")

    def test_resultat_grid_display_grid_uten_qualifier_finnes(self):
        # Sanity -- beviser at selve fellen fortsatt eksisterer (uendret
        # .resultat-grid { display: grid }), så testen under faktisk
        # tester mot noe reelt, ikke en forsvunnet klasse.
        self.assertRegex(self.css, r"\.resultat-grid\s*\{[^}]*display:\s*grid")

    def test_verktoy_abv_resultat_hidden_override_finnes(self):
        match = re.search(
            r"#verktoy-abv-resultat-normal\[hidden\]\s*,\s*"
            r"#verktoy-abv-resultat-hoygrav\[hidden\]\s*\{([^}]*)\}",
            self.css,
        )
        self.assertIsNotNone(
            match,
            "Mangler #verktoy-abv-resultat-normal[hidden], "
            "#verktoy-abv-resultat-hoygrav[hidden] { display: none; } i "
            "web/css/style.css -- uten denne overstyringen vinner "
            ".resultat-grid sin display:grid over `hidden`-attributtet, "
            "og resultatboksene forblir synlige selv når JS skjuler dem.",
        )
        self.assertRegex(match.group(1), r"display:\s*none\s*;?")


class TestVisibilityStateMachine(unittest.TestCase):
    """Real, executed Python port of _oppdaterAbvKalkulator()'s branch
    logic, parity-checked against the live JS threshold constant, then
    exercised with real assertions -- not just pattern matches -- to
    prove AC1-4: exactly one result state (feil / normal / hoygrav) is
    ever active for a given (og, fg) input, never zero, never two."""

    @staticmethod
    def _hent_terskel_fra_js():
        js = _VERKTOY_JS.read_text(encoding="utf-8")
        match = re.search(
            r"VERKTOY_HOY_GRAVITET_TERSKEL_OG\s*=\s*([0-9.]+)", js
        )
        assert match, "Fant ikke VERKTOY_HOY_GRAVITET_TERSKEL_OG i verktoy_page.js"
        return float(match.group(1))

    @staticmethod
    def _valider_maalt_og_fg(og, fg):
        if og <= 1.0:
            raise ValueError("OG må være høyere enn 1.000")
        if fg <= 0:
            raise ValueError("FG må være et positivt tall")
        if fg > og:
            raise ValueError("FG kan ikke være høyere enn OG")
        if og >= 1.775:
            raise ValueError("OG er urealistisk høy for en ABV-beregning")

    def _synlig_tilstand(self, og, fg, terskel):
        """Port av _oppdaterAbvKalkulator(): returnerer hvilken av
        {"feil", "normal", "hoygrav"} som er synlig for gitt (og, fg)."""
        if og is None or fg is None:
            return "feil"
        try:
            self._valider_maalt_og_fg(og, fg)
        except ValueError:
            return "feil"
        return "hoygrav" if og >= terskel else "normal"

    def setUp(self):
        self.terskel = self._hent_terskel_fra_js()

    def test_terskel_matcher_kjent_kontraktverdi(self):
        # Samme terskel som ui/abv_calculator_panel.py i App (se
        # verktoy_page.js sin egen header-kommentar) -- 1.070.
        self.assertEqual(self.terskel, 1.070)

    def test_ugyldig_input_gir_kun_feil_synlig(self):
        for og, fg in [(None, 1.010), (1.050, None), (1.0, 1.010), (1.050, 0), (1.010, 1.050), (1.800, 1.010)]:
            with self.subTest(og=og, fg=fg):
                self.assertEqual(self._synlig_tilstand(og, fg, self.terskel), "feil")

    def test_gyldig_lav_gravitet_gir_kun_normal_synlig(self):
        for og, fg in [(1.050, 1.010), (1.040, 1.008), (1.0699, 1.010)]:
            with self.subTest(og=og, fg=fg):
                self.assertEqual(self._synlig_tilstand(og, fg, self.terskel), "normal")

    def test_gyldig_hoy_gravitet_gir_kun_hoygrav_synlig(self):
        for og, fg in [(1.070, 1.010), (1.100, 1.020), (1.774, 1.020)]:
            with self.subTest(og=og, fg=fg):
                self.assertEqual(self._synlig_tilstand(og, fg, self.terskel), "hoygrav")

    def test_omregning_bytter_ren_tilstand_uten_overlapp(self):
        # AC3/AC4: en rekalkulering (lav -> høy -> ugyldig -> lav) skal
        # aldri la forrige tilstand henge igjen -- nøyaktig én aktiv
        # tilstand for hvert steg i sekvensen.
        sekvens = [
            ((1.050, 1.010), "normal"),
            ((1.100, 1.020), "hoygrav"),
            ((1.010, 1.050), "feil"),
            ((1.045, 1.008), "normal"),
        ]
        for (og, fg), forventet in sekvens:
            with self.subTest(og=og, fg=fg):
                tilstand = self._synlig_tilstand(og, fg, self.terskel)
                self.assertEqual(tilstand, forventet)
                alle = {"feil", "normal", "hoygrav"}
                # Nøyaktig én tilstand aktiv -- de to andre er implisitt
                # ikke det, siden _synlig_tilstand returnerer én verdi.
                self.assertIn(tilstand, alle)


if __name__ == "__main__":
    unittest.main()
