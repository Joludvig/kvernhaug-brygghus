"""
Tester for issue #59: Kvernhaug Design System — design/tokens.json,
modules/design_tokens.py og docs/DESIGN.md.

Dekker:
- Skjemavalidering av design/tokens.json (via modules.design_tokens.
  validate_tokens) mot syntetiske, bevisst ødelagte kopier -- ikke bare
  at den ekte filen tilfeldigvis er gyldig.
- Token-drift-vakt: de seks aksentfargene (gull/pergament/mose/kobber/
  elfenbein/danger) skal være byte-identiske på tvers av design/tokens.json,
  ui/branding.py (via faktisk import, ikke kildetekst-regex) og de to
  fortsatt uavhengige, håndvedlikeholdte kopiene i
  modules/card_template.py og web/css/style.css sin :root-blokk.
  En fremtidig endring av én av disse fire uten å oppdatere de andre skal
  feile denne testen -- det er selve poenget med "prevent obvious token
  drift".
- docs/DESIGN.md finnes og dekker minimumskravene fra issue #59 sitt scope.

Kjøres med: py -3 -m unittest tests.test_design_tokens
"""
import json
import re
import unittest
from pathlib import Path

from modules.design_tokens import TOKENS_PATH, load_tokens, validate_tokens
from modules.card_template import _GOLD, _PERGAMENT, _MOSS, _COPPER, _ELFENBEIN
from ui.branding import _COLORS as APP_COLORS

ROOT = Path(__file__).resolve().parent.parent
STYLE_CSS = ROOT / "web" / "css" / "style.css"
DESIGN_MD = ROOT / "docs" / "DESIGN.md"


def _css_root_var(name: str) -> str:
    match = re.search(rf"--{re.escape(name)}:\s*(#[0-9a-fA-F]{{6}})\s*;", STYLE_CSS.read_text(encoding="utf-8"))
    if not match:
        raise AssertionError(f"Fant ingen --{name} i web/css/style.css :root")
    return match.group(1)


class TestTokensJsonGyldig(unittest.TestCase):
    def test_ekte_tokens_json_parser_og_validerer(self):
        data = load_tokens()
        self.assertEqual(data["schema_version"], "1.0.0")
        self.assertIn("accent", data["color"])

    def test_tokens_path_peker_pa_design_tokens_json(self):
        self.assertEqual(TOKENS_PATH, ROOT / "design" / "tokens.json")
        self.assertTrue(TOKENS_PATH.is_file())


class TestValiderTokensAvviserOdelagteData(unittest.TestCase):
    """validate_tokens() tas inn med bevisst ødelagte, syntetiske kopier --
    aldri den ekte filen -- slik at testene faktisk øver på
    valideringslogikken og ikke bare på at design/tokens.json tilfeldigvis
    er gyldig i dag."""

    def _gyldig_kopi(self) -> dict:
        return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))

    def test_manglende_toppnivanokkel_feiler(self):
        data = self._gyldig_kopi()
        del data["spacing_rem"]
        with self.assertRaises(ValueError):
            validate_tokens(data)

    def test_manglende_aksentfarge_feiler(self):
        data = self._gyldig_kopi()
        del data["color"]["accent"]["gold"]
        with self.assertRaises(ValueError):
            validate_tokens(data)

    def test_ugyldig_hex_format_feiler(self):
        data = self._gyldig_kopi()
        data["color"]["accent"]["gold"] = "gold"
        with self.assertRaises(ValueError):
            validate_tokens(data)

    def test_hex_uten_lademerke_feiler(self):
        data = self._gyldig_kopi()
        data["color"]["accent"]["gold"] = "c49a2a"
        with self.assertRaises(ValueError):
            validate_tokens(data)

    def test_negativ_spacing_feiler(self):
        data = self._gyldig_kopi()
        data["spacing_rem"] = [0.5, -1.0, 2.0]
        with self.assertRaises(ValueError):
            validate_tokens(data)

    def test_usortert_spacing_feiler(self):
        data = self._gyldig_kopi()
        data["spacing_rem"] = [2.0, 0.5, 1.0]
        with self.assertRaises(ValueError):
            validate_tokens(data)

    def test_tom_typografi_rolle_feiler(self):
        data = self._gyldig_kopi()
        data["typography"]["serif"] = ""
        with self.assertRaises(ValueError):
            validate_tokens(data)

    def test_ikke_heltall_radius_feiler(self):
        data = self._gyldig_kopi()
        data["radius_px"]["sm"] = 4.5
        with self.assertRaises(ValueError):
            validate_tokens(data)

    def test_gyldig_kopi_validerer_uten_feil(self):
        # Sanity: selve kopien (uendret) skal fortsatt validere -- ellers
        # ville testene over kunne feile av feil grunn.
        validate_tokens(self._gyldig_kopi())


