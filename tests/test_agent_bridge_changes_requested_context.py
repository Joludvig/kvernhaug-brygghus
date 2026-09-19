"""
Kvernhaug Agent Bridge -- regresjonstester for den deterministiske,
fail-closed changes-requested-handoffen
(.github/scripts/changes_requested_context.py, issue #329).

BAKGRUNN: Agent Bridge-kjøring 35399093833 (issue #327 / PR #328) passerte
ALLE eksisterende porter -- autorisert trigger, korrekt deterministisk
branch, korrekt pre-run head, PR satt i Draft, Draft verifisert -- og endte
likevel `conclusion: success` med `permission_denials_count = 11`, INGEN ny
commit og uendret PR-head. Triggeren var aldri feilen; HANDOFFEN var det:
wrapperen ga Claude nesten ingen verifisert arbeidskontekst og lot Claude
gjenoppdage branch, PR og selve Chief-reviewen gjennom gh/git-kall før den
kunne begynne på reviewen. Se moduldocstringen i
changes_requested_context.py og AGENT_WORKFLOW.md ("Deterministic
changes-requested handoff") for hele resonnementet.

Testene dekker akseptansepunktene A-L i issue #329:
  A. happy path -- én korrekt PR, eksakt branch/base/head, siste
     repo-owner-review = CHANGES_REQUESTED, review-commit == eksakt head
     -> gyldig kontekst returneres,
  B. ingen PR -> fail closed,
  C. flere/tvetydige PR-er -> fail closed,
  D. feil base/head branch -> fail closed,
  E. head-SHA mismatch -> fail closed, og (Chief-review-fiks, PR #330) en
     PR som ikke lenger er Draft ved fersk refetch -> fail closed,
  F. ingen CHANGES_REQUESTED-review -> fail closed,
  G. CHANGES_REQUESTED fra feil author -> fail closed,
  H. repo-owner-review finnes, men commit_id != eksakt head -> fail closed,
  I. nyere review-state gjør gammel CHANGES_REQUESTED stale -> fail closed
     etter den dokumenterte semantikken i `_nyeste_beslutning`,
  J. review-body med multiline tekst, backticks, anførselstegn og
     shell-lignende innhold transporteres via FIL -- aldri gjennom
     shell-quoting, `$GITHUB_OUTPUT` eller `${{ }}` -- og blir aldri
     evaluert som shell,
  K. changes-requested-checkouten lander på eksakt pre-run head før Claude
     (`verifiser_lokalt_hode` + workflow-koblingen),
  L. `status:ready` er upåvirket -- porten er et ikke-alarmerende "ikke
     påkrevd" og den eksisterende branch-opprettings-banen står urørt.

Pluss workflow-kildetekst-kontrakten: stegene er gatet riktig (etter
Draft-verifiseringen, FØR "Run Claude Code"), review-body går aldri gjennom
et shell-kommandoargument, og ingen ny merge/master-push-overflate
introduseres.

Ren stdlib-test, ingen GitHub-kall -- kjøres av den vanlige suiten
(`py -3 -m unittest discover -s tests -b`).
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "changes_requested_context.py")
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml")
_GITIGNORE = os.path.join(_REPO_ROOT, ".gitignore")

HEAD = "6699b63b039b7cefc086fceb65b01eb48adc3542"
ANNET_HODE = "ab5801f9a3360c4e15dac58a6095545a540bd9fe"
EIER = "Joludvig"
BRANCH = "agent/issue-327"


def _last_modul(sti, navn):
    spec = importlib.util.spec_from_file_location(navn, sti)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


crc = _last_modul(_SCRIPT, "changes_requested_context")


def _pr(**overstyr):
    pr = {
        "number": 328,
        "state": "OPEN",
        "baseRefName": "master",
        "headRefName": BRANCH,
        "headRefOid": HEAD,
        "isDraft": True,
    }
    pr.update(overstyr)
    return pr


def _review(**overstyr):
    r = {
        "id": 5252972553,
        "state": "CHANGES_REQUESTED",
        "commit_id": HEAD,
        "body": "Fresh Streamlit radio has a pre-selected answer. Bounded fix requested.",
        "submitted_at": "2026-09-18T21:54:34Z",
        "user": {"login": EIER},
    }
    r.update(overstyr)
    return r


def _bygg(**overstyr):
    kwargs = {
        "trigger_label": "status:changes-requested",
        "issue_nummer": "327",
        "branch_navn": BRANCH,
        "before_pr_number": "328",
        "before_head_sha": HEAD,
        "prs": [_pr()],
        "reviews": [_review()],
        "repo_owner": EIER,
    }
    kwargs.update(overstyr)
    return crc.bygg_kontekst(**kwargs)


def _les_workflow():
    with open(_WORKFLOW, encoding="utf-8") as f:
        return f.read()


def _steg_blokk(tekst, steg_id):
    """Rå YAML-tekst for steget med `id: <steg_id>`, fram til neste steg.

    Rene kommentarlinjer strippes: et steg etterfølges i denne workflowen av
    den STORE forklarings-kommentaren som hører til NESTE steg (se
    `--allowedTools`-historikken over "Run Claude Code"), og den nevner
    f.eks. `git merge`/`gh pr merge` som noe som bevisst IKKE finnes. Uten
    strippingen ville kontrakt-testene under lest naboens kommentar som om
    det var dette stegets egen kode.
    """
    m = re.search(
        r"\n      - name: [^\n]*\n(?:(?!\n      - name: ).)*?id: "
        + re.escape(steg_id)
        + r"\n(?:(?!\n      - name: ).)*",
        tekst,
        re.S,
    )
    assert m, f"fant ikke steg med id {steg_id!r} i workflowen"
    linjer = [l for l in m.group(0).splitlines() if not l.lstrip().startswith("#")]
    return "\n".join(linjer)


class TestHappyPath(unittest.TestCase):
    """Akseptansepunkt A."""

    def test_a_gyldig_kontekst_returneres(self):
        ok, kontekst, grunn = _bygg()
        self.assertTrue(ok, grunn)
        self.assertIsNotNone(kontekst)
        self.assertEqual(kontekst["pr_number"], "328")
        self.assertEqual(kontekst["head_sha"], HEAD)
        self.assertEqual(kontekst["branch"], BRANCH)
        self.assertEqual(kontekst["base"], "master")
        self.assertEqual(kontekst["review_id"], "5252972553")
        self.assertEqual(kontekst["review_author"], EIER)
        self.assertEqual(kontekst["issue"], "327")

    def test_a2_konteksten_barer_selve_review_bodyen(self):
        ok, kontekst, _ = _bygg()
        self.assertTrue(ok)
        self.assertIn("pre-selected answer", kontekst["review_body"])

    def test_a3_en_kommentar_review_gjor_ikke_changes_requested_ugyldig(self):
        # COMMENTED er ingen beslutning -- en oppfølgingskommentar fra Chief
        # etter selve reviewen skal ikke blokkere runden.
        reviews = [
            _review(),
            _review(id=999, state="COMMENTED", body="en kort kommentar",
                    submitted_at="2026-09-18T22:10:00Z"),
        ]
        ok, kontekst, grunn = _bygg(reviews=reviews)
        self.assertTrue(ok, grunn)
        self.assertEqual(kontekst["review_id"], "5252972553")


class TestFailClosed(unittest.TestCase):
    """Akseptansepunkt B-I."""

    def test_b_ingen_pr(self):
        ok, kontekst, grunn = _bygg(prs=[])
        self.assertFalse(ok)
        self.assertIsNone(kontekst)
        self.assertIn("ingen åpen PR", grunn)

    def test_b2_kun_lukket_pr_teller_ikke(self):
        ok, _, grunn = _bygg(prs=[_pr(state="CLOSED")])
        self.assertFalse(ok)
        self.assertIn("ingen åpen PR", grunn)

    def test_c_flere_tvetydige_prer(self):
        ok, kontekst, grunn = _bygg(prs=[_pr(), _pr(number=333)])
        self.assertFalse(ok)
        self.assertIsNone(kontekst)
        self.assertIn("tvetydig", grunn)

    def test_d_feil_base(self):
        ok, _, grunn = _bygg(prs=[_pr(baseRefName="develop")])
        self.assertFalse(ok)
        self.assertIn("avviker", grunn)

    def test_d2_feil_head_branch(self):
        ok, _, grunn = _bygg(prs=[_pr(headRefName="agent/issue-999")])
        self.assertFalse(ok)
        self.assertIn("avviker", grunn)

    def test_e_head_sha_mismatch(self):
        ok, kontekst, grunn = _bygg(prs=[_pr(headRefOid=ANNET_HODE)])
        self.assertFalse(ok)
        self.assertIsNone(kontekst)
        self.assertIn("hode har endret seg", grunn)

    def test_e2_pr_identitet_endret(self):
        ok, _, grunn = _bygg(before_pr_number="999")
        self.assertFalse(ok)
        self.assertIn("PR-identiteten endret seg", grunn)

    def test_e3_ufullstendig_pre_run_head_avvises(self):
        ok, _, grunn = _bygg(before_head_sha="6699b63")
        self.assertFalse(ok)
        self.assertIn("40-tegns", grunn)

    def test_e4_manglende_pre_run_tilstand_avvises(self):
        for felt in ("before_pr_number", "before_head_sha"):
            with self.subTest(felt=felt):
                ok, _, grunn = _bygg(**{felt: None})
                self.assertFalse(ok)
                self.assertIn("FØR denne kjøringen", grunn)

    # Chief-review-fiks (PR #330, blokkerende funn): Draft må RE-BEVISES her.
    # Issue #44-porten kjører FØR disse #329-stegene, så en PR som blir satt
    # Ready i mellomtiden ville ellers passert og latt Claude kjøre -- og
    # runden ville mistet Draft -> Ready-vekkesignalet som trigger Chiefs
    # re-review (pr_ready_handoff.py ville sett `already_ready`).

    def test_e5_ready_pr_avvises_selv_om_alt_annet_er_gyldig(self):
        ok, kontekst, grunn = _bygg(prs=[_pr(isDraft=False)])
        self.assertFalse(ok, "en Ready PR må avvises fail-closed")
        self.assertIsNone(kontekst)
        self.assertIn("ikke bekreftet Draft", grunn)

    def test_e6_manglende_isdraft_felt_avvises_likt_som_false(self):
        pr = _pr()
        del pr["isDraft"]
        ok, kontekst, grunn = _bygg(prs=[pr])
        self.assertFalse(ok, "manglende isDraft må behandles som ikke-bevist")
        self.assertIsNone(kontekst)
        self.assertIn("ikke bekreftet Draft", grunn)

    def test_e7_truthy_men_ikke_true_isdraft_avvises(self):
        # Kun ekte boolsk True teller -- ingen "true"-strenger eller 1-ere,
        # slik at en endret API-form ikke stille kan passere porten.
        for verdi in ("true", "True", 1, [], {}, None):
            with self.subTest(verdi=verdi):
                ok, _, grunn = _bygg(prs=[_pr(isDraft=verdi)])
                self.assertFalse(ok)
                self.assertIn("ikke bekreftet Draft", grunn)

    def test_e8_draft_avvisning_skrives_aldri_som_verifisert_kontekst(self):
        # Fail-closed betyr også: ingen handoff-fil, ingen review_body_path.
        data = {
            "trigger_label": "status:changes-requested",
            "issue": "327", "branch": BRANCH,
            "before_pr_number": "328", "before_head_sha": HEAD,
            "repo_owner": EIER,
            "prs": [_pr(isDraft=False)], "reviews": [_review()],
        }
        with tempfile.TemporaryDirectory() as td:
            sti = os.path.join(td, ".agent_bridge_run", "chief_review.md")
            p = subprocess.run(
                [sys.executable, _SCRIPT, "verify"],
                input=json.dumps(data), capture_output=True, text=True,
                env=dict(os.environ, CONTEXT_BODY_PATH=sti),
            )
            self.assertEqual(p.returncode, 1, "Ready PR må gi fail-closed exit 1")
            self.assertIn("context_verified=false", p.stdout)
            self.assertNotIn("review_body_path=", p.stdout)
            self.assertFalse(os.path.exists(sti))

    def test_f_ingen_changes_requested_review(self):
        ok, kontekst, grunn = _bygg(reviews=[])
        self.assertFalse(ok)
        self.assertIsNone(kontekst)
        self.assertIn("Ingen review fra autorisert Chief-identitet", grunn)

    def test_f2_kun_kommentar_reviews_er_ingen_arbeidsordre(self):
        ok, _, grunn = _bygg(reviews=[_review(state="COMMENTED")])
        self.assertFalse(ok)
        self.assertIn("ingen beslutnings-review", grunn)

    def test_g_changes_requested_fra_feil_author(self):
        ok, kontekst, grunn = _bygg(reviews=[_review(user={"login": "en-annen"})])
        self.assertFalse(ok)
        self.assertIsNone(kontekst)
        self.assertIn("Ingen review fra autorisert Chief-identitet", grunn)
        self.assertIn("en-annen", grunn)

    def test_g2_en_annen_forfatter_kan_ikke_overstyre_eierens_approved(self):
        reviews = [
            _review(id=1, state="APPROVED", submitted_at="2026-09-18T20:00:00Z"),
            _review(id=2, user={"login": "en-annen"},
                    submitted_at="2026-09-18T21:54:34Z"),
        ]
        ok, _, grunn = _bygg(reviews=reviews)
        self.assertFalse(ok)
        self.assertIn("APPROVED", grunn)

    def test_h_review_commit_er_ikke_eksakt_head(self):
        ok, kontekst, grunn = _bygg(reviews=[_review(commit_id=ANNET_HODE)])
        self.assertFalse(ok)
        self.assertIsNone(kontekst)
        self.assertIn("ikke PR-ens eksakte nåværende head", grunn)

    def test_h2_manglende_commit_id_avvises(self):
        ok, _, grunn = _bygg(reviews=[_review(commit_id=None)])
        self.assertFalse(ok)
        self.assertIn("ikke PR-ens eksakte nåværende head", grunn)

    def test_i_nyere_approved_gjor_changes_requested_stale(self):
        reviews = [
            _review(),
            _review(id=777, state="APPROVED", body="ok nå",
                    submitted_at="2026-09-18T23:00:00Z"),
        ]
        ok, kontekst, grunn = _bygg(reviews=reviews)
        self.assertFalse(ok)
        self.assertIsNone(kontekst)
        self.assertIn("foreldet", grunn)

    def test_i2_nyere_dismissed_gjor_changes_requested_stale(self):
        reviews = [
            _review(),
            _review(id=778, state="DISMISSED", body="",
                    submitted_at="2026-09-18T23:00:00Z"),
        ]
        ok, _, grunn = _bygg(reviews=reviews)
        self.assertFalse(ok)
        self.assertIn("foreldet", grunn)

    def test_i3_nyere_changes_requested_vinner_over_eldre(self):
        reviews = [
            _review(id=1, body="gammel runde", submitted_at="2026-09-17T10:00:00Z"),
            _review(id=2, body="nyeste arbeidsordre", submitted_at="2026-09-18T21:54:34Z"),
        ]
        ok, kontekst, grunn = _bygg(reviews=reviews)
        self.assertTrue(ok, grunn)
        self.assertEqual(kontekst["review_id"], "2")
        self.assertEqual(kontekst["review_body"], "nyeste arbeidsordre")

    def test_tom_review_body_avvises(self):
        ok, _, grunn = _bygg(reviews=[_review(body="   \n  ")])
        self.assertFalse(ok)
        self.assertIn("tom body", grunn)

    def test_manglende_repo_owner_avvises(self):
        ok, _, grunn = _bygg(repo_owner=None)
        self.assertFalse(ok)
        self.assertIn("autorisert Chief-identitet er ikke oppgitt", grunn)

    def test_manglende_branch_navn_avvises(self):
        ok, _, grunn = _bygg(branch_navn=None)
        self.assertFalse(ok)
        self.assertIn("Deterministisk branch-navn mangler", grunn)


class TestStatusReadyUpavirket(unittest.TestCase):
    """Akseptansepunkt L -- porten må ikke røre den ferske banen."""

    def test_l_status_ready_er_ikke_paakrevd(self):
        ok, kontekst, grunn = _bygg(trigger_label="status:ready", prs=[], reviews=[])
        self.assertTrue(ok)
        self.assertIsNone(kontekst)
        self.assertIn("ikke en forutsetning", grunn)

    def test_l2_tom_trigger_etikett_er_heller_ikke_paakrevd(self):
        ok, kontekst, _ = _bygg(trigger_label="", prs=[], reviews=[])
        self.assertTrue(ok)
        self.assertIsNone(kontekst)

    def test_l4_draft_kravet_lekker_ikke_inn_i_status_ready(self):
        # Chief-review-fiks (PR #330): det nye isDraft-kravet gjelder KUN
        # changes-requested. En status:ready-runde med en Ready PR i
        # tilstanden skal fortsatt være et ikke-alarmerende "ikke påkrevd".
        ok, kontekst, grunn = _bygg(
            trigger_label="status:ready", prs=[_pr(isDraft=False)], reviews=[],
        )
        self.assertTrue(ok, grunn)
        self.assertIsNone(kontekst)
        self.assertIn("ikke en forutsetning", grunn)

    def test_l3_checkout_verifisering_er_ikke_paakrevd_for_status_ready(self):
        ok, grunn = crc.verifiser_lokalt_hode(
            trigger_label="status:ready", expected_head="", local_head="",
            branch_navn=None, local_branch=None,
        )
        self.assertTrue(ok)
        self.assertIn("ikke en forutsetning", grunn)


class TestCheckoutVerifisering(unittest.TestCase):
    """Akseptansepunkt K -- wrapperen, ikke Claude, eier branch-oppsettet."""

    def _kall(self, **overstyr):
        kwargs = {
            "trigger_label": "status:changes-requested",
            "expected_head": HEAD,
            "local_head": HEAD,
            "branch_navn": BRANCH,
            "local_branch": BRANCH,
        }
        kwargs.update(overstyr)
        return crc.verifiser_lokalt_hode(**kwargs)

    def test_k_riktig_branch_pa_eksakt_head_godkjennes(self):
        ok, grunn = self._kall()
        self.assertTrue(ok, grunn)
        self.assertIn("klargjort på eksakt verifisert head", grunn)

    def test_k2_feil_lokal_head_avvises(self):
        ok, grunn = self._kall(local_head=ANNET_HODE)
        self.assertFalse(ok)
        self.assertIn("står ikke på det eksakte hodet", grunn)

    def test_k3_fortsatt_pa_master_avvises(self):
        # Nøyaktig hendelses-tilstanden: actions/checkout lander på master.
        ok, grunn = self._kall(local_head=ANNET_HODE, local_branch="master")
        self.assertFalse(ok)

    def test_k4_riktig_head_men_feil_branch_avvises(self):
        ok, grunn = self._kall(local_branch="master")
        self.assertFalse(ok)
        self.assertIn("ikke den deterministiske", grunn)

    def test_k5_detached_head_avvises(self):
        ok, grunn = self._kall(local_branch="HEAD")
        self.assertFalse(ok)

    def test_k6_ufullstendige_shaer_avvises(self):
        for felt in ("expected_head", "local_head"):
            with self.subTest(felt=felt):
                ok, grunn = self._kall(**{felt: "6699b63"})
                self.assertFalse(ok)
                self.assertIn("40-tegns", grunn)


class TestReviewTransport(unittest.TestCase):
    """Akseptansepunkt J -- fiendtlig review-body skal transporteres som
    DATA, aldri som shell."""

    FIENDTLIG = (
        "Line one with `backticks` and 'single' and \"double\" quotes.\n"
        "$(touch /tmp/pwned_by_review_body)\n"
        "`touch /tmp/pwned_by_backtick`\n"
        "; rm -rf / ; echo done\n"
        "${{ github.token }}\n"
        "EOF\n"
        "  - name: injected step\n"
        "    run: echo nope\n"
        "%0Aset-output name=x::y\n"
        "Slutt: ✅ æøå — multiline bevart.\n"
    )

    def test_j_fiendtlig_body_skrives_ordrett_til_fil(self):
        ok, kontekst, grunn = _bygg(reviews=[_review(body=self.FIENDTLIG)])
        self.assertTrue(ok, grunn)
        with tempfile.TemporaryDirectory() as td:
            sti = os.path.join(td, ".agent_bridge_run", "chief_review.md")
            crc.skriv_review_fil(kontekst, sti)
            with open(sti, encoding="utf-8") as f:
                innhold = f.read()
        # Ordrett bevart -- ingen escaping, ingen evaluering, ingen tap.
        self.assertIn(self.FIENDTLIG.strip(), innhold)
        self.assertIn("$(touch /tmp/pwned_by_review_body)", innhold)
        self.assertIn("${{ github.token }}", innhold)
        self.assertIn("æøå", innhold)
        # Verifisert, strukturell overskrift.
        self.assertIn(f"`{HEAD}`", innhold)
        self.assertIn("#328", innhold)

    def test_j2_cli_skriver_filen_og_aldri_bodyen_til_github_output(self):
        data = {
            "trigger_label": "status:changes-requested",
            "issue": "327",
            "branch": BRANCH,
            "before_pr_number": "328",
            "before_head_sha": HEAD,
            "repo_owner": EIER,
            "prs": [_pr()],
            "reviews": [_review(body=self.FIENDTLIG)],
        }
        with tempfile.TemporaryDirectory() as td:
            sti = os.path.join(td, ".agent_bridge_run", "chief_review.md")
            env = dict(os.environ, CONTEXT_BODY_PATH=sti)
            p = subprocess.run(
                [sys.executable, _SCRIPT, "verify"],
                input=json.dumps(data), capture_output=True, text=True, env=env, cwd=td,
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertTrue(os.path.exists(sti))
            with open(sti, encoding="utf-8") as f:
                self.assertIn("$(touch /tmp/pwned_by_review_body)", f.read())

        # Ingen del av review-bodyen -- og ingen ekstra linje overhodet --
        # kommer ut på stdout (som workflowen appender til $GITHUB_OUTPUT).
        for linje in p.stdout.splitlines():
            self.assertRegex(linje, r"^[a-z_]+=", f"ikke en key=value-linje: {linje!r}")
            self.assertNotIn("pwned", linje)
            self.assertNotIn("rm -rf", linje)
        self.assertIn(f"head_sha={HEAD}", p.stdout)
        self.assertIn(f"review_body_path={sti}", p.stdout)

        # Sabotasje-bevis: hadde bodyen blitt evaluert som shell, ville
        # disse filene eksistert.
        self.assertFalse(os.path.exists("/tmp/pwned_by_review_body"))
        self.assertFalse(os.path.exists("/tmp/pwned_by_backtick"))

    def test_j3_reason_linjen_er_alltid_en_enkelt_linje(self):
        ok, _, grunn = _bygg(reviews=[_review(body=self.FIENDTLIG)])
        self.assertTrue(ok)
        for tilfelle in ([], [_pr(), _pr(number=9)], [_pr(headRefOid=ANNET_HODE)]):
            _, _, g = _bygg(prs=tilfelle)
            self.assertNotIn("\n", g)


class TestCliKontrakt(unittest.TestCase):
    """Exit-kode-kontrakten -- samme som pr_draft_handoff.py/
    chief_ready_signal.py, slik at et feilende steg stopper jobben FØR
    "Run Claude Code"."""

    def _verify(self, data, **env_overstyr):
        env = dict(os.environ)
        env.update(env_overstyr)
        return subprocess.run(
            [sys.executable, _SCRIPT, "verify"],
            input=json.dumps(data), capture_output=True, text=True, env=env,
        )

    def test_cli_exit_1_ved_reell_avvisning(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._verify(
                {"trigger_label": "status:changes-requested", "branch": BRANCH,
                 "before_pr_number": "328", "before_head_sha": HEAD,
                 "repo_owner": EIER, "prs": [], "reviews": []},
                CONTEXT_BODY_PATH=os.path.join(td, "cr.md"),
            )
        self.assertEqual(p.returncode, 1)
        self.assertIn("context_verified=false", p.stdout)
        self.assertNotIn("review_body_path=", p.stdout)

    def test_cli_exit_0_for_status_ready_uten_a_skrive_fil(self):
        with tempfile.TemporaryDirectory() as td:
            sti = os.path.join(td, "cr.md")
            p = self._verify(
                {"trigger_label": "status:ready", "branch": BRANCH},
                CONTEXT_BODY_PATH=sti,
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("context_verified=true", p.stdout)
            self.assertFalse(os.path.exists(sti))

    def test_cli_tom_eller_ugyldig_stdin_er_fail_closed(self):
        for raa in ("", "ikke json", "[]"):
            with self.subTest(raa=raa):
                p = subprocess.run(
                    [sys.executable, _SCRIPT, "verify"],
                    input=raa, capture_output=True, text=True,
                )
                # Tom/ugyldig input gir tom trigger_label -> "ikke påkrevd".
                # Det er trygt: uten en changes-requested-trigger finnes det
                # ingen review-kontekst å bevise, og ingen fil skrives.
                self.assertEqual(p.returncode, 0)
                self.assertNotIn("review_body_path=", p.stdout)

    def test_checkout_verify_cli_exit_koder(self):
        felles = dict(os.environ, TRIGGER_LABEL="status:changes-requested",
                      BRANCH=BRANCH, LOCAL_BRANCH=BRANCH, EXPECTED_HEAD=HEAD)
        ok = subprocess.run([sys.executable, _SCRIPT, "checkout-verify"],
                            capture_output=True, text=True,
                            env=dict(felles, LOCAL_HEAD=HEAD))
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("checkout_verified=true", ok.stdout)

        feil = subprocess.run([sys.executable, _SCRIPT, "checkout-verify"],
                              capture_output=True, text=True,
                              env=dict(felles, LOCAL_HEAD=ANNET_HODE))
        self.assertEqual(feil.returncode, 1)
        self.assertIn("checkout_verified=false", feil.stdout)

    def test_ukjent_modus_avvises(self):
        p = subprocess.run([sys.executable, _SCRIPT, "tull"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


class TestWorkflowKobling(unittest.TestCase):
    """Statisk kontrakt mot selve workflowen -- at den PURE modulen er
    riktig innkoblet, i riktig rekkefølge, uten ny farlig overflate."""

    def setUp(self):
        self.tekst = _les_workflow()

    def test_alle_fire_stegene_finnes(self):
        for steg_id in ("cr_state", "cr_context", "cr_branch", "cr_checkout"):
            with self.subTest(steg_id=steg_id):
                self.assertIn(f"id: {steg_id}\n", self.tekst)

    def test_rekkefolge_etter_draft_verify_for_claude(self):
        i_draft = self.tekst.index("id: draft_verify")
        i_state = self.tekst.index("id: cr_state")
        i_context = self.tekst.index("id: cr_context")
        i_branch = self.tekst.index("id: cr_branch")
        i_checkout = self.tekst.index("id: cr_checkout")
        i_claude = self.tekst.index("id: claude")
        self.assertLess(i_draft, i_state)
        self.assertLess(i_state, i_context)
        self.assertLess(i_context, i_branch)
        self.assertLess(i_branch, i_checkout)
        self.assertLess(i_checkout, i_claude, "verifiseringen MÅ stå før Run Claude Code")

    def test_verifiseringen_kaller_den_pure_modulen(self):
        blokk = _steg_blokk(self.tekst, "cr_context")
        self.assertIn("changes_requested_context.py verify", blokk)
        self.assertIn('>> "$GITHUB_OUTPUT"', blokk)

    def test_checkout_verifiseringen_kaller_den_pure_modulen(self):
        blokk = _steg_blokk(self.tekst, "cr_checkout")
        self.assertIn("changes_requested_context.py checkout-verify", blokk)

    def test_branch_klargjoringen_checkouter_eksakt_verifisert_head(self):
        blokk = _steg_blokk(self.tekst, "cr_branch")
        self.assertIn("steps.cr_context.outputs.head_sha", blokk)
        self.assertIn('git checkout -B "$BRANCH" "$EXPECTED_HEAD"', blokk)
        self.assertIn("git rev-parse HEAD", blokk)
        # Ingen destruktive operasjoner mot arbeidstreet.
        for forbudt in ("git reset --hard", "git clean", "git rebase", "--force"):
            self.assertNotIn(forbudt, blokk, f"{forbudt!r} hører ikke hjemme her")

    def test_branch_stegene_er_scopet_til_changes_requested(self):
        for steg_id in ("cr_branch", "cr_checkout"):
            with self.subTest(steg_id=steg_id):
                blokk = _steg_blokk(self.tekst, steg_id)
                self.assertIn(
                    "needs.guard.outputs.trigger_label == 'status:changes-requested'",
                    blokk,
                    "status:ready må ikke berøres av branch-klargjøringen",
                )

    def test_review_body_gar_aldri_gjennom_et_shell_kommandoargument(self):
        blokk = _steg_blokk(self.tekst, "cr_state")
        # Tilstanden settes sammen med --slurpfile fra FILER, aldri fra en
        # shell-variabel som har holdt review-teksten.
        self.assertIn("--slurpfile reviews", blokk)
        self.assertNotIn("--argjson reviews", blokk)
        self.assertNotIn("$(gh api", blokk.replace("$(git", ""))
        self.assertNotIn("REVIEW_BODY", self.tekst)

    def test_reviews_hentes_fra_reviews_apiet_ikke_kommentarer(self):
        blokk = _steg_blokk(self.tekst, "cr_state")
        self.assertIn("/reviews", blokk)
        self.assertNotIn("/comments", blokk)

    def test_repo_owner_er_den_autoriserte_chief_identiteten(self):
        blokk = _steg_blokk(self.tekst, "cr_state")
        self.assertIn("REPO_OWNER: ${{ github.repository_owner }}", blokk)

    def test_ingen_ny_merge_eller_master_push_overflate(self):
        for steg_id in ("cr_state", "cr_context", "cr_branch", "cr_checkout"):
            blokk = _steg_blokk(self.tekst, steg_id)
            for forbudt in ("gh pr merge", "git merge", "git push"):
                self.assertNotIn(forbudt, blokk, f"{forbudt!r} i steg {steg_id}")

    def test_prompten_gir_claude_den_verifiserte_konteksten_direkte(self):
        for uttrykk in (
            "steps.cr_context.outputs.pr_number",
            "steps.cr_context.outputs.head_sha",
            "steps.cr_context.outputs.review_id",
            "steps.cr_context.outputs.review_author",
            ".agent_bridge_run/chief_review.md",
        ):
            with self.subTest(uttrykk=uttrykk):
                self.assertIn(uttrykk, self.tekst)

    def test_prompten_ber_ikke_lenger_claude_finne_pr_en_selv(self):
        self.assertNotIn(
            "to find its PR", self.tekst,
            "changes-requested-prompten skal ikke lenger be Claude gjenoppdage PR-en",
        )
        self.assertNotIn(
            "Read the latest Chief review on that PR", self.tekst,
            "reviewen leveres nå verifisert, den skal ikke gjenoppdages",
        )

    def test_handoff_filen_er_git_ignorert(self):
        with open(_GITIGNORE, encoding="utf-8") as f:
            self.assertIn(".agent_bridge_run/", f.read())


if __name__ == "__main__":
    unittest.main()
