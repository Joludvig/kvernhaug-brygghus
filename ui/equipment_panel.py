import streamlit as st
from config import DEMO_MODE
from modules.equipment import last_equipment, lagre_equipment
from ui import demo_state


def _hent_equipment():
    return demo_state.hent_equipment() if DEMO_MODE else last_equipment()


def _lagre_equipment(data):
    if DEMO_MODE:
        demo_state.lagre_equipment(data)
    else:
        lagre_equipment(data)


def render_equipment_panel():
    st.write("---")
    with st.expander("⚙️ Utstyrsprofil"):
        eq = _hent_equipment()
        st.caption(
            "Standardverdier er BrewZilla 35L Gen 4.1. "
            "Endre for ditt eget utstyr — beregningene oppdateres ved neste rendering."
        )

        col1, col2 = st.columns(2)
        with col1:
            efficiency = st.number_input(
                "Brygghuseffektivitet (%)",
                min_value=50, max_value=100, step=1,
                value=int(round(eq["efficiency"] * 100)),
                key="eq_efficiency",
                help=(
                    "Andelen av maltets potensielle sukker som ender som "
                    "gravity points i ferdig batch. Bruk din målte "
                    "brygghuseffektivitet, ikke meskeeffektivitet."
                ),
            )
            boil_off = st.number_input(
                "Fordampning (L/time)",
                min_value=0.5, max_value=10.0, step=0.5,
                value=float(eq["boil_off_l_per_hour"]),
                key="eq_boil_off",
            )
            mash_ratio = st.number_input(
                "Maskeforhold (L/kg korn)",
                min_value=1.0, max_value=6.0, step=0.1, format="%.1f",
                value=float(eq["mash_ratio_l_per_kg"]),
                key="eq_mash_ratio",
            )
        with col2:
            grain_abs = st.number_input(
                "Kornabsorpsjon (L/kg)",
                min_value=0.2, max_value=2.0, step=0.1, format="%.1f",
                value=float(eq["grain_absorption_l_per_kg"]),
                key="eq_grain_abs",
            )
            dead_space = st.number_input(
                "Dead volume (L)",
                min_value=0.0, max_value=10.0, step=0.5,
                value=float(eq["dead_space_l"]),
                key="eq_dead_space",
            )
            kettle_cap = st.number_input(
                "Kjelekapasitet (L)",
                min_value=10.0, max_value=200.0, step=5.0,
                value=float(eq["kettle_capacity_l"]),
                key="eq_kettle_cap",
            )

        boil_time = st.number_input(
            "Standard koketid (min)",
            min_value=30, max_value=120, step=15,
            value=int(eq["default_boil_time_min"]),
            key="eq_boil_time",
        )

        if st.button("💾 Lagre utstyrsprofil", width="stretch", key="eq_save_btn"):
            _lagre_equipment({
                "efficiency": efficiency / 100.0,
                "boil_off_l_per_hour": boil_off,
                "grain_absorption_l_per_kg": grain_abs,
                "dead_space_l": dead_space,
                "mash_ratio_l_per_kg": mash_ratio,
                "kettle_capacity_l": kettle_cap,
                "default_boil_time_min": boil_time,
            })
            melding = "Utstyrsprofil lagret! (demo — ikke permanent)" if DEMO_MODE else "Utstyrsprofil lagret!"
            st.toast(melding, icon="⚙️")
            st.rerun()
