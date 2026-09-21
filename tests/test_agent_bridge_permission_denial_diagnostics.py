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

    def test_3_tom_fil_gir_utilgjengelig_ikke_stille_null_avslag(self):
        # Chief-review (PR #349) blokker 2: en tom logg skal ALDRI late som
        # et gyldig "0 avslag"-resultat -- kun `available=false`, present
        # av samme grunn som en manglende fil.
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            rader, grunn = _PDD.les_meldinger(path)
            self.assertIsNone(rader)
            self.assertIn("tom", grunn)
        finally:
            os.unlink(path)

    def test_3b_gyldig_tom_json_liste_gir_ogsa_utilgjengelig(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([], f)
            path = f.name
        try:
            rader, grunn = _PDD.les_meldinger(path)
            self.assertIsNone(rader)
            self.assertIsNotNone(grunn)
        finally:
            os.unlink(path)

    def test_3c_jsonl_kun_ugyldige_linjer_gir_utilgjengelig(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("dette er ikke json\n")
            f.write("heller ikke dette\n")
            path = f.name
        try:
            rader, grunn = _PDD.les_meldinger(path)
            self.assertIsNone(rader)
            self.assertIsNotNone(grunn)
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
        # Chief-review runde 2 (issue #348): rå kommandolinje vises ALDRI
        # lenger -- kun en allowlist-basert signatur (programnavn + kjente
        # trygge ord/flagg-navn), pluss en sha256 for korrelasjon.
        self.assertIn("git", funn[0]["input_excerpt"])
        self.assertIn("[REDIGERT]", funn[0]["input_excerpt"])
        self.assertIn("sha256=", funn[0]["input_excerpt"])
        self.assertNotIn("rev-parse", funn[0]["input_excerpt"])
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

    def test_17b_cli_tom_execution_fil_gir_available_false(self):
        # Chief-review (PR #349) blokker 2: dette må aldri stille bli lest
        # som `denial_count=0`/`available=true`.
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            res = self._kjor_cli({"EXECUTION_FILE": path})
            self.assertEqual(res.returncode, 0)
            self.assertIn("available=false", res.stdout)
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

    def test_24b_rapport_steg_refererer_available_issue_348_blokker_2(self):
        # Chief-review (PR #349) blokker 2: "0 denials" og "unavailable"
        # må være skilt i den repo-synlige diagnostikken, ikke bare i CLI-
        # utdataet -- begge rapport-stegene må lese `steps.denials.outputs.
        # available`, ikke bare `denial_count`.
        self.assertEqual(self.text.count("steps.denials.outputs.available"), 2)


def _tool_use_med_input(navn, tool_input):
    return {
        "type": "assistant",
        "message": {
            "content": [{"type": "tool_use", "id": "toolu_x", "name": navn, "input": tool_input}]
        },
    }


def _avslag_med_tekst(tekst):
    return {
        "type": "user",
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_x",
                    "is_error": True,
                    "content": [{"type": "text", "text": tekst}],
                }
            ]
        },
    }


class TestHemmelighetsRedigering(unittest.TestCase):
    """Chief-review (PR #349) blokker 1: rå input-verdier/avslagstekst med
    hemmeligheter skal ALDRI overleve til `input_excerpt`/`denial_excerpt`,
    som begge publiseres til en repo-synlig issue-kommentar."""

    _AVVIST = "Claude requested permissions to use Bash, but you haven't granted it yet."

    def test_25_github_pat_redigeres_bort_fra_bash_input(self):
        bruk = _tool_use_med_input(
            "Bash", {"command": "curl -H 'Authorization: token ghp_1234567890abcdef1234567890abcdef1234' https://api.github.com"}
        )
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertEqual(len(funn), 1)
        self.assertNotIn("ghp_1234567890abcdef1234567890abcdef1234", funn[0]["input_excerpt"])
        self.assertIn("[REDIGERT]", funn[0]["input_excerpt"])

    def test_26_github_fine_grained_pat_redigeres_bort(self):
        hemmelig = "github_pat_11ABCDEFG0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQ"
        bruk = _tool_use_med_input("Bash", {"command": f"git push https://x-access-token:{hemmelig}@github.com/foo/bar"})
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn(hemmelig, funn[0]["input_excerpt"])

    def test_27_aws_access_key_id_redigeres_bort(self):
        bruk = _tool_use_med_input("Bash", {"command": "export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"})
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", funn[0]["input_excerpt"])

    def test_28_aws_secret_access_key_tildeling_redigeres_bort(self):
        bruk = _tool_use_med_input(
            "Bash", {"command": "aws_secret_access_key=wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY python3 deploy.py"}
        )
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn("wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY", funn[0]["input_excerpt"])

    def test_29_anthropic_key_redigeres_bort(self):
        bruk = _tool_use_med_input("Bash", {"command": "echo sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH"})
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn("sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGH", funn[0]["input_excerpt"])

    def test_30_generisk_token_flagg_redigeres_bort(self):
        bruk = _tool_use_med_input("Bash", {"command": "curl --token hunter2supersecretvalue https://example.com"})
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn("hunter2supersecretvalue", funn[0]["input_excerpt"])
        self.assertIn("--token", funn[0]["input_excerpt"])

    def test_31_hemmelighet_i_selve_avslagsteksten_redigeres_ogsa(self):
        bruk = _tool_use_med_input("Bash", {"command": "echo hei"})
        avslag_med_hemmelighet = _avslag_med_tekst(
            "permission denied for token ghp_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ"
        )
        funn = _PDD.finn_tillatelses_avslag([bruk, avslag_med_hemmelighet])
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyzABCDEFGHIJ", funn[0]["denial_excerpt"])

    def test_32_write_content_verdi_vises_aldri_kun_feltnavn(self):
        # Write/Edit-lignende fritekst-felter (content/new_string/old_string)
        # skal ALDRI gjengis rått -- kun hvilke feltnavn input hadde.
        bruk = _tool_use_med_input(
            "Write",
            {"content": "API_KEY=sk-ant-api03-should-never-appear-in-a-comment-anywhere"},
        )
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn("sk-ant-api03-should-never-appear-in-a-comment-anywhere", funn[0]["input_excerpt"])
        self.assertIn("content", funn[0]["input_excerpt"])

    def test_33_write_file_path_er_trygt_a_vise(self):
        bruk = _tool_use_med_input(
            "Write", {"file_path": "/repo/data/pantry.json", "content": "hemmelig innhold"}
        )
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertEqual(funn[0]["input_excerpt"], "/repo/data/pantry.json")
        self.assertNotIn("hemmelig innhold", funn[0]["input_excerpt"])


