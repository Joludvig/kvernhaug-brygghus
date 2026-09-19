"""
Tester for issue #335: start_app.bat åpnet nettleseren to ganger ved
normal lokal oppstart -- én gang fra den eksplisitte
`start "" http://localhost:8501`-linjen, én gang fra Streamlit selv
(server.headless er ikke satt). Fjerner kun den eksplisitte
nettleser-åpne-linjen; ingen produktkode- eller Streamlit-config-endring.

Dekker (statisk fil-sjekk, ingen prosess-oppstart):
- Ingen eksplisitt `start ""`-nettleser-åpning finnes lengre i filen.
- Streamlit-kommandoen som starter appen på port 8501 er uendret/tilstede.
- Filen beholder repoets faktiske linjeskift-konvensjon: `.gitattributes`
  har `* text=auto eol=lf` for hele repoet (issue #55), så den commitede
  blob-en er alltid LF -- ikke CRLF -- uavhengig av hva et Windows-
  checkout viser lokalt. cmd.exe/`.bat`-kjøring er upåvirket av dette;
  denne testen sjekker derfor at filen fortsatt bare inneholder LF (ingen
  CR er introdusert av denne endringen), ikke at den er CRLF.

Kjøres med: python3 -m unittest tests.test_start_app_launcher -b
"""
import unittest
from pathlib import Path

LAUNCHER_PATH = Path(__file__).resolve().parent.parent / "start_app.bat"


class TestStartAppLauncher(unittest.TestCase):
    def setUp(self):
        self.raw = LAUNCHER_PATH.read_bytes()
        self.text = self.raw.decode("ascii")

    def test_no_explicit_browser_open(self):
        self.assertNotIn('start "" http://localhost:8501', self.text)
        for line in self.text.splitlines():
            stripped = line.strip()
            self.assertFalse(
                stripped.lower().startswith("start ") and "http://" in stripped.lower(),
                f"Uventet eksplisitt nettleser-åpning funnet: {line!r}",
            )

    def test_streamlit_launch_command_present(self):
        self.assertIn(
            '".venv\\Scripts\\python.exe" -m streamlit run app.py --server.port 8501',
            self.text,
        )

    def test_lf_line_endings_preserved(self):
        self.assertNotIn(
            b"\r",
            self.raw,
            "Fant CR-byte -- repoets .gitattributes (eol=lf) krever LF, ikke CRLF.",
        )
        self.assertTrue(self.raw.endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
