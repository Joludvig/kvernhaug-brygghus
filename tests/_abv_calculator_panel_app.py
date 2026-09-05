"""Minimal vertskap-app for AppTest av ui/abv_calculator_panel.py
(issue #77). Ikke en del av selve applikasjonen, og plukkes ikke opp av
`unittest discover` (matcher ikke test*.py)."""
from ui.i18n import init_sprak_state
from ui.abv_calculator_panel import render_abv_calculator_panel

init_sprak_state()
render_abv_calculator_panel()
