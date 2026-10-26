"""Brand bar, navigation and theme toggle."""

import streamlit as st


def render(ctx) -> None:
    is_dark = ctx.is_dark
    # 5. Global Header Bar: Brand, Clean Unified Navigation & Controls
    header_brand, header_nav, header_ctrl = st.columns([2.8, 6.0, 3.2], gap="medium")

    with header_brand:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 10px; height: 100%; padding-top: 4px;">
                <div style="background: linear-gradient(135deg, #F59E0B, #D97706); color: #FFFFFF; width: 28px; height: 28px; border-radius: 0px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.78rem; font-family: var(--font-heading); box-shadow: 0 2px 8px rgba(245,158,11,0.25);">
                    AS
                </div>
                <span style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: var(--text-pure); letter-spacing: -0.02em;">
                    AI SCHEDULER
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    with header_nav:
        n1, n2, n3, n4 = st.columns(4, gap="small")
        with n1:
            is_active = st.session_state.current_tab == "overview"
            if st.button("Overview", use_container_width=True, width="stretch", type="primary" if is_active else "secondary"):
                st.session_state.current_tab = "overview"
                st.rerun()
        with n2:
            is_active = st.session_state.current_tab == "playground"
            if st.button("Dispatch", use_container_width=True, width="stretch", type="primary" if is_active else "secondary"):
                st.session_state.current_tab = "playground"
                st.rerun()
        with n3:
            is_active = st.session_state.current_tab == "endpoints"
            if st.button("Cluster", use_container_width=True, width="stretch", type="primary" if is_active else "secondary"):
                st.session_state.current_tab = "endpoints"
                st.rerun()
        with n4:
            is_active = st.session_state.current_tab == "telemetry"
            if st.button("Telemetry", use_container_width=True, width="stretch", type="primary" if is_active else "secondary"):
                st.session_state.current_tab = "telemetry"
                st.rerun()

    with header_ctrl:
        theme_col, status_col = st.columns([1.1, 1.3], gap="small")
        with theme_col:
            new_theme = st.toggle("Dark mode", value=is_dark, key="theme_toggle")
            if new_theme != is_dark:
                st.session_state.theme_mode = 'dark' if new_theme else 'light'
                st.rerun()
        with status_col:
            state = ctx.cloud_status()
            color = {"online": "#10B981", "offline": "#DC2626"}.get(state, "var(--text-muted)")
            label = {"online": "Cloud online", "offline": "Cloud offline"}.get(state, "Cloud not set")
            st.markdown(
                f"""
                <div style="display: flex; justify-content: flex-end; align-items: center; height: 100%; padding-top: 4px;">
                    <span class="tech-chip" style="color: {color}; border-color: {color};">
                        <span class="pulse-dot" style="background-color: {color};"></span> {label}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<div style='margin-bottom: 2.2rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.6rem;'></div>", unsafe_allow_html=True)
