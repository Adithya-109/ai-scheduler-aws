"""Overview page."""

import streamlit as st


def _stat(label: str, value: str, note: str) -> str:
    return f"""
    <div class="dev-card" style="padding: 1.1rem 1.2rem;">
        <div style="font-size: 0.78rem; font-weight: 500; color: var(--text-muted);">{label}</div>
        <div style="font-size: 1.9rem; font-weight: 650; color: var(--text-pure); margin: 2px 0;">{value}</div>
        <div style="font-size: 0.78rem; color: var(--text-muted);">{note}</div>
    </div>
    """


def _step(num: str, title: str, body: str) -> str:
    return f"""
    <div class="dev-card">
        <div style="font-size: 0.78rem; font-weight: 600; color: var(--accent-amber); margin-bottom: 0.5rem;">{num}</div>
        <div style="font-size: 1.05rem; font-weight: 650; color: var(--text-pure); margin-bottom: 0.4rem;">{title}</div>
        <p style="font-size: 0.9rem; color: var(--text-muted); line-height: 1.6; margin: 0;">{body}</p>
    </div>
    """


def render(ctx) -> None:
    CLOUD_HOST, SCHED_VS_EDGE, STAT = ctx.CLOUD_HOST, ctx.SCHED_VS_EDGE, ctx.STAT
    st.markdown("<div class='fluid-view'>", unsafe_allow_html=True)

    hero_l, hero_r = st.columns([1.15, 0.85], gap="large")
    with hero_l:
        st.markdown(
            """
            <div style="padding: 0.6rem 0 1rem 0;">
                <h1 style="font-size: 2.7rem; line-height: 1.15; margin: 0 0 1rem 0;">
                    Run each Python job where it finishes first
                </h1>
                <p style="font-size: 1.05rem; color: var(--text-muted); line-height: 1.65; max-width: 540px; margin: 0 0 1.6rem 0;">
                    The scheduler reads your code, estimates how much work it is, and sends it either to this
                    machine or to an AWS EC2 instance, whichever is predicted to be faster once network delay is counted.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2, _ = st.columns([3, 3, 3], gap="small")
        with b1:
            if st.button("Run a workload", type="primary", use_container_width=True, width="stretch"):
                st.session_state.current_tab = "playground"
                st.rerun()
        with b2:
            if st.button("View cluster", type="secondary", use_container_width=True, width="stretch"):
                st.session_state.current_tab = "endpoints"
                st.rerun()

    with hero_r:
        st.markdown(
            f"""
            <div class="dev-card" style="padding: 1.5rem;">
                <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted); margin-bottom: 1rem;">How a job is routed</div>
                <div style="display: grid; gap: 10px; font-size: 0.9rem; color: var(--text-primary);">
                    <div style="display: flex; justify-content: space-between;"><span>1. Read the code (no execution)</span><b>{STAT['extract_ms']:.2f} ms</b></div>
                    <div style="display: flex; justify-content: space-between;"><span>2. Predict edge and cloud time</span><b>{SCHED_VS_EDGE} vs edge-only</b></div>
                    <div style="display: flex; justify-content: space-between;"><span>3. Add network delay to the cloud</span><b>{STAT['rtt_ms']:.0f} ms round trip</b></div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 1.2rem;">
                    <div style="background: var(--surface-well); border: 1px solid var(--border-color); border-radius: 8px; padding: 10px 12px;">
                        <div style="font-size: 0.72rem; color: var(--text-muted);">Edge</div>
                        <div style="font-size: 0.92rem; font-weight: 600; color: var(--text-pure);">localhost:8000</div>
                    </div>
                    <div style="background: var(--surface-well); border: 1px solid var(--border-color); border-radius: 8px; padding: 10px 12px;">
                        <div style="font-size: 0.72rem; color: var(--text-muted);">Cloud</div>
                        <div style="font-size: 0.92rem; font-weight: 600; color: var(--text-pure);">{CLOUD_HOST}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    cols = st.columns(4, gap="medium")
    stats = (
        ("Total time vs always-edge", SCHED_VS_EDGE, "held-out script families"),
        ("Reading the code", f"{STAT['extract_ms']:.2f} ms", "median, never runs the script"),
        ("Scripts measured", f"{STAT['scripts']}", "timed on both workers"),
        ("Cloud time fit (R²)", f"{STAT['cloud_r2']:.2f}", "on held-out families"),
    )
    for col, (label, value, note) in zip(cols, stats):
        with col:
            st.markdown(_stat(label, value, note), unsafe_allow_html=True)

    st.markdown(
        "<h2 style='font-size: 1.4rem; margin: 2.6rem 0 1rem 0;'>How it works</h2>",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(_step("Step 1", "Read the code",
                          "The Python syntax tree is parsed to count loops, recursion and array operations. "
                          "The script is never run just to size it up."), unsafe_allow_html=True)
    with c2:
        st.markdown(_step("Step 2", "Predict both sides",
                          "Two gradient-boosted models, trained on measured run times, predict how long the job takes "
                          "on the edge and on the cloud."), unsafe_allow_html=True)
    with c3:
        st.markdown(_step("Step 3", "Account for the network",
                          "The cloud is chosen only if its predicted time plus the round trip and data transfer "
                          "beats the edge."), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