class TestAllowlistSignaturChiefRunde2(unittest.TestCase):
    """Chief re-review (PR #349, issue #348): en endelig secret-regex skal
    ALDRI være den primære sikkerhetsgrensen -- default skal være å SKJULE
    et posisjonsargument/felt med mindre det står på en fast, liten,
    kjent-trygg allowlist. Disse testene dekker nettopp det Chief ba om i
    "Required bounded fix" punkt 4: en ukjent hemmelighet i et Bash-
    posisjonsargument, URL-legitimasjon/-query, vilkårlig `pattern`-tekst,
    og at signaturen fortsatt skiller nyttige kommandoklasser."""

    _AVVIST = "Claude requested permissions to use Bash, but you haven't granted it yet."

    def test_34_ukjent_hemmelighet_i_bash_posisjonsargument_overlever_ikke(self):
        # En hemmelighet uten noe kjent prefiks/mønster i det hele tatt --
        # ingen regex i _KJENTE_HEMMELIGHETER/_HEMMELIG_TILDELING ville
        # noensinne fanget denne. Allowlisten må skjule den likevel, fordi
        # den bare er et vilkårlig posisjonsargument til et program uten
        # kjent underkommando-vokabular.
        ukjent_hemmelighet = "xK7qP9mZ2vT4nB8jL1wR6yD3sF0hQ5cV"
        bruk = _tool_use_med_input("Bash", {"command": f"curl https://internal.example.com --data {ukjent_hemmelighet}"})
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn(ukjent_hemmelighet, funn[0]["input_excerpt"])
        self.assertIn("[REDIGERT]", funn[0]["input_excerpt"])
        self.assertIn("curl", funn[0]["input_excerpt"])

    def test_35_url_med_brukernavn_passord_overlever_ikke_i_bash(self):
        bruk = _tool_use_med_input(
            "Bash", {"command": "git push https://alice:S3cretPassw0rd@example.com/repo.git"}
        )
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn("S3cretPassw0rd", funn[0]["input_excerpt"])
        self.assertNotIn("alice:S3cretPassw0rd", funn[0]["input_excerpt"])

    def test_36_url_med_query_hemmelighet_overlever_ikke_som_trygt_felt(self):
        # `url` er bevisst fjernet fra _TRYGGE_INPUT_NOKLER -- en URL kan
        # bære en query-streng-hemmelighet (f.eks. et signert token) og er
        # derfor ikke universelt trygg å gjengi rått.
        bruk = _tool_use_med_input(
            "WebFetch", {"url": "https://example.com/download?token=hemmelig-signert-verdi"}
        )
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn("hemmelig-signert-verdi", funn[0]["input_excerpt"])
        self.assertNotIn("https://example.com", funn[0]["input_excerpt"])

    def test_37_vilkarlig_pattern_tekst_overlever_ikke_som_trygt_felt(self):
        # `pattern` er bevisst fjernet fra _TRYGGE_INPUT_NOKLER -- et
        # søkemønster kan selv inneholde vilkårlig sensitiv fritekst.
        bruk = _tool_use_med_input(
            "Grep", {"pattern": "AKIAIOSFODNN7EXAMPLE|super hemmelig intern kundeliste"}
        )
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn("super hemmelig intern kundeliste", funn[0]["input_excerpt"])
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", funn[0]["input_excerpt"])
        self.assertIn("pattern", funn[0]["input_excerpt"])

    def test_38_signaturen_skiller_git_push_fra_gh_pr_edit(self):
        push = _tool_use_med_input("Bash", {"command": "git push -u origin agent/issue-348"})
        pr_edit = _tool_use_med_input("Bash", {"command": "gh pr edit 349 --body 'oppdatert rapport'"})
        funn_push = _PDD.finn_tillatelses_avslag([push, _avslag_med_tekst(self._AVVIST)])
        funn_edit = _PDD.finn_tillatelses_avslag([pr_edit, _avslag_med_tekst(self._AVVIST)])
        self.assertIn("git push", funn_push[0]["input_excerpt"])
        self.assertIn("gh pr edit", funn_edit[0]["input_excerpt"])
        self.assertNotEqual(funn_push[0]["input_excerpt"], funn_edit[0]["input_excerpt"])
        self.assertNotIn("oppdatert rapport", funn_edit[0]["input_excerpt"])

    def test_39_signaturen_skiller_python3_m_unittest_fra_git_push(self):
        unittest_kall = _tool_use_med_input(
            "Bash", {"command": "python3 -m unittest discover -s tests -b"}
        )
        push = _tool_use_med_input("Bash", {"command": "git push origin agent/issue-348"})
        funn_unittest = _PDD.finn_tillatelses_avslag([unittest_kall, _avslag_med_tekst(self._AVVIST)])
        funn_push = _PDD.finn_tillatelses_avslag([push, _avslag_med_tekst(self._AVVIST)])
        self.assertIn("python3 -m unittest", funn_unittest[0]["input_excerpt"])
        self.assertNotIn("python3 -m unittest", funn_push[0]["input_excerpt"])
        self.assertNotEqual(funn_unittest[0]["input_excerpt"], funn_push[0]["input_excerpt"])

    def test_40_ukjent_flagg_uten_likhetstegn_skjules_helt(self):
        # `-pHunter2` (en hemmelighet limt rett inn i et kortflagg uten
        # `=`) skal ikke overleve som "flagg-navn" -- hele tokenet skjules.
        bruk = _tool_use_med_input("Bash", {"command": "mysql -pHunter2VerySecret -uadmin"})
        funn = _PDD.finn_tillatelses_avslag([bruk, _avslag_med_tekst(self._AVVIST)])
        self.assertNotIn("Hunter2VerySecret", funn[0]["input_excerpt"])


