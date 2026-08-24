"""
Regresjonstest for Supplier Data Cleanup V1: den defekte og villedende
leverandør-synk-kodestien skal være borte og ikke komme snikende tilbake.

Bakgrunn (Supplier Catalog Audit V1 + Favorittbutikk-audit V1, begge
verifisert to ganger): `modules/store_sync.py` gjorde ett `requests.get()`
mot butikkforsiden, kastet svaret uten å bruke det, og returnerte i stedet
15 hardkodede produkter. Sammenligningen leste `pris_olbrygging` /
`pris_vestbrygg` -- felt som fantes i 0 av 216 masteroppføringer etter at
prisdata ble flyttet til `butikk_match`. Resultatet var at ui/supplier_panel.py
meldte «Kontakter vestbrygg.no og olbrygging.no...» og «Synkronisering
fullført!», rapporterte ALLE produkter som prisavvik mot en DB-pris på 0 kr,
og listet hardkodede produkter som «nye i butikk».

Panelet var i tillegg fullstendig redundant: produktoppdagelse dekkes av
store_scraper + unmatched_*.json + review_panel, priser av butikk_match +
smart_shopping_list, og «utdaterte varer» er direkte utledbart fra
butikk_match. Derfor sletting fremfor reparasjon -- en reparasjon ville
duplisert en pipeline som allerede finnes og virker.

Testene her kjører uten Streamlit-kontekst og gjør ingen nettverkskall.
"""
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestDefektKodestiErFjernet(unittest.TestCase):

    def test_store_sync_modulen_finnes_ikke(self):
        self.assertFalse((REPO_ROOT / "modules" / "store_sync.py").exists(),
                         "modules/store_sync.py skal være slettet")

    def test_supplier_panel_finnes_ikke(self):
        self.assertFalse((REPO_ROOT / "ui" / "supplier_panel.py").exists(),
                         "ui/supplier_panel.py skal være slettet")

    def test_store_sync_kan_ikke_importeres(self):
        with self.assertRaises(ImportError):
            import modules.store_sync  # noqa: F401

    def test_supplier_panel_kan_ikke_importeres(self):
        with self.assertRaises(ImportError):
            import ui.supplier_panel  # noqa: F401


class TestIngenGjenvaerendeReferanser(unittest.TestCase):
    """
    En slettet modul som fortsatt refereres gir ImportError ved oppstart av
    hele appen -- derfor sjekkes kildekoden direkte, ikke bare filsystemet.
    """

    def _py_filer(self):
        for sti in REPO_ROOT.rglob("*.py"):
            deler = set(sti.parts)
            if "__pycache__" in deler or ".venv" in deler or "backup" in deler:
                continue
            yield sti

    def test_ingen_python_fil_refererer_store_sync_eller_supplier_panel(self):
        treff = []
        for sti in self._py_filer():
            if sti.name == Path(__file__).name:
                continue
            tekst = sti.read_text(encoding="utf-8", errors="replace")
            for navn in ("store_sync", "supplier_panel", "lag_sortimentrapport"):
                if navn in tekst:
                    treff.append(f"{sti.relative_to(REPO_ROOT)} -> {navn}")
        self.assertEqual(treff, [], "gjenværende referanser: %s" % treff)

    def test_app_py_har_verken_import_eller_render_kall(self):
        app = (REPO_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("supplier_panel", app)
        self.assertNotIn("render_supplier_panel", app)


class TestKorrektPipelineErIntakt(unittest.TestCase):
    """
    Fjerningen skal IKKE ha rørt de leverandørflytene som faktisk virker.
    Uten denne testen kunne en for ivrig opprydding tatt med seg riktig kode.
    """

    def test_de_fungerende_supplier_modulene_finnes_fortsatt(self):
        for rel in [
            "modules/store_scraper.py",
            "modules/store_matcher.py",
            "modules/product_link_scraper.py",
            "modules/smart_shopping_list.py",
            "ui/review_panel.py",
            "ui/smart_shopping_list_panel.py",
        ]:
            with self.subTest(modul=rel):
                self.assertTrue((REPO_ROOT / rel).exists(), f"{rel} skal være urørt")

    def test_de_fungerende_modulene_kan_fortsatt_importeres(self):
        import modules.product_link_scraper  # noqa: F401
        import modules.store_matcher  # noqa: F401
        import modules.store_scraper  # noqa: F401
        import modules.smart_shopping_list  # noqa: F401


if __name__ == "__main__":
    unittest.main()
