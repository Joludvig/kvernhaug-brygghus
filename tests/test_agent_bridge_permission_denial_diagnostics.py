"""
Kvernhaug Agent Bridge -- regresjonstester for
.github/scripts/permission_denial_diagnostics.py (issue #348).

Kjerneprinsippet: en manglende, tom, eller uventet-formatert execution-logg
skal ALDRI gi en feil/exception -- kun en tydelig "utilgjengelig"-rapport,
siden dette diagnostikk-steget aldri får blokkere eller endre leveranse-
porten, branch/push-reglene eller noen annen eksisterende kontroll.

Ren stdlib-test, ingen GitHub-kall, ingen nettverkstilgang.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "permission_denial_diagnostics.py")
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml")


def _last_modul():
    spec = importlib.util.spec_from_file_location("permission_denial_diagnostics", _SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_PDD = _last_modul()


_TOOL_USE_MSG = {
    "type": "assistant",
    "message": {
        "content": [
            {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {"command": "git rev-parse HEAD"}}
        ]
    },
}
_TOOL_DENIAL_MSG = {
    "type": "user",
    "message": {
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_1",
                "is_error": True,
                "content": [
                    {
                        "type": "text",
                        "text": "Claude requested permissions to use Bash, but you haven't granted it yet.",
                    }
                ],
            }
        ]
    },
}
_TOOL_OK_MSG = {
    "type": "user",
    "message": {
        "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "abc123"}
        ]
    },
}


class TestLesMeldinger(unittest.TestCase):
    def test_1_manglende_sti_gir_none_og_grunn(self):
        rader, grunn = _PDD.les_meldinger("")
        self.assertIsNone(rader)
        self.assertIn("Ingen execution_file", grunn)

    def test_2_ikke_eksisterende_fil_gir_none_og_grunn(self):
        rader, grunn = _PDD.les_meldinger("/tmp/kbh-does-not-exist-issue-348.json")
        self.assertIsNone(rader)
        self.assertIn("Fant ingen", grunn)

    def test_3_tom_fil_gir_tom_liste_ikke_feil(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            rader, grunn = _PDD.les_meldinger(path)
            self.assertEqual(rader, [])
            self.assertIsNone(grunn)
        finally:
            os.unlink(path)

    def test_4_json_liste_parses(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([_TOOL_USE_MSG, _TOOL_DENIAL_MSG], f)
            path = f.name
        try:
            rader, grunn = _PDD.les_meldinger(path)
            self.assertIsNone(grunn)
            self.assertEqual(len(rader), 2)
        finally:
            os.unlink(path)

    def test_5_jsonl_parses_og_hopper_over_ugyldige_linjer(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps(_TOOL_USE_MSG) + "\n")
            f.write("dette er ikke gyldig json\n")
            f.write(json.dumps(_TOOL_DENIAL_MSG) + "\n")
            path = f.name
        try:
            rader, grunn = _PDD.les_meldinger(path)
            self.assertIsNone(grunn)
            self.assertEqual(len(rader), 2)
        finally:
            os.unlink(path)

    def test_6_uventet_json_form_gir_none_og_grunn(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(42, f)
            path = f.name
        try:
            rader, grunn = _PDD.les_meldinger(path)
            self.assertIsNone(rader)
            self.assertIn("uventet format", grunn)
        finally:
            os.unlink(path)


class TestFinnTillatelsesAvslag(unittest.TestCase):
    def test_7_finner_avslag_med_riktig_verktoy_og_input(self):
        funn = _PDD.finn_tillatelses_avslag([_TOOL_USE_MSG, _TOOL_DENIAL_MSG])
        self.assertEqual(len(funn), 1)
        self.assertEqual(funn[0]["tool"], "Bash")
        self.assertIn("git rev-parse HEAD", funn[0]["input_excerpt"])
        self.assertIn("requested permissions to use Bash", funn[0]["denial_excerpt"])

    def test_8_vellykket_tool_result_gir_ingen_avslag(self):
        funn = _PDD.finn_tillatelses_avslag([_TOOL_USE_MSG, _TOOL_OK_MSG])
        self.assertEqual(funn, [])

    def test_9_tom_liste_gir_ingen_avslag_ikke_feil(self):
        self.assertEqual(_PDD.finn_tillatelses_avslag([]), [])
        self.assertEqual(_PDD.finn_tillatelses_avslag(None), [])

    def test_10_ukjent_tool_use_id_faller_tilbake_til_ukjent_verktoy(self):
        orphan_denial = {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_does_not_exist",
                        "content": "permission denied",
                    }
                ]
            },
        }
        funn = _PDD.finn_tillatelses_avslag([orphan_denial])
        self.assertEqual(len(funn), 1)
        self.assertEqual(funn[0]["tool"], "ukjent verktøy")

    def test_11_ikke_en_avslags_setning_matcher_ikke(self):
        benign = {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "tool_use_id": "toolu_1", "content": "everything is fine"}
                ]
            },
        }
        self.assertEqual(_PDD.finn_tillatelses_avslag([_TOOL_USE_MSG, benign]), [])


class TestFormatering(unittest.TestCase):
    def test_12_sammendrag_utilgjengelig_nevner_grunn(self):
        tekst = _PDD.formater_sammendrag([], False, "Fant ingen execution-loggfil")
        self.assertIn("utilgjengelig", tekst)
        self.assertIn("Fant ingen execution-loggfil", tekst)

    def test_13_sammendrag_ingen_avslag(self):
        tekst = _PDD.formater_sammendrag([], True, None)
        self.assertIn("Ingen permission-avslag", tekst)

    def test_14_sammendrag_er_alltid_en_linje(self):
        avslag = [{"tool": "Bash", "input_excerpt": "git rev-parse HEAD", "denial_excerpt": "avvist"}]
        tekst = _PDD.formater_sammendrag(avslag, True, None)
        self.assertNotIn("\n", tekst)
        self.assertIn("Bash", tekst)

    def test_15_kort_kutter_lange_strenger_uten_a_feile(self):
        tekst = _PDD._kort("x" * 1000, maks=50)
        self.assertLessEqual(len(tekst), 50)


class TestCliKontrakt(unittest.TestCase):
    def _kjor_cli(self, env_overrides):
        env = dict(os.environ)
        env.update(env_overrides)
        return subprocess.run([sys.executable, _SCRIPT], capture_output=True, text=True, env=env)

    def test_16_cli_uten_execution_file_er_trygt(self):
        env = dict(os.environ)
        env.pop("EXECUTION_FILE", None)
        env.pop("GITHUB_STEP_SUMMARY", None)
        res = subprocess.run([sys.executable, _SCRIPT], capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0)
        self.assertIn("available=false", res.stdout)
        self.assertIn("denial_count=0", res.stdout)
        self.assertIn("denial_summary=", res.stdout)

    def test_17_cli_med_avslag_teller_riktig(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([_TOOL_USE_MSG, _TOOL_DENIAL_MSG], f)
            path = f.name
        try:
            res = self._kjor_cli({"EXECUTION_FILE": path})
            self.assertEqual(res.returncode, 0)
            self.assertIn("available=true", res.stdout)
            self.assertIn("denial_count=1", res.stdout)
            self.assertIn("Bash", res.stdout)
        finally:
            os.unlink(path)

    def test_18_cli_skriver_til_github_step_summary_uten_a_feile(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([_TOOL_USE_MSG, _TOOL_DENIAL_MSG], f)
            path = f.name
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as summary_f:
            summary_path = summary_f.name
        try:
            res = self._kjor_cli({"EXECUTION_FILE": path, "GITHUB_STEP_SUMMARY": summary_path})
            self.assertEqual(res.returncode, 0)
            with open(summary_path, "r", encoding="utf-8") as f:
                summary_content = f.read()
            self.assertIn("permission-denial diagnostics", summary_content)
            self.assertIn("Bash", summary_content)
        finally:
            os.unlink(path)
            os.unlink(summary_path)

    def test_19_cli_uten_github_step_summary_env_er_trygt(self):
        env = dict(os.environ)
        env.pop("GITHUB_STEP_SUMMARY", None)
        env["EXECUTION_FILE"] = ""
        res = subprocess.run([sys.executable, _SCRIPT], capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0)


class TestWorkflowWiring(unittest.TestCase):
    """Beviser at det nye steget faktisk er koblet inn i workflowen -- kun
    via workflowens EGET Python-kall mot execution-loggen på disk, ALDRI
    gjennom Claudes --allowedTools -- og at det er markert best-effort
    (kan aldri feile/blokkere jobben)."""

    def setUp(self):
        with open(_WORKFLOW, "r", encoding="utf-8") as f:
            self.text = f.read()

    def test_20_steget_finnes_og_kaller_riktig_script(self):
        self.assertIn("Capture Claude permission-denial diagnostics (issue #348)", self.text)
        self.assertIn("python3 .github/scripts/permission_denial_diagnostics.py", self.text)

    def test_21_steget_bruker_execution_file_output_fra_claude_steget(self):
        self.assertIn("EXECUTION_FILE: ${{ steps.claude.outputs.execution_file }}", self.text)

    def test_22_steget_kjorer_med_always_ikke_bare_success(self):
        match_idx = self.text.index("Capture Claude permission-denial diagnostics (issue #348)")
        window = self.text[match_idx : match_idx + 600]
        self.assertIn("always()", window)

    def test_23_ingen_ny_bash_tillatelse_ble_lagt_til_for_dette(self):
        # Diagnostikken kjører helt uavhengig av Claudes --allowedTools --
        # ingen ny Bash(...)-regel skal være nødvendig for selve steget.
        allowed_tools_line = next(
            line for line in self.text.splitlines() if "--allowedTools" in line
        )
        self.assertNotIn("permission_denial_diagnostics", allowed_tools_line)

    def test_24_rapport_steg_refererer_denial_count_eller_summary(self):
        self.assertIn("steps.denials.outputs.denial_count", self.text)
        self.assertIn("steps.denials.outputs.denial_summary", self.text)


if __name__ == "__main__":
    unittest.main()
