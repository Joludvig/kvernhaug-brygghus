import base64
import os
import streamlit as st

_LOGO_PATH = os.path.join("assets", "branding", "master_v1.png")

_COLORS = {
    "antikk_gull":  "#c49a2a",
    "pergament":    "#dfd0a0",
    "mosegroen":    "#3d6b2a",
    "kobber":       "#9e6030",
    "skifer_sort":  "#0a0a0a",
}


def _logo_base64() -> str:
    with open(_LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


def render_header():
    col_img, col_text = st.columns([1, 2.8])

    with col_img:
        if os.path.exists(_LOGO_PATH):
            data = _logo_base64()
            st.markdown(
                f'<img src="data:image/png;base64,{data}" '
                f'style="width:100%; max-width:260px; display:block; margin:auto;">',
                unsafe_allow_html=True,
            )

    with col_text:
        gold   = _COLORS["antikk_gull"]
        parch  = _COLORS["pergament"]
        green  = _COLORS["mosegroen"]
        st.markdown(
            f"""
            <div style="padding: 18px 0 10px 16px;">
              <div style="
                color: {parch};
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 2.6em;
                font-weight: bold;
                letter-spacing: 0.06em;
                line-height: 1.1;
                margin-bottom: 6px;
                text-shadow: 1px 1px 4px #000;
              ">KVERNHAUG BRYGGHUS</div>
              <div style="
                color: {gold};
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 1.15em;
                font-style: italic;
                letter-spacing: 0.04em;
                margin-bottom: 10px;
              ">Brygg med ild. Del med ære.</div>
              <div style="
                color: {green};
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 0.88em;
                letter-spacing: 0.18em;
                text-transform: uppercase;
              ">Håndverk&nbsp;&nbsp;•&nbsp;&nbsp;Tradisjon&nbsp;&nbsp;•&nbsp;&nbsp;Karakter</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<hr style='border:none; border-top:1px solid {_COLORS['antikk_gull']}; "
        f"margin: 8px 0 22px 0;'>",
        unsafe_allow_html=True,
    )
