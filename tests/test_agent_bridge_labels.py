"""
Kvernhaug Agent Bridge V1 -- regresjonstester for den EKSKLUSIVE
livssyklus-etikett-overgangen (.github/scripts/lifecycle_labels.py).

Chief review-fiks (PR #7, blokkerende punkt 2): en issue skal ALDRI
kunne bære to `status:*`-etiketter samtidig. Den viktigste testen her
(`test_full_review_loop_...`) kjører nøyaktig den normale runden
reviewet pekte på -- ready -> working -> review -> changes-requested ->
working -> review -> approved -- og krever at det finnes NØYAKTIG ÉN
livssyklus-etikett etter HVERT eneste steg, samtidig som
agent:claude/area:*-etikettene overlever uendret.

Ren stdlib-test, ingen GitHub-kall, ingen bash-avhengighet -- kjøres av
den vanlige suiten (`py -3 -m unittest discover -s tests`) på samme måte
som resten av prosjektets tester.
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "lifecycle_labels.py")


def _last_modul():
    """Laster .github/scripts/lifecycle_labels.py direkte fra sti --
    ligger bevisst utenfor Python-pakkestrukturen (det er en
    workflow-hjelper, ikke en app-modul), så den kan ikke importeres
    vanlig."""
    spec = importlib.util.spec_from_file_location("lifecycle_labels", _SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_LL = _last_modul()

# Etiketter som IKKE er livssyklus -- skal alltid overleve uendret.
_ADDITIVE = ["agent:claude", "area:infra"]


class TestNesteEtiketter(unittest.TestCase):
    def _livssyklus_i(self, etiketter):
        return [e for e in etiketter if e in _LL.LIVSSYKLUS_ETIKETTER]

    # ─── 1: selve eksklusivitets-garantien ──────────────────────────────

    def test_1_gammel_livssyklusetikett_fjernes_alltid(self):
        nye = _LL.neste_etiketter(_ADDITIVE + ["status:ready"], "status:working")
        self.assertEqual(self._livssyklus_i(nye), ["status:working"])

    def test_2_flere_stale_livssyklusetiketter_ryddes_alle(self):
        # Selv en allerede korrumpert issue (flere status-etiketter fra
        # før) normaliseres til nøyaktig én.
        skitten = _ADDITIVE + ["status:review", "status:changes-requested", "status:ready"]
        nye = _LL.neste_etiketter(skitten, "status:working")
        self.assertEqual(self._livssyklus_i(nye), ["status:working"])

    def test_3_ikke_livssyklusetiketter_beholdes_uendret_og_i_rekkefolge(self):
        nye = _LL.neste_etiketter(
            ["agent:claude", "status:ready", "area:infra", "enhancement"], "status:working",
        )
        self.assertEqual(nye, ["agent:claude", "area:infra", "enhancement", "status:working"])

    def test_4_ingen_duplikater(self):
        nye = _LL.neste_etiketter(["agent:claude", "agent:claude", "status:working"], "status:working")
        self.assertEqual(nye, ["agent:claude", "status:working"])

    def test_5_maal_none_fjerner_alle_livssyklusetiketter(self):
        nye = _LL.neste_etiketter(_ADDITIVE + ["status:review"], None)
        self.assertEqual(self._livssyklus_i(nye), [])
        self.assertEqual(nye, _ADDITIVE)

    def test_6_ugyldig_maal_avvises(self):
        with self.assertRaises(ValueError):
            _LL.neste_etiketter(_ADDITIVE, "status:noe-helt-annet")

    # ─── 7: HELE den normale review-runden (reviewets eksakte scenario) ──

    def test_7_full_review_loop_beholder_aldri_konflikterende_status(self):
        # Nøyaktig sekvensen Chief review beskrev som selv-korrumperende
        # i den opprinnelige implementasjonen.
        etiketter = _ADDITIVE + ["status:ready"]          # owner: klar
        forventet = [
            ("status:working", "workflow: kjøring startet"),
            ("status:review", "workflow: kjøring OK"),
            ("status:changes-requested", "owner: Chief ba om endringer"),
            ("status:working", "workflow: ny kjøring startet"),
            ("status:review", "workflow: kjøring OK igjen"),
            ("status:approved", "owner: Chief PASS -- ERSTATTER review, ikke i tillegg"),
        ]
        for maal, hva in forventet:
            etiketter = _LL.neste_etiketter(etiketter, maal)
            livssyklus = self._livssyklus_i(etiketter)
            self.assertEqual(
                livssyklus, [maal],
                f"{hva}: forventet nøyaktig ['{maal}'], fikk {livssyklus}",
            )
            # De additive etikettene overlever HVERT steg.
            for e in _ADDITIVE:
                self.assertIn(e, etiketter, f"{hva}: mistet {e}")

    # ─── 8: CLI-grensesnittet workflowen faktisk bruker ─────────────────

    def test_8_cli_gir_gyldig_put_body(self):
        inn = json.dumps(_ADDITIVE + ["status:review"])
        res = subprocess.run(
            [sys.executable, _SCRIPT, "status:working"],
            input=inn, capture_output=True, text=True, check=True,
        )
        body = json.loads(res.stdout)
        self.assertEqual(body, {"labels": ["agent:claude", "area:infra", "status:working"]})

    def test_9_cli_avviser_ugyldig_maal_uten_a_skrive_body(self):
        res = subprocess.run(
            [sys.executable, _SCRIPT, "ikke-en-status"],
            input=json.dumps(_ADDITIVE), capture_output=True, text=True,
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
