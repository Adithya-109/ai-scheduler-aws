"""Schedule, dispatch and show one workload."""

import plotly.graph_objects as go
import streamlit as st


def execute_workload(ctx, code_string, filename, dispatcher):
    """Schedule and run one script through the Dispatcher (fallback, circuit
    breaker, live RTT, history and the decision log all apply)."""
    chart_act, chart_grid, chart_pred, chart_text = ctx.chart_act, ctx.chart_grid, ctx.chart_pred, ctx.chart_text
    st.toast("Scheduling and dispatching", icon="🛰️")
    try:
        res = dispatcher.run(code_string)
    except Exception as ex:  # an edge failure is a real error; cloud errors fall back inside run()
        st.error(f"Execution failed: {ex}")
        return

    if "error" in res:
        st.error(f"AST Parsing Failed for {filename}: {res['error']}")
        return

    preds = res["predictions"]
    decision = res["decision"]
    confidence = res.get("confidence", 0)
    decision_method = res.get("decision_method", "regression")
    is_edge = res["target"] == "edge"
    target_name = "Local Edge Worker" if is_edge else "AWS EC2 Cloud Node"
    target_url = dispatcher.edge.url if is_edge else dispatcher.cloud.url
    if res.get("fallback"):
        st.warning(f"The scheduler chose {decision} but the job ran on the local edge worker ({res['fallback']}).")
    if res.get("explored"):
        st.info("Exploration run: this low-confidence job was sent to the other side so the models see both.")

    st.markdown("<br>", unsafe_allow_html=True)

    banner_class = "edge-decision" if is_edge else "cloud-decision"
    badge_color = "#10B981" if is_edge else "var(--accent-amber)"

    st.markdown(
        f"""
        <div class="decision-banner {banner_class}" style="margin: 1.5rem 0 1.2rem 0;">
            <div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.08em; margin-bottom: 4px;">
                    ROUTING DECISION · {decision_method.upper()} ({confidence:.1%} CONFIDENCE)
                </div>
                <div style="font-family: var(--font-heading); font-size: 1.3rem; font-weight: 700; color: {badge_color};">
                    Dispatched to {target_name}
                </div>
            </div>
            <div class="tech-chip" style="font-size: 0.8rem; padding: 5px 12px;">
                URL: {target_url}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.metric(label="Predicted Edge Latency", value=f"{preds['predicted_edge_time']:.4f} s")
    with m2:
        st.metric(label="Predicted Cloud Latency", value=f"{preds['predicted_cloud_time']:.4f} s")
    with m3:
        speedup = (preds['predicted_edge_time'] - preds['predicted_cloud_time'])
        st.metric(label="Predicted Offload Delta", value=f"{speedup:+.4f} s", delta="Cloud Speedup" if speedup > 0 else "Edge Faster")

    worker_data = res["worker"]
    total_rtt = res["wall_time_s"]
    st.markdown(
        """
    <style>
    @keyframes doneBanner {
        0%   { opacity: 0; transform: translate(-50%, -14px); }
        12%  { opacity: 1; transform: translate(-50%, 0); }
        78%  { opacity: 1; transform: translate(-50%, 0); }
        100% { opacity: 0; transform: translate(-50%, -6px); visibility: hidden; }
    }
    .done-banner {
        position: fixed; top: 18px; left: 50%; z-index: 999999; pointer-events: none;
        padding: 14px 26px; min-width: 320px; text-align: center;
        background: var(--surface-card); color: var(--text-pure);
        border: 4px solid var(--border-color); box-shadow: var(--card-shadow);
        font-family: var(--font-heading); font-size: 0.95rem; letter-spacing: 0.02em;
        animation: doneBanner 1.6s ease-out forwards;
    }
    .done-banner b { color: var(--accent-emerald); }
    .done-banner span { font-family: var(--font-mono); font-size: 1.3rem; color: var(--text-muted); }
    </style>
    <div class="done-banner"><b>DONE</b> &middot; ran on __TARGET__<br><span>__TIME__ s round trip</span></div>
    <style>
    @keyframes arcadeFlash { 0%,100% { opacity: 0; } 8%,70% { opacity: 1; } 85% { opacity: 0; } }
    @keyframes arcadeRun { 0% { left: 6%; } 60%,100% { left: __END__%; } }
    @keyframes arcadePop { 0% { transform: scale(0.2); opacity: 0; } 55% { transform: scale(1.25); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
    @keyframes arcadeCoin { 0% { transform: translateY(0); opacity: 1; } 100% { transform: translateY(-60px); opacity: 0; } }
    .arcade { position: fixed; left: 0; right: 0; top: 38%; height: 190px; z-index: 999998; pointer-events: none;
        background: rgba(0,0,0,0.82); border-top: 4px solid #45f3ff; border-bottom: 4px solid #ff003c;
        font-family: 'Press Start 2P', cursive; color: #fff; animation: arcadeFlash 1.8s steps(12) forwards; opacity: 0; }
    .arcade .lane { position: absolute; left: 6%; right: 6%; top: 112px; border-top: 4px dashed #555; }
    .arcade .end { position: absolute; top: 90px; font-size: 14px; color: #45f3ff; }
    .arcade .end.l { left: 2%; } .arcade .end.r { right: 2%; }
    .arcade .ship { position: absolute; top: 80px; font-size: 34px; animation: arcadeRun 1.1s steps(10) forwards; }
    .arcade .title { position: absolute; top: 18px; width: 100%; text-align: center; font-size: 26px; color: #ffe600;
        text-shadow: 4px 4px 0 #ff003c; animation: arcadePop 0.6s steps(6) 0.7s both; }
    .arcade .coin { position: absolute; top: 60px; font-size: 22px; color: #ffe600; animation: arcadeCoin 0.7s steps(7) 1s both; }
    </style>
    <div class="arcade"><div class="title">STAGE CLEAR!</div>
        <div class="end l">EDGE</div><div class="end r">CLOUD</div><div class="lane"></div>
        <div class="ship">&#9654;&#9654;</div>
        <span class="coin" style="left:30%">&#9733;</span><span class="coin" style="left:50%">&#9733;</span><span class="coin" style="left:70%">&#9733;</span></div>
    """.replace("__END__", "8" if is_edge else "88").replace("__TARGET__", "EDGE" if is_edge else "CLOUD").replace("__TIME__", f"{total_rtt:.3f}"),
        unsafe_allow_html=True,
    )

    if worker_data:
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        col_out, col_chart = st.columns([1.1, 1.3], gap="large")

        with col_out:
            st.markdown(
                """
                <div style="background: var(--surface-well); border: 4px solid var(--border-color); box-shadow: var(--card-shadow); border-radius: 0px; padding: 8px 12px; margin-bottom: 8px; font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); display: flex; justify-content: space-between;">
                    <span>RUNTIME EXECUTION CONSOLE</span>
                    <span style="color:#10B981;">200 OK</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            if worker_data.get("stdout"):
                st.code(worker_data["stdout"], language="text")
            if worker_data.get("stderr"):
                st.error(worker_data["stderr"])

            st.markdown(
                f"""
                <div style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted); margin-top: 8px;">
                    Worker Compute: <b style="color:var(--text-pure);">{worker_data.get('execution_time_seconds', 0):.4f}s</b> &nbsp;|&nbsp;
                    Network Round-Trip: <b style="color:var(--accent-amber);">{total_rtt:.4f}s</b>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_chart:
            st.markdown(
                """
                <div style="font-family: var(--font-heading); font-size: 1.05rem; font-weight: 700; color: var(--text-pure); margin-bottom: 8px;">
                    Execution Telemetry Comparison
                </div>
                """,
                unsafe_allow_html=True
            )
            categories = ["Local Edge", "AWS Cloud"]
            pred_values = [preds["predicted_edge_time"], preds["predicted_cloud_time"]]
            actual_values = [
                total_rtt if is_edge else 0,
                total_rtt if not is_edge else 0
            ]
            actual_texts = [
                f"{total_rtt:.4f} s" if is_edge else "Not Dispatched",
                f"{total_rtt:.4f} s" if not is_edge else "Not Dispatched"
            ]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Predicted Latency",
                x=categories,
                y=pred_values,
                marker_color=chart_pred,
                text=[f"{v:.4f} s" for v in pred_values],
                textposition="outside",
                hovertemplate="<b>%{x} (Predicted)</b>: %{y:.4f} s<extra></extra>"
            ))
            fig.add_trace(go.Bar(
                name="Actual RTT",
                x=categories,
                y=actual_values,
                marker_color=chart_act,
                text=actual_texts,
                textposition="outside",
                hovertemplate="<b>%{x} (Actual)</b>: %{text}<extra></extra>"
            ))

            all_vals = pred_values + [total_rtt]
            max_y = max(all_vals) if all_vals else 1.0

            fig.update_layout(
                barmode="group", bargap=0.3, bargroupgap=0.08,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=260,
                margin=dict(l=15, r=15, t=25, b=25),
                font=dict(color=chart_text, family="Space Grotesk, sans-serif", size=11),
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0, font=dict(size=11, color=chart_text)),
                xaxis=dict(showgrid=False, linecolor=chart_grid, tickfont=dict(size=11, color=chart_text)),
                yaxis=dict(showgrid=True, gridcolor=chart_grid, zeroline=True, zerolinecolor=chart_grid, range=[0, max_y * 1.35], ticksuffix=" s", tickfont=dict(size=11, color=chart_text))
            )
            st.plotly_chart(fig, use_container_width=True, width="stretch")
