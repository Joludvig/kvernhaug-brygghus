"""
V2.2 G3M (issue #388) — regresjonstester for Koking/humle Learn -> Plan-
broen i ui/hop_panel.py, se docs/development/
v22_g3l_boil_hop_learn_plan_contract.md.

Speiler EKSAKT samme mønster som TestLaerBroGjaeringBridge i
tests/test_yeast_panel.py (issue #384) / TestLaerBroMeskingBridge i
tests/test_process_panel.py (issue #352) for selve broen.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import logging
import os
import unittest
from unittest import mock

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.i18n import t as _t
from bryggeskole.pilot_boil_hop import PilotContentError, read_pilot_file, render_chunk

_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_hop_panel_app.py")

_ALLE_CHUNK_IDER = (
    "CHUNK-BOILHOP-A", "CHUNK-BOILHOP-B", "CHUNK-BOILHOP-C",
    "CHUNK-BOILHOP-D", "CHUNK-BOILHOP-E", "CHUNK-BOILHOP-F",
)
_BRO_CHUNK_IDER = ("CHUNK-BOILHOP-C", "CHUNK-BOILHOP-D", "CHUNK-BOILHOP-E", "CHUNK-BOILHOP-F")


def _ny_at():
    at = AppTest.from_file(_APP)
    at.run()
    return at


def _finn_laer_bro(at, sprak="no"):
    tittel = _t("koking.laer_bro.tittel", sprak)
    treff = [e for e in at.expander if e.label == tittel]
    assert len(treff) == 1, f"Fant ikke akkurat én Learn->Plan-bro med label={tittel!r}: {[e.label for e in at.expander]}"
    return treff[0]


def _markdown_tekster(bro):
    return [c.value for c in bro.children.values() if type(c).__name__ == "Markdown"]


class TestLaerBroKokingHumleBridge(unittest.TestCase):
    """§4/§9.2/§10.1 i kontrakten: kollapset som standard, rendres
    nøyaktig én gang uansett radantall, viser CHUNK-BOILHOP-C/D/E/F
    uendret i NO/EN (ikke A/B), guardrail rendres i begge språk, feiler
    lukket ved ugyldig pilotinnhold."""

    def test_broen_finnes_og_er_kollapset_som_standard(self):
        at = _ny_at()
        bro = _finn_laer_bro(at)
        self.assertFalse(bro.proto.expanded)

    def test_broen_rendres_noyaktig_en_gang_med_en_rad(self):
        at = _ny_at()
        _finn_laer_bro(at)  # raiser AssertionError hvis != 1 treff

    def test_broen_rendres_fortsatt_noyaktig_en_gang_etter_flere_rader(self):
        at = _ny_at()
        for _ in range(3):
            at.button(key="add_hop_btn").click().run()
        self.assertEqual(len(at.session_state["valgt_humle"]), 4)
        _finn_laer_bro(at)  # fortsatt nøyaktig ett treff

    def test_broen_rendres_fortsatt_noyaktig_en_gang_etter_sletting_av_rader(self):
        at = _ny_at()
        at.button(key="add_hop_btn").click().run()
        self.assertEqual(len(at.session_state["valgt_humle"]), 2)
        slett_knapper = [b for b in at.button if b.key and b.key.startswith("slett_humle_")]
        self.assertTrue(slett_knapper)
        slett_knapper[0].click().run()
        self.assertEqual(len(at.session_state["valgt_humle"]), 1)
        _finn_laer_bro(at)  # fortsatt nøyaktig ett treff

    def test_broen_viser_chunk_boilhop_c_d_e_f_uendret_paa_norsk(self):
        at = _ny_at()
        bro = _finn_laer_bro(at)
        pilot = read_pilot_file()
        chunker = {c["id"]: c for c in pilot["chunks"]}
        forventet = [render_chunk(chunker[cid], "no")["text"] for cid in _BRO_CHUNK_IDER]
        self.assertEqual(_markdown_tekster(bro), forventet)

    def test_broen_viser_chunk_boilhop_c_d_e_f_uendret_paa_engelsk(self):
        at = AppTest.from_file(_APP)
        at.session_state["sprak"] = "en"
        at.run()
        bro = _finn_laer_bro(at, sprak="en")
        pilot = read_pilot_file()
        chunker = {c["id"]: c for c in pilot["chunks"]}
        forventet = [render_chunk(chunker[cid], "en")["text"] for cid in _BRO_CHUNK_IDER]
        self.assertEqual(_markdown_tekster(bro), forventet)

    def test_chunk_a_og_b_rendres_ikke(self):
        at = _ny_at()
        bro = _finn_laer_bro(at)
        pilot = read_pilot_file()
        chunker = {c["id"]: c for c in pilot["chunks"]}
        rendrede_tekster = _markdown_tekster(bro)
        for utelatt_id in ("CHUNK-BOILHOP-A", "CHUNK-BOILHOP-B"):
            utelatt_tekst = render_chunk(chunker[utelatt_id], "no")["text"]
            self.assertNotIn(utelatt_tekst, rendrede_tekster)

    def test_guardrail_rendres_paa_norsk(self):
        at = _ny_at()
        bro = _finn_laer_bro(at)
        varsler = [w.value for w in bro.children.values() if type(w).__name__ == "Warning"]
        self.assertEqual(len(varsler), 1)
        # st.warning skiller ut en ledende emoji som eget ikon (aldri en del
        # av .value) -- sammenlign derfor mot i18n-strengen uten "⚠️ "-prefikset.
        self.assertEqual(varsler[0], _t("koking.laer_bro.guardrail", "no").replace("⚠️ ", "", 1))

    def test_guardrail_rendres_paa_engelsk(self):
        at = AppTest.from_file(_APP)
        at.session_state["sprak"] = "en"
        at.run()
        bro = _finn_laer_bro(at, sprak="en")
        varsler = [w.value for w in bro.children.values() if type(w).__name__ == "Warning"]
        self.assertEqual(len(varsler), 1)
        self.assertEqual(varsler[0], _t("koking.laer_bro.guardrail", "en").replace("⚠️ ", "", 1))

    def test_guardrail_skiller_aktiv_koketid_fra_whirlpool_paa_begge_sprak(self):
        no_tekst = _t("koking.laer_bro.guardrail", "no")
        en_tekst = _t("koking.laer_bro.guardrail", "en")
        self.assertIn("aktiv", no_tekst.lower())
        self.assertIn("whirlpool", no_tekst.lower())
        self.assertIn("active-boil", en_tekst.lower())
        self.assertIn("whirlpool", en_tekst.lower())

    def test_ugyldig_pilotinnhold_krasjer_ikke_oppskrift_fanen(self):
        with mock.patch(
            "ui.hop_panel._pilot_koking.read_pilot_file",
            side_effect=PilotContentError(["ugyldig innhold"]),
        ):
            at = _ny_at()
        self.assertFalse(at.exception, f"Panelet skal aldri krasje ved ugyldig pilotinnhold: {at.exception}")
        bro = _finn_laer_bro(at)
        feilmeldinger = " ".join(e.value for e in at.error)
        self.assertIn("Kunne ikke laste leksjonsinnholdet akkurat nå.", feilmeldinger)
        self.assertEqual(_markdown_tekster(bro), [], "Ingen chunk-tekst skal rendres når pilotinnholdet er ugyldig.")


class TestEksisterendeHumleradAtferdUendret(unittest.TestCase):
    """§5/§6/§10.1 i kontrakten: broen legger til ingen ny persistert
    tilstand -- humleradens form forblir nøyaktig id/gram/tid, og
    eksisterende legg til/rediger/slett-atferd er uendret."""

    def test_humlerad_form_forblir_id_gram_tid(self):
        at = _ny_at()
        for rad in at.session_state["valgt_humle"]:
            self.assertEqual(set(rad.keys()), {"id", "gram", "tid"})

    def test_legg_til_humle_gir_standardrad_id_gram_tid(self):
        at = _ny_at()
        at.button(key="add_hop_btn").click().run()
        self.assertEqual(len(at.session_state["valgt_humle"]), 2)
        for rad in at.session_state["valgt_humle"]:
            self.assertEqual(set(rad.keys()), {"id", "gram", "tid"})

    def test_rediger_tid_oppdaterer_raden_uendret(self):
        at = _ny_at()
        at.number_input(key="humle_tid_0_v0").set_value(15).run()
        self.assertEqual(at.session_state["valgt_humle"][0]["tid"], 15)
        self.assertEqual(set(at.session_state["valgt_humle"][0].keys()), {"id", "gram", "tid"})

    def test_slett_humle_fjerner_raden(self):
        at = _ny_at()
        at.button(key="add_hop_btn").click().run()
        at.button(key="slett_humle_1_v0").click().run()
        self.assertEqual(len(at.session_state["valgt_humle"]), 1)

    def test_ingen_ny_planleggings_session_state_nokkel_introduseres(self):
        at = _ny_at()
        nye_bs_nokler = {
            k for k in at.session_state
            if isinstance(k, str) and k.startswith(("koking_", "laer_bro_", "bo_", "bs_"))
        }
        self.assertEqual(nye_bs_nokler, set())


if __name__ == "__main__":
    unittest.main()
