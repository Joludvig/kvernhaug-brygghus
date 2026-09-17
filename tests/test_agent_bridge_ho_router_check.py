"""
Kvernhaug Agent Bridge -- regresjonstester for HO router-freshness-sjekken
(.github/scripts/ho_router_check.py, issue #252).

BAKGRUNN: #252 dokumenterte at #152s router-pointer kunne bli stille
foreldet -- en nyere gyldig `KBH_COS_LIVE_CHECKPOINT_V1`-kommentar fantes
på mål-issuen (#196), mens #152s nyeste `KBH_COS_CHECKPOINT_PTR_V1`-linje
fortsatt pekte til en eldre. Se ho_router_check.py sin moduldocstring for
det fulle resonnementet -- denne testfilen bruker de FAKTISKE, live
kommentar-ID-ene fra hendelsen (hentet 2026-09-13 via GitHub API) som
regresjonsdata, slik at testen beviser modulen faktisk fanger den samme
klassen hendelse den ble skrevet for, ikke bare en syntetisk analog.

Testene dekker:
  1. `nyeste_gyldig_pointer` velger korrekt den nyeste (størst
     kilde-kommentar-ID) gyldige pointer-linja, og ignorerer siterte/
     midt-i-linja/nesten-like varianter -- samme sitat-immunitet som
     chief_ready_signal.py allerede beviser for sin egen markør.
  2. `gyldige_sjekkpunkt_id_er` finner alle gyldige sjekkpunkt-kommentarer
     og ignorerer siterte/embedded varianter.
  3. `sjekk_router` gir OK når pointeren peker til det nyeste gyldige
     sjekkpunktet (den FAKTISKE, reparerte live-tilstanden 2026-09-13:
     #152 kommentar 5654816841 -> #196 kommentar 5654816412).
  4. `sjekk_router` gir ORPHAN når et nyere gyldig sjekkpunkt finnes enn
     det pointeren peker til -- gjenskaper #252s EKSAKTE dokumenterte
     hendelse (pointer pekte til #196 kommentar 5648254902, mens et
     nyere gyldig sjekkpunkt, kommentar 5648280519, allerede fantes).
  5. `sjekk_router` gir NO_POINTER / INVALID_TARGET / POINTER_ISSUE_MISMATCH
     fail-closed på hvert av sine respektive uklarhets-tilfeller.
  6. CLI-kontrakten (`pointer`- og `verify`-modus): riktige GITHUB_OUTPUT-
     linjer og riktig exit-kode (0 kun for et positivt funn/OK, 1 ellers).

Ren stdlib-test, ingen GitHub-kall -- kjøres av den vanlige suiten
(`py -3 -m unittest discover -s tests`).
"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".github", "scripts"))

import ho_router_check as hrc  # noqa: E402


# ─── Syntetiske #152-kommentarer, modellert på policyens egne eksempler ────

_POINTER_KOMMENTARER_TOMT = []

_POINTER_KOMMENTARER_ENKEL = [
    {"id": 100, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=555"},
]

_POINTER_KOMMENTARER_FLERE = [
    {"id": 100, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=111"},
    {"id": 200, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=222"},
    {"id": 150, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=333"},
]

_POINTER_KOMMENTARER_SITAT_OG_STOY = [
    {"id": 50, "body": "> KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=999 (sitert, skal ignoreres)"},
    {"id": 60, "body": "Ikke bruk KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=888 midt i en setning."},
    {"id": 70, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=777 ekstra tekst på samme linje"},
    {"id": 80, "body": "kbh_cos_checkpoint_ptr_v1 issue=196 comment=666"},
]

# ─── Faktiske, live kommentar-ID-er fra issue #252s hendelse (2026-09-12/13,
# hentet via GitHub API) -- se ho_router_check.py moduldocstring. ───────────

_LIVE_196_SJEKKPUNKTER_UNDER_HENDELSEN = [
    {"id": 5647709144, "body": "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT — 2026-09-12 ..."},
    {"id": 5648254902, "body": "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT — 2026-09-12 ..."},
    {"id": 5648280519, "body": "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT — 2026-09-12 ..."},
]

_LIVE_152_POINTER_UNDER_HENDELSEN = [
    {"id": 5647710789, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=5647709144"},
    {"id": 5648256776, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=5648254902"},
]

_LIVE_196_SJEKKPUNKTER_FERSK = _LIVE_196_SJEKKPUNKTER_UNDER_HENDELSEN + [
    {"id": 5654816412, "body": "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT — 2026-09-13 ..."},
]

_LIVE_152_POINTER_FERSK = _LIVE_152_POINTER_UNDER_HENDELSEN + [
    {"id": 5654816841, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=5654816412"},
]


class TestNyesteGyldigPointer(unittest.TestCase):
    def test_1a_ingen_kommentarer_gir_none(self):
        self.assertIsNone(hrc.nyeste_gyldig_pointer(_POINTER_KOMMENTARER_TOMT))

    def test_1b_en_gyldig_linje(self):
        pointer = hrc.nyeste_gyldig_pointer(_POINTER_KOMMENTARER_ENKEL)
        self.assertEqual(pointer, {"issue": 196, "comment": 555, "kilde_id": 100})

    def test_1c_velger_nyeste_via_storst_kommentar_id_ikke_listerekkefolge(self):
        pointer = hrc.nyeste_gyldig_pointer(_POINTER_KOMMENTARER_FLERE)
        # kommentar-ID 200 er størst, selv om den ikke står sist i input-lista.
        self.assertEqual(pointer, {"issue": 196, "comment": 222, "kilde_id": 200})

    def test_1d_siterte_midt_i_linja_og_feil_case_varianter_ignoreres(self):
        self.assertIsNone(hrc.nyeste_gyldig_pointer(_POINTER_KOMMENTARER_SITAT_OG_STOY))

    def test_1e_live_hendelses_pointer_under_regresjon_velger_eldste_reelle(self):
        pointer = hrc.nyeste_gyldig_pointer(_LIVE_152_POINTER_UNDER_HENDELSEN)
        self.assertEqual(pointer, {"issue": 196, "comment": 5648254902, "kilde_id": 5648256776})

    def test_1f_live_pointer_etter_reparasjon_velger_den_ferske(self):
        pointer = hrc.nyeste_gyldig_pointer(_LIVE_152_POINTER_FERSK)
        self.assertEqual(pointer, {"issue": 196, "comment": 5654816412, "kilde_id": 5654816841})


class TestMarkorHerdingIssue301(unittest.TestCase):
    """Fokuserte regresjonstester for de fire audit-hullene issue #301
    lukket i selve markør-parsingen (CRLF, fenced kodeblokker, tvetydige
    doble markør-linjer for hhv. pointer og sjekkpunkt). Se
    ho_router_check.py sin moduldocstring, avsnittet "HERDING (issue
    #301)", for det fulle resonnementet."""

    def test_6a_pointer_linje_med_crlf_linjeskift_godtas(self):
        kommentarer = [
            {"id": 100, "body": "noe innledende tekst\r\nKBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=555\r\nmer tekst"},
        ]
        pointer = hrc.nyeste_gyldig_pointer(kommentarer)
        self.assertEqual(pointer, {"issue": 196, "comment": 555, "kilde_id": 100})

    def test_6b_sjekkpunkt_linje_med_crlf_linjeskift_godtas(self):
        kommentarer = [
            {"id": 3, "body": "innledning\r\nKBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT -- gyldig\r\n"},
        ]
        self.assertEqual(hrc.gyldige_sjekkpunkt_id_er(kommentarer), [3])

    def test_6c_pointer_linje_inni_fenced_kodeblokk_ignoreres(self):
        kommentarer = [
            {
                "id": 100,
                "body": (
                    "Eksempel på hvordan en pointer-linje ser ut:\n"
                    "```\n"
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=999\n"
                    "```\n"
                    "(ingen reell pointer i denne kommentaren)"
                ),
            },
        ]
        self.assertIsNone(hrc.nyeste_gyldig_pointer(kommentarer))

    def test_6d_sjekkpunkt_linje_inni_fenced_kodeblokk_ignoreres(self):
        kommentarer = [
            {
                "id": 1,
                "body": (
                    "Eksempel:\n"
                    "~~~\n"
                    "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT -- kun eksempel\n"
                    "~~~\n"
                ),
            },
        ]
        self.assertEqual(hrc.gyldige_sjekkpunkt_id_er(kommentarer), [])

    def test_6e_fenced_kodeblokk_skjuler_ikke_en_reell_linje_utenfor_blokken(self):
        kommentarer = [
            {
                "id": 100,
                "body": (
                    "```\n"
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=999\n"
                    "```\n"
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=555\n"
                ),
            },
        ]
        pointer = hrc.nyeste_gyldig_pointer(kommentarer)
        self.assertEqual(pointer, {"issue": 196, "comment": 555, "kilde_id": 100})

    def test_6f_to_aktive_pointer_linjer_i_samme_kommentar_avvises_som_tvetydig(self):
        kommentarer = [
            {"id": 100, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=111\nKBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=222"},
        ]
        self.assertIsNone(hrc.nyeste_gyldig_pointer(kommentarer))

    def test_6g_tvetydig_kommentar_hindrer_ikke_en_annen_gyldig_kommentar_fra_a_vinne(self):
        kommentarer = [
            {"id": 100, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=111\nKBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=222"},
            {"id": 50, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=333"},
        ]
        pointer = hrc.nyeste_gyldig_pointer(kommentarer)
        self.assertEqual(pointer, {"issue": 196, "comment": 333, "kilde_id": 50})

    def test_6h_to_aktive_sjekkpunkt_linjer_i_samme_kommentar_avvises_som_tvetydig(self):
        kommentarer = [
            {
                "id": 3,
                "body": (
                    "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT -- forste\n"
                    "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT -- andre\n"
                ),
            },
        ]
        self.assertEqual(hrc.gyldige_sjekkpunkt_id_er(kommentarer), [])

    def test_6i_tvetydig_sjekkpunkt_kommentar_hindrer_ikke_andre_gyldige(self):
        kommentarer = [
            {
                "id": 3,
                "body": (
                    "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT -- forste\n"
                    "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT -- andre\n"
                ),
            },
            {"id": 4, "body": "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT -- gyldig"},
        ]
        self.assertEqual(hrc.gyldige_sjekkpunkt_id_er(kommentarer), [4])

    def test_6j_ambigu_pointer_kommentar_gir_no_pointer_via_sjekk_router(self):
        status, pointer, begrunnelse = hrc.sjekk_router(
            pointer_kommentarer=[
                {"id": 100, "body": "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=111\nKBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=222"},
            ],
            target_issue_nummer=196,
            target_kommentarer=_LIVE_196_SJEKKPUNKTER_FERSK,
        )
        self.assertEqual(status, "NO_POINTER")
        self.assertIsNone(pointer)

    # ─── Runde 2 (Chief-blocker): closing-fence-semantikk i
    # `_uten_fenced_kodeblokker` selv -- en closer må ha samme fence-tegn
    # som åpneren, closer-lengde >= åpner-lengde, og kun whitespace etter
    # fence-tegnene. Se ho_router_check.py, "HERDING (issue #301, runde 2)".

    def test_6k_fire_backtick_opener_lukkes_ikke_av_tre_backtick_pseudo_closer(self):
        kommentarer = [
            {
                "id": 100,
                "body": (
                    "````\n"
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=999\n"
                    "```\n"  # for kort (3 < 4) -- lukker IKKE fire-backtick-fencen
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=888\n"
                    "````\n"  # faktisk gyldig closer (samme tegn, lengde 4 >= 4)
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=555\n"
                ),
            },
        ]
        pointer = hrc.nyeste_gyldig_pointer(kommentarer)
        self.assertEqual(pointer, {"issue": 196, "comment": 555, "kilde_id": 100})

    def test_6l_samme_tegn_pseudo_closer_med_trailing_tekst_lukker_ikke_blokken(self):
        kommentarer = [
            {
                "id": 100,
                "body": (
                    "```\n"
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=999\n"
                    "``` fortsatt eksempel, ikke en gyldig closer\n"  # info-streng -- ugyldig closer
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=888\n"
                    "```\n"  # faktisk gyldig closer (ingen tekst etter fence-tegnene)
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=555\n"
                ),
            },
        ]
        pointer = hrc.nyeste_gyldig_pointer(kommentarer)
        self.assertEqual(pointer, {"issue": 196, "comment": 555, "kilde_id": 100})

    def test_6m_markor_rett_etter_pseudo_closer_forblir_ignorert_helt_til_kommentarens_slutt(self):
        kommentarer = [
            {
                "id": 5,
                "body": (
                    "````\n"
                    "``` (for kort til å lukke fire-backtick-fencen ovenfor)\n"
                    "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT -- fortsatt inni blokken\n"
                ),
            },
        ]
        # Blokken har ingen gyldig closer i det hele tatt her -- markøren
        # rett etter pseudo-closeren skal derfor aldri telle som aktiv,
        # uavhengig av at den ligner en fence-lukking.
        self.assertEqual(hrc.gyldige_sjekkpunkt_id_er(kommentarer), [])

    def test_6n_gyldig_lengre_closer_med_kun_whitespace_etter_lukker_korrekt(self):
        kommentarer = [
            {
                "id": 100,
                "body": (
                    "```\n"
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=999\n"
                    "````   \n"  # gyldig: lengde 4 >= åpner-lengde 3, kun whitespace etter
                    "KBH_COS_CHECKPOINT_PTR_V1 issue=196 comment=555\n"
                ),
            },
        ]
        pointer = hrc.nyeste_gyldig_pointer(kommentarer)
        self.assertEqual(pointer, {"issue": 196, "comment": 555, "kilde_id": 100})


class TestGyldigeSjekkpunktIder(unittest.TestCase):
    def test_2a_ingen_kommentarer_gir_tom_liste(self):
        self.assertEqual(hrc.gyldige_sjekkpunkt_id_er([]), [])

    def test_2b_finner_alle_gyldige_sortert(self):
        self.assertEqual(
            hrc.gyldige_sjekkpunkt_id_er(_LIVE_196_SJEKKPUNKTER_UNDER_HENDELSEN),
            [5647709144, 5648254902, 5648280519],
        )

    def test_2c_siterte_og_embedded_varianter_ignoreres(self):
        kommentarer = [
            {"id": 1, "body": "> KBH_COS_LIVE_CHECKPOINT_V1 sitert, skal ignoreres"},
            {"id": 2, "body": "ikke KBH_COS_LIVE_CHECKPOINT_V1 midt i en setning"},
            {"id": 3, "body": "KBH_COS_LIVE_CHECKPOINT_V1 CHIEF LIVE CHECKPOINT -- gyldig"},
        ]
        self.assertEqual(hrc.gyldige_sjekkpunkt_id_er(kommentarer), [3])


class TestSjekkRouter(unittest.TestCase):
    def test_3a_ok_nar_pointer_peker_til_nyeste_gyldige_sjekkpunkt(self):
        status, pointer, begrunnelse = hrc.sjekk_router(
            pointer_kommentarer=_LIVE_152_POINTER_FERSK,
            target_issue_nummer=196,
            target_kommentarer=_LIVE_196_SJEKKPUNKTER_FERSK,
        )
        self.assertEqual(status, "OK")
        self.assertEqual(pointer["comment"], 5654816412)
        self.assertIn("fersk", begrunnelse)

    def test_3b_orphan_gjenskaper_issue_252s_eksakte_hendelse(self):
        # Dette ER #252s dokumenterte regresjon: #152s nyeste pointer på det
        # tidspunktet pekte til kommentar 5648254902, mens et nyere gyldig
        # sjekkpunkt (5648280519) allerede fantes på #196.
        status, pointer, begrunnelse = hrc.sjekk_router(
            pointer_kommentarer=_LIVE_152_POINTER_UNDER_HENDELSEN,
            target_issue_nummer=196,
            target_kommentarer=_LIVE_196_SJEKKPUNKTER_UNDER_HENDELSEN,
        )
        self.assertEqual(status, "ORPHAN")
        self.assertEqual(pointer["comment"], 5648254902)
        self.assertIn("5648280519", begrunnelse)
        self.assertIn("#252", begrunnelse)

    def test_3c_no_pointer_nar_152_har_ingen_gyldig_linje(self):
        status, pointer, begrunnelse = hrc.sjekk_router(
            pointer_kommentarer=_POINTER_KOMMENTARER_SITAT_OG_STOY,
            target_issue_nummer=196,
            target_kommentarer=_LIVE_196_SJEKKPUNKTER_FERSK,
        )
        self.assertEqual(status, "NO_POINTER")
        self.assertIsNone(pointer)

    def test_3d_pointer_issue_mismatch_nar_feil_mal_issue_oppgitt(self):
        status, pointer, begrunnelse = hrc.sjekk_router(
            pointer_kommentarer=_LIVE_152_POINTER_FERSK,
            target_issue_nummer=999,
            target_kommentarer=_LIVE_196_SJEKKPUNKTER_FERSK,
        )
        self.assertEqual(status, "POINTER_ISSUE_MISMATCH")
        self.assertEqual(pointer["issue"], 196)

    def test_3e_invalid_target_nar_malet_ikke_finnes_blant_gyldige_sjekkpunkter(self):
        status, pointer, begrunnelse = hrc.sjekk_router(
            pointer_kommentarer=_POINTER_KOMMENTARER_ENKEL,  # peker til comment=555
            target_issue_nummer=196,
            target_kommentarer=_LIVE_196_SJEKKPUNKTER_FERSK,  # 555 finnes ikke her
        )
        self.assertEqual(status, "INVALID_TARGET")

    def test_3f_invalid_target_nar_ingen_gyldige_sjekkpunkter_i_det_hele_tatt(self):
        status, pointer, begrunnelse = hrc.sjekk_router(
            pointer_kommentarer=_LIVE_152_POINTER_FERSK,
            target_issue_nummer=196,
            target_kommentarer=[],
        )
        self.assertEqual(status, "INVALID_TARGET")


class TestCliPointerModus(unittest.TestCase):
    def _kjor(self, payload):
        stdin_backup, stdout_buf, stderr_buf = sys.stdin, io.StringIO(), io.StringIO()
        sys.stdin = io.StringIO(json.dumps(payload))
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exit_code = hrc.main(["ho_router_check.py", "pointer"])
        finally:
            sys.stdin = stdin_backup
        return exit_code, stdout_buf.getvalue()

    def test_4a_funnet_gir_exit_0_og_riktige_output_linjer(self):
        exit_code, out = self._kjor({"comments": _LIVE_152_POINTER_FERSK})
        self.assertEqual(exit_code, 0)
        self.assertIn("pointer_found=true", out)
        self.assertIn("pointer_issue=196", out)
        self.assertIn("pointer_comment=5654816412", out)

    def test_4b_ikke_funnet_gir_exit_1(self):
        exit_code, out = self._kjor({"comments": []})
        self.assertEqual(exit_code, 1)
        self.assertIn("pointer_found=false", out)


class TestCliVerifyModus(unittest.TestCase):
    def _kjor(self, payload):
        stdin_backup, stdout_buf, stderr_buf = sys.stdin, io.StringIO(), io.StringIO()
        sys.stdin = io.StringIO(json.dumps(payload))
        try:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                exit_code = hrc.main(["ho_router_check.py", "verify"])
        finally:
            sys.stdin = stdin_backup
        return exit_code, stdout_buf.getvalue()

    def test_5a_ok_gir_exit_0(self):
        exit_code, out = self._kjor({
            "pointer_comments": _LIVE_152_POINTER_FERSK,
            "target_issue": 196,
            "target_comments": _LIVE_196_SJEKKPUNKTER_FERSK,
        })
        self.assertEqual(exit_code, 0)
        self.assertIn("status=OK", out)

    def test_5b_orphan_gir_exit_1(self):
        exit_code, out = self._kjor({
            "pointer_comments": _LIVE_152_POINTER_UNDER_HENDELSEN,
            "target_issue": 196,
            "target_comments": _LIVE_196_SJEKKPUNKTER_UNDER_HENDELSEN,
        })
        self.assertEqual(exit_code, 1)
        self.assertIn("status=ORPHAN", out)

    def test_5c_manglende_target_issue_gir_exit_1_invalid_target(self):
        exit_code, out = self._kjor({
            "pointer_comments": _LIVE_152_POINTER_FERSK,
            "target_comments": _LIVE_196_SJEKKPUNKTER_FERSK,
        })
        self.assertEqual(exit_code, 1)
        self.assertIn("status=INVALID_TARGET", out)


if __name__ == "__main__":
    unittest.main()
