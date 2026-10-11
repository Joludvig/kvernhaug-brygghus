# Wide-layout twin of bryggeskole_harness.py for real-browser layout specs
# (tests/playwright_streamlit/learning-page-layout.spec.js, owner acceptance
# #508). app.py runs Streamlit with layout="wide"; the default centered
# harness caps the main column near the lesson's own reading measure, so a
# width/column check needs the production page layout to mean anything.
# Same production render_bryggeskole_panel() call and language picker.
import streamlit as st

st.set_page_config(layout="wide")

from ui.bryggeskole_panel import render_bryggeskole_panel  # noqa: E402
from ui.i18n import render_sprak_valger  # noqa: E402

render_sprak_valger()
render_bryggeskole_panel()