class TestStrukturertePermissionDenials(unittest.TestCase):
    """Chief-review 5267215839: SDK-resultatets permission_denials[] er
    primærkilden og må fungere uten tekstlige denial-tool_results."""

    def test_41_to_strukturerte_denials_uten_tool_result_gir_eksakt_to(self):
        rader = [
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "permission_denials": [
                    {
                        "tool_name": "Bash",
                        "tool_use_id": "toolu_a",
                        "tool_input": {
                            "command": "git push https://alice:ultrahemmelig@example.com/repo.git"
                        },
                    },
                    {
                        "tool_name": "Edit",
                        "tool_use_id": "toolu_b",
                        "tool_input": {
                            "file_path": "/repo/docs/file.md",
                            "new_string": "privat-innhold-som-ikke-skal-vises",
                        },
                    },
                ],
            }
        ]

        funn = _PDD.finn_tillatelses_avslag(rader)

        self.assertEqual(len(funn), 2)
        self.assertEqual([f["tool"] for f in funn], ["Bash", "Edit"])
        self.assertNotIn("ultrahemmelig", funn[0]["input_excerpt"])
        self.assertIn("git push", funn[0]["input_excerpt"])
        self.assertEqual(funn[1]["input_excerpt"], "/repo/docs/file.md")
        self.assertNotIn("privat-innhold", funn[1]["input_excerpt"])

    def test_42_strukturert_og_tekstlig_samme_denial_dobbelttelles_ikke(self):
        tool_use = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "id": "toolu_same",
                        "name": "Bash",
                        "input": {"command": "git push origin agent/issue-348"},
                    }
                ]
            },
        }
        tool_result = {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_same",
                        "is_error": True,
                        "content": "permission denied",
                    }
                ]
            },
        }
        result = {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "permission_denials": [
                {
                    "tool_name": "Bash",
                    "tool_use_id": "toolu_same",
                    "tool_input": {"command": "git push origin agent/issue-348"},
                }
            ],
        }

        funn = _PDD.finn_tillatelses_avslag([tool_use, tool_result, result])

        self.assertEqual(len(funn), 1)
        self.assertEqual(funn[0]["tool"], "Bash")
        self.assertIn("git push", funn[0]["input_excerpt"])

    def test_43_tomt_strukturert_felt_er_autoritativt_og_bruker_ikke_tekstfallback(self):
        # Når SDK-resultatet eksplisitt sier ingen denials, skal en eldre
        # tekstheuristikk ikke overstyre den autoritative kilden.
        result = {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "permission_denials": [],
        }
        self.assertEqual(
            _PDD.finn_tillatelses_avslag([_TOOL_USE_MSG, _TOOL_DENIAL_MSG, result]),
            [],
        )


if __name__ == "__main__":
    unittest.main()
