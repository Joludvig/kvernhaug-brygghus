"""
WEB FIX -- B06 batch 3 (issue #150, finding #8): the dynamically generated
brew-log tasting sliders in web/js/brygg_page.js had a visible <label> per
flavor category but never linked it to its <input type="range"> via
id/for -- a screen reader had no per-slider accessible name for which of
up to 18 flavor axes a given control adjusts.

VIKTIG METODEMERKNAD (samme prinsipp som test_web_unit_labels.py og
test_web_custom_ingredient_id_active_draft.py): dette miljoet har ingen
JavaScript-kjoretid (Node er bevisst blokkert som Bash-allowlist-omgaelse,
se tests/web_js_runtime.py). Denne testen kan derfor ikke faktisk kjore
_byggSmakSliders() og observere en ekte, klonet DOM -- den er en
KILDE-KONTRAKT-test: den leser den FAKTISKE, kjorende
web/js/brygg_page.js-kildeteksten og verifiserer, via presise,
funksjons-skopede monstre, at riktig id/for-kobling faktisk skjer, at
id-en er brew-/indeks-basert (ikke avledet fra oversatt kategori-tekst),
og at den kanoniske dataset.kategori-nokkelen _lesSmakSliders() leser er
uendret. Reell multi-kort-/multi-slider-unikhet, native input.labels-
oppslosning, og skjermleser-annonsering kan bare bekreftes i en ekte
nettleser -- se PR-rapporten for owner/manual browser-gate status.

Kjores med:
    py -3 -m unittest tests.test_web_b06_batch3_tasting_slider_labels
"""
import io
import os
import re
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BRYGG_PAGE_JS = os.path.join(_REPO_ROOT, "web", "js", "brygg_page.js")


def _les(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _funksjonskropp(kilde, funksjonssignatur_regex):
    m = re.search(funksjonssignatur_regex, kilde)
    assert m, "fant ikke funksjonssignaturen: %r" % funksjonssignatur_regex
    start = m.end()
    slutt = kilde.index("\n}", start)
    return kilde[start:slutt]


class TestByggSmakSlidersIdForKobling(unittest.TestCase):
    def setUp(self):
        self.kropp = _funksjonskropp(
            _les(_BRYGG_PAGE_JS), r"function _byggSmakSliders\(container, brew\)\s*\{"
        )

    def test_id_avledes_fra_brewid_og_indeks_ikke_oversatt_tekst(self):
        self.assertRegex(self.kropp, r"\$\{brew\.brewId\}-smak-\$\{indeks\}")
        self.assertNotIn("smaksKategoriVisning(kategori)}`", self.kropp)

    def test_input_far_id_og_label_far_matchende_htmlfor(self):
        self.assertIn("input.id = feltId;", self.kropp)
        self.assertIn("label.htmlFor = feltId;", self.kropp)

    def test_loop_gar_over_indeks_ikke_bare_nokkelen(self):
        self.assertRegex(self.kropp, r"Object\.keys\(predikert\)\.forEach\(\(kategori, indeks\)")

    def test_kanonisk_dataset_kategori_urort(self):
        self.assertIn("input.dataset.kategori = kategori;", self.kropp)

    def test_smakskategorivisning_fortsatt_brukt_for_synlig_tekst(self):
        """B09 (allerede DEPLOYED/LIVE) sin oversettelses-fix skal ikke
        rores av denne batchen -- synlig label-tekst skal fortsatt bruke
        smaksKategoriVisning(kategori)."""
        self.assertIn("kategori: smaksKategoriVisning(kategori),", self.kropp)


class TestLesSmakSlidersUendret(unittest.TestCase):
    """_lesSmakSliders() skal fortsatt lese den kanoniske
    dataset.kategori-nokkelen -- id/for-fiksen skal ikke pavirke lagring."""

    def test_leser_dataset_kategori(self):
        kropp = _funksjonskropp(
            _les(_BRYGG_PAGE_JS), r"function _lesSmakSliders\(container\)\s*\{"
        )
        self.assertIn("el.dataset.kategori", kropp)


if __name__ == "__main__":
    unittest.main()
