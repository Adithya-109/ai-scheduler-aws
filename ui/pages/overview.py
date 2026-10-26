"""overview page."""

import streamlit as st


def render(ctx) -> None:
    CLOUD_HOST, SCHED_VS_EDGE, STAT = ctx.CLOUD_HOST, ctx.SCHED_VS_EDGE, ctx.STAT
    st.markdown("<div class='fluid-view'>", unsafe_allow_html=True)

    # Hero Section
    hero_l, hero_r = st.columns([1.18, 0.82], gap="large")
    with hero_l:
        st.markdown(
            """
            <div style="padding: 1.0rem 0 1.2rem 0;">
                <div class="tech-chip" style="margin-bottom: 1.4rem; border-color: rgba(245,158,11,0.25); color: var(--accent-amber);">
                    <span class="pulse-dot-amber"></span> AUTONOMOUS HYBRID SCHEDULING
                </div>
                <h1 style="font-size: 3.3rem; font-weight: 700; line-height: 1.12; letter-spacing: -0.03em; margin-bottom: 1.2rem; color: var(--text-pure);">
                    Intelligent Workload Routing<br>
                    Between <span class="gradient-text">Edge & AWS Cloud</span>
                </h1>
                <p style="font-size: 1.05rem; color: var(--text-muted); line-height: 1.7; max-width: 570px; margin-bottom: 2.2rem;">
                    Static Python AST analysis evaluates computational complexity in microseconds to autonomously route code between local edge hardware and AWS EC2 instances based on real-time network latency.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        btn_c1, btn_c2, _ = st.columns([3.5, 3.5, 3.0], gap="small")
        with btn_c1:
            if st.button("Launch Live Dispatch →", type="primary", use_container_width=True, width="stretch"):
                st.session_state.current_tab = "playground"
                st.rerun()
        with btn_c2:
            if st.button("Cluster Topology & RTT", type="secondary", use_container_width=True, width="stretch"):
                st.session_state.current_tab = "endpoints"
                st.rerun()

    with hero_r:
        st.markdown(
            f"""
            <div class="dev-card" style="padding: 1.8rem 1.6rem; border-color: var(--border-hover);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem;">
                    <span class="tech-chip" style="color: var(--accent-amber);">SYSTEM TOPOLOGY</span>
                    <span class="tech-chip" style="color: #10B981; border-color: rgba(16,185,129,0.3);">
                        <span class="pulse-dot"></span> REST FABRIC READY
                    </span>
                </div>
                <div style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.8rem;">
                    Real-Time Latency Arbitration
                </div>
                <div style="background: var(--surface-well); border: 4px solid var(--border-color); box-shadow: var(--card-shadow); border-radius: 0px; padding: 12px 14px; margin-bottom: 1.2rem; font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted); line-height: 1.85;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>01 / Static AST Profiling</span>
                        <span style="color: var(--accent-amber);">{STAT['extract_ms']:.2f}ms</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>02 / ML Routing Decision</span>
                        <span style="color: #10B981;">{SCHED_VS_EDGE} vs edge-only</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>03 / WAN Delay Modeling</span>
                        <span style="color: var(--text-pure);">{STAT['rtt_ms']:.0f}ms RTT</span>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 1.2rem;">
                    <div style="background: var(--surface-well); padding: 10px 12px; border-radius: 0px; border: 4px solid var(--border-color); box-shadow: var(--card-shadow);">
                        <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted);">LOCAL EDGE</div>
                        <div style="font-family: var(--font-heading); font-size: 0.98rem; font-weight: 700; color: var(--text-pure);">localhost:8000</div>
                        <div style="font-family: var(--font-mono); font-size: 0.68rem; color: #10B981;">0ms Transit Penalty</div>
                    </div>
                    <div style="background: var(--surface-well); padding: 10px 12px; border-radius: 0px; border: 4px solid var(--border-color); box-shadow: var(--card-shadow);">
                        <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted);">AWS EC2 CLOUD</div>
                        <div style="font-family: var(--font-heading); font-size: 0.98rem; font-weight: 700; color: var(--text-pure);">{CLOUD_HOST}</div>
                        <div style="font-family: var(--font-mono); font-size: 0.68rem; color: var(--accent-amber);">{STAT['rtt_ms']:.0f}ms WAN Delay</div>
                    </div>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); border-top: 1px solid var(--border-color); padding-top: 10px; display: flex; justify-content: space-between;">
                    <span>Rule: Cost(Cloud) + RTT &lt; Cost(Edge)</span>
                    <span style="color: var(--accent-amber);">Dynamic Offload</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Key Validation Metrics Ribbon with Balanced Margin
    st.markdown("<div style='margin: 3.5rem 0 2.2rem 0; border-top: 1px solid var(--border-color);'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4, gap="medium")
    with m1:
        st.markdown(
            f"""
            <div class="dev-card" style="padding: 1.3rem 1.2rem; border-top: 2px solid var(--accent-amber);">
                <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">TOTAL TIME VS EDGE-ONLY</div>
                <div style="font-family: var(--font-heading); font-size: 2.1rem; font-weight: 700; color: var(--text-pure); margin: 3px 0;">{SCHED_VS_EDGE}</div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: #10B981;">Held-out script families</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m2:
        st.markdown(
            f"""
            <div class="dev-card" style="padding: 1.3rem 1.2rem; border-top: 2px solid var(--accent-emerald);">
                <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">PROFILING LATENCY</div>
                <div style="font-family: var(--font-heading); font-size: 2.1rem; font-weight: 700; color: var(--text-pure); margin: 3px 0;">{STAT['extract_ms']:.2f}ms</div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: #10B981;">Zero Execution Risk</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m3:
        st.markdown(
            f"""
            <div class="dev-card" style="padding: 1.3rem 1.2rem; border-top: 2px solid var(--accent-purple);">
                <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">EVALUATED WORKLOADS</div>
                <div style="font-family: var(--font-heading); font-size: 2.1rem; font-weight: 700; color: var(--text-pure); margin: 3px 0;">{STAT['scripts']}</div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted);">Diverse AST Scripts</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m4:
        st.markdown(
            f"""
            <div class="dev-card" style="padding: 1.3rem 1.2rem; border-top: 2px solid var(--accent-cyan);">
                <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">REGRESSION FIT</div>
                <div style="font-family: var(--font-heading); font-size: 2.1rem; font-weight: 700; color: var(--text-pure); margin: 3px 0;">{STAT['cloud_r2']:.2f}</div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted);">Cloud latency R², held-out</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Core Architectural Pillars (3 Clean Cards with Generous Spacing)
    st.markdown(
        """
        <div style="margin: 3.5rem 0 1.6rem 0;">
            <div class="tech-chip" style="color: var(--accent-amber); margin-bottom: 6px;">CORE ARCHITECTURE</div>
            <h2 style="font-size: 1.9rem; color: var(--text-pure);">Architectural Foundations</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(
            """
            <div class="dev-card">
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-amber); margin-bottom: 0.6rem; font-weight: 600;">01 / STATIC PROFILING</div>
                <div style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.5rem;">
                    AST Syntax Analysis
                </div>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.65; margin: 0;">
                    Parses abstract syntax trees to measure matrix operations, nested loop depth, and recursion in microseconds—without executing untrusted code.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <div class="dev-card">
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-amber); margin-bottom: 0.6rem; font-weight: 600;">02 / NETWORK AWARENESS</div>
                <div style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.5rem;">
                    RTT Compensation
                </div>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.65; margin: 0;">
                    Dynamically models real-time WAN round-trip delays, guaranteeing that cloud offloading only occurs when compute speedup exceeds transit time.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            """
            <div class="dev-card">
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-amber); margin-bottom: 0.6rem; font-weight: 600;">03 / MACHINE LEARNING</div>
                <div style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.5rem;">
                    Dual-Engine Inference
                </div>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.65; margin: 0;">
                    Two gradient-boosted regressors predict edge and cloud time. The scheduler offloads only when predicted cloud compute plus network RTT beats the edge.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)
