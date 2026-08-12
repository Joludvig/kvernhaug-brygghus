import base64
import os
import streamlit as st

_LOGO_PATH = os.path.join("assets", "branding", "kbh_emblem_master.png")

# Samme godkjente motiv/fil-prinsipp som web/assets/branding/kvernhaug_header_banner.jpg
# (web/README.md) -- en ren, ubeskåret nedskalering av den godkjente kildefilen
# kvernhaug_brygghus_i_gyllen_fjelldal.png (samme sideforhold, ingen AI-behandling,
# ingen ny beskjæring). Delt visuelt univers mellom web og desktop-appen.
_BANNER_PATH = os.path.join("assets", "branding", "kvernhaug_header_banner.jpg")

_COLORS = {
    "antikk_gull":  "#c49a2a",
    "pergament":    "#dfd0a0",
    "mosegroen":    "#3d6b2a",
    "kobber":       "#9e6030",
    "skifer_sort":  "#0a0a0a",
}


@st.cache_data
def _logo_base64() -> str:
    with open(_LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


@st.cache_data
def _banner_base64() -> str:
    with open(_BANNER_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()


def render_header():
    # Bred hero-banner (ikke lenger liten logo + tekst ved siden av) --
    # samme visuelle identitet som web-heroen (web/index.html .hero), men i
    # en kompakt arbeidsflate-variant (clamp 150-210px) siden desktop-appen
    # trenger vertikal plass til selve byggeren rett under. Bildet vises via
    # CSS background-position/background-size -- selve filen er urørt.
    if not os.path.exists(_BANNER_PATH):
        st.warning("Header-banner mangler: assets/branding/kvernhaug_header_banner.jpg")
        return

    gold  = _COLORS["antikk_gull"]
    parch = _COLORS["pergament"]
    green = _COLORS["mosegroen"]
    banner_b64 = _banner_base64()

    st.markdown(
        f"""
        <div style="
          position: relative;
          width: 100%;
          height: clamp(165px, 15vw, 295px);
          overflow: hidden;
          border-radius: 10px;
          border-bottom: 2px solid {gold};
          box-shadow: 0 6px 22px rgba(0, 0, 0, 0.4);
          margin-bottom: 22px;
          background-image: url('data:image/jpeg;base64,{banner_b64}');
          background-size: cover;
          background-position: center 68%;
          container-type: inline-size;
        ">
          <div style="
            position: absolute; inset: 0;
            background: linear-gradient(to top,
              rgba(8, 5, 3, 0.88) 0%,
              rgba(8, 5, 3, 0.45) 38%,
              rgba(8, 5, 3, 0.06) 62%,
              rgba(8, 5, 3, 0) 78%);
          "></div>
          <div style="
            position: absolute; left: 0; bottom: 0;
            max-width: 62%;
            padding: clamp(0.6rem, 1.6vw, 1.2rem) clamp(0.4rem, 1.2cqw, 1rem);
            font-family: Georgia, 'Times New Roman', serif;
          ">
            <div style="
              color: {gold};
              font-size: clamp(0.85rem, 1.45cqw, 1.4rem);
              font-weight: bold;
              letter-spacing: 0.02em;
              line-height: 1.1;
              text-shadow: 1px 2px 10px rgba(0, 0, 0, 0.85);
            ">KVERNHAUG BRYGGHUS</div>
            <div style="
              color: {parch};
              font-style: italic;
              font-size: clamp(0.8rem, 1.2vw, 1.05rem);
              letter-spacing: 0.02em;
              margin-top: 0.3rem;
              text-shadow: 1px 1px 8px rgba(0, 0, 0, 0.85);
            ">Brygg med ild. Del med ære.</div>
            <div style="
              color: {green};
              font-size: clamp(0.62rem, 0.9vw, 0.78rem);
              letter-spacing: 0.16em;
              text-transform: uppercase;
              margin-top: 0.3rem;
              text-shadow: 1px 1px 6px rgba(0, 0, 0, 0.85);
            ">Håndverk&nbsp;&nbsp;•&nbsp;&nbsp;Tradisjon&nbsp;&nbsp;•&nbsp;&nbsp;Karakter</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
