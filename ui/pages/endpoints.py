"""endpoints page."""
import time

import requests
import streamlit as st

import config


def render(ctx) -> None:
    STAT = ctx.STAT
    st.markdown("<div class='fluid-view'>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="margin-bottom: 1.8rem;">
            <h2 style="font-size: 1.8rem; margin: 0 0 4px 0;">Cluster</h2>
            <p style="color: var(--text-muted); font-size: 0.95rem; margin: 0;">The two workers jobs can run on, and the network delay the scheduler assumes between them.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    ep_col1, ep_col2 = st.columns(2, gap="large")
    with ep_col1:
        st.markdown(
            f"""
            <div class="dev-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <span style="font-size: 1.1rem; font-weight: 650; color: var(--text-pure);">Local edge worker</span>
                    <span class="tech-chip">This machine</span>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-muted); line-height: 1.85; margin-bottom: 1.2rem;">
                    <b>Address:</b> {config.execute_url(config.LOCAL_WORKER_URL)}<br>
                    <b>Network delay:</b> none (loopback)<br>
                    <b>Best for:</b> short scripts, where sending the job away costs more than it saves
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("Check edge worker", use_container_width=True, width="stretch"):
            try:
                t0 = time.perf_counter()
                r = requests.get(config.health_url(config.LOCAL_WORKER_URL), timeout=3)
                ms = (time.perf_counter() - t0) * 1000
                st.success(f"Edge worker responded in {ms:.0f} ms (HTTP {r.status_code})")
            except Exception as e:
                st.error(f"Could not reach the edge worker: {e}")

    with ep_col2:
        st.markdown(
            f"""
            <div class="dev-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <span style="font-size: 1.1rem; font-weight: 650; color: var(--text-pure);">AWS cloud worker</span>
                    <span class="tech-chip">EC2</span>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-muted); line-height: 1.85; margin-bottom: 1.2rem;">
                    <b>Address:</b> {config.execute_url(config.CLOUD_WORKER_URL) or "not configured"}<br>
                    <b>Network delay:</b> {STAT['rtt_ms']:.0f} ms (measured when the models were trained)<br>
                    <b>Best for:</b> heavy, parallel numeric work such as large matrix operations
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("Check cloud worker", use_container_width=True, width="stretch"):
            if not config.CLOUD_WORKER_URL:
                st.warning("CLOUD_WORKER_URL is not set (see .env.example).")
            else:
                try:
                    t0 = time.perf_counter()
                    r = requests.get(config.health_url(config.CLOUD_WORKER_URL), timeout=5)
                    ms = (time.perf_counter() - t0) * 1000
                    st.success(f"Cloud worker responded in {ms:.0f} ms (HTTP {r.status_code})")
                except Exception as e:
                    st.error(f"Could not reach the cloud worker: {e}")

    st.markdown("<div style='margin: 3.2rem 0 2rem 0; border-top: 1px solid var(--border-color);'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="dev-card" style="padding: 1.8rem 2rem;">
            <div style="font-size: 1.1rem; font-weight: 650; color: var(--text-pure); margin-bottom: 0.4rem;">
                Network delay
            </div>
            <p style="color: var(--text-muted); font-size: 0.88rem; margin-bottom: 1.2rem;">
                The scheduler adds this delay to the cloud estimate. A larger value makes it offload less often.
            </p>
        """,
        unsafe_allow_html=True
    )

    new_rtt = st.slider(
        "Assumed round trip to the cloud (ms)",
        10, 500,
        st.session_state.sim_cloud_rtt,
        help="Added to the cloud estimate when the scheduler compares edge and cloud."
    )
    st.session_state.sim_cloud_rtt = new_rtt
    st.caption(f"Using **{new_rtt} ms**. The cloud is chosen only when it saves more than this, plus transfer time.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
