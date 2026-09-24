"""
Minimal, dedicated Streamlit entrypoint for real *runtime* browser
regression coverage of the three Bryggeskole static SVG visuals --
boil/hop timeline (issue #366), cool/transfer flow (issue #370) and
package flow (issue #374) -- per the Chief review on issue #378/PR #379.

Not part of the production app (`app.py`) navigation. It deliberately
bypasses the Bryggeskole lesson/chunk/session-state machinery in
`ui/bryggeskole_panel.py` so a Playwright test can load one stable page
directly, while still exercising the *exact same* rendering call each
of the three renderers goes through in production:

    st.markdown(<svg markup>, unsafe_allow_html=True)

(see `ui/bryggeskole_panel.py` lines ~570/576/582). This is the
smallest possible real Streamlit runtime surface for these visuals --
not a general Streamlit E2E framework.

Language is selected via the `lang` query parameter (`?lang=no` /
`?lang=en`, default `no`), so the Playwright spec can cover both
without needing a separate harness page per language.

Run standalone for manual inspection:
    streamlit run tests/playwright_streamlit/harness_app.py --server.headless true
"""

import streamlit as st

from bryggeskole.boil_timeline import render_boil_timeline_svg
from bryggeskole.cool_transfer_flow import render_cool_transfer_flow_svg
from bryggeskole.package_flow import render_package_flow_svg

_sprak = st.query_params.get("lang", "no")
if _sprak not in ("no", "en"):
    _sprak = "no"

st.markdown(render_boil_timeline_svg(_sprak), unsafe_allow_html=True)
st.markdown(render_cool_transfer_flow_svg(_sprak), unsafe_allow_html=True)
st.markdown(render_package_flow_svg(_sprak), unsafe_allow_html=True)
