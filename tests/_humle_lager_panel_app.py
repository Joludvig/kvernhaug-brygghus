"""Minimal vertskap-app for AppTest av ui/humle_lager_panel.py (samme
mønster som tests/_process_panel_app.py). Ikke en del av selve
applikasjonen, og plukkes ikke opp av `unittest discover` (matcher ikke
test*.py)."""
from ui.humle_lager_panel import render_humle_lager_panel

humle_database = {"citra": {"display_name": "Citra"}, "magnum": {"display_name": "Magnum"}}

render_humle_lager_panel(humle_database)
