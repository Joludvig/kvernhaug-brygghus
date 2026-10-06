"""
Testhjelper: nøklene i AppTest.session_state på tvers av støttede
Streamlit-versjoner (requirements.txt: >=1.59,<2.0).

Fra Streamlit 1.64 er ``at.session_state`` en mapping-wrapper som kan
itereres og gir ``filtered_state`` (brukerstate + widgets med key, ikke
interne Streamlit-nøkler). Før 1.64 er det en ``SafeSessionState`` uten
``__iter__``; ``for k in at.session_state`` faller da tilbake til
sekvensprotokollen og feiler med ``KeyError: ... no key "0"``. Den
eksponerer i stedet de samme nøklene via egenskapen ``filtered_state``.
"""


def apptest_session_state_keys(at):
    """Samme nøkkelsett som ``set(at.session_state)`` gir på Streamlit >= 1.64."""
    state = at.session_state
    if hasattr(type(state), "keys"):
        return set(state.keys())
    return set(state.filtered_state)