class TestAksentfargerErSammeOverAlt(unittest.TestCase):
    """De seks aksentfargene var allerede byte-identiske på tvers av disse
    filene FØR denne modulen fantes (rent tilfeldig konsistente kopier) --
    denne testen formaliserer akkurat det som en fremtidig, håndhevet
    kontrakt i stedet for et tilfeldig sammenfall."""

    @classmethod
    def setUpClass(cls):
        cls.tokens = load_tokens()["color"]["accent"]

    def test_gull(self):
        gull = self.tokens["gold"]
        self.assertEqual(APP_COLORS["antikk_gull"], gull)
        self.assertEqual(_GOLD, gull)
        self.assertEqual(_css_root_var("gold"), gull)

    def test_pergament(self):
        pergament = self.tokens["pergament"]
        self.assertEqual(APP_COLORS["pergament"], pergament)
        self.assertEqual(_PERGAMENT, pergament)
        self.assertEqual(_css_root_var("pergament"), pergament)

    def test_mosegroenn(self):
        mose = self.tokens["moss"]
        self.assertEqual(APP_COLORS["mosegroen"], mose)
        self.assertEqual(_MOSS, mose)
        self.assertEqual(_css_root_var("moss"), mose)

    def test_kobber(self):
        kobber = self.tokens["copper"]
        self.assertEqual(APP_COLORS["kobber"], kobber)
        self.assertEqual(_COPPER, kobber)
        self.assertEqual(_css_root_var("copper"), kobber)

    def test_elfenbein(self):
        elfenbein = self.tokens["elfenbein"]
        self.assertEqual(_ELFENBEIN, elfenbein)
        self.assertEqual(_css_root_var("elfenbein"), elfenbein)

    def test_danger_finnes_kun_i_tokens_og_css(self):
        # danger brukes (ennå) ikke av modules/card_template.py eller
        # ui/branding.py -- kun av web/css/style.css. Sjekk likevel at den
        # er internt konsistent der den faktisk brukes.
        danger = self.tokens["danger"]
        self.assertEqual(_css_root_var("danger"), danger)


class TestDesignMdFinnesOgDekkerScope(unittest.TestCase):
    """Sjekker at docs/DESIGN.md finnes og har seksjoner for hvert punkt
    issue #59 sitt scope (pkt. 2) eksplisitt ba om -- ikke selve
    proseinnholdet (det er ikke noe en test bør låse), men at
    dokumentstrukturen faktisk dekker alle de etterspurte temaene."""

    @classmethod
    def setUpClass(cls):
        cls.text = DESIGN_MD.read_text(encoding="utf-8").lower()

    def test_filen_finnes(self):
        self.assertTrue(DESIGN_MD.is_file())

    def test_er_versjonert(self):
        self.assertRegex(self.text, r"v(?:ersjon\s*)?1\.0")

    def _assert_naevner(self, *ord: str):
        for w in ord:
            self.assertIn(w.lower(), self.text, f"DESIGN.md nevner ikke '{w}'")

    def test_dekker_fargeroller(self):
        self._assert_naevner("farge")

    def test_dekker_typografi(self):
        self._assert_naevner("typografi")

    def test_dekker_avstand(self):
        self._assert_naevner("avstand")

    def test_dekker_radius_og_skygge(self):
        self._assert_naevner("radius", "skygge")

    def test_dekker_kontroller(self):
        self._assert_naevner("knapp")

    def test_dekker_tilstander(self):
        self._assert_naevner("fokus", "disabled", "feil")

    def test_dekker_tilgjengelighet(self):
        self._assert_naevner("kontrast", "tilgjengelighet")

    def test_dekker_responsivitet(self):
        self._assert_naevner("responsiv")

    def test_dekker_tone_og_mikrotekst(self):
        self._assert_naevner("tone")

    def test_dekker_produkttilpasning_web_vs_app(self):
        self._assert_naevner("web", "app")


if __name__ == "__main__":
    unittest.main()
