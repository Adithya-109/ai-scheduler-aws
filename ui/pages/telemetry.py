"""telemetry page."""

import plotly.graph_objects as go
import streamlit as st

import config
from pipeline import reporting
from pipeline.telemetry import DecisionLog


def render(ctx) -> None:
    SCHED_VS_EDGE, STAT, chart_grid, chart_pred, chart_text, get_curve = ctx.SCHED_VS_EDGE, ctx.STAT, ctx.chart_grid, ctx.chart_pred, ctx.chart_text, ctx.get_curve
    st.markdown("<div class='fluid-view'>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="margin-bottom: 1.8rem;">
            <h2 style="font-size: 1.8rem; margin: 0 0 4px 0;">Telemetry</h2>
            <p style="color: var(--text-muted); font-size: 0.95rem; margin: 0;">Measured on {STAT['scripts']} real edge/cloud timings. Accuracy is judged by total wall-clock time against always-edge, always-cloud and the oracle, with whole script families held out.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1:
        st.metric(label="Scheduler vs always-edge", value=SCHED_VS_EDGE, delta="total time, held-out", delta_color="off")
    with k2:
        st.metric(label="Latency R² (edge / cloud)", value=f"{STAT['edge_r2']:.2f} / {STAT['cloud_r2']:.2f}", delta="held-out families", delta_color="off")
    with k3:
        st.metric(label="Measured cloud wins", value=f"{STAT['cloud_wins']} / {STAT['scripts']}", delta="compute + RTT < edge", delta_color="off")
    with k4:
        st.metric(label="AST extraction (median)", value=f"{STAT['extract_ms']:.2f} ms", delta="measured now", delta_color="off")

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

    chart_c1, chart_c2 = st.columns([1.25, 0.75], gap="large")
    with chart_c1:
        st.markdown(
            """
            <div style="font-size: 1.05rem; font-weight: 650; color: var(--text-pure); margin-bottom: 0.6rem;">
                Measured time: edge vs. cloud plus round trip
            </div>
            """,
            unsafe_allow_html=True
        )
        curve = get_curve(st.session_state.sim_cloud_rtt)
        x_complexity, y_edge, y_cloud_net = curve["x"], curve["edge"], curve["cloud_plus_rtt"]

        curve_fig = go.Figure()
        curve_fig.add_trace(go.Scatter(
            x=x_complexity, y=y_edge,
            mode='lines+markers', name='Edge',
            line=dict(color='#059669', width=3),
            marker=dict(size=7)
        ))
        curve_fig.add_trace(go.Scatter(
            x=x_complexity, y=y_cloud_net,
            mode='lines+markers', name=f"Cloud + {st.session_state.sim_cloud_rtt} ms round trip",
            line=dict(color=chart_pred, width=3, dash='dot'),
            marker=dict(size=7)
        ))

        curve_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=300, margin=dict(l=15, r=15, t=30, b=25),
            font=dict(color=chart_text, family="Inter, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0),
            xaxis=dict(title="Estimated complexity (log10 ops), median per bin", showgrid=True, gridcolor=chart_grid),
            yaxis=dict(title="Time (seconds)", showgrid=True, gridcolor=chart_grid)
        )
        st.plotly_chart(curve_fig, use_container_width=True, width="stretch")

    with chart_c2:
        st.markdown(
            """
            <div style="font-size: 1.05rem; font-weight: 650; color: var(--text-pure); margin-bottom: 0.6rem;">
                Routing decisions on held-out scripts
            </div>
            """,
            unsafe_allow_html=True
        )
        pie_fig = go.Figure(data=[go.Pie(
            labels=['Edge', 'Cloud'],
            values=[STAT['scripts'] - STAT['routed_to_cloud'], STAT['routed_to_cloud']],
            hole=.55,
            marker_colors=['#059669', chart_pred]
        )])
        pie_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=300, margin=dict(l=10, r=10, t=10, b=10),
            font=dict(color=chart_text, family="Inter, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
        )
        st.plotly_chart(pie_fig, use_container_width=True, width="stretch")

    # ---- what the running system has actually done ----
    live = reporting.live_log_summary(DecisionLog(config.DECISION_LOG).read())
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 650; color: var(--text-pure); margin-bottom: 0.6rem;">
            Decision log for this deployment
        </div>
        """,
        unsafe_allow_html=True
    )
    l1, l2, l3, l4 = st.columns(4, gap="medium")
    with l1:
        st.metric(label="Logged runs", value=f"{live['runs']}")
    with l2:
        st.metric(label="Ran on cloud", value=f"{live['on_cloud']}")
    with l3:
        st.metric(label="Fallbacks / explored runs", value=f"{live['fallbacks']} / {live['explored']}")
    with l4:
        err = live["pred_vs_actual_median_abs_pct"]
        st.metric(label="Prediction error (median)", value="n/a" if err is None else f"{err:.0f}%")
    if live["recent"]:
        st.dataframe(live["recent"], use_container_width=True, hide_index=True)
    else:
        st.caption("No runs logged yet. Run something from the Dispatch tab and it is recorded in "
                   f"{config.DECISION_LOG}.")

    st.markdown("</div>", unsafe_allow_html=True)
