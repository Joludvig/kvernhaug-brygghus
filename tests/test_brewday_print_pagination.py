"""
Regresjonstest for Brewday Print Pagination Fix V1.

Bakgrunn: et faktisk generert Bryggedagsark kunne bli splittet stygt
over to A4-sider ved utskrift -- CSS-gridet "Målinger" (.stats-4, 4×2
målebokser) hadde ingen fragmenteringsregel, slik at nettleseren kunne
splitte det midt mellom rad 1 (Pre-boil SG/Vol, Post-boil Vol, OG) og
rad 2 (FG, ABV, Pitch temp, Maskeeff), med visuelt komprimert/
overlappende innhold rundt sideskiftet (effektivitetsrad, notater).

Fiksen samler overskriften "Målinger", .stats-4 og .eff-row i én
semantisk wrapper (.maalinger-block) med break-inside/page-break-inside:
avoid, slik at HELE blokken enten blir stående samlet på én side eller
flyttes samlet til neste side -- aldri splittet midt i.

Dette er en ren print-layout-fiks: ingen data, beregninger eller
eksportkontrakt er endret -- disse testene bekrefter nettopp DET, ikke
ny funksjonalitet.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

from modules.brewday_calc import lag_brewday_plan
from modules.brewday_template import render_brewday_html

_MALT_DB = {}
_HUMLE_DB = {}
_GJAER_INFO = {"display_name": "Testgjær", "gjaertype": "Ale"}


def _plan():
    return lag_brewday_plan(
        malt_valg=[{"id": "test_malt", "mengde": 5.0}],
        humle_valg=[{"id": "test_humle", "gram": 20.0, "tid": 60}],
        gjaer_id="test_gjaer", gjaer_info=_GJAER_INFO,
        og=1.050, batch_volum_l=20.0, humle_database=_HUMLE_DB,
        malt_database=_MALT_DB,
    )


def _ctx():
    return {
        "name": "Testbrygg", "volum": 20.0, "brygger_stil": "",
        "og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20, "ebc": 15,
        "total_pris": 400, "summary": "",
        "style_analysis": {"stil": "", "stil_liste": []},
        "recipe": {}, "effektivitet": 0.75,
    }


def _log_alle_maalinger_utfylt():
    # Samme situasjon som i det rapporterte bugget: samtlige 8
    # målebokser har en verdi (ikke bare noen av dem).
    return {
        "pre_boil_sg": 1.058, "pre_boil_vol": 24.0, "post_boil_vol": 21.0,
        "og": "1.050", "fg": "1.012", "abv": "5.0",
        "pitch_temp": 18.0, "mash_eff": 0.75, "brewhouse_eff": 0.72,
    }


class TestMaalingerBlokkStruktur(unittest.TestCase):
    """Overskrift + stats-4 + eff-row skal ligge samlet i én wrapper med
    break-inside/page-break-inside: avoid, uavhengig av om målingene er
    fylt ut eller ikke."""

    def _hent_html(self, log=None):
        return render_brewday_html(_ctx(), _plan(), log=log or {})

    def test_maalinger_block_wrapper_finnes_nøyaktig_én_gang(self):
        html_output = self._hent_html()
        self.assertEqual(html_output.count('<div class="maalinger-block">'), 1)
        self.assertIn('</div><!-- /maalinger-block -->', html_output)

    def test_maalinger_block_har_break_inside_avoid_css(self):
        html_output = self._hent_html()
        self.assertIn(".maalinger-block {", html_output)
        css_seksjon = html_output[
            html_output.index(".maalinger-block {"):
            html_output.index(".maalinger-block {") + 200
        ]
        self.assertIn("break-inside: avoid;", css_seksjon)
        self.assertIn("page-break-inside: avoid;", css_seksjon)

    def test_stat_box_har_ogsaa_break_inside_avoid(self):
        # Forsvar i dybden -- selve boksen skal heller aldri splittes.
        html_output = self._hent_html()
        css_seksjon = html_output[
            html_output.index(".stat-box {"):
            html_output.index(".stat-box {") + 300
        ]
        self.assertIn("break-inside: avoid;", css_seksjon)
        self.assertIn("page-break-inside: avoid;", css_seksjon)

    def test_rekkefolge_overskrift_stats4_effrow_inne_i_wrapper(self):
        html_output = self._hent_html()
        i_start = html_output.index('<div class="maalinger-block">')
        i_h2    = html_output.index("<h2>Målinger</h2>")
        i_stats = html_output.index('<div class="stats-4">')
        i_eff   = html_output.index('<div class="eff-row"')
        i_end   = html_output.index('</div><!-- /maalinger-block -->')
        self.assertTrue(i_start < i_h2 < i_stats < i_eff < i_end,
                         "Overskrift/stats-4/eff-row ligger ikke i forventet "
                         "rekkefølge inne i .maalinger-block")

    def test_alle_8_malebokser_fortsatt_til_stede_med_data_uendret(self):
        # Selve MÅLINGENE (verdier/beregninger) skal være helt uendret av
        # denne rene layout-fiksen.
        html_output = self._hent_html(log=_log_alle_maalinger_utfylt())
        for forventet in (
            "Pre-boil SG", "Pre-boil Vol", "Post-boil Vol", "OG",
            "FG", "ABV", "Pitch temp", "Maskeeff",
        ):
            self.assertIn(forventet, html_output)
        for verdi in ("1.058", "24.0", "21.0", "18.0"):
            self.assertIn(verdi, html_output)

    def test_notater_seksjon_fortsatt_til_stede_utenfor_wrapper(self):
        # Notater skal fortsatt rendres, som normalt, ETTER
        # maalinger-block (uendret rekkefølge i dokumentet for øvrig).
        html_output = self._hent_html()
        i_end    = html_output.index('</div><!-- /maalinger-block -->')
        i_notater = html_output.index('<div class="notes-section">')
        self.assertTrue(i_end < i_notater)

    def test_layout_forøvrig_uendret(self):
        html_output = self._hent_html()
        self.assertIn("KVERNHAUG BRYGGHUS", html_output)
        self.assertIn("Bryggedags-sjekkliste", html_output)
        self.assertIn("Brygghuseffektivitet", html_output)


if __name__ == "__main__":
    unittest.main()
