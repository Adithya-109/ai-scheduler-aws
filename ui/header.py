"""Brand bar, navigation and theme toggle."""

import streamlit as st

TABS = (("overview", "Overview"), ("playground", "Dispatch"), ("endpoints", "Cluster"), ("telemetry", "Telemetry"))


def render(ctx) -> None:
    is_dark = ctx.is_dark
    header_brand, header_nav, header_ctrl = st.columns([2.2, 5.2, 3.2], gap="medium")

    with header_brand:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 10px; height: 100%; padding-top: 6px;">
                <span style="width: 10px; height: 10px; border-radius: 3px; background: var(--accent-amber);"></span>
                <span style="font-size: 1.1rem; font-weight: 650; color: var(--text-pure); letter-spacing: -0.01em;">
                    AI Scheduler
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_nav:
        for col, (key, label) in zip(st.columns(len(TABS), gap="small"), TABS):
            with col:
                active = st.session_state.current_tab == key
                if st.button(label, key=f"nav_{key}", use_container_width=True, width="stretch",
                             type="primary" if active else "secondary"):
                    st.session_state.current_tab = key
                    st.rerun()

    with header_ctrl:
        theme_col, status_col = st.columns([1.2, 1.2], gap="small")
        with theme_col:
            new_theme = st.toggle("Dark mode", value=is_dark, key="theme_toggle")
            if new_theme != is_dark:
                st.session_state.theme_mode = "dark" if new_theme else "light"
                st.rerun()
        with status_col:
            state = ctx.cloud_status()
            color = {"online": "#059669", "offline": "#dc2626"}.get(state, "var(--text-muted)")
            label = {"online": "Cloud online", "offline": "Cloud offline"}.get(state, "Cloud not set")
            st.markdown(
                f"""
                <div style="display: flex; justify-content: flex-end; align-items: center; height: 100%; padding-top: 6px;">
                    <span class="tech-chip" style="color: {color}; border-color: {color};">
                        <span class="pulse-dot" style="background-color: {color};"></span> {label}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin: 0.6rem 0 1.8rem 0; border-bottom: 1px solid var(--border-color);'></div>",
                unsafe_allow_html=True)
