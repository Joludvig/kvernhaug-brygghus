# Minimal AppTest-harness for ui/bryggeskole_panel.py::render_bryggeskole_panel()
# alene -- render_bryggeskole_panel() har ingen avhengighet til
# ctx/malt/humle/gjaer, så harnessen trenger bare selve panelet + en
# språkvelger (samme "sprak"-widget-key som den ekte appen bruker), for å
# kunne teste NO/EN akkurat som ui/i18n.py::render_sprak_valger() gjør i
# app.py sin sidebar.
from ui.bryggeskole_panel import render_bryggeskole_panel
from ui.i18n import render_sprak_valger

render_sprak_valger()
render_bryggeskole_panel()
