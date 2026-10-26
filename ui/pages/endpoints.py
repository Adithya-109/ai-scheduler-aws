"""endpoints page."""
import time

import requests
import streamlit as st

import config


def render(ctx) -> None:
    CLOUD_HOST, STAT = ctx.CLOUD_HOST, ctx.STAT
    st.markdown("<div class='fluid-view'>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="margin-bottom: 1.8rem;">
            <div class="tech-chip" style="color: var(--accent-amber); margin-bottom: 6px;">COMPUTE FABRIC MONITOR</div>
            <h2 style="font-size: 2.1rem; color: var(--text-pure);">Cluster Endpoints & Network Latency</h2>
            <p style="color: var(--text-muted); font-size: 0.95rem;">Perform live connectivity pings to compute nodes and adjust the simulated network round-trip compensation delay.</p>
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
                    <span style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: var(--text-pure);">
                        Local Edge Worker
                    </span>
                    <span class="tech-chip" style="color: #10B981; border-color: rgba(16,185,129,0.3);">
                        <span class="pulse-dot"></span> ONLINE
                    </span>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-muted); line-height: 1.85; margin-bottom: 1.2rem;">
                    <b>URL:</b> {config.execute_url(config.LOCAL_WORKER_URL)}<br>
                    <b>Hardware:</b> Local Host Worker Process<br>
                    <b>Network Transit:</b> 0ms (Local Loopback)<br>
                    <b>Optimal For:</b> Lightweight scripts, string heuristics, fast transforms
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("Ping Local Edge Worker", use_container_width=True, width="stretch"):
            try:
                t0 = time.perf_counter()
                r = requests.get(config.health_url(config.LOCAL_WORKER_URL), timeout=3)
                ms = (time.perf_counter() - t0) * 1000
                st.success(f"Local Edge responded in {ms:.1f}ms (HTTP {r.status_code})")
            except Exception as e:
                st.error(f"Edge connection failed: {e}")

    with ep_col2:
        st.markdown(
            f"""
            <div class="dev-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <span style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: var(--text-pure);">
                        AWS EC2 Cloud Node
                    </span>
                    <span class="tech-chip" style="color: #10B981; border-color: rgba(16,185,129,0.3);">
                        <span class="pulse-dot"></span> {CLOUD_HOST}
                    </span>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-muted); line-height: 1.85; margin-bottom: 1.2rem;">
                    <b>URL:</b> {config.execute_url(config.CLOUD_WORKER_URL) or "not configured"}<br>
                    <b>Hardware:</b> AWS EC2 Cloud Instance<br>
                    <b>Network Transit:</b> {STAT['rtt_ms']:.0f}ms (measured at training time)<br>
                    <b>Optimal For:</b> High-dimensional matrices, parallel PyTorch/NumPy
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("Ping AWS EC2 Node", use_container_width=True, width="stretch"):
            if not config.CLOUD_WORKER_URL:
                st.warning("CLOUD_WORKER_URL is not set (see .env.example).")
            else:
                try:
                    t0 = time.perf_counter()
                    r = requests.get(config.health_url(config.CLOUD_WORKER_URL), timeout=5)
                    ms = (time.perf_counter() - t0) * 1000
                    st.success(f"AWS EC2 responded in {ms:.1f}ms (HTTP {r.status_code})")
                except Exception as e:
                    st.error(f"AWS EC2 connection failed: {e}")

    st.markdown("<div style='margin: 3.2rem 0 2rem 0; border-top: 1px solid var(--border-color);'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="dev-card" style="padding: 1.8rem 2rem;">
            <div style="font-family: var(--font-heading); font-size: 1.3rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.4rem;">
                Dynamic Network Round-Trip Delay Simulator
            </div>
            <p style="color: var(--text-muted); font-size: 0.88rem; margin-bottom: 1.2rem;">
                Adjusting the simulated WAN network delay alters the offload crossover threshold in real-time.
            </p>
        """,
        unsafe_allow_html=True
    )

    new_rtt = st.slider(
        "Simulated Cloud Latency (ms)",
        10, 500,
        st.session_state.sim_cloud_rtt,
        help="Adjusting this slider updates the network penalty applied during latency prediction and classification."
    )
    st.session_state.sim_cloud_rtt = new_rtt
    st.caption(f"Currently simulating **{new_rtt}ms** WAN latency. Offloading to AWS Cloud will only trigger when compute acceleration exceeds {new_rtt}ms.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
