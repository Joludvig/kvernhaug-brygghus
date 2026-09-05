# ui/abv_calculator_panel.py
import streamlit as st

from modules.calculations import beregn_abv_fra_og_fg
from ui.i18n import t

# UI-presentasjonsterskel (ikke en del av Core-kontrakten) for når
# high-gravity-estimatet vises i tillegg til standardestimatet -- se
# "Measured-gravity ABV (issue #77)" i
# docs/development/CORE_CALCULATION_CONTRACT.md. Samme terskel som
# web/js/verktoy_page.js sin tilsvarende konstant.
_HOY_GRAVITET_TERSKEL_OG = 1.070


def render_abv_calculator_panel():
    """Frittstående ABV-kalkulator (issue #77): tar MÅLT OG+FG direkte,
    uten å opprette, åpne eller endre noen oppskrift/brygg. Bruker
    utelukkende modules/calculations.py::beregn_abv_fra_og_fg() -- ingen
    egen formel her."""
    st.write("---")
    with st.expander(t("abv_calc.tittel"), expanded=True):
        st.caption(t("abv_calc.beskrivelse"))

        col1, col2 = st.columns(2)
        with col1:
            og = st.number_input(
                t("abv_calc.og_label"),
                min_value=0.980, max_value=1.300, step=0.001, format="%.3f",
                value=1.050, key="abv_calc_og",
            )
        with col2:
            fg = st.number_input(
                t("abv_calc.fg_label"),
                min_value=0.980, max_value=1.300, step=0.001, format="%.3f",
                value=1.010, key="abv_calc_fg",
            )

        try:
            resultat = beregn_abv_fra_og_fg(og, fg)
        except ValueError:
            st.error(t("abv_calc.ugyldig_input"))
            return

        if og >= _HOY_GRAVITET_TERSKEL_OG:
            res1, res2 = st.columns(2)
            res1.metric(t("abv_calc.standard_label"), f"{resultat['standard']:.1f}%")
            res2.metric(t("abv_calc.high_gravity_label"), f"{resultat['high_gravity']:.1f}%")
            st.caption(t("abv_calc.high_gravity_forklaring"))
        else:
            st.metric(t("abv_calc.resultat_label"), f"{resultat['standard']:.1f}%")
